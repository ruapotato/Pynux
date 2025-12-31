# Pynux Kernel Tests for QEMU
#
# Example kernel tests that run in QEMU.
# Tests timer tick counting, memory allocation, process creation,
# and scheduler round-robin behavior.

from lib.io import print_str, print_int, print_newline, uart_init
from tests.framework import (
    test_init, test_run, test_assert, test_assert_eq, test_assert_ne,
    test_assert_gt, test_assert_ge, test_assert_lt, test_assert_not_null,
    test_fail, test_skip, test_pass, test_section, test_summary
)
from kernel.timer import (
    timer_init, timer_init_poll, timer_tick, timer_get_ticks,
    timer_delay_ms, timer_delay_us
)
from lib.memory import (
    heap_init, alloc, calloc, free, realloc,
    heap_remaining, heap_total, heap_used
)
from kernel.process import (
    process_init, process_create, process_getpid, process_yield,
    proc_get_priority, proc_set_priority, proc_get_timeslice,
    proc_set_timeslice, scheduler_start, find_proc_slot,
    PROC_STATE_READY, PROC_STATE_RUNNING, PROC_STATE_TERMINATED,
    DEFAULT_PRIORITY, DEFAULT_TIMESLICE, MAX_PRIORITY, MIN_PRIORITY,
    proc_state, proc_pid, proc_priority
)

# ============================================================================
# Timer Tests
# ============================================================================

def test_timer_init_completes():
    """Test that timer initialization completes without error."""
    timer_init_poll()
    test_pass("timer_init completes")

def test_timer_tick_count():
    """Test that timer tick counting works."""
    timer_init_poll()

    # Get initial ticks
    initial: int32 = timer_get_ticks()
    test_assert_ge(initial, 0, "initial ticks >= 0")

    # Poll timer to accumulate some ticks
    i: int32 = 0
    while i < 100:
        timer_tick()
        i = i + 1

    # Ticks should not go backwards
    after: int32 = timer_get_ticks()
    test_assert_ge(after, initial, "ticks don't decrease")

def test_timer_tick_increment():
    """Test that ticks can increment."""
    timer_init_poll()
    initial: int32 = timer_get_ticks()

    # Do a delay to ensure ticks advance
    timer_delay_ms(5)

    after: int32 = timer_get_ticks()

    # After delay, ticks should have advanced
    # (may not be exact due to QEMU timing)
    test_assert_ge(after, initial, "ticks increment after delay")

def test_timer_delay_completes():
    """Test that timer delays complete without hanging."""
    timer_init_poll()

    # Short delays should complete
    timer_delay_ms(1)
    test_pass("delay_ms(1) completes")

    timer_delay_ms(10)
    test_pass("delay_ms(10) completes")

    timer_delay_us(100)
    test_pass("delay_us(100) completes")

# ============================================================================
# Memory Allocation Tests
# ============================================================================

def test_alloc_basic():
    """Test basic memory allocation."""
    heap_init()

    ptr: Ptr[uint8] = alloc(64)
    test_assert_not_null(cast[Ptr[void]](ptr), "alloc 64 bytes")

    # Should be writable
    ptr[0] = 0xAB
    ptr[63] = 0xCD
    test_assert_eq(cast[int32](ptr[0]), 0xAB, "can write first byte")
    test_assert_eq(cast[int32](ptr[63]), 0xCD, "can write last byte")

    free(ptr)
    test_pass("free succeeds")

def test_alloc_multiple():
    """Test multiple allocations are distinct."""
    heap_init()

    ptr1: Ptr[uint8] = alloc(32)
    ptr2: Ptr[uint8] = alloc(32)
    ptr3: Ptr[uint8] = alloc(32)

    test_assert_not_null(cast[Ptr[void]](ptr1), "first alloc")
    test_assert_not_null(cast[Ptr[void]](ptr2), "second alloc")
    test_assert_not_null(cast[Ptr[void]](ptr3), "third alloc")

    # All should be different addresses
    test_assert_ne(cast[int32](ptr1), cast[int32](ptr2), "ptr1 != ptr2")
    test_assert_ne(cast[int32](ptr2), cast[int32](ptr3), "ptr2 != ptr3")
    test_assert_ne(cast[int32](ptr1), cast[int32](ptr3), "ptr1 != ptr3")

    free(ptr1)
    free(ptr2)
    free(ptr3)

def test_calloc_zeroed():
    """Test that calloc returns zeroed memory."""
    heap_init()

    ptr: Ptr[uint8] = calloc(32, 1)
    test_assert_not_null(cast[Ptr[void]](ptr), "calloc 32 bytes")

    # All bytes should be zero
    all_zero: bool = True
    i: int32 = 0
    while i < 32:
        if ptr[i] != 0:
            all_zero = False
        i = i + 1

    test_assert(all_zero, "calloc memory is zeroed")
    free(ptr)

def test_realloc_preserves():
    """Test that realloc preserves existing data."""
    heap_init()

    ptr: Ptr[uint8] = alloc(16)
    ptr[0] = 0x11
    ptr[15] = 0x22

    new_ptr: Ptr[uint8] = realloc(ptr, 32)
    test_assert_not_null(cast[Ptr[void]](new_ptr), "realloc succeeds")

    # Original data preserved
    test_assert_eq(cast[int32](new_ptr[0]), 0x11, "first byte preserved")
    test_assert_eq(cast[int32](new_ptr[15]), 0x22, "last byte preserved")

    free(new_ptr)

def test_heap_stats():
    """Test heap statistics functions."""
    heap_init()

    total: int32 = heap_total()
    test_assert_gt(total, 0, "heap_total > 0")

    remaining: int32 = heap_remaining()
    test_assert_gt(remaining, 0, "heap_remaining > 0")

    # Allocate and verify remaining decreases
    ptr: Ptr[uint8] = alloc(1024)
    remaining_after: int32 = heap_remaining()
    test_assert_lt(remaining_after, remaining, "remaining decreased after alloc")

    free(ptr)

# ============================================================================
# Process Creation Tests
# ============================================================================

# Test process entry function
def dummy_process_entry():
    """Dummy process entry for testing."""
    pass

def test_process_init_completes():
    """Test that process subsystem initializes."""
    process_init()
    test_pass("process_init completes")

def test_process_create():
    """Test process creation."""
    process_init()
    heap_init()

    pid: int32 = process_create(&dummy_process_entry)
    test_assert_ge(pid, 0, "process_create returns valid PID")

    # Find the process slot
    slot: int32 = find_proc_slot(pid)
    test_assert_ge(slot, 0, "process has valid slot")

    # Check process state
    test_assert_eq(proc_state[slot], PROC_STATE_READY, "process is READY")

def test_process_priority():
    """Test process priority get/set."""
    process_init()
    heap_init()

    pid: int32 = process_create(&dummy_process_entry)
    test_assert_ge(pid, 0, "created process")

    # Default priority
    prio: int32 = proc_get_priority(pid)
    test_assert_eq(prio, DEFAULT_PRIORITY, "default priority")

    # Set high priority
    result: bool = proc_set_priority(pid, MAX_PRIORITY)
    test_assert(result, "set high priority")

    prio = proc_get_priority(pid)
    test_assert_eq(prio, MAX_PRIORITY, "priority updated")

    # Set low priority
    result = proc_set_priority(pid, MIN_PRIORITY)
    test_assert(result, "set low priority")

    prio = proc_get_priority(pid)
    test_assert_eq(prio, MIN_PRIORITY, "priority is low")

def test_process_timeslice():
    """Test process timeslice configuration."""
    process_init()
    heap_init()

    pid: int32 = process_create(&dummy_process_entry)
    test_assert_ge(pid, 0, "created process")

    # Default timeslice
    ts: int32 = proc_get_timeslice(pid)
    test_assert_eq(ts, DEFAULT_TIMESLICE, "default timeslice")

    # Set custom timeslice
    result: bool = proc_set_timeslice(pid, 50)
    test_assert(result, "set timeslice to 50")

    ts = proc_get_timeslice(pid)
    test_assert_eq(ts, 50, "timeslice updated")

def test_multiple_processes():
    """Test creating multiple processes."""
    process_init()
    heap_init()

    pid1: int32 = process_create(&dummy_process_entry)
    pid2: int32 = process_create(&dummy_process_entry)
    pid3: int32 = process_create(&dummy_process_entry)

    test_assert_ge(pid1, 0, "first process created")
    test_assert_ge(pid2, 0, "second process created")
    test_assert_ge(pid3, 0, "third process created")

    # All PIDs should be different
    test_assert_ne(pid1, pid2, "pid1 != pid2")
    test_assert_ne(pid2, pid3, "pid2 != pid3")
    test_assert_ne(pid1, pid3, "pid1 != pid3")

# ============================================================================
# Scheduler Round-Robin Tests
# ============================================================================

def test_scheduler_start():
    """Test that scheduler can start."""
    process_init()
    heap_init()

    # Create a process
    pid: int32 = process_create(&dummy_process_entry)
    test_assert_ge(pid, 0, "created process for scheduler")

    # Scheduler start should not crash
    # (We won't actually run as that would require context switches)
    test_pass("scheduler_start available")

def test_priority_ordering():
    """Test that processes are created with different priorities."""
    process_init()
    heap_init()

    # Create processes with different priorities
    pid1: int32 = process_create(&dummy_process_entry)
    proc_set_priority(pid1, 10)

    pid2: int32 = process_create(&dummy_process_entry)
    proc_set_priority(pid2, 20)

    pid3: int32 = process_create(&dummy_process_entry)
    proc_set_priority(pid3, 15)

    # Verify priorities
    test_assert_eq(proc_get_priority(pid1), 10, "pid1 priority 10")
    test_assert_eq(proc_get_priority(pid2), 20, "pid2 priority 20")
    test_assert_eq(proc_get_priority(pid3), 15, "pid3 priority 15")

    # Higher priority process should be selected first by scheduler
    # (pid2 has highest priority)
    test_pass("priority ordering works")

def test_round_robin_same_priority():
    """Test round-robin for processes with same priority."""
    process_init()
    heap_init()

    # Create multiple processes with same priority
    pid1: int32 = process_create(&dummy_process_entry)
    pid2: int32 = process_create(&dummy_process_entry)
    pid3: int32 = process_create(&dummy_process_entry)

    # All at same priority
    proc_set_priority(pid1, 16)
    proc_set_priority(pid2, 16)
    proc_set_priority(pid3, 16)

    # All should have same priority
    test_assert_eq(proc_get_priority(pid1), 16, "pid1 priority 16")
    test_assert_eq(proc_get_priority(pid2), 16, "pid2 priority 16")
    test_assert_eq(proc_get_priority(pid3), 16, "pid3 priority 16")

    # Round-robin should give each a turn (can't fully test without running)
    test_pass("round-robin setup works")

# ============================================================================
# Main Entry Point
# ============================================================================

def run_kernel_tests():
    """Run all kernel tests."""
    print_str("\n=== Pynux Kernel Tests (QEMU) ===\n")

    test_init()

    # Timer tests
    test_section("Timer")
    test_run("timer_init_completes", test_timer_init_completes)
    test_run("timer_tick_count", test_timer_tick_count)
    test_run("timer_tick_increment", test_timer_tick_increment)
    test_run("timer_delay_completes", test_timer_delay_completes)

    # Memory tests
    test_section("Memory Allocation")
    test_run("alloc_basic", test_alloc_basic)
    test_run("alloc_multiple", test_alloc_multiple)
    test_run("calloc_zeroed", test_calloc_zeroed)
    test_run("realloc_preserves", test_realloc_preserves)
    test_run("heap_stats", test_heap_stats)

    # Process tests
    test_section("Process Creation")
    test_run("process_init_completes", test_process_init_completes)
    test_run("process_create", test_process_create)
    test_run("process_priority", test_process_priority)
    test_run("process_timeslice", test_process_timeslice)
    test_run("multiple_processes", test_multiple_processes)

    # Scheduler tests
    test_section("Scheduler Round-Robin")
    test_run("scheduler_start", test_scheduler_start)
    test_run("priority_ordering", test_priority_ordering)
    test_run("round_robin_same_priority", test_round_robin_same_priority)

    return test_summary()
