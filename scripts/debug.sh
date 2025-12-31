#!/bin/bash
# Pynux GDB Debugging
#
# Usage:
#   ./scripts/debug.sh              # Debug in QEMU
#   ./scripts/debug.sh --rp2040     # Debug on RP2040 via OpenOCD
#   ./scripts/debug.sh --stm32f4    # Debug on STM32F4 via OpenOCD
#
# This script starts the target (QEMU or OpenOCD) and connects GDB.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

TARGET="qemu"
GDB="arm-none-eabi-gdb"

for arg in "$@"; do
    case $arg in
        --rp2040)
            TARGET="rp2040"
            ;;
        --stm32f4)
            TARGET="stm32f4"
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --rp2040    Debug on RP2040 hardware"
            echo "  --stm32f4   Debug on STM32F4 hardware"
            echo "  --help      Show this help"
            echo ""
            echo "Default: Debug in QEMU emulator"
            exit 0
            ;;
    esac
done

if [ ! -f "build/pynux.elf" ]; then
    echo "Error: build/pynux.elf not found"
    echo "Run: ./build.sh --target=$TARGET"
    exit 1
fi

case $TARGET in
    qemu)
        echo "=== Starting QEMU with GDB server ==="
        echo "QEMU will wait for GDB connection on port 1234"
        echo ""

        # Start QEMU in background with GDB server
        qemu-system-arm \
            -M mps2-an385 \
            -cpu cortex-m3 \
            -nographic \
            -S -gdb tcp::1234 \
            -kernel build/pynux.elf &
        QEMU_PID=$!

        sleep 1

        echo "Starting GDB..."
        echo ""

        # Connect GDB
        $GDB build/pynux.elf \
            -ex "target remote :1234" \
            -ex "load" \
            -ex "break main" \
            -ex "continue"

        # Cleanup
        kill $QEMU_PID 2>/dev/null || true
        ;;

    rp2040)
        echo "=== Starting OpenOCD for RP2040 ==="
        echo "Make sure the Pico is connected via SWD debugger"
        echo ""

        # Start OpenOCD in background
        openocd \
            -f interface/cmsis-dap.cfg \
            -f target/rp2040.cfg &
        OPENOCD_PID=$!

        sleep 2

        echo "Starting GDB..."
        echo ""

        # Connect GDB
        $GDB build/pynux.elf \
            -ex "target extended-remote :3333" \
            -ex "monitor reset halt" \
            -ex "load" \
            -ex "break main" \
            -ex "continue"

        # Cleanup
        kill $OPENOCD_PID 2>/dev/null || true
        ;;

    stm32f4)
        echo "=== Starting OpenOCD for STM32F4 ==="
        echo "Make sure the board is connected via ST-Link"
        echo ""

        # Start OpenOCD in background
        openocd \
            -f interface/stlink.cfg \
            -f target/stm32f4x.cfg &
        OPENOCD_PID=$!

        sleep 2

        echo "Starting GDB..."
        echo ""

        # Connect GDB
        $GDB build/pynux.elf \
            -ex "target extended-remote :3333" \
            -ex "monitor reset halt" \
            -ex "load" \
            -ex "break main" \
            -ex "continue"

        # Cleanup
        kill $OPENOCD_PID 2>/dev/null || true
        ;;
esac
