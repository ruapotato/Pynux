# Pynux I/O Library
#
# Basic I/O primitives for bare-metal ARM Cortex-M3.
# Talks directly to UART for console I/O.

# UART register base address
UART_BASE: uint32 = 0x40004000

# UART register offsets
UART_DATA_OFFSET: uint32 = 0x00
UART_STATUS_OFFSET: uint32 = 0x04
UART_CTRL_OFFSET: uint32 = 0x08

# UART status register bits
UART_STATUS_TX_FULL: uint32 = 0x01
UART_STATUS_RX_EMPTY: uint32 = 0x02

# Volatile pointers for direct UART register access (hardware I/O)
UART_DATA: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](UART_BASE)
UART_STATUS: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](UART_BASE + 4)
UART_CTRL: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](UART_BASE + 8)

# These are implemented in runtime/io.s
extern def uart_init()
extern def print_str(s: str)
extern def print_int(n: int32)
extern def print_hex(n: uint32)
extern def print_newline()

# Low-level UART character output using volatile register access
def uart_putc(c: char):
    # Wait until TX FIFO is not full
    while (*UART_STATUS & UART_STATUS_TX_FULL) != 0:
        pass
    # Memory barrier before write to ensure ordering
    dmb()
    # Write character to data register
    *UART_DATA = cast[uint32](c)
    # Memory barrier after write
    dmb()

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

# Low-level UART character input using volatile register access
def uart_getc() -> char:
    # Wait until RX FIFO is not empty
    while (*UART_STATUS & UART_STATUS_RX_EMPTY) != 0:
        pass
    # Memory barrier before read
    dmb()
    # Read character from data register
    c: char = cast[char](*UART_DATA & 0xFF)
    # Memory barrier after read
    dmb()
    return c

# Check if character available (non-blocking)
def uart_available() -> bool:
    # Memory barrier to ensure fresh read
    dmb()
    return (*UART_STATUS & UART_STATUS_RX_EMPTY) == 0

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
