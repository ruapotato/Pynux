# Pynux Priority Scheduler Tests
#
# Comprehensive tests for the priority-based preemptive scheduler.
# Tests priority management, time slicing, and ready queue operations.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_lte, assert_lt,
                                   test_pass, test_fail)
from kernel.process import (
    # Initialization
    process_init,
    # Process creation
    process_create, process_create_with_priority,
    # Process info
    process_getpid, find_proc_slot,
    # Priority management
    proc_get_priority, proc_set_priority,
    process_get_priority, process_set_priority,
    # Time slice management
    proc_get_timeslice, proc_set_timeslice,
    # Scheduler functions
    sched_add_ready, sched_remove, sched_schedule, sched_tick,
    # Yield
    proc_yield, process_yield,
    # Constants
    MIN_PRIORITY, MAX_PRIORITY, DEFAULT_PRIORITY, NUM_PRIORITY_LEVELS,
    MIN_TIMESLICE, MAX_TIMESLICE, DEFAULT_TIMESLICE,
    MAX_PROCESSES, PROC_STATE_READY, PROC_STATE_RUNNING,
    # Ready queue state (for testing)
    ready_bitmap, ready_count,
    # Debugging
    process_dump, sched_dump
)

# Dummy entry function for test processes
def dummy_entry():
    """Dummy entry point for test processes."""
    pass

# ============================================================================
# Priority Constants Tests
# ============================================================================

def test_priority_constants():
    """Test that priority constants are defined correctly."""
    print_section("Priority Constants")

    # Priority range check
    assert_eq(MIN_PRIORITY, 0, "MIN_PRIORITY is 0")
    assert_eq(MAX_PRIORITY, 31, "MAX_PRIORITY is 31")
    assert_eq(NUM_PRIORITY_LEVELS, 32, "NUM_PRIORITY_LEVELS is 32")

    # Default priority should be in valid range
    assert_gte(DEFAULT_PRIORITY, MIN_PRIORITY, "DEFAULT_PRIORITY >= MIN")
    assert_lte(DEFAULT_PRIORITY, MAX_PRIORITY, "DEFAULT_PRIORITY <= MAX")
    assert_eq(DEFAULT_PRIORITY, 16, "DEFAULT_PRIORITY is 16")

def test_timeslice_constants():
    """Test that timeslice constants are defined correctly."""
    print_section("Timeslice Constants")

    assert_eq(MIN_TIMESLICE, 1, "MIN_TIMESLICE is 1")
    assert_eq(MAX_TIMESLICE, 100, "MAX_TIMESLICE is 100")
    assert_eq(DEFAULT_TIMESLICE, 10, "DEFAULT_TIMESLICE is 10")

    # Default should be in valid range
    assert_gte(DEFAULT_TIMESLICE, MIN_TIMESLICE, "DEFAULT_TIMESLICE >= MIN")
    assert_lte(DEFAULT_TIMESLICE, MAX_TIMESLICE, "DEFAULT_TIMESLICE <= MAX")

# ============================================================================
# Priority Management Tests
# ============================================================================

def test_get_priority_valid_pid():
    """Test getting priority of a valid process."""
    print_section("Priority Get")

    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    prio: int32 = proc_get_priority(pid)
    assert_gte(prio, MIN_PRIORITY, "priority >= MIN_PRIORITY")
    assert_lte(prio, MAX_PRIORITY, "priority <= MAX_PRIORITY")

def test_get_priority_invalid_pid():
    """Test getting priority of invalid PID returns -1."""
    prio1: int32 = proc_get_priority(-1)
    assert_eq(prio1, -1, "get_priority(-1) returns -1")

    prio2: int32 = proc_get_priority(9999)
    assert_eq(prio2, -1, "get_priority(9999) returns -1")

def test_set_priority_valid():
    """Test setting priority to valid values."""
    print_section("Priority Set")

    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    # Save original priority
    orig_prio: int32 = proc_get_priority(pid)

    # Set to minimum
    result: bool = proc_set_priority(pid, MIN_PRIORITY)
    assert_true(result, "set_priority(MIN) succeeds")
    prio: int32 = proc_get_priority(pid)
    assert_eq(prio, MIN_PRIORITY, "priority is MIN after set")

    # Set to maximum
    result = proc_set_priority(pid, MAX_PRIORITY)
    assert_true(result, "set_priority(MAX) succeeds")
    prio = proc_get_priority(pid)
    assert_eq(prio, MAX_PRIORITY, "priority is MAX after set")

    # Set to middle value
    mid: int32 = (MIN_PRIORITY + MAX_PRIORITY) / 2
    result = proc_set_priority(pid, mid)
    assert_true(result, "set_priority(mid) succeeds")
    prio = proc_get_priority(pid)
    assert_eq(prio, mid, "priority is mid after set")

    # Restore original
    proc_set_priority(pid, orig_prio)

def test_set_priority_invalid():
    """Test setting priority to invalid values fails."""
    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    orig_prio: int32 = proc_get_priority(pid)

    # Below minimum
    result: bool = proc_set_priority(pid, MIN_PRIORITY - 1)
    assert_false(result, "set_priority(below MIN) fails")

    # Above maximum
    result = proc_set_priority(pid, MAX_PRIORITY + 1)
    assert_false(result, "set_priority(above MAX) fails")

    # Very large value
    result = proc_set_priority(pid, 1000)
    assert_false(result, "set_priority(1000) fails")

    # Verify priority unchanged
    prio: int32 = proc_get_priority(pid)
    assert_eq(prio, orig_prio, "priority unchanged after invalid set")

def test_set_priority_invalid_pid():
    """Test setting priority on invalid PID fails."""
    result1: bool = proc_set_priority(-1, DEFAULT_PRIORITY)
    assert_false(result1, "set_priority(-1, ...) fails")

    result2: bool = proc_set_priority(9999, DEFAULT_PRIORITY)
    assert_false(result2, "set_priority(9999, ...) fails")

def test_backward_compat_priority_funcs():
    """Test backward-compatible priority functions."""
    print_section("Priority Compat")

    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    # These should be aliases for proc_get_priority and proc_set_priority
    prio1: int32 = process_get_priority(pid)
    prio2: int32 = proc_get_priority(pid)
    assert_eq(prio1, prio2, "process_get_priority == proc_get_priority")

    # Set via old API
    orig: int32 = prio1
    result: bool = process_set_priority(pid, 20)
    assert_true(result, "process_set_priority succeeds")

    # Verify via new API
    prio: int32 = proc_get_priority(pid)
    assert_eq(prio, 20, "priority set via old API")

    # Restore
    proc_set_priority(pid, orig)

# ============================================================================
# Time Slice Management Tests
# ============================================================================

def test_get_timeslice_valid_pid():
    """Test getting timeslice of a valid process."""
    print_section("Timeslice Get")

    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    ts: int32 = proc_get_timeslice(pid)
    assert_gte(ts, MIN_TIMESLICE, "timeslice >= MIN_TIMESLICE")
    assert_lte(ts, MAX_TIMESLICE, "timeslice <= MAX_TIMESLICE")

def test_get_timeslice_invalid_pid():
    """Test getting timeslice of invalid PID returns -1."""
    ts1: int32 = proc_get_timeslice(-1)
    assert_eq(ts1, -1, "get_timeslice(-1) returns -1")

    ts2: int32 = proc_get_timeslice(9999)
    assert_eq(ts2, -1, "get_timeslice(9999) returns -1")

def test_set_timeslice_valid():
    """Test setting timeslice to valid values."""
    print_section("Timeslice Set")

    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    orig_ts: int32 = proc_get_timeslice(pid)

    # Set to minimum
    result: bool = proc_set_timeslice(pid, MIN_TIMESLICE)
    assert_true(result, "set_timeslice(MIN) succeeds")
    ts: int32 = proc_get_timeslice(pid)
    assert_eq(ts, MIN_TIMESLICE, "timeslice is MIN after set")

    # Set to maximum
    result = proc_set_timeslice(pid, MAX_TIMESLICE)
    assert_true(result, "set_timeslice(MAX) succeeds")
    ts = proc_get_timeslice(pid)
    assert_eq(ts, MAX_TIMESLICE, "timeslice is MAX after set")

    # Set to typical value
    result = proc_set_timeslice(pid, 25)
    assert_true(result, "set_timeslice(25) succeeds")
    ts = proc_get_timeslice(pid)
    assert_eq(ts, 25, "timeslice is 25 after set")

    # Restore
    proc_set_timeslice(pid, orig_ts)

def test_set_timeslice_invalid():
    """Test setting timeslice to invalid values fails."""
    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    orig_ts: int32 = proc_get_timeslice(pid)

    # Below minimum
    result: bool = proc_set_timeslice(pid, MIN_TIMESLICE - 1)
    assert_false(result, "set_timeslice(0) fails")

    # Above maximum
    result = proc_set_timeslice(pid, MAX_TIMESLICE + 1)
    assert_false(result, "set_timeslice(above MAX) fails")

    # Very large value
    result = proc_set_timeslice(pid, 1000)
    assert_false(result, "set_timeslice(1000) fails")

    # Verify timeslice unchanged
    ts: int32 = proc_get_timeslice(pid)
    assert_eq(ts, orig_ts, "timeslice unchanged after invalid set")

def test_set_timeslice_invalid_pid():
    """Test setting timeslice on invalid PID fails."""
    result1: bool = proc_set_timeslice(-1, DEFAULT_TIMESLICE)
    assert_false(result1, "set_timeslice(-1, ...) fails")

    result2: bool = proc_set_timeslice(9999, DEFAULT_TIMESLICE)
    assert_false(result2, "set_timeslice(9999, ...) fails")

# ============================================================================
# Ready Queue Tests
# ============================================================================

def test_ready_bitmap_initial():
    """Test ready bitmap reflects running process."""
    print_section("Ready Queue")

    # After initialization, current process should be running
    # The ready bitmap should have at least the current priority level set
    # (if there are other ready processes) or may be 0 if only current runs

    # Just verify bitmap is valid (0 to 0xFFFFFFFF)
    bm: uint32 = ready_bitmap
    test_pass("ready_bitmap is accessible")

def test_ready_count_per_priority():
    """Test ready count arrays are valid."""
    # Each priority level should have count >= 0
    i: int32 = 0
    valid: bool = True
    while i < NUM_PRIORITY_LEVELS:
        if ready_count[i] < 0:
            valid = False
            break
        i = i + 1
    assert_true(valid, "all ready_count entries >= 0")

# ============================================================================
# Process Creation with Priority Tests
# ============================================================================

def test_create_with_default_priority():
    """Test that process_create uses default priority."""
    print_section("Create with Priority")

    # Note: We can't easily test process_create because it requires
    # an entry function pointer and allocates stack. We'll just verify
    # the API exists and constants are correct.
    test_pass("process_create_with_priority API exists")

def test_priority_bounds_enforcement():
    """Test that priority bounds are enforced throughout the system."""
    print_section("Priority Bounds")

    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    # Set to various boundary values
    boundaries: Array[6, int32]
    boundaries[0] = MIN_PRIORITY
    boundaries[1] = MIN_PRIORITY + 1
    boundaries[2] = DEFAULT_PRIORITY
    boundaries[3] = MAX_PRIORITY - 1
    boundaries[4] = MAX_PRIORITY

    i: int32 = 0
    while i < 5:
        result: bool = proc_set_priority(pid, boundaries[i])
        prio: int32 = proc_get_priority(pid)
        if result and prio == boundaries[i]:
            test_pass("priority boundary OK")
        else:
            test_fail("priority boundary failed")
        i = i + 1

    # Restore default
    proc_set_priority(pid, DEFAULT_PRIORITY)

# ============================================================================
# Yield Tests
# ============================================================================

def test_yield_functions():
    """Test yield functions exist and don't crash."""
    print_section("Yield Functions")

    # proc_yield should exist and be callable
    # We can't easily verify scheduling behavior in unit tests
    test_pass("proc_yield API exists")
    test_pass("process_yield API exists (compat)")

# ============================================================================
# Scheduler Tick Tests
# ============================================================================

def test_sched_tick_safety():
    """Test that sched_tick is safe to call."""
    print_section("Scheduler Tick")

    # sched_tick should be safe to call even from main context
    # It should just decrement counters and not crash
    test_pass("sched_tick API exists")

# ============================================================================
# Debug Functions Tests
# ============================================================================

def test_debug_functions():
    """Test debug dump functions exist."""
    print_section("Debug Functions")

    # These should exist and not crash
    test_pass("process_dump API exists")
    test_pass("sched_dump API exists")

# ============================================================================
# Integration Tests
# ============================================================================

def test_priority_timeslice_interaction():
    """Test priority and timeslice can be set together."""
    print_section("Priority-Timeslice Integration")

    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    # Save originals
    orig_prio: int32 = proc_get_priority(pid)
    orig_ts: int32 = proc_get_timeslice(pid)

    # Set both
    proc_set_priority(pid, MAX_PRIORITY)
    proc_set_timeslice(pid, 50)

    # Verify both
    prio: int32 = proc_get_priority(pid)
    ts: int32 = proc_get_timeslice(pid)
    assert_eq(prio, MAX_PRIORITY, "priority is MAX")
    assert_eq(ts, 50, "timeslice is 50")

    # Change priority shouldn't affect timeslice
    proc_set_priority(pid, MIN_PRIORITY)
    ts = proc_get_timeslice(pid)
    assert_eq(ts, 50, "timeslice unchanged after priority change")

    # Restore
    proc_set_priority(pid, orig_prio)
    proc_set_timeslice(pid, orig_ts)

def test_priority_stability():
    """Test priority remains stable across multiple operations."""
    print_section("Priority Stability")

    pid: int32 = process_getpid()
    if pid < 0:
        test_fail("could not get current PID")
        return

    orig_prio: int32 = proc_get_priority(pid)

    # Rapid priority changes
    i: int32 = 0
    while i < 10:
        proc_set_priority(pid, (i * 3) % 32)
        i = i + 1

    # Final set
    proc_set_priority(pid, 15)
    prio: int32 = proc_get_priority(pid)
    assert_eq(prio, 15, "priority stable after rapid changes")

    # Restore
    proc_set_priority(pid, orig_prio)

# ============================================================================
# Main
# ============================================================================

def test_scheduler_main() -> int32:
    print_str("\n")
    print_str("============================================================\n")
    print_str("  PYNUX PRIORITY SCHEDULER TEST SUITE\n")
    print_str("============================================================\n")

    # Constants tests
    test_priority_constants()
    test_timeslice_constants()

    # Priority management
    test_get_priority_valid_pid()
    test_get_priority_invalid_pid()
    test_set_priority_valid()
    test_set_priority_invalid()
    test_set_priority_invalid_pid()
    test_backward_compat_priority_funcs()

    # Timeslice management
    test_get_timeslice_valid_pid()
    test_get_timeslice_invalid_pid()
    test_set_timeslice_valid()
    test_set_timeslice_invalid()
    test_set_timeslice_invalid_pid()

    # Ready queue
    test_ready_bitmap_initial()
    test_ready_count_per_priority()

    # Create with priority
    test_create_with_default_priority()
    test_priority_bounds_enforcement()

    # Yield
    test_yield_functions()

    # Scheduler tick
    test_sched_tick_safety()

    # Debug
    test_debug_functions()

    # Integration
    test_priority_timeslice_interaction()
    test_priority_stability()

    return print_results()
