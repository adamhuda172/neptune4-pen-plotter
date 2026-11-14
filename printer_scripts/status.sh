#!/bin/sh
# Show what the printer is doing and how far through the drawing it is.
API=http://localhost:7125

curl -s "$API/printer/objects/query?print_stats=state,filename&virtual_sdcard=progress&gcode_move=speed_factor" |
    python3 -c '
import json, sys
s = json.load(sys.stdin)["result"]["status"]
print("State:    ", s["print_stats"]["state"])
print("File:     ", s["print_stats"]["filename"] or "-")
print("Progress: ", "%d%%" % round(100 * s["virtual_sdcard"]["progress"]))
print("Speed:    ", "%d%%" % round(100 * s["gcode_move"]["speed_factor"]))
'
echo "Touchscreen: $(systemctl is-active makerbase-client)"
