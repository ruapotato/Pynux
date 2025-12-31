# Pynux Logging Library
#
# Structured logging system for ARM Cortex-M3.
# Provides log levels, circular buffer storage, timestamps,
# and optional persistent storage via ramfs.

from lib.io import print_str, print_int, print_newline, uart_putc
from lib.string import strlen, strcpy, strncpy, strcmp

# ============================================================================
# Log Levels
# ============================================================================

LOG_DEBUG: int32 = 0
LOG_INFO: int32 = 1
LOG_WARN: int32 = 2
LOG_ERROR: int32 = 3
LOG_FATAL: int32 = 4

# Level name strings
_level_names: Array[5, Array[8, char]]
_level_prefixes: Array[5, Array[12, char]]

def _init_level_names():
    """Initialize log level name arrays."""
    global _level_names, _level_prefixes

    # DEBUG
    _level_names[0][0] = 'D'
    _level_names[0][1] = 'E'
    _level_names[0][2] = 'B'
    _level_names[0][3] = 'U'
    _level_names[0][4] = 'G'
    _level_names[0][5] = '\0'

    _level_prefixes[0][0] = '['
    _level_prefixes[0][1] = 'D'
    _level_prefixes[0][2] = 'E'
    _level_prefixes[0][3] = 'B'
    _level_prefixes[0][4] = 'U'
    _level_prefixes[0][5] = 'G'
    _level_prefixes[0][6] = ']'
    _level_prefixes[0][7] = ' '
    _level_prefixes[0][8] = '\0'

    # INFO
    _level_names[1][0] = 'I'
    _level_names[1][1] = 'N'
    _level_names[1][2] = 'F'
    _level_names[1][3] = 'O'
    _level_names[1][4] = '\0'

    _level_prefixes[1][0] = '['
    _level_prefixes[1][1] = 'I'
    _level_prefixes[1][2] = 'N'
    _level_prefixes[1][3] = 'F'
    _level_prefixes[1][4] = 'O'
    _level_prefixes[1][5] = ']'
    _level_prefixes[1][6] = ' '
    _level_prefixes[1][7] = ' '
    _level_prefixes[1][8] = '\0'

    # WARN
    _level_names[2][0] = 'W'
    _level_names[2][1] = 'A'
    _level_names[2][2] = 'R'
    _level_names[2][3] = 'N'
    _level_names[2][4] = '\0'

    _level_prefixes[2][0] = '['
    _level_prefixes[2][1] = 'W'
    _level_prefixes[2][2] = 'A'
    _level_prefixes[2][3] = 'R'
    _level_prefixes[2][4] = 'N'
    _level_prefixes[2][5] = ']'
    _level_prefixes[2][6] = ' '
    _level_prefixes[2][7] = ' '
    _level_prefixes[2][8] = '\0'

    # ERROR
    _level_names[3][0] = 'E'
    _level_names[3][1] = 'R'
    _level_names[3][2] = 'R'
    _level_names[3][3] = 'O'
    _level_names[3][4] = 'R'
    _level_names[3][5] = '\0'

    _level_prefixes[3][0] = '['
    _level_prefixes[3][1] = 'E'
    _level_prefixes[3][2] = 'R'
    _level_prefixes[3][3] = 'R'
    _level_prefixes[3][4] = 'O'
    _level_prefixes[3][5] = 'R'
    _level_prefixes[3][6] = ']'
    _level_prefixes[3][7] = '\0'

    # FATAL
    _level_names[4][0] = 'F'
    _level_names[4][1] = 'A'
    _level_names[4][2] = 'T'
    _level_names[4][3] = 'A'
    _level_names[4][4] = 'L'
    _level_names[4][5] = '\0'

    _level_prefixes[4][0] = '['
    _level_prefixes[4][1] = 'F'
    _level_prefixes[4][2] = 'A'
    _level_prefixes[4][3] = 'T'
    _level_prefixes[4][4] = 'A'
    _level_prefixes[4][5] = 'L'
    _level_prefixes[4][6] = ']'
    _level_prefixes[4][7] = '\0'

# ============================================================================
# Log Entry Structure
# ============================================================================

# Each log entry: [timestamp:4][level:1][msg_len:1][message:N][\0]
# Fixed-size entry for circular buffer
LOG_ENTRY_MAX_MSG: int32 = 120
LOG_ENTRY_SIZE: int32 = 128  # 4 + 1 + 1 + 120 + 2 padding

# Maximum number of log entries in buffer
LOG_MAX_ENTRIES: int32 = 32

# ============================================================================
# Log Buffer State
# ============================================================================

# Circular buffer for log entries
_log_buffer: Array[4096, uint8]  # 32 * 128 = 4096 bytes

# Buffer indices
_log_head: int32 = 0      # Next write position
_log_tail: int32 = 0      # Oldest entry position
_log_count: int32 = 0     # Number of entries in buffer

# Logging configuration
_log_min_level: int32 = LOG_DEBUG   # Minimum level to record
_log_output_enabled: bool = True     # Output to console immediately
_log_initialized: bool = False

# Persistent log file path
_log_file_path: Array[64, char]
_log_file_enabled: bool = False

# Statistics
_log_total_count: int32 = 0
_log_dropped_count: int32 = 0

# ============================================================================
# Initialization
# ============================================================================

def log_init():
    """Initialize the logging system."""
    global _log_head, _log_tail, _log_count, _log_initialized
    global _log_total_count, _log_dropped_count
    global _log_min_level, _log_output_enabled, _log_file_enabled

    _init_level_names()

    state: int32 = critical_enter()

    _log_head = 0
    _log_tail = 0
    _log_count = 0
    _log_total_count = 0
    _log_dropped_count = 0
    _log_min_level = LOG_DEBUG
    _log_output_enabled = True
    _log_file_enabled = False
    _log_initialized = True

    # Clear buffer
    i: int32 = 0
    while i < 4096:
        _log_buffer[i] = 0
        i = i + 1

    critical_exit(state)

def log_deinit():
    """Deinitialize the logging system."""
    global _log_initialized

    # Flush to file if enabled
    if _log_file_enabled:
        log_flush_to_file()

    _log_initialized = False

# ============================================================================
# Configuration
# ============================================================================

def log_set_level(level: int32):
    """Set minimum log level to record.

    Args:
        level: LOG_DEBUG, LOG_INFO, LOG_WARN, LOG_ERROR, or LOG_FATAL
    """
    global _log_min_level

    if level < LOG_DEBUG:
        level = LOG_DEBUG
    if level > LOG_FATAL:
        level = LOG_FATAL

    _log_min_level = level

def log_get_level() -> int32:
    """Get current minimum log level.

    Returns:
        Current log level
    """
    return _log_min_level

def log_set_output(enabled: bool):
    """Enable/disable immediate console output.

    Args:
        enabled: True to output logs to console
    """
    global _log_output_enabled
    _log_output_enabled = enabled

def log_set_file(path: Ptr[char]):
    """Set file path for persistent logging.

    Args:
        path: Path to log file in ramfs (e.g., "/var/log")
    """
    global _log_file_enabled

    i: int32 = 0
    while path[i] != '\0' and i < 62:
        _log_file_path[i] = path[i]
        i = i + 1
    _log_file_path[i] = '\0'

    _log_file_enabled = True

def log_disable_file():
    """Disable file logging."""
    global _log_file_enabled
    _log_file_enabled = False

# ============================================================================
# Internal Helpers
# ============================================================================

def _log_entry_ptr(index: int32) -> Ptr[uint8]:
    """Get pointer to log entry at given index."""
    offset: int32 = (index % LOG_MAX_ENTRIES) * LOG_ENTRY_SIZE
    return &_log_buffer[offset]

def _format_timestamp(buf: Ptr[char], timestamp: int32) -> int32:
    """Format timestamp as seconds.milliseconds string.

    Args:
        buf: Buffer to write to (at least 12 bytes)
        timestamp: Timestamp in milliseconds

    Returns:
        Length of formatted string
    """
    secs: int32 = timestamp / 1000
    ms: int32 = timestamp % 1000

    # Format seconds
    pos: int32 = 0

    if secs == 0:
        buf[pos] = '0'
        pos = pos + 1
    else:
        # Build digits in reverse
        digits: Array[12, char]
        i: int32 = 0
        n: int32 = secs
        while n > 0:
            digits[i] = cast[char](48 + (n % 10))
            n = n / 10
            i = i + 1
        # Copy in correct order
        while i > 0:
            i = i - 1
            buf[pos] = digits[i]
            pos = pos + 1

    buf[pos] = '.'
    pos = pos + 1

    # Format milliseconds (always 3 digits)
    buf[pos] = cast[char](48 + (ms / 100))
    pos = pos + 1
    buf[pos] = cast[char](48 + ((ms / 10) % 10))
    pos = pos + 1
    buf[pos] = cast[char](48 + (ms % 10))
    pos = pos + 1

    buf[pos] = '\0'

    return pos

def _output_entry(entry: Ptr[uint8]):
    """Output a log entry to console."""
    # Extract fields
    timestamp: int32 = cast[int32](entry[0])
    timestamp = timestamp | (cast[int32](entry[1]) << 8)
    timestamp = timestamp | (cast[int32](entry[2]) << 16)
    timestamp = timestamp | (cast[int32](entry[3]) << 24)

    level: int32 = cast[int32](entry[4])
    msg_len: int32 = cast[int32](entry[5])
    msg: Ptr[char] = cast[Ptr[char]](&entry[6])

    # Format: [TIMESTAMP] [LEVEL] message
    ts_buf: Array[16, char]
    _format_timestamp(&ts_buf[0], timestamp)

    uart_putc('[')
    print_str(&ts_buf[0])
    uart_putc(']')
    uart_putc(' ')

    # Print level prefix
    if level >= 0 and level <= 4:
        print_str(&_level_prefixes[level][0])
    else:
        print_str("[???] ")

    # Print message
    i: int32 = 0
    while i < msg_len and msg[i] != '\0':
        uart_putc(msg[i])
        i = i + 1

    print_newline()

# ============================================================================
# Logging Functions
# ============================================================================

def log_write(level: int32, msg: Ptr[char]):
    """Write a log message.

    Args:
        level: Log level (LOG_DEBUG, LOG_INFO, etc.)
        msg: Message string
    """
    global _log_head, _log_tail, _log_count
    global _log_total_count, _log_dropped_count

    if not _log_initialized:
        return

    # Check minimum level
    if level < _log_min_level:
        return

    state: int32 = critical_enter()

    # Get timestamp
    timestamp: int32 = timer_get_ticks()

    # Get message length
    msg_len: int32 = strlen(msg)
    if msg_len > LOG_ENTRY_MAX_MSG:
        msg_len = LOG_ENTRY_MAX_MSG

    # Get entry pointer
    entry: Ptr[uint8] = _log_entry_ptr(_log_head)

    # Write timestamp (4 bytes, little-endian)
    entry[0] = cast[uint8](timestamp & 0xFF)
    entry[1] = cast[uint8]((timestamp >> 8) & 0xFF)
    entry[2] = cast[uint8]((timestamp >> 16) & 0xFF)
    entry[3] = cast[uint8]((timestamp >> 24) & 0xFF)

    # Write level
    entry[4] = cast[uint8](level)

    # Write message length
    entry[5] = cast[uint8](msg_len)

    # Write message
    i: int32 = 0
    while i < msg_len:
        entry[6 + i] = cast[uint8](msg[i])
        i = i + 1
    entry[6 + msg_len] = 0  # Null terminate

    # Update head
    _log_head = (_log_head + 1) % LOG_MAX_ENTRIES

    # Update count and tail if buffer is full
    if _log_count < LOG_MAX_ENTRIES:
        _log_count = _log_count + 1
    else:
        _log_tail = (_log_tail + 1) % LOG_MAX_ENTRIES
        _log_dropped_count = _log_dropped_count + 1

    _log_total_count = _log_total_count + 1

    critical_exit(state)

    # Output to console if enabled
    if _log_output_enabled:
        _output_entry(entry)

def log_debug(msg: Ptr[char]):
    """Log a debug message."""
    log_write(LOG_DEBUG, msg)

def log_info(msg: Ptr[char]):
    """Log an info message."""
    log_write(LOG_INFO, msg)

def log_warn(msg: Ptr[char]):
    """Log a warning message."""
    log_write(LOG_WARN, msg)

def log_error(msg: Ptr[char]):
    """Log an error message."""
    log_write(LOG_ERROR, msg)

def log_fatal(msg: Ptr[char]):
    """Log a fatal error message."""
    log_write(LOG_FATAL, msg)

# ============================================================================
# Log with Integer Argument
# ============================================================================

def log_write_int(level: int32, msg: Ptr[char], value: int32):
    """Write a log message with an integer value.

    Args:
        level: Log level
        msg: Message prefix
        value: Integer value to append
    """
    # Build message with value
    buf: Array[128, char]

    # Copy message
    i: int32 = 0
    while msg[i] != '\0' and i < 100:
        buf[i] = msg[i]
        i = i + 1

    # Add value
    if value == 0:
        buf[i] = '0'
        i = i + 1
    else:
        neg: bool = value < 0
        if neg:
            buf[i] = '-'
            i = i + 1
            value = -value

        # Build digits
        digits: Array[12, char]
        j: int32 = 0
        while value > 0:
            digits[j] = cast[char](48 + (value % 10))
            value = value / 10
            j = j + 1

        # Copy in reverse
        while j > 0:
            j = j - 1
            buf[i] = digits[j]
            i = i + 1

    buf[i] = '\0'

    log_write(level, &buf[0])

def log_debug_int(msg: Ptr[char], value: int32):
    """Log a debug message with integer value."""
    log_write_int(LOG_DEBUG, msg, value)

def log_info_int(msg: Ptr[char], value: int32):
    """Log an info message with integer value."""
    log_write_int(LOG_INFO, msg, value)

def log_warn_int(msg: Ptr[char], value: int32):
    """Log a warning message with integer value."""
    log_write_int(LOG_WARN, msg, value)

def log_error_int(msg: Ptr[char], value: int32):
    """Log an error message with integer value."""
    log_write_int(LOG_ERROR, msg, value)

# ============================================================================
# Buffer Operations
# ============================================================================

def log_clear():
    """Clear all log entries from buffer."""
    global _log_head, _log_tail, _log_count

    state: int32 = critical_enter()

    _log_head = 0
    _log_tail = 0
    _log_count = 0

    critical_exit(state)

def log_get_count() -> int32:
    """Get number of entries in buffer.

    Returns:
        Number of log entries
    """
    return _log_count

def log_get_total_count() -> int32:
    """Get total number of messages logged (including dropped).

    Returns:
        Total log count
    """
    return _log_total_count

def log_get_dropped_count() -> int32:
    """Get number of log entries dropped due to buffer overflow.

    Returns:
        Dropped entry count
    """
    return _log_dropped_count

def log_is_empty() -> bool:
    """Check if log buffer is empty.

    Returns:
        True if no entries
    """
    return _log_count == 0

def log_is_full() -> bool:
    """Check if log buffer is full.

    Returns:
        True if buffer is at capacity
    """
    return _log_count >= LOG_MAX_ENTRIES

# ============================================================================
# Dump and Filter
# ============================================================================

def log_dump():
    """Dump all log entries to console."""
    if _log_count == 0:
        print_str("Log buffer is empty\n")
        return

    print_str("=== Log Dump (")
    print_int(_log_count)
    print_str(" entries) ===\n")

    i: int32 = 0
    idx: int32 = _log_tail
    while i < _log_count:
        entry: Ptr[uint8] = _log_entry_ptr(idx)
        _output_entry(entry)
        idx = (idx + 1) % LOG_MAX_ENTRIES
        i = i + 1

    print_str("=== End Log Dump ===\n")

def log_dump_level(level: int32):
    """Dump log entries at or above specified level.

    Args:
        level: Minimum level to dump
    """
    if _log_count == 0:
        print_str("Log buffer is empty\n")
        return

    print_str("=== Log Dump (level >= ")
    if level >= 0 and level <= 4:
        print_str(&_level_names[level][0])
    else:
        print_int(level)
    print_str(") ===\n")

    count: int32 = 0
    i: int32 = 0
    idx: int32 = _log_tail
    while i < _log_count:
        entry: Ptr[uint8] = _log_entry_ptr(idx)
        entry_level: int32 = cast[int32](entry[4])

        if entry_level >= level:
            _output_entry(entry)
            count = count + 1

        idx = (idx + 1) % LOG_MAX_ENTRIES
        i = i + 1

    print_str("=== ")
    print_int(count)
    print_str(" entries ===\n")

def log_dump_last(n: int32):
    """Dump the last N log entries.

    Args:
        n: Number of entries to dump
    """
    if _log_count == 0:
        print_str("Log buffer is empty\n")
        return

    if n > _log_count:
        n = _log_count

    print_str("=== Last ")
    print_int(n)
    print_str(" log entries ===\n")

    # Start from (head - n) entries
    start_idx: int32 = (_log_head - n + LOG_MAX_ENTRIES) % LOG_MAX_ENTRIES

    i: int32 = 0
    idx: int32 = start_idx
    while i < n:
        entry: Ptr[uint8] = _log_entry_ptr(idx)
        _output_entry(entry)
        idx = (idx + 1) % LOG_MAX_ENTRIES
        i = i + 1

    print_str("=== End ===\n")

# ============================================================================
# Persistent Storage
# ============================================================================

def log_flush_to_file() -> int32:
    """Flush log buffer to ramfs file.

    Returns:
        Number of bytes written, or -1 on error
    """
    if not _log_file_enabled:
        return -1

    if _log_count == 0:
        return 0

    # Build log content as text
    buf: Array[2048, char]
    pos: int32 = 0

    i: int32 = 0
    idx: int32 = _log_tail
    while i < _log_count and pos < 1900:
        entry: Ptr[uint8] = _log_entry_ptr(idx)

        # Extract fields
        timestamp: int32 = cast[int32](entry[0])
        timestamp = timestamp | (cast[int32](entry[1]) << 8)
        timestamp = timestamp | (cast[int32](entry[2]) << 16)
        timestamp = timestamp | (cast[int32](entry[3]) << 24)

        level: int32 = cast[int32](entry[4])
        msg_len: int32 = cast[int32](entry[5])
        msg: Ptr[char] = cast[Ptr[char]](&entry[6])

        # Format timestamp
        ts_buf: Array[16, char]
        ts_len: int32 = _format_timestamp(&ts_buf[0], timestamp)

        # Write: [timestamp] [level] message\n
        buf[pos] = '['
        pos = pos + 1

        j: int32 = 0
        while j < ts_len:
            buf[pos] = ts_buf[j]
            pos = pos + 1
            j = j + 1

        buf[pos] = ']'
        pos = pos + 1
        buf[pos] = ' '
        pos = pos + 1

        # Level prefix
        if level >= 0 and level <= 4:
            j = 0
            while _level_prefixes[level][j] != '\0':
                buf[pos] = _level_prefixes[level][j]
                pos = pos + 1
                j = j + 1

        # Message
        j = 0
        while j < msg_len and msg[j] != '\0':
            buf[pos] = msg[j]
            pos = pos + 1
            j = j + 1

        buf[pos] = '\n'
        pos = pos + 1

        idx = (idx + 1) % LOG_MAX_ENTRIES
        i = i + 1

    buf[pos] = '\0'

    # Write to ramfs
    return ramfs_write(&_log_file_path[0], &buf[0])

def log_read_from_file(buf: Ptr[char], max_len: int32) -> int32:
    """Read log content from ramfs file.

    Args:
        buf: Buffer to read into
        max_len: Maximum bytes to read

    Returns:
        Number of bytes read, or -1 on error
    """
    if not _log_file_enabled:
        return -1

    return ramfs_read(&_log_file_path[0], cast[Ptr[uint8]](buf), max_len)

# ============================================================================
# Statistics and Debug
# ============================================================================

def log_print_stats():
    """Print logging statistics."""
    print_str("Logging Statistics:\n")
    print_str("  Buffer entries: ")
    print_int(_log_count)
    print_str("/")
    print_int(LOG_MAX_ENTRIES)
    print_newline()

    print_str("  Total logged: ")
    print_int(_log_total_count)
    print_newline()

    print_str("  Dropped: ")
    print_int(_log_dropped_count)
    print_newline()

    print_str("  Min level: ")
    if _log_min_level >= 0 and _log_min_level <= 4:
        print_str(&_level_names[_log_min_level][0])
    else:
        print_int(_log_min_level)
    print_newline()

    print_str("  Console output: ")
    if _log_output_enabled:
        print_str("enabled")
    else:
        print_str("disabled")
    print_newline()

    print_str("  File logging: ")
    if _log_file_enabled:
        print_str(&_log_file_path[0])
    else:
        print_str("disabled")
    print_newline()

def log_level_name(level: int32) -> Ptr[char]:
    """Get name string for log level.

    Args:
        level: Log level

    Returns:
        Level name string
    """
    if level >= 0 and level <= 4:
        return &_level_names[level][0]
    return "UNKNOWN"

def log_parse_level(name: Ptr[char]) -> int32:
    """Parse log level from name string.

    Args:
        name: Level name (DEBUG, INFO, WARN, ERROR, FATAL)

    Returns:
        Log level, or -1 if unknown
    """
    i: int32 = 0
    while i <= 4:
        if strcmp(name, &_level_names[i][0]) == 0:
            return i
        i = i + 1
    return -1

# External function references
extern def timer_get_ticks() -> int32
extern def critical_enter() -> int32
extern def critical_exit(state: int32)
extern def ramfs_write(path: Ptr[char], data: Ptr[char]) -> int32
extern def ramfs_read(path: Ptr[char], buf: Ptr[uint8], count: int32) -> int32
