# Pynux Integration Tests
#
# Tests that verify different OS components work well together.

from lib.io import print_str, print_int, print_newline
from lib.string import strcmp, strlen, strcpy, atoi
from lib.memory import alloc, free, memcpy, memset, heap_init
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, assert_not_null,
                                   test_pass, test_fail)
from kernel.process import (proc_create, signal_send, proc_state,
                             pipe_create, pipe_write, pipe_read, pipe_close,
                             mq_create, mq_send, mq_receive, mq_close,
                             SIGTERM, PROC_STATE_READY)
from kernel.ramfs import (ramfs_init, ramfs_create, ramfs_write, ramfs_read,
                           ramfs_delete, ramfs_exists, ramfs_size, ramfs_append)
from kernel.devfs import (devfs_init, devfs_register, devfs_read, devfs_write,
                           devfs_find_by_name, DEV_GPIO, DEV_ADC, DEV_PWM)
from kernel.timer import timer_init, timer_tick, timer_get_ticks

# ============================================================================
# Memory + Process Integration
# ============================================================================

def test_process_with_memory():
    """Test that processes can use dynamic memory."""
    print_section("Process + Memory")

    # Create a process
    pid: int32 = proc_create("mem_proc")
    assert_gte(pid, 0, "create process for memory test")

    # Allocate memory (simulating process memory use)
    buf: Ptr[uint8] = alloc(256)
    assert_not_null(cast[Ptr[void]](buf), "process can allocate memory")

    # Use the memory
    memset(buf, 0xAA, 256)
    if buf[0] == 0xAA and buf[255] == 0xAA:
        test_pass("process can use allocated memory")
    else:
        test_fail("memory should be usable")

    # Clean up
    free(buf)
    signal_send(pid, SIGTERM)

def test_multiple_processes_memory():
    """Test multiple processes with independent memory."""
    pids: Array[3, int32]
    bufs: Array[3, Ptr[uint8]]
    i: int32 = 0

    # Create processes and allocate memory for each
    while i < 3:
        pids[i] = proc_create("multi_mem")
        bufs[i] = alloc(64)

        # Each writes different pattern
        if bufs[i] != Ptr[uint8](0):
            memset(bufs[i], cast[uint8](i + 1), 64)
        i = i + 1

    # Verify each has its own data
    all_correct: bool = True
    i = 0
    while i < 3:
        if bufs[i] != Ptr[uint8](0):
            expected: uint8 = cast[uint8](i + 1)
            if bufs[i][0] != expected or bufs[i][63] != expected:
                all_correct = False
        i = i + 1

    assert_true(all_correct, "processes have independent memory")

    # Clean up
    i = 0
    while i < 3:
        if bufs[i] != Ptr[uint8](0):
            free(bufs[i])
        if pids[i] >= 0:
            signal_send(pids[i], SIGTERM)
        i = i + 1

# ============================================================================
# IPC + Memory Integration
# ============================================================================

def test_pipe_with_dynamic_buffer():
    """Test pipes using dynamically allocated buffers."""
    print_section("IPC + Memory")

    fd: int32 = pipe_create()
    assert_gte(fd, 0, "create pipe")

    # Allocate send buffer
    send_buf: Ptr[uint8] = alloc(32)
    assert_not_null(cast[Ptr[void]](send_buf), "allocate send buffer")

    # Fill with data
    i: int32 = 0
    while i < 32:
        send_buf[i] = cast[uint8](i)
        i = i + 1

    # Write to pipe
    written: int32 = pipe_write(fd, send_buf, 32)
    assert_eq(written, 32, "write dynamic buffer to pipe")

    # Allocate receive buffer
    recv_buf: Ptr[uint8] = alloc(32)
    assert_not_null(cast[Ptr[void]](recv_buf), "allocate recv buffer")

    # Read from pipe
    read_len: int32 = pipe_read(fd, recv_buf, 32)
    assert_eq(read_len, 32, "read into dynamic buffer")

    # Verify data
    matched: bool = True
    i = 0
    while i < 32:
        if recv_buf[i] != cast[uint8](i):
            matched = False
        i = i + 1

    assert_true(matched, "dynamic buffer data matches")

    # Clean up
    free(send_buf)
    free(recv_buf)
    pipe_close(fd)

def test_mq_with_struct():
    """Test message queues with structured data."""
    mqid: int32 = mq_create()
    assert_gte(mqid, 0, "create mq for struct")

    # Create a "message struct" in memory
    # Format: [type:4][payload:28]
    msg: Ptr[uint8] = alloc(32)
    assert_not_null(cast[Ptr[void]](msg), "allocate message")

    # Set type = 1
    msg_int: Ptr[int32] = cast[Ptr[int32]](msg)
    msg_int[0] = 1

    # Set payload
    msg[4] = 'D'
    msg[5] = 'A'
    msg[6] = 'T'
    msg[7] = 'A'

    # Send
    success: bool = mq_send(mqid, msg, 32)
    assert_true(success, "send struct message")

    # Receive
    recv: Ptr[uint8] = alloc(32)
    recv_len: int32 = mq_receive(mqid, recv, 32)
    assert_eq(recv_len, 32, "receive struct message")

    # Verify
    recv_int: Ptr[int32] = cast[Ptr[int32]](recv)
    type_ok: bool = (recv_int[0] == 1)
    data_ok: bool = (recv[4] == 'D' and recv[5] == 'A')
    assert_true(type_ok and data_ok, "struct data preserved")

    free(msg)
    free(recv)
    mq_close(mqid)

# ============================================================================
# Filesystem + Memory Integration
# ============================================================================

def test_file_with_dynamic_content():
    """Test file operations with dynamic content."""
    print_section("Filesystem + Memory")

    ramfs_create("/dyn_content.txt", False)

    # Create dynamic content
    content: Ptr[char] = cast[Ptr[char]](alloc(64))
    assert_not_null(cast[Ptr[void]](content), "allocate content")

    strcpy(content, "Dynamic content in file!")

    # Write to file
    result: int32 = ramfs_write("/dyn_content.txt", content)
    assert_gte(result, 0, "write dynamic content")

    # Verify size
    size: int32 = ramfs_size("/dyn_content.txt")
    expected_len: int32 = strlen(content)
    assert_eq(size, expected_len, "file size matches content")

    # Read back
    read_buf: Ptr[uint8] = alloc(64)
    read_len: int32 = ramfs_read("/dyn_content.txt", read_buf, 64)
    assert_eq(read_len, expected_len, "read back full content")

    # Verify content
    matched: bool = (read_buf[0] == 'D' and read_buf[1] == 'y')
    assert_true(matched, "content matches")

    free(content)
    free(read_buf)
    ramfs_delete("/dyn_content.txt")

def test_file_log_simulation():
    """Simulate a log file with multiple writes."""
    ramfs_create("/log.txt", False)

    # Write multiple log entries
    ramfs_write("/log.txt", "Log entry 1\n")

    ramfs_append("/log.txt", "Log entry 2\n")
    ramfs_append("/log.txt", "Log entry 3\n")

    # Check total size
    size: int32 = ramfs_size("/log.txt")
    # "Log entry N\n" is 12 bytes each, 3 entries = 36 bytes
    assert_eq(size, 36, "log file correct size")

    # Read and verify
    buf: Array[64, uint8]
    read_len: int32 = ramfs_read("/log.txt", &buf[0], 64)
    assert_eq(read_len, 36, "read full log")

    ramfs_delete("/log.txt")
    test_pass("log simulation complete")

# ============================================================================
# Device + Memory Integration
# ============================================================================

def test_device_data_processing():
    """Test reading device and processing data."""
    print_section("Device + Memory")

    # Register ADC
    idx: int32 = devfs_register(DEV_ADC, 7, 26, "int_adc")
    assert_gte(idx, 0, "register ADC")

    # Allocate buffer for samples
    samples: Ptr[int32] = cast[Ptr[int32]](alloc(40))  # 10 samples
    assert_not_null(cast[Ptr[void]](samples), "allocate samples")

    # Take 10 readings
    i: int32 = 0
    while i < 10:
        value: Ptr[char] = devfs_read(idx)
        samples[i] = atoi(value)
        i = i + 1

    # Calculate average
    total: int32 = 0
    i = 0
    while i < 10:
        total = total + samples[i]
        i = i + 1

    avg: int32 = total / 10

    # Average should be in valid ADC range
    if avg >= 0 and avg <= 4095:
        test_pass("device data processing works")
    else:
        test_fail("average out of range")

    print_str("  (average: ")
    print_int(avg)
    print_str(")")
    print_newline()

    free(cast[Ptr[uint8]](samples))

def test_gpio_state_file():
    """Test saving GPIO state to file."""
    # Register GPIO
    gpio_idx: int32 = devfs_register(DEV_GPIO, 9, 9, "state_gpio")
    ramfs_create("/gpio_state.txt", False)

    # Set GPIO
    devfs_write(gpio_idx, "1")

    # Read GPIO value
    value: Ptr[char] = devfs_read(gpio_idx)

    # Save to file
    ramfs_write("/gpio_state.txt", value)

    # Verify saved
    buf: Array[8, uint8]
    ramfs_read("/gpio_state.txt", &buf[0], 8)

    if buf[0] == '1' or buf[0] == '0':
        test_pass("GPIO state saved to file")
    else:
        test_fail("GPIO state should be in file")

    ramfs_delete("/gpio_state.txt")

# ============================================================================
# Timer + Process Integration
# ============================================================================

def test_timed_process_operation():
    """Test timing a process operation."""
    print_section("Timer + Process")

    start: int32 = timer_get_ticks()

    # Do some work (create/cleanup processes)
    i: int32 = 0
    while i < 5:
        pid: int32 = proc_create("timed_proc")
        if pid >= 0:
            signal_send(pid, SIGTERM)
        timer_tick()  # Simulate time passing
        i = i + 1

    end: int32 = timer_get_ticks()
    elapsed: int32 = end - start

    assert_gte(elapsed, 5, "timing captured")

    print_str("  (elapsed: ")
    print_int(elapsed)
    print_str(" ticks)")
    print_newline()

# ============================================================================
# Full System Integration
# ============================================================================

def test_full_system_workflow():
    """Test a complete system workflow."""
    print_section("Full System Workflow")

    # 1. Create a process
    pid: int32 = proc_create("workflow_proc")
    assert_gte(pid, 0, "1. Create process")

    # 2. Allocate working memory
    work_buf: Ptr[uint8] = alloc(128)
    assert_not_null(cast[Ptr[void]](work_buf), "2. Allocate memory")

    # 3. Read from device
    adc_idx: int32 = devfs_register(DEV_ADC, 8, 27, "wf_adc")
    value: Ptr[char] = devfs_read(adc_idx)
    assert_not_null(cast[Ptr[void]](value), "3. Read device")

    # 4. Copy to work buffer
    i: int32 = 0
    while value[i] != '\0' and i < 127:
        work_buf[i] = cast[uint8](value[i])
        i = i + 1
    work_buf[i] = 0
    test_pass("4. Process data")

    # 5. Save to file
    ramfs_create("/workflow.txt", False)
    ramfs_write("/workflow.txt", cast[Ptr[char]](work_buf))
    file_ok: bool = ramfs_exists("/workflow.txt")
    assert_true(file_ok, "5. Save to file")

    # 6. Create pipe for IPC
    pipe_fd: int32 = pipe_create()
    assert_gte(pipe_fd, 0, "6. Create pipe")

    # 7. Send data through pipe
    pipe_write(pipe_fd, work_buf, i)
    test_pass("7. Send via pipe")

    # 8. Record timing
    start: int32 = timer_get_ticks()
    timer_tick()
    timer_tick()
    end: int32 = timer_get_ticks()
    assert_gt(end, start, "8. Timing works")

    # Clean up
    pipe_close(pipe_fd)
    ramfs_delete("/workflow.txt")
    free(work_buf)
    signal_send(pid, SIGTERM)

    test_pass("Full workflow complete!")

# ============================================================================
# Error Handling Integration
# ============================================================================

def test_error_recovery():
    """Test system recovers from errors gracefully."""
    print_section("Error Recovery")

    # Try invalid operations - should not crash
    ramfs_read("/nonexistent", cast[Ptr[uint8]](0), 0)
    test_pass("invalid file read doesn't crash")

    devfs_read(-1)
    test_pass("invalid device read doesn't crash")

    pipe_close(-1)
    test_pass("invalid pipe close doesn't crash")

    signal_send(-1, SIGTERM)
    test_pass("invalid signal send doesn't crash")

    free(Ptr[uint8](0))
    test_pass("free(null) doesn't crash")

    # System should still work after errors
    ptr: Ptr[uint8] = alloc(16)
    assert_not_null(cast[Ptr[void]](ptr), "system works after errors")
    free(ptr)

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    print_str("\n=== Pynux Integration Tests ===\n")

    # Initialize all subsystems
    heap_init()
    ramfs_init()
    devfs_init()
    timer_init()

    test_process_with_memory()
    test_multiple_processes_memory()

    test_pipe_with_dynamic_buffer()
    test_mq_with_struct()

    test_file_with_dynamic_content()
    test_file_log_simulation()

    test_device_data_processing()
    test_gpio_state_file()

    test_timed_process_operation()

    test_full_system_workflow()

    test_error_recovery()

    return print_results()
