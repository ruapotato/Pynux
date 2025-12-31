# Data Logger Example
#
# Logs sensor readings to RAM filesystem with timestamps.
# Demonstrates: sensors, ramfs, timer, profiling

from lib.io import console_puts, console_print_int
from lib.sensors import temp_read, light_read, humid_read, sensors_init_all, sensors_seed
from lib.string import strcpy, strcat, itoa_simple
from kernel.timer import timer_get_ticks
from kernel.ramfs import ramfs_create, ramfs_append, ramfs_read, ramfs_size

# Configuration
LOG_FILE: Ptr[char] = "/tmp/sensor_log.txt"
MAX_ENTRIES: int32 = 100
log_count: int32 = 0
last_log_time: int32 = 0
LOG_INTERVAL: int32 = 5000  # Log every 5 seconds

# Buffer for building log entries
log_buffer: Array[128, char]

def itoa_simple(n: int32, buf: Ptr[char]) -> int32:
    """Convert integer to string, return length."""
    if n == 0:
        buf[0] = '0'
        buf[1] = '\0'
        return 1

    is_neg: bool = False
    if n < 0:
        is_neg = True
        n = -n

    # Build digits in reverse
    digits: Array[12, char]
    i: int32 = 0
    while n > 0:
        digits[i] = cast[char](48 + (n % 10))
        n = n / 10
        i = i + 1

    # Write to buffer
    pos: int32 = 0
    if is_neg:
        buf[pos] = '-'
        pos = pos + 1

    while i > 0:
        i = i - 1
        buf[pos] = digits[i]
        pos = pos + 1

    buf[pos] = '\0'
    return pos

def datalogger_init():
    """Initialize the data logger."""
    global log_count

    console_puts("DataLogger: Initializing...\n")

    # Initialize sensors
    sensors_seed(12345)
    sensors_init_all()

    # Create log file
    ramfs_create(LOG_FILE, False)

    # Write header
    ramfs_append(LOG_FILE, "# Pynux Sensor Log\n")
    ramfs_append(LOG_FILE, "# Time(ms), Temp(cC), Light, Humidity(0.1%)\n")

    log_count = 0
    console_puts("  Log file: ")
    console_puts(LOG_FILE)
    console_puts("\n")
    console_puts("DataLogger: Ready\n\n")

def datalogger_log():
    """Log current sensor readings."""
    global log_count, last_log_time

    now: int32 = timer_get_ticks()
    if now - last_log_time < LOG_INTERVAL:
        return

    if log_count >= MAX_ENTRIES:
        return

    last_log_time = now

    # Read sensors
    temp: int32 = temp_read()
    light: int32 = light_read()
    humid: int32 = humid_read()

    # Build log entry: "time,temp,light,humid\n"
    pos: int32 = 0

    # Time
    pos = pos + itoa_simple(now, &log_buffer[pos])
    log_buffer[pos] = ','
    pos = pos + 1

    # Temperature
    pos = pos + itoa_simple(temp, &log_buffer[pos])
    log_buffer[pos] = ','
    pos = pos + 1

    # Light
    pos = pos + itoa_simple(light, &log_buffer[pos])
    log_buffer[pos] = ','
    pos = pos + 1

    # Humidity
    pos = pos + itoa_simple(humid, &log_buffer[pos])
    log_buffer[pos] = '\n'
    pos = pos + 1
    log_buffer[pos] = '\0'

    # Append to file
    ramfs_append(LOG_FILE, &log_buffer[0])

    log_count = log_count + 1

    # Status
    console_puts("[")
    console_print_int(log_count)
    console_puts("] T=")
    console_print_int(temp / 100)
    console_puts(".")
    console_print_int(temp % 100)
    console_puts("C L=")
    console_print_int(light)
    console_puts(" H=")
    console_print_int(humid / 10)
    console_puts("%\n")

def datalogger_dump():
    """Display the log file contents."""
    console_puts("\n=== Log File Contents ===\n")

    size: int32 = ramfs_size(LOG_FILE)
    console_puts("Size: ")
    console_print_int(size)
    console_puts(" bytes, ")
    console_print_int(log_count)
    console_puts(" entries\n\n")

    # Read and print (limit to 512 bytes)
    buf: Array[512, char]
    bytes_read: int32 = ramfs_read(LOG_FILE, cast[Ptr[uint8]](&buf[0]), 511)
    if bytes_read > 0:
        buf[bytes_read] = '\0'
        console_puts(&buf[0])

    console_puts("\n=== End of Log ===\n")

def datalogger_main(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    """Standalone demo mode."""
    datalogger_init()

    console_puts("=== Data Logger Demo ===\n")
    console_puts("Logging 5 entries...\n\n")

    # Force immediate logging by setting interval to 0
    i: int32 = 0
    while i < 5:
        # Force log by resetting timer
        last_log_time = timer_get_ticks() - LOG_INTERVAL - 1
        datalogger_log()
        i = i + 1

    # Show logged data
    datalogger_dump()

    console_puts("\nDemo complete.\n")
    return 0
