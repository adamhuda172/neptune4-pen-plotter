#!/bin/sh
# One-time setup on macOS: creates a private Python environment in .venv with
# everything the converter and printer tools need.
# Run from the repo folder:  sh mac/setup.sh
set -e
cd "$(dirname "$0")/.."

if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 not found. Run 'xcode-select --install' (or install Python from python.org), then try again."
    exit 1
fi

python3 -m venv .venv
.venv/bin/pip install --upgrade pip >/dev/null
.venv/bin/pip install -r requirements.txt

echo
echo "Done. Try:"
echo "  .venv/bin/python image_to_gcode.py picture.png picture.gcode --preview picture_preview.png"
echo "  .venv/bin/python tools/printer_link.py ports"
