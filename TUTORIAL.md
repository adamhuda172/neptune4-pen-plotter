# Tutorial: make your Neptune 4 write out your own work

This assumes the hardware is done: the hotend and bed sensor are off, a pen
is mounted in their place (print-head cable still plugged in), the paper is
taped to the bed, and the printer is switched on.

You need a Mac or Windows computer, a USB-C cable and about 20 minutes for
the first-time setup. After that, each new page takes about 5 minutes.

---

## Part A — one-time setup

### Step 1. Get the code
On the GitHub page click **Code → Download ZIP** and unzip it, or run:
```
git clone <repo URL>
```
Open a terminal **inside the `neptune4-pen-plotter` folder**. On Windows,
click the folder's address bar, type `powershell` and press Enter.

### Step 2. Install the Python tools
**Mac:**
```
sh mac/setup.sh
```
**Windows:** install Python from python.org (tick "Add to PATH"), then:
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```
This makes a private Python environment in `.venv` with the libraries in
[`requirements.txt`](requirements.txt). From now on, **`PY`** in this
tutorial means:
* Mac: `.venv/bin/python`
* Windows: `.venv\Scripts\python.exe`

### Step 3. Log in to the printer
The printer's front **USB-C port** gives you a text console on its built-in
computer. Plug a USB-C cable from that port into your computer.

* **Mac:** `sh mac/connect.sh` ([`mac/connect.sh`](mac/connect.sh) finds the
  port and opens it). Press Enter.
* **Windows:** install **PuTTY**. Find the port in Device Manager → *Ports* →
  "USB-SERIAL CH340 (COMx)". In PuTTY choose **Serial**, Serial line `COMx`,
  Speed `1500000`, then **Open** and press Enter.

Log in with username `mks` and password `makerbase` (the password stays
invisible as you type). When you see `mks@mkspi:~$`, **close the console**:
on Mac press Ctrl+A, K, Y; on Windows close the PuTTY window. You stay logged
in, and the port is now free for the tools.

### Step 4. Install pen mode and the printer commands
```
PY tools/printer_link.py install
```
[`tools/printer_link.py`](tools/printer_link.py) finds the printer's USB port
and then:
* copies the commands in [`printer_scripts/`](printer_scripts/) to `~/pen/`
  on the printer
* copies [`printer_config/pen_plotter.cfg`](printer_config/pen_plotter.cfg)
  to the printer
* runs [`pen_mode_on.sh`](printer_scripts/pen_mode_on.sh), which backs up
  `printer.cfg` and switches **pen mode** on

Pen mode does two things:
1. **"Home" no longer moves anything.** Real homing lowers the head onto the
   bed and would crash the pen, so homing just resets the position counters.
2. **Movement limits are widened**, so the buttons never get blocked.
   ⚠️ The only real limit now is the end of each axis. **If a motor grinds or
   buzzes, stop pressing that direction.**

The output should end with `Pen mode is on.` and a list of the commands.

---

## Part B — every time you write a page

### Step 5. Get a good picture of your work
* **Scan it**, or take a photo straight on in even light.
* Dark ink on white paper works best. Pencil works if it's dark.
* Handwriting, diagrams and line drawings work well. Shaded drawings and
  photos of people come out as rough outlines, because a pen can only draw
  lines.
* Save it in the `neptune4-pen-plotter` folder, e.g. `mywork.jpg`.

### Step 6. Turn it into G-code
**A scan or clean image:**
```
PY image_to_gcode.py mywork.jpg mywork.gcode --width 170 --height 170 --preview mywork_preview.png
```
**A photo of a page** (crops the table around it and fixes shadows):
```
PY image_to_gcode.py mywork.jpg mywork.gcode --photo --width 170 --height 170 --preview mywork_preview.png
```

[`image_to_gcode.py`](image_to_gcode.py) does this:
1. finds the ink (`load_ink`)
2. traces each line down its middle so it's drawn once (`trace_ink`, `trace_skeleton`)
3. smooths the strokes so they look hand-drawn (`smooth`)
4. orders them so the pen travels as little as possible (`order_paths`, `join_close`)
5. writes the moves as G-code (`gcode_lines`)

It prints the size, e.g. `1100 strokes, ... 170 x 168 mm`.

**Open `mywork_preview.png` and check it.** If something's wrong, adjust and
run it again:

| Problem in the preview | Add / change |
|---|---|
| Too big or small for your paper | `--width` and `--height` (mm) |
| Faint lines missing | `--threshold 232` (try 220–240) |
| Background specks or shadows | add `--photo`, or crop the picture tighter |
| One area should be drawn last | `--last x0,y0,x1,y1` (fractions of the picture, e.g. `0.6,0.1,1,0.4`) |

To check a detail up close (numbers are mm from the bottom-left corner):
```
PY tools/preview_gcode.py mywork.gcode closeup.png 0 60 0 40
```

<details><summary>What's inside a G-code file?</summary>

Open it in any text editor:
```
SET_KINEMATIC_POSITION X=0 Y=0 Z=5   ; wherever the pen is now = bottom-left corner, touching paper
G1 Z7.00 F1800                       ; pen up 2 mm
G0 X2.61 Y5.46 F12000                ; travel to the start of a stroke
G1 Z4.60 F1800                       ; pen down (0.4 mm into the paper)
G1 X2.70 Y5.80 F5400                 ; draw ...
```
X is left/right, Y is up/down the page (the bed moves) and Z is pen height.
F is speed in mm/minute. There's no heating and no extrusion, only movement.
</details>

### Step 7. Send it to the printer
```
PY tools/printer_link.py send mywork.gcode
```
It should say `Sent mywork.gcode -> /home/mks/gcode_files/mywork.gcode (... bytes, checked)`.
(Or copy the file onto a USB stick, plug it into the printer, and call it
`sda1/mywork.gcode` in step 9.)

### Step 8. Put the pen on the starting corner
Use the printer's **touchscreen → Prepare**:
1. **Raise Z** first, so the pen is clear of the paper.
2. Move **X/Y** until the pen is over the **front-left corner** of where the
   page should go. Leave room to the right and toward the back for the size
   printed in step 6.
3. Lower **Z** with the big steps, then the **0.1 mm** step, until the tip
   **just touches** the paper. Don't press it in; the drawing does that itself.

If a direction stops moving, tap **Home**. In pen mode nothing moves; it only
resets the counters.

### Step 9. Start drawing
Open the console again (step 3), then type:
```
~/pen/draw.sh mywork.gcode
```
Type the password `makerbase` if asked.
[`draw.sh`](printer_scripts/draw.sh) turns the **touchscreen off** (otherwise
it lifts the pen when a drawing starts), starts the drawing, and runs it at
**double speed**. For other speeds, add a percentage:
```
~/pen/draw.sh mywork.gcode 100     (normal speed: neatest)
~/pen/draw.sh mywork.gcode 300     (fastest: may wobble)
```

⚠️ **Never start a drawing with the touchscreen's Print button.** It moves the
head before the drawing starts, and the pen ends up drawing in mid-air.

### Step 10. Watch, check, stop
```
~/pen/status.sh      progress %, speed, touchscreen on/off
~/pen/stop.sh        stop instantly, restart, touchscreen back on
```
[`stop.sh`](printer_scripts/stop.sh) is also what you run **after a drawing
finishes** to get the touchscreen back. **Emergency stop: switch the printer
off.** Pen mode stays on when you switch it back on.

### Another copy or another page?
Run `~/pen/stop.sh`, put in fresh paper, and repeat steps 8–10 (or 5–10 for
a new page).

---

## Part C — going back to normal 3D printing

1. In the console: `~/pen/pen_mode_off.sh`
   ([`pen_mode_off.sh`](printer_scripts/pen_mode_off.sh) removes the one
   pen-mode line from `printer.cfg`).
2. Refit the hotend and bed sensor (sensor pointing straight down, at the same
   height as before) and plug them in.
3. Restart the printer, run **Level** on the touchscreen, and check the first
   layer of a small test print.

To go back to pen mode later: `~/pen/pen_mode_on.sh`.

---

## Quick fixes

| Problem | Fix |
|---|---|
| Screen says "ADC out of range" | The print-head cable is unplugged. Plug it back in (the hotend can hang loose). |
| "Endstop z still triggered after retract" | Something tried to really home. Run `~/pen/pen_mode_on.sh`. |
| Pen draws in the air | The drawing was started from the touchscreen. Use `~/pen/draw.sh`. |
| `printer_link.py` can't open the port | Close PuTTY / the Mac console first. |
| `printer_link.py`: "No answer from the printer" | You're logged out. Do step 3 again. |
| Lines faint | Remake with `--down 4.4` (presses harder). |
| Pen digs in or tears the paper | Remake with `--down 4.8` (presses lighter). |
| Wobbly letters | `~/pen/draw.sh mywork.gcode 100` |
| No printer port on a Mac | Install the CH340 USB-serial driver. |
