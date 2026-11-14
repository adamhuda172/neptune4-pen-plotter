#!/bin/sh
# Turn the touchscreen program back on. (Switching the printer off and on also does this.)
sudo systemctl start makerbase-client && echo "Touchscreen is on."
