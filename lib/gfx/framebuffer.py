# Pynux Graphics Library - Framebuffer Management
#
# Double-buffered framebuffer for bare-metal ARM graphics.
# Supports variable resolution and bit depths.

from lib.memory import alloc, free, memset, memcpy

# ============================================================================
# Framebuffer State
# ============================================================================

# Framebuffer dimensions and format
_fb_width: int32 = 0
_fb_height: int32 = 0
_fb_bpp: int32 = 0              # Bits per pixel (8, 16, 24, or 32)
_fb_pitch: int32 = 0            # Bytes per row
_fb_size: int32 = 0             # Total buffer size in bytes

# Double buffer pointers
_fb_front: Ptr[uint8] = cast[Ptr[uint8]](0)
_fb_back: Ptr[uint8] = cast[Ptr[uint8]](0)

# Current draw target (points to back buffer normally)
_fb_draw: Ptr[uint8] = cast[Ptr[uint8]](0)

# Initialization state
_fb_initialized: bool = False

# ============================================================================
# Framebuffer Initialization
# ============================================================================

def fb_init(width: int32, height: int32, bpp: int32) -> bool:
    """Initialize framebuffer with specified dimensions and bit depth.

    Creates a double-buffered framebuffer.

    Args:
        width: Width in pixels
        height: Height in pixels
        bpp: Bits per pixel (8, 16, 24, or 32)

    Returns:
        True if initialization successful, False on error
    """
    global _fb_width, _fb_height, _fb_bpp, _fb_pitch, _fb_size
    global _fb_front, _fb_back, _fb_draw, _fb_initialized

    # Validate parameters
    if width <= 0 or height <= 0:
        return False

    # Validate and normalize bpp
    if bpp != 8 and bpp != 16 and bpp != 24 and bpp != 32:
        bpp = 32  # Default to 32-bit

    # Calculate sizes
    bytes_per_pixel: int32 = bpp / 8
    pitch: int32 = width * bytes_per_pixel
    size: int32 = pitch * height

    # Free existing buffers if reinitializing
    if _fb_initialized:
        fb_destroy()

    # Allocate front buffer
    _fb_front = alloc(size)
    if cast[uint32](_fb_front) == 0:
        return False

    # Allocate back buffer
    _fb_back = alloc(size)
    if cast[uint32](_fb_back) == 0:
        free(_fb_front)
        _fb_front = cast[Ptr[uint8]](0)
        return False

    # Initialize state
    _fb_width = width
    _fb_height = height
    _fb_bpp = bpp
    _fb_pitch = pitch
    _fb_size = size
    _fb_draw = _fb_back
    _fb_initialized = True

    # Clear both buffers
    memset(_fb_front, 0, size)
    memset(_fb_back, 0, size)

    return True

def fb_destroy():
    """Free framebuffer resources."""
    global _fb_front, _fb_back, _fb_draw, _fb_initialized
    global _fb_width, _fb_height, _fb_bpp, _fb_pitch, _fb_size

    if cast[uint32](_fb_front) != 0:
        free(_fb_front)
        _fb_front = cast[Ptr[uint8]](0)

    if cast[uint32](_fb_back) != 0:
        free(_fb_back)
        _fb_back = cast[Ptr[uint8]](0)

    _fb_draw = cast[Ptr[uint8]](0)
    _fb_initialized = False
    _fb_width = 0
    _fb_height = 0
    _fb_bpp = 0
    _fb_pitch = 0
    _fb_size = 0

# ============================================================================
# Framebuffer Queries
# ============================================================================

def fb_get_width() -> int32:
    """Get framebuffer width in pixels.

    Returns:
        Width in pixels, or 0 if not initialized
    """
    return _fb_width

def fb_get_height() -> int32:
    """Get framebuffer height in pixels.

    Returns:
        Height in pixels, or 0 if not initialized
    """
    return _fb_height

def fb_get_bpp() -> int32:
    """Get framebuffer bits per pixel.

    Returns:
        Bits per pixel (8, 16, 24, or 32)
    """
    return _fb_bpp

def fb_get_pitch() -> int32:
    """Get framebuffer pitch (bytes per row).

    Returns:
        Pitch in bytes
    """
    return _fb_pitch

def fb_get_size() -> int32:
    """Get framebuffer size in bytes.

    Returns:
        Size in bytes
    """
    return _fb_size

def fb_is_initialized() -> bool:
    """Check if framebuffer is initialized.

    Returns:
        True if initialized
    """
    return _fb_initialized

# ============================================================================
# Buffer Access
# ============================================================================

def fb_get_buffer() -> Ptr[uint8]:
    """Get pointer to current draw buffer.

    Returns:
        Pointer to back buffer (draw target)
    """
    return _fb_draw

def fb_get_front_buffer() -> Ptr[uint8]:
    """Get pointer to front (display) buffer.

    Returns:
        Pointer to front buffer
    """
    return _fb_front

def fb_get_back_buffer() -> Ptr[uint8]:
    """Get pointer to back (draw) buffer.

    Returns:
        Pointer to back buffer
    """
    return _fb_back

# ============================================================================
# Buffer Operations
# ============================================================================

def fb_clear(color: uint32):
    """Clear framebuffer to specified color.

    Args:
        color: Fill color (32-bit ARGB)
    """
    if not _fb_initialized:
        return

    if _fb_bpp == 32:
        # 32-bit: direct fill
        buf32: Ptr[uint32] = cast[Ptr[uint32]](_fb_draw)
        count: int32 = _fb_size / 4
        i: int32 = 0
        while i < count:
            buf32[i] = color
            i = i + 1

    elif _fb_bpp == 16:
        # 16-bit: convert to RGB565
        color16: uint16 = _color_to_16(color)
        buf16: Ptr[uint16] = cast[Ptr[uint16]](_fb_draw)
        count: int32 = _fb_size / 2
        i: int32 = 0
        while i < count:
            buf16[i] = color16
            i = i + 1

    elif _fb_bpp == 8:
        # 8-bit: convert to grayscale
        gray: uint8 = _color_to_8(color)
        memset(_fb_draw, gray, _fb_size)

    elif _fb_bpp == 24:
        # 24-bit: RGB triplets
        r: uint8 = cast[uint8]((color >> 16) & 0xFF)
        g: uint8 = cast[uint8]((color >> 8) & 0xFF)
        b: uint8 = cast[uint8](color & 0xFF)
        i: int32 = 0
        while i < _fb_size:
            _fb_draw[i] = b
            _fb_draw[i + 1] = g
            _fb_draw[i + 2] = r
            i = i + 3

def fb_swap():
    """Swap front and back buffers (present frame).

    Copies back buffer to front buffer for double-buffering.
    In a real implementation, this might trigger a DMA transfer
    or swap buffer pointers if the display supports it.
    """
    if not _fb_initialized:
        return

    # Copy back buffer to front buffer
    memcpy(_fb_front, _fb_back, _fb_size)

def fb_copy_to_front():
    """Copy back buffer to front without swapping."""
    if not _fb_initialized:
        return
    memcpy(_fb_front, _fb_back, _fb_size)

def fb_copy_to_back():
    """Copy front buffer to back (restore previous frame)."""
    if not _fb_initialized:
        return
    memcpy(_fb_back, _fb_front, _fb_size)

# ============================================================================
# Pixel Operations
# ============================================================================

def fb_set_pixel(x: int32, y: int32, color: uint32):
    """Set a single pixel in the framebuffer.

    Args:
        x: X coordinate
        y: Y coordinate
        color: Pixel color (32-bit ARGB)
    """
    if not _fb_initialized:
        return

    # Bounds check
    if x < 0 or x >= _fb_width or y < 0 or y >= _fb_height:
        return

    if _fb_bpp == 32:
        offset: int32 = y * _fb_pitch + x * 4
        buf32: Ptr[uint32] = cast[Ptr[uint32]](&_fb_draw[offset])
        buf32[0] = color

    elif _fb_bpp == 16:
        offset: int32 = y * _fb_pitch + x * 2
        buf16: Ptr[uint16] = cast[Ptr[uint16]](&_fb_draw[offset])
        buf16[0] = _color_to_16(color)

    elif _fb_bpp == 8:
        offset: int32 = y * _fb_pitch + x
        _fb_draw[offset] = _color_to_8(color)

    elif _fb_bpp == 24:
        offset: int32 = y * _fb_pitch + x * 3
        _fb_draw[offset] = cast[uint8](color & 0xFF)          # B
        _fb_draw[offset + 1] = cast[uint8]((color >> 8) & 0xFF)   # G
        _fb_draw[offset + 2] = cast[uint8]((color >> 16) & 0xFF)  # R

def fb_get_pixel(x: int32, y: int32) -> uint32:
    """Get a single pixel from the framebuffer.

    Args:
        x: X coordinate
        y: Y coordinate

    Returns:
        Pixel color (32-bit ARGB), or 0 if out of bounds
    """
    if not _fb_initialized:
        return 0

    # Bounds check
    if x < 0 or x >= _fb_width or y < 0 or y >= _fb_height:
        return 0

    if _fb_bpp == 32:
        offset: int32 = y * _fb_pitch + x * 4
        buf32: Ptr[uint32] = cast[Ptr[uint32]](&_fb_draw[offset])
        return buf32[0]

    elif _fb_bpp == 16:
        offset: int32 = y * _fb_pitch + x * 2
        buf16: Ptr[uint16] = cast[Ptr[uint16]](&_fb_draw[offset])
        return _color_from_16(buf16[0])

    elif _fb_bpp == 8:
        offset: int32 = y * _fb_pitch + x
        gray: int32 = cast[int32](_fb_draw[offset])
        return 0xFF000000 | (cast[uint32](gray) << 16) | (cast[uint32](gray) << 8) | cast[uint32](gray)

    elif _fb_bpp == 24:
        offset: int32 = y * _fb_pitch + x * 3
        b: int32 = cast[int32](_fb_draw[offset])
        g: int32 = cast[int32](_fb_draw[offset + 1])
        r: int32 = cast[int32](_fb_draw[offset + 2])
        return 0xFF000000 | (cast[uint32](r) << 16) | (cast[uint32](g) << 8) | cast[uint32](b)

    return 0

def fb_set_pixel_fast(x: int32, y: int32, color: uint32):
    """Set pixel without bounds checking (faster but unsafe).

    Args:
        x: X coordinate (must be valid)
        y: Y coordinate (must be valid)
        color: Pixel color
    """
    if _fb_bpp == 32:
        offset: int32 = y * _fb_pitch + x * 4
        buf32: Ptr[uint32] = cast[Ptr[uint32]](&_fb_draw[offset])
        buf32[0] = color

def fb_set_pixel_blend(x: int32, y: int32, color: uint32):
    """Set pixel with alpha blending.

    Args:
        x: X coordinate
        y: Y coordinate
        color: Pixel color with alpha
    """
    if not _fb_initialized:
        return

    if x < 0 or x >= _fb_width or y < 0 or y >= _fb_height:
        return

    alpha: int32 = cast[int32]((color >> 24) & 0xFF)

    # Fully transparent - do nothing
    if alpha == 0:
        return

    # Fully opaque - just set
    if alpha == 255:
        fb_set_pixel(x, y, color)
        return

    # Blend
    bg: uint32 = fb_get_pixel(x, y)
    inv_alpha: int32 = 255 - alpha

    r: int32 = (cast[int32]((color >> 16) & 0xFF) * alpha + cast[int32]((bg >> 16) & 0xFF) * inv_alpha) / 255
    g: int32 = (cast[int32]((color >> 8) & 0xFF) * alpha + cast[int32]((bg >> 8) & 0xFF) * inv_alpha) / 255
    b: int32 = (cast[int32](color & 0xFF) * alpha + cast[int32](bg & 0xFF) * inv_alpha) / 255

    fb_set_pixel(x, y, 0xFF000000 | (cast[uint32](r) << 16) | (cast[uint32](g) << 8) | cast[uint32](b))

# ============================================================================
# Internal Color Conversion Helpers
# ============================================================================

def _color_to_16(color: uint32) -> uint16:
    """Convert 32-bit ARGB to 16-bit RGB565."""
    r: int32 = (cast[int32]((color >> 16) & 0xFF) >> 3) & 0x1F
    g: int32 = (cast[int32]((color >> 8) & 0xFF) >> 2) & 0x3F
    b: int32 = (cast[int32](color & 0xFF) >> 3) & 0x1F
    return cast[uint16]((r << 11) | (g << 5) | b)

def _color_from_16(color16: uint16) -> uint32:
    """Convert 16-bit RGB565 to 32-bit ARGB."""
    r: int32 = ((cast[int32](color16) >> 11) & 0x1F) << 3
    g: int32 = ((cast[int32](color16) >> 5) & 0x3F) << 2
    b: int32 = (cast[int32](color16) & 0x1F) << 3
    return 0xFF000000 | (cast[uint32](r) << 16) | (cast[uint32](g) << 8) | cast[uint32](b)

def _color_to_8(color: uint32) -> uint8:
    """Convert 32-bit ARGB to 8-bit grayscale."""
    r: int32 = cast[int32]((color >> 16) & 0xFF)
    g: int32 = cast[int32]((color >> 8) & 0xFF)
    b: int32 = cast[int32](color & 0xFF)
    # Luminance: 0.299*R + 0.587*G + 0.114*B
    gray: int32 = (77 * r + 150 * g + 29 * b) / 256
    return cast[uint8](gray)

# ============================================================================
# Clipping Region
# ============================================================================

_clip_x1: int32 = 0
_clip_y1: int32 = 0
_clip_x2: int32 = 0
_clip_y2: int32 = 0
_clip_enabled: bool = False

def fb_set_clip(x: int32, y: int32, w: int32, h: int32):
    """Set clipping rectangle.

    Args:
        x, y: Top-left corner
        w, h: Width and height
    """
    global _clip_x1, _clip_y1, _clip_x2, _clip_y2, _clip_enabled

    _clip_x1 = x
    _clip_y1 = y
    _clip_x2 = x + w
    _clip_y2 = y + h
    _clip_enabled = True

def fb_clear_clip():
    """Clear clipping rectangle (use full framebuffer)."""
    global _clip_enabled
    _clip_enabled = False

def fb_is_clipped(x: int32, y: int32) -> bool:
    """Check if point is outside clipping region.

    Args:
        x, y: Point to check

    Returns:
        True if point is clipped (outside region)
    """
    if not _clip_enabled:
        return False
    return x < _clip_x1 or x >= _clip_x2 or y < _clip_y1 or y >= _clip_y2
