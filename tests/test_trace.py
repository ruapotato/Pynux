# Pynux Execution Trace Tests
#
# Tests for the execution tracing module.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, assert_lt,
                                   test_pass, test_fail)
from lib.trace import (trace_init, trace_enable, trace_disable, trace_is_enabled,
                       trace_log, trace_clear, trace_get_count, trace_get_overflow,
                       trace_set_filter, trace_get_filter, trace_count_events,
                       trace_find_event, trace_log_func_enter, trace_log_func_exit,
                       trace_log_irq, trace_log_irq_exit, trace_log_error,
                       trace_log_user, trace_log_alloc, trace_log_free,
                       TRACE_FUNC_ENTER, TRACE_FUNC_EXIT, TRACE_IRQ, TRACE_IRQ_EXIT,
                       TRACE_ALLOC, TRACE_FREE, TRACE_ERROR, TRACE_USER)

# ============================================================================
# Initialization Tests
# ============================================================================

def test_trace_init():
    """Test trace initialization."""
    print_section("Trace Initialization")

    trace_init()
    test_pass("trace_init completes")

    # Should be disabled initially
    assert_false(trace_is_enabled(), "initially disabled")

    # Count should be 0
    assert_eq(trace_get_count(), 0, "count is 0 after init")

def test_trace_enable_disable():
    """Test enable/disable."""
    trace_init()

    trace_enable()
    assert_true(trace_is_enabled(), "enabled after enable")

    trace_disable()
    assert_false(trace_is_enabled(), "disabled after disable")

# ============================================================================
# Basic Logging Tests
# ============================================================================

def test_trace_log_basic():
    """Test basic event logging."""
    print_section("Basic Logging")

    trace_init()
    trace_enable()

    # Log some events
    trace_log(TRACE_USER, 0x12345678)
    assert_eq(trace_get_count(), 1, "count is 1 after log")

    trace_log(TRACE_USER, 0xABCDEF00)
    assert_eq(trace_get_count(), 2, "count is 2 after second log")

def test_trace_log_disabled():
    """Test that logging is ignored when disabled."""
    trace_init()
    trace_disable()

    trace_log(TRACE_USER, 0x11111111)
    assert_eq(trace_get_count(), 0, "no logging when disabled")

def test_trace_clear():
    """Test clearing the trace buffer."""
    trace_init()
    trace_enable()

    # Add some events
    trace_log(TRACE_USER, 1)
    trace_log(TRACE_USER, 2)
    trace_log(TRACE_USER, 3)
    assert_eq(trace_get_count(), 3, "3 events logged")

    # Clear
    trace_clear()
    assert_eq(trace_get_count(), 0, "count is 0 after clear")
    assert_eq(trace_get_overflow(), 0, "overflow is 0 after clear")

# ============================================================================
# Convenience Function Tests
# ============================================================================

def test_trace_func_events():
    """Test function enter/exit logging."""
    print_section("Function Tracing")

    trace_init()
    trace_enable()

    trace_log_func_enter(0x08001000)
    trace_log_func_exit(0x08001000)

    assert_eq(trace_get_count(), 2, "2 function events")

    # Check event counts
    enters: int32 = trace_count_events(TRACE_FUNC_ENTER)
    exits: int32 = trace_count_events(TRACE_FUNC_EXIT)

    assert_eq(enters, 1, "1 enter event")
    assert_eq(exits, 1, "1 exit event")

def test_trace_irq_events():
    """Test IRQ enter/exit logging."""
    trace_init()
    trace_enable()

    trace_log_irq(15)
    trace_log_irq_exit(15)

    irqs: int32 = trace_count_events(TRACE_IRQ)
    irq_exits: int32 = trace_count_events(TRACE_IRQ_EXIT)

    assert_eq(irqs, 1, "1 IRQ event")
    assert_eq(irq_exits, 1, "1 IRQ exit event")

def test_trace_alloc_free():
    """Test allocation/free logging."""
    trace_init()
    trace_enable()

    trace_log_alloc(0x20001000, 256)
    trace_log_free(0x20001000)

    allocs: int32 = trace_count_events(TRACE_ALLOC)
    frees: int32 = trace_count_events(TRACE_FREE)

    assert_eq(allocs, 1, "1 alloc event")
    assert_eq(frees, 1, "1 free event")

def test_trace_error():
    """Test error logging."""
    trace_init()
    trace_enable()

    trace_log_error(-1)
    trace_log_error(-2)

    errors: int32 = trace_count_events(TRACE_ERROR)
    assert_eq(errors, 2, "2 error events")

# ============================================================================
# Filter Tests
# ============================================================================

def test_trace_filter():
    """Test event filtering."""
    print_section("Event Filtering")

    trace_init()
    trace_enable()

    # Get default filter (should be 0xFFFF - all enabled)
    default_filter: int32 = trace_get_filter()
    assert_eq(default_filter, 0xFFFF, "default filter is 0xFFFF")

    # Disable all events
    trace_set_filter(0x0000)

    trace_log(TRACE_USER, 0x1234)
    assert_eq(trace_get_count(), 0, "no events with filter 0")

    # Enable only TRACE_USER (bit 16+)
    trace_set_filter(0xFF00)

    trace_log(TRACE_USER, 0x5678)
    assert_eq(trace_get_count(), 1, "user event logged with filter 0xFF00")

    # Reset filter
    trace_set_filter(0xFFFF)

# ============================================================================
# Search Tests
# ============================================================================

def test_trace_find_event():
    """Test finding events by type."""
    print_section("Event Search")

    trace_init()
    trace_enable()

    trace_log_func_enter(0x1000)
    trace_log_user(0xAAAA)
    trace_log_func_exit(0x1000)
    trace_log_user(0xBBBB)

    # Find first user event
    idx: int32 = trace_find_event(TRACE_USER, 0)
    assert_eq(idx, 1, "first user event at index 1")

    # Find second user event
    idx = trace_find_event(TRACE_USER, 2)
    assert_eq(idx, 3, "second user event at index 3")

    # Find non-existent event
    idx = trace_find_event(TRACE_ERROR, 0)
    assert_eq(idx, -1, "no error event returns -1")

def test_trace_count_events():
    """Test counting events by type."""
    trace_init()
    trace_enable()

    trace_log_user(1)
    trace_log_user(2)
    trace_log_user(3)
    trace_log_error(-1)

    user_count: int32 = trace_count_events(TRACE_USER)
    error_count: int32 = trace_count_events(TRACE_ERROR)
    alloc_count: int32 = trace_count_events(TRACE_ALLOC)

    assert_eq(user_count, 3, "3 user events")
    assert_eq(error_count, 1, "1 error event")
    assert_eq(alloc_count, 0, "0 alloc events")

# ============================================================================
# Circular Buffer Tests
# ============================================================================

def test_trace_circular_buffer():
    """Test circular buffer behavior."""
    print_section("Circular Buffer")

    trace_init()
    trace_enable()

    # Log many events to test wrapping (buffer is 256 entries)
    i: int32 = 0
    while i < 300:
        trace_log_user(cast[uint32](i))
        i = i + 1

    # Count should be capped at 256
    count: int32 = trace_get_count()
    assert_eq(count, 256, "count capped at buffer size")

    # Should have overflow
    overflow: int32 = trace_get_overflow()
    assert_eq(overflow, 44, "overflow count is 44")

# ============================================================================
# Main
# ============================================================================

def test_trace_main() -> int32:
    print_str("\n=== Pynux Trace Tests ===\n")

    test_trace_init()
    test_trace_enable_disable()

    test_trace_log_basic()
    test_trace_log_disabled()
    test_trace_clear()

    test_trace_func_events()
    test_trace_irq_events()
    test_trace_alloc_free()
    test_trace_error()

    test_trace_filter()

    test_trace_find_event()
    test_trace_count_events()

    test_trace_circular_buffer()

    return print_results()
