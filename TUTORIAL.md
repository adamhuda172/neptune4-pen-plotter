# Tutorial: make your Neptune 4 write out your own work

This assumes the hardware side is already done. The hotend and bed sensor
are off, a pen is mounted in their place with the print head cable still
plugged in, paper is taped to the bed and the printer is switched on. There
is a printable pen holder in [hardware](hardware/). Print it before you take
the printer apart.

You need a Mac or a Windows computer and a USB-C cable. The first time setup
takes about 20 minutes, and after that each new page takes about 5.


## Part A: setup (only once)

### Step 1. Get the code

On the GitHub page click Code, then Download ZIP, and unzip it. Or if you
use git:
```
git clone https://github.com/adamhuda172/neptune4-pen-plotter.git
```
Open a terminal inside the `neptune4-pen-plotter` folder. On Windows you can
click the folder's address bar, type `powershell` and press Enter.

### Step 2. Install the Python tools

On a Mac:
```
sh mac/setup.sh
```
On Windows, install Python from python.org (tick "Add to PATH") and then run:
```
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```
This makes a private Python setup in a folder called `.venv` with the
libraries listed in [requirements.txt](requirements.txt). From here on,
wherever this tutorial says `PY`, type `.venv/bin/python` on a Mac or
`.venv\Scripts\python.exe` on Windows.

### Step 3. Log in to the printer

The front USB-C port on the printer gives you a text console for the small
computer inside it. Plug a USB-C cable from that port into your computer.

On a Mac run `sh mac/connect.sh` ([mac/connect.sh](mac/connect.sh) finds the
port and opens it) and press Enter.

On Windows install PuTTY. Find the port in Device Manager under Ports, where
it shows up as "USB-SERIAL CH340 (COMx)". In PuTTY pick Serial, type that
COMx in Serial line, set Speed to `1500000`, click Open and press Enter.

Log in with the username `mks` and the password `makerbase`. The password
doesn't show while you type. Once you see `mks@mkspi:~$`, close the console
(on a Mac press Ctrl+A, then K, then Y, and on Windows just close PuTTY). You
stay logged in and the port is free for the tools to use.

### Step 4. Install pen mode and the printer commands

```
PY tools/printer_link.py install
```
[tools/printer_link.py](tools/printer_link.py) finds the printer's USB port,
copies the commands in [printer_scripts](printer_scripts/) to `~/pen/` on
the printer, copies [printer_config/pen_plotter.cfg](printer_config/pen_plotter.cfg)
across, and runs [pen_mode_on.sh](printer_scripts/pen_mode_on.sh), which
backs up `printer.cfg` and switches pen mode on.

Pen mode changes two things. Home no longer moves anything, because real
homing lowers the head onto the bed and would crash the pen, so it just
resets the position counters instead. It also widens the movement limits so
the buttons never get blocked. That means the only real limit left is the
end of each axis, so if a motor ever grinds or buzzes, stop pressing that
direction.

At the end it should say `Pen mode is on.` and list the commands.


## Part B: every time you write a page

### Step 5. Get a good picture of your work

Scan it, or take a photo from straight above in even light. Dark ink on
white paper works best, and pencil is fine as long as it's dark.
Handwriting, diagrams and line drawings come out well. Shaded drawings and
photos of people only come out as rough outlines, because a pen can only
draw lines. Save the picture in the `neptune4-pen-plotter` folder, for
example as `mywork.jpg`.

### Step 6. Turn it into G-code

For a scan or a clean image:
```
PY image_to_gcode.py mywork.jpg mywork.gcode --width 170 --height 170 --preview mywork_preview.png
```
For a photo of a page (this crops out the table around it and fixes
shadows):
```
PY image_to_gcode.py mywork.jpg mywork.gcode --photo --width 170 --height 170 --preview mywork_preview.png
```

What [image_to_gcode.py](image_to_gcode.py) does, in order: it finds the ink
(`load_ink`), traces each line down its middle so it gets drawn once
(`trace_ink` and `trace_skeleton`), smooths the strokes so they look hand
drawn (`smooth`), puts them in an order that keeps pen travel short
(`order_paths` and `join_close`), and writes the moves out as G-code
(`gcode_lines`). When it finishes it prints the size, something like
`1100 strokes, ... 170 x 168 mm`.

Open `mywork_preview.png` and check it. If something looks wrong, change the
command and run it again:

| Problem in the preview | What to change |
|---|---|
| Too big or too small for your paper | `--width` and `--height` (in mm) |
| Faint lines are missing | Add `--threshold 232` (try between 220 and 240) |
| Specks or shadows from the background | Add `--photo`, or crop the picture tighter |
| You want one area drawn last | `--last x0,y0,x1,y1` as fractions of the picture, e.g. `0.6,0.1,1,0.4` |

To check a detail up close (the numbers are mm from the bottom left corner):
```
PY tools/preview_gcode.py mywork.gcode closeup.png 0 60 0 40
```

If you're curious what's in a G-code file, open it in any text editor. It
starts like this:
```
SET_KINEMATIC_POSITION X=0 Y=0 Z=5   ; wherever the pen is now is the bottom left corner, touching the paper
G1 Z7.00 F1800                       ; pen up 2 mm
G0 X2.61 Y5.46 F12000                ; travel to the start of a stroke
G1 Z4.60 F1800                       ; pen down (0.4 mm into the paper)
G1 X2.70 Y5.80 F5400                 ; draw
```
X is left and right, Y is up and down the page (the bed moves for that), Z
is the pen height, and F is the speed in mm per minute. Nothing gets heated
and nothing gets extruded.

### Step 7. Send it to the printer

```
PY tools/printer_link.py send mywork.gcode
```
It should say `Sent mywork.gcode -> /home/mks/gcode_files/mywork.gcode (... bytes, checked)`.
You can also copy the file onto a USB stick and plug that into the printer
instead, in which case you call it `sda1/mywork.gcode` in step 9.

### Step 8. Put the pen on the starting corner

On the touchscreen go to Prepare. Raise Z first so the pen is clear of the
paper. Move X and Y until the pen is over the front left corner of where the
page should go, leaving enough room to the right and towards the back for
the size from step 6. Then lower Z, first in big steps and then in 0.1 mm
steps, until the tip just touches the paper. Don't press it in, the drawing
does that itself.

If a direction stops moving, tap Home. In pen mode nothing moves, it only
resets the counters.

### Step 9. Start drawing

Open the console again like in step 3 and type:
```
~/pen/draw.sh mywork.gcode
```
Type the password `makerbase` if it asks. [draw.sh](printer_scripts/draw.sh)
turns the touchscreen off (otherwise it lifts the pen when a drawing
starts), starts the drawing and runs it at double speed. For a different
speed add a percentage on the end, for example `~/pen/draw.sh mywork.gcode 100`
for normal speed, which is the neatest, or `300` for the fastest, which can
get a bit wobbly.

Never start a drawing with the Print button on the touchscreen. It moves the
head before the drawing starts and the pen ends up drawing in the air.

### Step 10. Watch it, check it, stop it

`~/pen/status.sh` shows how far through it is, the speed, and whether the
touchscreen is on. `~/pen/stop.sh` stops it straight away, restarts the
printer and turns the touchscreen back on. [stop.sh](printer_scripts/stop.sh)
is also what you run after a drawing finishes to get the touchscreen back.

If you need an emergency stop, switch the printer off. Pen mode is still on
when you switch it back on.

### Another copy or another page

Run `~/pen/stop.sh`, put in a fresh sheet and repeat steps 8 to 10, or steps
5 to 10 for a new page.


## Part C: going back to normal 3D printing

1. In the console run `~/pen/pen_mode_off.sh`. [pen_mode_off.sh](printer_scripts/pen_mode_off.sh)
   removes the one pen mode line from `printer.cfg`.
2. Put the hotend and bed sensor back on (sensor pointing straight down, at
   the same height as before) and plug them in.
3. Restart the printer, run Level on the touchscreen, and check the first
   layer of a small test print.

To go back to pen mode later, run `~/pen/pen_mode_on.sh`.


## Quick fixes

| Problem | Fix |
|---|---|
| The screen says "ADC out of range" | The print head cable is unplugged. Plug it back in (the hotend can hang loose) |
| "Endstop z still triggered after retract" | Something tried to really home. Run `~/pen/pen_mode_on.sh` |
| The pen draws in the air | The drawing was started from the touchscreen. Use `~/pen/draw.sh` |
| `printer_link.py` can't open the port | Close PuTTY or the Mac console first |
| `printer_link.py` gets no answer from the printer | You've been logged out. Do step 3 again |
| Lines are faint | Make the file again with `--down 4.4` so it presses harder |
| The pen digs in or tears the paper | Make the file again with `--down 4.8` so it presses lighter |
| Wobbly letters | `~/pen/draw.sh mywork.gcode 100` |
| No printer port on a Mac | Install the CH340 USB serial driver |
