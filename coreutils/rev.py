# rev - reverse lines characterwise

from lib.io import print_str, print_newline, uart_putc, uart_getc
from lib.memory import alloc

LINE_BUF_SIZE: int32 = 1024

def rev_line(line: Ptr[char], length: int32):
    i: int32 = length - 1
    while i >= 0:
        uart_putc(line[i])
        i = i - 1
    print_newline()

def rev():
    line: Ptr[char] = cast[Ptr[char]](alloc(LINE_BUF_SIZE))
    pos: int32 = 0

    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            if pos > 0:
                rev_line(line, pos)
            break
        if c == '\n' or c == '\r':
            rev_line(line, pos)
            pos = 0
        else:
            if pos < LINE_BUF_SIZE - 1:
                line[pos] = c
                pos = pos + 1

def main() -> int32:
    print_str("rev: reversing lines (Ctrl+D to end)\n")
    rev()
    return 0
