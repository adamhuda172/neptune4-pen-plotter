#!/bin/sh
# Turn the touchscreen program off, so it can't move the head when a drawing starts.
sudo systemctl stop makerbase-client && echo "Touchscreen is off."
