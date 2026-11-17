#!/bin/sh
# Stop the pen instantly, restart the printer and bring the touchscreen back.
# Also use this after a drawing finishes, to get the touchscreen back.
API=http://localhost:7125

cant_stop() {
    echo "COULD NOT STOP: $1"
    echo "Switch the printer off at the power switch."
    exit 1
}

# --max-time on every request so a hung Moonraker can't stall the script.
resp=$(curl -s --max-time 5 -w '\n%{http_code}' -X POST "$API/printer/emergency_stop") ||
    cant_stop "the printer's Moonraker service didn't answer."
code=$(printf '%s\n' "$resp" | tail -n 1)
if [ "$code" != 200 ]; then
    # Moonraker refuses the stop when Klipper isn't running, e.g. when it is
    # already shut down. Only carry on if Klipper confirms it can't move.
    state=$(curl -s --max-time 5 "$API/printer/info" |
        grep -o '"state": *"[a-z]*"' | head -n 1 | sed 's/.*"\([a-z]*\)"$/\1/')
    case "$state" in
        shutdown|error|startup) echo "Klipper was already stopped ($state)." ;;
        *) cant_stop "the stop request was refused (HTTP $code)." ;;
    esac
fi
sleep 2
curl -s --max-time 10 -X POST "$API/printer/firmware_restart" >/dev/null
sleep 10
sudo systemctl start makerbase-client

# Wait for the printer to finish restarting.
ready=
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s --max-time 5 "$API/printer/info" | grep -q '"state": *"ready"'; then
        ready=1
        break
    fi
    sleep 3
done
if [ -z "$ready" ]; then
    echo "Stopped, but the printer hasn't finished restarting. Check the"
    echo "touchscreen for an error, then run ~/pen/stop.sh again."
    exit 1
fi

# Pen mode's "home": sets the position counters without moving anything.
curl -s --max-time 10 -X POST "$API/printer/gcode/script?script=G28" >/dev/null
echo "Stopped and restarted. The touchscreen is back on."
