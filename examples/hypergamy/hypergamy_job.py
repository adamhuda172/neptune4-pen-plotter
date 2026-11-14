"""Pen-plot the "Hypergamy - Mathematical Model" notes photo in a set order:

  1. text above the equation box
  2. the four equations inside the box, all in one go
  3. text below the box
  4. the mapping diagram, all in one go: numbers, N labels and dots first,
     then each oval as one loop, then each arrow as one sweep plus its head
  5. "- Mathematical Model" and the title underline
  6. last of all, the four lines of the box around the equations

Usage: python hypergamy_job.py photo.webp out.gcode --preview preview.png
"""
import argparse
import pathlib
import sys
from types import SimpleNamespace

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt, gaussian_filter1d
from skimage.measure import EllipseModel, LineModelND, label, ransac, regionprops
from skimage.morphology import skeletonize

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))  # the repo root
import image_to_gcode as itg  # noqa: E402

# Positions in the original photo's pixels, as (x0, y0, x1, y1).
DIAGRAM = (476, 45, 680, 282)
OVALS = [(476, 70, 566, 272), (582, 70, 680, 282)]
ARROW_ZONE = (527, 92, 623, 255)  # between the left numbers and the right ones
BOX = (40, 322, 372, 476)         # the box lines and everything inside them
BOX_LINES = {"left": 54, "right": 361, "top": 333, "bottom": 466}
BOTTOM_CUT = 663                  # tops of a cut-off line peeking in at the bottom
TITLE_BOTTOM = 56                 # the title and its underline sit above this
TITLE_SPLIT = 150                 # "Hypergamy" ends left of this; "- Mathematical Model" starts right
# Which right-hand row each arrow ends on, counting rows from the top:
# 1->2, 2->4, 3->8, 4->6, 5->10.
ARROW_ENDS = [0, 1, 3, 2, 4]

GROUP_COLOURS = {
    "text above box": (20, 30, 120), "equations": (0, 130, 60), "text below box": (20, 30, 120),
    "numbers and dots": (200, 120, 0), "ovals": (150, 0, 150), "arrows": (200, 30, 30),
    "title end": (230, 0, 120), "box lines": (0, 150, 200),
}


def box_border(ink, f):
    """Ink belonging to the four hand-drawn box lines. Each line is fitted
    straight through the ink near where it was drawn, then everything within
    a pen-width or so of those lines counts as border."""
    rows, cols = np.indices(ink.shape)
    x0, y0, x1, y1 = (v * f for v in BOX)
    inside = (cols >= x0) & (cols <= x1) & (rows >= y0) & (rows <= y1)
    band = 4 * f
    border = np.zeros_like(ink)
    for edge, at in BOX_LINES.items():
        vertical = edge in ("left", "right")
        near = inside & ink & (np.abs((cols if vertical else rows) - at * f) < 2 * band)
        r, c = np.nonzero(near)
        along, across = (r, c) if vertical else (c, r)
        slope, offset = np.polyfit(along, across, 1)
        expected = slope * (rows if vertical else cols) + offset
        border |= inside & ink & (np.abs((cols if vertical else rows) - expected) < band)
    return border


def fit_oval(ink, f, bbox):
    """Fit an ellipse to one hand-drawn oval, ignoring the numbers and arrows
    that sit inside or cross it, and return the ink lying on it."""
    rows, cols = np.indices(ink.shape)
    x0, y0, x1, y1 = (v * f for v in bbox)
    in_box = (cols >= x0) & (cols <= x1) & (rows >= y0) & (rows <= y1)
    r, c = np.nonzero(skeletonize(ink & in_box))
    pts = np.column_stack([c, r]).astype(float)
    model, _ = ransac(pts, EllipseModel, min_samples=5, residual_threshold=1.5 * f,
                      max_trials=3000, rng=0)
    r_all, c_all = np.nonzero(ink & in_box)
    dist = model.residuals(np.column_stack([c_all, r_all]).astype(float))
    on_oval = np.zeros_like(ink)
    on_oval[r_all[dist < 4 * f], c_all[dist < 4 * f]] = True
    return on_oval, model


def oval_loop(oval_ink, model, bins=120):
    """One continuous loop following the hand-drawn oval. Around the fitted
    ellipse, measure how far out the ink really is at each angle, so the loop
    keeps the oval's hand-drawn shape but is drawn in a single motion."""
    xc, yc, a, b, theta = model.params
    r, c = np.nonzero(skeletonize(oval_ink))
    ct, st = np.cos(theta), np.sin(theta)
    u = ((c - xc) * ct + (r - yc) * st) / a
    v = (-(c - xc) * st + (r - yc) * ct) / b
    which = ((np.arctan2(v, u) + np.pi) / (2 * np.pi) * bins).astype(int) % bins
    radius = np.hypot(u, v)
    reach = np.array([np.median(radius[which == i]) if (which == i).any() else np.nan
                      for i in range(bins)])
    k = np.arange(bins)
    known = ~np.isnan(reach)
    reach = np.interp(k, k[known], reach[known], period=bins)
    reach = gaussian_filter1d(reach, 2, mode="wrap")
    t = (k + 0.5) / bins * 2 * np.pi - np.pi
    t, reach = np.append(t, t[0]), np.append(reach, reach[0])
    uu, vv = reach * np.cos(t) * a, reach * np.sin(t) * b
    return np.column_stack([yc + uu * st + vv * ct, xc + uu * ct - vv * st])


def arrow_paths(arrow_ink, starts, heads, f):
    """Each arrow as one smooth sweep from its dot to its tip, plus a single
    stroke for the arrowhead. The sweep is a gentle curve fitted to the ink,
    pinned to the dot and the tip. `starts` and `heads` are the (row, col)
    centres of the start dots and the filled arrowheads, top to bottom."""
    ink_r, ink_c = np.nonzero(arrow_ink)
    r, c = np.nonzero(skeletonize(arrow_ink))
    out = []
    for i, (ys, xs) in enumerate(starts):
        hy, hx = heads[ARROW_ENDS[i]]
        # The tip is the furthest-right ink of that arrowhead.
        at_head = (np.abs(ink_r - hy) < 5 * f) & (np.abs(ink_c - hx) < 8 * f)
        j = np.argmax(np.where(at_head, ink_c, -1))
        yt, xt = float(ink_r[j]), float(ink_c[j])

        # y(x) = straight line + (x-xs)(x-xt)(p0 + p1(x-xs)): passes through both ends.
        line = lambda x: ys + (yt - ys) * (x - xs) / (xt - xs)
        bend = lambda x, p: (x - xs) * (x - xt) * (p[0] + p[1] * (x - xs))
        p = np.zeros(2)
        for band in (8 * f, 4 * f):
            use = (c > xs + 3 * f) & (c < xt - 8 * f) & (np.abs(r - line(c) - bend(c, p)) < band)
            x, y = c[use].astype(float), r[use].astype(float)
            g0 = (x - xs) * (x - xt)
            p = np.linalg.lstsq(np.column_stack([g0, g0 * (x - xs)]), y - line(x), rcond=None)[0]
        xx = np.linspace(xs, xt, int(xt - xs) + 1)
        sweep = np.column_stack([line(xx) + bend(xx, p), xx])
        out.append(sweep)

        # Arrowhead: one stroke from one barb, into the tip, out to the other.
        d = sweep[-1] - sweep[-1 - 3 * f]
        d /= np.hypot(*d)
        barbs = []
        for angle in (np.radians(28), -np.radians(28)):
            rot = np.array([[np.cos(angle), -np.sin(angle)], [np.sin(angle), np.cos(angle)]])
            barbs.append(sweep[-1] - 6 * f * (rot @ d))
        out.append(np.array([barbs[0], sweep[-1], barbs[1]]))
    return out


def find_dots(ink, f, region):
    """Centres and radii (pixels) of the filled dots at the start of each arrow."""
    dist = distance_transform_edt(ink)
    half_pen = np.median(dist[skeletonize(ink)])
    blobs = label(region & (dist > 2.2 * half_pen))
    return [(r.centroid, dist[r.slice][r.image].max()) for r in regionprops(blobs) if r.area >= f]


def dot_stroke(center_mm, radius_mm):
    """A tiny filled circle: a small loop with a pass through the middle."""
    t = np.linspace(0, 2 * np.pi, 9)
    loop = np.column_stack([np.cos(t), np.sin(t)]) * radius_mm + center_mm
    return np.vstack([center_mm, loop, center_mm])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--size", type=float, default=170, help="max drawing width/height, mm")
    ap.add_argument("--preview")
    a = ap.parse_args()
    settings = SimpleNamespace(up=itg.TOUCH_Z + 2.0, down=itg.TOUCH_Z - 0.4, draw_speed=5400,
                               travel_speed=12000, z_speed=1800, accel=10000, corner=20)

    ink, f = itg.load_ink(a.input, photo=True)
    rows, cols = np.indices(ink.shape)

    # Split the page into groups by connected piece of ink.
    pieces = label(ink)
    group_of_piece = {}
    for r in regionprops(pieces):
        cy, cx = (v / f for v in r.centroid)
        if cy > BOTTOM_CUT:
            group = None
        elif DIAGRAM[0] <= cx <= DIAGRAM[2] and DIAGRAM[1] <= cy <= DIAGRAM[3]:
            group = "diagram"
        elif BOX[0] <= cx <= BOX[2] and BOX[1] <= cy <= BOX[3]:
            group = "box"
        else:
            group = "text above box" if cy < BOX[1] else "text below box"
        group_of_piece[r.label] = group
    lookup = np.array([None] + [group_of_piece[i] for i in range(1, pieces.max() + 1)], dtype=object)
    piece_group = lookup[pieces]

    masks = {name: ink & (piece_group == name) for name in ("text above box", "text below box")}

    # Hold back "- Mathematical Model" and the title underline for near the end.
    # The underline is the long straight line under the title; fit it and take
    # the ink lying along it, so the descenders of "y" and "g" stay with "Hypergamy".
    title = masks["text above box"] & (rows < TITLE_BOTTOM * f)
    r_t, c_t = np.nonzero(skeletonize(title) & (rows > (TITLE_BOTTOM - 22) * f))
    line, _ = ransac(np.column_stack([c_t, r_t]).astype(float), LineModelND, min_samples=2,
                     residual_threshold=1.5 * f, max_trials=2000, rng=0)
    r_all, c_all = np.nonzero(title)
    on_line = line.residuals(np.column_stack([c_all, r_all]).astype(float)) < 3 * f
    # The hand-drawn underline bends a little, so refine the straight fit into
    # a gentle curve that follows it all the way along.
    for band in (5 * f, 3 * f):
        bend = np.polyfit(c_all[on_line], r_all[on_line], 2)
        on_line = np.abs(r_all - np.polyval(bend, c_all)) < band
    underline = np.zeros_like(ink)
    underline[r_all[on_line], c_all[on_line]] = True
    # Where a letter's tail hangs down through the underline, leave that ink
    # with the letter so the tail isn't cut in two.
    tails = np.zeros_like(ink)
    for shift in range(1, 5 * f):
        tails[shift:] |= title[:-shift] & ~underline[:-shift]
    underline &= ~(tails & (cols < TITLE_SPLIT * f))
    # The underline itself is drawn as one stroke along that curve.
    u_r, u_c = np.nonzero(underline)
    xx = np.linspace(u_c.min(), u_c.max(), 60)
    underline_stroke = np.column_stack([np.polyval(bend, xx), xx])
    masks["title end"] = title & (cols > TITLE_SPLIT * f) & ~underline
    masks["text above box"] &= ~(underline | masks["title end"])

    box = ink & (piece_group == "box")
    masks["box lines"] = box_border(box, f)
    masks["equations"] = box & ~masks["box lines"]

    diagram = ink & (piece_group == "diagram")
    (left, left_model), (right, right_model) = (fit_oval(diagram, f, b) for b in OVALS)
    masks["ovals"] = left | right
    rest = diagram & ~masks["ovals"]
    ax0, ay0, ax1, ay1 = (v * f for v in ARROW_ZONE)
    arrow_zone = (cols >= ax0) & (cols <= ax1) & (rows >= ay0) & (rows <= ay1)
    masks["arrows"] = rest & arrow_zone
    numbers = rest & ~arrow_zone
    # Where the hand-drawn ovals bulge away from a true ellipse, leftover scraps
    # of oval end up here; they touch the oval, whereas numbers and N labels don't.
    near_oval = distance_transform_edt(~masks["ovals"]) <= 2 * f
    scraps = label(numbers)
    for r in regionprops(scraps):
        piece = scraps == r.label
        if (piece & near_oval).any():
            masks["ovals"] |= piece
            numbers &= ~piece
    masks["numbers and dots"] = numbers
    # Filled blobs in the arrow area: dots where arrows start (left) and the
    # solid arrowheads where they end (right).
    blobs = find_dots(rest, f, rest & arrow_zone)
    middle = (OVALS[0][2] + OVALS[1][0]) / 2 * f
    dots = sorted((c, rad) for c, rad in blobs if c[1] < middle)
    heads = sorted(c for c, _ in blobs if c[1] >= middle)
    assert len(dots) == len(heads) == len(ARROW_ENDS), (len(dots), len(heads))

    # Same scaling as the plain converter: trim margins, fit the page size.
    r_ink, c_ink = np.nonzero(ink & (piece_group != None))  # noqa: E711
    r0, c0 = r_ink.min(), c_ink.min()
    scale = min(a.size / (c_ink.max() - c0), a.size / (r_ink.max() - r0))
    height_mm = (r_ink.max() - r0) * scale
    to_mm = lambda p: np.column_stack([(p[:, 1] - c0) * scale, height_mm - (p[:, 0] - r0) * scale])

    def strokes(mask):
        paths, marks = itg.trace_ink(mask)
        out = [to_mm(np.array(p, dtype=float)) for p in paths]
        out = [p for p in out if len(p) >= 2 and np.sum(np.hypot(*np.diff(p, axis=0).T)) > 0.4]
        return out + [to_mm(m) for m in marks]

    order = ["text above box", "equations", "text below box",
             "numbers and dots", "ovals", "arrows", "title end", "box lines"]
    drawn, pos = [], (0.0, 0.0)
    for name in order:
        if name == "ovals":
            group = []
            for (x0, y0, x1, y1), model in zip(OVALS, (left_model, right_model)):
                in_box = (cols >= x0 * f) & (cols <= x1 * f) & (rows >= y0 * f) & (rows <= y1 * f)
                group.append(to_mm(oval_loop(masks["ovals"] & in_box, model)))
        elif name == "arrows":
            # Already in drawing order: arrow 1 to 5, each sweep then its head.
            group = [itg.smooth(to_mm(p)) for p in arrow_paths(masks["arrows"], [c for c, _ in dots], heads, f)]
            drawn += [(name, p) for p in group]
            pos = tuple(group[-1][-1])
            print("%-17s %4d strokes" % (name, len(group)))
            continue
        else:
            group = strokes(masks[name])
        if name == "title end":
            group.append(to_mm(underline_stroke))
        if name == "numbers and dots":
            group += [dot_stroke(to_mm(np.array([c]))[0], max(0.15, 0.6 * rad * scale))
                      for c, rad in dots]
        group = itg.join_close(itg.order_paths(group, gap=0.35, start=pos), gap=0.35)
        group = [itg.smooth(p) for p in group]
        drawn += [(name, p) for p in group]
        pos = tuple(group[-1][-1])
        print("%-17s %4d strokes" % (name, len(group)))

    out = itg.gcode_lines([p for _, p in drawn], height_mm, settings)
    with open(a.output, "w") as fh:
        fh.write("\n".join(out))

    if a.preview:
        k = 6
        img = Image.new("RGB", (int(a.size * k) + 20, int(height_mm * k) + 20), "white")
        d = ImageDraw.Draw(img)
        to_px = lambda x, y: (10 + x * k, 10 + (height_mm - y) * k)
        for name, p in drawn:
            d.line([to_px(x, y) for x, y in p], fill=GROUP_COLOURS[name], width=2)
        img.save(a.preview)

    print("%d strokes, %d G-code lines, %.0f x %.0f mm" % (
        len(drawn), len(out), max(p[:, 0].max() for _, p in drawn), height_mm))


if __name__ == "__main__":
    main()
