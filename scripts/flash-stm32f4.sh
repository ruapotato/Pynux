#!/bin/bash
# Flash Pynux to STM32F4 boards
#
# Requirements (install one):
#   - st-flash: sudo apt install stlink-tools
#   - openocd:  sudo apt install openocd
#
# Supported boards:
#   - STM32F4 Discovery
#   - STM32F4 Nucleo
#   - Generic STM32F4 with ST-Link
#
# Usage:
#   ./scripts/flash-stm32f4.sh              # Flash using st-flash
#   ./scripts/flash-stm32f4.sh --openocd    # Flash using OpenOCD
#   ./scripts/flash-stm32f4.sh --build      # Build first, then flash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

BUILD_FIRST=false
USE_OPENOCD=false

for arg in "$@"; do
    case $arg in
        --build|-b)
            BUILD_FIRST=true
            ;;
        --openocd|-o)
            USE_OPENOCD=true
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --build, -b     Build before flashing"
            echo "  --openocd, -o   Use OpenOCD instead of st-flash"
            echo "  --help, -h      Show this help"
            exit 0
            ;;
    esac
done

if [ "$BUILD_FIRST" = true ]; then
    echo "=== Building for STM32F4 ==="
    ./build.sh --clean --target=stm32f4
    echo ""
fi

if [ ! -f "build/pynux.bin" ]; then
    echo "Error: build/pynux.bin not found"
    echo "Run: ./build.sh --target=stm32f4"
    exit 1
fi

if [ "$USE_OPENOCD" = true ]; then
    # Use OpenOCD
    if ! command -v openocd &> /dev/null; then
        echo "Error: openocd not found"
        echo "Install: sudo apt install openocd"
        exit 1
    fi

    echo "=== Flashing with OpenOCD ==="

    openocd \
        -f interface/stlink.cfg \
        -f target/stm32f4x.cfg \
        -c "program build/pynux.elf verify reset exit"

else
    # Use st-flash (default)
    if ! command -v st-flash &> /dev/null; then
        echo "Error: st-flash not found"
        echo "Install: sudo apt install stlink-tools"
        echo ""
        echo "Or use OpenOCD: $0 --openocd"
        exit 1
    fi

    echo "=== Flashing with st-flash ==="

    # Erase and flash
    st-flash --reset write build/pynux.bin 0x08000000
fi

echo ""
echo "Flash complete! Board is resetting..."
