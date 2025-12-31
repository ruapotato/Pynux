# Pynux Graphics Library - Sprite Handling
#
# Sprite management for bare-metal ARM graphics.
# Supports creation, loading, drawing, and scaling of sprites.

from lib.memory import alloc, free, memcpy, memset
from lib.gfx.framebuffer import fb_set_pixel, fb_set_pixel_blend, fb_is_initialized, fb_get_width, fb_get_height

# ============================================================================
# Sprite System Constants
# ============================================================================

MAX_SPRITES: int32 = 32  # Maximum number of sprites

# Sprite flags
SPRITE_FLAG_ACTIVE: int32 = 0x01
SPRITE_FLAG_ALPHA: int32 = 0x02     # Has alpha channel
SPRITE_FLAG_FLIP_H: int32 = 0x04   # Flip horizontal
SPRITE_FLAG_FLIP_V: int32 = 0x08   # Flip vertical

# ============================================================================
# Sprite Structure
# ============================================================================
# Each sprite has:
#   - width, height: dimensions
#   - data: pointer to pixel data (32-bit ARGB)
#   - flags: various sprite flags

# Sprite storage (simple array-based approach)
_sprite_width: Array[32, int32]
_sprite_height: Array[32, int32]
_sprite_data: Array[32, Ptr[uint32]]
_sprite_flags: Array[32, int32]

_sprites_initialized: bool = False

# ============================================================================
# Sprite System Initialization
# ============================================================================

def _sprite_init():
    """Initialize sprite system."""
    global _sprites_initialized

    if _sprites_initialized:
        return

    i: int32 = 0
    while i < MAX_SPRITES:
        _sprite_width[i] = 0
        _sprite_height[i] = 0
        _sprite_data[i] = cast[Ptr[uint32]](0)
        _sprite_flags[i] = 0
        i = i + 1

    _sprites_initialized = True

# ============================================================================
# Sprite Creation and Destruction
# ============================================================================

def sprite_create(width: int32, height: int32) -> int32:
    """Create a new sprite.

    Args:
        width: Sprite width in pixels
        height: Sprite height in pixels

    Returns:
        Sprite ID (0 to MAX_SPRITES-1), or -1 on error
    """
    if not _sprites_initialized:
        _sprite_init()

    if width <= 0 or height <= 0:
        return -1

    # Find free slot
    slot: int32 = -1
    i: int32 = 0
    while i < MAX_SPRITES:
        if (_sprite_flags[i] & SPRITE_FLAG_ACTIVE) == 0:
            slot = i
            break
        i = i + 1

    if slot < 0:
        return -1  # No free slots

    # Allocate pixel data (32-bit ARGB per pixel)
    size: int32 = width * height * 4
    data: Ptr[uint32] = cast[Ptr[uint32]](alloc(size))
    if cast[uint32](data) == 0:
        return -1  # Allocation failed

    # Clear to transparent
    memset(cast[Ptr[uint8]](data), 0, size)

    # Initialize sprite
    _sprite_width[slot] = width
    _sprite_height[slot] = height
    _sprite_data[slot] = data
    _sprite_flags[slot] = SPRITE_FLAG_ACTIVE

    return slot

def sprite_destroy(id: int32):
    """Destroy a sprite and free its memory.

    Args:
        id: Sprite ID to destroy
    """
    if id < 0 or id >= MAX_SPRITES:
        return

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    # Free pixel data
    if cast[uint32](_sprite_data[id]) != 0:
        free(cast[Ptr[uint8]](_sprite_data[id]))

    # Clear slot
    _sprite_width[id] = 0
    _sprite_height[id] = 0
    _sprite_data[id] = cast[Ptr[uint32]](0)
    _sprite_flags[id] = 0

def sprite_destroy_all():
    """Destroy all sprites."""
    i: int32 = 0
    while i < MAX_SPRITES:
        sprite_destroy(i)
        i = i + 1

# ============================================================================
# Sprite Loading
# ============================================================================

def sprite_load(id: int32, data: Ptr[uint32]):
    """Load pixel data into a sprite.

    Data must be in 32-bit ARGB format, size = width * height.

    Args:
        id: Sprite ID
        data: Pointer to pixel data
    """
    if id < 0 or id >= MAX_SPRITES:
        return

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    if cast[uint32](data) == 0:
        return

    size: int32 = _sprite_width[id] * _sprite_height[id] * 4
    memcpy(cast[Ptr[uint8]](_sprite_data[id]), cast[Ptr[uint8]](data), size)

    # Check if sprite has any non-opaque pixels
    _sprite_flags[id] = _sprite_flags[id] & (~SPRITE_FLAG_ALPHA)
    i: int32 = 0
    total: int32 = _sprite_width[id] * _sprite_height[id]
    while i < total:
        alpha: int32 = cast[int32]((_sprite_data[id][i] >> 24) & 0xFF)
        if alpha != 255:
            _sprite_flags[id] = _sprite_flags[id] | SPRITE_FLAG_ALPHA
            break
        i = i + 1

def sprite_load_raw(id: int32, data: Ptr[uint8], transparent_color: uint32):
    """Load raw 8-bit indexed data as sprite with transparency.

    Each byte is an index into a simple 8-color palette.

    Args:
        id: Sprite ID
        data: Pointer to raw pixel indices
        transparent_color: Color index to treat as transparent
    """
    if id < 0 or id >= MAX_SPRITES:
        return

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    if cast[uint32](data) == 0:
        return

    # Simple 8-color palette
    palette: Array[8, uint32]
    palette[0] = 0xFF000000  # Black
    palette[1] = 0xFFFF0000  # Red
    palette[2] = 0xFF00FF00  # Green
    palette[3] = 0xFF0000FF  # Blue
    palette[4] = 0xFFFFFF00  # Yellow
    palette[5] = 0xFF00FFFF  # Cyan
    palette[6] = 0xFFFF00FF  # Magenta
    palette[7] = 0xFFFFFFFF  # White

    total: int32 = _sprite_width[id] * _sprite_height[id]
    has_alpha: bool = False

    i: int32 = 0
    while i < total:
        idx: int32 = cast[int32](data[i]) & 0x07
        if cast[uint32](idx) == transparent_color:
            _sprite_data[id][i] = 0x00000000  # Fully transparent
            has_alpha = True
        else:
            _sprite_data[id][i] = palette[idx]
        i = i + 1

    if has_alpha:
        _sprite_flags[id] = _sprite_flags[id] | SPRITE_FLAG_ALPHA
    else:
        _sprite_flags[id] = _sprite_flags[id] & (~SPRITE_FLAG_ALPHA)

def sprite_set_pixel(id: int32, x: int32, y: int32, color: uint32):
    """Set a single pixel in a sprite.

    Args:
        id: Sprite ID
        x, y: Pixel coordinates
        color: Pixel color (32-bit ARGB)
    """
    if id < 0 or id >= MAX_SPRITES:
        return

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    w: int32 = _sprite_width[id]
    h: int32 = _sprite_height[id]

    if x < 0 or x >= w or y < 0 or y >= h:
        return

    _sprite_data[id][y * w + x] = color

def sprite_get_pixel(id: int32, x: int32, y: int32) -> uint32:
    """Get a single pixel from a sprite.

    Args:
        id: Sprite ID
        x, y: Pixel coordinates

    Returns:
        Pixel color (32-bit ARGB), or 0 if invalid
    """
    if id < 0 or id >= MAX_SPRITES:
        return 0

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return 0

    w: int32 = _sprite_width[id]
    h: int32 = _sprite_height[id]

    if x < 0 or x >= w or y < 0 or y >= h:
        return 0

    return _sprite_data[id][y * w + x]

# ============================================================================
# Sprite Drawing
# ============================================================================

def sprite_draw(id: int32, x: int32, y: int32):
    """Draw a sprite to the framebuffer.

    Args:
        id: Sprite ID
        x, y: Position (top-left corner)
    """
    if not fb_is_initialized():
        return

    if id < 0 or id >= MAX_SPRITES:
        return

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    w: int32 = _sprite_width[id]
    h: int32 = _sprite_height[id]
    data: Ptr[uint32] = _sprite_data[id]
    flags: int32 = _sprite_flags[id]

    has_alpha: bool = (flags & SPRITE_FLAG_ALPHA) != 0
    flip_h: bool = (flags & SPRITE_FLAG_FLIP_H) != 0
    flip_v: bool = (flags & SPRITE_FLAG_FLIP_V) != 0

    sy: int32 = 0
    while sy < h:
        src_y: int32 = h - 1 - sy if flip_v else sy

        sx: int32 = 0
        while sx < w:
            src_x: int32 = w - 1 - sx if flip_h else sx

            color: uint32 = data[src_y * w + src_x]

            # Skip fully transparent pixels
            alpha: int32 = cast[int32]((color >> 24) & 0xFF)
            if alpha > 0:
                if has_alpha and alpha < 255:
                    fb_set_pixel_blend(x + sx, y + sy, color)
                else:
                    fb_set_pixel(x + sx, y + sy, color)

            sx = sx + 1
        sy = sy + 1

def sprite_draw_scaled(id: int32, x: int32, y: int32, scale: int32):
    """Draw a sprite scaled by an integer factor.

    Args:
        id: Sprite ID
        x, y: Position (top-left corner)
        scale: Scale factor (1 = normal, 2 = double, etc.)
    """
    if not fb_is_initialized():
        return

    if id < 0 or id >= MAX_SPRITES:
        return

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    if scale < 1:
        scale = 1

    w: int32 = _sprite_width[id]
    h: int32 = _sprite_height[id]
    data: Ptr[uint32] = _sprite_data[id]
    flags: int32 = _sprite_flags[id]

    has_alpha: bool = (flags & SPRITE_FLAG_ALPHA) != 0
    flip_h: bool = (flags & SPRITE_FLAG_FLIP_H) != 0
    flip_v: bool = (flags & SPRITE_FLAG_FLIP_V) != 0

    sy: int32 = 0
    while sy < h:
        src_y: int32 = h - 1 - sy if flip_v else sy

        sx: int32 = 0
        while sx < w:
            src_x: int32 = w - 1 - sx if flip_h else sx

            color: uint32 = data[src_y * w + src_x]
            alpha: int32 = cast[int32]((color >> 24) & 0xFF)

            if alpha > 0:
                # Draw scaled pixel
                dy: int32 = 0
                while dy < scale:
                    dx: int32 = 0
                    while dx < scale:
                        if has_alpha and alpha < 255:
                            fb_set_pixel_blend(x + sx * scale + dx, y + sy * scale + dy, color)
                        else:
                            fb_set_pixel(x + sx * scale + dx, y + sy * scale + dy, color)
                        dx = dx + 1
                    dy = dy + 1

            sx = sx + 1
        sy = sy + 1

def sprite_draw_partial(id: int32, x: int32, y: int32,
                        src_x: int32, src_y: int32, src_w: int32, src_h: int32):
    """Draw a portion of a sprite (for sprite sheets).

    Args:
        id: Sprite ID
        x, y: Destination position
        src_x, src_y: Source position within sprite
        src_w, src_h: Size of region to draw
    """
    if not fb_is_initialized():
        return

    if id < 0 or id >= MAX_SPRITES:
        return

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    w: int32 = _sprite_width[id]
    h: int32 = _sprite_height[id]
    data: Ptr[uint32] = _sprite_data[id]
    flags: int32 = _sprite_flags[id]

    has_alpha: bool = (flags & SPRITE_FLAG_ALPHA) != 0

    # Clamp source region
    if src_x < 0:
        src_w = src_w + src_x
        x = x - src_x
        src_x = 0
    if src_y < 0:
        src_h = src_h + src_y
        y = y - src_y
        src_y = 0
    if src_x + src_w > w:
        src_w = w - src_x
    if src_y + src_h > h:
        src_h = h - src_y

    if src_w <= 0 or src_h <= 0:
        return

    sy: int32 = 0
    while sy < src_h:
        sx: int32 = 0
        while sx < src_w:
            color: uint32 = data[(src_y + sy) * w + (src_x + sx)]
            alpha: int32 = cast[int32]((color >> 24) & 0xFF)

            if alpha > 0:
                if has_alpha and alpha < 255:
                    fb_set_pixel_blend(x + sx, y + sy, color)
                else:
                    fb_set_pixel(x + sx, y + sy, color)

            sx = sx + 1
        sy = sy + 1

def sprite_draw_rotated(id: int32, cx: int32, cy: int32, angle: int32):
    """Draw a sprite rotated around its center.

    Uses simple rotation with nearest-neighbor sampling.

    Args:
        id: Sprite ID
        cx, cy: Center position for rotation
        angle: Rotation angle in degrees
    """
    if not fb_is_initialized():
        return

    if id < 0 or id >= MAX_SPRITES:
        return

    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    w: int32 = _sprite_width[id]
    h: int32 = _sprite_height[id]
    data: Ptr[uint32] = _sprite_data[id]
    flags: int32 = _sprite_flags[id]

    has_alpha: bool = (flags & SPRITE_FLAG_ALPHA) != 0

    # Pre-calculate sin/cos (scaled by 256)
    sin_a: int32 = _sin_deg(angle)
    cos_a: int32 = _cos_deg(angle)

    # Half dimensions
    hw: int32 = w / 2
    hh: int32 = h / 2

    # Iterate over destination area (larger to account for rotation)
    max_dim: int32 = w
    if h > max_dim:
        max_dim = h

    dy: int32 = -max_dim
    while dy < max_dim:
        dx: int32 = -max_dim
        while dx < max_dim:
            # Inverse rotation to find source pixel
            # src_x = dx*cos + dy*sin + hw
            # src_y = -dx*sin + dy*cos + hh
            src_x: int32 = (dx * cos_a + dy * sin_a) / 256 + hw
            src_y: int32 = (-dx * sin_a + dy * cos_a) / 256 + hh

            if src_x >= 0 and src_x < w and src_y >= 0 and src_y < h:
                color: uint32 = data[src_y * w + src_x]
                alpha: int32 = cast[int32]((color >> 24) & 0xFF)

                if alpha > 0:
                    if has_alpha and alpha < 255:
                        fb_set_pixel_blend(cx + dx, cy + dy, color)
                    else:
                        fb_set_pixel(cx + dx, cy + dy, color)

            dx = dx + 1
        dy = dy + 1

# ============================================================================
# Sprite Properties
# ============================================================================

def sprite_get_width(id: int32) -> int32:
    """Get sprite width.

    Args:
        id: Sprite ID

    Returns:
        Width in pixels, or 0 if invalid
    """
    if id < 0 or id >= MAX_SPRITES:
        return 0
    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return 0
    return _sprite_width[id]

def sprite_get_height(id: int32) -> int32:
    """Get sprite height.

    Args:
        id: Sprite ID

    Returns:
        Height in pixels, or 0 if invalid
    """
    if id < 0 or id >= MAX_SPRITES:
        return 0
    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return 0
    return _sprite_height[id]

def sprite_is_valid(id: int32) -> bool:
    """Check if sprite ID is valid and active.

    Args:
        id: Sprite ID

    Returns:
        True if sprite is valid and active
    """
    if id < 0 or id >= MAX_SPRITES:
        return False
    return (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) != 0

def sprite_set_flip(id: int32, flip_h: bool, flip_v: bool):
    """Set sprite flip flags.

    Args:
        id: Sprite ID
        flip_h: Flip horizontally
        flip_v: Flip vertically
    """
    if id < 0 or id >= MAX_SPRITES:
        return
    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    _sprite_flags[id] = _sprite_flags[id] & (~(SPRITE_FLAG_FLIP_H | SPRITE_FLAG_FLIP_V))
    if flip_h:
        _sprite_flags[id] = _sprite_flags[id] | SPRITE_FLAG_FLIP_H
    if flip_v:
        _sprite_flags[id] = _sprite_flags[id] | SPRITE_FLAG_FLIP_V

def sprite_get_data(id: int32) -> Ptr[uint32]:
    """Get pointer to sprite pixel data.

    Args:
        id: Sprite ID

    Returns:
        Pointer to pixel data, or null if invalid
    """
    if id < 0 or id >= MAX_SPRITES:
        return cast[Ptr[uint32]](0)
    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return cast[Ptr[uint32]](0)
    return _sprite_data[id]

# ============================================================================
# Sprite Effects
# ============================================================================

def sprite_fill(id: int32, color: uint32):
    """Fill entire sprite with a color.

    Args:
        id: Sprite ID
        color: Fill color
    """
    if id < 0 or id >= MAX_SPRITES:
        return
    if (_sprite_flags[id] & SPRITE_FLAG_ACTIVE) == 0:
        return

    total: int32 = _sprite_width[id] * _sprite_height[id]
    i: int32 = 0
    while i < total:
        _sprite_data[id][i] = color
        i = i + 1

def sprite_clear(id: int32):
    """Clear sprite to transparent.

    Args:
        id: Sprite ID
    """
    sprite_fill(id, 0x00000000)
    if id >= 0 and id < MAX_SPRITES:
        _sprite_flags[id] = _sprite_flags[id] | SPRITE_FLAG_ALPHA

def sprite_copy(src_id: int32, dst_id: int32) -> bool:
    """Copy sprite data from one sprite to another.

    Sprites must have the same dimensions.

    Args:
        src_id: Source sprite ID
        dst_id: Destination sprite ID

    Returns:
        True if copy successful
    """
    if src_id < 0 or src_id >= MAX_SPRITES:
        return False
    if dst_id < 0 or dst_id >= MAX_SPRITES:
        return False
    if (_sprite_flags[src_id] & SPRITE_FLAG_ACTIVE) == 0:
        return False
    if (_sprite_flags[dst_id] & SPRITE_FLAG_ACTIVE) == 0:
        return False

    if _sprite_width[src_id] != _sprite_width[dst_id]:
        return False
    if _sprite_height[src_id] != _sprite_height[dst_id]:
        return False

    size: int32 = _sprite_width[src_id] * _sprite_height[src_id] * 4
    memcpy(cast[Ptr[uint8]](_sprite_data[dst_id]),
           cast[Ptr[uint8]](_sprite_data[src_id]), size)

    # Copy alpha flag
    if (_sprite_flags[src_id] & SPRITE_FLAG_ALPHA) != 0:
        _sprite_flags[dst_id] = _sprite_flags[dst_id] | SPRITE_FLAG_ALPHA
    else:
        _sprite_flags[dst_id] = _sprite_flags[dst_id] & (~SPRITE_FLAG_ALPHA)

    return True

# ============================================================================
# Helper Functions
# ============================================================================

def _sin_deg(deg: int32) -> int32:
    """Sine of angle in degrees, scaled by 256."""
    # Normalize to 0-359
    while deg < 0:
        deg = deg + 360
    while deg >= 360:
        deg = deg - 360

    neg: bool = False
    if deg > 180:
        deg = deg - 180
        neg = True
    if deg > 90:
        deg = 180 - deg

    # Quadratic approximation
    result: int32 = 4 * deg * (90 - _abs(deg - 90)) * 256 / 8100

    if neg:
        return -result
    return result

def _cos_deg(deg: int32) -> int32:
    """Cosine of angle in degrees, scaled by 256."""
    return _sin_deg(deg + 90)

def _abs(x: int32) -> int32:
    """Absolute value."""
    if x < 0:
        return -x
    return x
