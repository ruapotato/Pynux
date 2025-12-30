# banner - print large ASCII art text

from lib.io import print_str, print_newline, uart_putc

# Simple 5x5 font for A-Z and 0-9
def print_char_line(c: char, line: int32):
    # Very simplified - just print the character 5 times
    i: int32 = 0
    while i < 5:
        if c >= 'A' and c <= 'Z':
            uart_putc(c)
        elif c >= 'a' and c <= 'z':
            uart_putc(cast[char](cast[int32](c) - 32))  # uppercase
        elif c >= '0' and c <= '9':
            uart_putc(c)
        elif c == ' ':
            uart_putc(' ')
        else:
            uart_putc('#')
        i = i + 1
    uart_putc(' ')

def banner(text: Ptr[char]):
    # Print 5 lines for banner effect
    line: int32 = 0
    while line < 5:
        i: int32 = 0
        while text[i] != '\0':
            print_char_line(text[i], line)
            i = i + 1
        print_newline()
        line = line + 1

def main() -> int32:
    banner("PYNUX")
    print_newline()
    banner("ARM")
    return 0
