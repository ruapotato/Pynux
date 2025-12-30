from lib.io import print_str, print_int, uart_init

# ============================================================================
# Dictionary and Slicing Tests
# ============================================================================

# --- Test 1: Dictionary with int keys ---
def test_dict_int() -> int32:
    d: Dict[int32, int32] = {1: 10, 2: 20, 3: 30}
    return d[2]  # Expected: 20

# --- Test 2: Dictionary sum ---
def test_dict_sum() -> int32:
    d: Dict[int32, int32] = {1: 10, 2: 20, 3: 12}
    return d[1] + d[2] + d[3]  # Expected: 42

# --- Test 3: Empty dict access ---
def test_empty_dict() -> int32:
    d: Dict[int32, int32] = {}
    return d[999] + 42  # Non-existent key returns 0, so 0 + 42 = 42

# --- Test 4: String slicing basic ---
def test_slice_basic() -> int32:
    s: str = "Hello World"
    sub: str = s[0:5]
    return len(sub)  # "Hello" = 5 chars

# --- Test 5: String slicing to end ---
def test_slice_to_end() -> int32:
    s: str = "Hello"
    sub: str = s[2:]
    return len(sub)  # "llo" = 3 chars

# --- Test 6: String slicing from start ---
def test_slice_from_start() -> int32:
    s: str = "Hello"
    sub: str = s[:3]
    return len(sub)  # "Hel" = 3 chars

# --- Test 7: String slice with step ---
def test_slice_step() -> int32:
    s: str = "abcdefgh"
    sub: str = s[0:8:2]
    return len(sub)  # "aceg" = 4 chars

# --- Test 8: Negative slice start ---
def test_slice_negative() -> int32:
    s: str = "Hello"
    sub: str = s[-3:]
    return len(sub)  # "llo" = 3 chars

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Dict & Slice Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1
    print_str("Test 1  (dict int):    ")
    r: int32 = test_dict_int()
    print_int(r)
    if r == 20:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 20)\n")
        failed = failed + 1

    # Test 2
    print_str("Test 2  (dict sum):    ")
    r = test_dict_sum()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 3
    print_str("Test 3  (empty dict):  ")
    r = test_empty_dict()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 4
    print_str("Test 4  (slice basic): ")
    r = test_slice_basic()
    print_int(r)
    if r == 5:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 5)\n")
        failed = failed + 1

    # Test 5
    print_str("Test 5  (slice end):   ")
    r = test_slice_to_end()
    print_int(r)
    if r == 3:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 3)\n")
        failed = failed + 1

    # Test 6
    print_str("Test 6  (slice start): ")
    r = test_slice_from_start()
    print_int(r)
    if r == 3:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 3)\n")
        failed = failed + 1

    # Test 7
    print_str("Test 7  (slice step):  ")
    r = test_slice_step()
    print_int(r)
    if r == 4:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 4)\n")
        failed = failed + 1

    # Test 8
    print_str("Test 8  (slice neg):   ")
    r = test_slice_negative()
    print_int(r)
    if r == 3:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 3)\n")
        failed = failed + 1

    # Summary
    print_str("\n=== Results: ")
    print_int(passed)
    print_str("/8 passed ===\n")

    if failed == 0:
        print_str("ALL TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return failed
