from lib.io import uart_init

# ============================================================================
# Python Builtins Test
# ============================================================================

def test_print() -> int32:
    print("Hello", 42, "World")
    print(123)
    print("Test passed")
    return 1

def test_len_string() -> int32:
    s: str = "Hello"
    return len(s)  # Expected: 5

def test_len_literal() -> int32:
    return len("World!")  # Expected: 6

def test_abs() -> int32:
    a: int32 = abs(-42)
    b: int32 = abs(10)
    return a + b  # Expected: 52

def test_min_max() -> int32:
    a: int32 = min(10, 5, 8)
    b: int32 = max(10, 5, 8)
    return a + b  # Expected: 5 + 10 = 15

def test_ord_chr() -> int32:
    a: int32 = ord('A')  # 65
    # chr returns a character, add to get result
    return a  # Expected: 65

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print("=== Python Builtins Tests ===")
    print("")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1: print (visual check)
    print("Test 1 (print):    ", "testing print...")
    test_print()
    passed = passed + 1

    # Test 2: len string
    print("Test 2 (len str):  ", end="")
    r: int32 = test_len_string()
    print(r, end="")
    if r == 5:
        print(" PASS")
        passed = passed + 1
    else:
        print(" FAIL (expected 5)")
        failed = failed + 1

    # Test 3: len literal
    print("Test 3 (len lit):  ", end="")
    r = test_len_literal()
    print(r, end="")
    if r == 6:
        print(" PASS")
        passed = passed + 1
    else:
        print(" FAIL (expected 6)")
        failed = failed + 1

    # Test 4: abs
    print("Test 4 (abs):      ", end="")
    r = test_abs()
    print(r, end="")
    if r == 52:
        print(" PASS")
        passed = passed + 1
    else:
        print(" FAIL (expected 52)")
        failed = failed + 1

    # Test 5: min/max
    print("Test 5 (min/max):  ", end="")
    r = test_min_max()
    print(r, end="")
    if r == 15:
        print(" PASS")
        passed = passed + 1
    else:
        print(" FAIL (expected 15)")
        failed = failed + 1

    # Test 6: ord
    print("Test 6 (ord):      ", end="")
    r = test_ord_chr()
    print(r, end="")
    if r == 65:
        print(" PASS")
        passed = passed + 1
    else:
        print(" FAIL (expected 65)")
        failed = failed + 1

    # Summary
    print("")
    print("=== Results: ", passed, "/6 passed ===")

    if failed == 0:
        print("ALL TESTS PASSED!")
    else:
        print("SOME TESTS FAILED!")

    return failed
