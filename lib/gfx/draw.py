# Pynux Graphics Library - Drawing Primitives
#
# Basic drawing operations using Bresenham algorithms.
# All drawing is done to the current framebuffer.

from lib.gfx.framebuffer import fb_set_pixel, fb_get_width, fb_get_height, fb_is_initialized

# ============================================================================
# Helper Functions
# ============================================================================

def _abs(x: int32) -> int32:
    """Absolute value."""
    if x < 0:
        return -x
    return x

def _swap_int(a: Ptr[int32], b: Ptr[int32]):
    """Swap two integers via pointers."""
    t: int32 = a[0]
    a[0] = b[0]
    b[0] = t

def _min(a: int32, b: int32) -> int32:
    """Minimum of two integers."""
    if a < b:
        return a
    return b

def _max(a: int32, b: int32) -> int32:
    """Maximum of two integers."""
    if a > b:
        return a
    return b

def _clamp(x: int32, lo: int32, hi: int32) -> int32:
    """Clamp value between lo and hi."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x

# ============================================================================
# Line Drawing (Bresenham's Algorithm)
# ============================================================================

def draw_line(x1: int32, y1: int32, x2: int32, y2: int32, color: uint32):
    """Draw a line using Bresenham's algorithm.

    Args:
        x1, y1: Start point
        x2, y2: End point
        color: Line color (32-bit ARGB)
    """
    if not fb_is_initialized():
        return

    dx: int32 = _abs(x2 - x1)
    dy: int32 = -_abs(y2 - y1)

    sx: int32 = 1 if x1 < x2 else -1
    sy: int32 = 1 if y1 < y2 else -1

    err: int32 = dx + dy

    x: int32 = x1
    y: int32 = y1

    while True:
        fb_set_pixel(x, y, color)

        if x == x2 and y == y2:
            break

        e2: int32 = 2 * err

        if e2 >= dy:
            err = err + dy
            x = x + sx

        if e2 <= dx:
            err = err + dx
            y = y + sy

def draw_hline(x: int32, y: int32, w: int32, color: uint32):
    """Draw horizontal line (optimized).

    Args:
        x, y: Start point
        w: Width (can be negative)
        color: Line color
    """
    if not fb_is_initialized():
        return

    if w < 0:
        x = x + w
        w = -w

    i: int32 = 0
    while i < w:
        fb_set_pixel(x + i, y, color)
        i = i + 1

def draw_vline(x: int32, y: int32, h: int32, color: uint32):
    """Draw vertical line (optimized).

    Args:
        x, y: Start point
        h: Height (can be negative)
        color: Line color
    """
    if not fb_is_initialized():
        return

    if h < 0:
        y = y + h
        h = -h

    i: int32 = 0
    while i < h:
        fb_set_pixel(x, y + i, color)
        i = i + 1

# ============================================================================
# Rectangle Drawing
# ============================================================================

def draw_rect(x: int32, y: int32, w: int32, h: int32, color: uint32):
    """Draw rectangle outline.

    Args:
        x, y: Top-left corner
        w, h: Width and height
        color: Border color
    """
    if not fb_is_initialized():
        return

    if w <= 0 or h <= 0:
        return

    # Top edge
    draw_hline(x, y, w, color)
    # Bottom edge
    draw_hline(x, y + h - 1, w, color)
    # Left edge
    draw_vline(x, y, h, color)
    # Right edge
    draw_vline(x + w - 1, y, h, color)

def draw_fill_rect(x: int32, y: int32, w: int32, h: int32, color: uint32):
    """Draw filled rectangle.

    Args:
        x, y: Top-left corner
        w, h: Width and height
        color: Fill color
    """
    if not fb_is_initialized():
        return

    if w <= 0 or h <= 0:
        return

    row: int32 = 0
    while row < h:
        draw_hline(x, y + row, w, color)
        row = row + 1

def draw_rounded_rect(x: int32, y: int32, w: int32, h: int32, r: int32, color: uint32):
    """Draw rectangle with rounded corners.

    Args:
        x, y: Top-left corner
        w, h: Width and height
        r: Corner radius
        color: Border color
    """
    if not fb_is_initialized():
        return

    if w <= 0 or h <= 0:
        return

    # Clamp radius
    max_r: int32 = _min(w / 2, h / 2)
    if r > max_r:
        r = max_r
    if r < 0:
        r = 0

    # Horizontal lines (top and bottom)
    draw_hline(x + r, y, w - 2 * r, color)
    draw_hline(x + r, y + h - 1, w - 2 * r, color)

    # Vertical lines (left and right)
    draw_vline(x, y + r, h - 2 * r, color)
    draw_vline(x + w - 1, y + r, h - 2 * r, color)

    # Corners (using circle arcs)
    _draw_corner(x + r, y + r, r, 1, color)              # Top-left
    _draw_corner(x + w - 1 - r, y + r, r, 2, color)      # Top-right
    _draw_corner(x + r, y + h - 1 - r, r, 4, color)      # Bottom-left
    _draw_corner(x + w - 1 - r, y + h - 1 - r, r, 8, color)  # Bottom-right

def _draw_corner(cx: int32, cy: int32, r: int32, corner: int32, color: uint32):
    """Draw a quarter circle arc (corner of rounded rect).

    Args:
        cx, cy: Center
        r: Radius
        corner: Bitmask (1=TL, 2=TR, 4=BL, 8=BR)
        color: Color
    """
    x: int32 = r
    y: int32 = 0
    err: int32 = 1 - r

    while x >= y:
        if (corner & 1) != 0:  # Top-left
            fb_set_pixel(cx - x, cy - y, color)
            fb_set_pixel(cx - y, cy - x, color)
        if (corner & 2) != 0:  # Top-right
            fb_set_pixel(cx + x, cy - y, color)
            fb_set_pixel(cx + y, cy - x, color)
        if (corner & 4) != 0:  # Bottom-left
            fb_set_pixel(cx - x, cy + y, color)
            fb_set_pixel(cx - y, cy + x, color)
        if (corner & 8) != 0:  # Bottom-right
            fb_set_pixel(cx + x, cy + y, color)
            fb_set_pixel(cx + y, cy + x, color)

        y = y + 1
        if err < 0:
            err = err + 2 * y + 1
        else:
            x = x - 1
            err = err + 2 * (y - x + 1)

# ============================================================================
# Circle Drawing (Bresenham's Midpoint Algorithm)
# ============================================================================

def draw_circle(cx: int32, cy: int32, r: int32, color: uint32):
    """Draw circle outline using Bresenham's midpoint algorithm.

    Args:
        cx, cy: Center point
        r: Radius
        color: Circle color
    """
    if not fb_is_initialized():
        return

    if r <= 0:
        fb_set_pixel(cx, cy, color)
        return

    x: int32 = r
    y: int32 = 0
    err: int32 = 1 - r

    while x >= y:
        # Draw 8 symmetric points
        fb_set_pixel(cx + x, cy + y, color)
        fb_set_pixel(cx + y, cy + x, color)
        fb_set_pixel(cx - y, cy + x, color)
        fb_set_pixel(cx - x, cy + y, color)
        fb_set_pixel(cx - x, cy - y, color)
        fb_set_pixel(cx - y, cy - x, color)
        fb_set_pixel(cx + y, cy - x, color)
        fb_set_pixel(cx + x, cy - y, color)

        y = y + 1
        if err < 0:
            err = err + 2 * y + 1
        else:
            x = x - 1
            err = err + 2 * (y - x + 1)

def draw_fill_circle(cx: int32, cy: int32, r: int32, color: uint32):
    """Draw filled circle.

    Args:
        cx, cy: Center point
        r: Radius
        color: Fill color
    """
    if not fb_is_initialized():
        return

    if r <= 0:
        fb_set_pixel(cx, cy, color)
        return

    x: int32 = r
    y: int32 = 0
    err: int32 = 1 - r

    while x >= y:
        # Draw horizontal lines to fill
        draw_hline(cx - x, cy + y, 2 * x + 1, color)
        draw_hline(cx - x, cy - y, 2 * x + 1, color)
        draw_hline(cx - y, cy + x, 2 * y + 1, color)
        draw_hline(cx - y, cy - x, 2 * y + 1, color)

        y = y + 1
        if err < 0:
            err = err + 2 * y + 1
        else:
            x = x - 1
            err = err + 2 * (y - x + 1)

# ============================================================================
# Ellipse Drawing
# ============================================================================

def draw_ellipse(cx: int32, cy: int32, rx: int32, ry: int32, color: uint32):
    """Draw ellipse outline.

    Args:
        cx, cy: Center point
        rx: X radius
        ry: Y radius
        color: Ellipse color
    """
    if not fb_is_initialized():
        return

    if rx <= 0 or ry <= 0:
        fb_set_pixel(cx, cy, color)
        return

    # Bresenham ellipse algorithm
    x: int32 = 0
    y: int32 = ry
    rx2: int32 = rx * rx
    ry2: int32 = ry * ry

    # Region 1
    px: int32 = 0
    py: int32 = 2 * rx2 * y

    # Initial decision parameter
    p: int32 = ry2 - rx2 * ry + rx2 / 4

    while px < py:
        fb_set_pixel(cx + x, cy + y, color)
        fb_set_pixel(cx - x, cy + y, color)
        fb_set_pixel(cx + x, cy - y, color)
        fb_set_pixel(cx - x, cy - y, color)

        x = x + 1
        px = px + 2 * ry2

        if p < 0:
            p = p + ry2 + px
        else:
            y = y - 1
            py = py - 2 * rx2
            p = p + ry2 + px - py

    # Region 2
    p = ry2 * (x * 2 + 1) * (x * 2 + 1) / 4 + rx2 * (y - 1) * (y - 1) - rx2 * ry2

    while y >= 0:
        fb_set_pixel(cx + x, cy + y, color)
        fb_set_pixel(cx - x, cy + y, color)
        fb_set_pixel(cx + x, cy - y, color)
        fb_set_pixel(cx - x, cy - y, color)

        y = y - 1
        py = py - 2 * rx2

        if p > 0:
            p = p + rx2 - py
        else:
            x = x + 1
            px = px + 2 * ry2
            p = p + rx2 - py + px

def draw_fill_ellipse(cx: int32, cy: int32, rx: int32, ry: int32, color: uint32):
    """Draw filled ellipse.

    Args:
        cx, cy: Center point
        rx: X radius
        ry: Y radius
        color: Fill color
    """
    if not fb_is_initialized():
        return

    if rx <= 0 or ry <= 0:
        fb_set_pixel(cx, cy, color)
        return

    # Simple scanline fill
    y: int32 = -ry
    while y <= ry:
        # Calculate x extent at this y
        # x^2/rx^2 + y^2/ry^2 = 1
        # x = rx * sqrt(1 - y^2/ry^2)
        y_sq: int32 = y * y
        ry_sq: int32 = ry * ry
        rx_sq: int32 = rx * rx

        # x = rx * sqrt(ry^2 - y^2) / ry
        inner: int32 = ry_sq - y_sq
        if inner >= 0:
            # Integer sqrt approximation
            x_extent: int32 = rx * _isqrt(inner) / ry
            draw_hline(cx - x_extent, cy + y, 2 * x_extent + 1, color)

        y = y + 1

def _isqrt(n: int32) -> int32:
    """Integer square root."""
    if n < 0:
        return 0
    if n < 2:
        return n

    x: int32 = n
    y: int32 = (x + 1) / 2

    while y < x:
        x = y
        y = (x + n / x) / 2

    return x

# ============================================================================
# Triangle Drawing
# ============================================================================

def draw_triangle(x1: int32, y1: int32, x2: int32, y2: int32, x3: int32, y3: int32, color: uint32):
    """Draw triangle outline.

    Args:
        x1, y1: First vertex
        x2, y2: Second vertex
        x3, y3: Third vertex
        color: Triangle color
    """
    draw_line(x1, y1, x2, y2, color)
    draw_line(x2, y2, x3, y3, color)
    draw_line(x3, y3, x1, y1, color)

def draw_fill_triangle(x1: int32, y1: int32, x2: int32, y2: int32, x3: int32, y3: int32, color: uint32):
    """Draw filled triangle using scanline algorithm.

    Args:
        x1, y1: First vertex
        x2, y2: Second vertex
        x3, y3: Third vertex
        color: Fill color
    """
    if not fb_is_initialized():
        return

    # Sort vertices by y coordinate (y1 <= y2 <= y3)
    if y1 > y2:
        t: int32 = y1
        y1 = y2
        y2 = t
        t = x1
        x1 = x2
        x2 = t

    if y1 > y3:
        t: int32 = y1
        y1 = y3
        y3 = t
        t = x1
        x1 = x3
        x3 = t

    if y2 > y3:
        t: int32 = y2
        y2 = y3
        y3 = t
        t = x2
        x2 = x3
        x3 = t

    # Handle flat top or flat bottom triangles
    total_height: int32 = y3 - y1
    if total_height == 0:
        # Degenerate triangle (all on same line)
        min_x: int32 = _min(_min(x1, x2), x3)
        max_x: int32 = _max(_max(x1, x2), x3)
        draw_hline(min_x, y1, max_x - min_x + 1, color)
        return

    # Fill triangle using scanline
    y: int32 = y1
    while y <= y3:
        second_half: bool = y > y2 or y1 == y2
        segment_height: int32 = y2 - y1 if not second_half else y3 - y2

        if segment_height == 0:
            segment_height = 1

        alpha: int32 = (y - y1) * 256 / total_height

        beta: int32 = 0
        if not second_half:
            beta = (y - y1) * 256 / segment_height
        else:
            beta = (y - y2) * 256 / segment_height

        # Interpolate x coordinates
        ax: int32 = x1 + (x3 - x1) * alpha / 256
        bx: int32 = 0
        if not second_half:
            bx = x1 + (x2 - x1) * beta / 256
        else:
            bx = x2 + (x3 - x2) * beta / 256

        if ax > bx:
            t: int32 = ax
            ax = bx
            bx = t

        draw_hline(ax, y, bx - ax + 1, color)
        y = y + 1

# ============================================================================
# Polygon Drawing
# ============================================================================

def draw_polygon(points: Ptr[int32], n: int32, color: uint32):
    """Draw polygon outline.

    Points are stored as [x0, y0, x1, y1, x2, y2, ...].

    Args:
        points: Pointer to array of x,y coordinate pairs
        n: Number of vertices
        color: Polygon color
    """
    if not fb_is_initialized():
        return

    if n < 2:
        return

    # Draw lines between consecutive points
    i: int32 = 0
    while i < n - 1:
        x1: int32 = points[i * 2]
        y1: int32 = points[i * 2 + 1]
        x2: int32 = points[(i + 1) * 2]
        y2: int32 = points[(i + 1) * 2 + 1]
        draw_line(x1, y1, x2, y2, color)
        i = i + 1

    # Close the polygon
    x1: int32 = points[(n - 1) * 2]
    y1: int32 = points[(n - 1) * 2 + 1]
    x2: int32 = points[0]
    y2: int32 = points[1]
    draw_line(x1, y1, x2, y2, color)

def draw_fill_polygon(points: Ptr[int32], n: int32, color: uint32):
    """Draw filled polygon using scanline algorithm.

    Points are stored as [x0, y0, x1, y1, x2, y2, ...].
    Uses an even-odd fill rule.

    Args:
        points: Pointer to array of x,y coordinate pairs
        n: Number of vertices
        color: Fill color
    """
    if not fb_is_initialized():
        return

    if n < 3:
        return

    # Find bounding box
    min_y: int32 = points[1]
    max_y: int32 = points[1]
    i: int32 = 1
    while i < n:
        y: int32 = points[i * 2 + 1]
        if y < min_y:
            min_y = y
        if y > max_y:
            max_y = y
        i = i + 1

    # Scanline fill
    # Allocate array for node X coordinates (max n intersections per scanline)
    # For simplicity, use fixed size array
    node_x: Array[64, int32]

    y: int32 = min_y
    while y <= max_y:
        # Build list of nodes (x intersections)
        nodes: int32 = 0
        j: int32 = n - 1
        i = 0
        while i < n:
            y_i: int32 = points[i * 2 + 1]
            y_j: int32 = points[j * 2 + 1]

            if (y_i < y and y_j >= y) or (y_j < y and y_i >= y):
                x_i: int32 = points[i * 2]
                x_j: int32 = points[j * 2]
                # Calculate intersection x
                ix: int32 = x_i + (y - y_i) * (x_j - x_i) / (y_j - y_i)
                if nodes < 64:
                    node_x[nodes] = ix
                    nodes = nodes + 1

            j = i
            i = i + 1

        # Sort nodes by x (simple bubble sort)
        si: int32 = 0
        while si < nodes - 1:
            sj: int32 = si + 1
            while sj < nodes:
                if node_x[si] > node_x[sj]:
                    t: int32 = node_x[si]
                    node_x[si] = node_x[sj]
                    node_x[sj] = t
                sj = sj + 1
            si = si + 1

        # Fill between pairs of nodes
        ni: int32 = 0
        while ni < nodes - 1:
            draw_hline(node_x[ni], y, node_x[ni + 1] - node_x[ni] + 1, color)
            ni = ni + 2

        y = y + 1

# ============================================================================
# Arc Drawing
# ============================================================================

def draw_arc(cx: int32, cy: int32, r: int32, start_angle: int32, end_angle: int32, color: uint32):
    """Draw arc (portion of circle).

    Args:
        cx, cy: Center point
        r: Radius
        start_angle: Start angle in degrees (0 = right, 90 = up)
        end_angle: End angle in degrees
        color: Arc color
    """
    if not fb_is_initialized():
        return

    if r <= 0:
        return

    # Normalize angles
    while start_angle < 0:
        start_angle = start_angle + 360
    while start_angle >= 360:
        start_angle = start_angle - 360
    while end_angle < 0:
        end_angle = end_angle + 360
    while end_angle >= 360:
        end_angle = end_angle - 360

    # Draw using parametric approach with small steps
    angle: int32 = start_angle
    while True:
        # Calculate point on circle
        # Use simple sin/cos approximation
        x: int32 = cx + (r * _cos_approx(angle)) / 256
        y: int32 = cy - (r * _sin_approx(angle)) / 256  # Y is inverted

        fb_set_pixel(x, y, color)

        if angle == end_angle:
            break

        angle = angle + 1
        if angle >= 360:
            angle = 0

        # Handle wrap-around
        if start_angle > end_angle:
            if angle == 0:
                # Just wrapped, continue
                pass
        elif angle > end_angle:
            break

def _sin_approx(deg: int32) -> int32:
    """Approximate sine * 256 for integer math."""
    # Simple lookup with linear interpolation
    # sin values for 0, 30, 45, 60, 90 degrees * 256
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

    # Approximate using quadratic
    # sin(x) ~= (4x(180-x)) / (40500 - x(180-x))  for x in degrees
    # Simplified: sin(x) ~= 4*x*(90-|x-90|) / 8100 for 0-180
    result: int32 = 4 * deg * (90 - _abs(deg - 90)) * 256 / 8100

    if neg:
        return -result
    return result

def _cos_approx(deg: int32) -> int32:
    """Approximate cosine * 256 for integer math."""
    return _sin_approx(deg + 90)

# ============================================================================
# Bezier Curves
# ============================================================================

def draw_bezier_quad(x0: int32, y0: int32, x1: int32, y1: int32, x2: int32, y2: int32, color: uint32):
    """Draw quadratic Bezier curve.

    Args:
        x0, y0: Start point
        x1, y1: Control point
        x2, y2: End point
        color: Curve color
    """
    if not fb_is_initialized():
        return

    # Use de Casteljau's algorithm with fixed steps
    steps: int32 = 32

    prev_x: int32 = x0
    prev_y: int32 = y0

    t: int32 = 1
    while t <= steps:
        # t_scaled is t/steps in fixed-point (* 256)
        t_scaled: int32 = t * 256 / steps
        inv_t: int32 = 256 - t_scaled

        # B(t) = (1-t)^2 * P0 + 2*(1-t)*t * P1 + t^2 * P2
        # All multiplied by 256^2, then divided by 256^2
        term0: int32 = inv_t * inv_t / 256
        term1: int32 = 2 * inv_t * t_scaled / 256
        term2: int32 = t_scaled * t_scaled / 256

        bx: int32 = (term0 * x0 + term1 * x1 + term2 * x2) / 256
        by: int32 = (term0 * y0 + term1 * y1 + term2 * y2) / 256

        draw_line(prev_x, prev_y, bx, by, color)

        prev_x = bx
        prev_y = by
        t = t + 1

def draw_bezier_cubic(x0: int32, y0: int32, x1: int32, y1: int32,
                       x2: int32, y2: int32, x3: int32, y3: int32, color: uint32):
    """Draw cubic Bezier curve.

    Args:
        x0, y0: Start point
        x1, y1: First control point
        x2, y2: Second control point
        x3, y3: End point
        color: Curve color
    """
    if not fb_is_initialized():
        return

    steps: int32 = 48

    prev_x: int32 = x0
    prev_y: int32 = y0

    t: int32 = 1
    while t <= steps:
        t_scaled: int32 = t * 256 / steps
        inv_t: int32 = 256 - t_scaled

        # B(t) = (1-t)^3*P0 + 3*(1-t)^2*t*P1 + 3*(1-t)*t^2*P2 + t^3*P3
        term0: int32 = inv_t * inv_t / 256 * inv_t / 256
        term1: int32 = 3 * inv_t * inv_t / 256 * t_scaled / 256
        term2: int32 = 3 * inv_t * t_scaled / 256 * t_scaled / 256
        term3: int32 = t_scaled * t_scaled / 256 * t_scaled / 256

        bx: int32 = (term0 * x0 + term1 * x1 + term2 * x2 + term3 * x3) / 256
        by: int32 = (term0 * y0 + term1 * y1 + term2 * y2 + term3 * y3) / 256

        draw_line(prev_x, prev_y, bx, by, color)

        prev_x = bx
        prev_y = by
        t = t + 1
