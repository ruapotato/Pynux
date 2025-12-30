# uniq - report or omit repeated lines

from lib.io import print_str, print_newline, uart_putc, uart_getc
from lib.string import strcmp, strcpy
from lib.memory import alloc

LINE_BUF_SIZE: int32 = 1024

def uniq():
    current: Ptr[char] = cast[Ptr[char]](alloc(LINE_BUF_SIZE))
    previous: Ptr[char] = cast[Ptr[char]](alloc(LINE_BUF_SIZE))
    pos: int32 = 0
    first_line: bool = True
    previous[0] = '\0'

    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            if pos > 0:
                current[pos] = '\0'
                if first_line or strcmp(current, previous) != 0:
                    print_str(current)
                    print_newline()
            break
        if c == '\n' or c == '\r':
            current[pos] = '\0'
            if first_line or strcmp(current, previous) != 0:
                print_str(current)
                print_newline()
                strcpy(previous, current)
                first_line = False
            pos = 0
        else:
            if pos < LINE_BUF_SIZE - 1:
                current[pos] = c
                pos = pos + 1

def main() -> int32:
    print_str("uniq: filter adjacent duplicates (Ctrl+D to end)\n")
    uniq()
    return 0
