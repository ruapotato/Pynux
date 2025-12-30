# Pynux

**GNU for microcontrollers. Python syntax. Native speed.**

Pynux is a Python-syntax systems language that compiles to native ARM. Run `cat`, `ls`, `grep`, and `sh` on a $4 Raspberry Pi Pico.

## What is this?

- **Python syntax** you already know
- **Compiles to native ARM** Thumb-2 (Cortex-M)
- **100+ shell commands** - Full Unix-like environment
- **VTNext** - Graphical desktop over USB serial
- **Not interpreted** - Real compiled code

## Quick Start

```bash
# Build
./build.sh

# Run in QEMU with VTNext graphical terminal
python vtnext/renderer.py &
./boot_vm.sh
```

## Shell Commands

### File Operations
`ls` `cat` `cp` `rm` `mkdir` `touch` `stat` `head` `tail`

### Text Processing
`grep` `sort` `uniq` `wc` `nl` `rev` `tac` `tr` `fold` `cut` `xxd` `strings`

### System
`uname` `hostname` `whoami` `id` `uptime` `free` `ps` `df` `env`

### Shell Builtins
`cd` `pwd` `echo` `sleep` `clear` `help` `exit`

### Utilities
`cal` `date` `seq` `factor` `basename` `dirname` `true` `false` `yes`

## Example

```python
# hello.py
from lib.io import print_str

def main() -> int32:
    print_str("Hello from Pynux!\n")
    return 0
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Pynux Desktop Environment                              │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────┐   │
│  │ Terminal                                        │   │
│  │ pynux:/> ls                                     │   │
│  │ dev/  etc/  home/  tmp/                         │   │
│  │ pynux:/> grep hello file.txt                    │   │
│  │ hello world                                     │   │
│  │ pynux:/> _                                      │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
│  Status: Ready                          Heap: 12KB     │
└─────────────────────────────────────────────────────────┘
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
lib/            # Standard library (io, string, memory, vtnext, shell, de)
coreutils/      # Standalone command implementations
vtnext/         # Graphical terminal renderer (pygame)
```

## Building

```bash
# Requirements
sudo apt install gcc-arm-none-eabi qemu-system-arm python3-pygame

# Build
./build.sh

# Run (text mode)
qemu-system-arm -M mps2-an385 -nographic -kernel build/pynux.elf

# Run (graphical mode)
python vtnext/renderer.py &
./boot_vm.sh
```

## Memory

- 16KB heap (bump allocator)
- ~80KB code
- RAMFS for files

## License

GPL-3.0 - See [LICENSE](LICENSE)
