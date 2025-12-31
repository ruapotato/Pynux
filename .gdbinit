# Pynux OS GDB Initialization File
#
# This file is automatically loaded by GDB when starting in the Pynux directory.
# It sets up the debugging environment for Pynux OS development.
#
# Note: You may need to add this directory to your ~/.gdbinit:
#   add-auto-load-safe-path /path/to/pynux/.gdbinit

# Basic GDB settings
set confirm off
set pagination off
set print pretty on
set print array on
set history save on
set history size 10000
set history filename ~/.gdb_history

# ARM Cortex-M specific settings
set mem inaccessible-by-default off

# Set architecture hints for bare-metal debugging
set architecture arm

# Python path setup for custom commands
python
import sys
import os

# Add tools/gdb to Python path
pynux_gdb_dir = os.path.join(os.getcwd(), "tools/gdb")
if pynux_gdb_dir not in sys.path:
    sys.path.insert(0, pynux_gdb_dir)

print(f"Pynux GDB directory: {pynux_gdb_dir}")
end

# Load the main Pynux debug script
# Check if we're in the right directory first
python
import os
pynux_script = os.path.join(os.getcwd(), "tools/gdb/pynux.gdb")
if os.path.exists(pynux_script):
    gdb.execute(f"source {pynux_script}")
else:
    print(f"Note: Pynux GDB scripts not found at {pynux_script}")
    print("Run 'source tools/gdb/pynux.gdb' after changing to the Pynux directory.")
end

# Default target configuration
# Uncomment and modify as needed:
#
# For QEMU:
# target remote localhost:1234
#
# For OpenOCD:
# target extended-remote localhost:3333
#
# For ST-Link via OpenOCD:
# target extended-remote localhost:3333
# monitor reset halt

# Symbol file
# Uncomment if you have a default location:
# file kernel.elf

# Display startup message
python
print("")
print("Pynux OS GDB Environment")
print("========================")
print("")
print("Quick start:")
print("  pynux-connect-qemu    - Connect to QEMU")
print("  pynux-connect-openocd - Connect to OpenOCD")
print("  pynux-status          - Show debug status")
print("")
print("For help: source tools/gdb/pynux.gdb")
print("")
end
