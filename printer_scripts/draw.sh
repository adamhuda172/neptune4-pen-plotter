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
case "$SPEED" in
    ''|*[!0-9]*) SPEED=0 ;;
esac
if [ "$SPEED" -lt 1 ]; then
    echo "SPEED must be a whole number above 0, e.g. 150"
    exit 1
fi

# POST to Moonraker with URL-encoded arguments (so file names with spaces or
# symbols work). On failure, print Moonraker's answer and return non-zero.
post() {
    endpoint="$1"; shift
    resp=$(curl -s --max-time 10 -w '\n%{http_code}' -X POST -G "$@" "$API$endpoint") || {
        echo "Can't reach the printer's Moonraker service at $API."
        return 1
    }
    code=$(printf '%s\n' "$resp" | tail -n 1)
    if [ "$code" != 200 ]; then
        echo "The printer refused $endpoint (HTTP $code):"
        printf '%s\n' "$resp" | sed '$d'
        return 1
    fi
}

# The touchscreen program lifts the head when a print starts, so it must be off.
sudo systemctl stop makerbase-client || exit 1

if ! post /printer/print/start --data-urlencode "filename=$FILE"; then
    if sudo systemctl start makerbase-client; then
        echo "Drawing not started. The touchscreen is back on."
    else
        echo "Drawing not started, and the touchscreen didn't restart."
        echo "Run ~/pen/screen_on.sh, or switch the printer off and on."
    fi
    exit 1
fi
sleep 1

if [ "$SPEED" -gt 100 ]; then
    # Faster corners and acceleration matter most for handwriting.
    SCRIPT="SET_VELOCITY_LIMIT ACCEL=20000 ACCEL_TO_DECEL=20000 SQUARE_CORNER_VELOCITY=30
M220 S$SPEED"
else
    SCRIPT="M220 S$SPEED"
fi
if [ "$SPEED" -ne 100 ]; then
    post /printer/gcode/script --data-urlencode "script=$SCRIPT" ||
        echo "Warning: the drawing started but its speed could not be set."
fi

echo "Drawing $FILE at $SPEED% speed."
echo "Check progress: ~/pen/status.sh    Stop instantly: ~/pen/stop.sh"
