# Pynux

**GNU for microcontrollers. Python syntax. Native speed.**

Pynux is a Python-syntax systems language that compiles to native ARM. Run `cat`, `ls`, `grep`, and `sh` on a $4 Raspberry Pi Pico.

## What is this?

- **Python syntax** you already know
- **Compiles to native ARM** Thumb-2 (Cortex-M)
- **Coreutils** - cat, ls, grep, echo, wc, head, tail, sh
- **VTNext** - graphical terminal over USB serial
- **Not interpreted** - real compiled code

## Quick Start

```bash
# Install
pip install -e .

# Compile
pynux compile examples/hello.py -o hello.elf

# Run in QEMU
qemu-system-arm -M mps2-an385 -nographic -kernel hello.elf
```

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
lib/            # Pynux standard library
coreutils/      # cat, ls, grep, sh, etc.
vtnext/         # Graphical terminal renderer
```

## License

GPL-3.0 - See [LICENSE](LICENSE)
