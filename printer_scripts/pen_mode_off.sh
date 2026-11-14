#!/bin/sh
# Switch pen mode OFF, for normal 3D printing: homing works again and the
# normal movement limits come back. Refit the bed sensor and extruder first,
# then run Level on the touchscreen afterwards.
CFG=~/klipper_config/printer.cfg

sed -i '/^\[include pen_plotter.cfg\]$/d' "$CFG"
curl -s -X POST http://localhost:7125/printer/firmware_restart >/dev/null
echo "Pen mode is off. Restart the printer, then run Level before printing."
