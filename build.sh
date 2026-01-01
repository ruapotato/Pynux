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
TEST_MODE=false
DEMO_MODE=false
INCLUDE_EXPERIMENTAL_NETWORKING=false

# ============================================================================
# Parse Arguments
# ============================================================================

print_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --target=TARGET   Build target: qemu (default), rp2040, rp2040w, stm32f4"
    echo "  --run             Run in QEMU after build (qemu target only)"
    echo "  --test            Build in test mode (auto-run tests on boot)"
    echo "  --flash           Flash to device after build (hardware targets)"
    echo "  --clean           Clean build directory before building"
    echo "  --include_experimental_native_networking"
    echo "                    Include experimental software TCP/IP stack"
    echo "  --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                      # Build for QEMU"
    echo "  $0 --target=rp2040      # Build for Raspberry Pi Pico"
    echo "  $0 --target=rp2040w     # Build for Raspberry Pi Pico W (WiFi)"
    echo "  $0 --target=stm32f4     # Build for STM32F4 boards"
    echo "  $0 --run                # Build and run in QEMU"
    echo "  $0 --test --run         # Build test kernel and run tests"
}

for arg in "$@"; do
    case $arg in
        --target=*)
            TARGET="${arg#*=}"
            ;;
        --run)
            RUN_AFTER_BUILD=true
            ;;
        --test)
            TEST_MODE=true
            ;;
        --demo)
            DEMO_MODE=true
            ;;
        --flash)
            FLASH_AFTER_BUILD=true
            ;;
        --clean)
            rm -rf "$BUILD_DIR"
            ;;
        --include_experimental_native_networking)
            INCLUDE_EXPERIMENTAL_NETWORKING=true
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
        LINK_LIBS=""
        SKIP_TESTS=false
        echo "=== Pynux OS Build (QEMU mps2-an385) ==="
        ;;
    rp2040)
        # RP2040 uses Cortex-M0+ (no Thumb-2, limited instructions)
        ASFLAGS="-mcpu=cortex-m0plus -mthumb"
        LINKER_SCRIPT="bsp/rp2040/rp2040.ld"
        STARTUP_FILE="bsp/rp2040/startup.s"
        IO_FILE=""  # UART is in startup.s for RP2040
        SYSTEM_CLOCK=125000000
        # Link libgcc for divide routines (M0+ has no hardware divide)
        LIBGCC=$(arm-none-eabi-gcc -mcpu=cortex-m0plus -mthumb -print-libgcc-file-name 2>/dev/null || echo "")
        LINK_LIBS="$LIBGCC"
        SKIP_TESTS=true  # Tests are designed for QEMU
        HAS_WIFI=false
        echo "=== Pynux OS Build (RP2040 / Raspberry Pi Pico) ==="
        ;;
    rp2040w)
        # RP2040 with CYW43439 WiFi chip (Pico W)
        ASFLAGS="-mcpu=cortex-m0plus -mthumb"
        LINKER_SCRIPT="bsp/rp2040/rp2040.ld"
        STARTUP_FILE="bsp/rp2040/startup.s"
        IO_FILE=""
        SYSTEM_CLOCK=125000000
        LIBGCC=$(arm-none-eabi-gcc -mcpu=cortex-m0plus -mthumb -print-libgcc-file-name 2>/dev/null || echo "")
        LINK_LIBS="$LIBGCC"
        SKIP_TESTS=true
        HAS_WIFI=true
        echo "=== Pynux OS Build (RP2040W / Raspberry Pi Pico W) ==="
        ;;
    stm32f4)
        # STM32F4 uses Cortex-M4 with FPU
        ASFLAGS="-mcpu=cortex-m4 -mthumb -mfloat-abi=soft"
        LINKER_SCRIPT="bsp/stm32f4/stm32f4.ld"
        STARTUP_FILE="bsp/stm32f4/startup.s"
        IO_FILE=""  # UART is in startup.s for STM32F4
        SYSTEM_CLOCK=168000000
        LIBGCC=$(arm-none-eabi-gcc -mcpu=cortex-m4 -mthumb -mfloat-abi=soft -print-libgcc-file-name 2>/dev/null || echo "")
        LINK_LIBS="$LIBGCC"
        SKIP_TESTS=true  # Tests are designed for QEMU
        echo "=== Pynux OS Build (STM32F405/F407) ==="
        ;;
    *)
        echo "Unknown target: $TARGET"
        echo "Valid targets: qemu, rp2040, rp2040w, stm32f4"
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
TEST_MODE = "$TEST_MODE" == "true"
DEMO_MODE = "$DEMO_MODE" == "true"
SKIP_TESTS = "$SKIP_TESTS" == "true"
INCLUDE_EXPERIMENTAL_NETWORKING = "$INCLUDE_EXPERIMENTAL_NETWORKING" == "true"
HAS_WIFI = "${HAS_WIFI:-false}" == "true"

# STM32F4 has limited RAM (128KB) - exclude memory-hungry modules
# RP2040 has 264KB so it can handle more
MINIMAL_BUILD = (TARGET == "stm32f4")

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
    ("lib/shell.py", "shell"),
    ("lib/devtools.py", "devtools"),
    ("lib/math.py", "mathlib"),
    ("lib/sensors.py", "sensors"),
    ("lib/motors.py", "motors"),
    # Hardware libraries
    ("lib/i2c.py", "i2c"),
    ("lib/spi.py", "spi"),
    # Control libraries
    ("lib/fsm.py", "fsm"),
    ("lib/pid.py", "pid"),
    ("lib/filters.py", "filters"),
    # Debug/profiling libraries
    ("lib/trace.py", "trace"),
    ("lib/profiler.py", "profiler"),
    ("lib/memtrack.py", "memtrack"),
    ("lib/breakpoint.py", "breakpoint"),
]

# Add UI/graphics modules only for targets with enough RAM
if not MINIMAL_BUILD:
    sources.extend([
        ("lib/vtnext.py", "vtnext"),
        ("lib/de.py", "de"),
        ("lib/widgets.py", "widgets"),
        # Graphics library
        ("lib/gfx/color.py", "gfx_color"),
        ("lib/gfx/framebuffer.py", "gfx_framebuffer"),
        ("lib/gfx/draw.py", "gfx_draw"),
    ])
    print("  [FULL BUILD - Including UI and graphics]")
else:
    print("  [MINIMAL BUILD - Excluding UI and graphics for RAM-constrained target]")

# Experimental native networking stack (opt-in only)
if INCLUDE_EXPERIMENTAL_NETWORKING:
    sources.extend([
        ("lib/net/ethernet.py", "net_ethernet"),
        ("lib/net/ip.py", "net_ip"),
        ("lib/net/udp.py", "net_udp"),
        ("lib/net/tcp.py", "net_tcp"),
        ("lib/net/dhcp.py", "net_dhcp"),
    ])
    print("  [EXPERIMENTAL: Native TCP/IP networking stack included]")

# Pico W WiFi support
if HAS_WIFI:
    if os.path.exists("lib/hal/rp2040_wifi.py"):
        sources.append(("lib/hal/rp2040_wifi.py", "rp2040_wifi"))
        print("  [WiFi: Pico W CYW43439 driver included]")
    else:
        print("  [WiFi: Driver not yet implemented]")

# Add user programs from programs/ folder
# Some programs are only for QEMU (they use test framework or QEMU-specific features)
hw_excluded_progs = ["run_tests", "sensormon", "datalogger"] if SKIP_TESTS else []

# For minimal builds, also exclude programs that require vtnext/graphics
if MINIMAL_BUILD:
    hw_excluded_progs.extend(["calc", "clock", "hexview", "imgview"])
user_programs = []
for prog_path in sorted(glob.glob("programs/*.py")):
    name = os.path.basename(prog_path).replace(".py", "")
    if name in hw_excluded_progs:
        continue
    sources.append((prog_path, f"prog_{name}"))
    user_programs.append(name)

if user_programs:
    print(f"  Found user programs: {', '.join(user_programs)}")
if hw_excluded_progs:
    print(f"  [SKIPPING programs for hardware: {', '.join(hw_excluded_progs)}]")

# Add test framework
# Test framework (skip for hardware targets)
if not SKIP_TESTS and os.path.exists("tests/framework.py"):
    sources.append(("tests/framework.py", "tests_framework"))
    print(f"  Found test framework: tests/framework.py")

# Add test files from tests/ folder (skip for hardware targets)
excluded_tests = ["test_compiler.py", "test_integration.py", "test_all.py",
                  "test_process.py", "test_sync.py",
                  "test_boot.py", "test_gfx.py",
                  "test_scheduler.py", "test_shell.py"]
test_files = []
if not SKIP_TESTS:
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
else:
    print("  [SKIPPING TESTS - Hardware target]")

for src_path, name in sources:
    try:
        with open(src_path) as f:
            source = f.read()

        # Enable test mode in kernel if requested
        if src_path == "kernel/kernel.py" and TEST_MODE:
            source = source.replace("TEST_MODE: bool = False", "TEST_MODE: bool = True")
            print(f"  [TEST MODE ENABLED]")

        # Enable demo mode in kernel if requested
        if src_path == "kernel/kernel.py" and DEMO_MODE:
            source = source.replace("DEMO_MODE: bool = False", "DEMO_MODE: bool = True")
            print(f"  [DEMO MODE ENABLED]")

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

# Save minimal build flag
with open("build/minimal_build.txt", "w") as f:
    f.write("true" if MINIMAL_BUILD else "false")

# Save experimental networking flag
with open("build/experimental_net.txt", "w") as f:
    f.write("true" if INCLUDE_EXPERIMENTAL_NETWORKING else "false")

# Save WiFi flag
with open("build/has_wifi.txt", "w") as f:
    f.write("true" if HAS_WIFI else "false")
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

# Read minimal build flag
MINIMAL_BUILD=$(cat "$BUILD_DIR/minimal_build.txt" 2>/dev/null || echo "false")

# Core libraries (always included)
for name in memory string iolib peripherals shell devtools mathlib sensors motors; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# UI libraries (only for full builds)
if [ "$MINIMAL_BUILD" != "true" ]; then
    for name in vtnext de widgets; do
        $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
        echo "  build/${name}.s"
    done
fi

# Hardware libraries
for name in i2c spi; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Control libraries
for name in fsm pid filters; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Debug/profiling libraries
for name in trace profiler memtrack breakpoint; do
    $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
    echo "  build/${name}.s"
done

# Graphics library (only for full builds)
if [ "$MINIMAL_BUILD" != "true" ]; then
    for name in gfx_color gfx_framebuffer gfx_draw; do
        $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
        echo "  build/${name}.s"
    done
fi

# Experimental native networking stack (opt-in only)
EXPERIMENTAL_NET=$(cat "$BUILD_DIR/experimental_net.txt" 2>/dev/null || echo "false")
if [ "$EXPERIMENTAL_NET" == "true" ]; then
    for name in net_ethernet net_ip net_udp net_tcp net_dhcp; do
        $AS $ASFLAGS -o "$BUILD_DIR/${name}.o" "$BUILD_DIR/${name}.s"
        echo "  build/${name}.s"
    done
fi

# Pico W WiFi driver
HAS_WIFI=$(cat "$BUILD_DIR/has_wifi.txt" 2>/dev/null || echo "false")
if [ "$HAS_WIFI" == "true" ] && [ -f "$BUILD_DIR/rp2040_wifi.s" ]; then
    $AS $ASFLAGS -o "$BUILD_DIR/rp2040_wifi.o" "$BUILD_DIR/rp2040_wifi.s"
    echo "  build/rp2040_wifi.s"
fi

# User programs
if [ -f "$BUILD_DIR/user_programs.txt" ]; then
    while read -r progname; do
        if [ -f "$BUILD_DIR/${progname}.s" ]; then
            $AS $ASFLAGS -o "$BUILD_DIR/${progname}.o" "$BUILD_DIR/${progname}.s"
            echo "  build/${progname}.s"
        fi
    done < "$BUILD_DIR/user_programs.txt"
fi

# Test framework
if [ -f "$BUILD_DIR/tests_framework.s" ]; then
    $AS $ASFLAGS -o "$BUILD_DIR/tests_framework.o" "$BUILD_DIR/tests_framework.s"
    echo "  build/tests_framework.s"
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

# Core libraries (always included)
OBJS="$OBJS $BUILD_DIR/memory.o $BUILD_DIR/string.o $BUILD_DIR/iolib.o $BUILD_DIR/peripherals.o"
OBJS="$OBJS $BUILD_DIR/shell.o $BUILD_DIR/devtools.o"
OBJS="$OBJS $BUILD_DIR/mathlib.o $BUILD_DIR/sensors.o $BUILD_DIR/motors.o"

# UI libraries (only for full builds)
if [ "$MINIMAL_BUILD" != "true" ]; then
    OBJS="$OBJS $BUILD_DIR/vtnext.o $BUILD_DIR/de.o $BUILD_DIR/widgets.o"
fi

# Hardware libraries
OBJS="$OBJS $BUILD_DIR/i2c.o $BUILD_DIR/spi.o"

# Control libraries
OBJS="$OBJS $BUILD_DIR/fsm.o $BUILD_DIR/pid.o $BUILD_DIR/filters.o"

# Debug/profiling libraries
OBJS="$OBJS $BUILD_DIR/trace.o $BUILD_DIR/profiler.o $BUILD_DIR/memtrack.o $BUILD_DIR/breakpoint.o"

# Graphics library (only for full builds)
if [ "$MINIMAL_BUILD" != "true" ]; then
    OBJS="$OBJS $BUILD_DIR/gfx_color.o $BUILD_DIR/gfx_framebuffer.o $BUILD_DIR/gfx_draw.o"
fi

# Experimental native networking stack (opt-in only)
if [ "$EXPERIMENTAL_NET" == "true" ]; then
    OBJS="$OBJS $BUILD_DIR/net_ethernet.o $BUILD_DIR/net_ip.o $BUILD_DIR/net_udp.o $BUILD_DIR/net_tcp.o $BUILD_DIR/net_dhcp.o"
fi

# Pico W WiFi driver
if [ "$HAS_WIFI" == "true" ] && [ -f "$BUILD_DIR/rp2040_wifi.o" ]; then
    OBJS="$OBJS $BUILD_DIR/rp2040_wifi.o"
fi

# User programs
if [ -f "$BUILD_DIR/user_programs.txt" ]; then
    while read -r progname; do
        if [ -f "$BUILD_DIR/${progname}.o" ]; then
            OBJS="$OBJS $BUILD_DIR/${progname}.o"
        fi
    done < "$BUILD_DIR/user_programs.txt"
fi

# Test framework
if [ -f "$BUILD_DIR/tests_framework.o" ]; then
    OBJS="$OBJS $BUILD_DIR/tests_framework.o"
fi

# Test files
if [ -f "$BUILD_DIR/test_files.txt" ]; then
    while read -r testname; do
        if [ -f "$BUILD_DIR/${testname}.o" ]; then
            OBJS="$OBJS $BUILD_DIR/${testname}.o"
        fi
    done < "$BUILD_DIR/test_files.txt"
fi

# Link with optional libgcc for hardware targets
if [ -n "$LINK_LIBS" ]; then
    $LD -T "$LINKER_SCRIPT" -o "$BUILD_DIR/pynux.elf" $OBJS $LINK_LIBS
else
    $LD -T "$LINKER_SCRIPT" -o "$BUILD_DIR/pynux.elf" $OBJS
fi
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
