# Inter-Process Communication Demo
#
# Demonstrates pipes and message queues for communication
# between producer/consumer patterns.

from lib.io import console_puts, console_print_int
from kernel.process import pipe_create, pipe_write, pipe_read, pipe_close
from kernel.process import mq_create, mq_send, mq_receive, mq_close
from lib.string import strlen, strcpy
from kernel.timer import timer_get_ticks

# ============================================================================
# Pipe-based streaming example
# ============================================================================

def demo_pipe_stream():
    """Demonstrate pipe for streaming data."""
    console_puts("\n=== Pipe Streaming Demo ===\n\n")

    # Create a pipe
    fd: int32 = pipe_create()
    if fd < 0:
        console_puts("ERROR: Failed to create pipe\n")
        return

    console_puts("Created pipe fd=")
    console_print_int(fd)
    console_puts("\n\n")

    # Simulate producer writing data
    console_puts("Producer writing data...\n")

    data1: Array[16, uint8]
    data1[0] = 'H'
    data1[1] = 'e'
    data1[2] = 'l'
    data1[3] = 'l'
    data1[4] = 'o'
    data1[5] = '\0'

    written: int32 = pipe_write(fd, &data1[0], 5)
    console_puts("  Wrote ")
    console_print_int(written)
    console_puts(" bytes: 'Hello'\n")

    data2: Array[16, uint8]
    data2[0] = 'W'
    data2[1] = 'o'
    data2[2] = 'r'
    data2[3] = 'l'
    data2[4] = 'd'
    data2[5] = '\0'

    written = pipe_write(fd, &data2[0], 5)
    console_puts("  Wrote ")
    console_print_int(written)
    console_puts(" bytes: 'World'\n")

    # Simulate consumer reading data
    console_puts("\nConsumer reading data...\n")

    buf: Array[32, uint8]
    bytes_read: int32 = pipe_read(fd, &buf[0], 10)

    console_puts("  Read ")
    console_print_int(bytes_read)
    console_puts(" bytes: '")

    i: int32 = 0
    while i < bytes_read:
        c: char = cast[char](buf[i])
        console_puts(&c)
        i = i + 1
    console_puts("'\n")

    pipe_close(fd)
    console_puts("\nPipe closed.\n")

# ============================================================================
# Message queue example
# ============================================================================

# Message types
MSG_SENSOR_DATA: int32 = 1
MSG_COMMAND: int32 = 2
MSG_STATUS: int32 = 3

def demo_message_queue():
    """Demonstrate message queues for structured communication."""
    console_puts("\n=== Message Queue Demo ===\n\n")

    # Create a message queue
    mqid: int32 = mq_create()
    if mqid < 0:
        console_puts("ERROR: Failed to create message queue\n")
        return

    console_puts("Created message queue id=")
    console_print_int(mqid)
    console_puts("\n\n")

    # Send sensor data message
    console_puts("Sending messages...\n")

    msg1: Array[16, uint8]
    msg1[0] = MSG_SENSOR_DATA
    msg1[1] = 0   # Sensor ID
    msg1[2] = 25  # Value high byte
    msg1[3] = 100 # Value low byte (25 * 256 + 100 = 6500 = 65.00 degrees)

    result: bool = mq_send(mqid, &msg1[0], 4)
    console_puts("  Sent SENSOR_DATA: ")
    if result:
        console_puts("OK\n")
    else:
        console_puts("FAIL\n")

    # Send command message
    msg2: Array[16, uint8]
    msg2[0] = MSG_COMMAND
    msg2[1] = 1   # Command: start
    msg2[2] = 0
    msg2[3] = 0

    result = mq_send(mqid, &msg2[0], 4)
    console_puts("  Sent COMMAND: ")
    if result:
        console_puts("OK\n")
    else:
        console_puts("FAIL\n")

    # Send status message
    msg3: Array[16, uint8]
    msg3[0] = MSG_STATUS
    msg3[1] = 0   # Status: running
    msg3[2] = 0
    msg3[3] = 0

    result = mq_send(mqid, &msg3[0], 4)
    console_puts("  Sent STATUS: ")
    if result:
        console_puts("OK\n")
    else:
        console_puts("FAIL\n")

    # Receive and process messages
    console_puts("\nReceiving messages...\n")

    recv_buf: Array[32, uint8]
    count: int32 = 0

    while count < 3:
        msg_len: int32 = mq_receive(mqid, &recv_buf[0], 32)
        if msg_len <= 0:
            break

        msg_type: int32 = cast[int32](recv_buf[0])

        console_puts("  Received: ")
        if msg_type == MSG_SENSOR_DATA:
            sensor_id: int32 = cast[int32](recv_buf[1])
            value: int32 = cast[int32](recv_buf[2]) * 256 + cast[int32](recv_buf[3])
            console_puts("SENSOR_DATA sensor=")
            console_print_int(sensor_id)
            console_puts(" value=")
            console_print_int(value)
        elif msg_type == MSG_COMMAND:
            cmd: int32 = cast[int32](recv_buf[1])
            console_puts("COMMAND cmd=")
            console_print_int(cmd)
        elif msg_type == MSG_STATUS:
            status: int32 = cast[int32](recv_buf[1])
            console_puts("STATUS status=")
            console_print_int(status)
        else:
            console_puts("UNKNOWN type=")
            console_print_int(msg_type)

        console_puts("\n")
        count = count + 1

    mq_close(mqid)
    console_puts("\nMessage queue closed.\n")

# ============================================================================
# Producer-Consumer pattern
# ============================================================================

def demo_producer_consumer():
    """Demonstrate producer-consumer with message queue."""
    console_puts("\n=== Producer-Consumer Pattern ===\n\n")

    mqid: int32 = mq_create()
    if mqid < 0:
        console_puts("ERROR: Failed to create queue\n")
        return

    # Producer: generate sensor readings
    console_puts("Producer: Generating readings...\n")

    i: int32 = 0
    msg: Array[8, uint8]
    while i < 5:
        # Simulate sensor reading
        reading: int32 = 2000 + i * 100  # 20.00, 21.00, etc.

        msg[0] = cast[uint8](i)                   # Sequence
        msg[1] = cast[uint8]((reading >> 8) & 0xFF)  # Value high
        msg[2] = cast[uint8](reading & 0xFF)         # Value low
        msg[3] = cast[uint8](timer_get_ticks() & 0xFF)  # Timestamp

        mq_send(mqid, &msg[0], 4)
        console_puts("  Produced #")
        console_print_int(i)
        console_puts(": value=")
        console_print_int(reading)
        console_puts("\n")

        i = i + 1

    # Consumer: process readings
    console_puts("\nConsumer: Processing readings...\n")

    recv_buf: Array[8, uint8]
    sum: int32 = 0
    count: int32 = 0

    while True:
        msg_len: int32 = mq_receive(mqid, &recv_buf[0], 8)
        if msg_len <= 0:
            break

        seq: int32 = cast[int32](recv_buf[0])
        value: int32 = (cast[int32](recv_buf[1]) << 8) | cast[int32](recv_buf[2])

        console_puts("  Consumed #")
        console_print_int(seq)
        console_puts(": value=")
        console_print_int(value)
        console_puts("\n")

        sum = sum + value
        count = count + 1

    if count > 0:
        avg: int32 = sum / count
        console_puts("\nAverage: ")
        console_print_int(avg / 100)
        console_puts(".")
        console_print_int(avg % 100)
        console_puts(" degrees\n")

    mq_close(mqid)

def ipc_demo_main(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    """Run all IPC demos."""
    console_puts("############################################\n")
    console_puts("#      IPC Communication Examples          #\n")
    console_puts("############################################\n")

    demo_pipe_stream()
    demo_message_queue()
    demo_producer_consumer()

    console_puts("\n=== All IPC Demos Complete ===\n")
    return 0
