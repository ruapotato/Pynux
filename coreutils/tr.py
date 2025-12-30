# tr - translate characters
# Simple version: tr 'a' 'b' - replace a with b

from lib.io import print_str, uart_putc, uart_getc

def tr(from_char: char, to_char: char):
    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            break
        if c == from_char:
            uart_putc(to_char)
        else:
            uart_putc(c)

def main() -> int32:
    print_str("tr: replacing 'a' with 'X' (Ctrl+D to end)\n")
    tr('a', 'X')
    return 0
