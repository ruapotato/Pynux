# cut - remove sections from lines
# Simple: cut first N characters

from lib.io import print_str, print_newline, uart_putc, uart_getc

def cut_chars(n: int32):
    count: int32 = 0

    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            break
        if c == '\n' or c == '\r':
            print_newline()
            count = 0
        else:
            if count < n:
                uart_putc(c)
            count = count + 1

def main() -> int32:
    print_str("cut: first 10 chars per line (Ctrl+D to end)\n")
    cut_chars(10)
    return 0
