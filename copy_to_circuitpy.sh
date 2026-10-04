#!/usr/bin/env bash
# LanternFire - Quick Copy Script for CircuitPython
# Copies code.py, fire_sim.py, and all required library dependencies to CIRCUITPY drive.

set -e

DEST="${1:-/Volumes/CIRCUITPY}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$SCRIPT_DIR/deploy/CIRCUITPY"

echo "=== LanternFire CircuitPython Deploy ==="
echo "Source: $SOURCE_DIR"
echo "Target: $DEST"
echo ""

if [ ! -d "$DEST" ]; then
    echo "⚠️  Target drive not found at: $DEST"
    echo ""
    echo "Make sure your CircuitPython board is plugged in via USB and mounted."
    echo ""
    echo "You can also specify a custom path:"
    echo "  $0 /path/to/CIRCUITPY"
    echo ""
    echo "Or open the pre-packaged folder to drag-and-drop in Finder:"
    echo "  open \"$SOURCE_DIR\""
    exit 1
fi

echo "Copying files to $DEST..."
cp -v "$SOURCE_DIR/code.py" "$DEST/"
cp -v "$SOURCE_DIR/fire_sim.py" "$DEST/"

mkdir -p "$DEST/lib"
cp -Rv "$SOURCE_DIR/lib/"* "$DEST/lib/"

echo ""
echo "Flushing disk buffer..."
sync

echo ""
echo "✅ LanternFire successfully deployed to $DEST!"
echo "Your board should automatically reload and start the fire simulation."
