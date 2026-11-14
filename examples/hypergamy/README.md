# Example: a page of handwritten maths notes

![preview](hypergamy_v2_preview.png)

This is a full page of handwritten notes with text, a box of equations and a
mapping diagram, drawn at about 170 by 170 mm. The colours in the preview
show the order it gets drawn in.

## Drawing it as it is

[hypergamy_v2.gcode](hypergamy_v2.gcode) is ready to draw. Send it with
```
PY tools/printer_link.py send examples/hypergamy/hypergamy_v2.gcode
```
then on the printer, with the pen touching the paper at the front left
corner, run
```
~/pen/draw.sh hypergamy_v2.gcode
```
Leave about 170 mm of room to the right and towards the back.

## How the custom drawing order works

The normal converter ([image_to_gcode.py](../../image_to_gcode.py)) draws
things in whatever order keeps the pen travel shortest.
[hypergamy_job.py](hypergamy_job.py) shows how to set the order yourself for
one particular page. It splits the picture into regions, using the photo's
own pixel coordinates which are set at the top of the file, and draws them
in this order:

1. the text above the box of equations
2. the four equations, all in one go
3. the text below the box
4. the mapping diagram, starting with the numbers and dots, then each oval
   as one continuous loop (`oval_loop`), then each arrow as one smooth sweep
   followed by its head (`arrow_paths`)
5. the end of the title and the line under it, as one stroke
6. the box around the equations, last of all

It reuses the converter's building blocks (`load_ink`, `trace_ink`,
`order_paths`, `join_close`, `smooth` and `gcode_lines`), so it's a good place
to start if you want your own page drawn in a set order. Copy it, then change
the region coordinates and the `order` list.

The original photo isn't included. To run the script on your own photo of a
similar page:
```
PY examples/hypergamy/hypergamy_job.py photo.webp out.gcode --preview out_preview.png
```
