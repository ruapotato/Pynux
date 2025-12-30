# Pynux

**GNU for microcontrollers. Python syntax. Native speed.**

Pynux is a Python-syntax systems language that compiles to native ARM. Run `cat`, `ls`, `grep`, and `sh` on a $4 Raspberry Pi Pico.

## What is this?

- **Python syntax** you already know
- **Compiles to native ARM** Thumb-2 (Cortex-M)
- **Graphical desktop** - Multi-window DE over VTNext protocol
- **Not interpreted** - Real compiled code

## Quick Start

```bash
# Build
./build.sh

# Run in QEMU with VTNext graphical desktop
./boot_vm.sh
```

## Desktop Environment

Pynux includes a graphical desktop environment with:

- **Menu** (ESC) - Launch apps, close windows
- **Terminal** - Full shell with file operations
- **Editor** - Text editor with Ctrl+S save
- **File Manager** - Navigate and open files

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ESC | Toggle menu |
| TAB | Switch windows |
| j/k | Navigate (menu/files) |
| Enter | Select/execute |
| Ctrl+S | Save (editor) |
| Ctrl+C | Cancel (terminal) |

```
┌─────────────────────────────────────────────────────────┐
│ Menu                                                    │
├─────────────────────────────────────────────────────────┤
│ ┌─ Terminal 1 ────────────────────────────────────────┐ │
│ │ Pynux Desktop Environment                          │ │
│ │ ESC=Menu TAB=Switch Ctrl+S=Save(editor)            │ │
│ │                                                     │ │
│ │ pynux:/> ls                                         │ │
│ │ dev/  etc/  home/  tmp/                             │ │
│ │ pynux:/> _                                          │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─ Files: / ─────────┐ ┌─ Editor ────────────────────┐ │
│ │ ..                  │ │                             │ │
│ │ dev/                │ │ (empty)                     │ │
│ │ etc/                │ │                             │ │
│ │ home/               │ └─────────────────────────────┘ │
│ └─────────────────────┘                                 │
├─────────────────────────────────────────────────────────┤
│ Heap: 1234/16384 | Win: 3 | F1:Menu F2:Switch          │
└─────────────────────────────────────────────────────────┘
```

## Shell Commands

### File Operations
`ls` `cat` `cp` `rm` `mkdir` `touch` `stat` `pwd` `cd`

### System
`uname` `hostname` `whoami` `id` `uptime` `free` `ps` `df` `env`

### Utilities
`echo` `write` `clear` `help` `date`

## Example

```python
# hello.py
from lib.io import print_str

def main() -> int32:
    print_str("Hello from Pynux!\n")
    return 0
```

## Target Hardware

| Platform | Status | Notes |
|----------|--------|-------|
| QEMU mps2-an385 | Primary | Cortex-M3, development |
| RP2040 (Pico) | Target | $4, huge community |
| RP2350 (Pico 2) | Future | RISC-V option |

## Project Structure

```
compiler/       # Python 3.10+ compiler (runs on host)
runtime/        # ARM assembly startup code
kernel/         # Kernel, RAMFS, timer
lib/            # Standard library (io, string, memory, vtnext, de)
vtnext/         # Graphical terminal renderer (pygame)
```

## Building

```bash
# Requirements
sudo apt install gcc-arm-none-eabi qemu-system-arm python3-pygame

# Build
./build.sh

# Run (text mode - press 's' at boot)
./build.sh --run

# Run (graphical mode)
./boot_vm.sh
```

## Memory

- 16KB heap (bump allocator)
- ~62KB code
- RAMFS for files

## License

GPL-3.0 - See [LICENSE](LICENSE)
