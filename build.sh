#!/bin/bash
# Pynux OS Build Script
# Builds kernel for QEMU or real hardware targets

set -e

# ============================================================================
# Configuration
# ============================================================================

BUILD_DIR="build"
RUNTIME_DIR="runtime"

# ARM toolchain
AS="arm-none-eabi-as"
LD="arm-none-eabi-ld"
OBJCOPY="arm-none-eabi-objcopy"

# QEMU settings
QEMU="qemu-system-arm"

# Default target
TARGET="qemu"
RUN_AFTER_BUILD=false
FLASH_AFTER_BUILD=false

# ============================================================================
# Parse Arguments
# ============================================================================

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --target=TARGET   Build target: qemu (default), rp2040, stm32f4"
    echo "  --run             Run in QEMU after build (qemu target only)"
    echo "  --flash           Flash to device after build (hardware targets)"
    echo "  --clean           Clean build directory before building"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Build for QEMU"
    echo "  $0 --target=rp2040      # Build for Raspberry Pi Pico"
    echo "  $0 --target=stm32f4     # Build for STM32F4 boards"
    echo "  $0 --run                # Build and run in QEMU"
}

for arg in "$@"; do
    case $arg in
        --target=*)
            TARGET="${arg#*=}"
            ;;
        --run)
            RUN_AFTER_BUILD=true
            ;;
        --flash)
            FLASH_AFTER_BUILD=true
            ;;
        --clean)
            rm -rf "$BUILD_DIR"
            ;;
        --help)
            print_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $arg"
            print_usage
            exit 1
            ;;
    esac
done

# ============================================================================
# Target Configuration
# ============================================================================

case $TARGET in
    qemu)
        ASFLAGS="-mcpu=cortex-m3 -mthumb"
        LINKER_SCRIPT="$RUNTIME_DIR/mps2-an385.ld"
        STARTUP_FILE="$RUNTIME_DIR/startup.s"
        IO_FILE="$RUNTIME_DIR/io.s"
        SYSTEM_CLOCK=25000000
        QEMU_MACHINE="mps2-an385"
        QEMU_CPU="cortex-m3"
        echo "=== Pynux OS Build (QEMU mps2-an385) ==="
        ;;
    rp2040)
        # RP2040 uses Cortex-M0+ (no Thumb-2, limited instructions)
        ASFLAGS="-mcpu=cortex-m0plus -mthumb"
        LINKER_SCRIPT="bsp/rp2040/rp2040.ld"
        STARTUP_FILE="bsp/rp2040/startup.s"
        IO_FILE=""  # UART is in startup.s for RP2040
        SYSTEM_CLOCK=125000000
        echo "=== Pynux OS Build (RP2040 / Raspberry Pi Pico) ==="
        ;;
    stm32f4)
        # STM32F4 uses Cortex-M4 with FPU
        ASFLAGS="-mcpu=cortex-m4 -mthumb -mfloat-abi=soft"
        LINKER_SCRIPT="bsp/stm32f4/stm32f4.ld"
        STARTUP_FILE="bsp/stm32f4/startup.s"
        IO_FILE=""  # UART is in startup.s for STM32F4
        SYSTEM_CLOCK=168000000
        echo "=== Pynux OS Build (STM32F405/F407) ==="
        ;;
    *)
        echo "Unknown target: $TARGET"
        echo "Valid targets: qemu, rp2040, stm32f4"
        exit 1
        ;;
esac

echo "  System clock: $((SYSTEM_CLOCK / 1000000)) MHz"
echo ""

# Create build directory
mkdir -p "$BUILD_DIR"

# ============================================================================
# Step 1: Compile Pynux sources to assembly
# ============================================================================

echo "[1/4] Compiling Pynux sources..."

python3 << PYEND
import sys
import os
import glob
sys.path.insert(0, '.')

from compiler.parser import parse
from compiler.codegen_arm import ARMCodeGen

# Target-specific configuration
TARGET = "$TARGET"
SYSTEM_CLOCK = $SYSTEM_CLOCK

# Core system sources
sources = [
    # Kernel modules
    ("kernel/kernel.py", "kernel"),
    ("kernel/timer.py", "timer"),
    ("kernel/ramfs.py", "ramfs"),
    ("kernel/process.py", "process"),
    ("kernel/devfs.py", "devfs"),
    ("kernel/boot.py", "boot"),
    ("kernel/debug.py", "debug"),
    ("kernel/firmware.py", "firmware"),
    ("kernel/gdb_stub.py", "gdb_stub"),
    ("kernel/sync.py", "sync"),
    # Core libraries
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
    # Hardware libraries
    ("lib/i2c.py", "i2c"),
    ("lib/spi.py", "spi"),
    # Debug/profiling libraries
    ("lib/trace.py", "trace"),
    ("lib/profiler.py", "profiler"),
    ("lib/memtrack.py", "memtrack"),
    ("lib/breakpoint.py", "breakpoint"),
    # Graphics library
    ("lib/gfx/color.py", "gfx_color"),
    ("lib/gfx/framebuffer.py", "gfx_framebuffer"),
    ("lib/gfx/draw.py", "gfx_draw"),
    # Network stack
    ("lib/net/ethernet.py", "net_ethernet"),
    ("lib/net/ip.py", "net_ip"),
    ("lib/net/udp.py", "net_udp"),
    ("lib/net/tcp.py", "net_tcp"),
    ("lib/net/dhcp.py", "net_dhcp"),
]

# Add user programs from programs/ folder
user_programs = []
for prog_path in sorted(glob.glob("programs/*.py")):
    name = os.path.basename(prog_path).replace(".py", "")
    sources.append((prog_path, f"prog_{name}"))
    user_programs.append(name)

if user_programs:
    print(f"  Found user programs: {', '.join(user_programs)}")

# Add test files from tests/ folder
excluded_tests = ["test_compiler.py", "test_integration.py", "test_all.py",
                  "test_process.py", "test_sync.py",
                  "test_boot.py", "test_gfx.py",
                  "test_scheduler.py", "test_shell.py"]
test_files = []
for test_path in sorted(glob.glob("tests/test_*.py")):
    name = os.path.basename(test_path)
    if name in excluded_tests:
        continue
    with open(test_path) as f:
        first_line = f.readline().strip()
    if first_line.startswith("#!/"):
        continue
    name = name.replace(".py", "")
    sources.append((test_path, f"tests_{name}"))
    test_files.append(name)

if test_files:
    print(f"  Found test files: {', '.join(test_files)}")

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

# Save lists for linker
with open("build/user_programs.txt", "w") as f:
    for name in user_programs:
        f.write(f"prog_{name}\n")

with open("build/test_files.txt", "w") as f:
    for name in test_files:
        f.write(f"tests_{name}\n")

# Save target info
with open("build/target.txt", "w") as f:
    f.write(TARGET)
PYEND

# ============================================================================
# Step 2: Assemble all .s files
# ============================================================================

echo "[2/4] Assembling..."

# Target-specific startup
$AS $ASFLAGS -o "$BUILD_DIR/startup.o" "$STARTUP_FILE"
echo "  $STARTUP_FILE"

# QEMU needs separate io.s
if [ -n "$IO_FILE" ]; then
    $AS $ASFLAGS -o "$BUILD_DIR/io.o" "$IO_FILE"
    echo "  $IO_FILE"
fi

# Compiled Pynux files - kernel modules
for name in kernel timer ramfs process devfs boot debug firmware gdb_stub sync; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Core libraries
for name in memory string iolib peripherals vtnext de shell widgets devtools mathlib sensors motors; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Hardware libraries
for name in i2c spi; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Debug/profiling libraries
for name in trace profiler memtrack breakpoint; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Graphics library
for name in gfx_color gfx_framebuffer gfx_draw; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Network stack
for name in net_ethernet net_ip net_udp net_tcp net_dhcp; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# User programs
if [ -f "$BUILD_DIR/user_programs.txt" ]; then
    while read -r progname; do
        if [ -f "$BUILD_DIR/${progname}.s" ]; then
            $AS $ASFLAGS -o "$BUILD_DIR/${progname}.o" "$BUILD_DIR/${progname}.s"
            echo "  build/${progname}.s"
        fi
    done < "$BUILD_DIR/user_programs.txt"
fi

# Test files
if [ -f "$BUILD_DIR/test_files.txt" ]; then
    while read -r testname; do
        if [ -f "$BUILD_DIR/${testname}.s" ]; then
            $AS $ASFLAGS -o "$BUILD_DIR/${testname}.o" "$BUILD_DIR/${testname}.s"
            echo "  build/${testname}.s"
        fi
    done < "$BUILD_DIR/test_files.txt"
fi

# ============================================================================
# Step 3: Link
# ============================================================================

echo "[3/4] Linking..."

# Build object list
OBJS="$BUILD_DIR/startup.o"
if [ -n "$IO_FILE" ]; then
    OBJS="$OBJS $BUILD_DIR/io.o"
fi

# Kernel modules
OBJS="$OBJS $BUILD_DIR/kernel.o $BUILD_DIR/timer.o $BUILD_DIR/ramfs.o"
OBJS="$OBJS $BUILD_DIR/process.o $BUILD_DIR/devfs.o $BUILD_DIR/boot.o"
OBJS="$OBJS $BUILD_DIR/debug.o $BUILD_DIR/firmware.o $BUILD_DIR/gdb_stub.o $BUILD_DIR/sync.o"

# Core libraries
OBJS="$OBJS $BUILD_DIR/memory.o $BUILD_DIR/string.o $BUILD_DIR/iolib.o $BUILD_DIR/peripherals.o"
OBJS="$OBJS $BUILD_DIR/vtnext.o $BUILD_DIR/de.o $BUILD_DIR/shell.o $BUILD_DIR/widgets.o $BUILD_DIR/devtools.o"
OBJS="$OBJS $BUILD_DIR/mathlib.o $BUILD_DIR/sensors.o $BUILD_DIR/motors.o"

# Hardware libraries
OBJS="$OBJS $BUILD_DIR/i2c.o $BUILD_DIR/spi.o"

# Debug/profiling libraries
OBJS="$OBJS $BUILD_DIR/trace.o $BUILD_DIR/profiler.o $BUILD_DIR/memtrack.o $BUILD_DIR/breakpoint.o"

# Graphics library
OBJS="$OBJS $BUILD_DIR/gfx_color.o $BUILD_DIR/gfx_framebuffer.o $BUILD_DIR/gfx_draw.o"

# Network stack
OBJS="$OBJS $BUILD_DIR/net_ethernet.o $BUILD_DIR/net_ip.o $BUILD_DIR/net_udp.o $BUILD_DIR/net_tcp.o $BUILD_DIR/net_dhcp.o"

# User programs
if [ -f "$BUILD_DIR/user_programs.txt" ]; then
    while read -r progname; do
        if [ -f "$BUILD_DIR/${progname}.o" ]; then
            OBJS="$OBJS $BUILD_DIR/${progname}.o"
        fi
    done < "$BUILD_DIR/user_programs.txt"
fi

# Test files
if [ -f "$BUILD_DIR/test_files.txt" ]; then
    while read -r testname; do
        if [ -f "$BUILD_DIR/${testname}.o" ]; then
            OBJS="$OBJS $BUILD_DIR/${testname}.o"
        fi
    done < "$BUILD_DIR/test_files.txt"
fi

$LD -T "$LINKER_SCRIPT" -o "$BUILD_DIR/pynux.elf" $OBJS
echo "  -> build/pynux.elf"

# Create binary
$OBJCOPY -O binary "$BUILD_DIR/pynux.elf" "$BUILD_DIR/pynux.bin"
echo "  -> build/pynux.bin"

# Create UF2 for RP2040 (if target is rp2040)
if [ "$TARGET" == "rp2040" ]; then
    # Check if elf2uf2 is available
    if command -v elf2uf2 &> /dev/null; then
        elf2uf2 "$BUILD_DIR/pynux.elf" "$BUILD_DIR/pynux.uf2"
        echo "  -> build/pynux.uf2"
    else
        echo "  (elf2uf2 not found, skipping UF2 generation)"
        echo "  Install pico-sdk tools or use picotool to flash"
    fi
fi

# Show size
arm-none-eabi-size "$BUILD_DIR/pynux.elf"

echo ""
echo "=== Build Complete ==="
echo ""

# ============================================================================
# Step 4: Run or Flash
# ============================================================================

if [ "$RUN_AFTER_BUILD" = true ]; then
    if [ "$TARGET" == "qemu" ]; then
        echo "[4/4] Running in QEMU..."
        echo "  Machine: $QEMU_MACHINE"
        echo "  CPU: $QEMU_CPU"
        echo "  Press Ctrl+A, X to exit"
        echo ""
        $QEMU -machine $QEMU_MACHINE \
            -cpu $QEMU_CPU \
            -nographic \
            -semihosting \
            -kernel "$BUILD_DIR/pynux.elf"
    else
        echo "Error: --run is only supported for QEMU target"
        exit 1
    fi
fi

if [ "$FLASH_AFTER_BUILD" = true ]; then
    case $TARGET in
        rp2040)
            echo "[4/4] Flashing to RP2040..."
            if [ -f "$BUILD_DIR/pynux.uf2" ]; then
                # Try to find mounted Pico
                PICO_MOUNT=$(find /media /mnt /run/media -name "RPI-RP2" -type d 2>/dev/null | head -1)
                if [ -n "$PICO_MOUNT" ]; then
                    cp "$BUILD_DIR/pynux.uf2" "$PICO_MOUNT/"
                    echo "  Copied to $PICO_MOUNT"
                    echo "  Pico will reboot automatically"
                else
                    echo "  Error: Pico not found in BOOTSEL mode"
                    echo "  Hold BOOTSEL while connecting USB, then run again"
                fi
            else
                echo "  Error: pynux.uf2 not found. Install elf2uf2."
            fi
            ;;
        stm32f4)
            echo "[4/4] Flashing to STM32F4..."
            if command -v st-flash &> /dev/null; then
                st-flash write "$BUILD_DIR/pynux.bin" 0x08000000
            elif command -v openocd &> /dev/null; then
                openocd -f interface/stlink.cfg -f target/stm32f4x.cfg \
                    -c "program $BUILD_DIR/pynux.elf verify reset exit"
            else
                echo "  Error: Neither st-flash nor openocd found"
                echo "  Install stlink-tools or openocd"
            fi
            ;;
        *)
            echo "Error: --flash not supported for target: $TARGET"
            exit 1
            ;;
    esac
fi
