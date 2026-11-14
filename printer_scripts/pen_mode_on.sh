#!/bin/sh
# Switch pen mode ON: homing is skipped (it would crash the pen into the bed)
# and the movement limits are widened so the buttons never get blocked.
CFG=~/klipper_config/printer.cfg
LINE='[include pen_plotter.cfg]'

if [ ! -f ~/klipper_config/pen_plotter.cfg ]; then
    echo "~/klipper_config/pen_plotter.cfg is missing - run the installer first."
    exit 1
fi
# Keep a copy of the untouched settings the first time.
[ -f "$CFG.before-pen" ] || cp "$CFG" "$CFG.before-pen"

if ! grep -qF "$LINE" "$CFG"; then
    if grep -q '^#\*# <-* SAVE_CONFIG' "$CFG"; then
        # Klipper's saved-settings block must stay last, so go just above it.
        sed -i "/^#\*# <-* SAVE_CONFIG/i $LINE\n" "$CFG"
    else
        printf '\n%s\n' "$LINE" >> "$CFG"
    fi
fi
curl -s -X POST http://localhost:7125/printer/firmware_restart >/dev/null
echo "Pen mode is on."
