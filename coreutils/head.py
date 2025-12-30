# head - output first part of input
# Usage: head [-n lines]

from lib.io import print_str, print_newline, uart_putc, uart_getc

def head(n_lines: int32) -> int32:
    lines: int32 = 0

    while lines < n_lines:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            break
        uart_putc(c)
        if c == '\n' or c == '\r':
            lines = lines + 1
            if c == '\r':
                uart_putc('\n')

    return 0

def main() -> int32:
    print_str("head: first 10 lines (Ctrl+D to end)\n")
    head(10)
    return 0
