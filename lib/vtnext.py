# Pynux VTNext Graphics Library
#
# VTNext protocol for graphical terminal over serial.
# Protocol: ESC ] vtn ; <command> ; <params> BEL
#
# Commands:
#   clear - Clear screen or region
#   rect  - Draw rectangle
#   circle - Draw circle
#   line  - Draw line
#   text  - Draw text
#   viewport - Set viewport size
#   input - Set input mode (raw/normal)
#   cursor - Show/hide cursor

from lib.io import uart_putc

# Output buffer for batching commands
VTN_BUF_SIZE: int32 = 4096
vtn_buffer: Array[4096, uint8]
vtn_buf_pos: int32 = 0

# Escape codes
ESC: int32 = 27
BEL: int32 = 7

# Flush buffer to UART
def vtn_flush():
    i: int32 = 0
    while i < vtn_buf_pos:
        uart_putc(cast[char](vtn_buffer[i]))
        i = i + 1
    vtn_buf_pos = 0

# Write byte to buffer
def vtn_write_byte(b: int32):
    if vtn_buf_pos >= VTN_BUF_SIZE - 1:
        vtn_flush()
    vtn_buffer[vtn_buf_pos] = cast[uint8](b)
    vtn_buf_pos = vtn_buf_pos + 1

# Write string to buffer
def vtn_write_str(s: Ptr[uint8]):
    i: int32 = 0
    while s[i] != 0:
        vtn_write_byte(cast[int32](s[i]))
        i = i + 1

# Write integer to buffer
def vtn_write_int(n: int32):
    if n < 0:
        vtn_write_byte(45)  # '-'
        n = -n
    if n == 0:
        vtn_write_byte(48)  # '0'
        return

    # Build digits in reverse
    temp: int32 = 0
    count: int32 = 0
    while n > 0:
        temp = temp * 10 + (n % 10)
        n = n / 10
        count = count + 1

    # Output digits
    while count > 0:
        vtn_write_byte(48 + (temp % 10))
        temp = temp / 10
        count = count - 1

# Begin VTNext command
def vtn_begin_cmd(cmd: Ptr[uint8]):
    vtn_write_byte(ESC)
    vtn_write_byte(93)  # ']'
    vtn_write_str("vtn;")
    vtn_write_str(cmd)
    vtn_write_byte(59)  # ';'

# End command
def vtn_end_cmd():
    vtn_write_byte(BEL)

# Separator
def vtn_sep():
    vtn_write_byte(59)  # ';'

# ============================================================================
# VTNext Commands
# ============================================================================

# Initialize raw input mode
def vtn_init_raw():
    vtn_begin_cmd("input")
    vtn_write_str("raw")
    vtn_end_cmd()
    vtn_flush()

# Initialize normal input mode
def vtn_init_normal():
    vtn_begin_cmd("input")
    vtn_write_str("normal")
    vtn_end_cmd()
    vtn_flush()

# Hide cursor
def vtn_cursor_hide():
    vtn_begin_cmd("cursor")
    vtn_write_str("hide")
    vtn_end_cmd()

# Show cursor
def vtn_cursor_show():
    vtn_begin_cmd("cursor")
    vtn_write_str("show")
    vtn_end_cmd()

# Set viewport size
def vtn_viewport(w: int32, h: int32):
    vtn_begin_cmd("viewport")
    vtn_write_int(w)
    vtn_sep()
    vtn_write_int(h)
    vtn_end_cmd()

# Clear screen with color
def vtn_clear(r: int32, g: int32, b: int32, a: int32):
    vtn_begin_cmd("clear")
    vtn_write_int(r)
    vtn_sep()
    vtn_write_int(g)
    vtn_sep()
    vtn_write_int(b)
    vtn_sep()
    vtn_write_int(a)
    vtn_end_cmd()

# Clear region
def vtn_clear_region(x: int32, y: int32, w: int32, h: int32, r: int32, g: int32, b: int32, a: int32):
    vtn_begin_cmd("clear")
    vtn_write_int(x)
    vtn_sep()
    vtn_write_int(y)
    vtn_sep()
    vtn_write_int(w)
    vtn_sep()
    vtn_write_int(h)
    vtn_sep()
    vtn_write_int(r)
    vtn_sep()
    vtn_write_int(g)
    vtn_sep()
    vtn_write_int(b)
    vtn_sep()
    vtn_write_int(a)
    vtn_end_cmd()

# Draw filled rectangle
def vtn_rect(x: int32, y: int32, w: int32, h: int32, r: int32, g: int32, b: int32, a: int32):
    vtn_begin_cmd("rect")
    vtn_write_int(x)
    vtn_sep()
    vtn_write_int(y)
    vtn_sep()
    vtn_write_int(w)
    vtn_sep()
    vtn_write_int(h)
    vtn_sep()
    vtn_write_int(r)
    vtn_sep()
    vtn_write_int(g)
    vtn_sep()
    vtn_write_int(b)
    vtn_sep()
    vtn_write_int(a)
    vtn_end_cmd()

# Draw rectangle outline
def vtn_rect_outline(x: int32, y: int32, w: int32, h: int32, thickness: int32, r: int32, g: int32, b: int32, a: int32):
    vtn_begin_cmd("rect_outline")
    vtn_write_int(x)
    vtn_sep()
    vtn_write_int(y)
    vtn_sep()
    vtn_write_int(w)
    vtn_sep()
    vtn_write_int(h)
    vtn_sep()
    vtn_write_int(thickness)
    vtn_sep()
    vtn_write_int(r)
    vtn_sep()
    vtn_write_int(g)
    vtn_sep()
    vtn_write_int(b)
    vtn_sep()
    vtn_write_int(a)
    vtn_end_cmd()

# Draw filled circle
def vtn_circle(x: int32, y: int32, radius: int32, r: int32, g: int32, b: int32, a: int32):
    vtn_begin_cmd("circle")
    vtn_write_int(x)
    vtn_sep()
    vtn_write_int(y)
    vtn_sep()
    vtn_write_int(radius)
    vtn_sep()
    vtn_write_int(r)
    vtn_sep()
    vtn_write_int(g)
    vtn_sep()
    vtn_write_int(b)
    vtn_sep()
    vtn_write_int(a)
    vtn_end_cmd()

# Draw line
def vtn_line(x1: int32, y1: int32, x2: int32, y2: int32, thickness: int32, r: int32, g: int32, b: int32, a: int32):
    vtn_begin_cmd("line")
    vtn_write_int(x1)
    vtn_sep()
    vtn_write_int(y1)
    vtn_sep()
    vtn_write_int(x2)
    vtn_sep()
    vtn_write_int(y2)
    vtn_sep()
    vtn_write_int(thickness)
    vtn_sep()
    vtn_write_int(r)
    vtn_sep()
    vtn_write_int(g)
    vtn_sep()
    vtn_write_int(b)
    vtn_sep()
    vtn_write_int(a)
    vtn_end_cmd()

# Draw text
def vtn_text(text: Ptr[uint8], x: int32, y: int32, scale: int32, r: int32, g: int32, b: int32, a: int32):
    vtn_begin_cmd("text")
    vtn_write_int(x)
    vtn_sep()
    vtn_write_int(y)
    vtn_sep()
    vtn_write_int(1)  # z
    vtn_sep()
    vtn_write_int(0)  # rotation
    vtn_sep()
    vtn_write_int(scale)
    vtn_sep()
    vtn_write_int(r)
    vtn_sep()
    vtn_write_int(g)
    vtn_sep()
    vtn_write_int(b)
    vtn_sep()
    vtn_write_int(a)
    vtn_sep()
    vtn_write_byte(34)  # '"'
    vtn_write_str(text)
    vtn_write_byte(34)  # '"'
    vtn_end_cmd()

# Simple text (white, scale 1)
def vtn_print(text: Ptr[uint8], x: int32, y: int32):
    vtn_text(text, x, y, 1, 255, 255, 255, 255)

# Present (flush all commands)
def vtn_present():
    vtn_begin_cmd("present")
    vtn_end_cmd()
    vtn_flush()

# ============================================================================
# High-level helpers
# ============================================================================

# Initialize graphics mode
def vtn_init(width: int32, height: int32):
    vtn_init_raw()
    vtn_viewport(width, height)
    vtn_cursor_hide()
    vtn_clear(0, 0, 0, 255)
    vtn_present()

# Draw colored rectangle (convenience)
def vtn_fill_rect(x: int32, y: int32, w: int32, h: int32, color: int32):
    r: int32 = (color >> 16) & 0xFF
    g: int32 = (color >> 8) & 0xFF
    b: int32 = color & 0xFF
    vtn_rect(x, y, w, h, r, g, b, 255)

# Color constants
VTN_BLACK: int32 = 0x000000
VTN_WHITE: int32 = 0xFFFFFF
VTN_RED: int32 = 0xFF0000
VTN_GREEN: int32 = 0x00FF00
VTN_BLUE: int32 = 0x0000FF
VTN_YELLOW: int32 = 0xFFFF00
VTN_CYAN: int32 = 0x00FFFF
VTN_MAGENTA: int32 = 0xFF00FF
VTN_GRAY: int32 = 0x808080
