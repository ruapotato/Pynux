#!/bin/bash
# Pynux VM Boot Script
# Builds if needed and runs QEMU with VTNext renderer

set -e

# Parse arguments
SIMPLE_SHELL=0
DEBUG_MODE=0
for arg in "$@"; do
    case $arg in
        --shell|--simple-shell|--text)
            SIMPLE_SHELL=1
            ;;
        --debug)
            DEBUG_MODE=1
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --shell, --simple-shell, --text   Run in text mode (no graphics)"
            echo "  --debug                           Show raw VTNext commands"
            echo "  --help, -h                        Show this help"
            exit 0
            ;;
    esac
done

# Build if pynux.elf doesn't exist or sources are newer
BUILD_NEEDED=0

if [ ! -f "build/pynux.elf" ]; then
    BUILD_NEEDED=1
else
    # Check if any source is newer than the elf
    for src in kernel/*.py lib/*.py; do
        if [ "$src" -nt "build/pynux.elf" ]; then
            BUILD_NEEDED=1
            break
        fi
    done
fi

if [ "$BUILD_NEEDED" -eq 1 ]; then
    echo "Building Pynux..."
    ./build.sh
    echo ""
fi

# Simple shell mode - just run QEMU with nographic
if [ "$SIMPLE_SHELL" -eq 1 ]; then
    echo "Starting Pynux in text mode..."
    echo "Type 'exit' to quit, or Ctrl+A X to force exit QEMU."
    echo ""
    exec qemu-system-arm \
        -machine mps2-an385 \
        -cpu cortex-m3 \
        -m 16M \
        -nographic \
        -no-reboot \
        -kernel build/pynux.elf
fi

echo "Starting Pynux VM with VTNext graphical renderer..."
echo "Close the pygame window to exit."
if [ "$DEBUG_MODE" -eq 1 ]; then
    echo "DEBUG MODE: Showing raw VTNext commands"
fi
echo ""

# QEMU's -serial pipe:NAME expects NAME.in and NAME.out files
PIPE_BASE="/tmp/pynux_$$"

cleanup() {
    rm -f "${PIPE_BASE}.in" "${PIPE_BASE}.out"
    # Kill any background jobs
    jobs -p | xargs -r kill 2>/dev/null || true
}
trap cleanup EXIT

# Create FIFOs that QEMU expects
# QEMU reads from .in and writes to .out
mkfifo "${PIPE_BASE}.in"
mkfifo "${PIPE_BASE}.out"

# Build renderer args
RENDERER_ARGS="--fifo-in ${PIPE_BASE}.out --fifo-out ${PIPE_BASE}.in"
if [ "$DEBUG_MODE" -eq 1 ]; then
    RENDERER_ARGS="$RENDERER_ARGS --debug"
fi

# Start renderer FIRST in background so it's ready to respond to probe
python3 vtnext/renderer.py $RENDERER_ARGS &
RENDERER_PID=$!

# Give renderer time to open the FIFOs
sleep 0.5

# Start QEMU with serial connected to FIFOs
qemu-system-arm \
    -machine mps2-an385 \
    -cpu cortex-m3 \
    -m 16M \
    -nographic \
    -monitor none \
    -serial pipe:${PIPE_BASE} \
    -kernel build/pynux.elf &

QEMU_PID=$!

# Wait for renderer to exit (user closes window)
wait $RENDERER_PID 2>/dev/null || true

# Clean up QEMU
kill $QEMU_PID 2>/dev/null || true
wait $QEMU_PID 2>/dev/null || true
