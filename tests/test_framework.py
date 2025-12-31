# Pynux Test Framework
#
# Common utilities for writing OS tests.

from lib.io import print_str, print_int, print_newline

# Test counters
_tests_passed: int32 = 0
_tests_failed: int32 = 0
_tests_skipped: int32 = 0

def test_pass(name: Ptr[char]):
    """Mark a test as passed."""
    global _tests_passed
    print_str("[PASS] ")
    print_str(name)
    print_newline()
    _tests_passed = _tests_passed + 1

def test_fail(name: Ptr[char]):
    """Mark a test as failed."""
    global _tests_failed
    print_str("[FAIL] ")
    print_str(name)
    print_newline()
    _tests_failed = _tests_failed + 1

def test_fail_with_msg(name: Ptr[char], msg: Ptr[char]):
    """Mark a test as failed with additional message."""
    global _tests_failed
    print_str("[FAIL] ")
    print_str(name)
    print_str(": ")
    print_str(msg)
    print_newline()
    _tests_failed = _tests_failed + 1

def test_skip(name: Ptr[char]):
    """Mark a test as skipped."""
    global _tests_skipped
    print_str("[SKIP] ")
    print_str(name)
    print_newline()
    _tests_skipped = _tests_skipped + 1

def assert_true(condition: bool, name: Ptr[char]):
    """Assert that condition is true."""
    if condition:
        test_pass(name)
    else:
        test_fail(name)

def assert_false(condition: bool, name: Ptr[char]):
    """Assert that condition is false."""
    if not condition:
        test_pass(name)
    else:
        test_fail(name)

def assert_eq(actual: int32, expected: int32, name: Ptr[char]):
    """Assert two integers are equal."""
    if actual == expected:
        test_pass(name)
    else:
        print_str("[FAIL] ")
        print_str(name)
        print_str(" (expected ")
        print_int(expected)
        print_str(", got ")
        print_int(actual)
        print_str(")")
        print_newline()
        global _tests_failed
        _tests_failed = _tests_failed + 1

def assert_neq(actual: int32, expected: int32, name: Ptr[char]):
    """Assert two integers are not equal."""
    if actual != expected:
        test_pass(name)
    else:
        print_str("[FAIL] ")
        print_str(name)
        print_str(" (should not be ")
        print_int(expected)
        print_str(")")
        print_newline()
        global _tests_failed
        _tests_failed = _tests_failed + 1

def assert_gt(actual: int32, threshold: int32, name: Ptr[char]):
    """Assert actual > threshold."""
    if actual > threshold:
        test_pass(name)
    else:
        print_str("[FAIL] ")
        print_str(name)
        print_str(" (")
        print_int(actual)
        print_str(" not > ")
        print_int(threshold)
        print_str(")")
        print_newline()
        global _tests_failed
        _tests_failed = _tests_failed + 1

def assert_gte(actual: int32, threshold: int32, name: Ptr[char]):
    """Assert actual >= threshold."""
    if actual >= threshold:
        test_pass(name)
    else:
        print_str("[FAIL] ")
        print_str(name)
        print_str(" (")
        print_int(actual)
        print_str(" not >= ")
        print_int(threshold)
        print_str(")")
        print_newline()
        global _tests_failed
        _tests_failed = _tests_failed + 1

def assert_lt(actual: int32, threshold: int32, name: Ptr[char]):
    """Assert actual < threshold."""
    if actual < threshold:
        test_pass(name)
    else:
        print_str("[FAIL] ")
        print_str(name)
        print_str(" (")
        print_int(actual)
        print_str(" not < ")
        print_int(threshold)
        print_str(")")
        print_newline()
        global _tests_failed
        _tests_failed = _tests_failed + 1

def assert_lte(actual: int32, threshold: int32, name: Ptr[char]):
    """Assert actual <= threshold."""
    if actual <= threshold:
        test_pass(name)
    else:
        print_str("[FAIL] ")
        print_str(name)
        print_str(" (")
        print_int(actual)
        print_str(" not <= ")
        print_int(threshold)
        print_str(")")
        print_newline()
        global _tests_failed
        _tests_failed = _tests_failed + 1

def assert_not_null(ptr: Ptr[void], name: Ptr[char]):
    """Assert pointer is not null."""
    if ptr != Ptr[void](0):
        test_pass(name)
    else:
        test_fail_with_msg(name, "pointer is null")

def assert_null(ptr: Ptr[void], name: Ptr[char]):
    """Assert pointer is null."""
    if ptr == Ptr[void](0):
        test_pass(name)
    else:
        test_fail_with_msg(name, "pointer should be null")

def print_section(name: Ptr[char]):
    """Print a test section header."""
    print_newline()
    print_str("--- ")
    print_str(name)
    print_str(" ---")
    print_newline()

def print_results() -> int32:
    """Print test results and return exit code."""
    print_newline()
    print_str("=== Test Results ===")
    print_newline()
    print_str("Passed:  ")
    print_int(_tests_passed)
    print_newline()
    print_str("Failed:  ")
    print_int(_tests_failed)
    print_newline()
    print_str("Skipped: ")
    print_int(_tests_skipped)
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

def reset_counters():
    """Reset test counters."""
    global _tests_passed, _tests_failed, _tests_skipped
    _tests_passed = 0
    _tests_failed = 0
    _tests_skipped = 0

def get_passed() -> int32:
    """Get number of passed tests."""
    return _tests_passed

def get_failed() -> int32:
    """Get number of failed tests."""
    return _tests_failed
