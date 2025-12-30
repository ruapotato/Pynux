from lib.io import print_str, print_int, print_hex, uart_init

# ============================================================================
# Pynux Python Features Test Suite
# Tests all the new Python-like built-in functions and syntax
# ============================================================================

# --- Test 1: print() built-in ---
def test_print() -> int32:
    # print() should auto-detect types and add newline
    print("Hello from print!")
    print(42)
    print("Value:", 100)
    return 1  # Just verify it doesn't crash

# --- Test 2: len() built-in for strings ---
def test_len_string() -> int32:
    s: str = "Hello"
    return len(s)  # Expected: 5

# --- Test 3: len() built-in for arrays ---
arr10: Array[10, int32]

def test_len_array() -> int32:
    return len(arr10)  # Expected: 10

# --- Test 4: abs() built-in ---
def test_abs() -> int32:
    a: int32 = abs(-42)
    b: int32 = abs(17)
    return a + b  # Expected: 42 + 17 = 59

# --- Test 5: min() built-in ---
def test_min() -> int32:
    return min(100, 42, 73)  # Expected: 42

# --- Test 6: max() built-in ---
def test_max() -> int32:
    return max(10, 99, 50)  # Expected: 99

# --- Test 7: ord() built-in ---
def test_ord() -> int32:
    return ord('A')  # Expected: 65

# --- Test 8: chr() built-in ---
def test_chr() -> int32:
    c: char = chr(66)
    return c  # Expected: 66 (ASCII for 'B')

# --- Test 9: Negative indexing ---
arr5: Array[5, int32]

def test_negative_index() -> int32:
    for i in range(5):
        arr5[i] = (i + 1) * 10  # [10, 20, 30, 40, 50]
    return arr5[-1]  # Expected: 50 (last element)

# --- Test 10: Negative indexing -2 ---
def test_negative_index2() -> int32:
    return arr5[-2]  # Expected: 40 (second to last)

# --- Test 11: 'in' operator for strings ---
def test_in_string() -> int32:
    s: str = "Hello World"
    if 'o' in s:
        return 1  # Expected: 1 (found)
    return 0

# --- Test 12: 'not in' operator ---
def test_not_in() -> int32:
    s: str = "Hello"
    if 'z' not in s:
        return 1  # Expected: 1 (not found)
    return 0

# --- Test 13: f-string interpolation with print ---
def test_fstring() -> int32:
    x: int32 = 42
    print(f"The answer is {x}")
    return x  # Expected: 42

# --- Test 14: Multiple args to print ---
def test_print_multi() -> int32:
    a: int32 = 10
    b: int32 = 20
    print("a =", a, "b =", b)
    return a + b  # Expected: 30

# --- Test 15: Combined features ---
def test_combined() -> int32:
    # Use multiple Python features together
    data: Array[5, int32]
    for i in range(5):
        data[i] = i * i  # [0, 1, 4, 9, 16]

    # Get last element with negative indexing
    last: int32 = data[-1]  # 16

    # Get array length
    length: int32 = len(data)  # 5

    # Get max and min of some values
    m: int32 = max(last, length, 10)  # 16

    return m + abs(-4)  # Expected: 16 + 4 = 20

# ============================================================================
# Main - Run all tests
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Pynux Python Features Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1: print()
    print_str("Test 1  (print):       ")
    r: int32 = test_print()
    print_int(r)
    if r == 1:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Test 2: len(string)
    print_str("Test 2  (len str):     ")
    r = test_len_string()
    print_int(r)
    if r == 5:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 5)\n")
        failed = failed + 1

    # Test 3: len(array)
    print_str("Test 3  (len arr):     ")
    r = test_len_array()
    print_int(r)
    if r == 10:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 10)\n")
        failed = failed + 1

    # Test 4: abs()
    print_str("Test 4  (abs):         ")
    r = test_abs()
    print_int(r)
    if r == 59:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 59)\n")
        failed = failed + 1

    # Test 5: min()
    print_str("Test 5  (min):         ")
    r = test_min()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 6: max()
    print_str("Test 6  (max):         ")
    r = test_max()
    print_int(r)
    if r == 99:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 99)\n")
        failed = failed + 1

    # Test 7: ord()
    print_str("Test 7  (ord):         ")
    r = test_ord()
    print_int(r)
    if r == 65:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 65)\n")
        failed = failed + 1

    # Test 8: chr()
    print_str("Test 8  (chr):         ")
    r = test_chr()
    print_int(r)
    if r == 66:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 66)\n")
        failed = failed + 1

    # Test 9: arr[-1]
    print_str("Test 9  (arr[-1]):     ")
    r = test_negative_index()
    print_int(r)
    if r == 50:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 50)\n")
        failed = failed + 1

    # Test 10: arr[-2]
    print_str("Test 10 (arr[-2]):     ")
    r = test_negative_index2()
    print_int(r)
    if r == 40:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 40)\n")
        failed = failed + 1

    # Test 11: 'in' operator
    print_str("Test 11 (in):          ")
    r = test_in_string()
    print_int(r)
    if r == 1:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 1)\n")
        failed = failed + 1

    # Test 12: 'not in' operator
    print_str("Test 12 (not in):      ")
    r = test_not_in()
    print_int(r)
    if r == 1:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 1)\n")
        failed = failed + 1

    # Test 13: f-string
    print_str("Test 13 (f-string):    ")
    r = test_fstring()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 14: print with multiple args
    print_str("Test 14 (print multi): ")
    r = test_print_multi()
    print_int(r)
    if r == 30:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 30)\n")
        failed = failed + 1

    # Test 15: Combined features
    print_str("Test 15 (combined):    ")
    r = test_combined()
    print_int(r)
    if r == 20:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 20)\n")
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
