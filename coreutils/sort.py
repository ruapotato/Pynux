# sort - sort lines of text

from lib.io import print_str, print_newline, uart_putc, uart_getc
from lib.string import strcmp
from lib.memory import alloc

BUF_SIZE: int32 = 8192
MAX_LINES: int32 = 256

def sort():
    buffer: Ptr[char] = cast[Ptr[char]](alloc(BUF_SIZE))
    lines: Ptr[Ptr[char]] = cast[Ptr[Ptr[char]]](alloc(MAX_LINES * 4))

    buf_pos: int32 = 0
    line_count: int32 = 0
    current_line_start: int32 = 0

    # Read all input
    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            if buf_pos > current_line_start:
                buffer[buf_pos] = '\0'
                if line_count < MAX_LINES:
                    lines[line_count] = &buffer[current_line_start]
                    line_count = line_count + 1
            break
        if c == '\n' or c == '\r':
            buffer[buf_pos] = '\0'
            buf_pos = buf_pos + 1
            if line_count < MAX_LINES:
                lines[line_count] = &buffer[current_line_start]
                line_count = line_count + 1
            current_line_start = buf_pos
        else:
            if buf_pos < BUF_SIZE - 1:
                buffer[buf_pos] = c
                buf_pos = buf_pos + 1

    # Bubble sort (simple but works for small inputs)
    i: int32 = 0
    while i < line_count - 1:
        j: int32 = 0
        while j < line_count - i - 1:
            if strcmp(lines[j], lines[j + 1]) > 0:
                temp: Ptr[char] = lines[j]
                lines[j] = lines[j + 1]
                lines[j + 1] = temp
            j = j + 1
        i = i + 1

    # Print sorted lines
    i = 0
    while i < line_count:
        print_str(lines[i])
        print_newline()
        i = i + 1

def main() -> int32:
    print_str("sort: sorting lines (Ctrl+D to end)\n")
    sort()
    return 0
