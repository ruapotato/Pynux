#!/bin/bash
# Flash Pynux to RP2040 (Raspberry Pi Pico)
#
# Requirements:
#   - picotool: sudo apt install picotool
#   - Or just drag-and-drop pynux.uf2 to the Pico in BOOTSEL mode
#
# Usage:
#   ./scripts/flash-rp2040.sh          # Flash using picotool
#   ./scripts/flash-rp2040.sh --build  # Build first, then flash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

BUILD_FIRST=false

for arg in "$@"; do
    case $arg in
        --build|-b)
            BUILD_FIRST=true
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --build, -b   Build before flashing"
            echo "  --help, -h    Show this help"
            echo ""
            echo "Alternative: Put Pico in BOOTSEL mode (hold BOOTSEL while plugging in)"
            echo "            Then drag-and-drop build/pynux.uf2 to the RPI-RP2 drive"
            exit 0
            ;;
    esac
done

if [ "$BUILD_FIRST" = true ]; then
    echo "=== Building for RP2040 ==="
    ./build.sh --clean --target=rp2040
    echo ""
fi

if [ ! -f "build/pynux.elf" ]; then
    echo "Error: build/pynux.elf not found"
    echo "Run: ./build.sh --target=rp2040"
    exit 1
fi

# Check for picotool
if command -v picotool &> /dev/null; then
    echo "=== Flashing with picotool ==="
    echo "Note: Pico must be in BOOTSEL mode"
    echo ""

    # Try to reboot into BOOTSEL mode first
    picotool reboot -f -u 2>/dev/null || true
    sleep 2

    # Flash the firmware
    picotool load build/pynux.elf -f
    picotool reboot

    echo ""
    echo "Flash complete! Pico is rebooting..."
else
    echo "picotool not found."
    echo ""
    echo "Option 1: Install picotool"
    echo "  sudo apt install picotool"
    echo ""
    echo "Option 2: Manual UF2 flashing"
    echo "  1. Hold BOOTSEL button and plug in Pico"
    echo "  2. Copy build/pynux.uf2 to the RPI-RP2 drive"
    echo ""

    # Create UF2 if elf2uf2 is available
    if command -v elf2uf2 &> /dev/null; then
        echo "Creating UF2 file..."
        elf2uf2 build/pynux.elf build/pynux.uf2
        echo "Created: build/pynux.uf2"
    fi

    exit 1
fi
