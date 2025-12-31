# Pynux Process Management Tests
#
# Tests for process creation, state management, and lifecycle.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_lt, test_pass, test_fail)
from kernel.process import (proc_create, proc_exit, proc_state, proc_wait,
                             proc_getpid, proc_cleanup, signal_send,
                             SIGTERM, SIGKILL, SIGUSR1, SIGUSR2,
                             PROC_STATE_READY, PROC_STATE_RUNNING,
                             PROC_STATE_BLOCKED, PROC_STATE_ZOMBIE,
                             MAX_PROCS)

# ============================================================================
# Process Creation Tests
# ============================================================================

def test_create_process():
    """Test basic process creation."""
    print_section("Process Creation")

    # Create a simple process
    pid: int32 = proc_create("test_proc")
    assert_gte(pid, 0, "create returns valid PID")

    # Verify process state
    state: int32 = proc_state(pid)
    assert_eq(state, PROC_STATE_READY, "new process is READY")

    # Clean up
    signal_send(pid, SIGTERM)

def test_create_multiple_processes():
    """Test creating multiple processes."""
    pids: Array[5, int32]
    i: int32 = 0

    # Create 5 processes
    while i < 5:
        pids[i] = proc_create("multi_proc")
        i = i + 1

    # Verify all were created successfully
    created: int32 = 0
    i = 0
    while i < 5:
        if pids[i] >= 0:
            created = created + 1
        i = i + 1

    assert_eq(created, 5, "create 5 processes")

    # Each should have unique PID
    unique: bool = True
    i = 0
    while i < 5 and unique:
        j: int32 = i + 1
        while j < 5:
            if pids[i] == pids[j]:
                unique = False
            j = j + 1
        i = i + 1

    assert_true(unique, "all PIDs are unique")

    # Clean up
    i = 0
    while i < 5:
        if pids[i] >= 0:
            signal_send(pids[i], SIGTERM)
        i = i + 1

def test_process_table_limit():
    """Test that process table respects MAX_PROCS limit."""
    pids: Array[20, int32]
    i: int32 = 0

    # Try to create MAX_PROCS + 2 processes
    while i < MAX_PROCS + 2:
        pids[i] = proc_create("limit_proc")
        i = i + 1

    # Count successful creations
    created: int32 = 0
    i = 0
    while i < MAX_PROCS + 2:
        if pids[i] >= 0:
            created = created + 1
        i = i + 1

    # Should not exceed MAX_PROCS
    assert_lt(created, MAX_PROCS + 1, "process table respects limit")

    # Clean up
    i = 0
    while i < MAX_PROCS + 2:
        if pids[i] >= 0:
            signal_send(pids[i], SIGTERM)
        i = i + 1

# ============================================================================
# Process State Tests
# ============================================================================

def test_process_states():
    """Test process state transitions."""
    print_section("Process States")

    # Create process
    pid: int32 = proc_create("state_proc")
    assert_gte(pid, 0, "create for state test")

    # Initial state should be READY
    state: int32 = proc_state(pid)
    assert_eq(state, PROC_STATE_READY, "initial state is READY")

    # Invalid PID should return error
    invalid_state: int32 = proc_state(-1)
    assert_eq(invalid_state, -1, "invalid PID returns -1")

    invalid_state = proc_state(9999)
    assert_eq(invalid_state, -1, "out-of-range PID returns -1")

    # Clean up
    signal_send(pid, SIGTERM)

def test_getpid():
    """Test getting current process ID."""
    # Current process should have valid PID
    my_pid: int32 = proc_getpid()
    assert_gte(my_pid, 0, "getpid returns valid PID")

    # Calling again should return same PID
    my_pid2: int32 = proc_getpid()
    assert_eq(my_pid, my_pid2, "getpid is consistent")

# ============================================================================
# Signal Tests
# ============================================================================

def test_signal_delivery():
    """Test signal sending."""
    print_section("Signals")

    # Create a process to signal
    pid: int32 = proc_create("signal_proc")
    assert_gte(pid, 0, "create for signal test")

    # Send SIGTERM - should succeed
    result: int32 = signal_send(pid, SIGTERM)
    assert_eq(result, 0, "SIGTERM delivery succeeds")

    # Create another process
    pid2: int32 = proc_create("signal_proc2")
    if pid2 >= 0:
        # Send SIGKILL
        result = signal_send(pid2, SIGKILL)
        assert_eq(result, 0, "SIGKILL delivery succeeds")

    # Signal to invalid PID should fail
    result = signal_send(-1, SIGTERM)
    assert_eq(result, -1, "signal to invalid PID fails")

def test_user_signals():
    """Test user-defined signals."""
    pid: int32 = proc_create("user_signal_proc")
    if pid < 0:
        test_fail("create for user signal test")
        return

    # Send SIGUSR1
    result: int32 = signal_send(pid, SIGUSR1)
    assert_eq(result, 0, "SIGUSR1 delivery")

    # Send SIGUSR2
    result = signal_send(pid, SIGUSR2)
    assert_eq(result, 0, "SIGUSR2 delivery")

    # Clean up
    signal_send(pid, SIGTERM)

# ============================================================================
# Process Cleanup Tests
# ============================================================================

def test_process_cleanup():
    """Test process cleanup reclaims resources."""
    print_section("Process Cleanup")

    # Create and immediately terminate processes
    i: int32 = 0
    while i < 3:
        pid: int32 = proc_create("cleanup_proc")
        if pid >= 0:
            signal_send(pid, SIGTERM)
            proc_cleanup(pid)
        i = i + 1

    test_pass("cleanup does not crash")

    # Should be able to create new processes after cleanup
    pid: int32 = proc_create("after_cleanup")
    assert_gte(pid, 0, "create after cleanup works")

    if pid >= 0:
        signal_send(pid, SIGTERM)

# ============================================================================
# Intuitive API Tests
# ============================================================================

def test_intuitive_process_api():
    """Test that the process API behaves intuitively."""
    print_section("Intuitive API")

    # Creating a process should return a positive PID
    pid: int32 = proc_create("intuitive")
    if pid >= 0:
        test_pass("proc_create returns usable PID")
    else:
        test_fail("proc_create should return positive PID")
        return

    # Getting state of valid process should work
    state: int32 = proc_state(pid)
    if state >= 0:
        test_pass("proc_state returns valid state")
    else:
        test_fail("proc_state should work on valid PID")

    # Signaling should return 0 on success
    result: int32 = signal_send(pid, SIGTERM)
    if result == 0:
        test_pass("signal_send returns 0 on success")
    else:
        test_fail("signal_send should return 0 on success")

    # After termination, state should reflect that
    # (might be ZOMBIE or cleaned up)

# ============================================================================
# Main
# ============================================================================

def test_process_main() -> int32:
    print_str("\n=== Pynux Process Management Tests ===\n")

    test_create_process()
    test_create_multiple_processes()
    test_process_table_limit()

    test_process_states()
    test_getpid()

    test_signal_delivery()
    test_user_signals()

    test_process_cleanup()

    test_intuitive_process_api()

    return print_results()
