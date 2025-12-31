# Pynux Test Framework
#
# Compatibility wrapper - re-exports from tests/framework.py
# All test infrastructure is now in tests/framework.py

from tests.framework import test_init, test_run, test_summary
from tests.framework import test_assert, test_assert_eq, test_assert_ne
from tests.framework import test_assert_lt, test_assert_gt, test_assert_le, test_assert_ge
from tests.framework import test_assert_not_null, test_assert_null
from tests.framework import test_pass, test_fail, test_skip, test_section
from tests.framework import get_tests_passed, get_tests_failed, get_tests_skipped, get_tests_total

# Backward-compatible aliases
from tests.framework import assert_true, assert_false, assert_eq, assert_neq
from tests.framework import assert_gt, assert_gte, assert_lt, assert_lte
from tests.framework import assert_not_null, assert_null
from tests.framework import print_section, print_results, reset_counters
from tests.framework import get_passed, get_failed
