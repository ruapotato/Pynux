from lib.io import print_str, print_int, uart_init

# ============================================================================
# Lambda and List Comprehension Tests
# ============================================================================

# --- Test 1: Lambda basic ---
def test_lambda_basic() -> int32:
    f = lambda x: x * 2
    return f(21)  # Expected: 42

# --- Test 2: Lambda with multiple args ---
def test_lambda_multi() -> int32:
    add = lambda a, b: a + b
    return add(15, 27)  # Expected: 42

# --- Test 3: List comprehension basic ---
def test_list_comp_basic() -> int32:
    squares = [x*x for x in range(5)]
    # [0, 1, 4, 9, 16] - sum = 30
    total: int32 = 0
    for i in range(5):
        total = total + squares[i]
    return total  # Expected: 30

# --- Test 4: List comprehension with filter ---
def test_list_comp_filter() -> int32:
    evens = [x for x in range(10) if x % 2 == 0]
    # [0, 2, 4, 6, 8] - sum = 20
    total: int32 = 0
    for i in range(5):
        total = total + evens[i]
    return total  # Expected: 20

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Lambda & List Comp Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1
    print_str("Test 1  (lambda basic):  ")
    r: int32 = test_lambda_basic()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 2
    print_str("Test 2  (lambda multi):  ")
    r = test_lambda_multi()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 3
    print_str("Test 3  (list comp):     ")
    r = test_list_comp_basic()
    print_int(r)
    if r == 30:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 30)\n")
        failed = failed + 1

    # Test 4
    print_str("Test 4  (list filter):   ")
    r = test_list_comp_filter()
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
    print_str("/4 passed ===\n")

    if failed == 0:
        print_str("ALL TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return failed
