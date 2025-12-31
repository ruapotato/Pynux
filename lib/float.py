# Pynux Software Floating Point Library
#
# IEEE 754 single-precision (32-bit) floating point operations for bare-metal ARM.
# Uses software emulation since Cortex-M3 lacks hardware FPU.
#
# Float format (IEEE 754 single precision):
#   Bit 31: Sign (0 = positive, 1 = negative)
#   Bits 30-23: Exponent (8 bits, biased by 127)
#   Bits 22-0: Mantissa (23 bits, implicit 1.xxx)
#
# Special values:
#   Zero: exponent=0, mantissa=0
#   Infinity: exponent=255, mantissa=0
#   NaN: exponent=255, mantissa!=0
#   Denormal: exponent=0, mantissa!=0

# Constants
F_ZERO: uint32 = 0x00000000        # 0.0
F_ONE: uint32 = 0x3F800000         # 1.0
F_MINUS_ONE: uint32 = 0xBF800000   # -1.0
F_TWO: uint32 = 0x40000000         # 2.0
F_HALF: uint32 = 0x3F000000        # 0.5
F_PI: uint32 = 0x40490FDB          # 3.14159265
F_E: uint32 = 0x402DF854           # 2.71828182
F_INF: uint32 = 0x7F800000         # +infinity
F_NINF: uint32 = 0xFF800000        # -infinity
F_NAN: uint32 = 0x7FC00000         # NaN

SIGN_MASK: uint32 = 0x80000000
EXP_MASK: uint32 = 0x7F800000
MANT_MASK: uint32 = 0x007FFFFF
EXP_BIAS: int32 = 127
MANT_BITS: int32 = 23

# ============================================================================
# Float Component Extraction
# ============================================================================

def f_sign(f: uint32) -> int32:
    """Get sign bit (0 or 1)."""
    return cast[int32]((f >> 31) & 1)

def f_exp(f: uint32) -> int32:
    """Get biased exponent (0-255)."""
    return cast[int32]((f >> 23) & 0xFF)

def f_mant(f: uint32) -> uint32:
    """Get raw mantissa (23 bits)."""
    return f & MANT_MASK

def f_is_zero(f: uint32) -> bool:
    """Check if float is zero (positive or negative)."""
    return (f & 0x7FFFFFFF) == 0

def f_is_inf(f: uint32) -> bool:
    """Check if float is infinity."""
    return (f & 0x7FFFFFFF) == F_INF

def f_is_nan(f: uint32) -> bool:
    """Check if float is NaN."""
    e: int32 = f_exp(f)
    m: uint32 = f_mant(f)
    return e == 255 and m != 0

def f_is_negative(f: uint32) -> bool:
    """Check if float is negative."""
    return (f & SIGN_MASK) != 0

def f_is_denormal(f: uint32) -> bool:
    """Check if float is denormalized."""
    return f_exp(f) == 0 and f_mant(f) != 0

# ============================================================================
# Float Construction
# ============================================================================

def f_make(sign: int32, exp: int32, mant: uint32) -> uint32:
    """Construct float from components."""
    s: uint32 = (cast[uint32](sign) & 1) << 31
    e: uint32 = (cast[uint32](exp) & 0xFF) << 23
    m: uint32 = mant & MANT_MASK
    return s | e | m

def f_negate(f: uint32) -> uint32:
    """Negate a float."""
    return f ^ SIGN_MASK

def f_abs(f: uint32) -> uint32:
    """Absolute value of float."""
    return f & 0x7FFFFFFF

# ============================================================================
# Integer to Float Conversion
# ============================================================================

def f_from_int(n: int32) -> uint32:
    """Convert signed integer to float."""
    if n == 0:
        return F_ZERO

    sign: int32 = 0
    if n < 0:
        sign = 1
        n = -n

    # Find position of highest bit
    u: uint32 = cast[uint32](n)
    exp: int32 = 31
    while exp >= 0 and ((u >> cast[uint32](exp)) & 1) == 0:
        exp = exp - 1

    # Shift mantissa to proper position
    mant: uint32
    if exp <= 23:
        mant = u << cast[uint32](23 - exp)
    else:
        mant = u >> cast[uint32](exp - 23)

    # Remove implicit 1
    mant = mant & MANT_MASK

    return f_make(sign, exp + EXP_BIAS, mant)

def f_to_int(f: uint32) -> int32:
    """Convert float to signed integer (truncate toward zero)."""
    if f_is_zero(f):
        return 0
    if f_is_nan(f):
        return 0
    if f_is_inf(f):
        if f_is_negative(f):
            return -2147483647
        return 2147483647

    sign: int32 = f_sign(f)
    exp: int32 = f_exp(f) - EXP_BIAS
    mant: uint32 = f_mant(f) | 0x00800000  # Add implicit 1

    result: int32
    if exp < 0:
        result = 0
    elif exp >= 31:
        result = 2147483647
    elif exp >= 23:
        result = cast[int32](mant << cast[uint32](exp - 23))
    else:
        result = cast[int32](mant >> cast[uint32](23 - exp))

    if sign != 0:
        result = -result
    return result

# ============================================================================
# Float Addition and Subtraction
# ============================================================================

def fadd(a: uint32, b: uint32) -> uint32:
    """Add two floats."""
    # Handle special cases
    if f_is_nan(a):
        return a
    if f_is_nan(b):
        return b
    if f_is_zero(a):
        return b
    if f_is_zero(b):
        return a
    if f_is_inf(a):
        if f_is_inf(b) and f_sign(a) != f_sign(b):
            return F_NAN  # inf + (-inf) = NaN
        return a
    if f_is_inf(b):
        return b

    # Extract components
    sign_a: int32 = f_sign(a)
    sign_b: int32 = f_sign(b)
    exp_a: int32 = f_exp(a)
    exp_b: int32 = f_exp(b)
    mant_a: uint32 = f_mant(a) | 0x00800000  # Add implicit 1
    mant_b: uint32 = f_mant(b) | 0x00800000

    # Align mantissas to same exponent
    exp_diff: int32 = exp_a - exp_b
    result_exp: int32
    result_mant: uint32
    result_sign: int32

    if exp_diff > 0:
        # a has larger exponent
        result_exp = exp_a
        if exp_diff >= 32:
            mant_b = 0
        else:
            mant_b = mant_b >> cast[uint32](exp_diff)
    elif exp_diff < 0:
        # b has larger exponent
        result_exp = exp_b
        exp_diff = -exp_diff
        if exp_diff >= 32:
            mant_a = 0
        else:
            mant_a = mant_a >> cast[uint32](exp_diff)
    else:
        result_exp = exp_a

    # Add or subtract mantissas based on signs
    if sign_a == sign_b:
        result_sign = sign_a
        result_mant = mant_a + mant_b
    else:
        if mant_a >= mant_b:
            result_sign = sign_a
            result_mant = mant_a - mant_b
        else:
            result_sign = sign_b
            result_mant = mant_b - mant_a

    # Handle zero result
    if result_mant == 0:
        return F_ZERO

    # Normalize: shift until bit 23 is set
    while result_mant >= 0x01000000:  # Bit 24 set
        result_mant = result_mant >> 1
        result_exp = result_exp + 1
    while result_mant < 0x00800000 and result_exp > 0:  # Bit 23 not set
        result_mant = result_mant << 1
        result_exp = result_exp - 1

    # Handle overflow/underflow
    if result_exp >= 255:
        if result_sign != 0:
            return F_NINF
        return F_INF
    if result_exp <= 0:
        return F_ZERO

    return f_make(result_sign, result_exp, result_mant)

def fsub(a: uint32, b: uint32) -> uint32:
    """Subtract two floats: a - b."""
    return fadd(a, f_negate(b))

# ============================================================================
# Float Multiplication
# ============================================================================

def fmul(a: uint32, b: uint32) -> uint32:
    """Multiply two floats."""
    # Handle special cases
    if f_is_nan(a):
        return a
    if f_is_nan(b):
        return b

    result_sign: int32 = f_sign(a) ^ f_sign(b)

    if f_is_zero(a) or f_is_zero(b):
        if f_is_inf(a) or f_is_inf(b):
            return F_NAN  # 0 * inf = NaN
        if result_sign != 0:
            return 0x80000000  # -0
        return F_ZERO

    if f_is_inf(a) or f_is_inf(b):
        if result_sign != 0:
            return F_NINF
        return F_INF

    # Extract components
    exp_a: int32 = f_exp(a) - EXP_BIAS
    exp_b: int32 = f_exp(b) - EXP_BIAS
    mant_a: uint32 = f_mant(a) | 0x00800000
    mant_b: uint32 = f_mant(b) | 0x00800000

    # Multiply mantissas (24x24 = 48 bits, but we only need top 24)
    # Use 32-bit multiply and shift
    # mant_a and mant_b are both in 1.23 format (bit 23 = implicit 1)
    # Product is in 2.46 format, we need to get 1.23

    # Split into high and low parts for wider multiply
    a_hi: uint32 = mant_a >> 12
    a_lo: uint32 = mant_a & 0xFFF
    b_hi: uint32 = mant_b >> 12
    b_lo: uint32 = mant_b & 0xFFF

    # Compute partial products
    hi_hi: uint32 = a_hi * b_hi
    hi_lo: uint32 = a_hi * b_lo
    lo_hi: uint32 = a_lo * b_hi

    # Combine (48-bit result, we want bits 47-24)
    result_mant: uint32 = hi_hi + (hi_lo >> 12) + (lo_hi >> 12)

    # Compute exponent
    result_exp: int32 = exp_a + exp_b + EXP_BIAS

    # Normalize
    if result_mant >= 0x01000000:
        result_mant = result_mant >> 1
        result_exp = result_exp + 1
    while result_mant < 0x00800000 and result_exp > 0:
        result_mant = result_mant << 1
        result_exp = result_exp - 1

    # Handle overflow/underflow
    if result_exp >= 255:
        if result_sign != 0:
            return F_NINF
        return F_INF
    if result_exp <= 0:
        return F_ZERO

    return f_make(result_sign, result_exp, result_mant)

# ============================================================================
# Float Division
# ============================================================================

def fdiv(a: uint32, b: uint32) -> uint32:
    """Divide two floats: a / b."""
    # Handle special cases
    if f_is_nan(a):
        return a
    if f_is_nan(b):
        return b

    result_sign: int32 = f_sign(a) ^ f_sign(b)

    if f_is_zero(b):
        if f_is_zero(a):
            return F_NAN  # 0/0 = NaN
        if result_sign != 0:
            return F_NINF
        return F_INF

    if f_is_zero(a):
        if result_sign != 0:
            return 0x80000000  # -0
        return F_ZERO

    if f_is_inf(a):
        if f_is_inf(b):
            return F_NAN  # inf/inf = NaN
        if result_sign != 0:
            return F_NINF
        return F_INF

    if f_is_inf(b):
        if result_sign != 0:
            return 0x80000000  # -0
        return F_ZERO

    # Extract components
    exp_a: int32 = f_exp(a) - EXP_BIAS
    exp_b: int32 = f_exp(b) - EXP_BIAS
    mant_a: uint32 = f_mant(a) | 0x00800000
    mant_b: uint32 = f_mant(b) | 0x00800000

    # Divide mantissas using integer division
    # Shift dividend left to get more precision
    dividend: uint32 = mant_a << 8  # Now in 1.31 format
    divisor: uint32 = mant_b

    result_mant: uint32 = dividend / divisor

    # Adjust exponent
    result_exp: int32 = exp_a - exp_b + EXP_BIAS

    # Normalize
    while result_mant >= 0x01000000:
        result_mant = result_mant >> 1
        result_exp = result_exp + 1
    while result_mant < 0x00800000 and result_exp > 0:
        result_mant = result_mant << 1
        result_exp = result_exp - 1

    # Handle overflow/underflow
    if result_exp >= 255:
        if result_sign != 0:
            return F_NINF
        return F_INF
    if result_exp <= 0:
        return F_ZERO

    return f_make(result_sign, result_exp, result_mant)

# ============================================================================
# Float Comparison
# ============================================================================

def fcmp(a: uint32, b: uint32) -> int32:
    """Compare two floats. Returns -1 if a<b, 0 if a==b, 1 if a>b."""
    if f_is_nan(a) or f_is_nan(b):
        return 0  # NaN comparisons are unordered

    # Handle zeros (positive and negative zero are equal)
    if f_is_zero(a) and f_is_zero(b):
        return 0

    sign_a: int32 = f_sign(a)
    sign_b: int32 = f_sign(b)

    # Different signs
    if sign_a != sign_b:
        if sign_a != 0:
            return -1  # a is negative, b is positive
        return 1  # a is positive, b is negative

    # Same sign - compare as integers (works for IEEE 754 floats)
    if a == b:
        return 0

    result: int32
    if a < b:
        result = -1
    else:
        result = 1

    # If both negative, reverse comparison
    if sign_a != 0:
        result = -result

    return result

def feq(a: uint32, b: uint32) -> bool:
    """Test if two floats are equal."""
    return fcmp(a, b) == 0

def flt(a: uint32, b: uint32) -> bool:
    """Test if a < b."""
    return fcmp(a, b) < 0

def fle(a: uint32, b: uint32) -> bool:
    """Test if a <= b."""
    return fcmp(a, b) <= 0

def fgt(a: uint32, b: uint32) -> bool:
    """Test if a > b."""
    return fcmp(a, b) > 0

def fge(a: uint32, b: uint32) -> bool:
    """Test if a >= b."""
    return fcmp(a, b) >= 0

# ============================================================================
# Float Math Functions
# ============================================================================

def ffloor(f: uint32) -> uint32:
    """Floor: largest integer <= f."""
    if f_is_nan(f) or f_is_inf(f) or f_is_zero(f):
        return f

    i: int32 = f_to_int(f)
    result: uint32 = f_from_int(i)

    # If f was negative and not an integer, subtract 1
    if f_is_negative(f) and fgt(f_from_int(i), f):
        return f_from_int(i - 1)

    return result

def fceil(f: uint32) -> uint32:
    """Ceiling: smallest integer >= f."""
    if f_is_nan(f) or f_is_inf(f) or f_is_zero(f):
        return f

    i: int32 = f_to_int(f)
    result: uint32 = f_from_int(i)

    # If f was positive and not an integer, add 1
    if not f_is_negative(f) and flt(f_from_int(i), f):
        return f_from_int(i + 1)

    return result

def fround(f: uint32) -> uint32:
    """Round to nearest integer."""
    if f_is_negative(f):
        return ffloor(fadd(f, F_HALF))
    return ffloor(fadd(f, F_HALF))

def fmin(a: uint32, b: uint32) -> uint32:
    """Return minimum of two floats."""
    if flt(a, b):
        return a
    return b

def fmax(a: uint32, b: uint32) -> uint32:
    """Return maximum of two floats."""
    if fgt(a, b):
        return a
    return b

# ============================================================================
# Float Square Root (Newton-Raphson)
# ============================================================================

def fsqrt(f: uint32) -> uint32:
    """Square root using Newton-Raphson iteration."""
    if f_is_zero(f) or f_is_nan(f):
        return f
    if f_is_negative(f):
        return F_NAN
    if f_is_inf(f):
        return f

    # Initial guess: use half the exponent
    exp: int32 = f_exp(f) - EXP_BIAS
    guess_exp: int32 = exp / 2 + EXP_BIAS
    guess: uint32 = f_make(0, guess_exp, 0)

    # Newton-Raphson: x = (x + n/x) / 2
    i: int32 = 0
    while i < 10:  # Typically converges in 4-5 iterations
        div_result: uint32 = fdiv(f, guess)
        sum_result: uint32 = fadd(guess, div_result)
        new_guess: uint32 = fmul(sum_result, F_HALF)

        # Check for convergence
        if new_guess == guess:
            break
        guess = new_guess
        i = i + 1

    return guess
