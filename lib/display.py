# Pynux Display Library
#
# Emulated display drivers for QEMU ARM Cortex-M3.
# Simulates LCD and OLED displays, outputs to console or VTNext.
#
# Displays included:
#   - HD44780 Character LCD (16x2, 20x4)
#   - SSD1306 OLED (128x64 monochrome)
#   - 7-Segment LED Display (1-4 digits)

from lib.io import console_putc, console_puts, console_print_int
from lib.vtnext import vtn_rect, vtn_text, vtn_clear_rect, vtn_present, vtn_flush
from lib.math import abs_int, clamp

# ============================================================================
# Display Output Mode
# ============================================================================

# Output modes
DISPLAY_MODE_CONSOLE: int32 = 0   # Output to console/UART
DISPLAY_MODE_VTNEXT: int32 = 1    # Output to VTNext graphics

_display_mode: int32 = DISPLAY_MODE_CONSOLE

def display_set_mode(mode: int32):
    """Set display output mode.

    Args:
        mode: DISPLAY_MODE_CONSOLE or DISPLAY_MODE_VTNEXT
    """
    global _display_mode
    _display_mode = mode

def display_get_mode() -> int32:
    """Get current display output mode."""
    return _display_mode

# ============================================================================
# HD44780 Character LCD (16x2 or 20x4)
# ============================================================================
# Classic parallel character LCD with 8 custom characters
# Emulates common HD44780-compatible displays

# LCD dimensions
LCD_COLS: int32 = 20
LCD_ROWS: int32 = 4

# LCD state
_lcd_initialized: bool = False
_lcd_cursor_x: int32 = 0
_lcd_cursor_y: int32 = 0
_lcd_cursor_visible: bool = True
_lcd_display_on: bool = True
_lcd_width: int32 = 16
_lcd_height: int32 = 2

# LCD buffer (20x4 max)
_lcd_buffer: Array[80, char]

# Custom characters (8 characters, 8 bytes each for 5x8 pattern)
_lcd_custom: Array[64, uint8]

# VTNext display position for LCD
_lcd_vtn_x: int32 = 10
_lcd_vtn_y: int32 = 10
_lcd_vtn_scale: int32 = 2
_lcd_vtn_fg_r: int32 = 0
_lcd_vtn_fg_g: int32 = 255
_lcd_vtn_fg_b: int32 = 128
_lcd_vtn_bg_r: int32 = 0
_lcd_vtn_bg_g: int32 = 40
_lcd_vtn_bg_b: int32 = 20

def lcd_init(cols: int32, rows: int32):
    """Initialize HD44780 LCD.

    Args:
        cols: Number of columns (16 or 20)
        rows: Number of rows (2 or 4)
    """
    global _lcd_initialized, _lcd_width, _lcd_height
    global _lcd_cursor_x, _lcd_cursor_y, _lcd_display_on, _lcd_cursor_visible

    _lcd_width = clamp(cols, 1, LCD_COLS)
    _lcd_height = clamp(rows, 1, LCD_ROWS)
    _lcd_cursor_x = 0
    _lcd_cursor_y = 0
    _lcd_display_on = True
    _lcd_cursor_visible = True
    _lcd_initialized = True

    # Clear buffer
    lcd_clear()

def lcd_clear():
    """Clear LCD display and reset cursor to home."""
    global _lcd_cursor_x, _lcd_cursor_y

    i: int32 = 0
    while i < 80:
        _lcd_buffer[i] = ' '
        i = i + 1

    _lcd_cursor_x = 0
    _lcd_cursor_y = 0

    # Update display
    _lcd_refresh()

def lcd_home():
    """Move cursor to home position (0, 0)."""
    global _lcd_cursor_x, _lcd_cursor_y
    _lcd_cursor_x = 0
    _lcd_cursor_y = 0

def lcd_set_cursor(col: int32, row: int32):
    """Set cursor position.

    Args:
        col: Column (0 to width-1)
        row: Row (0 to height-1)
    """
    global _lcd_cursor_x, _lcd_cursor_y
    _lcd_cursor_x = clamp(col, 0, _lcd_width - 1)
    _lcd_cursor_y = clamp(row, 0, _lcd_height - 1)

def lcd_cursor_on():
    """Enable cursor visibility."""
    global _lcd_cursor_visible
    _lcd_cursor_visible = True

def lcd_cursor_off():
    """Disable cursor visibility."""
    global _lcd_cursor_visible
    _lcd_cursor_visible = False

def lcd_display_on():
    """Turn display on."""
    global _lcd_display_on
    _lcd_display_on = True
    _lcd_refresh()

def lcd_display_off():
    """Turn display off."""
    global _lcd_display_on
    _lcd_display_on = False
    _lcd_refresh()

def lcd_print_char(c: char):
    """Print a single character at cursor position.

    Args:
        c: Character to print
    """
    global _lcd_cursor_x, _lcd_cursor_y

    if not _lcd_initialized:
        return

    # Calculate buffer position
    pos: int32 = _lcd_cursor_y * LCD_COLS + _lcd_cursor_x
    if pos < 80:
        _lcd_buffer[pos] = c

    # Advance cursor
    _lcd_cursor_x = _lcd_cursor_x + 1
    if _lcd_cursor_x >= _lcd_width:
        _lcd_cursor_x = 0
        _lcd_cursor_y = _lcd_cursor_y + 1
        if _lcd_cursor_y >= _lcd_height:
            _lcd_cursor_y = 0

    _lcd_refresh()

def lcd_print_str(s: Ptr[char]):
    """Print a string starting at cursor position.

    Args:
        s: Null-terminated string to print
    """
    i: int32 = 0
    while s[i] != '\0':
        lcd_print_char(s[i])
        i = i + 1

def lcd_print_int(n: int32):
    """Print an integer at cursor position.

    Args:
        n: Integer to print
    """
    if n == 0:
        lcd_print_char('0')
        return

    if n < 0:
        lcd_print_char('-')
        n = -n

    # Build digits in reverse
    digits: Array[12, char]
    count: int32 = 0
    while n > 0 and count < 11:
        digits[count] = cast[char](48 + (n % 10))
        n = n / 10
        count = count + 1

    # Print in correct order
    while count > 0:
        count = count - 1
        lcd_print_char(digits[count])

def lcd_create_char(index: int32, pattern: Ptr[uint8]):
    """Create a custom character.

    Args:
        index: Character index (0-7)
        pattern: 8-byte pattern (5 bits per row, 8 rows)
    """
    if index < 0 or index > 7:
        return

    base: int32 = index * 8
    i: int32 = 0
    while i < 8:
        _lcd_custom[base + i] = pattern[i]
        i = i + 1

def lcd_write_raw(data: uint8):
    """Write raw data byte to LCD (for custom chars 0-7).

    Args:
        data: Data byte (0-7 for custom chars)
    """
    if data < 8:
        lcd_print_char(cast[char](data))

def lcd_get_char(col: int32, row: int32) -> char:
    """Get character at position.

    Args:
        col: Column
        row: Row

    Returns:
        Character at position
    """
    if col < 0 or col >= _lcd_width or row < 0 or row >= _lcd_height:
        return ' '
    pos: int32 = row * LCD_COLS + col
    return _lcd_buffer[pos]

def lcd_set_vtn_position(x: int32, y: int32):
    """Set VTNext rendering position for LCD.

    Args:
        x: X position in pixels
        y: Y position in pixels
    """
    global _lcd_vtn_x, _lcd_vtn_y
    _lcd_vtn_x = x
    _lcd_vtn_y = y

def lcd_set_vtn_colors(fg_r: int32, fg_g: int32, fg_b: int32, bg_r: int32, bg_g: int32, bg_b: int32):
    """Set VTNext colors for LCD rendering.

    Args:
        fg_r, fg_g, fg_b: Foreground (text) color
        bg_r, bg_g, bg_b: Background color
    """
    global _lcd_vtn_fg_r, _lcd_vtn_fg_g, _lcd_vtn_fg_b
    global _lcd_vtn_bg_r, _lcd_vtn_bg_g, _lcd_vtn_bg_b
    _lcd_vtn_fg_r = fg_r
    _lcd_vtn_fg_g = fg_g
    _lcd_vtn_fg_b = fg_b
    _lcd_vtn_bg_r = bg_r
    _lcd_vtn_bg_g = bg_g
    _lcd_vtn_bg_b = bg_b

def _lcd_refresh():
    """Internal: Refresh LCD display output."""
    if not _lcd_initialized:
        return

    if _display_mode == DISPLAY_MODE_CONSOLE:
        _lcd_refresh_console()
    else:
        _lcd_refresh_vtnext()

def _lcd_refresh_console():
    """Internal: Output LCD to console."""
    # Print top border
    console_putc('+')
    i: int32 = 0
    while i < _lcd_width:
        console_putc('-')
        i = i + 1
    console_putc('+')
    console_putc('\n')

    # Print each row
    row: int32 = 0
    while row < _lcd_height:
        console_putc('|')
        if _lcd_display_on:
            col: int32 = 0
            while col < _lcd_width:
                c: char = lcd_get_char(col, row)
                console_putc(c)
                col = col + 1
        else:
            col: int32 = 0
            while col < _lcd_width:
                console_putc(' ')
                col = col + 1
        console_putc('|')
        console_putc('\n')
        row = row + 1

    # Print bottom border
    console_putc('+')
    i = 0
    while i < _lcd_width:
        console_putc('-')
        i = i + 1
    console_putc('+')
    console_putc('\n')

def _lcd_refresh_vtnext():
    """Internal: Output LCD to VTNext graphics."""
    # Character dimensions (approximate)
    char_w: int32 = 8 * _lcd_vtn_scale
    char_h: int32 = 16 * _lcd_vtn_scale

    # Draw background
    vtn_rect(_lcd_vtn_x - 4, _lcd_vtn_y - 4, _lcd_width * char_w + 8, _lcd_height * char_h + 8, _lcd_vtn_bg_r, _lcd_vtn_bg_g, _lcd_vtn_bg_b, 255)

    if not _lcd_display_on:
        vtn_flush()
        return

    # Draw each row
    line_buf: Array[24, uint8]
    row: int32 = 0
    while row < _lcd_height:
        # Build line string
        col: int32 = 0
        while col < _lcd_width and col < 23:
            line_buf[col] = cast[uint8](lcd_get_char(col, row))
            col = col + 1
        line_buf[col] = 0

        # Draw text
        y: int32 = _lcd_vtn_y + row * char_h
        vtn_text(&line_buf[0], _lcd_vtn_x, y, _lcd_vtn_scale, _lcd_vtn_fg_r, _lcd_vtn_fg_g, _lcd_vtn_fg_b, 255)
        row = row + 1

    vtn_flush()

# ============================================================================
# SSD1306 OLED (128x64 Monochrome)
# ============================================================================
# Monochrome OLED with framebuffer approach
# Each byte represents 8 vertical pixels

# OLED dimensions
OLED_WIDTH: int32 = 128
OLED_HEIGHT: int32 = 64
OLED_PAGES: int32 = 8           # 64 / 8 = 8 pages

# OLED state
_oled_initialized: bool = False
_oled_display_on: bool = True
_oled_inverted: bool = False

# Framebuffer: 128 * 8 = 1024 bytes
# Each byte is a vertical column of 8 pixels
_oled_fb: Array[1024, uint8]

# VTNext position for OLED
_oled_vtn_x: int32 = 10
_oled_vtn_y: int32 = 10
_oled_vtn_scale: int32 = 2
_oled_vtn_fg_r: int32 = 255
_oled_vtn_fg_g: int32 = 255
_oled_vtn_fg_b: int32 = 255

def oled_init():
    """Initialize SSD1306 OLED display."""
    global _oled_initialized, _oled_display_on, _oled_inverted
    _oled_initialized = True
    _oled_display_on = True
    _oled_inverted = False
    oled_clear()

def oled_clear():
    """Clear OLED framebuffer (all pixels off)."""
    i: int32 = 0
    while i < 1024:
        _oled_fb[i] = 0
        i = i + 1

def oled_fill():
    """Fill OLED framebuffer (all pixels on)."""
    i: int32 = 0
    while i < 1024:
        _oled_fb[i] = 0xFF
        i = i + 1

def oled_display_on():
    """Turn OLED display on."""
    global _oled_display_on
    _oled_display_on = True

def oled_display_off():
    """Turn OLED display off."""
    global _oled_display_on
    _oled_display_on = False

def oled_invert(inverted: bool):
    """Set display inversion mode.

    Args:
        inverted: True for inverted display
    """
    global _oled_inverted
    _oled_inverted = inverted

def oled_set_pixel(x: int32, y: int32, on: bool):
    """Set a single pixel.

    Args:
        x: X coordinate (0-127)
        y: Y coordinate (0-63)
        on: True for pixel on, False for off
    """
    if x < 0 or x >= OLED_WIDTH or y < 0 or y >= OLED_HEIGHT:
        return

    page: int32 = y / 8
    bit: int32 = y % 8
    idx: int32 = page * OLED_WIDTH + x

    if on:
        _oled_fb[idx] = _oled_fb[idx] | cast[uint8](1 << bit)
    else:
        _oled_fb[idx] = _oled_fb[idx] & cast[uint8](~(1 << bit))

def oled_get_pixel(x: int32, y: int32) -> bool:
    """Get pixel state.

    Args:
        x: X coordinate (0-127)
        y: Y coordinate (0-63)

    Returns:
        True if pixel is on, False if off
    """
    if x < 0 or x >= OLED_WIDTH or y < 0 or y >= OLED_HEIGHT:
        return False

    page: int32 = y / 8
    bit: int32 = y % 8
    idx: int32 = page * OLED_WIDTH + x

    return (_oled_fb[idx] & cast[uint8](1 << bit)) != 0

def oled_draw_line(x0: int32, y0: int32, x1: int32, y1: int32, on: bool):
    """Draw a line using Bresenham's algorithm.

    Args:
        x0, y0: Start point
        x1, y1: End point
        on: Pixel state
    """
    dx: int32 = abs_int(x1 - x0)
    dy: int32 = -abs_int(y1 - y0)
    sx: int32 = 1 if x0 < x1 else -1
    sy: int32 = 1 if y0 < y1 else -1
    err: int32 = dx + dy

    while True:
        oled_set_pixel(x0, y0, on)
        if x0 == x1 and y0 == y1:
            break
        e2: int32 = 2 * err
        if e2 >= dy:
            err = err + dy
            x0 = x0 + sx
        if e2 <= dx:
            err = err + dx
            y0 = y0 + sy

def oled_draw_hline(x: int32, y: int32, w: int32, on: bool):
    """Draw horizontal line.

    Args:
        x, y: Start point
        w: Width
        on: Pixel state
    """
    i: int32 = 0
    while i < w:
        oled_set_pixel(x + i, y, on)
        i = i + 1

def oled_draw_vline(x: int32, y: int32, h: int32, on: bool):
    """Draw vertical line.

    Args:
        x, y: Start point
        h: Height
        on: Pixel state
    """
    i: int32 = 0
    while i < h:
        oled_set_pixel(x, y + i, on)
        i = i + 1

def oled_draw_rect(x: int32, y: int32, w: int32, h: int32, on: bool):
    """Draw rectangle outline.

    Args:
        x, y: Top-left corner
        w, h: Width and height
        on: Pixel state
    """
    oled_draw_hline(x, y, w, on)
    oled_draw_hline(x, y + h - 1, w, on)
    oled_draw_vline(x, y, h, on)
    oled_draw_vline(x + w - 1, y, h, on)

def oled_fill_rect(x: int32, y: int32, w: int32, h: int32, on: bool):
    """Draw filled rectangle.

    Args:
        x, y: Top-left corner
        w, h: Width and height
        on: Pixel state
    """
    row: int32 = 0
    while row < h:
        oled_draw_hline(x, y + row, w, on)
        row = row + 1

def oled_draw_circle(cx: int32, cy: int32, r: int32, on: bool):
    """Draw circle outline using midpoint algorithm.

    Args:
        cx, cy: Center point
        r: Radius
        on: Pixel state
    """
    x: int32 = r
    y: int32 = 0
    err: int32 = 1 - r

    while x >= y:
        oled_set_pixel(cx + x, cy + y, on)
        oled_set_pixel(cx + y, cy + x, on)
        oled_set_pixel(cx - y, cy + x, on)
        oled_set_pixel(cx - x, cy + y, on)
        oled_set_pixel(cx - x, cy - y, on)
        oled_set_pixel(cx - y, cy - x, on)
        oled_set_pixel(cx + y, cy - x, on)
        oled_set_pixel(cx + x, cy - y, on)

        y = y + 1
        if err < 0:
            err = err + 2 * y + 1
        else:
            x = x - 1
            err = err + 2 * (y - x + 1)

# Simple 5x7 font for OLED
# Each character is 5 columns, each column is 7 bits (LSB at top)
# Only printable ASCII (32-126)

_oled_font: Array[475, uint8]  # 95 chars * 5 bytes
_oled_font_initialized: bool = False

def _oled_init_font():
    """Initialize simple 5x7 font."""
    global _oled_font_initialized

    if _oled_font_initialized:
        return

    # Space (32)
    _oled_font[0] = 0x00
    _oled_font[1] = 0x00
    _oled_font[2] = 0x00
    _oled_font[3] = 0x00
    _oled_font[4] = 0x00
    # ! (33)
    _oled_font[5] = 0x00
    _oled_font[6] = 0x00
    _oled_font[7] = 0x5F
    _oled_font[8] = 0x00
    _oled_font[9] = 0x00
    # " (34)
    _oled_font[10] = 0x00
    _oled_font[11] = 0x07
    _oled_font[12] = 0x00
    _oled_font[13] = 0x07
    _oled_font[14] = 0x00
    # # (35)
    _oled_font[15] = 0x14
    _oled_font[16] = 0x7F
    _oled_font[17] = 0x14
    _oled_font[18] = 0x7F
    _oled_font[19] = 0x14
    # $ (36)
    _oled_font[20] = 0x24
    _oled_font[21] = 0x2A
    _oled_font[22] = 0x7F
    _oled_font[23] = 0x2A
    _oled_font[24] = 0x12
    # % (37)
    _oled_font[25] = 0x23
    _oled_font[26] = 0x13
    _oled_font[27] = 0x08
    _oled_font[28] = 0x64
    _oled_font[29] = 0x62
    # & (38)
    _oled_font[30] = 0x36
    _oled_font[31] = 0x49
    _oled_font[32] = 0x55
    _oled_font[33] = 0x22
    _oled_font[34] = 0x50
    # ' (39)
    _oled_font[35] = 0x00
    _oled_font[36] = 0x05
    _oled_font[37] = 0x03
    _oled_font[38] = 0x00
    _oled_font[39] = 0x00
    # ( (40)
    _oled_font[40] = 0x00
    _oled_font[41] = 0x1C
    _oled_font[42] = 0x22
    _oled_font[43] = 0x41
    _oled_font[44] = 0x00
    # ) (41)
    _oled_font[45] = 0x00
    _oled_font[46] = 0x41
    _oled_font[47] = 0x22
    _oled_font[48] = 0x1C
    _oled_font[49] = 0x00
    # * (42)
    _oled_font[50] = 0x14
    _oled_font[51] = 0x08
    _oled_font[52] = 0x3E
    _oled_font[53] = 0x08
    _oled_font[54] = 0x14
    # + (43)
    _oled_font[55] = 0x08
    _oled_font[56] = 0x08
    _oled_font[57] = 0x3E
    _oled_font[58] = 0x08
    _oled_font[59] = 0x08
    # , (44)
    _oled_font[60] = 0x00
    _oled_font[61] = 0x50
    _oled_font[62] = 0x30
    _oled_font[63] = 0x00
    _oled_font[64] = 0x00
    # - (45)
    _oled_font[65] = 0x08
    _oled_font[66] = 0x08
    _oled_font[67] = 0x08
    _oled_font[68] = 0x08
    _oled_font[69] = 0x08
    # . (46)
    _oled_font[70] = 0x00
    _oled_font[71] = 0x60
    _oled_font[72] = 0x60
    _oled_font[73] = 0x00
    _oled_font[74] = 0x00
    # / (47)
    _oled_font[75] = 0x20
    _oled_font[76] = 0x10
    _oled_font[77] = 0x08
    _oled_font[78] = 0x04
    _oled_font[79] = 0x02
    # 0 (48)
    _oled_font[80] = 0x3E
    _oled_font[81] = 0x51
    _oled_font[82] = 0x49
    _oled_font[83] = 0x45
    _oled_font[84] = 0x3E
    # 1 (49)
    _oled_font[85] = 0x00
    _oled_font[86] = 0x42
    _oled_font[87] = 0x7F
    _oled_font[88] = 0x40
    _oled_font[89] = 0x00
    # 2 (50)
    _oled_font[90] = 0x42
    _oled_font[91] = 0x61
    _oled_font[92] = 0x51
    _oled_font[93] = 0x49
    _oled_font[94] = 0x46
    # 3 (51)
    _oled_font[95] = 0x21
    _oled_font[96] = 0x41
    _oled_font[97] = 0x45
    _oled_font[98] = 0x4B
    _oled_font[99] = 0x31
    # 4 (52)
    _oled_font[100] = 0x18
    _oled_font[101] = 0x14
    _oled_font[102] = 0x12
    _oled_font[103] = 0x7F
    _oled_font[104] = 0x10
    # 5 (53)
    _oled_font[105] = 0x27
    _oled_font[106] = 0x45
    _oled_font[107] = 0x45
    _oled_font[108] = 0x45
    _oled_font[109] = 0x39
    # 6 (54)
    _oled_font[110] = 0x3C
    _oled_font[111] = 0x4A
    _oled_font[112] = 0x49
    _oled_font[113] = 0x49
    _oled_font[114] = 0x30
    # 7 (55)
    _oled_font[115] = 0x01
    _oled_font[116] = 0x71
    _oled_font[117] = 0x09
    _oled_font[118] = 0x05
    _oled_font[119] = 0x03
    # 8 (56)
    _oled_font[120] = 0x36
    _oled_font[121] = 0x49
    _oled_font[122] = 0x49
    _oled_font[123] = 0x49
    _oled_font[124] = 0x36
    # 9 (57)
    _oled_font[125] = 0x06
    _oled_font[126] = 0x49
    _oled_font[127] = 0x49
    _oled_font[128] = 0x29
    _oled_font[129] = 0x1E
    # : (58)
    _oled_font[130] = 0x00
    _oled_font[131] = 0x36
    _oled_font[132] = 0x36
    _oled_font[133] = 0x00
    _oled_font[134] = 0x00
    # 
    (59)
    _oled_font[135] = 0x00
    _oled_font[136] = 0x56
    _oled_font[137] = 0x36
    _oled_font[138] = 0x00
    _oled_font[139] = 0x00
    # < (60)
    _oled_font[140] = 0x08
    _oled_font[141] = 0x14
    _oled_font[142] = 0x22
    _oled_font[143] = 0x41
    _oled_font[144] = 0x00
    # = (61)
    _oled_font[145] = 0x14
    _oled_font[146] = 0x14
    _oled_font[147] = 0x14
    _oled_font[148] = 0x14
    _oled_font[149] = 0x14
    # > (62)
    _oled_font[150] = 0x00
    _oled_font[151] = 0x41
    _oled_font[152] = 0x22
    _oled_font[153] = 0x14
    _oled_font[154] = 0x08
    # ? (63)
    _oled_font[155] = 0x02
    _oled_font[156] = 0x01
    _oled_font[157] = 0x51
    _oled_font[158] = 0x09
    _oled_font[159] = 0x06
    # @ (64)
    _oled_font[160] = 0x32
    _oled_font[161] = 0x49
    _oled_font[162] = 0x79
    _oled_font[163] = 0x41
    _oled_font[164] = 0x3E
    # A (65)
    _oled_font[165] = 0x7E
    _oled_font[166] = 0x11
    _oled_font[167] = 0x11
    _oled_font[168] = 0x11
    _oled_font[169] = 0x7E
    # B (66)
    _oled_font[170] = 0x7F
    _oled_font[171] = 0x49
    _oled_font[172] = 0x49
    _oled_font[173] = 0x49
    _oled_font[174] = 0x36
    # C (67)
    _oled_font[175] = 0x3E
    _oled_font[176] = 0x41
    _oled_font[177] = 0x41
    _oled_font[178] = 0x41
    _oled_font[179] = 0x22
    # D (68)
    _oled_font[180] = 0x7F
    _oled_font[181] = 0x41
    _oled_font[182] = 0x41
    _oled_font[183] = 0x22
    _oled_font[184] = 0x1C
    # E (69)
    _oled_font[185] = 0x7F
    _oled_font[186] = 0x49
    _oled_font[187] = 0x49
    _oled_font[188] = 0x49
    _oled_font[189] = 0x41
    # F (70)
    _oled_font[190] = 0x7F
    _oled_font[191] = 0x09
    _oled_font[192] = 0x09
    _oled_font[193] = 0x09
    _oled_font[194] = 0x01
    # G (71)
    _oled_font[195] = 0x3E
    _oled_font[196] = 0x41
    _oled_font[197] = 0x49
    _oled_font[198] = 0x49
    _oled_font[199] = 0x7A
    # H (72)
    _oled_font[200] = 0x7F
    _oled_font[201] = 0x08
    _oled_font[202] = 0x08
    _oled_font[203] = 0x08
    _oled_font[204] = 0x7F
    # I (73)
    _oled_font[205] = 0x00
    _oled_font[206] = 0x41
    _oled_font[207] = 0x7F
    _oled_font[208] = 0x41
    _oled_font[209] = 0x00
    # J (74)
    _oled_font[210] = 0x20
    _oled_font[211] = 0x40
    _oled_font[212] = 0x41
    _oled_font[213] = 0x3F
    _oled_font[214] = 0x01
    # K (75)
    _oled_font[215] = 0x7F
    _oled_font[216] = 0x08
    _oled_font[217] = 0x14
    _oled_font[218] = 0x22
    _oled_font[219] = 0x41
    # L (76)
    _oled_font[220] = 0x7F
    _oled_font[221] = 0x40
    _oled_font[222] = 0x40
    _oled_font[223] = 0x40
    _oled_font[224] = 0x40
    # M (77)
    _oled_font[225] = 0x7F
    _oled_font[226] = 0x02
    _oled_font[227] = 0x0C
    _oled_font[228] = 0x02
    _oled_font[229] = 0x7F
    # N (78)
    _oled_font[230] = 0x7F
    _oled_font[231] = 0x04
    _oled_font[232] = 0x08
    _oled_font[233] = 0x10
    _oled_font[234] = 0x7F
    # O (79)
    _oled_font[235] = 0x3E
    _oled_font[236] = 0x41
    _oled_font[237] = 0x41
    _oled_font[238] = 0x41
    _oled_font[239] = 0x3E
    # P (80)
    _oled_font[240] = 0x7F
    _oled_font[241] = 0x09
    _oled_font[242] = 0x09
    _oled_font[243] = 0x09
    _oled_font[244] = 0x06
    # Q (81)
    _oled_font[245] = 0x3E
    _oled_font[246] = 0x41
    _oled_font[247] = 0x51
    _oled_font[248] = 0x21
    _oled_font[249] = 0x5E
    # R (82)
    _oled_font[250] = 0x7F
    _oled_font[251] = 0x09
    _oled_font[252] = 0x19
    _oled_font[253] = 0x29
    _oled_font[254] = 0x46
    # S (83)
    _oled_font[255] = 0x46
    _oled_font[256] = 0x49
    _oled_font[257] = 0x49
    _oled_font[258] = 0x49
    _oled_font[259] = 0x31
    # T (84)
    _oled_font[260] = 0x01
    _oled_font[261] = 0x01
    _oled_font[262] = 0x7F
    _oled_font[263] = 0x01
    _oled_font[264] = 0x01
    # U (85)
    _oled_font[265] = 0x3F
    _oled_font[266] = 0x40
    _oled_font[267] = 0x40
    _oled_font[268] = 0x40
    _oled_font[269] = 0x3F
    # V (86)
    _oled_font[270] = 0x1F
    _oled_font[271] = 0x20
    _oled_font[272] = 0x40
    _oled_font[273] = 0x20
    _oled_font[274] = 0x1F
    # W (87)
    _oled_font[275] = 0x3F
    _oled_font[276] = 0x40
    _oled_font[277] = 0x38
    _oled_font[278] = 0x40
    _oled_font[279] = 0x3F
    # X (88)
    _oled_font[280] = 0x63
    _oled_font[281] = 0x14
    _oled_font[282] = 0x08
    _oled_font[283] = 0x14
    _oled_font[284] = 0x63
    # Y (89)
    _oled_font[285] = 0x07
    _oled_font[286] = 0x08
    _oled_font[287] = 0x70
    _oled_font[288] = 0x08
    _oled_font[289] = 0x07
    # Z (90)
    _oled_font[290] = 0x61
    _oled_font[291] = 0x51
    _oled_font[292] = 0x49
    _oled_font[293] = 0x45
    _oled_font[294] = 0x43
    # [ (91)
    _oled_font[295] = 0x00
    _oled_font[296] = 0x7F
    _oled_font[297] = 0x41
    _oled_font[298] = 0x41
    _oled_font[299] = 0x00
    # \ (92)
    _oled_font[300] = 0x02
    _oled_font[301] = 0x04
    _oled_font[302] = 0x08
    _oled_font[303] = 0x10
    _oled_font[304] = 0x20
    # ] (93)
    _oled_font[305] = 0x00
    _oled_font[306] = 0x41
    _oled_font[307] = 0x41
    _oled_font[308] = 0x7F
    _oled_font[309] = 0x00
    # ^ (94)
    _oled_font[310] = 0x04
    _oled_font[311] = 0x02
    _oled_font[312] = 0x01
    _oled_font[313] = 0x02
    _oled_font[314] = 0x04
    # _ (95)
    _oled_font[315] = 0x40
    _oled_font[316] = 0x40
    _oled_font[317] = 0x40
    _oled_font[318] = 0x40
    _oled_font[319] = 0x40
    # ` (96)
    _oled_font[320] = 0x00
    _oled_font[321] = 0x01
    _oled_font[322] = 0x02
    _oled_font[323] = 0x04
    _oled_font[324] = 0x00
    # a (97)
    _oled_font[325] = 0x20
    _oled_font[326] = 0x54
    _oled_font[327] = 0x54
    _oled_font[328] = 0x54
    _oled_font[329] = 0x78
    # b (98)
    _oled_font[330] = 0x7F
    _oled_font[331] = 0x48
    _oled_font[332] = 0x44
    _oled_font[333] = 0x44
    _oled_font[334] = 0x38
    # c (99)
    _oled_font[335] = 0x38
    _oled_font[336] = 0x44
    _oled_font[337] = 0x44
    _oled_font[338] = 0x44
    _oled_font[339] = 0x20
    # d (100)
    _oled_font[340] = 0x38
    _oled_font[341] = 0x44
    _oled_font[342] = 0x44
    _oled_font[343] = 0x48
    _oled_font[344] = 0x7F
    # e (101)
    _oled_font[345] = 0x38
    _oled_font[346] = 0x54
    _oled_font[347] = 0x54
    _oled_font[348] = 0x54
    _oled_font[349] = 0x18
    # f (102)
    _oled_font[350] = 0x08
    _oled_font[351] = 0x7E
    _oled_font[352] = 0x09
    _oled_font[353] = 0x01
    _oled_font[354] = 0x02
    # g (103)
    _oled_font[355] = 0x0C
    _oled_font[356] = 0x52
    _oled_font[357] = 0x52
    _oled_font[358] = 0x52
    _oled_font[359] = 0x3E
    # h (104)
    _oled_font[360] = 0x7F
    _oled_font[361] = 0x08
    _oled_font[362] = 0x04
    _oled_font[363] = 0x04
    _oled_font[364] = 0x78
    # i (105)
    _oled_font[365] = 0x00
    _oled_font[366] = 0x44
    _oled_font[367] = 0x7D
    _oled_font[368] = 0x40
    _oled_font[369] = 0x00
    # j (106)
    _oled_font[370] = 0x20
    _oled_font[371] = 0x40
    _oled_font[372] = 0x44
    _oled_font[373] = 0x3D
    _oled_font[374] = 0x00
    # k (107)
    _oled_font[375] = 0x7F
    _oled_font[376] = 0x10
    _oled_font[377] = 0x28
    _oled_font[378] = 0x44
    _oled_font[379] = 0x00
    # l (108)
    _oled_font[380] = 0x00
    _oled_font[381] = 0x41
    _oled_font[382] = 0x7F
    _oled_font[383] = 0x40
    _oled_font[384] = 0x00
    # m (109)
    _oled_font[385] = 0x7C
    _oled_font[386] = 0x04
    _oled_font[387] = 0x18
    _oled_font[388] = 0x04
    _oled_font[389] = 0x78
    # n (110)
    _oled_font[390] = 0x7C
    _oled_font[391] = 0x08
    _oled_font[392] = 0x04
    _oled_font[393] = 0x04
    _oled_font[394] = 0x78
    # o (111)
    _oled_font[395] = 0x38
    _oled_font[396] = 0x44
    _oled_font[397] = 0x44
    _oled_font[398] = 0x44
    _oled_font[399] = 0x38
    # p (112)
    _oled_font[400] = 0x7C
    _oled_font[401] = 0x14
    _oled_font[402] = 0x14
    _oled_font[403] = 0x14
    _oled_font[404] = 0x08
    # q (113)
    _oled_font[405] = 0x08
    _oled_font[406] = 0x14
    _oled_font[407] = 0x14
    _oled_font[408] = 0x18
    _oled_font[409] = 0x7C
    # r (114)
    _oled_font[410] = 0x7C
    _oled_font[411] = 0x08
    _oled_font[412] = 0x04
    _oled_font[413] = 0x04
    _oled_font[414] = 0x08
    # s (115)
    _oled_font[415] = 0x48
    _oled_font[416] = 0x54
    _oled_font[417] = 0x54
    _oled_font[418] = 0x54
    _oled_font[419] = 0x20
    # t (116)
    _oled_font[420] = 0x04
    _oled_font[421] = 0x3F
    _oled_font[422] = 0x44
    _oled_font[423] = 0x40
    _oled_font[424] = 0x20
    # u (117)
    _oled_font[425] = 0x3C
    _oled_font[426] = 0x40
    _oled_font[427] = 0x40
    _oled_font[428] = 0x20
    _oled_font[429] = 0x7C
    # v (118)
    _oled_font[430] = 0x1C
    _oled_font[431] = 0x20
    _oled_font[432] = 0x40
    _oled_font[433] = 0x20
    _oled_font[434] = 0x1C
    # w (119)
    _oled_font[435] = 0x3C
    _oled_font[436] = 0x40
    _oled_font[437] = 0x30
    _oled_font[438] = 0x40
    _oled_font[439] = 0x3C
    # x (120)
    _oled_font[440] = 0x44
    _oled_font[441] = 0x28
    _oled_font[442] = 0x10
    _oled_font[443] = 0x28
    _oled_font[444] = 0x44
    # y (121)
    _oled_font[445] = 0x0C
    _oled_font[446] = 0x50
    _oled_font[447] = 0x50
    _oled_font[448] = 0x50
    _oled_font[449] = 0x3C
    # z (122)
    _oled_font[450] = 0x44
    _oled_font[451] = 0x64
    _oled_font[452] = 0x54
    _oled_font[453] = 0x4C
    _oled_font[454] = 0x44
    # { (123)
    _oled_font[455] = 0x00
    _oled_font[456] = 0x08
    _oled_font[457] = 0x36
    _oled_font[458] = 0x41
    _oled_font[459] = 0x00
    # | (124)
    _oled_font[460] = 0x00
    _oled_font[461] = 0x00
    _oled_font[462] = 0x7F
    _oled_font[463] = 0x00
    _oled_font[464] = 0x00
    # } (125)
    _oled_font[465] = 0x00
    _oled_font[466] = 0x41
    _oled_font[467] = 0x36
    _oled_font[468] = 0x08
    _oled_font[469] = 0x00
    # ~ (126)
    _oled_font[470] = 0x10
    _oled_font[471] = 0x08
    _oled_font[472] = 0x08
    _oled_font[473] = 0x10
    _oled_font[474] = 0x08

    _oled_font_initialized = True

def oled_draw_char(x: int32, y: int32, c: char, on: bool):
    """Draw a character using 5x7 font.

    Args:
        x, y: Position (top-left of character)
        c: Character to draw (ASCII 32-126)
        on: Pixel state for character
    """
    _oled_init_font()

    code: int32 = cast[int32](c)
    if code < 32 or code > 126:
        code = 32  # Default to space

    idx: int32 = (code - 32) * 5

    col: int32 = 0
    while col < 5:
        bits: uint8 = _oled_font[idx + col]
        row: int32 = 0
        while row < 7:
            if (bits & cast[uint8](1 << row)) != 0:
                oled_set_pixel(x + col, y + row, on)
            else:
                oled_set_pixel(x + col, y + row, not on)
            row = row + 1
        col = col + 1

def oled_draw_string(x: int32, y: int32, s: Ptr[char], on: bool):
    """Draw a string using 5x7 font.

    Args:
        x, y: Starting position
        s: Null-terminated string
        on: Pixel state for characters
    """
    i: int32 = 0
    cx: int32 = x
    while s[i] != '\0':
        oled_draw_char(cx, y, s[i], on)
        cx = cx + 6  # 5 pixels + 1 spacing
        i = i + 1

def oled_set_vtn_position(x: int32, y: int32, scale: int32):
    """Set VTNext rendering position and scale.

    Args:
        x, y: Position in pixels
        scale: Pixel scale factor
    """
    global _oled_vtn_x, _oled_vtn_y, _oled_vtn_scale
    _oled_vtn_x = x
    _oled_vtn_y = y
    _oled_vtn_scale = scale

def oled_set_vtn_color(r: int32, g: int32, b: int32):
    """Set VTNext foreground color for OLED pixels.

    Args:
        r, g, b: Pixel color
    """
    global _oled_vtn_fg_r, _oled_vtn_fg_g, _oled_vtn_fg_b
    _oled_vtn_fg_r = r
    _oled_vtn_fg_g = g
    _oled_vtn_fg_b = b

def oled_update():
    """Update display output (call after drawing operations)."""
    if _display_mode == DISPLAY_MODE_CONSOLE:
        _oled_update_console()
    else:
        _oled_update_vtnext()

def _oled_update_console():
    """Internal: Output OLED to console (simplified)."""
    # Print top border
    console_putc('+')
    i: int32 = 0
    while i < 64:  # Half width for console
        console_putc('-')
        i = i + 1
    console_putc('+')
    console_putc('\n')

    # Print every other row (64 rows -> 32 console lines)
    row: int32 = 0
    while row < 64:
        console_putc('|')
        col: int32 = 0
        while col < 128:
            # Sample every other pixel
            if oled_get_pixel(col, row):
                console_putc('#')
            else:
                console_putc(' ')
            col = col + 2
        console_putc('|')
        console_putc('\n')
        row = row + 2

    # Print bottom border
    console_putc('+')
    i = 0
    while i < 64:
        console_putc('-')
        i = i + 1
    console_putc('+')
    console_putc('\n')

def _oled_update_vtnext():
    """Internal: Output OLED to VTNext graphics."""
    s: int32 = _oled_vtn_scale

    # Clear background
    vtn_rect(_oled_vtn_x - 2, _oled_vtn_y - 2, OLED_WIDTH * s + 4, OLED_HEIGHT * s + 4, 20, 20, 30, 255)

    # Draw pixels
    y: int32 = 0
    while y < OLED_HEIGHT:
        x: int32 = 0
        while x < OLED_WIDTH:
            pixel_on: bool = oled_get_pixel(x, y)
            if _oled_inverted:
                pixel_on = not pixel_on
            if pixel_on:
                vtn_rect(_oled_vtn_x + x * s, _oled_vtn_y + y * s, s, s, _oled_vtn_fg_r, _oled_vtn_fg_g, _oled_vtn_fg_b, 255)
            x = x + 1
        y = y + 1

    vtn_flush()

# ============================================================================
# 7-Segment Display (1-4 digits)
# ============================================================================
# Common anode/cathode 7-segment LED display
# Segments: a(top), b(top-right), c(bot-right), d(bot), e(bot-left), f(top-left), g(middle), dp(decimal)

# 7-segment state
_seg7_initialized: bool = False
_seg7_digits: int32 = 4         # Number of digits
_seg7_value: Array[4, int32]    # Digit values (-1 = blank)
_seg7_dp: Array[4, bool]        # Decimal point per digit

# VTNext position for 7-segment
_seg7_vtn_x: int32 = 10
_seg7_vtn_y: int32 = 10
_seg7_vtn_scale: int32 = 3
_seg7_vtn_r: int32 = 255
_seg7_vtn_g: int32 = 0
_seg7_vtn_b: int32 = 0

# Segment patterns for digits 0-9 and some letters
# Bits: 0=a, 1=b, 2=c, 3=d, 4=e, 5=f, 6=g
_seg7_patterns: Array[16, uint8]

def _seg7_init_patterns():
    """Initialize segment patterns."""
    _seg7_patterns[0] = 0x3F   # 0: abcdef
    _seg7_patterns[1] = 0x06   # 1: bc
    _seg7_patterns[2] = 0x5B   # 2: abdeg
    _seg7_patterns[3] = 0x4F   # 3: abcdg
    _seg7_patterns[4] = 0x66   # 4: bcfg
    _seg7_patterns[5] = 0x6D   # 5: acdfg
    _seg7_patterns[6] = 0x7D   # 6: acdefg
    _seg7_patterns[7] = 0x07   # 7: abc
    _seg7_patterns[8] = 0x7F   # 8: abcdefg
    _seg7_patterns[9] = 0x6F   # 9: abcdfg
    _seg7_patterns[10] = 0x77  # A: abcefg
    _seg7_patterns[11] = 0x7C  # b: cdefg
    _seg7_patterns[12] = 0x39  # C: adef
    _seg7_patterns[13] = 0x5E  # d: bcdeg
    _seg7_patterns[14] = 0x79  # E: adefg
    _seg7_patterns[15] = 0x71  # F: aefg

def seg7_init(num_digits: int32):
    """Initialize 7-segment display.

    Args:
        num_digits: Number of digits (1-4)
    """
    global _seg7_initialized, _seg7_digits

    _seg7_init_patterns()
    _seg7_digits = clamp(num_digits, 1, 4)
    _seg7_initialized = True

    # Clear all digits
    seg7_clear()

def seg7_clear():
    """Clear all digits (blank display)."""
    i: int32 = 0
    while i < 4:
        _seg7_value[i] = -1  # Blank
        _seg7_dp[i] = False
        i = i + 1
    _seg7_refresh()

def seg7_set_digit(pos: int32, value: int32):
    """Set a single digit value.

    Args:
        pos: Digit position (0 = leftmost)
        value: Digit value (0-15 for hex, -1 for blank)
    """
    if pos < 0 or pos >= _seg7_digits:
        return
    _seg7_value[pos] = value
    _seg7_refresh()

def seg7_set_decimal(pos: int32, on: bool):
    """Set decimal point for a digit.

    Args:
        pos: Digit position
        on: True to enable decimal point
    """
    if pos < 0 or pos >= _seg7_digits:
        return
    _seg7_dp[pos] = on
    _seg7_refresh()

def seg7_set_number(n: int32):
    """Set display to show an integer.

    Args:
        n: Number to display (0-9999 for 4 digits)
    """
    # Clear first
    i: int32 = 0
    while i < 4:
        _seg7_value[i] = -1
        i = i + 1

    if n < 0:
        n = -n

    # Fill digits from right
    pos: int32 = _seg7_digits - 1
    while pos >= 0 and n > 0:
        _seg7_value[pos] = n % 10
        n = n / 10
        pos = pos - 1

    # If n was 0, show single 0
    if _seg7_value[_seg7_digits - 1] == -1:
        _seg7_value[_seg7_digits - 1] = 0

    _seg7_refresh()

def seg7_set_number_dp(n: int32, dp_pos: int32):
    """Set display with decimal point.

    Args:
        n: Number to display
        dp_pos: Position of decimal point from right (1 = X.X, 2 = X.XX)
    """
    seg7_set_number(n)
    if dp_pos > 0 and dp_pos < _seg7_digits:
        _seg7_dp[_seg7_digits - 1 - dp_pos] = True
    _seg7_refresh()

def seg7_set_hex(n: int32):
    """Set display to show hexadecimal value.

    Args:
        n: Number to display (0-0xFFFF for 4 digits)
    """
    i: int32 = 0
    while i < 4:
        _seg7_value[i] = -1
        i = i + 1

    pos: int32 = _seg7_digits - 1
    while pos >= 0 and n > 0:
        _seg7_value[pos] = n & 0xF
        n = n >> 4
        pos = pos - 1

    if _seg7_value[_seg7_digits - 1] == -1:
        _seg7_value[_seg7_digits - 1] = 0

    _seg7_refresh()

def seg7_set_vtn_position(x: int32, y: int32, scale: int32):
    """Set VTNext position and scale for 7-segment.

    Args:
        x, y: Position
        scale: Scale factor
    """
    global _seg7_vtn_x, _seg7_vtn_y, _seg7_vtn_scale
    _seg7_vtn_x = x
    _seg7_vtn_y = y
    _seg7_vtn_scale = scale

def seg7_set_vtn_color(r: int32, g: int32, b: int32):
    """Set VTNext color for 7-segment display.

    Args:
        r, g, b: Segment color
    """
    global _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b
    _seg7_vtn_r = r
    _seg7_vtn_g = g
    _seg7_vtn_b = b

def _seg7_refresh():
    """Internal: Refresh 7-segment display."""
    if not _seg7_initialized:
        return

    if _display_mode == DISPLAY_MODE_CONSOLE:
        _seg7_refresh_console()
    else:
        _seg7_refresh_vtnext()

def _seg7_refresh_console():
    """Internal: Output 7-segment to console."""
    # Simple text representation
    console_putc('[')
    i: int32 = 0
    while i < _seg7_digits:
        v: int32 = _seg7_value[i]
        if v < 0:
            console_putc(' ')
        elif v < 10:
            console_putc(cast[char](48 + v))
        else:
            console_putc(cast[char](55 + v))  # A-F
        if _seg7_dp[i]:
            console_putc('.')
        i = i + 1
    console_putc(']')
    console_putc('\n')

def _seg7_refresh_vtnext():
    """Internal: Output 7-segment to VTNext graphics."""
    s: int32 = _seg7_vtn_scale
    digit_w: int32 = 12 * s
    digit_h: int32 = 20 * s
    seg_thick: int32 = 2 * s

    # Background
    vtn_rect(_seg7_vtn_x - 4, _seg7_vtn_y - 4, _seg7_digits * (digit_w + 4) + 4, digit_h + 8, 20, 20, 20, 255)

    i: int32 = 0
    while i < _seg7_digits:
        x: int32 = _seg7_vtn_x + i * (digit_w + 4)
        y: int32 = _seg7_vtn_y
        v: int32 = _seg7_value[i]

        if v >= 0 and v < 16:
            pattern: uint8 = _seg7_patterns[v]

            # Draw segments based on pattern
            # Segment a (top horizontal)
            if (pattern & 0x01) != 0:
                vtn_rect(x + seg_thick, y, digit_w - 2 * seg_thick, seg_thick, _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b, 255)
            # Segment b (top-right vertical)
            if (pattern & 0x02) != 0:
                vtn_rect(x + digit_w - seg_thick, y + seg_thick, seg_thick, digit_h / 2 - seg_thick, _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b, 255)
            # Segment c (bottom-right vertical)
            if (pattern & 0x04) != 0:
                vtn_rect(x + digit_w - seg_thick, y + digit_h / 2, seg_thick, digit_h / 2 - seg_thick, _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b, 255)
            # Segment d (bottom horizontal)
            if (pattern & 0x08) != 0:
                vtn_rect(x + seg_thick, y + digit_h - seg_thick, digit_w - 2 * seg_thick, seg_thick, _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b, 255)
            # Segment e (bottom-left vertical)
            if (pattern & 0x10) != 0:
                vtn_rect(x, y + digit_h / 2, seg_thick, digit_h / 2 - seg_thick, _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b, 255)
            # Segment f (top-left vertical)
            if (pattern & 0x20) != 0:
                vtn_rect(x, y + seg_thick, seg_thick, digit_h / 2 - seg_thick, _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b, 255)
            # Segment g (middle horizontal)
            if (pattern & 0x40) != 0:
                vtn_rect(x + seg_thick, y + digit_h / 2 - seg_thick / 2, digit_w - 2 * seg_thick, seg_thick, _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b, 255)

        # Decimal point
        if _seg7_dp[i]:
            vtn_rect(x + digit_w + s, y + digit_h - seg_thick, seg_thick, seg_thick, _seg7_vtn_r, _seg7_vtn_g, _seg7_vtn_b, 255)

        i = i + 1

    vtn_flush()
