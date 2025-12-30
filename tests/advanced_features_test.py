from lib.io import print_str, print_int, uart_init

# ============================================================================
# Pynux Advanced Features Test Suite
# Tests list comprehensions, tuple unpacking, try/except, string methods
# ============================================================================

# --- Test 1: List Comprehension Basic ---
def test_list_comp_basic() -> int32:
    # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81] - sum = 285
    squares = [x*x for x in range(10)]
    total: int32 = 0
    for i in range(10):
        total = total + squares[i]
    return total  # Expected: 285

# --- Test 2: List Comprehension with Condition ---
def test_list_comp_filter() -> int32:
    # Even squares only: [0, 4, 16, 36, 64] - sum = 120
    even_squares = [x*x for x in range(10) if x % 2 == 0]
    total: int32 = 0
    for i in range(5):
        total = total + even_squares[i]
    return total  # Expected: 120

# --- Test 3: Tuple Unpacking Swap ---
def test_tuple_swap() -> int32:
    a: int32 = 10
    b: int32 = 20
    a, b = b, a
    # After swap: a=20, b=10
    return a - b  # Expected: 10

# --- Test 4: Tuple Unpacking Triple ---
def test_tuple_triple() -> int32:
    x: int32 = 1
    y: int32 = 2
    z: int32 = 3
    x, y, z = z, x, y
    # After: x=3, y=1, z=2
    return x * 100 + y * 10 + z  # Expected: 312

# --- Test 5: String Upper ---
def test_string_upper() -> int32:
    s: str = "hello"
    upper: str = s.upper()
    # "HELLO" - check first char is 'H' (72)
    return upper[0]  # Expected: 72

# --- Test 6: String Lower ---
def test_string_lower() -> int32:
    s: str = "WORLD"
    lower: str = s.lower()
    # "world" - check first char is 'w' (119)
    return lower[0]  # Expected: 119

# --- Test 7: String StartsWith ---
def test_startswith() -> int32:
    s: str = "Hello World"
    if s.startswith("Hello"):
        return 1
    return 0  # Expected: 1

# --- Test 8: String EndsWith ---
def test_endswith() -> int32:
    s: str = "Hello World"
    if s.endswith("World"):
        return 1
    return 0  # Expected: 1

# --- Test 9: String Find ---
def test_string_find() -> int32:
    s: str = "Hello World"
    idx: int32 = s.find("World")
    return idx  # Expected: 6

# --- Test 10: String IsDigit ---
def test_isdigit() -> int32:
    s1: str = "12345"
    s2: str = "123a5"
    r1: int32 = 0
    r2: int32 = 0
    if s1.isdigit():
        r1 = 1
    if s2.isdigit():
        r2 = 1
    return r1 * 10 + r2  # Expected: 10 (first is digits, second is not)

# --- Test 11: String IsAlpha ---
def test_isalpha() -> int32:
    s1: str = "Hello"
    s2: str = "Hello1"
    r1: int32 = 0
    r2: int32 = 0
    if s1.isalpha():
        r1 = 1
    if s2.isalpha():
        r2 = 1
    return r1 * 10 + r2  # Expected: 10

# --- Test 12: Try/Except Basic ---
def test_try_basic() -> int32:
    result: int32 = 0
    try:
        result = 42
    except:
        result = 0
    return result  # Expected: 42

# --- Test 13: Try/Finally ---
def test_try_finally() -> int32:
    result: int32 = 0
    try:
        result = 10
    finally:
        result = result + 5
    return result  # Expected: 15

# --- Test 14: Combined Features ---
def test_combined() -> int32:
    # Create list of squares
    nums = [x*x for x in range(5)]  # [0, 1, 4, 9, 16]

    # Swap first and last using tuple unpacking
    a: int32 = nums[0]   # 0
    b: int32 = nums[-1]  # 16
    a, b = b, a

    # Test string method
    s: str = "test"
    upper: str = s.upper()
    first_char: int32 = upper[0]  # 'T' = 84

    return a + b + first_char  # Expected: 16 + 0 + 84 = 100

# --- Test 15: List Comprehension Length ---
def test_list_comp_len() -> int32:
    # Create list with 7 elements (odd numbers 1-13)
    odds = [x for x in range(1, 14, 2)]
    # 1, 3, 5, 7, 9, 11, 13 - sum should be 49
    total: int32 = 0
    for i in range(7):
        total = total + odds[i]
    return total  # Expected: 49

# ============================================================================
# Main - Run all tests
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Pynux Advanced Features Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1
    print_str("Test 1  (list comp):     ")
    r: int32 = test_list_comp_basic()
    print_int(r)
    if r == 285:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 285)\n")
        failed = failed + 1

    # Test 2
    print_str("Test 2  (list filter):   ")
    r = test_list_comp_filter()
    print_int(r)
    if r == 120:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 120)\n")
        failed = failed + 1

    # Test 3
    print_str("Test 3  (tuple swap):    ")
    r = test_tuple_swap()
    print_int(r)
    if r == 10:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 10)\n")
        failed = failed + 1

    # Test 4
    print_str("Test 4  (tuple triple):  ")
    r = test_tuple_triple()
    print_int(r)
    if r == 312:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 312)\n")
        failed = failed + 1

    # Test 5
    print_str("Test 5  (str.upper):     ")
    r = test_string_upper()
    print_int(r)
    if r == 72:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 72)\n")
        failed = failed + 1

    # Test 6
    print_str("Test 6  (str.lower):     ")
    r = test_string_lower()
    print_int(r)
    if r == 119:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 119)\n")
        failed = failed + 1

    # Test 7
    print_str("Test 7  (startswith):    ")
    r = test_startswith()
    print_int(r)
    if r == 1:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 1)\n")
        failed = failed + 1

    # Test 8
    print_str("Test 8  (endswith):      ")
    r = test_endswith()
    print_int(r)
    if r == 1:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 1)\n")
        failed = failed + 1

    # Test 9
    print_str("Test 9  (str.find):      ")
    r = test_string_find()
    print_int(r)
    if r == 6:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 6)\n")
        failed = failed + 1

    # Test 10
    print_str("Test 10 (isdigit):       ")
    r = test_isdigit()
    print_int(r)
    if r == 10:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 10)\n")
        failed = failed + 1

    # Test 11
    print_str("Test 11 (isalpha):       ")
    r = test_isalpha()
    print_int(r)
    if r == 10:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 10)\n")
        failed = failed + 1

    # Test 12
    print_str("Test 12 (try/except):    ")
    r = test_try_basic()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 13
    print_str("Test 13 (try/finally):   ")
    r = test_try_finally()
    print_int(r)
    if r == 15:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 15)\n")
        failed = failed + 1

    # Test 14
    print_str("Test 14 (combined):      ")
    r = test_combined()
    print_int(r)
    if r == 100:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 100)\n")
        failed = failed + 1

    # Test 15
    print_str("Test 15 (list step):     ")
    r = test_list_comp_len()
    print_int(r)
    if r == 49:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 49)\n")
        failed = failed + 1

    # Summary
    print_str("\n=== Results: ")
    print_int(passed)
    print_str("/15 passed ===\n")

    if failed == 0:
        print_str("ALL TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return failed
