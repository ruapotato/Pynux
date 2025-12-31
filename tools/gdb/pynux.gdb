# Pynux OS GDB Debug Script
# Main entry point for Pynux debugging
#
# Usage: source tools/gdb/pynux.gdb

# Set up useful defaults for ARM debugging
set confirm off
set pagination off
set print pretty on
set print array on
set print array-indexes on
set disassembly-flavor intel
set mem inaccessible-by-default off

# ARM Cortex-M specific settings
set $cpsr = 0
set $xpsr = 0

# Load helper scripts
set $gdb_scripts_dir = "tools/gdb"

# Source register helpers
source tools/gdb/registers.gdb

# Source memory helpers
source tools/gdb/memory.gdb

# Source breakpoint helpers
source tools/gdb/breakpoints.gdb

# Load Python extensions
python
import sys
import os

# Add the gdb scripts directory to Python path
gdb_dir = os.path.join(os.getcwd(), "tools/gdb")
if gdb_dir not in sys.path:
    sys.path.insert(0, gdb_dir)

# Import pretty printers
try:
    import pynux_printers
    pynux_printers.register_printers(None)
    print("Pynux pretty printers loaded")
except ImportError as e:
    print(f"Warning: Could not load pynux_printers: {e}")

# Import custom commands
try:
    import pynux_commands
    print("Pynux commands loaded")
except ImportError as e:
    print(f"Warning: Could not load pynux_commands: {e}")
end

# -----------------------------------------------------------------------------
# Connection Commands
# -----------------------------------------------------------------------------

define pynux-connect-qemu
    if $argc == 0
        target remote localhost:1234
    else
        target remote $arg0
    end
    echo Connected to QEMU gdbserver\n
    # Load symbol file if available
    if $_shell("test -f kernel.elf") == 0
        file kernel.elf
        echo Loaded kernel.elf symbols\n
    end
    # Show initial state
    info registers
end
document pynux-connect-qemu
Connect to QEMU gdbserver.
Usage: pynux-connect-qemu [host:port]
Default: localhost:1234
end

define pynux-connect-openocd
    if $argc == 0
        target extended-remote localhost:3333
    else
        target extended-remote $arg0
    end
    echo Connected to OpenOCD\n
    # Reset and halt target
    monitor reset halt
    # Load symbol file if available
    if $_shell("test -f kernel.elf") == 0
        file kernel.elf
        echo Loaded kernel.elf symbols\n
    end
    info registers
end
document pynux-connect-openocd
Connect to OpenOCD gdbserver.
Usage: pynux-connect-openocd [host:port]
Default: localhost:3333
end

# -----------------------------------------------------------------------------
# Target Control Commands
# -----------------------------------------------------------------------------

define pynux-reset
    echo Resetting target...\n
    # Try OpenOCD reset first
    monitor reset halt
    echo Target reset complete\n
end
document pynux-reset
Reset the target processor.
Works with OpenOCD. For QEMU, restart QEMU instead.
end

define pynux-halt
    monitor halt
    echo Target halted\n
end
document pynux-halt
Halt the target processor.
end

define pynux-resume
    continue
end
document pynux-resume
Resume target execution.
end

# -----------------------------------------------------------------------------
# Quick Debug Commands
# -----------------------------------------------------------------------------

define pynux-status
    echo === Pynux Debug Status ===\n
    echo \nRegisters:\n
    info registers
    echo \nBacktrace:\n
    backtrace
    echo \nCurrent instruction:\n
    x/5i $pc
end
document pynux-status
Show current debugging status including registers, backtrace, and current instruction.
end

define pynux-where
    echo Current location:\n
    info line *$pc
    echo \nDisassembly:\n
    x/10i $pc-10
    echo --> \n
    x/1i $pc
    echo \n
    x/5i $pc+4
end
document pynux-where
Show current execution location with surrounding disassembly.
end

# -----------------------------------------------------------------------------
# Initialization
# -----------------------------------------------------------------------------

echo \n
echo =============================================\n
echo   Pynux OS GDB Debug Environment Loaded\n
echo =============================================\n
echo \n
echo Connection commands:\n
echo   pynux-connect-qemu    - Connect to QEMU (localhost:1234)\n
echo   pynux-connect-openocd - Connect to OpenOCD (localhost:3333)\n
echo \n
echo Target commands:\n
echo   pynux-reset           - Reset target\n
echo   pynux-status          - Show debug status\n
echo \n
echo Register commands:\n
echo   arm-regs              - Print all ARM registers\n
echo   arm-cpsr              - Decode CPSR/xPSR flags\n
echo   arm-stack             - Show stack contents\n
echo   arm-fault             - Decode fault registers\n
echo   arm-nvic              - Show NVIC status\n
echo   arm-systick           - Show SysTick status\n
echo \n
echo Memory commands:\n
echo   mem-dump <addr> <len> - Hex dump memory\n
echo   mem-regions           - Show memory map\n
echo   periph-dump <base>    - Dump peripheral registers\n
echo \n
echo Breakpoint commands:\n
echo   break-fault           - Break on any fault\n
echo   break-hardfault       - Break on HardFault\n
echo   break-malloc-fail     - Break on allocation failure\n
echo   break-assert          - Break on assertion\n
echo \n
echo Pynux commands:\n
echo   pynux-processes       - List all processes\n
echo   pynux-timers          - Show active timers\n
echo   pynux-heap            - Show heap status\n
echo   pynux-tasks           - Show scheduler state\n
echo   pynux-trace           - Show trace buffer\n
echo \n
echo Type 'help <command>' for detailed usage.\n
echo \n
