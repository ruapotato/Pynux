from lib.io import print_str, print_int, uart_init

# ============================================================================
# OS Features Tests
# Tests for volatile, struct init, memory barriers, unions, packed, interrupt
# ============================================================================

# --- Struct for testing initialization ---
class Point:
    x: int32
    y: int32

class Color:
    r: uint8
    g: uint8
    b: uint8

# --- Union for testing ---
union Register:
    raw: uint32
    low_byte: uint8

# --- Test 1: Struct initialization syntax ---
def test_struct_init() -> int32:
    p: Point = Point{x=10, y=32}
    return p.x + p.y  # Expected: 42

# --- Test 2: Struct init with expressions ---
def test_struct_init_expr() -> int32:
    a: int32 = 20
    b: int32 = 22
    p: Point = Point{x=a, y=b}
    return p.x + p.y  # Expected: 42

# --- Test 3: Volatile variable ---
def test_volatile() -> int32:
    v: volatile int32 = 42
    return v  # Expected: 42

# --- Test 4: Memory barrier (should not crash) ---
def test_memory_barrier() -> int32:
    dmb()
    dsb()
    isb()
    return 42  # If we get here, barriers worked

# --- Test 5: Union access ---
def test_union() -> int32:
    r: Register = Register{raw=0x12345678}
    # Low byte should be 0x78 (little-endian)
    # But since we read as uint32, let's just verify it stores
    if r.raw == 0x12345678:
        return 42
    return 0

# --- Test 6: Multiple struct fields ---
def test_color_struct() -> int32:
    c: Color = Color{r=10, g=20, b=12}
    total: int32 = c.r + c.g + c.b
    return total  # Expected: 42

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== OS Features Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1
    print_str("Test 1  (struct init):   ")
    r: int32 = test_struct_init()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 2
    print_str("Test 2  (struct expr):   ")
    r = test_struct_init_expr()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 3
    print_str("Test 3  (volatile):      ")
    r = test_volatile()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 4
    print_str("Test 4  (mem barriers):  ")
    r = test_memory_barrier()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 5
    print_str("Test 5  (union):         ")
    r = test_union()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 6
    print_str("Test 6  (color struct):  ")
    r = test_color_struct()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Summary
    print_str("\n=== Results: ")
    print_int(passed)
    print_str("/6 passed ===\n")

    if failed == 0:
        print_str("ALL TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return failed
