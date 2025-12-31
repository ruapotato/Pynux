# Pynux Graphics Library - Color Utilities
#
# Color conversion and manipulation for bare-metal ARM.
# Provides RGB, RGBA, HSV conversion and common color constants.

# ============================================================================
# Common Color Constants (32-bit ARGB format: 0xAARRGGBB)
# ============================================================================

BLACK: uint32 = 0xFF000000
WHITE: uint32 = 0xFFFFFFFF
RED: uint32 = 0xFFFF0000
GREEN: uint32 = 0xFF00FF00
BLUE: uint32 = 0xFF0000FF
YELLOW: uint32 = 0xFFFFFF00
CYAN: uint32 = 0xFF00FFFF
MAGENTA: uint32 = 0xFFFF00FF
ORANGE: uint32 = 0xFFFF8000
PURPLE: uint32 = 0xFF800080
PINK: uint32 = 0xFFFF69B4
BROWN: uint32 = 0xFF8B4513
GRAY: uint32 = 0xFF808080
DARK_GRAY: uint32 = 0xFF404040
LIGHT_GRAY: uint32 = 0xFFC0C0C0
TRANSPARENT: uint32 = 0x00000000

# ============================================================================
# Color Creation Functions
# ============================================================================

def rgb(r: int32, g: int32, b: int32) -> uint32:
    """Create 32-bit color from RGB components (0-255 each).

    Args:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)

    Returns:
        32-bit ARGB color (alpha = 255)
    """
    # Clamp values to 0-255
    if r < 0:
        r = 0
    if r > 255:
        r = 255
    if g < 0:
        g = 0
    if g > 255:
        g = 255
    if b < 0:
        b = 0
    if b > 255:
        b = 255

    return 0xFF000000 | (cast[uint32](r) << 16) | (cast[uint32](g) << 8) | cast[uint32](b)

def rgba(r: int32, g: int32, b: int32, a: int32) -> uint32:
    """Create 32-bit color from RGBA components (0-255 each).

    Args:
        r: Red component (0-255)
        g: Green component (0-255)
        b: Blue component (0-255)
        a: Alpha component (0-255, 0=transparent, 255=opaque)

    Returns:
        32-bit ARGB color
    """
    # Clamp values to 0-255
    if r < 0:
        r = 0
    if r > 255:
        r = 255
    if g < 0:
        g = 0
    if g > 255:
        g = 255
    if b < 0:
        b = 0
    if b > 255:
        b = 255
    if a < 0:
        a = 0
    if a > 255:
        a = 255

    return (cast[uint32](a) << 24) | (cast[uint32](r) << 16) | (cast[uint32](g) << 8) | cast[uint32](b)

def hsv_to_rgb(h: int32, s: int32, v: int32) -> uint32:
    """Convert HSV color to RGB.

    Args:
        h: Hue (0-359 degrees)
        s: Saturation (0-255)
        v: Value/Brightness (0-255)

    Returns:
        32-bit ARGB color
    """
    # Normalize hue to 0-359
    while h < 0:
        h = h + 360
    while h >= 360:
        h = h - 360

    # Clamp s and v
    if s < 0:
        s = 0
    if s > 255:
        s = 255
    if v < 0:
        v = 0
    if v > 255:
        v = 255

    # If saturation is 0, return grayscale
    if s == 0:
        return rgb(v, v, v)

    # Calculate color
    # sector: 0-5 (which 60-degree sector of the color wheel)
    sector: int32 = h / 60
    remainder: int32 = (h - sector * 60) * 255 / 60

    p: int32 = (v * (255 - s)) / 255
    q: int32 = (v * (255 - (s * remainder) / 255)) / 255
    t: int32 = (v * (255 - (s * (255 - remainder)) / 255)) / 255

    r: int32 = 0
    g: int32 = 0
    b: int32 = 0

    if sector == 0:
        r = v
        g = t
        b = p
    elif sector == 1:
        r = q
        g = v
        b = p
    elif sector == 2:
        r = p
        g = v
        b = t
    elif sector == 3:
        r = p
        g = q
        b = v
    elif sector == 4:
        r = t
        g = p
        b = v
    else:
        r = v
        g = p
        b = q

    return rgb(r, g, b)

# ============================================================================
# Color Component Extraction
# ============================================================================

def color_get_r(color: uint32) -> int32:
    """Extract red component from color.

    Args:
        color: 32-bit ARGB color

    Returns:
        Red component (0-255)
    """
    return cast[int32]((color >> 16) & 0xFF)

def color_get_g(color: uint32) -> int32:
    """Extract green component from color.

    Args:
        color: 32-bit ARGB color

    Returns:
        Green component (0-255)
    """
    return cast[int32]((color >> 8) & 0xFF)

def color_get_b(color: uint32) -> int32:
    """Extract blue component from color.

    Args:
        color: 32-bit ARGB color

    Returns:
        Blue component (0-255)
    """
    return cast[int32](color & 0xFF)

def color_get_a(color: uint32) -> int32:
    """Extract alpha component from color.

    Args:
        color: 32-bit ARGB color

    Returns:
        Alpha component (0-255)
    """
    return cast[int32]((color >> 24) & 0xFF)

# ============================================================================
# Color Manipulation
# ============================================================================

def color_blend(fg: uint32, bg: uint32) -> uint32:
    """Blend foreground color over background using alpha.

    Args:
        fg: Foreground color (ARGB)
        bg: Background color (ARGB)

    Returns:
        Blended color
    """
    fg_a: int32 = color_get_a(fg)

    # Fully transparent foreground
    if fg_a == 0:
        return bg

    # Fully opaque foreground
    if fg_a == 255:
        return fg

    # Alpha blending
    bg_a: int32 = 255 - fg_a

    r: int32 = (color_get_r(fg) * fg_a + color_get_r(bg) * bg_a) / 255
    g: int32 = (color_get_g(fg) * fg_a + color_get_g(bg) * bg_a) / 255
    b: int32 = (color_get_b(fg) * fg_a + color_get_b(bg) * bg_a) / 255

    return rgb(r, g, b)

def color_lerp(c1: uint32, c2: uint32, t: int32) -> uint32:
    """Linear interpolation between two colors.

    Args:
        c1: First color
        c2: Second color
        t: Interpolation factor (0-255, 0=c1, 255=c2)

    Returns:
        Interpolated color
    """
    if t <= 0:
        return c1
    if t >= 255:
        return c2

    inv_t: int32 = 255 - t

    r: int32 = (color_get_r(c1) * inv_t + color_get_r(c2) * t) / 255
    g: int32 = (color_get_g(c1) * inv_t + color_get_g(c2) * t) / 255
    b: int32 = (color_get_b(c1) * inv_t + color_get_b(c2) * t) / 255
    a: int32 = (color_get_a(c1) * inv_t + color_get_a(c2) * t) / 255

    return rgba(r, g, b, a)

def color_darken(color: uint32, amount: int32) -> uint32:
    """Darken a color by reducing RGB values.

    Args:
        color: Original color
        amount: Amount to darken (0-255)

    Returns:
        Darkened color
    """
    r: int32 = color_get_r(color) - amount
    g: int32 = color_get_g(color) - amount
    b: int32 = color_get_b(color) - amount

    if r < 0:
        r = 0
    if g < 0:
        g = 0
    if b < 0:
        b = 0

    return rgba(r, g, b, color_get_a(color))

def color_lighten(color: uint32, amount: int32) -> uint32:
    """Lighten a color by increasing RGB values.

    Args:
        color: Original color
        amount: Amount to lighten (0-255)

    Returns:
        Lightened color
    """
    r: int32 = color_get_r(color) + amount
    g: int32 = color_get_g(color) + amount
    b: int32 = color_get_b(color) + amount

    if r > 255:
        r = 255
    if g > 255:
        g = 255
    if b > 255:
        b = 255

    return rgba(r, g, b, color_get_a(color))

def color_invert(color: uint32) -> uint32:
    """Invert a color (complement).

    Args:
        color: Original color

    Returns:
        Inverted color
    """
    r: int32 = 255 - color_get_r(color)
    g: int32 = 255 - color_get_g(color)
    b: int32 = 255 - color_get_b(color)

    return rgba(r, g, b, color_get_a(color))

def color_grayscale(color: uint32) -> uint32:
    """Convert color to grayscale.

    Uses standard luminance formula: 0.299*R + 0.587*G + 0.114*B

    Args:
        color: Original color

    Returns:
        Grayscale color
    """
    # Use integer approximation: (77*R + 150*G + 29*B) / 256
    r: int32 = color_get_r(color)
    g: int32 = color_get_g(color)
    b: int32 = color_get_b(color)

    gray: int32 = (77 * r + 150 * g + 29 * b) / 256

    return rgba(gray, gray, gray, color_get_a(color))

# ============================================================================
# Color Format Conversion
# ============================================================================

def color_to_rgb565(color: uint32) -> uint16:
    """Convert 32-bit ARGB to 16-bit RGB565 format.

    RGB565: 5 bits red, 6 bits green, 5 bits blue

    Args:
        color: 32-bit ARGB color

    Returns:
        16-bit RGB565 color
    """
    r: int32 = (color_get_r(color) >> 3) & 0x1F  # 5 bits
    g: int32 = (color_get_g(color) >> 2) & 0x3F  # 6 bits
    b: int32 = (color_get_b(color) >> 3) & 0x1F  # 5 bits

    return cast[uint16]((r << 11) | (g << 5) | b)

def color_from_rgb565(color565: uint16) -> uint32:
    """Convert 16-bit RGB565 to 32-bit ARGB.

    Args:
        color565: 16-bit RGB565 color

    Returns:
        32-bit ARGB color
    """
    r: int32 = ((cast[int32](color565) >> 11) & 0x1F) << 3
    g: int32 = ((cast[int32](color565) >> 5) & 0x3F) << 2
    b: int32 = (cast[int32](color565) & 0x1F) << 3

    return rgb(r, g, b)

def color_to_rgb332(color: uint32) -> uint8:
    """Convert 32-bit ARGB to 8-bit RGB332 format.

    RGB332: 3 bits red, 3 bits green, 2 bits blue

    Args:
        color: 32-bit ARGB color

    Returns:
        8-bit RGB332 color
    """
    r: int32 = (color_get_r(color) >> 5) & 0x07  # 3 bits
    g: int32 = (color_get_g(color) >> 5) & 0x07  # 3 bits
    b: int32 = (color_get_b(color) >> 6) & 0x03  # 2 bits

    return cast[uint8]((r << 5) | (g << 2) | b)

def color_from_rgb332(color332: uint8) -> uint32:
    """Convert 8-bit RGB332 to 32-bit ARGB.

    Args:
        color332: 8-bit RGB332 color

    Returns:
        32-bit ARGB color
    """
    r: int32 = ((cast[int32](color332) >> 5) & 0x07) << 5
    g: int32 = ((cast[int32](color332) >> 2) & 0x07) << 5
    b: int32 = (cast[int32](color332) & 0x03) << 6

    return rgb(r, g, b)
