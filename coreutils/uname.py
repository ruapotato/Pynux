# uname - print system information

from lib.io import print_str, print_newline

def uname(all: bool):
    if all:
        print_str("Pynux 0.1.0 ARM Cortex-M3 mps2-an385 QEMU\n")
    else:
        print_str("Pynux\n")

def main() -> int32:
    uname(True)
    return 0
