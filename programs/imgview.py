# Pynux BMP Image Viewer
#
# Display 24-bit uncompressed BMP images.
# BMP Structure:
#   - 14-byte file header
#   - DIB header (typically 40 bytes for BITMAPINFOHEADER)
#   - Pixel data (BGR format, bottom-up by default)
#
# Supports scaling for images larger than screen.

from kernel.ramfs import ramfs_read, ramfs_exists, ramfs_isdir, ramfs_size
from lib.vtnext import vtn_rect, vtn_textline, vtn_clear, vtn_present
from lib.io import console_puts

# Constants
IMG_MAX_FILE_SIZE: int32 = 8192  # Max file size to load
IMG_SCREEN_W: int32 = 800
IMG_SCREEN_H: int32 = 600

# Image buffer
img_file_buf: Array[8192, uint8]
img_file_size: int32 = 0

# BMP header info (parsed)
bmp_width: int32 = 0
bmp_height: int32 = 0
bmp_data_offset: int32 = 0
bmp_bits_per_pixel: int32 = 0
bmp_row_size: int32 = 0  # Row size including padding
bmp_top_down: bool = False  # True if top-down DIB

def bmp_read_u16(offset: int32) -> int32:
    """Read little-endian 16-bit value from buffer."""
    low: int32 = cast[int32](img_file_buf[offset])
    high: int32 = cast[int32](img_file_buf[offset + 1])
    return low + (high << 8)

def bmp_read_u32(offset: int32) -> int32:
    """Read little-endian 32-bit value from buffer."""
    b0: int32 = cast[int32](img_file_buf[offset])
    b1: int32 = cast[int32](img_file_buf[offset + 1])
    b2: int32 = cast[int32](img_file_buf[offset + 2])
    b3: int32 = cast[int32](img_file_buf[offset + 3])
    return b0 + (b1 << 8) + (b2 << 16) + (b3 << 24)

def bmp_read_i32(offset: int32) -> int32:
    """Read little-endian signed 32-bit value from buffer."""
    # Same as u32 but interpret as signed
    return bmp_read_u32(offset)

def bmp_parse_header() -> bool:
    """Parse BMP file header. Returns True on success."""
    global bmp_width, bmp_height, bmp_data_offset
    global bmp_bits_per_pixel, bmp_row_size, bmp_top_down

    # Check file size
    if img_file_size < 54:  # Minimum BMP size
        console_puts("imgview: File too small\n")
        return False

    # Check BMP signature "BM"
    if img_file_buf[0] != 66 or img_file_buf[1] != 77:  # 'B' = 66, 'M' = 77
        console_puts("imgview: Not a BMP file\n")
        return False

    # Read file header (14 bytes)
    # Offset 10: pixel data offset
    bmp_data_offset = bmp_read_u32(10)

    # Read DIB header
    # Offset 14: DIB header size (should be >= 40 for BITMAPINFOHEADER)
    dib_size: int32 = bmp_read_u32(14)
    if dib_size < 40:
        console_puts("imgview: Unsupported BMP format\n")
        return False

    # Offset 18: image width
    bmp_width = bmp_read_i32(18)

    # Offset 22: image height (negative = top-down)
    height: int32 = bmp_read_i32(22)
    if height < 0:
        bmp_top_down = True
        bmp_height = -height
    else:
        bmp_top_down = False
        bmp_height = height

    # Offset 26: color planes (must be 1)
    planes: int32 = bmp_read_u16(26)
    if planes != 1:
        console_puts("imgview: Invalid color planes\n")
        return False

    # Offset 28: bits per pixel
    bmp_bits_per_pixel = bmp_read_u16(28)
    if bmp_bits_per_pixel != 24:
        console_puts("imgview: Only 24-bit BMP supported\n")
        return False

    # Offset 30: compression (0 = none)
    compression: int32 = bmp_read_u32(30)
    if compression != 0:
        console_puts("imgview: Compressed BMP not supported\n")
        return False

    # Calculate row size (each row padded to 4-byte boundary)
    # Row size = ((width * 3) + 3) & ~3
    bmp_row_size = ((bmp_width * 3) + 3) & 0xFFFFFFFC

    # Validate dimensions
    if bmp_width <= 0 or bmp_height <= 0:
        console_puts("imgview: Invalid dimensions\n")
        return False

    if bmp_width > 1024 or bmp_height > 1024:
        console_puts("imgview: Image too large\n")
        return False

    return True

def imgview_load(path: Ptr[char]) -> bool:
    """Load BMP file into buffer. Returns True on success."""
    global img_file_size

    # Check file exists and is not a directory
    if not ramfs_exists(path):
        console_puts("imgview: File not found\n")
        return False

    if ramfs_isdir(path):
        console_puts("imgview: Cannot view directory\n")
        return False

    # Get file size and read
    fsize: int32 = ramfs_size(path)
    if fsize < 0:
        fsize = 0
    if fsize > IMG_MAX_FILE_SIZE:
        console_puts("imgview: File too large\n")
        return False

    img_file_size = ramfs_read(path, &img_file_buf[0], fsize)
    if img_file_size < 0:
        img_file_size = 0
        console_puts("imgview: Read error\n")
        return False

    # Parse header
    return bmp_parse_header()

def imgview_get_pixel(x: int32, y: int32, r: Ptr[int32], g: Ptr[int32], b: Ptr[int32]) -> bool:
    """Get pixel color at (x, y). Returns True if valid."""
    if x < 0 or x >= bmp_width or y < 0 or y >= bmp_height:
        return False

    # BMP stores rows bottom-up unless top-down
    row: int32 = y
    if not bmp_top_down:
        row = bmp_height - 1 - y

    # Calculate pixel offset
    # Pixel data starts at bmp_data_offset
    # Each row is bmp_row_size bytes
    # Each pixel is 3 bytes (BGR)
    offset: int32 = bmp_data_offset + row * bmp_row_size + x * 3

    if offset + 2 >= img_file_size:
        return False

    # BMP stores BGR, not RGB
    b[0] = cast[int32](img_file_buf[offset])
    g[0] = cast[int32](img_file_buf[offset + 1])
    r[0] = cast[int32](img_file_buf[offset + 2])

    return True

def imgview_draw(view_x: int32, view_y: int32, max_w: int32, max_h: int32):
    """Draw loaded image at specified location with optional scaling.

    Args:
        view_x, view_y: Top-left corner position
        max_w, max_h: Maximum width and height for display area
    """
    # Calculate scale factor (integer scaling down only)
    scale: int32 = 1
    while (bmp_width / scale) > max_w or (bmp_height / scale) > max_h:
        scale = scale + 1

    # Calculate display size
    disp_w: int32 = bmp_width / scale
    disp_h: int32 = bmp_height / scale

    # Center image in view area
    offset_x: int32 = view_x + (max_w - disp_w) / 2
    offset_y: int32 = view_y + (max_h - disp_h) / 2

    # Draw background
    vtn_rect(view_x, view_y, max_w, max_h, 32, 32, 32, 255)

    # Draw pixels
    # For efficiency, draw in batches of same-colored horizontal runs
    r: int32 = 0
    g: int32 = 0
    b: int32 = 0

    dy: int32 = 0
    while dy < disp_h:
        dx: int32 = 0
        while dx < disp_w:
            # Sample source pixel (use nearest-neighbor)
            src_x: int32 = dx * scale
            src_y: int32 = dy * scale

            if imgview_get_pixel(src_x, src_y, &r, &g, &b):
                # Draw pixel as 1x1 rectangle
                px: int32 = offset_x + dx
                py: int32 = offset_y + dy

                # Optimization: draw larger blocks when not scaling
                if scale == 1:
                    vtn_rect(px, py, 1, 1, r, g, b, 255)
                else:
                    # When scaling, we can draw larger blocks
                    vtn_rect(px, py, 1, 1, r, g, b, 255)

            dx = dx + 1
        dy = dy + 1

def imgview_draw_fast(view_x: int32, view_y: int32, max_w: int32, max_h: int32):
    """Draw loaded image using horizontal line optimization.

    Groups consecutive pixels of similar color into single rectangles.
    """
    # Calculate scale factor
    scale: int32 = 1
    while (bmp_width / scale) > max_w or (bmp_height / scale) > max_h:
        scale = scale + 1

    # Calculate display size
    disp_w: int32 = bmp_width / scale
    disp_h: int32 = bmp_height / scale

    # Center image
    offset_x: int32 = view_x + (max_w - disp_w) / 2
    offset_y: int32 = view_y + (max_h - disp_h) / 2

    # Draw background
    vtn_rect(view_x, view_y, max_w, max_h, 32, 32, 32, 255)

    # Draw each row
    r: int32 = 0
    g: int32 = 0
    b: int32 = 0

    dy: int32 = 0
    while dy < disp_h:
        # For each row, try to batch horizontal runs
        dx: int32 = 0
        run_start: int32 = 0
        run_r: int32 = 0
        run_g: int32 = 0
        run_b: int32 = 0
        in_run: bool = False

        while dx <= disp_w:
            got_pixel: bool = False
            if dx < disp_w:
                src_x: int32 = dx * scale
                src_y: int32 = dy * scale
                got_pixel = imgview_get_pixel(src_x, src_y, &r, &g, &b)

            # Check if we should end current run
            end_run: bool = False
            if not got_pixel:
                end_run = True
            elif in_run:
                # Check if color is different (allow small tolerance for compression)
                if r != run_r or g != run_g or b != run_b:
                    end_run = True

            if end_run and in_run:
                # Draw the run
                run_len: int32 = dx - run_start
                if run_len > 0:
                    vtn_rect(offset_x + run_start, offset_y + dy, run_len, 1, run_r, run_g, run_b, 255)
                in_run = False

            if got_pixel and not in_run:
                # Start new run
                run_start = dx
                run_r = r
                run_g = g
                run_b = b
                in_run = True

            dx = dx + 1

        dy = dy + 1

def imgview_draw_info(x: int32, y: int32):
    """Draw image information."""
    info_line: Array[64, char]

    # Format info string manually
    # "WxH, 24-bit BMP"
    i: int32 = 0

    # Width
    w: int32 = bmp_width
    if w >= 100:
        info_line[i] = cast[char](48 + (w / 100) % 10)
        i = i + 1
    if w >= 10:
        info_line[i] = cast[char](48 + (w / 10) % 10)
        i = i + 1
    info_line[i] = cast[char](48 + w % 10)
    i = i + 1

    info_line[i] = 'x'
    i = i + 1

    # Height
    h: int32 = bmp_height
    if h >= 100:
        info_line[i] = cast[char](48 + (h / 100) % 10)
        i = i + 1
    if h >= 10:
        info_line[i] = cast[char](48 + (h / 10) % 10)
        i = i + 1
    info_line[i] = cast[char](48 + h % 10)
    i = i + 1

    # Rest of string
    info_line[i] = ','
    i = i + 1
    info_line[i] = ' '
    i = i + 1
    info_line[i] = '2'
    i = i + 1
    info_line[i] = '4'
    i = i + 1
    info_line[i] = '-'
    i = i + 1
    info_line[i] = 'b'
    i = i + 1
    info_line[i] = 'i'
    i = i + 1
    info_line[i] = 't'
    i = i + 1
    info_line[i] = ' '
    i = i + 1
    info_line[i] = 'B'
    i = i + 1
    info_line[i] = 'M'
    i = i + 1
    info_line[i] = 'P'
    i = i + 1
    info_line[i] = '\0'

    vtn_textline(&info_line[0], x, y, 180, 180, 180)

def imgview_main(path: Ptr[char]):
    """Main entry point for image viewer.

    Usage: imgview <filepath>
    """
    if not imgview_load(path):
        return

    console_puts("Image loaded successfully\n")

    # Draw view (standalone mode - full screen)
    vtn_clear(0, 0, 0, 255)

    # Draw image info at top
    imgview_draw_info(10, 10)

    # Draw image (fast version with run-length optimization)
    imgview_draw_fast(0, 30, IMG_SCREEN_W, IMG_SCREEN_H - 30)

    vtn_present()
