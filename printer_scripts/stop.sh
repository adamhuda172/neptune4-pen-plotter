#!/bin/sh
# Stop the pen instantly, restart the printer and bring the touchscreen back.
# Also use this after a drawing finishes, to get the touchscreen back.
API=http://localhost:7125

curl -s -X POST "$API/printer/emergency_stop" >/dev/null
sleep 2
curl -s -X POST "$API/printer/firmware_restart" >/dev/null
sleep 10
sudo systemctl start makerbase-client

# Wait for the printer to finish restarting.
for i in 1 2 3 4 5 6 7 8 9 10; do
    curl -s "$API/printer/info" | grep -q '"state": "ready"' && break
    sleep 3
done

# Pen mode's "home": sets the position counters without moving anything.
curl -s -X POST "$API/printer/gcode/script?script=G28" >/dev/null
echo "Stopped and restarted. The touchscreen is back on."
