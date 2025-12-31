# Pynux Scheduler Stress Test
#
# Tests process table and pipe limits.

from lib.io import print_str, print_int, print_newline
from kernel.process import proc_create, proc_state, signal_send, SIGTERM
from kernel.process import pipe_create, pipe_write, pipe_read, pipe_close
from kernel.process import mq_create, mq_send, mq_receive, mq_close
from kernel.process import MAX_PROCS, MAX_PIPES, MAX_MESSAGE_QUEUES

# Test results
tests_passed: int32 = 0
tests_failed: int32 = 0

def test_pass(name: Ptr[char]):
    global tests_passed
    print_str("[PASS] ")
    print_str(name)
    print_newline()
    tests_passed = tests_passed + 1

def test_fail(name: Ptr[char]):
    global tests_failed
    print_str("[FAIL] ")
    print_str(name)
    print_newline()
    tests_failed = tests_failed + 1

# ============================================================================
# Process Table Tests
# ============================================================================

def test_process_table_limit():
    """Test that process table respects MAX_PROCS limit."""
    print_str("Testing process table limit...\n")

    created: int32 = 0
    i: int32 = 0

    # Try to create MAX_PROCS + 5 processes
    # Most should fail after limit is reached
    while i < MAX_PROCS + 5:
        pid: int32 = proc_create("test_proc")
        if pid >= 0:
            created = created + 1
        i = i + 1

    print_str("  Created ")
    print_int(created)
    print_str(" processes (max: ")
    print_int(MAX_PROCS)
    print_str(")\n")

    if created <= MAX_PROCS:
        test_pass("process_table_limit")
    else:
        test_fail("process_table_limit")

# ============================================================================
# Pipe Tests
# ============================================================================

def test_pipe_limit():
    """Test that pipe creation respects MAX_PIPES limit."""
    print_str("Testing pipe limit...\n")

    created: int32 = 0
    pipe_fds: Array[20, int32]
    i: int32 = 0

    # Try to create MAX_PIPES + 5 pipes
    while i < MAX_PIPES + 5:
        pipe_fds[i] = pipe_create()
        if pipe_fds[i] >= 0:
            created = created + 1
        i = i + 1

    print_str("  Created ")
    print_int(created)
    print_str(" pipes (max: ")
    print_int(MAX_PIPES)
    print_str(")\n")

    # Clean up - close all created pipes
    i = 0
    while i < MAX_PIPES + 5:
        if pipe_fds[i] >= 0:
            pipe_close(pipe_fds[i])
        i = i + 1

    if created <= MAX_PIPES:
        test_pass("pipe_limit")
    else:
        test_fail("pipe_limit")

def test_pipe_read_write():
    """Test pipe read/write operations."""
    print_str("Testing pipe read/write...\n")

    fd: int32 = pipe_create()
    if fd < 0:
        test_fail("pipe_read_write (create failed)")
        return

    # Write data
    write_buf: Array[16, uint8]
    write_buf[0] = 'H'
    write_buf[1] = 'i'
    write_buf[2] = '\0'

    written: int32 = pipe_write(fd, &write_buf[0], 3)
    if written != 3:
        test_fail("pipe_read_write (write failed)")
        pipe_close(fd)
        return

    # Read data
    read_buf: Array[16, uint8]
    read_len: int32 = pipe_read(fd, &read_buf[0], 16)

    pipe_close(fd)

    if read_len == 3 and read_buf[0] == 'H' and read_buf[1] == 'i':
        test_pass("pipe_read_write")
    else:
        test_fail("pipe_read_write")

def test_pipe_buffer_full():
    """Test pipe behavior when buffer is full."""
    print_str("Testing pipe buffer full...\n")

    fd: int32 = pipe_create()
    if fd < 0:
        test_fail("pipe_buffer_full (create failed)")
        return

    # Write until buffer is full (assuming 256 byte buffer)
    data: Array[32, uint8]
    i: int32 = 0
    while i < 32:
        data[i] = 'X'
        i = i + 1

    total_written: int32 = 0
    attempts: int32 = 0
    while attempts < 20:
        written: int32 = pipe_write(fd, &data[0], 32)
        if written <= 0:
            break
        total_written = total_written + written
        attempts = attempts + 1

    print_str("  Wrote ")
    print_int(total_written)
    print_str(" bytes before full\n")

    pipe_close(fd)

    # Should have written something but eventually stopped
    if total_written > 0 and attempts < 20:
        test_pass("pipe_buffer_full")
    else:
        test_fail("pipe_buffer_full")

# ============================================================================
# Message Queue Tests
# ============================================================================

def test_mq_limit():
    """Test message queue creation limit."""
    print_str("Testing message queue limit...\n")

    created: int32 = 0
    mq_ids: Array[10, int32]
    i: int32 = 0

    # Try to create MAX_MESSAGE_QUEUES + 2 queues
    while i < MAX_MESSAGE_QUEUES + 2:
        mq_ids[i] = mq_create()
        if mq_ids[i] >= 0:
            created = created + 1
        i = i + 1

    print_str("  Created ")
    print_int(created)
    print_str(" queues (max: ")
    print_int(MAX_MESSAGE_QUEUES)
    print_str(")\n")

    # Clean up
    i = 0
    while i < MAX_MESSAGE_QUEUES + 2:
        if mq_ids[i] >= 0:
            mq_close(mq_ids[i])
        i = i + 1

    if created <= MAX_MESSAGE_QUEUES:
        test_pass("mq_limit")
    else:
        test_fail("mq_limit")

def test_mq_send_receive():
    """Test message queue send/receive."""
    print_str("Testing message queue send/receive...\n")

    mqid: int32 = mq_create()
    if mqid < 0:
        test_fail("mq_send_receive (create failed)")
        return

    # Send message
    msg: Array[16, uint8]
    msg[0] = 'T'
    msg[1] = 'E'
    msg[2] = 'S'
    msg[3] = 'T'

    success: bool = mq_send(mqid, &msg[0], 4)
    if not success:
        test_fail("mq_send_receive (send failed)")
        mq_close(mqid)
        return

    # Receive message
    recv_buf: Array[64, uint8]
    recv_len: int32 = mq_receive(mqid, &recv_buf[0], 64)

    mq_close(mqid)

    if recv_len == 4 and recv_buf[0] == 'T' and recv_buf[3] == 'T':
        test_pass("mq_send_receive")
    else:
        test_fail("mq_send_receive")

def test_mq_full():
    """Test message queue full behavior."""
    print_str("Testing message queue full...\n")

    mqid: int32 = mq_create()
    if mqid < 0:
        test_fail("mq_full (create failed)")
        return

    msg: Array[64, uint8]
    i: int32 = 0
    while i < 64:
        msg[i] = 'M'
        i = i + 1

    # Send messages until queue is full
    sent: int32 = 0
    while sent < 20:
        success: bool = mq_send(mqid, &msg[0], 32)
        if not success:
            break
        sent = sent + 1

    print_str("  Sent ")
    print_int(sent)
    print_str(" messages before full\n")

    mq_close(mqid)

    # Should have sent some but eventually failed
    if sent > 0 and sent < 20:
        test_pass("mq_full")
    else:
        test_fail("mq_full")

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    print_str("\n=== Scheduler Stress Tests ===\n\n")

    # Process tests
    test_process_table_limit()

    # Pipe tests
    test_pipe_limit()
    test_pipe_read_write()
    test_pipe_buffer_full()

    # Message queue tests
    test_mq_limit()
    test_mq_send_receive()
    test_mq_full()

    print_str("\n=== Results ===\n")
    print_str("Passed: ")
    print_int(tests_passed)
    print_newline()
    print_str("Failed: ")
    print_int(tests_failed)
    print_newline()

    if tests_failed == 0:
        print_str("\nAll tests passed!\n")
        return 0
    else:
        print_str("\nSome tests failed.\n")
        return 1
