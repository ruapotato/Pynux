# Pynux Comprehensive Test Runner
#
# Runs all available tests and reports results.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import reset_counters, get_passed, get_failed, print_section

# ============================================================================
# Test Suite Imports - import the test main functions directly
# ============================================================================

from tests.test_ipc import test_ipc_main
from tests.test_ramfs import test_ramfs_main
from tests.test_devfs import test_devfs_main
from tests.test_memory import test_memory_main
from tests.test_timer import test_timer_main

# ============================================================================
# Test Runner State
# ============================================================================

_suites_passed: int32 = 0
_suites_failed: int32 = 0
_total_tests_passed: int32 = 0
_total_tests_failed: int32 = 0

def run_suite_ipc():
    """Run IPC tests and track results."""
    global _suites_passed, _suites_failed
    global _total_tests_passed, _total_tests_failed

    print_str("\n============================================================\n")
    print_str("  IPC TESTS\n")
    print_str("============================================================\n")

    reset_counters()
    result: int32 = test_ipc_main()

    passed: int32 = get_passed()
    failed: int32 = get_failed()

    _total_tests_passed = _total_tests_passed + passed
    _total_tests_failed = _total_tests_failed + failed

    if result == 0 and failed == 0:
        _suites_passed = _suites_passed + 1
        print_str("\n[SUITE PASSED] IPC: ")
    else:
        _suites_failed = _suites_failed + 1
        print_str("\n[SUITE FAILED] IPC: ")

    print_int(passed)
    print_str(" passed, ")
    print_int(failed)
    print_str(" failed\n")

def run_suite_ramfs():
    """Run RAMFS tests and track results."""
    global _suites_passed, _suites_failed
    global _total_tests_passed, _total_tests_failed

    print_str("\n============================================================\n")
    print_str("  RAMFS TESTS\n")
    print_str("============================================================\n")

    reset_counters()
    result: int32 = test_ramfs_main()

    passed: int32 = get_passed()
    failed: int32 = get_failed()

    _total_tests_passed = _total_tests_passed + passed
    _total_tests_failed = _total_tests_failed + failed

    if result == 0 and failed == 0:
        _suites_passed = _suites_passed + 1
        print_str("\n[SUITE PASSED] RAMFS: ")
    else:
        _suites_failed = _suites_failed + 1
        print_str("\n[SUITE FAILED] RAMFS: ")

    print_int(passed)
    print_str(" passed, ")
    print_int(failed)
    print_str(" failed\n")

def run_suite_devfs():
    """Run DEVFS tests and track results."""
    global _suites_passed, _suites_failed
    global _total_tests_passed, _total_tests_failed

    print_str("\n============================================================\n")
    print_str("  DEVFS TESTS\n")
    print_str("============================================================\n")

    reset_counters()
    result: int32 = test_devfs_main()

    passed: int32 = get_passed()
    failed: int32 = get_failed()

    _total_tests_passed = _total_tests_passed + passed
    _total_tests_failed = _total_tests_failed + failed

    if result == 0 and failed == 0:
        _suites_passed = _suites_passed + 1
        print_str("\n[SUITE PASSED] DEVFS: ")
    else:
        _suites_failed = _suites_failed + 1
        print_str("\n[SUITE FAILED] DEVFS: ")

    print_int(passed)
    print_str(" passed, ")
    print_int(failed)
    print_str(" failed\n")

def run_suite_memory():
    """Run Memory tests and track results."""
    global _suites_passed, _suites_failed
    global _total_tests_passed, _total_tests_failed

    print_str("\n============================================================\n")
    print_str("  MEMORY TESTS\n")
    print_str("============================================================\n")

    reset_counters()
    result: int32 = test_memory_main()

    passed: int32 = get_passed()
    failed: int32 = get_failed()

    _total_tests_passed = _total_tests_passed + passed
    _total_tests_failed = _total_tests_failed + failed

    if result == 0 and failed == 0:
        _suites_passed = _suites_passed + 1
        print_str("\n[SUITE PASSED] MEMORY: ")
    else:
        _suites_failed = _suites_failed + 1
        print_str("\n[SUITE FAILED] MEMORY: ")

    print_int(passed)
    print_str(" passed, ")
    print_int(failed)
    print_str(" failed\n")

def run_suite_timer():
    """Run Timer tests and track results."""
    global _suites_passed, _suites_failed
    global _total_tests_passed, _total_tests_failed

    print_str("\n============================================================\n")
    print_str("  TIMER TESTS\n")
    print_str("============================================================\n")

    reset_counters()
    result: int32 = test_timer_main()

    passed: int32 = get_passed()
    failed: int32 = get_failed()

    _total_tests_passed = _total_tests_passed + passed
    _total_tests_failed = _total_tests_failed + failed

    if result == 0 and failed == 0:
        _suites_passed = _suites_passed + 1
        print_str("\n[SUITE PASSED] TIMER: ")
    else:
        _suites_failed = _suites_failed + 1
        print_str("\n[SUITE FAILED] TIMER: ")

    print_int(passed)
    print_str(" passed, ")
    print_int(failed)
    print_str(" failed\n")

def print_banner():
    """Print test banner."""
    print_str("\n")
    print_str("############################################################\n")
    print_str("#                                                          #\n")
    print_str("#        PYNUX COMPREHENSIVE TEST SUITE                    #\n")
    print_str("#                                                          #\n")
    print_str("#  Testing: Scheduler, Shell, IPC, Memory, Timer, FS       #\n")
    print_str("#                                                          #\n")
    print_str("############################################################\n")

def print_final_results():
    """Print final test results."""
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
        print_str("*                                                          *\n")
        print_str("*         ALL TESTS PASSED! PYNUX IS WORKING WELL!         *\n")
        print_str("*                                                          *\n")
        print_str("************************************************************\n")
    else:
        print_str("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        print_str("!                                                           !\n")
        print_str("!              SOME TESTS FAILED - SEE ABOVE                !\n")
        print_str("!                                                           !\n")
        print_str("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")

def run_tests_main():
    """Main test runner entry point."""
    print_banner()

    # Core OS tests
    run_suite_ipc()
    run_suite_memory()
    run_suite_timer()

    # Filesystem tests
    run_suite_ramfs()
    run_suite_devfs()

    print_final_results()

    if _total_tests_failed == 0:
        return 0
    return 1
