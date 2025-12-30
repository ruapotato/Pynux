from lib.io import print_str, print_int, uart_init

# ============================================================================
# With Statement Tests
# ============================================================================

# Global to track context manager state
ctx_state: int32 = 0

class FileContext:
    value: int32 = 0
    is_open: int32 = 0

    def __enter__(self) -> int32:
        global ctx_state
        self.is_open = 1
        self.value = 10
        ctx_state = 1  # Mark enter called
        return self.value

    def __exit__(self) -> int32:
        global ctx_state
        self.is_open = 0
        ctx_state = 2  # Mark exit called
        return 0

def test_with_statement() -> int32:
    global ctx_state
    ctx_state = 0
    result: int32 = 0

    with FileContext() as f:
        result = f + 32

    # Exit should have been called
    if ctx_state == 2:
        return result  # Should be 42
    return 0  # Failed

def test_with_no_as() -> int32:
    global ctx_state
    ctx_state = 0

    with FileContext():
        ctx_state = 10

    # Exit should have been called after body
    if ctx_state == 2:
        return 42
    return ctx_state  # Return what we got for debugging

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== With Statement Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1
    print_str("Test 1  (with as):       ")
    r: int32 = test_with_statement()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 2
    print_str("Test 2  (with no as):    ")
    r = test_with_no_as()
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
    print_str("/2 passed ===\n")

    if failed == 0:
        print_str("ALL TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return failed
