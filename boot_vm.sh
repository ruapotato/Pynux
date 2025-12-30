#!/bin/bash
# Pynux VM Boot Script
# Builds if needed and runs QEMU with VTNext renderer

set -e

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

echo "Starting Pynux VM with VTNext renderer..."
echo "Close the pygame window to exit."
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

# Start QEMU with serial connected to FIFOs
qemu-system-arm \
    -machine mps2-an385 \
    -cpu cortex-m3 \
    -nographic \
    -monitor none \
    -serial pipe:${PIPE_BASE} \
    -kernel build/pynux.elf &

QEMU_PID=$!

# Give QEMU a moment to start
sleep 0.3

# Run renderer:
# - Read from QEMU's output (.out) for graphics
# - Write to QEMU's input (.in) for keyboard
python3 vtnext/renderer.py --fifo-in "${PIPE_BASE}.out" --fifo-out "${PIPE_BASE}.in"

# Clean up QEMU
kill $QEMU_PID 2>/dev/null || true
wait $QEMU_PID 2>/dev/null || true
