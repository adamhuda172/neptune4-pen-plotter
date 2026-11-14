# Neptune 4 Pen Plotter

This turns an Elegoo Neptune 4 3D printer into a pen plotter. You fix a pen to
the print head and it draws pictures, handwriting and diagrams on paper.

There are four parts to it. `image_to_gcode.py` turns a picture into G-code
for the pen. It traces each line down its centre so it gets drawn once,
smooths the strokes so they look hand drawn, and puts them in an order that
keeps pen travel short. Pen mode is a small settings file for the printer
that skips homing (which would crash the pen into the bed) and widens the
movement limits. A few short commands on the printer start, stop, speed up
and monitor drawings. Finally `printer_link.py` copies drawings to the
printer over the front USB-C cable from a Mac, Windows or Linux computer.

If you are new to this, follow [TUTORIAL.md](TUTORIAL.md) step by step. The
pen holder I designed is in [hardware](hardware/), and a ready made drawing
with an example of a custom drawing order is in
[examples/hypergamy](examples/hypergamy/).

I tested this on a stock Neptune 4 (firmware V1.1.3.1, UI 1.2.14) from
Windows. The Mac steps use the same tools but I haven't tried them on a Mac
yet, so please open an issue if something doesn't work.


## How it works

```
picture  >  image_to_gcode.py  >  drawing.gcode  >  printer_link.py send (or a USB stick)  >  printer
then on the printer:  ~/pen/draw.sh drawing.gcode
```

A G-code file is a plain text list of moves:

```
SET_KINEMATIC_POSITION X=0 Y=0 Z=5   ; wherever the pen is now is the bottom left corner, touching the paper
G1 Z7.00 F1800                       ; pen up
G0 X2.61 Y5.46 F12000                ; travel to the start of a stroke
G1 Z4.60 F1800                       ; pen down (0.4 mm into the paper)
G1 X2.70 Y5.80 F5400                 ; draw
```

Nothing gets heated and nothing gets extruded, it is all just movement.
Because every file starts with `SET_KINEMATIC_POSITION`, wherever the pen is
resting when a drawing starts becomes the bottom left corner of the drawing.


## 1. Hardware

Print the pen holder in [hardware](hardware/) before you take the printer
apart. Then take the hotend, extruder and bed levelling sensor off the print
head and mount the holder in their place.

Keep the print head cable plugged in. If the nozzle temperature sensor is
disconnected the printer shuts down with "ADC out of range". The hotend can
just hang loose, it never gets heated.

Fineliners and gel pens give the cleanest lines. Tape the paper flat on the
bed.


## 2. Software setup (once)

On a Mac:
```
cd neptune4-pen-plotter
sh mac/setup.sh
```

On Windows, in PowerShell:
```
cd neptune4-pen-plotter
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

In the rest of this page `PY` means `.venv/bin/python` on a Mac or Linux and
`.venv\Scripts\python.exe` on Windows.


## 3. Printer setup (once)

The front USB-C port on the printer is a text console for the small Linux
computer inside it.

1. Plug a USB-C cable from that port into your computer and switch the
   printer on.
2. Open the console and log in. The default login is user `mks` with
   password `makerbase`. On a Mac run `sh mac/connect.sh` (leave it with
   Ctrl+A, K, Y). On Windows use PuTTY with connection type Serial, the COM
   port shown in Device Manager under Ports as "USB-SERIAL CH340", and speed
   `1500000`.
3. Close the console program so the port is free. You stay logged in.
4. Install the commands and pen mode:
   ```
   PY tools/printer_link.py install
   ```
   This copies `printer_scripts/*.sh` to `~/pen/` and `pen_plotter.cfg` to
   `~/klipper_config/` on the printer, backs up `printer.cfg`, and switches
   pen mode on.


## 4. Making a drawing

```
PY image_to_gcode.py picture.png picture.gcode --preview picture_preview.png
```

Look at `picture_preview.png`, then send the drawing:

```
PY tools/printer_link.py send picture.gcode
```

You can also copy it onto a USB stick and plug that into the printer, in
which case the file is called `sda1/picture.gcode` on the printer.

Useful options:

| Option | What it does |
|---|---|
| `--photo` | The input is a photo of a page. Crops the background and evens out the lighting |
| `--width 170 --height 170` | Largest size in mm (default 180 by 135) |
| `--threshold 232` | Picks up fainter ink (0 to 255) |
| `--down 4.4` or `--down 4.8` | Pen presses harder or lighter (touching is 5) |
| `--draw-speed 5400 --travel-speed 12000 --z-speed 1800` | Speeds in mm per minute |
| `--accel 10000 --corner 20` | Acceleration and cornering speed |
| `--last x0,y0,x1,y1` | Draws this area last (fractions of the picture, e.g. `0.6,0.1,1,0.4`) |

Line art, handwriting and diagrams work best. Photos of faces only come out
as rough outlines because a pen can only draw lines.

To look at part of a drawing up close before you draw it (numbers are mm from
the bottom left corner):
```
PY tools/preview_gcode.py picture.gcode closeup.png 0 60 0 40
```


## 5. Drawing it

1. On the touchscreen go to Prepare. Raise Z, move X and Y until the pen is
   over the front left corner of where the drawing should go, then lower Z
   until the tip just touches the paper. If a direction stops moving, tap
   Home. In pen mode that doesn't move anything, it only resets the counters.
2. In the printer console type
   ```
   ~/pen/draw.sh picture.gcode
   ```
   and the password if it asks. This turns the touchscreen off, starts the
   drawing and runs it at double speed.
3. When it has finished, or if you want to stop it straight away, type
   ```
   ~/pen/stop.sh
   ```

Don't start drawings from the Print button on the touchscreen. The
touchscreen program lifts the head when a print starts, so the pen ends up
drawing in the air. That is why `draw.sh` turns the touchscreen off first.

The printer commands:

| Command | What it does |
|---|---|
| `~/pen/draw.sh` | Lists the drawings on the printer |
| `~/pen/draw.sh FILE.gcode SPEED` | Draws FILE. SPEED is a percentage of the file's own speed and is optional (default 200) |
| `~/pen/status.sh` | Shows the state, progress, speed and whether the touchscreen is on |
| `~/pen/stop.sh` | Stops straight away, restarts and turns the touchscreen back on |
| `~/pen/screen_off.sh` and `screen_on.sh` | Turn the touchscreen program off or on |
| `~/pen/pen_mode_on.sh` and `pen_mode_off.sh` | Switch pen mode on or off |

You can also run these from your computer without opening the console, for
example `PY tools/printer_link.py run "~/pen/status.sh"`. The ones that need
the password (draw, stop and the screen ones) only work like this if you
typed the password in the console in the last 15 minutes or so (`sudo -v`).

If you need to stop it and don't have a computer to hand, switch the printer
off. When it comes back on the touchscreen works again and pen mode is still
on.


## 6. Going back to 3D printing

1. Put the hotend and bed levelling sensor back on (sensor pointing straight
   down at the same height as before) and plug everything in.
2. Run `~/pen/pen_mode_off.sh`.
3. Restart the printer, run Level, and check the first layer of a small test
   print.


## Safety

Pen mode turns off homing and the normal movement limits, so the only limit
left is the physical end of each axis. If a motor grinds or buzzes, stop
moving that way. Never heat the nozzle with the pen holder fitted, and keep
your hands clear while it draws because it moves fast.


## Troubleshooting

| Problem | Fix |
|---|---|
| "ADC out of range" | The nozzle temperature sensor is unplugged. Plug the print head cable back in |
| "Endstop z still triggered after retract" | Something tried to really home. Run `~/pen/pen_mode_on.sh` |
| The pen draws in the air at the start | The touchscreen was on. Use `~/pen/draw.sh`, not the Print button |
| A direction button stops working | Tap Home on Prepare (nothing moves) |
| `printer_link.py` can't open the port | Close PuTTY or screen and try again |
| `printer_link.py` gets no answer from the printer | Nobody is logged in. Log in once in the console, then close it |
| No port shows up on a Mac | Install the CH340 USB serial driver |
| Lines are faint or the pen digs in | Make the file again with `--down 4.4` (harder) or `--down 4.8` (lighter) |
| Wobbly lines | Draw slower with `~/pen/draw.sh FILE.gcode 100` |
