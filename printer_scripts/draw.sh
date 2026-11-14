#!/bin/sh
# Start a pen drawing: pause the touchscreen, start the file, then speed it up.
# The pen must already be resting on the paper at the drawing's front-left corner.
#
# Usage:  ~/pen/draw.sh FILE.gcode [SPEED]
#   FILE.gcode  a file in ~/gcode_files (run with no arguments to list them)
#   SPEED       percent of the file's own speed, default 200 (double speed)

FILE="$1"
SPEED="${2:-200}"
API=http://localhost:7125

if [ -z "$FILE" ]; then
    echo "Usage: ~/pen/draw.sh FILE.gcode [SPEED]"
    echo "Drawings on the printer:"
    ls ~/gcode_files | grep '\.gcode$'
    exit 1
fi
if [ ! -f ~/gcode_files/"$FILE" ]; then
    echo "No such file: ~/gcode_files/$FILE"
    exit 1
fi

# The touchscreen program lifts the head when a print starts, so it must be off.
sudo systemctl stop makerbase-client || exit 1

curl -s -X POST "$API/printer/print/start?filename=$FILE" >/dev/null
sleep 1

if [ "$SPEED" -gt 100 ]; then
    # Faster corners and acceleration matter most for handwriting.
    LIMITS="SET_VELOCITY_LIMIT%20ACCEL=20000%20ACCEL_TO_DECEL=20000%20SQUARE_CORNER_VELOCITY=30"
    curl -s -X POST "$API/printer/gcode/script?script=$LIMITS%0AM220%20S$SPEED" >/dev/null
elif [ "$SPEED" -ne 100 ]; then
    curl -s -X POST "$API/printer/gcode/script?script=M220%20S$SPEED" >/dev/null
fi

echo "Drawing $FILE at $SPEED% speed."
echo "Check progress: ~/pen/status.sh    Stop instantly: ~/pen/stop.sh"
