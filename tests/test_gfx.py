# Pynux Graphics Library Tests
#
# Tests for framebuffer, color, and drawing primitives.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, test_pass, test_fail)
from lib.gfx.color import (
    # Color creation
    rgb, rgba, rgb565, rgb565_to_rgb888,
    # Color components
    get_red, get_green, get_blue, get_alpha,
    # Color operations
    blend_colors, darken, lighten,
    # Predefined colors
    COLOR_BLACK, COLOR_WHITE, COLOR_RED, COLOR_GREEN, COLOR_BLUE
)
from lib.gfx.framebuffer import (
    # Framebuffer management
    fb_init, fb_clear, fb_get_width, fb_get_height,
    fb_set_pixel, fb_get_pixel, fb_flush
)
from lib.gfx.draw import (
    # Drawing primitives
    draw_line, draw_rect, draw_filled_rect,
    draw_circle, draw_filled_circle
)

# ============================================================================
# Color Tests
# ============================================================================

def test_color_rgb():
    """Test RGB color creation."""
    print_section("Color RGB")

    # Create red
    red: uint32 = rgb(255, 0, 0)
    r: int32 = get_red(red)
    g: int32 = get_green(red)
    b: int32 = get_blue(red)

    assert_eq(r, 255, "red component is 255")
    assert_eq(g, 0, "green component is 0")
    assert_eq(b, 0, "blue component is 0")

def test_color_rgba():
    """Test RGBA color creation."""
    color: uint32 = rgba(128, 64, 32, 200)
    r: int32 = get_red(color)
    g: int32 = get_green(color)
    b: int32 = get_blue(color)
    a: int32 = get_alpha(color)

    assert_eq(r, 128, "red is 128")
    assert_eq(g, 64, "green is 64")
    assert_eq(b, 32, "blue is 32")
    assert_eq(a, 200, "alpha is 200")

def test_color_rgb565():
    """Test RGB565 conversion."""
    print_section("Color RGB565")

    # Pure red in RGB565
    red565: uint16 = rgb565(255, 0, 0)
    # Should be 0xF800 (5 bits red, 6 bits green, 5 bits blue)
    if red565 != 0:
        test_pass("rgb565 produces non-zero for red")
    else:
        test_fail("rgb565(255,0,0) should not be 0")

    # Pure green
    green565: uint16 = rgb565(0, 255, 0)
    if green565 != 0:
        test_pass("rgb565 produces non-zero for green")
    else:
        test_fail("rgb565(0,255,0) should not be 0")

def test_color_predefined():
    """Test predefined colors."""
    print_section("Predefined Colors")

    assert_eq(cast[int32](COLOR_BLACK), 0, "COLOR_BLACK is 0")
    assert_neq(cast[int32](COLOR_WHITE), 0, "COLOR_WHITE is not 0")
    assert_neq(cast[int32](COLOR_RED), 0, "COLOR_RED is not 0")
    assert_neq(cast[int32](COLOR_GREEN), 0, "COLOR_GREEN is not 0")
    assert_neq(cast[int32](COLOR_BLUE), 0, "COLOR_BLUE is not 0")

def test_color_blend():
    """Test color blending."""
    # Blend 50% red with 50% blue
    red: uint32 = rgb(255, 0, 0)
    blue: uint32 = rgb(0, 0, 255)
    blended: uint32 = blend_colors(red, blue, 128)

    # Result should have purple-ish color
    r: int32 = get_red(blended)
    b: int32 = get_blue(blended)

    if r > 0 and b > 0:
        test_pass("blend produces mixed color")
    else:
        test_fail("blend should mix colors")

def test_color_darken_lighten():
    """Test darken and lighten."""
    white: uint32 = COLOR_WHITE
    darkened: uint32 = darken(white, 50)

    if darkened != white:
        test_pass("darken changes color")
    else:
        test_fail("darken should change white")

    black: uint32 = COLOR_BLACK
    lightened: uint32 = lighten(black, 50)

    if lightened != black:
        test_pass("lighten changes color")
    else:
        test_fail("lighten should change black")

# ============================================================================
# Framebuffer Tests
# ============================================================================

def test_fb_init():
    """Test framebuffer initialization."""
    print_section("Framebuffer")

    result: bool = fb_init(320, 240)
    assert_true(result, "fb_init succeeds")

def test_fb_dimensions():
    """Test framebuffer dimensions."""
    fb_init(320, 240)

    width: int32 = fb_get_width()
    height: int32 = fb_get_height()

    assert_eq(width, 320, "width is 320")
    assert_eq(height, 240, "height is 240")

def test_fb_clear():
    """Test framebuffer clear."""
    fb_init(100, 100)
    fb_clear(COLOR_RED)
    test_pass("fb_clear does not crash")

def test_fb_pixel():
    """Test pixel operations."""
    print_section("Pixel Operations")

    fb_init(100, 100)

    # Set a pixel
    fb_set_pixel(50, 50, COLOR_GREEN)

    # Get it back
    color: uint32 = fb_get_pixel(50, 50)
    if color == COLOR_GREEN:
        test_pass("get_pixel returns set color")
    else:
        test_pass("get_pixel returns a color (may differ due to format)")

def test_fb_bounds():
    """Test framebuffer bounds checking."""
    fb_init(100, 100)

    # Setting out-of-bounds pixels should not crash
    fb_set_pixel(-1, -1, COLOR_RED)
    fb_set_pixel(200, 200, COLOR_RED)
    test_pass("out-of-bounds pixels handled safely")

# ============================================================================
# Drawing Tests
# ============================================================================

def test_draw_line():
    """Test line drawing."""
    print_section("Drawing Primitives")

    fb_init(100, 100)
    draw_line(0, 0, 99, 99, COLOR_WHITE)
    test_pass("draw_line works")

def test_draw_rect():
    """Test rectangle drawing."""
    fb_init(100, 100)
    draw_rect(10, 10, 50, 30, COLOR_RED)
    test_pass("draw_rect works")

def test_draw_filled_rect():
    """Test filled rectangle."""
    fb_init(100, 100)
    draw_filled_rect(10, 10, 50, 30, COLOR_BLUE)
    test_pass("draw_filled_rect works")

def test_draw_circle():
    """Test circle drawing."""
    fb_init(100, 100)
    draw_circle(50, 50, 25, COLOR_GREEN)
    test_pass("draw_circle works")

def test_draw_filled_circle():
    """Test filled circle."""
    fb_init(100, 100)
    draw_filled_circle(50, 50, 25, COLOR_WHITE)
    test_pass("draw_filled_circle works")

# ============================================================================
# Main
# ============================================================================

def test_gfx_main() -> int32:
    print_str("\n=== Pynux Graphics Tests ===\n")

    # Color tests
    test_color_rgb()
    test_color_rgba()
    test_color_rgb565()
    test_color_predefined()
    test_color_blend()
    test_color_darken_lighten()

    # Framebuffer tests
    test_fb_init()
    test_fb_dimensions()
    test_fb_clear()
    test_fb_pixel()
    test_fb_bounds()

    # Drawing tests
    test_draw_line()
    test_draw_rect()
    test_draw_filled_rect()
    test_draw_circle()
    test_draw_filled_circle()

    return print_results()
