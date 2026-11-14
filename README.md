# Neptune 4 Pen Plotter

Turn an **Elegoo Neptune 4** 3D printer into a pen plotter: strap a pen to the
print head and have it draw pictures, handwriting and diagrams on paper.

* `image_to_gcode.py` turns a picture into pen G-code. It traces every line
  down its centre so it is drawn once, smooths the strokes so they look
  hand-drawn, and orders them to keep pen travel short.
* **Pen mode** for the printer skips homing (which would crash the pen into the
  bed) and widens the movement limits, all in one file that switches on and off.
* Short commands on the printer start, stop, speed up and monitor drawings.
* `printer_link.py` copies drawings to the printer over the front USB-C cable
  on **macOS, Windows or Linux**.

**New here? Follow the step-by-step [TUTORIAL.md](TUTORIAL.md).**
For a ready-made drawing and an example of a custom drawing order, see
[examples/hypergamy](examples/hypergamy/).

Tested on a stock Neptune 4 (firmware V1.1.3.1, UI 1.2.14) from Windows.
The macOS steps use the same tools but haven't been tested on a Mac yet, so
please open an issue if something doesn't work.

---

## How it works

```
 picture ──image_to_gcode.py──▶ drawing.gcode ──printer_link.py send──▶ printer
                                                       (or a USB stick)
 then, on the printer:  ~/pen/draw.sh drawing.gcode  ──▶ pen draws
```

A G-code file is a plain-text list of moves:

```
SET_KINEMATIC_POSITION X=0 Y=0 Z=5   ; wherever the pen is now = bottom-left corner, touching
G1 Z7.00 F1800                       ; pen up
G0 X2.61 Y5.46 F12000                ; travel to the start of a stroke
G1 Z4.60 F1800                       ; pen down (0.4 mm into the paper)
G1 X2.70 Y5.80 F5400                 ; draw ...
```

There's no heating and no extrusion, only movement. Because the file starts
with `SET_KINEMATIC_POSITION`, **wherever the pen is resting when the drawing
starts becomes its bottom-left corner**.

---

## 1. Hardware

* Remove the hotend/extruder and the bed-levelling sensor from the print head,
  and mount a pen holder in their place. A **spring-loaded** holder gives the
  most even lines. Search Printables/Thingiverse for "Neptune 4 pen holder".
* **Keep the print-head cable plugged in.** The printer shuts down with
  "ADC out of range" if the nozzle temperature sensor is disconnected. The
  hotend can hang loose. It is never heated.
* Fineliners and gel pens work best. Use a mechanical pencil if you want pencil.
* Tape the paper flat on the bed.

## 2. Software setup (once)

**macOS:**
```
cd neptune4-pen-plotter
sh mac/setup.sh
```

**Windows (PowerShell):**
```
cd neptune4-pen-plotter
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

Below, `PY` means `.venv/bin/python` on macOS/Linux or
`.venv\Scripts\python.exe` on Windows.

## 3. Printer setup (once)

The printer's front **USB-C port** is a text console to its built-in Linux
computer.

1. Plug a USB-C cable from the printer's front port into your computer and
   switch the printer on.
2. Open the console and log in. The default login is user `mks`, password
   `makerbase`.
   * **macOS:** `sh mac/connect.sh`, then leave with Ctrl+A, K, Y.
   * **Windows:** PuTTY → Connection type **Serial**, Serial line `COMx`
     (find it in Device Manager → Ports, "USB-SERIAL CH340"), Speed `1500000`.
3. **Close the console program**, so the port is free. You stay logged in.
4. Install the commands and pen mode:
   ```
   PY tools/printer_link.py install
   ```
   This copies `printer_scripts/*.sh` to `~/pen/` and `pen_plotter.cfg` to
   `~/klipper_config/`, backs up `printer.cfg`, and switches pen mode on.

## 4. Making a drawing

```
PY image_to_gcode.py picture.png picture.gcode --preview picture_preview.png
```

Check `picture_preview.png`, then send the drawing:

```
PY tools/printer_link.py send picture.gcode
```

Or copy it onto a USB stick and plug that into the printer. It appears as
`sda1/picture.gcode`.

Useful options:

| Option | Effect |
|---|---|
| `--photo` | Input is a photo of paper: crops the background and evens out lighting |
| `--width 170 --height 170` | Maximum size in mm (default 180 × 135) |
| `--threshold 232` | Pick up fainter ink (0–255) |
| `--down 4.4` / `--down 4.8` | Pen presses harder / lighter (touching = 5) |
| `--draw-speed 5400 --travel-speed 12000 --z-speed 1800` | Speeds in mm/min |
| `--accel 10000 --corner 20` | Acceleration and cornering speed |
| `--last x0,y0,x1,y1` | Draw this area last (fractions of the picture, e.g. `0.6,0.1,1,0.4`) |

Line art, handwriting and diagrams work best. Photos of faces come out as
rough outlines, because a pen can only draw lines.

Check a detail up close before drawing (mm from the bottom-left corner):
```
PY tools/preview_gcode.py picture.gcode closeup.png 0 60 0 40
```

## 5. Drawing it

1. **Touchscreen → Prepare:** raise Z, move X/Y so the pen is over the
   **front-left corner** of the drawing area, then lower Z until the tip
   **just touches** the paper. If a direction stops moving, tap **Home**.
   In pen mode nothing moves; it only resets the counters.
2. In the printer console:
   ```
   ~/pen/draw.sh picture.gcode
   ```
   Enter the password if asked. This turns the touchscreen off, starts the
   drawing and runs it at double speed.
3. When it's finished, or to stop it instantly:
   ```
   ~/pen/stop.sh
   ```

**Don't start drawings from the touchscreen's Print button.** The touchscreen
program lifts the head when a print starts, so the pen would draw in mid-air.
That's why `draw.sh` turns the touchscreen off first.

### Printer commands

| Command | What it does |
|---|---|
| `~/pen/draw.sh` | List drawings on the printer |
| `~/pen/draw.sh FILE.gcode [SPEED]` | Draw FILE; SPEED is percent of the file's speed (default 200) |
| `~/pen/status.sh` | State, progress, speed, touchscreen on/off |
| `~/pen/stop.sh` | Instant stop, restart, touchscreen back on |
| `~/pen/screen_off.sh` / `screen_on.sh` | Touchscreen program off / on |
| `~/pen/pen_mode_on.sh` / `pen_mode_off.sh` | Switch pen mode on / off |

You can also run any of these from your computer without opening the console:
```
PY tools/printer_link.py run "~/pen/status.sh"
```
Commands that need the password (draw, stop, screen) only work this way if
you typed the password in the console within the last ~15 minutes
(`sudo -v`).

**Emergency stop without a computer:** switch the printer off. When it's
switched back on, the touchscreen returns and pen mode stays on.

## 6. Back to 3D printing

1. Refit the hotend and bed-levelling sensor (sensor pointing straight down,
   same height as before) and plug everything in.
2. `~/pen/pen_mode_off.sh`
3. Restart the printer, run **Level**, and check the first layer of a test print.

## Safety

* **Pen mode disables homing and the normal movement limits.** The only limit
  left is the physical end of each axis. If a motor grinds or buzzes, stop
  moving in that direction.
* Never heat the nozzle with a pen holder fitted.
* Keep hands clear while drawing. Drawings run fast.

## Troubleshooting

| Problem | Fix |
|---|---|
| "ADC out of range" | The nozzle temperature sensor is unplugged. Reconnect the print-head cable. |
| "Endstop z still triggered after retract" | Something tried to really home. Run `~/pen/pen_mode_on.sh`. |
| Pen draws in the air at the start | The touchscreen was on. Use `~/pen/draw.sh`, not the Print button. |
| A direction button stops working | Tap **Home** on Prepare (nothing moves). |
| `printer_link.py`: "Can't open" the port | Close PuTTY/screen and try again. |
| `printer_link.py`: "No answer from the printer" | Nobody is logged in. Log in once in the console, then close it. |
| No port on macOS | Install the CH340 USB-serial driver. |
| Lines faint / pen digging in | Remake with `--down 4.4` (harder) or `--down 4.8` (lighter). |
| Wobbly lines | Draw slower: `~/pen/draw.sh FILE.gcode 100` |
