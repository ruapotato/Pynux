# grep - print lines matching pattern
# Simple substring match (not regex)

from lib.io import print_str, print_newline, uart_putc, uart_getc
from lib.string import strstr
from lib.memory import alloc

LINE_BUF_SIZE: int32 = 1024

def grep(pattern: Ptr[char]) -> int32:
    # Allocate line buffer
    line: Ptr[char] = cast[Ptr[char]](alloc(LINE_BUF_SIZE))
    line_pos: int32 = 0
    matches: int32 = 0

    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            # Check last line if not empty
            if line_pos > 0:
                line[line_pos] = '\0'
                if strstr(line, pattern) != Ptr[char](0):
                    print_str(line)
                    print_newline()
                    matches = matches + 1
            break

        if c == '\n' or c == '\r':
            line[line_pos] = '\0'
            # Check if line contains pattern
            if strstr(line, pattern) != Ptr[char](0):
                print_str(line)
                print_newline()
                matches = matches + 1
            line_pos = 0
        else:
            if line_pos < LINE_BUF_SIZE - 1:
                line[line_pos] = c
                line_pos = line_pos + 1

    return matches

def main() -> int32:
    print_str("grep: searching for 'hello' (Ctrl+D to end)\n")
    grep("hello")
    return 0
