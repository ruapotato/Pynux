# tail - output last part of input
# For bare metal: buffers last N lines

from lib.io import print_str, print_newline, uart_putc, uart_getc
from lib.memory import alloc

# Buffer size
TAIL_BUF_SIZE: int32 = 4096

def tail(n_lines: int32) -> int32:
    # Allocate circular buffer
    buffer: Ptr[char] = cast[Ptr[char]](alloc(TAIL_BUF_SIZE))
    line_starts: Ptr[int32] = cast[Ptr[int32]](alloc(256 * 4))  # Up to 256 lines

    buf_pos: int32 = 0
    line_count: int32 = 0
    current_line_start: int32 = 0

    # Read all input
    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            break

        if buf_pos < TAIL_BUF_SIZE:
            buffer[buf_pos] = c
            buf_pos = buf_pos + 1

            if c == '\n' or c == '\r':
                if line_count < 256:
                    line_starts[line_count] = current_line_start
                    line_count = line_count + 1
                current_line_start = buf_pos

    # Mark end of last line if not newline-terminated
    if buf_pos > 0 and buffer[buf_pos - 1] != '\n':
        if line_count < 256:
            line_starts[line_count] = current_line_start
            line_count = line_count + 1

    # Print last n_lines
    start_line: int32 = line_count - n_lines
    if start_line < 0:
        start_line = 0

    i: int32 = start_line
    while i < line_count:
        line_start: int32 = line_starts[i]
        # Find line end
        j: int32 = line_start
        while j < buf_pos and buffer[j] != '\n':
            uart_putc(buffer[j])
            j = j + 1
        print_newline()
        i = i + 1

    return 0

def main() -> int32:
    print_str("tail: last 10 lines (Ctrl+D to end)\n")
    tail(10)
    return 0
