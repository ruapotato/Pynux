# Pynux I/O Library
#
# Basic I/O primitives for bare-metal ARM Cortex-M3.
# Talks directly to UART for console I/O.

# ============================================================================
# UART hardware registers
# ============================================================================

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
extern def uart_putc(c: char)
extern def uart_getc() -> char
extern def uart_available() -> bool

# ============================================================================
# Console output abstraction
# ============================================================================
# This allows output to be redirected (e.g., to DE terminal instead of UART)

# Console mode: 0 = UART (direct), 1 = buffered (for DE capture)
console_mode: int32 = 0

# Output buffer for DE mode
console_buf: Array[512, char]
console_buf_pos: int32 = 0

def console_putc(c: char):
    """Output a character to console (UART or DE buffer based on mode)."""
    global console_buf_pos
    if console_mode == 0:
        uart_putc(c)
    else:
        # Buffer for DE capture
        if console_buf_pos < 510:
            console_buf[console_buf_pos] = c
            console_buf_pos = console_buf_pos + 1
            console_buf[console_buf_pos] = '\0'

def console_puts(s: Ptr[char]):
    """Output a string to console."""
    i: int32 = 0
    while s[i] != '\0':
        console_putc(s[i])
        i = i + 1

def console_print_int(n: int32):
    """Output an integer to console."""
    if n == 0:
        console_putc('0')
        return
    if n < 0:
        console_putc('-')
        n = -n
    # Build digits in reverse
    digits: Array[12, char]
    i: int32 = 0
    while n > 0:
        digits[i] = cast[char](48 + (n % 10))
        n = n / 10
        i = i + 1
    # Output in correct order
    while i > 0:
        i = i - 1
        console_putc(digits[i])

def console_set_mode(mode: int32):
    """Set console mode: 0=UART, 1=buffered for DE."""
    global console_mode
    console_mode = mode

def console_flush() -> Ptr[char]:
    """Get buffered output and reset. Returns pointer to buffer."""
    global console_buf_pos
    console_buf[console_buf_pos] = '\0'
    console_buf_pos = 0
    return &console_buf[0]

def console_has_output() -> bool:
    """Check if there's buffered output."""
    return console_buf_pos > 0

# ============================================================================
# Helper print functions
# ============================================================================

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

# ============================================================================
# Line input
# ============================================================================

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
