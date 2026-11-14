"""Turn a picture of line art / handwriting into pen-plotter G-code for a
Klipper printer (Elegoo Neptune 4). The ink is traced down its centre line so
each stroke is drawn once, like a person writing it.

Usage: python image_to_gcode.py input.png output.gcode [--width 180] [--height 135]
                                [--down 4.6] [--up 7] [--preview preview.png]
"""
import argparse

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, gaussian_filter1d
from skimage.filters import threshold_otsu
from skimage.measure import approximate_polygon, label, regionprops
from skimage.morphology import remove_small_objects, skeletonize, binary_closing, closing, disk

NEIGHBOURS = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

# Z height the pen tip is told it is at while touching the paper (see START).
TOUCH_Z = 5.0


def crop_to_paper(img, inset=0.012):
    """For photos: crop away the dark background around the sheet of paper."""
    grey = np.asarray(img, dtype=float)
    bright = grey > threshold_otsu(grey)
    rows = np.nonzero(bright.mean(axis=1) > 0.6)[0]
    cols = np.nonzero(bright.mean(axis=0) > 0.6)[0]
    dy, dx = int(inset * img.height), int(inset * img.width)
    # Only trim past the paper's edge on sides where there is background to remove.
    left = cols[0] + dx if cols[0] > 0 else 0
    top = rows[0] + dy if rows[0] > 0 else 0
    right = cols[-1] - dx if cols[-1] < img.width - 1 else img.width
    bottom = rows[-1] - dy if rows[-1] < img.height - 1 else img.height
    return img.crop((left, top, right, bottom))


def flatten_lighting(img):
    """For photos: divide out shadows and uneven lighting so the paper is an
    even white everywhere and only the ink stays dark."""
    grey = np.asarray(img, dtype=float)
    background = closing(grey, disk(8))  # paper brightness with the ink removed
    background = gaussian_filter(background, 10)
    flat = np.clip(grey / np.maximum(background, 1) * 255, 0, 255)
    return Image.fromarray(flat.astype(np.uint8))


def load_ink(path, min_width=2000, threshold=None, photo=False):
    """Threshold the ink. Small images are enlarged first so thin, faint pen
    lines stay joined up and keep enough pixels to trace."""
    img = Image.open(path).convert("L")
    if photo:
        img = flatten_lighting(crop_to_paper(img))
    factor = max(1, int(np.ceil(min_width / img.width)))
    if factor > 1:
        img = img.resize((img.width * factor, img.height * factor), Image.BICUBIC)
    grey = np.asarray(img, dtype=float)
    ink = grey < (threshold if threshold else threshold_otsu(grey))
    ink = binary_closing(ink, disk(1))
    return remove_small_objects(ink, 4 * factor), factor


def split_small_marks(ink, max_px=7):
    """Pull out dots, decimal points and short dashes, which skeletonising
    would shrink to nothing. Returns the remaining ink and a list of short
    (row, col) strokes, one per mark: a line along it if elongated, else a dot."""
    big = ink.copy()
    marks = []
    for r in regionprops(label(ink)):
        r0, c0, r1, c1 = r.bbox
        h, w = r1 - r0, c1 - c0
        if max(h, w) > max_px:
            continue
        big[r.slice][r.image] = False
        cy, cx = r.centroid
        if w >= 2 * h:
            marks.append(np.array([[cy, c0 + 0.5], [cy, c1 - 1.5]]))
        elif h >= 2 * w:
            marks.append(np.array([[r0 + 0.5, cx], [r1 - 1.5, cx]]))
        else:
            marks.append(np.array([[cy, cx - 1.5], [cy, cx + 1.5]]))
    return big, marks


def trace_skeleton(skel, spur_px=0):
    """Walk the 1-pixel skeleton into polylines of (row, col) points."""
    pixels = set(zip(*np.nonzero(skel)))

    def nbrs(p):
        return [(p[0] + dr, p[1] + dc) for dr, dc in NEIGHBOURS if (p[0] + dr, p[1] + dc) in pixels]

    degree = {p: len(nbrs(p)) for p in pixels}
    visited = set()  # undirected edges already drawn

    def edge(a, b):
        return (a, b) if a < b else (b, a)

    def walk(start, nxt):
        path = [start, nxt]
        visited.add(edge(start, nxt))
        prev, cur = start, nxt
        while degree[cur] == 2:
            step = [n for n in nbrs(cur) if n != prev and edge(cur, n) not in visited]
            if not step:
                break
            prev, cur = cur, step[0]
            visited.add(edge(prev, cur))
            path.append(cur)
        return path

    paths = []
    # Endpoints and junctions first, then whatever is left (closed loops like "O").
    nodes = [p for p in pixels if degree[p] != 2] + [p for p in pixels if degree[p] == 2]
    for p in nodes:
        for n in nbrs(p):
            if edge(p, n) not in visited:
                paths.append(walk(p, n))

    # Skeletons grow little whiskers off thick strokes and leave tiny scraps
    # inside junctions; drawing those makes the writing look jagged.
    kept = []
    for path in paths:
        free = [degree[path[0]] == 1, degree[path[-1]] == 1]
        if free[0] != free[1] and len(path) < spur_px:
            continue
        if not any(free) and len(path) <= 3:
            continue
        kept.append(path)
    return kept


def smooth(p, step=0.1, sigma=0.22):
    """Resample a polyline (mm) evenly and Gaussian-smooth it so pixel
    staircases become flowing pen strokes. Ends stay put; loops wrap."""
    seg = np.hypot(*np.diff(p, axis=0).T)
    total = seg.sum()
    if total < 3 * step:
        return p
    dist = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, total, int(total / step) + 1)
    q = np.column_stack([np.interp(t, dist, p[:, 0]), np.interp(t, dist, p[:, 1])])
    closed = np.hypot(*(p[0] - p[-1])) < 2 * step
    q = gaussian_filter1d(q, sigma / step, axis=0, mode="wrap" if closed else "nearest")
    if not closed:
        q[0], q[-1] = p[0], p[-1]
    return approximate_polygon(q, tolerance=0.015)


def heading(p, at_end, reach=0.6):
    """Unit direction a stroke travels at its start (or end), measured over
    `reach` mm so pixel noise doesn't dominate."""
    q = p[::-1] if at_end else p
    dist = np.hypot(*(q - q[0]).T)
    far = q[min(np.searchsorted(dist, reach), len(q) - 1)]
    v = (q[0] - far) if at_end else (far - q[0])
    n = np.hypot(*v)
    return v / n if n else v


def order_paths(paths, gap, start=(0.0, 0.0)):
    """Greedy nearest-neighbour ordering, reversing paths where shorter. Where
    several strokes meet the pen, it carries on along the straightest one, so
    lines run smoothly through crossings instead of turning corners."""
    remaining = list(paths)
    ordered, pos, direction = [], np.array(start, dtype=float), None
    while remaining:
        best, best_score, best_rev = 0, float("inf"), False
        for i, p in enumerate(remaining):
            for rev, end in ((False, p[0]), (True, p[-1])):
                d = np.hypot(*(end - pos))
                score = d
                if direction is not None and d <= gap and len(p) > 1:
                    # Touching strokes: rank by how straight the join is.
                    score = -float(np.dot(direction, heading(p[::-1] if rev else p, False)))
                    score -= 10  # always beats strokes that need a pen lift
                if score < best_score:
                    best, best_score, best_rev = i, score, rev
        p = remaining.pop(best)
        p = p[::-1] if best_rev else p
        ordered.append(p)
        pos = p[-1]
        direction = heading(p, True) if len(p) > 1 else None
    return ordered


def join_close(paths, gap, min_cos=0.5):
    """Merge consecutive paths whose ends nearly touch and that carry on in
    roughly the same direction, saving pen lifts without making sharp kinks."""
    joined = [paths[0]]
    for p in paths[1:]:
        prev = joined[-1]
        close = np.hypot(*(p[0] - prev[-1])) <= gap
        if close and len(p) > 1 and len(prev) > 1 and \
                np.dot(heading(prev, True), heading(p, False)) >= min_cos:
            joined[-1] = np.vstack([prev, p])
        else:
            joined.append(p)
    return joined


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--width", type=float, default=180, help="max drawing width, mm")
    ap.add_argument("--height", type=float, default=135, help="max drawing height, mm")
    ap.add_argument("--down", type=float, default=TOUCH_Z - 0.4, help="pen-down Z")
    ap.add_argument("--up", type=float, default=TOUCH_Z + 2.0, help="pen-up Z")
    ap.add_argument("--draw-speed", type=float, default=1800, help="mm/min")
    ap.add_argument("--travel-speed", type=float, default=4000, help="mm/min")
    ap.add_argument("--z-speed", type=float, default=600, help="pen lift/lower speed, mm/min")
    ap.add_argument("--accel", type=float, help="acceleration limit, mm/s^2 (default: printer's)")
    ap.add_argument("--corner", type=float, help="square corner velocity, mm/s (default: printer's)")
    ap.add_argument("--photo", action="store_true",
                    help="input is a photo of paper: crop to the sheet and even out lighting")
    ap.add_argument("--last", type=lambda s: [float(v) for v in s.split(",")],
                    help="x0,y0,x1,y1 box (0-1 fractions of the image) drawn last")
    ap.add_argument("--threshold", type=float,
                    help="0-255 grey level counted as ink (default: automatic)")
    ap.add_argument("--preview")
    a = ap.parse_args()

    ink, factor = load_ink(a.input, threshold=a.threshold, photo=a.photo)
    h_px, w_px = ink.shape
    paths, marks = trace_ink(ink)

    # Trim the unused margin around the ink, then scale to fit the paper area.
    rows, cols = np.nonzero(ink)
    r0, c0 = rows.min(), cols.min()
    scale = min(a.width / (cols.max() - c0), a.height / (rows.max() - r0))
    height_mm = (rows.max() - r0) * scale

    mm_paths = []
    for p in paths:
        p = np.array(p, dtype=float)
        xy = np.column_stack([(p[:, 1] - c0) * scale, height_mm - (p[:, 0] - r0) * scale])
        if len(xy) >= 2 and np.hypot(*(xy[-1] - xy[0])) + np.sum(np.hypot(*np.diff(xy, axis=0).T)) > 0.4:
            mm_paths.append(xy)
    for p in marks:
        mm_paths.append(np.column_stack([(p[:, 1] - c0) * scale, height_mm - (p[:, 0] - r0) * scale]))
    # Strokes whose centre lies in the --last box (fractions of the image) are
    # drawn after everything else.
    first, last = mm_paths, []
    if a.last:
        fx0, fy0, fx1, fy1 = a.last
        x0, x1 = (fx0 * w_px - c0) * scale, (fx1 * w_px - c0) * scale
        y0, y1 = height_mm - (fy1 * h_px - r0) * scale, height_mm - (fy0 * h_px - r0) * scale
        inside = lambda p: x0 <= p[:, 0].mean() <= x1 and y0 <= p[:, 1].mean() <= y1
        first = [p for p in mm_paths if not inside(p)]
        last = [p for p in mm_paths if inside(p)]
    mm_paths = join_close(order_paths(first, gap=0.35), gap=0.35)
    n_first = len(mm_paths)
    if last:
        mm_paths += join_close(order_paths(last, gap=0.35), gap=0.35)
    mm_paths = [smooth(p) for p in mm_paths]

    out = gcode_lines(mm_paths, height_mm, a)
    with open(a.output, "w") as f:
        f.write("\n".join(out))

    if a.preview:
        k = 6  # preview pixels per mm
        img = Image.new("RGB", (int(a.width * k) + 20, int(height_mm * k) + 20), "white")
        d = ImageDraw.Draw(img)
        to_px = lambda x, y: (10 + x * k, 10 + (height_mm - y) * k)
        # Strokes drawn last are shown in red.
        for i, p in enumerate(mm_paths):
            colour = (20, 30, 120) if i < n_first else (200, 30, 30)
            d.line([to_px(x, y) for x, y in p], fill=colour, width=2)
        img.save(a.preview)

    print("%d strokes, %d G-code lines, %.0f x %.0f mm" % (
        len(mm_paths), len(out), max(p[:, 0].max() for p in mm_paths), height_mm))


def trace_ink(ink):
    """Turn an ink mask into pen strokes: centre-line paths plus short marks
    for dots, both as (row, col) pixel arrays."""
    # A dot is about one pen-width across; anything much bigger is a letter.
    pen_px = ink.sum() / max(skeletonize(ink).sum(), 1)
    lines_ink, marks = split_small_marks(ink, max_px=max(3, 2.2 * pen_px))
    skel = skeletonize(lines_ink)
    stroke_px = lines_ink.sum() / max(skel.sum(), 1)  # average pen width in pixels
    paths = trace_skeleton(skel, spur_px=0.7 * stroke_px)

    # Filled blobs such as bullet points skeletonise to almost nothing; any
    # shape that produced no stroke at all is drawn as a dot instead.
    blobs = label(lines_ink)
    traced = {blobs[r, c] for path in paths if len(path) > 2 for r, c in path}
    for r in regionprops(blobs):
        if r.label not in traced:
            cy, cx = r.centroid
            marks.append(np.array([[cy, cx - 1.5], [cy, cx + 1.5]]))
    return paths, marks


def gcode_lines(mm_paths, height_mm, a):
    """The full G-code program for a list of pen strokes (mm, in drawing order)."""
    out = [
        "; Pen plot generated by image_to_gcode.py",
        "; BEFORE STARTING: pen tip must be resting on the paper at the",
        "; FRONT-LEFT corner of the drawing. Drawing size: %.0f x %.0f mm" % (
            max(p[:, 0].max() for p in mm_paths), height_mm),
        "SET_GCODE_OFFSET Z=0",
        "BED_MESH_CLEAR",
        "SET_KINEMATIC_POSITION X=0 Y=0 Z=%.2f" % TOUCH_Z,
        "G21",
        "G90",
        "G1 Z%.2f F%d" % (a.up, a.z_speed),
    ]
    if a.accel or a.corner:
        limits = ""
        if a.accel:
            limits += " ACCEL=%d ACCEL_TO_DECEL=%d" % (a.accel, a.accel)
        if a.corner:
            limits += " SQUARE_CORNER_VELOCITY=%g" % a.corner
        out.insert(out.index("G21"), "SET_VELOCITY_LIMIT" + limits)
    for p in mm_paths:
        out.append("G0 X%.2f Y%.2f F%d" % (p[0, 0], p[0, 1], a.travel_speed))
        out.append("G1 Z%.2f F%d" % (a.down, a.z_speed))
        out.extend("G1 X%.2f Y%.2f F%d" % (x, y, a.draw_speed) for x, y in p[1:])
        out.append("G1 Z%.2f F%d" % (a.up, a.z_speed))
    out += ["G1 Z%.2f F%d" % (TOUCH_Z + 10, a.z_speed), "G0 X0 Y0 F%d" % a.travel_speed, "M84", ""]
    return out


if __name__ == "__main__":
    main()
