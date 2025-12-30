# tac - reverse lines of input (cat backwards)

from lib.io import print_str, print_newline, uart_putc, uart_getc
from lib.memory import alloc

BUF_SIZE: int32 = 4096
MAX_LINES: int32 = 256

def tac():
    buffer: Ptr[char] = cast[Ptr[char]](alloc(BUF_SIZE))
    line_starts: Ptr[int32] = cast[Ptr[int32]](alloc(MAX_LINES * 4))
    line_ends: Ptr[int32] = cast[Ptr[int32]](alloc(MAX_LINES * 4))

    buf_pos: int32 = 0
    line_count: int32 = 0
    current_line_start: int32 = 0

    # Read all input
    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            break
        if buf_pos < BUF_SIZE:
            buffer[buf_pos] = c
            buf_pos = buf_pos + 1
            if c == '\n':
                if line_count < MAX_LINES:
                    line_starts[line_count] = current_line_start
                    line_ends[line_count] = buf_pos - 1
                    line_count = line_count + 1
                current_line_start = buf_pos

    # Handle last line without newline
    if buf_pos > current_line_start:
        if line_count < MAX_LINES:
            line_starts[line_count] = current_line_start
            line_ends[line_count] = buf_pos
            line_count = line_count + 1

    # Print lines in reverse order
    i: int32 = line_count - 1
    while i >= 0:
        j: int32 = line_starts[i]
        while j < line_ends[i]:
            uart_putc(buffer[j])
            j = j + 1
        print_newline()
        i = i - 1

def main() -> int32:
    print_str("tac: reverse lines (Ctrl+D to end)\n")
    tac()
    return 0
