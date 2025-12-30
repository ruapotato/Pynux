from lib.io import print_str, print_int, print_hex, uart_init

# ============================================================================
# Pynux Feature Test Suite
# Each test computes a specific value that proves the feature works.
# Expected output is listed in comments.
# ============================================================================

# --- Test 1: Break Statement ---
# Break at i=5, so i should be 5
def test_break() -> int32:
    i: int32 = 0
    while i < 100:
        if i == 5:
            break
        i = i + 1
    return i  # Expected: 5

# --- Test 2: Continue Statement ---
# Sum 0-9 but skip 3 and 7: 0+1+2+4+5+6+8+9 = 35
def test_continue() -> int32:
    total: int32 = 0
    for i in range(10):
        if i == 3:
            continue
        if i == 7:
            continue
        total = total + i
    return total  # Expected: 35

# --- Test 3: For Loop with Step ---
# Sum even numbers 0,2,4,6,8 = 20
def test_for_step() -> int32:
    total: int32 = 0
    for i in range(0, 10, 2):
        total = total + i
    return total  # Expected: 20

# --- Test 4: Nested Loops with Break ---
# Outer loop runs 3 times, inner breaks at 2 each time
# Result: 3 * 2 = 6
def test_nested_break() -> int32:
    count: int32 = 0
    for i in range(3):
        for j in range(10):
            if j == 2:
                break
            count = count + 1
    return count  # Expected: 6

# --- Test 5: Float Literal (IEEE 754 bits) ---
# 3.14159 in IEEE 754 single precision = 0x40490FD0
def test_float() -> uint32:
    x: float32 = 3.14159
    return x  # Expected: 0x40490fd0 (1078530000 decimal)

# --- Test 6: Defer Statement ---
# Defer executes in reverse order, accumulating: 1, then *2, then +10
# Start with result=0, defer +10, defer *2, set result=1
# On return: result=1, then *2=2, then +10=12
def test_defer() -> int32:
    result: int32 = 0
    defer result = result + 10
    defer result = result * 2
    result = 1
    return result  # Expected: 12

# --- Test 7: Assert (passing) ---
# If assert works, we continue and return 42
def test_assert() -> int32:
    x: int32 = 42
    assert x == 42
    assert x > 0
    assert x != 0
    return x  # Expected: 42

# --- Test 8: While Loop with Complex Condition ---
# Collatz-like: start at 7, if odd multiply by 3 and add 1, if even divide by 2
# Count steps until we hit 1: 7->22->11->34->17->52->26->13->40->20->10->5->16->8->4->2->1
# That's 16 steps
def test_while_complex() -> int32:
    n: int32 = 7
    steps: int32 = 0
    while n != 1:
        if n % 2 == 0:
            n = n / 2
        else:
            n = n * 3 + 1
        steps = steps + 1
    return steps  # Expected: 16

# --- Test 9: Ternary/Conditional Expression ---
# max(17, 42) using ternary
def test_ternary() -> int32:
    a: int32 = 17
    b: int32 = 42
    result: int32 = a if a > b else b
    return result  # Expected: 42

# --- Test 10: Bitwise Operations ---
# (0xAA & 0x0F) | (0x50 ^ 0x05) << 4 = 0x0A | 0x550 = 0x55A = 1370
def test_bitwise() -> int32:
    x: int32 = 0xAA & 0x0F      # 0x0A = 10
    y: int32 = (0x50 ^ 0x05)    # 0x55 = 85
    z: int32 = y << 4           # 0x550 = 1360
    return x | z                # Expected: 1370

# --- Test 11: Global Variable ---
global_counter: int32 = 0

def increment_global():
    global global_counter
    global_counter = global_counter + 7

def test_global() -> int32:
    global global_counter
    global_counter = 0
    increment_global()
    increment_global()
    increment_global()
    return global_counter  # Expected: 21

# --- Test 12: Array Operations ---
arr: Array[10, int32]

def test_array() -> int32:
    # Fill array with squares
    for i in range(10):
        arr[i] = i * i
    # Sum them: 0+1+4+9+16+25+36+49+64+81 = 285
    total: int32 = 0
    for i in range(10):
        total = total + arr[i]
    return total  # Expected: 285

# --- Test 13: Char Array ---
buf: Array[16, char]

def test_char_array() -> int32:
    buf[0] = 'H'
    buf[1] = 'e'
    buf[2] = 'l'
    buf[3] = 'l'
    buf[4] = 'o'
    buf[5] = '\0'
    # Sum ASCII values: 72+101+108+108+111 = 500
    total: int32 = 0
    i: int32 = 0
    while buf[i] != '\0':
        total = total + buf[i]
        i = i + 1
    return total  # Expected: 500

# --- Test 14: Function Calls and Return Values ---
def fib(n: int32) -> int32:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

def test_recursion() -> int32:
    return fib(10)  # Expected: 55

# --- Test 15: Compound Assignment ---
def test_compound() -> int32:
    x: int32 = 10
    x += 5      # 15
    x *= 2      # 30
    x -= 3      # 27
    x &= 0x1F   # 27 & 31 = 27
    x |= 0x40   # 27 | 64 = 91
    return x    # Expected: 91


# ============================================================================
# Main - Run all tests and report results
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Pynux Feature Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1: Break
    print_str("Test 1  (break):      ")
    r: int32 = test_break()
    print_int(r)
    if r == 5:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 5)\n")
        failed = failed + 1

    # Test 2: Continue
    print_str("Test 2  (continue):   ")
    r = test_continue()
    print_int(r)
    if r == 35:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 35)\n")
        failed = failed + 1

    # Test 3: For Step
    print_str("Test 3  (for step):   ")
    r = test_for_step()
    print_int(r)
    if r == 20:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 20)\n")
        failed = failed + 1

    # Test 4: Nested Break
    print_str("Test 4  (nested brk): ")
    r = test_nested_break()
    print_int(r)
    if r == 6:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 6)\n")
        failed = failed + 1

    # Test 5: Float
    print_str("Test 5  (float):      ")
    rf: uint32 = test_float()
    print_hex(rf)
    if rf == 1078530000:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 0x40490fd0)\n")
        failed = failed + 1

    # Test 6: Defer
    print_str("Test 6  (defer):      ")
    r = test_defer()
    print_int(r)
    if r == 12:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 12)\n")
        failed = failed + 1

    # Test 7: Assert
    print_str("Test 7  (assert):     ")
    r = test_assert()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 8: While Complex
    print_str("Test 8  (while):      ")
    r = test_while_complex()
    print_int(r)
    if r == 16:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 16)\n")
        failed = failed + 1

    # Test 9: Ternary
    print_str("Test 9  (ternary):    ")
    r = test_ternary()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 10: Bitwise
    print_str("Test 10 (bitwise):    ")
    r = test_bitwise()
    print_int(r)
    if r == 1370:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 1370)\n")
        failed = failed + 1

    # Test 11: Global
    print_str("Test 11 (global):     ")
    r = test_global()
    print_int(r)
    if r == 21:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 21)\n")
        failed = failed + 1

    # Test 12: Array
    print_str("Test 12 (array):      ")
    r = test_array()
    print_int(r)
    if r == 285:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 285)\n")
        failed = failed + 1

    # Test 13: Char Array
    print_str("Test 13 (char arr):   ")
    r = test_char_array()
    print_int(r)
    if r == 500:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 500)\n")
        failed = failed + 1

    # Test 14: Recursion
    print_str("Test 14 (recursion):  ")
    r = test_recursion()
    print_int(r)
    if r == 55:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 55)\n")
        failed = failed + 1

    # Test 15: Compound Assignment
    print_str("Test 15 (compound):   ")
    r = test_compound()
    print_int(r)
    if r == 91:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 91)\n")
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
