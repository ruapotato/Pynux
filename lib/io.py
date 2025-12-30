# Pynux I/O Library
#
# Basic I/O primitives for bare-metal ARM.
# Talks directly to UART for console I/O.

# These are implemented in runtime/io.s
extern def uart_init()
extern def uart_putc(c: char)
extern def print_str(s: str)
extern def print_int(n: int32)
extern def print_hex(n: uint32)
extern def print_newline()

# Print a character
def putc(c: char):
    uart_putc(c)

# Print a string with newline
def println(s: str):
    print_str(s)
    print_newline()

# Print formatted integer
def print_num(n: int32):
    print_int(n)

# Print with format (simple version)
# Supports {} placeholders for integers
def printf(fmt: Ptr[char], arg: int32):
    i: int32 = 0
    while fmt[i] != '\0':
        c: char = fmt[i]
        if c == '{' and fmt[i + 1] == '}':
            print_int(arg)
            i = i + 2
        else:
            uart_putc(c)
            i = i + 1

# Read a character from UART (blocking)
extern def uart_getc() -> char

# Check if character available
extern def uart_available() -> bool

# Simple input buffer for reading lines
INPUT_BUF_SIZE: int32 = 256
input_buffer: Array[256, char]
input_pos: int32 = 0

def read_char() -> char:
    return uart_getc()

def read_line() -> str:
    # Read until newline
    input_pos = 0
    while True:
        c: char = uart_getc()
        if c == '\n' or c == '\r':
            input_buffer[input_pos] = '\0'
            print_newline()
            break
        if c == '\b' or c == 127:  # Backspace
            if input_pos > 0:
                input_pos = input_pos - 1
                print_str("\b \b")  # Erase character
        else:
            if input_pos < INPUT_BUF_SIZE - 1:
                input_buffer[input_pos] = c
                input_pos = input_pos + 1
                uart_putc(c)  # Echo
    return &input_buffer[0]
