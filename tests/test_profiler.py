# Pynux Profiler Tests
#
# Tests for the function timing profiler module.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, assert_lt,
                                   test_pass, test_fail)
from lib.profiler import (profile_init, profile_start, profile_stop,
                          profile_reset, profile_enable, profile_disable,
                          profile_is_enabled, profile_get_count,
                          profile_get_calls, profile_get_total,
                          profile_get_avg, profile_get_max)

# ============================================================================
# Initialization Tests
# ============================================================================

def test_profile_init():
    """Test profiler initialization."""
    print_section("Profiler Initialization")

    profile_init()
    test_pass("profile_init completes")

    # Should be enabled after init
    assert_true(profile_is_enabled(), "enabled after init")

    # Count should be 0
    assert_eq(profile_get_count(), 0, "count is 0 after init")

def test_profile_enable_disable():
    """Test enable/disable."""
    profile_init()

    profile_disable()
    assert_false(profile_is_enabled(), "disabled after disable")

    profile_enable()
    assert_true(profile_is_enabled(), "enabled after enable")

# ============================================================================
# Basic Profiling Tests
# ============================================================================

def test_profile_basic():
    """Test basic start/stop."""
    print_section("Basic Profiling")

    profile_init()

    # Start a section
    profile_start("test_func")

    # Do some work
    i: int32 = 0
    while i < 100:
        i = i + 1

    # Stop the section
    profile_stop("test_func")

    # Should have 1 profiled section
    assert_eq(profile_get_count(), 1, "1 profiled section")

    # Should have 1 call
    calls: int32 = profile_get_calls("test_func")
    assert_eq(calls, 1, "1 call recorded")

def test_profile_multiple_calls():
    """Test multiple calls to same section."""
    profile_init()

    # Call section multiple times
    i: int32 = 0
    while i < 5:
        profile_start("multi")

        # Do some work
        j: int32 = 0
        while j < 50:
            j = j + 1

        profile_stop("multi")
        i = i + 1

    calls: int32 = profile_get_calls("multi")
    assert_eq(calls, 5, "5 calls recorded")

def test_profile_timing():
    """Test timing values are reasonable."""
    print_section("Timing Values")

    profile_init()

    profile_start("timing")

    # Do some work
    i: int32 = 0
    while i < 1000:
        i = i + 1

    profile_stop("timing")

    total: int32 = profile_get_total("timing")
    avg: int32 = profile_get_avg("timing")
    max_t: int32 = profile_get_max("timing")

    # Total should be > 0
    assert_gt(total, 0, "total time > 0")

    # Avg should equal total for 1 call
    assert_eq(avg, total, "avg equals total for 1 call")

    # Max should equal total for 1 call
    assert_eq(max_t, total, "max equals total for 1 call")

def test_profile_max_tracking():
    """Test max time tracking."""
    profile_init()

    # Do a short call
    profile_start("max_test")
    i: int32 = 0
    while i < 10:
        i = i + 1
    profile_stop("max_test")

    first_max: int32 = profile_get_max("max_test")

    # Do a longer call
    profile_start("max_test")
    i = 0
    while i < 1000:
        i = i + 1
    profile_stop("max_test")

    second_max: int32 = profile_get_max("max_test")

    # Max should have increased
    assert_gte(second_max, first_max, "max increased after longer call")

# ============================================================================
# Multiple Sections Tests
# ============================================================================

def test_profile_multiple_sections():
    """Test multiple named sections."""
    print_section("Multiple Sections")

    profile_init()

    # Create multiple sections
    profile_start("section_a")
    profile_stop("section_a")

    profile_start("section_b")
    profile_stop("section_b")

    profile_start("section_c")
    profile_stop("section_c")

    count: int32 = profile_get_count()
    assert_eq(count, 3, "3 sections created")

    # Each should have 1 call
    a_calls: int32 = profile_get_calls("section_a")
    b_calls: int32 = profile_get_calls("section_b")
    c_calls: int32 = profile_get_calls("section_c")

    assert_eq(a_calls, 1, "section_a has 1 call")
    assert_eq(b_calls, 1, "section_b has 1 call")
    assert_eq(c_calls, 1, "section_c has 1 call")

# ============================================================================
# Disabled State Tests
# ============================================================================

def test_profile_disabled():
    """Test profiling when disabled."""
    print_section("Disabled State")

    profile_init()
    profile_disable()

    # Start/stop should be no-ops
    profile_start("disabled_test")
    profile_stop("disabled_test")

    # Should not have created a section
    count: int32 = profile_get_count()
    assert_eq(count, 0, "no sections when disabled")

def test_profile_nested_ignored():
    """Test that nested calls to same section are ignored."""
    profile_init()

    # Start section
    profile_start("nested")

    # Try to start again (should be ignored)
    profile_start("nested")

    # Stop once
    profile_stop("nested")

    # Should still have 1 call
    calls: int32 = profile_get_calls("nested")
    assert_eq(calls, 1, "nested start ignored")

# ============================================================================
# Reset Tests
# ============================================================================

def test_profile_reset():
    """Test resetting profiler data."""
    print_section("Reset")

    profile_init()

    # Add some data
    profile_start("reset_test")
    profile_stop("reset_test")
    profile_start("reset_test")
    profile_stop("reset_test")

    assert_eq(profile_get_count(), 1, "1 section before reset")
    assert_eq(profile_get_calls("reset_test"), 2, "2 calls before reset")

    # Reset
    profile_reset()

    assert_eq(profile_get_count(), 0, "0 sections after reset")

# ============================================================================
# Unknown Section Tests
# ============================================================================

def test_profile_unknown_section():
    """Test querying unknown sections."""
    print_section("Unknown Section")

    profile_init()

    # Query non-existent section
    calls: int32 = profile_get_calls("nonexistent")
    total: int32 = profile_get_total("nonexistent")
    avg: int32 = profile_get_avg("nonexistent")
    max_t: int32 = profile_get_max("nonexistent")

    assert_eq(calls, 0, "unknown section has 0 calls")
    assert_eq(total, 0, "unknown section has 0 total")
    assert_eq(avg, 0, "unknown section has 0 avg")
    assert_eq(max_t, 0, "unknown section has 0 max")

# ============================================================================
# Main
# ============================================================================

def test_profiler_main() -> int32:
    print_str("\n=== Pynux Profiler Tests ===\n")

    test_profile_init()
    test_profile_enable_disable()

    test_profile_basic()
    test_profile_multiple_calls()
    test_profile_timing()
    test_profile_max_tracking()

    test_profile_multiple_sections()

    test_profile_disabled()
    test_profile_nested_ignored()

    test_profile_reset()

    test_profile_unknown_section()

    return print_results()
