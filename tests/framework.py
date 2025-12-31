# Pynux Test Framework
#
# Target-side test framework for writing and running OS tests.
# Output format is designed to be parseable by qemu_runner.py.
#
# Usage:
#     from tests.framework import test_init, test_run, test_assert, test_summary
#
#     test_init()
#     test_run("my_test", my_test_func)
#     test_summary()
#
# Output format:
#     [TEST] test_name           - Test started
#     [PASS] test_name           - Test passed
#     [FAIL] test_name: message  - Test failed with message
#     [SKIP] test_name: reason   - Test skipped with reason
#     [SUMMARY] N passed, M failed, K skipped

from lib.io import print_str, print_int, print_newline

# ============================================================================
# Test State
# ============================================================================

# Test counters
_tests_passed: int32 = 0
_tests_failed: int32 = 0
_tests_skipped: int32 = 0

# Current test name (for nested assertions)
_current_test: Ptr[char] = Ptr[char](0)
_current_test_failed: bool = False

# ============================================================================
# Initialization
# ============================================================================

def test_init():
    """Initialize test framework. Call at start of test suite."""
    global _tests_passed, _tests_failed, _tests_skipped
    global _current_test, _current_test_failed

    _tests_passed = 0
    _tests_failed = 0
    _tests_skipped = 0
    _current_test = Ptr[char](0)
    _current_test_failed = False

# ============================================================================
# Test Execution
# ============================================================================

def test_run(name: Ptr[char], func: Fn[void]):
    """Run a single test function.

    Prints [TEST] marker, runs the function, and reports result.
    If no assertions fail during the function, test passes.

    Args:
        name: Test name (used in output)
        func: Test function to execute (takes no arguments, returns nothing)
    """
    global _current_test, _current_test_failed

    # Print test start marker
    print_str("[TEST] ")
    print_str(name)
    print_newline()

    # Set up test context
    _current_test = name
    _current_test_failed = False

    # Run the test function
    func()

    # If no failures, mark as passed
    if not _current_test_failed:
        _test_pass_internal(name)

    # Clear context
    _current_test = Ptr[char](0)

def _test_pass_internal(name: Ptr[char]):
    """Internal: Mark test as passed."""
    global _tests_passed
    print_str("[PASS] ")
    print_str(name)
    print_newline()
    _tests_passed = _tests_passed + 1

def _test_fail_internal(name: Ptr[char], msg: Ptr[char]):
    """Internal: Mark test as failed."""
    global _tests_failed, _current_test_failed
    _current_test_failed = True
    print_str("[FAIL] ")
    print_str(name)
    if msg != Ptr[char](0) and msg[0] != '\0':
        print_str(": ")
        print_str(msg)
    print_newline()
    _tests_failed = _tests_failed + 1

# ============================================================================
# Assertions
# ============================================================================

def test_assert(condition: bool, message: Ptr[char]):
    """Assert that condition is true.

    Args:
        condition: Condition to check
        message: Message to display (used as test name if standalone)
    """
    global _current_test

    if condition:
        # Only print pass if not inside test_run
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        if _current_test != Ptr[char](0):
            _test_fail_internal(_current_test, message)
        else:
            _test_fail_internal(message, Ptr[char](0))

def test_assert_eq(a: int32, b: int32, message: Ptr[char]):
    """Assert that two integers are equal.

    Args:
        a: First value
        b: Second value (expected)
        message: Test description
    """
    global _current_test, _current_test_failed, _tests_failed

    if a == b:
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        _current_test_failed = True
        print_str("[FAIL] ")
        if _current_test != Ptr[char](0):
            print_str(_current_test)
            print_str(": ")
        print_str(message)
        print_str(" (expected ")
        print_int(b)
        print_str(", got ")
        print_int(a)
        print_str(")")
        print_newline()
        _tests_failed = _tests_failed + 1

def test_assert_ne(a: int32, b: int32, message: Ptr[char]):
    """Assert that two integers are not equal.

    Args:
        a: First value
        b: Second value (should not equal)
        message: Test description
    """
    global _current_test, _current_test_failed, _tests_failed

    if a != b:
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        _current_test_failed = True
        print_str("[FAIL] ")
        if _current_test != Ptr[char](0):
            print_str(_current_test)
            print_str(": ")
        print_str(message)
        print_str(" (should not be ")
        print_int(b)
        print_str(")")
        print_newline()
        _tests_failed = _tests_failed + 1

def test_assert_lt(a: int32, b: int32, message: Ptr[char]):
    """Assert that a < b.

    Args:
        a: First value
        b: Second value (threshold)
        message: Test description
    """
    global _current_test, _current_test_failed, _tests_failed

    if a < b:
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        _current_test_failed = True
        print_str("[FAIL] ")
        if _current_test != Ptr[char](0):
            print_str(_current_test)
            print_str(": ")
        print_str(message)
        print_str(" (")
        print_int(a)
        print_str(" not < ")
        print_int(b)
        print_str(")")
        print_newline()
        _tests_failed = _tests_failed + 1

def test_assert_gt(a: int32, b: int32, message: Ptr[char]):
    """Assert that a > b.

    Args:
        a: First value
        b: Second value (threshold)
        message: Test description
    """
    global _current_test, _current_test_failed, _tests_failed

    if a > b:
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        _current_test_failed = True
        print_str("[FAIL] ")
        if _current_test != Ptr[char](0):
            print_str(_current_test)
            print_str(": ")
        print_str(message)
        print_str(" (")
        print_int(a)
        print_str(" not > ")
        print_int(b)
        print_str(")")
        print_newline()
        _tests_failed = _tests_failed + 1

def test_assert_le(a: int32, b: int32, message: Ptr[char]):
    """Assert that a <= b.

    Args:
        a: First value
        b: Second value (threshold)
        message: Test description
    """
    global _current_test, _current_test_failed, _tests_failed

    if a <= b:
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        _current_test_failed = True
        print_str("[FAIL] ")
        if _current_test != Ptr[char](0):
            print_str(_current_test)
            print_str(": ")
        print_str(message)
        print_str(" (")
        print_int(a)
        print_str(" not <= ")
        print_int(b)
        print_str(")")
        print_newline()
        _tests_failed = _tests_failed + 1

def test_assert_ge(a: int32, b: int32, message: Ptr[char]):
    """Assert that a >= b.

    Args:
        a: First value
        b: Second value (threshold)
        message: Test description
    """
    global _current_test, _current_test_failed, _tests_failed

    if a >= b:
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        _current_test_failed = True
        print_str("[FAIL] ")
        if _current_test != Ptr[char](0):
            print_str(_current_test)
            print_str(": ")
        print_str(message)
        print_str(" (")
        print_int(a)
        print_str(" not >= ")
        print_int(b)
        print_str(")")
        print_newline()
        _tests_failed = _tests_failed + 1

def test_assert_not_null(ptr: Ptr[void], message: Ptr[char]):
    """Assert that pointer is not null.

    Args:
        ptr: Pointer to check
        message: Test description
    """
    if ptr != Ptr[void](0):
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        if _current_test != Ptr[char](0):
            _test_fail_internal(_current_test, message)
        else:
            global _current_test_failed, _tests_failed
            _current_test_failed = True
            print_str("[FAIL] ")
            print_str(message)
            print_str(": pointer is null")
            print_newline()
            _tests_failed = _tests_failed + 1

def test_assert_null(ptr: Ptr[void], message: Ptr[char]):
    """Assert that pointer is null.

    Args:
        ptr: Pointer to check
        message: Test description
    """
    if ptr == Ptr[void](0):
        if _current_test == Ptr[char](0):
            _test_pass_internal(message)
    else:
        if _current_test != Ptr[char](0):
            _test_fail_internal(_current_test, message)
        else:
            global _current_test_failed, _tests_failed
            _current_test_failed = True
            print_str("[FAIL] ")
            print_str(message)
            print_str(": pointer should be null")
            print_newline()
            _tests_failed = _tests_failed + 1

# ============================================================================
# Explicit Pass/Fail/Skip
# ============================================================================

def test_fail(message: Ptr[char]):
    """Explicitly fail the current test.

    Args:
        message: Failure message
    """
    global _current_test
    if _current_test != Ptr[char](0):
        _test_fail_internal(_current_test, message)
    else:
        _test_fail_internal(message, Ptr[char](0))

def test_pass(name: Ptr[char]):
    """Explicitly pass a test (for standalone tests not using test_run).

    Args:
        name: Test name
    """
    _test_pass_internal(name)

def test_skip(reason: Ptr[char]):
    """Skip the current test with a reason.

    Args:
        reason: Reason for skipping
    """
    global _current_test, _tests_skipped, _current_test_failed

    _current_test_failed = True  # Prevent auto-pass
    print_str("[SKIP] ")
    if _current_test != Ptr[char](0):
        print_str(_current_test)
    else:
        print_str("test")
    if reason != Ptr[char](0) and reason[0] != '\0':
        print_str(": ")
        print_str(reason)
    print_newline()
    _tests_skipped = _tests_skipped + 1

# ============================================================================
# Summary
# ============================================================================

def test_summary() -> int32:
    """Print test summary and return exit code.

    Prints a summary in the format:
        [SUMMARY] N passed, M failed, K skipped

    Returns:
        0 if all tests passed, 1 otherwise
    """
    print_newline()
    print_str("[SUMMARY] ")
    print_int(_tests_passed)
    print_str(" passed, ")
    print_int(_tests_failed)
    print_str(" failed, ")
    print_int(_tests_skipped)
    print_str(" skipped")
    print_newline()
    print_newline()

    if _tests_failed == 0:
        print_str("All tests passed!")
        print_newline()
        return 0
    else:
        print_str("Some tests failed.")
        print_newline()
        return 1

# ============================================================================
# Helper Functions
# ============================================================================

def test_section(name: Ptr[char]):
    """Print a test section header (for organizing output).

    Args:
        name: Section name
    """
    print_newline()
    print_str("--- ")
    print_str(name)
    print_str(" ---")
    print_newline()

def get_tests_passed() -> int32:
    """Get number of passed tests."""
    return _tests_passed

def get_tests_failed() -> int32:
    """Get number of failed tests."""
    return _tests_failed

def get_tests_skipped() -> int32:
    """Get number of skipped tests."""
    return _tests_skipped

def get_tests_total() -> int32:
    """Get total number of tests run."""
    return _tests_passed + _tests_failed + _tests_skipped

# ============================================================================
# Backwards Compatibility with test_framework.py
# ============================================================================
# These functions provide compatibility with existing tests using the old
# test_framework.py API.

def assert_true(condition: bool, name: Ptr[char]):
    """Assert that condition is true (backward compatible)."""
    test_assert(condition, name)

def assert_false(condition: bool, name: Ptr[char]):
    """Assert that condition is false (backward compatible)."""
    test_assert(not condition, name)

def assert_eq(actual: int32, expected: int32, name: Ptr[char]):
    """Assert two integers are equal (backward compatible)."""
    test_assert_eq(actual, expected, name)

def assert_neq(actual: int32, expected: int32, name: Ptr[char]):
    """Assert two integers are not equal (backward compatible)."""
    test_assert_ne(actual, expected, name)

def assert_gt(actual: int32, threshold: int32, name: Ptr[char]):
    """Assert actual > threshold (backward compatible)."""
    test_assert_gt(actual, threshold, name)

def assert_gte(actual: int32, threshold: int32, name: Ptr[char]):
    """Assert actual >= threshold (backward compatible)."""
    test_assert_ge(actual, threshold, name)

def assert_lt(actual: int32, threshold: int32, name: Ptr[char]):
    """Assert actual < threshold (backward compatible)."""
    test_assert_lt(actual, threshold, name)

def assert_lte(actual: int32, threshold: int32, name: Ptr[char]):
    """Assert actual <= threshold (backward compatible)."""
    test_assert_le(actual, threshold, name)

def assert_not_null(ptr: Ptr[void], name: Ptr[char]):
    """Assert pointer is not null (backward compatible)."""
    test_assert_not_null(ptr, name)

def assert_null(ptr: Ptr[void], name: Ptr[char]):
    """Assert pointer is null (backward compatible)."""
    test_assert_null(ptr, name)

def print_section(name: Ptr[char]):
    """Print test section header (backward compatible)."""
    test_section(name)

def print_results() -> int32:
    """Print test results (backward compatible alias for test_summary)."""
    return test_summary()

def reset_counters():
    """Reset test counters (backward compatible alias for test_init)."""
    test_init()
