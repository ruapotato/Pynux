# Pynux Hex Viewer
#
# Display file contents in hexadecimal format with ASCII representation.
# Format: OOOO: HH HH HH HH HH HH HH HH  HH HH HH HH HH HH HH HH  AAAAAAAAAAAAAAAA
#
# 16 bytes per line with scrolling support.

from kernel.ramfs import ramfs_read, ramfs_exists, ramfs_isdir, ramfs_size
from lib.vtnext import vtn_rect, vtn_textline, vtn_clear, vtn_present
from lib.io import console_puts

# Constants
HEX_BYTES_PER_LINE: int32 = 16
HEX_MAX_FILE_SIZE: int32 = 4096  # Max file size to load
HEX_LINES_PER_PAGE: int32 = 24   # Lines visible on screen

# File buffer
hex_file_buf: Array[4096, uint8]
hex_file_size: int32 = 0
hex_scroll_offset: int32 = 0  # Current scroll position (in lines)

# Display state
hex_win_x: int32 = 0
hex_win_y: int32 = 0
hex_win_w: int32 = 800
hex_win_h: int32 = 400

# Output line buffer
hex_line: Array[80, char]

# Hex digits lookup
hex_chars: Array[17, char]

def hex_init_chars():
    """Initialize hex character lookup table."""
    hex_chars[0] = '0'
    hex_chars[1] = '1'
    hex_chars[2] = '2'
    hex_chars[3] = '3'
    hex_chars[4] = '4'
    hex_chars[5] = '5'
    hex_chars[6] = '6'
    hex_chars[7] = '7'
    hex_chars[8] = '8'
    hex_chars[9] = '9'
    hex_chars[10] = 'A'
    hex_chars[11] = 'B'
    hex_chars[12] = 'C'
    hex_chars[13] = 'D'
    hex_chars[14] = 'E'
    hex_chars[15] = 'F'
    hex_chars[16] = '\0'

def hex_byte_to_str(b: int32, out: Ptr[char], pos: int32):
    """Convert byte to 2-char hex string at position."""
    high: int32 = (b >> 4) & 0x0F
    low: int32 = b & 0x0F
    out[pos] = hex_chars[high]
    out[pos + 1] = hex_chars[low]

def hex_offset_to_str(offset: int32, out: Ptr[char], pos: int32):
    """Convert 16-bit offset to 4-char hex string at position."""
    hex_byte_to_str((offset >> 8) & 0xFF, out, pos)
    hex_byte_to_str(offset & 0xFF, out, pos + 2)

def hex_is_printable(c: int32) -> bool:
    """Check if character is printable ASCII."""
    return c >= 32 and c < 127

def hex_format_line(offset: int32, data: Ptr[uint8], count: int32) -> Ptr[char]:
    """Format one line of hex output.

    Format: OOOO: HH HH HH HH HH HH HH HH  HH HH HH HH HH HH HH HH  AAAAAAAAAAAAAAAA
    """
    # Clear line
    i: int32 = 0
    while i < 78:
        hex_line[i] = ' '
        i = i + 1
    hex_line[78] = '\0'

    # Offset (4 hex chars + colon)
    hex_offset_to_str(offset, &hex_line[0], 0)
    hex_line[4] = ':'

    # Hex bytes
    pos: int32 = 6
    i = 0
    while i < count:
        hex_byte_to_str(cast[int32](data[i]), &hex_line[0], pos)
        pos = pos + 3
        # Extra space after 8 bytes
        if i == 7:
            pos = pos + 1
        i = i + 1

    # Fill remaining hex positions with spaces if count < 16
    while i < HEX_BYTES_PER_LINE:
        hex_line[pos] = ' '
        hex_line[pos + 1] = ' '
        pos = pos + 3
        if i == 7:
            pos = pos + 1
        i = i + 1

    # ASCII representation
    ascii_start: int32 = 57  # Position for ASCII part
    i = 0
    while i < count:
        cv: int32 = cast[int32](data[i])
        if hex_is_printable(cv):
            hex_line[ascii_start + i] = cast[char](cv)
        else:
            hex_line[ascii_start + i] = '.'
        i = i + 1

    return &hex_line[0]

def hexview_load(path: Ptr[char]) -> bool:
    """Load file into hex view buffer. Returns True on success."""
    global hex_file_size, hex_scroll_offset

    # Check file exists and is not a directory
    if not ramfs_exists(path):
        console_puts("hexview: File not found\n")
        return False

    if ramfs_isdir(path):
        console_puts("hexview: Cannot view directory\n")
        return False

    # Get file size and read
    fsize: int32 = ramfs_size(path)
    if fsize < 0:
        fsize = 0
    if fsize > HEX_MAX_FILE_SIZE:
        fsize = HEX_MAX_FILE_SIZE

    hex_file_size = ramfs_read(path, &hex_file_buf[0], fsize)
    if hex_file_size < 0:
        hex_file_size = 0
        console_puts("hexview: Read error\n")
        return False

    hex_scroll_offset = 0
    return True

def hexview_total_lines() -> int32:
    """Calculate total number of lines needed for file."""
    if hex_file_size == 0:
        return 0
    return (hex_file_size + HEX_BYTES_PER_LINE - 1) / HEX_BYTES_PER_LINE

def hexview_draw(x: int32, y: int32, w: int32, h: int32):
    """Draw hex view at specified location.

    Args:
        x, y: Top-left corner position
        w, h: Width and height of view area
    """
    global hex_win_x, hex_win_y, hex_win_w, hex_win_h

    hex_win_x = x
    hex_win_y = y
    hex_win_w = w
    hex_win_h = h

    # Background
    vtn_rect(x, y, w, h, 24, 24, 24, 255)

    # Calculate visible lines based on height (16 pixels per line)
    char_h: int32 = 16
    visible_lines: int32 = (h - 8) / char_h
    if visible_lines > HEX_LINES_PER_PAGE:
        visible_lines = HEX_LINES_PER_PAGE

    total_lines: int32 = hexview_total_lines()

    # Draw header
    vtn_textline("OFFS  00 01 02 03 04 05 06 07  08 09 0A 0B 0C 0D 0E 0F   ASCII", x + 4, y + 4, 128, 128, 128)

    # Draw separator line
    vtn_rect(x + 4, y + 20, w - 8, 1, 64, 64, 64, 255)

    # Draw hex lines
    line: int32 = 0
    while line < visible_lines and (hex_scroll_offset + line) < total_lines:
        offset: int32 = (hex_scroll_offset + line) * HEX_BYTES_PER_LINE
        remaining: int32 = hex_file_size - offset
        if remaining > HEX_BYTES_PER_LINE:
            remaining = HEX_BYTES_PER_LINE
        if remaining > 0:
            line_str: Ptr[char] = hex_format_line(offset, &hex_file_buf[offset], remaining)
            vtn_textline(line_str, x + 4, y + 24 + line * char_h, 200, 200, 200)
        line = line + 1

    # Draw scroll indicator if needed
    if total_lines > visible_lines:
        # Scrollbar background
        sb_x: int32 = x + w - 12
        sb_y: int32 = y + 24
        sb_h: int32 = h - 28
        vtn_rect(sb_x, sb_y, 8, sb_h, 48, 48, 48, 255)

        # Scrollbar thumb
        thumb_h: int32 = (visible_lines * sb_h) / total_lines
        if thumb_h < 16:
            thumb_h = 16
        thumb_y: int32 = sb_y + (hex_scroll_offset * (sb_h - thumb_h)) / (total_lines - visible_lines)
        vtn_rect(sb_x, thumb_y, 8, thumb_h, 100, 100, 100, 255)

def hexview_scroll_up():
    """Scroll up one line."""
    global hex_scroll_offset
    if hex_scroll_offset > 0:
        hex_scroll_offset = hex_scroll_offset - 1

def hexview_scroll_down():
    """Scroll down one line."""
    global hex_scroll_offset
    total: int32 = hexview_total_lines()
    max_scroll: int32 = total - HEX_LINES_PER_PAGE
    if max_scroll < 0:
        max_scroll = 0
    if hex_scroll_offset < max_scroll:
        hex_scroll_offset = hex_scroll_offset + 1

def hexview_page_up():
    """Scroll up one page."""
    global hex_scroll_offset
    hex_scroll_offset = hex_scroll_offset - HEX_LINES_PER_PAGE
    if hex_scroll_offset < 0:
        hex_scroll_offset = 0

def hexview_page_down():
    """Scroll down one page."""
    global hex_scroll_offset
    total: int32 = hexview_total_lines()
    max_scroll: int32 = total - HEX_LINES_PER_PAGE
    if max_scroll < 0:
        max_scroll = 0
    hex_scroll_offset = hex_scroll_offset + HEX_LINES_PER_PAGE
    if hex_scroll_offset > max_scroll:
        hex_scroll_offset = max_scroll

def hexview_main(path: Ptr[char]):
    """Main entry point for hex viewer.

    Usage: hexview <filepath>
    """
    hex_init_chars()

    if not hexview_load(path):
        return

    console_puts("Loaded file for hex viewing\n")

    # Draw view (standalone mode - full screen)
    vtn_clear(0, 0, 0, 255)
    hexview_draw(0, 0, 800, 400)
    vtn_present()
