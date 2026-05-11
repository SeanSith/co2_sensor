#!/bin/bash
# Copy firmware files to the CIRCUITPY drive
# Usage: ./tools/deploy.sh

set -e
cd "$(dirname "$0")/.."

DEST="/Volumes/CIRCUITPY"

if [ ! -d "$DEST" ]; then
    echo "CIRCUITPY drive not mounted. Connect the FeatherS3 and retry." >&2
    exit 1
fi

cp code.py "$DEST/code.py" && cp feathers3.py "$DEST/feathers3.py"
echo "Deployed. Device will reset automatically."
