# nl - number lines

from lib.io import print_str, print_int, print_newline, uart_putc, uart_getc
from lib.memory import alloc

LINE_BUF_SIZE: int32 = 1024

def nl():
    line: Ptr[char] = cast[Ptr[char]](alloc(LINE_BUF_SIZE))
    pos: int32 = 0
    line_num: int32 = 1

    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            if pos > 0:
                line[pos] = '\0'
                print_int(line_num)
                print_str("\t")
                print_str(line)
                print_newline()
            break
        if c == '\n' or c == '\r':
            line[pos] = '\0'
            print_int(line_num)
            print_str("\t")
            print_str(line)
            print_newline()
            line_num = line_num + 1
            pos = 0
        else:
            if pos < LINE_BUF_SIZE - 1:
                line[pos] = c
                pos = pos + 1

def main() -> int32:
    print_str("nl: numbering lines (Ctrl+D to end)\n")
    nl()
    return 0
