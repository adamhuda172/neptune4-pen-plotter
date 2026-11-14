#!/bin/sh
# Open the printer's console on macOS (the Mac equivalent of PuTTY).
# Run from the repo folder:  sh mac/connect.sh
# Log in as mks. To leave: press Ctrl+A, then K, then Y.

PORT=$(ls /dev/cu.usbserial-* /dev/cu.wchusbserial* 2>/dev/null | head -n 1)
if [ -z "$PORT" ]; then
    echo "Printer not found. Plug in the front USB-C cable and switch the printer on."
    echo "If it still isn't found, install the CH340 USB-serial driver and try again."
    exit 1
fi

echo "Connecting to $PORT. Press Enter, then log in. Leave with Ctrl+A, K, Y."
sleep 1
exec screen "$PORT" 1500000
