# Pynux IPC Tests
#
# Tests for inter-process communication: pipes, message queues.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, assert_lt,
                                   test_pass, test_fail)
from kernel.process import (pipe_create, pipe_read, pipe_write, pipe_close,
                             mq_create, mq_send, mq_receive, mq_close,
                             MAX_PIPES, MAX_MESSAGE_QUEUES)

# Helper: unpack read fd from pipe_create result (low 16 bits)
def pipe_get_read_fd(pfd: int32) -> int32:
    return pfd & 65535  # 0xFFFF

# Helper: unpack write fd from pipe_create result (high 16 bits)
def pipe_get_write_fd(pfd: int32) -> int32:
    return (pfd >> 16) & 65535  # 0xFFFF

# Helper: close both ends of a pipe
def pipe_close_both(pfd: int32):
    if pfd >= 0:
        read_fd: int32 = pipe_get_read_fd(pfd)
        write_fd: int32 = pipe_get_write_fd(pfd)
        pipe_close(read_fd)
        pipe_close(write_fd)

# ============================================================================
# Pipe Creation Tests
# ============================================================================

def test_pipe_create():
    """Test basic pipe creation."""
    print_section("Pipe Creation")

    # Create a pipe
    fd: int32 = pipe_create()
    assert_gte(fd, 0, "pipe_create returns valid fd")

    # Clean up
    if fd >= 0:
        pipe_close_both(fd)

def test_create_multiple_pipes():
    """Test creating multiple pipes."""
    fds: Array[5, int32]
    i: int32 = 0

    # Create 5 pipes
    while i < 5:
        fds[i] = pipe_create()
        i = i + 1

    # Count successful creations
    created: int32 = 0
    i = 0
    while i < 5:
        if fds[i] >= 0:
            created = created + 1
        i = i + 1

    assert_eq(created, 5, "create 5 pipes")

    # Clean up
    i = 0
    while i < 5:
        if fds[i] >= 0:
            pipe_close_both(fds[i])
        i = i + 1

def test_pipe_limit():
    """Test pipe table limit."""
    fds: Array[12, int32]
    i: int32 = 0

    # Try to create more than MAX_PIPES
    while i < MAX_PIPES + 2:
        fds[i] = pipe_create()
        i = i + 1

    created: int32 = 0
    i = 0
    while i < MAX_PIPES + 2:
        if fds[i] >= 0:
            created = created + 1
        i = i + 1

    assert_lt(created, MAX_PIPES + 1, "pipe limit enforced")

    # Clean up
    i = 0
    while i < MAX_PIPES + 2:
        if fds[i] >= 0:
            pipe_close_both(fds[i])
        i = i + 1

# ============================================================================
# Pipe Read/Write Tests
# ============================================================================

def test_pipe_write_read():
    """Test basic pipe write and read."""
    print_section("Pipe I/O")

    pfd: int32 = pipe_create()
    if pfd < 0:
        test_fail("create pipe for I/O test")
        return

    read_fd: int32 = pipe_get_read_fd(pfd)
    write_fd: int32 = pipe_get_write_fd(pfd)

    # Write some data
    write_buf: Array[16, uint8]
    write_buf[0] = 'H'
    write_buf[1] = 'e'
    write_buf[2] = 'l'
    write_buf[3] = 'l'
    write_buf[4] = 'o'

    written: int32 = pipe_write(write_fd, &write_buf[0], 5)
    assert_eq(written, 5, "write 5 bytes")

    # Read it back
    read_buf: Array[16, uint8]
    read_len: int32 = pipe_read(read_fd, &read_buf[0], 16)
    assert_eq(read_len, 5, "read returns 5 bytes")

    # Verify content
    matched: bool = (read_buf[0] == 'H' and read_buf[1] == 'e' and
                   read_buf[2] == 'l' and read_buf[3] == 'l' and
                   read_buf[4] == 'o')
    assert_true(matched, "read content matches written")

    pipe_close_both(pfd)

def test_pipe_multiple_writes():
    """Test multiple writes to a pipe."""
    pfd: int32 = pipe_create()
    if pfd < 0:
        test_fail("create pipe for multi-write")
        return

    read_fd: int32 = pipe_get_read_fd(pfd)
    write_fd: int32 = pipe_get_write_fd(pfd)

    buf: Array[8, uint8]

    # Write "AB"
    buf[0] = 'A'
    buf[1] = 'B'
    written1: int32 = pipe_write(write_fd, &buf[0], 2)

    # Write "CD"
    buf[0] = 'C'
    buf[1] = 'D'
    written2: int32 = pipe_write(write_fd, &buf[0], 2)

    assert_eq(written1 + written2, 4, "total bytes written")

    # Read all
    read_buf: Array[16, uint8]
    total_read: int32 = pipe_read(read_fd, &read_buf[0], 16)
    assert_eq(total_read, 4, "read all written bytes")

    # Should be ABCD
    matched: bool = (read_buf[0] == 'A' and read_buf[1] == 'B' and
                   read_buf[2] == 'C' and read_buf[3] == 'D')
    assert_true(matched, "FIFO order preserved")

    pipe_close_both(pfd)

def test_pipe_buffer_full():
    """Test pipe behavior when buffer fills up."""
    pfd: int32 = pipe_create()
    if pfd < 0:
        test_fail("create pipe for buffer test")
        return

    write_fd: int32 = pipe_get_write_fd(pfd)

    # Fill buffer with data
    data: Array[64, uint8]
    i: int32 = 0
    while i < 64:
        data[i] = 'X'
        i = i + 1

    total_written: int32 = 0
    attempts: int32 = 0

    # Keep writing until buffer is full
    while attempts < 20:
        written: int32 = pipe_write(write_fd, &data[0], 64)
        if written <= 0:
            break
        total_written = total_written + written
        attempts = attempts + 1

    assert_gt(total_written, 0, "wrote some data")
    assert_lt(attempts, 20, "buffer fills up eventually")

    print_str("  (wrote ")
    print_int(total_written)
    print_str(" bytes before full)")
    print_newline()

    pipe_close_both(pfd)

def test_pipe_empty_read():
    """Test reading from empty pipe."""
    pfd: int32 = pipe_create()
    if pfd < 0:
        test_fail("create pipe for empty read")
        return

    read_fd: int32 = pipe_get_read_fd(pfd)

    buf: Array[16, uint8]
    # Read from empty pipe - should return 0 or block
    # In non-blocking mode, should return 0
    read_len: int32 = pipe_read(read_fd, &buf[0], 16)
    assert_eq(read_len, 0, "empty pipe read returns 0")

    pipe_close_both(pfd)

# ============================================================================
# Message Queue Tests
# ============================================================================

def test_mq_create():
    """Test message queue creation."""
    print_section("Message Queues")

    mqid: int32 = mq_create()
    assert_gte(mqid, 0, "mq_create returns valid id")

    if mqid >= 0:
        mq_close(mqid)

def test_mq_limit():
    """Test message queue limit."""
    mqs: Array[10, int32]
    i: int32 = 0

    while i < MAX_MESSAGE_QUEUES + 2:
        mqs[i] = mq_create()
        i = i + 1

    created: int32 = 0
    i = 0
    while i < MAX_MESSAGE_QUEUES + 2:
        if mqs[i] >= 0:
            created = created + 1
        i = i + 1

    assert_lt(created, MAX_MESSAGE_QUEUES + 1, "mq limit enforced")

    # Clean up
    i = 0
    while i < MAX_MESSAGE_QUEUES + 2:
        if mqs[i] >= 0:
            mq_close(mqs[i])
        i = i + 1

def test_mq_send_receive():
    """Test sending and receiving messages."""
    print_section("Message Queue I/O")

    mqid: int32 = mq_create()
    if mqid < 0:
        test_fail("create mq for send/recv")
        return

    # Send a message
    msg: Array[16, uint8]
    msg[0] = 'T'
    msg[1] = 'E'
    msg[2] = 'S'
    msg[3] = 'T'

    success: bool = mq_send(mqid, &msg[0], 4)
    assert_true(success, "mq_send succeeds")

    # Receive the message
    recv_buf: Array[64, uint8]
    recv_len: int32 = mq_receive(mqid, &recv_buf[0], 64)
    assert_eq(recv_len, 4, "mq_receive returns correct length")

    # Verify content
    matched: bool = (recv_buf[0] == 'T' and recv_buf[1] == 'E' and
                   recv_buf[2] == 'S' and recv_buf[3] == 'T')
    assert_true(matched, "message content matches")

    mq_close(mqid)

def test_mq_multiple_messages():
    """Test sending multiple messages."""
    mqid: int32 = mq_create()
    if mqid < 0:
        test_fail("create mq for multi-msg")
        return

    msg1: Array[4, uint8]
    msg1[0] = 'O'
    msg1[1] = 'N'
    msg1[2] = 'E'
    msg1[3] = '\0'

    msg2: Array[4, uint8]
    msg2[0] = 'T'
    msg2[1] = 'W'
    msg2[2] = 'O'
    msg2[3] = '\0'

    # Send two messages
    ok1: bool = mq_send(mqid, &msg1[0], 4)
    ok2: bool = mq_send(mqid, &msg2[0], 4)
    assert_true(ok1 and ok2, "send 2 messages")

    # Receive first - should be "ONE"
    buf: Array[64, uint8]
    len1: int32 = mq_receive(mqid, &buf[0], 64)
    first_ok: bool = (len1 == 4 and buf[0] == 'O' and buf[1] == 'N')
    assert_true(first_ok, "first message is ONE")

    # Receive second - should be "TWO"
    len2: int32 = mq_receive(mqid, &buf[0], 64)
    second_ok: bool = (len2 == 4 and buf[0] == 'T' and buf[1] == 'W')
    assert_true(second_ok, "second message is TWO")

    mq_close(mqid)

def test_mq_full():
    """Test message queue full behavior."""
    mqid: int32 = mq_create()
    if mqid < 0:
        test_fail("create mq for full test")
        return

    msg: Array[32, uint8]
    i: int32 = 0
    while i < 32:
        msg[i] = 'M'
        i = i + 1

    # Send until full
    sent: int32 = 0
    while sent < 20:
        success: bool = mq_send(mqid, &msg[0], 32)
        if not success:
            break
        sent = sent + 1

    assert_gt(sent, 0, "sent some messages")
    assert_lt(sent, 20, "queue fills up")

    print_str("  (sent ")
    print_int(sent)
    print_str(" messages before full)")
    print_newline()

    mq_close(mqid)

# ============================================================================
# Intuitive API Tests
# ============================================================================

def test_intuitive_pipe_api():
    """Test that pipe API is intuitive."""
    print_section("Intuitive IPC API")

    # pipe_create should return usable fd (pfd read|write)
    pfd: int32 = pipe_create()
    if pfd >= 0:
        test_pass("pipe_create returns usable fd")
    else:
        test_fail("pipe_create should return >= 0")
        return

    read_fd: int32 = pipe_get_read_fd(pfd)
    write_fd: int32 = pipe_get_write_fd(pfd)

    # write returns number of bytes written
    buf: Array[4, uint8]
    buf[0] = 'X'
    written: int32 = pipe_write(write_fd, &buf[0], 1)
    if written == 1:
        test_pass("pipe_write returns bytes written")
    else:
        test_fail("pipe_write should return byte count")

    # read returns number of bytes read
    read_len: int32 = pipe_read(read_fd, &buf[0], 4)
    if read_len == 1:
        test_pass("pipe_read returns bytes read")
    else:
        test_fail("pipe_read should return byte count")

    # close should work without errors
    pipe_close_both(pfd)
    test_pass("pipe_close works")

def test_intuitive_mq_api():
    """Test that message queue API is intuitive."""
    # mq_create returns usable id
    mqid: int32 = mq_create()
    if mqid >= 0:
        test_pass("mq_create returns usable id")
    else:
        test_fail("mq_create should return >= 0")
        return

    # mq_send returns bool for success
    buf: Array[4, uint8]
    buf[0] = 'Y'
    success: bool = mq_send(mqid, &buf[0], 1)
    if success:
        test_pass("mq_send returns true on success")
    else:
        test_fail("mq_send should return true")

    # mq_receive returns message length
    recv_len: int32 = mq_receive(mqid, &buf[0], 4)
    if recv_len == 1:
        test_pass("mq_receive returns msg length")
    else:
        test_fail("mq_receive should return length")

    mq_close(mqid)
    test_pass("mq_close works")

# ============================================================================
# Main
# ============================================================================

def test_ipc_main() -> int32:
    print_str("\n=== Pynux IPC Tests ===\n")

    test_pipe_create()
    test_create_multiple_pipes()
    test_pipe_limit()

    test_pipe_write_read()
    test_pipe_multiple_writes()
    test_pipe_buffer_full()
    test_pipe_empty_read()

    test_mq_create()
    test_mq_limit()
    test_mq_send_receive()
    test_mq_multiple_messages()
    test_mq_full()

    test_intuitive_pipe_api()
    test_intuitive_mq_api()

    return print_results()
