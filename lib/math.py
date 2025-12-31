# Pynux Math Library
#
# Mathematical functions for bare-metal ARM.
# Uses fixed-point and integer approximations where possible.

# ============================================================================
# Constants
# ============================================================================

# Integer constants
INT_MAX: int32 = 2147483647
INT_MIN: int32 = -2147483648

# Fixed-point constants (16.16 format)
FP_ONE: int32 = 65536       # 1.0 in 16.16 fixed-point
FP_HALF: int32 = 32768      # 0.5 in 16.16 fixed-point
FP_PI: int32 = 205887       # PI in 16.16 (~3.14159)
FP_2PI: int32 = 411775      # 2*PI in 16.16
FP_PI_2: int32 = 102944     # PI/2 in 16.16
FP_E: int32 = 178145        # e in 16.16 (~2.71828)

# ============================================================================
# Basic Integer Math
# ============================================================================

def abs_int(x: int32) -> int32:
    """Absolute value of integer."""
    if x < 0:
        return -x
    return x

def min_int(a: int32, b: int32) -> int32:
    """Minimum of two integers."""
    if a < b:
        return a
    return b

def max_int(a: int32, b: int32) -> int32:
    """Maximum of two integers."""
    if a > b:
        return a
    return b

def clamp(x: int32, lo: int32, hi: int32) -> int32:
    """Clamp value between lo and hi."""
    if x < lo:
        return lo
    if x > hi:
        return hi
    return x

def sign(x: int32) -> int32:
    """Return sign of integer: -1, 0, or 1."""
    if x > 0:
        return 1
    if x < 0:
        return -1
    return 0

# ============================================================================
# Integer Square Root (Newton's method)
# ============================================================================

def isqrt(n: int32) -> int32:
    """Integer square root using Newton's method."""
    if n < 0:
        return 0
    if n < 2:
        return n

    # Initial guess
    x: int32 = n
    y: int32 = (x + 1) / 2

    while y < x:
        x = y
        y = (x + n / x) / 2

    return x

def sqrt_int(n: int32) -> int32:
    """Alias for isqrt."""
    return isqrt(n)

# ============================================================================
# Integer Power
# ============================================================================

def pow_int(base: int32, exp: int32) -> int32:
    """Integer power: base^exp."""
    if exp < 0:
        return 0  # Integer division would give 0
    if exp == 0:
        return 1

    result: int32 = 1
    while exp > 0:
        if (exp & 1) == 1:
            result = result * base
        exp = exp >> 1
        base = base * base

    return result

def square(x: int32) -> int32:
    """Square of integer."""
    return x * x

def cube(x: int32) -> int32:
    """Cube of integer."""
    return x * x * x

# ============================================================================
# Division and Modulo
# ============================================================================

def div_floor(a: int32, b: int32) -> int32:
    """Floor division (rounds toward negative infinity)."""
    if b == 0:
        return 0
    q: int32 = a / b
    r: int32 = a - q * b
    if r != 0 and ((a < 0) != (b < 0)):
        q = q - 1
    return q

def div_ceil(a: int32, b: int32) -> int32:
    """Ceiling division (rounds toward positive infinity)."""
    if b == 0:
        return 0
    q: int32 = a / b
    r: int32 = a - q * b
    if r != 0 and ((a > 0) == (b > 0)):
        q = q + 1
    return q

def mod(a: int32, b: int32) -> int32:
    """Modulo that always returns non-negative result."""
    if b == 0:
        return 0
    r: int32 = a - (a / b) * b
    if r < 0:
        r = r + abs_int(b)
    return r

def gcd(a: int32, b: int32) -> int32:
    """Greatest common divisor using Euclidean algorithm."""
    a = abs_int(a)
    b = abs_int(b)
    while b != 0:
        t: int32 = b
        b = a - (a / b) * b
        a = t
    return a

def lcm(a: int32, b: int32) -> int32:
    """Least common multiple."""
    if a == 0 or b == 0:
        return 0
    return abs_int(a / gcd(a, b) * b)

# ============================================================================
# Fixed-Point Math (16.16 format)
# ============================================================================

def fp_from_int(x: int32) -> int32:
    """Convert integer to 16.16 fixed-point."""
    return x << 16

def fp_to_int(x: int32) -> int32:
    """Convert 16.16 fixed-point to integer (truncate)."""
    return x >> 16

def fp_round(x: int32) -> int32:
    """Round 16.16 fixed-point to nearest integer."""
    if x >= 0:
        return (x + FP_HALF) >> 16
    return (x - FP_HALF) >> 16

def fp_mul(a: int32, b: int32) -> int32:
    """Multiply two 16.16 fixed-point numbers."""
    # Use 64-bit intermediate (simulated with two 32-bit ops)
    # For simplicity, use shifted multiply
    return (a >> 8) * (b >> 8)

def fp_div(a: int32, b: int32) -> int32:
    """Divide two 16.16 fixed-point numbers."""
    if b == 0:
        return 0
    return (a << 8) / (b >> 8)

def fp_sqrt(x: int32) -> int32:
    """Square root of 16.16 fixed-point number."""
    if x <= 0:
        return 0
    # Scale up, take integer sqrt, adjust
    # sqrt(x * 2^16) = sqrt(x) * 2^8
    return isqrt(x) << 8

# ============================================================================
# Trigonometry (using lookup table approximation)
# ============================================================================

# Sine table for 0-90 degrees in steps of 5 degrees (16.16 fixed-point)
# sin(0), sin(5), sin(10), ..., sin(90)
sin_table: Array[19, int32]

def _init_sin_table():
    """Initialize sine lookup table."""
    # Values: sin(0°) to sin(90°) in steps of 5°
    # Stored as 16.16 fixed-point
    sin_table[0] = 0        # sin(0) = 0
    sin_table[1] = 5716     # sin(5) = 0.0872
    sin_table[2] = 11356    # sin(10) = 0.1736
    sin_table[3] = 16846    # sin(15) = 0.2588
    sin_table[4] = 22129    # sin(20) = 0.3420
    sin_table[5] = 27145    # sin(25) = 0.4226
    sin_table[6] = 31847    # sin(30) = 0.5000
    sin_table[7] = 36195    # sin(35) = 0.5736
    sin_table[8] = 40163    # sin(40) = 0.6428
    sin_table[9] = 43722    # sin(45) = 0.7071
    sin_table[10] = 46859   # sin(50) = 0.7660
    sin_table[11] = 49558   # sin(55) = 0.8192
    sin_table[12] = 51819   # sin(60) = 0.8660
    sin_table[13] = 53636   # sin(65) = 0.9063
    sin_table[14] = 55010   # sin(70) = 0.9397
    sin_table[15] = 55945   # sin(75) = 0.9659
    sin_table[16] = 56448   # sin(80) = 0.9848
    sin_table[17] = 56524   # sin(85) = 0.9962
    sin_table[18] = 65536   # sin(90) = 1.0000

def sin_deg(degrees: int32) -> int32:
    """Sine of angle in degrees. Returns 16.16 fixed-point."""
    # Normalize to 0-360
    degrees = mod(degrees, 360)

    # Use symmetry to reduce to 0-90
    flip: bool = False
    if degrees > 180:
        degrees = degrees - 180
        flip = True
    if degrees > 90:
        degrees = 180 - degrees

    # Lookup with linear interpolation
    idx: int32 = degrees / 5
    frac: int32 = degrees - idx * 5

    if idx >= 18:
        idx = 18
        frac = 0

    v0: int32 = sin_table[idx]
    v1: int32 = sin_table[idx + 1] if idx < 18 else v0
    result: int32 = v0 + (v1 - v0) * frac / 5

    if flip:
        return -result
    return result

def cos_deg(degrees: int32) -> int32:
    """Cosine of angle in degrees. Returns 16.16 fixed-point."""
    return sin_deg(degrees + 90)

def tan_deg(degrees: int32) -> int32:
    """Tangent of angle in degrees. Returns 16.16 fixed-point."""
    c: int32 = cos_deg(degrees)
    if c == 0:
        return INT_MAX
    return fp_div(sin_deg(degrees), c)

# ============================================================================
# Logarithms and Exponentials (integer approximations)
# ============================================================================

def log2_int(x: int32) -> int32:
    """Integer log base 2 (floor)."""
    if x <= 0:
        return -1
    result: int32 = 0
    while x > 1:
        x = x >> 1
        result = result + 1
    return result

def exp2_int(x: int32) -> int32:
    """Integer 2^x."""
    if x < 0:
        return 0
    if x > 30:
        return INT_MAX
    return 1 << x

def log10_int(x: int32) -> int32:
    """Integer log base 10 (floor)."""
    if x <= 0:
        return -1
    result: int32 = 0
    while x >= 10:
        x = x / 10
        result = result + 1
    return result

# ============================================================================
# Distance and Geometry
# ============================================================================

def distance_sq(x1: int32, y1: int32, x2: int32, y2: int32) -> int32:
    """Squared distance between two points."""
    dx: int32 = x2 - x1
    dy: int32 = y2 - y1
    return dx * dx + dy * dy

def distance(x1: int32, y1: int32, x2: int32, y2: int32) -> int32:
    """Integer distance between two points."""
    return isqrt(distance_sq(x1, y1, x2, y2))

def manhattan_dist(x1: int32, y1: int32, x2: int32, y2: int32) -> int32:
    """Manhattan (taxicab) distance."""
    return abs_int(x2 - x1) + abs_int(y2 - y1)

# ============================================================================
# Random Number Generation (Linear Congruential Generator)
# ============================================================================

_rand_seed: int32 = 12345

def srand(seed: int32):
    """Set random seed."""
    global _rand_seed
    _rand_seed = seed

def rand() -> int32:
    """Generate random integer (0 to INT_MAX)."""
    global _rand_seed
    # LCG parameters from Numerical Recipes
    _rand_seed = _rand_seed * 1103515245 + 12345
    return (_rand_seed >> 1) & INT_MAX

def rand_range(lo: int32, hi: int32) -> int32:
    """Random integer in range [lo, hi]."""
    if hi <= lo:
        return lo
    range_size: int32 = hi - lo + 1
    return lo + (rand() % range_size)

def rand_bool() -> bool:
    """Random boolean."""
    return (rand() & 1) == 1
