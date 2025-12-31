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
# Font data stored as hex string for compact representation

_oled_font: Array[475, uint8]  # 95 chars * 5 bytes
_oled_font_initialized: bool = False

# Font data as hex string (2 chars per byte, 475 bytes = 950 chars)
# Split into multiple strings to avoid line length issues
_font_hex_0: Ptr[char] = "000000000000005F00000007000700147F147F14242A7F2A12231308646236495522500005030000001C2241000041221C0014083E081408083E080800503000000808080808006060000020100804023E5149453E00427F4000"
_font_hex_1: Ptr[char] = "42615149462141454B311814127F1027454545393C4A49493001710905033649494936064949291E003636000000563600000814224100141414141400412214080201510906324979413E7E1111117E7F494949363E41414122"
_font_hex_2: Ptr[char] = "7F4141221C7F494949417F090909013E4149497A7F0808087F00417F41002040413F017F081422417F404040407F020C027F7F0408107F3E4141413E7F090909063E4151215E7F09192946464949493101017F01013F4040403F"
_font_hex_3: Ptr[char] = "1F2040201F3F4038403F631408146307087008076151494543007F41410002040810200041417F0004020102044040404040000102040020545454787F484444383844444420384444487F3854545418087E0901020C5252523E"
_font_hex_4: Ptr[char] = "7F0804047800447D40002040443D007F1028440000417F40007C041804787C0804047838444444387C14141408081414187C7C080404084854545420043F4440203C4040207C1C2040201C3C4030403C44281028440C5050503C"
_font_hex_5: Ptr[char] = "4464544C44000836410000007F000000413608001008081008"

def _hex_to_nibble(c: char) -> uint8:
    """Convert hex character to 4-bit value."""
    code: int32 = cast[int32](c)
    if code >= 48 and code <= 57:  # '0'-'9'
        return cast[uint8](code - 48)
    if code >= 65 and code <= 70:  # 'A'-'F'
        return cast[uint8](code - 55)
    if code >= 97 and code <= 102:  # 'a'-'f'
        return cast[uint8](code - 87)
    return 0

def _decode_hex_chunk(hex_str: Ptr[char], start_idx: int32):
    """Decode a hex string chunk into _oled_font array."""
    i: int32 = 0
    while hex_str[i * 2] != '\0' and (start_idx + i) < 475:
        hi: uint8 = _hex_to_nibble(hex_str[i * 2])
        lo: uint8 = _hex_to_nibble(hex_str[i * 2 + 1])
        _oled_font[start_idx + i] = (hi << 4) | lo
        i = i + 1

def _oled_init_font():
    """Initialize simple 5x7 font from hex data."""
    global _oled_font_initialized

    if _oled_font_initialized:
        return

    # Decode each chunk (each chunk is ~95 bytes = 190 hex chars)
    _decode_hex_chunk(_font_hex_0, 0)
    _decode_hex_chunk(_font_hex_1, 95)
    _decode_hex_chunk(_font_hex_2, 190)
    _decode_hex_chunk(_font_hex_3, 285)
    _decode_hex_chunk(_font_hex_4, 380)
    _decode_hex_chunk(_font_hex_5, 475 - 27)  # Last chunk is shorter

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
