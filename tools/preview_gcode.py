"""Render the pen-down moves of part of a G-code file at high zoom, to check
it before drawing. Coordinates are in mm from the drawing's bottom-left corner.

Usage: python tools/preview_gcode.py drawing.gcode out.png X0 X1 Y0 Y1
"""
import re
import sys

from PIL import Image, ImageDraw

k = 20
path, out, x0, x1, y0, y1 = sys.argv[1], sys.argv[2], *map(float, sys.argv[3:7])
segs, pos, down = [], None, False
for line in open(path):
    m = re.match(r"G[01] (?:X([\d.]+) Y([\d.]+))?(?: ?Z([\d.]+))?", line)
    if not m:
        continue
    if m.group(3):
        down = float(m.group(3)) < 5
        continue
    p = (float(m.group(1)), float(m.group(2)))
    if down and pos:
        segs.append((pos, p))
    pos = p
img = Image.new("RGB", (int((x1 - x0) * k), int((y1 - y0) * k)), "white")
d = ImageDraw.Draw(img)
for a, b in segs:
    d.line([((a[0] - x0) * k, (y1 - a[1]) * k), ((b[0] - x0) * k, (y1 - b[1]) * k)], fill=(20, 30, 120), width=3)
img.save(out)
