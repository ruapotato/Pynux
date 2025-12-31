# Pynux Test Suite Runner
#
# Runs all OS tests and reports overall results.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import reset_counters, get_passed, get_failed

# Import test modules
from tests.test_process import main as run_process_tests
from tests.test_ipc import main as run_ipc_tests
from tests.test_ramfs import main as run_ramfs_tests
from tests.test_devfs import main as run_devfs_tests
from tests.test_memory import main as run_memory_tests
from tests.test_timer import main as run_timer_tests
from tests.test_integration import main as run_integration_tests

# Track suite-level stats
_suites_passed: int32 = 0
_suites_failed: int32 = 0
_total_tests_passed: int32 = 0
_total_tests_failed: int32 = 0

def run_suite(name: Ptr[char], result: int32):
    """Track results of a test suite."""
    global _suites_passed, _suites_failed
    global _total_tests_passed, _total_tests_failed

    passed: int32 = get_passed()
    failed: int32 = get_failed()

    _total_tests_passed = _total_tests_passed + passed
    _total_tests_failed = _total_tests_failed + failed

    if result == 0:
        _suites_passed = _suites_passed + 1
    else:
        _suites_failed = _suites_failed + 1

def main() -> int32:
    global _suites_passed, _suites_failed
    global _total_tests_passed, _total_tests_failed

    print_str("\n")
    print_str("############################################################\n")
    print_str("#                PYNUX TEST SUITE                          #\n")
    print_str("############################################################\n")

    # Run all test suites
    print_str("\n=== Process Management Tests ===\n")
    reset_counters()
    result: int32 = run_process_tests()
    run_suite("Process", result)

    print_str("\n=== IPC Tests ===\n")
    reset_counters()
    result = run_ipc_tests()
    run_suite("IPC", result)

    print_str("\n=== RAM Filesystem Tests ===\n")
    reset_counters()
    result = run_ramfs_tests()
    run_suite("RAMFS", result)

    print_str("\n=== Device Filesystem Tests ===\n")
    reset_counters()
    result = run_devfs_tests()
    run_suite("DevFS", result)

    print_str("\n=== Memory Management Tests ===\n")
    reset_counters()
    result = run_memory_tests()
    run_suite("Memory", result)

    print_str("\n=== Timer Tests ===\n")
    reset_counters()
    result = run_timer_tests()
    run_suite("Timer", result)

    print_str("\n=== Integration Tests ===\n")
    reset_counters()
    result = run_integration_tests()
    run_suite("Integration", result)

    # Print final summary
    print_str("\n")
    print_str("############################################################\n")
    print_str("#                   FINAL RESULTS                          #\n")
    print_str("############################################################\n\n")

    print_str("Test Suites:\n")
    print_str("  Passed:  ")
    print_int(_suites_passed)
    print_newline()
    print_str("  Failed:  ")
    print_int(_suites_failed)
    print_newline()
    print_str("  Total:   ")
    print_int(_suites_passed + _suites_failed)
    print_newline()

    print_str("\nIndividual Tests:\n")
    print_str("  Passed:  ")
    print_int(_total_tests_passed)
    print_newline()
    print_str("  Failed:  ")
    print_int(_total_tests_failed)
    print_newline()
    print_str("  Total:   ")
    print_int(_total_tests_passed + _total_tests_failed)
    print_newline()

    print_str("\n")

    if _total_tests_failed == 0 and _suites_failed == 0:
        print_str("************************************************************\n")
        print_str("*         ALL TESTS PASSED! OS IS WORKING WELL!            *\n")
        print_str("************************************************************\n")
        return 0
    else:
        print_str("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        print_str("!              SOME TESTS FAILED                           !\n")
        print_str("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        return 1
