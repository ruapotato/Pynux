# fold - wrap lines at specified width

from lib.io import print_str, print_newline, uart_putc, uart_getc

def fold(width: int32):
    col: int32 = 0

    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            break
        if c == '\n' or c == '\r':
            print_newline()
            col = 0
        else:
            if col >= width:
                print_newline()
                col = 0
            uart_putc(c)
            col = col + 1

def main() -> int32:
    print_str("fold: wrapping at 40 chars (Ctrl+D to end)\n")
    fold(40)
    return 0
