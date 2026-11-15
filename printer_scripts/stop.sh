#!/bin/sh
# Stop the pen instantly, restart the printer and bring the touchscreen back.
# Also use this after a drawing finishes, to get the touchscreen back.
API=http://localhost:7125

# curl only fails here if Moonraker can't be reached at all. (If Klipper is
# already shut down, Moonraker answers with an error but nothing is moving.)
if ! curl -s -X POST "$API/printer/emergency_stop" >/dev/null; then
    echo "COULD NOT STOP: the printer's Moonraker service didn't answer."
    echo "Switch the printer off at the power switch."
    exit 1
fi
sleep 2
curl -s -X POST "$API/printer/firmware_restart" >/dev/null
sleep 10
sudo systemctl start makerbase-client

# Wait for the printer to finish restarting.
ready=
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -s "$API/printer/info" | grep -q '"state": *"ready"'; then
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
curl -s -X POST "$API/printer/gcode/script?script=G28" >/dev/null
echo "Stopped and restarted. The touchscreen is back on."
