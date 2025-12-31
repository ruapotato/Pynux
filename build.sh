#!/bin/bash
# Pynux OS Build Script
# Builds kernel and runs in QEMU

set -e

BUILD_DIR="build"
RUNTIME_DIR="runtime"

# ARM toolchain
AS="arm-none-eabi-as"
LD="arm-none-eabi-ld"
OBJCOPY="arm-none-eabi-objcopy"

# QEMU
QEMU="qemu-system-arm"
MACHINE="mps2-an385"

# Assembler flags
ASFLAGS="-mcpu=cortex-m3 -mthumb"

# Create build directory
mkdir -p "$BUILD_DIR"

echo "=== Pynux OS Build ==="
echo ""

# Step 1: Compile Pynux sources to assembly
echo "[1/4] Compiling Pynux sources..."

# List of Pynux source files to compile
PYNUX_SOURCES=(
    "kernel/kernel.py"
    "kernel/timer.py"
    "kernel/ramfs.py"
    "lib/memory.py"
    "lib/string.py"
    "coreutils/sh.py"
)

python3 << 'PYEND'
import sys
import os
import glob
sys.path.insert(0, '.')

from compiler.parser import parse
from compiler.codegen_arm import ARMCodeGen

# Core system sources
sources = [
    ("kernel/kernel.py", "kernel"),
    ("kernel/timer.py", "timer"),
    ("kernel/ramfs.py", "ramfs"),
    ("kernel/process.py", "process"),
    ("kernel/devfs.py", "devfs"),
    ("lib/memory.py", "memory"),
    ("lib/string.py", "string"),
    ("lib/io.py", "iolib"),
    ("lib/peripherals.py", "peripherals"),
    ("lib/vtnext.py", "vtnext"),
    ("lib/de.py", "de"),
    ("lib/shell.py", "shell"),
    ("lib/widgets.py", "widgets"),
    ("lib/devtools.py", "devtools"),
    ("lib/math.py", "mathlib"),
    ("lib/sensors.py", "sensors"),
    ("lib/motors.py", "motors"),
]

# Add user programs from programs/ folder
user_programs = []
for prog_path in sorted(glob.glob("programs/*.py")):
    name = os.path.basename(prog_path).replace(".py", "")
    sources.append((prog_path, f"prog_{name}"))
    user_programs.append(name)

if user_programs:
    print(f"  Found user programs: {', '.join(user_programs)}")

for src_path, name in sources:
    try:
        with open(src_path) as f:
            source = f.read()
        ast = parse(source, src_path)
        codegen = ARMCodeGen()
        asm = codegen.gen_program(ast)
        out_path = f"build/{name}.s"
        with open(out_path, 'w') as f:
            f.write(asm)
        print(f"  {src_path} -> {out_path}")
    except Exception as e:
        print(f"  ERROR: {src_path}: {e}")
        sys.exit(1)

# Save list of user programs for linker
with open("build/user_programs.txt", "w") as f:
    for name in user_programs:
        f.write(f"prog_{name}\n")
PYEND

# Step 2: Assemble all .s files
echo "[2/4] Assembling..."

# Runtime assembly files
$AS $ASFLAGS -o "$BUILD_DIR/startup.o" "$RUNTIME_DIR/startup.s"
echo "  runtime/startup.s"

$AS $ASFLAGS -o "$BUILD_DIR/io.o" "$RUNTIME_DIR/io.s"
echo "  runtime/io.s"

# Compiled Pynux files
for name in kernel timer ramfs process devfs memory string iolib peripherals vtnext de shell widgets devtools mathlib sensors motors; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Compile user programs
if [ -f "$BUILD_DIR/user_programs.txt" ]; then
    while read -r progname; do
        if [ -f "$BUILD_DIR/${progname}.s" ]; then
            $AS $ASFLAGS -o "$BUILD_DIR/${progname}.o" "$BUILD_DIR/${progname}.s"
            echo "  build/${progname}.s"
        fi
    done < "$BUILD_DIR/user_programs.txt"
fi

# Step 3: Link
echo "[3/4] Linking..."

# Build list of object files
OBJS="$BUILD_DIR/startup.o $BUILD_DIR/io.o"
OBJS="$OBJS $BUILD_DIR/kernel.o $BUILD_DIR/timer.o $BUILD_DIR/ramfs.o $BUILD_DIR/process.o $BUILD_DIR/devfs.o"
OBJS="$OBJS $BUILD_DIR/memory.o $BUILD_DIR/string.o $BUILD_DIR/iolib.o $BUILD_DIR/peripherals.o"
OBJS="$OBJS $BUILD_DIR/vtnext.o $BUILD_DIR/de.o $BUILD_DIR/shell.o $BUILD_DIR/widgets.o $BUILD_DIR/devtools.o"
OBJS="$OBJS $BUILD_DIR/mathlib.o $BUILD_DIR/sensors.o $BUILD_DIR/motors.o"

# Add user program objects
if [ -f "$BUILD_DIR/user_programs.txt" ]; then
    while read -r progname; do
        if [ -f "$BUILD_DIR/${progname}.o" ]; then
            OBJS="$OBJS $BUILD_DIR/${progname}.o"
        fi
    done < "$BUILD_DIR/user_programs.txt"
fi

$LD -T "$RUNTIME_DIR/mps2-an385.ld" -o "$BUILD_DIR/pynux.elf" $OBJS
echo "  -> build/pynux.elf"

# Create binary
$OBJCOPY -O binary "$BUILD_DIR/pynux.elf" "$BUILD_DIR/pynux.bin"
echo "  -> build/pynux.bin"

# Show size
arm-none-eabi-size "$BUILD_DIR/pynux.elf"

echo ""
echo "=== Build Complete ==="
echo ""

# Step 4: Run in QEMU (if --run flag given)
if [ "$1" == "--run" ]; then
    echo "[4/4] Running in QEMU..."
    echo "  Machine: $MACHINE"
    echo "  Press Ctrl+A, X to exit"
    echo ""
    $QEMU -machine $MACHINE \
        -cpu cortex-m3 \
        -nographic \
        -semihosting \
        -kernel "$BUILD_DIR/pynux.elf"
fi
