# Pynux Execution Tracing
#
# Lightweight execution tracer for bare-metal ARM Cortex-M3.
# Uses a circular buffer for minimal memory overhead.
# Designed for low-overhead tracing of function calls, IRQs, etc.

from lib.io import print_str, print_int, print_hex, print_newline, uart_putc

# ============================================================================
# Trace Event Types
# ============================================================================

TRACE_FUNC_ENTER: int32 = 0x01
TRACE_FUNC_EXIT: int32 = 0x02
TRACE_IRQ: int32 = 0x03
TRACE_IRQ_EXIT: int32 = 0x04
TRACE_SYSCALL: int32 = 0x05
TRACE_ALLOC: int32 = 0x06
TRACE_FREE: int32 = 0x07
TRACE_LOCK: int32 = 0x08
TRACE_UNLOCK: int32 = 0x09
TRACE_YIELD: int32 = 0x0A
TRACE_WAKE: int32 = 0x0B
TRACE_ERROR: int32 = 0x0C
TRACE_USER: int32 = 0x10

# ============================================================================
# Configuration
# ============================================================================

# Trace buffer size (power of 2 for efficient masking)
TRACE_BUFFER_SIZE: int32 = 256
TRACE_BUFFER_MASK: int32 = 255

# ============================================================================
# SysTick for timestamps
# ============================================================================

TRACE_SYST_CVR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E018)
TRACE_SYST_RVR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E014)

# ============================================================================
# Trace entry structure (packed in arrays)
# ============================================================================
#
# Each entry (8 bytes, compact for minimal cache/memory impact):
#   timestamp: uint16   - Low 16 bits of cycle counter (2 bytes)
#   event: uint8        - Event type (1 byte)
#   flags: uint8        - Additional flags (1 byte)
#   data: uint32        - Event-specific data (4 bytes)
#
# Entry size: 8 bytes
# Total buffer: 256 * 8 = 2048 bytes

TRACE_ENTRY_SIZE: int32 = 8
TRACE_ENTRY_TIMESTAMP_OFFSET: int32 = 0
TRACE_ENTRY_EVENT_OFFSET: int32 = 2
TRACE_ENTRY_FLAGS_OFFSET: int32 = 3
TRACE_ENTRY_DATA_OFFSET: int32 = 4

# ============================================================================
# Trace state
# ============================================================================

# Circular buffer storage
_trace_buffer: Array[2048, uint8]

# Buffer indices
_trace_head: int32 = 0          # Next write position
_trace_count: int32 = 0         # Number of entries (max TRACE_BUFFER_SIZE)
_trace_seq: uint32 = 0          # Sequence number for overflow detection

# Control
_trace_enabled: bool = False
_trace_filter: int32 = 0xFFFF   # Bitmask of enabled event types

# Overflow counter
_trace_overflow: int32 = 0

# ============================================================================
# Internal helpers
# ============================================================================

def _trace_get_entry_ptr(idx: int32) -> Ptr[uint8]:
    """Get pointer to entry at index."""
    return &_trace_buffer[(idx & TRACE_BUFFER_MASK) * TRACE_ENTRY_SIZE]

def _trace_get_timestamp() -> uint16:
    """Get current timestamp (low 16 bits of cycle counter)."""
    reload: uint32 = TRACE_SYST_RVR[0]
    current: uint32 = TRACE_SYST_CVR[0]
    cycles: uint32 = reload - current
    return cast[uint16](cycles & 0xFFFF)

def _trace_is_event_enabled(event: int32) -> bool:
    """Check if event type passes the filter."""
    if event >= 16:
        # User events always pass if any user bit set
        return (_trace_filter & 0xFF00) != 0
    return (_trace_filter & (1 << event)) != 0

# ============================================================================
# Public API
# ============================================================================

def trace_init():
    """Initialize the trace system."""
    global _trace_head, _trace_count, _trace_seq
    global _trace_enabled, _trace_overflow, _trace_filter

    state: int32 = critical_enter()

    _trace_head = 0
    _trace_count = 0
    _trace_seq = 0
    _trace_enabled = False
    _trace_overflow = 0
    _trace_filter = 0xFFFF  # All events enabled

    # Zero buffer
    i: int32 = 0
    while i < 2048:
        _trace_buffer[i] = 0
        i = i + 1

    critical_exit(state)

def trace_enable():
    """Start tracing."""
    global _trace_enabled
    _trace_enabled = True

def trace_disable():
    """Stop tracing."""
    global _trace_enabled
    _trace_enabled = False

def trace_is_enabled() -> bool:
    """Check if tracing is enabled."""
    return _trace_enabled

def trace_set_filter(mask: int32):
    """Set event filter bitmask.

    Bits 0-15 correspond to event types.
    Set bit to 1 to enable that event type.
    """
    global _trace_filter
    _trace_filter = mask

def trace_get_filter() -> int32:
    """Get current event filter."""
    return _trace_filter

def trace_log(event: int32, data: uint32):
    """Log a trace event.

    Args:
        event: Event type (TRACE_FUNC_ENTER, etc.)
        data: Event-specific data (function addr, IRQ num, etc.)
    """
    global _trace_head, _trace_count, _trace_seq, _trace_overflow

    if not _trace_enabled:
        return

    if not _trace_is_event_enabled(event):
        return

    state: int32 = critical_enter()

    # Get current position and advance
    idx: int32 = _trace_head
    _trace_head = (_trace_head + 1) & TRACE_BUFFER_MASK

    # Track overflow
    if _trace_count < TRACE_BUFFER_SIZE:
        _trace_count = _trace_count + 1
    else:
        _trace_overflow = _trace_overflow + 1

    _trace_seq = _trace_seq + 1

    # Get entry pointer
    entry: Ptr[uint8] = _trace_get_entry_ptr(idx)

    # Write timestamp (2 bytes)
    ts: uint16 = _trace_get_timestamp()
    ts_ptr: Ptr[uint16] = cast[Ptr[uint16]](&entry[TRACE_ENTRY_TIMESTAMP_OFFSET])
    ts_ptr[0] = ts

    # Write event and flags (2 bytes)
    entry[TRACE_ENTRY_EVENT_OFFSET] = cast[uint8](event & 0xFF)
    entry[TRACE_ENTRY_FLAGS_OFFSET] = 0

    # Write data (4 bytes)
    data_ptr: Ptr[uint32] = cast[Ptr[uint32]](&entry[TRACE_ENTRY_DATA_OFFSET])
    data_ptr[0] = data

    critical_exit(state)

def trace_log_func_enter(func_addr: uint32):
    """Log function entry."""
    trace_log(TRACE_FUNC_ENTER, func_addr)

def trace_log_func_exit(func_addr: uint32):
    """Log function exit."""
    trace_log(TRACE_FUNC_EXIT, func_addr)

def trace_log_irq(irq_num: int32):
    """Log IRQ entry."""
    trace_log(TRACE_IRQ, cast[uint32](irq_num))

def trace_log_irq_exit(irq_num: int32):
    """Log IRQ exit."""
    trace_log(TRACE_IRQ_EXIT, cast[uint32](irq_num))

def trace_log_alloc(ptr: uint32, size: int32):
    """Log allocation. Encodes size in upper bits."""
    # Pack size in upper 16 bits, use lower 16 bits of ptr
    packed_val: uint32 = (cast[uint32](size) << 16) | (ptr & 0xFFFF)
    trace_log(TRACE_ALLOC, packed_val)

def trace_log_free(ptr: uint32):
    """Log deallocation."""
    trace_log(TRACE_FREE, ptr)

def trace_log_error(code: int32):
    """Log error."""
    trace_log(TRACE_ERROR, cast[uint32](code))

def trace_log_user(data: uint32):
    """Log user-defined event."""
    trace_log(TRACE_USER, data)

def trace_clear():
    """Clear the trace buffer."""
    global _trace_head, _trace_count, _trace_overflow

    state: int32 = critical_enter()

    _trace_head = 0
    _trace_count = 0
    _trace_overflow = 0

    critical_exit(state)

def trace_get_count() -> int32:
    """Get number of entries in buffer."""
    return _trace_count

def trace_get_overflow() -> int32:
    """Get number of lost entries due to overflow."""
    return _trace_overflow

def _get_event_name(event: int32) -> Ptr[char]:
    """Get human-readable event name."""
    if event == TRACE_FUNC_ENTER:
        return "ENTER"
    elif event == TRACE_FUNC_EXIT:
        return "EXIT "
    elif event == TRACE_IRQ:
        return "IRQ  "
    elif event == TRACE_IRQ_EXIT:
        return "IRQX "
    elif event == TRACE_SYSCALL:
        return "SYSC "
    elif event == TRACE_ALLOC:
        return "ALLOC"
    elif event == TRACE_FREE:
        return "FREE "
    elif event == TRACE_LOCK:
        return "LOCK "
    elif event == TRACE_UNLOCK:
        return "UNLCK"
    elif event == TRACE_YIELD:
        return "YIELD"
    elif event == TRACE_WAKE:
        return "WAKE "
    elif event == TRACE_ERROR:
        return "ERROR"
    elif event >= TRACE_USER:
        return "USER "
    else:
        return "???? "

def trace_dump():
    """Dump trace buffer to console."""
    state: int32 = critical_enter()

    print_str("=== Trace Dump ===")
    print_newline()
    print_str("Entries: ")
    print_int(_trace_count)
    print_str("  Overflow: ")
    print_int(_trace_overflow)
    print_newline()
    print_newline()

    if _trace_count == 0:
        print_str("  No trace data")
        print_newline()
        critical_exit(state)
        return

    # Header
    print_str("  #    Time   Event  Data")
    print_newline()
    print_str("  ---------------------------------")
    print_newline()

    # Calculate start position (oldest entry)
    start: int32 = 0
    if _trace_count >= TRACE_BUFFER_SIZE:
        start = _trace_head  # Oldest is next write position
    else:
        start = 0

    # Print entries from oldest to newest
    i: int32 = 0
    while i < _trace_count:
        idx: int32 = (start + i) & TRACE_BUFFER_MASK
        entry: Ptr[uint8] = _trace_get_entry_ptr(idx)

        # Read entry
        ts_ptr: Ptr[uint16] = cast[Ptr[uint16]](&entry[TRACE_ENTRY_TIMESTAMP_OFFSET])
        ts: int32 = cast[int32](ts_ptr[0])
        event: int32 = cast[int32](entry[TRACE_ENTRY_EVENT_OFFSET])
        data_ptr: Ptr[uint32] = cast[Ptr[uint32]](&entry[TRACE_ENTRY_DATA_OFFSET])
        data: uint32 = data_ptr[0]

        # Print entry number
        _trace_print_padded_int(i, 4)
        print_str("  ")

        # Print timestamp
        _trace_print_padded_int(ts, 5)
        print_str("  ")

        # Print event name
        print_str(_get_event_name(event))
        print_str("  ")

        # Print data
        print_str("0x")
        print_hex(data)
        print_newline()

        i = i + 1

    print_newline()

    critical_exit(state)

def _trace_print_padded_int(val: int32, width: int32):
    """Print integer right-padded to width."""
    digits: int32 = 1
    tmp: int32 = val
    if tmp < 0:
        tmp = -tmp
        digits = digits + 1
    while tmp >= 10:
        tmp = tmp / 10
        digits = digits + 1

    spaces: int32 = width - digits
    while spaces > 0:
        uart_putc(' ')
        spaces = spaces - 1

    print_int(val)

def trace_dump_range(start_idx: int32, count: int32):
    """Dump a range of trace entries."""
    state: int32 = critical_enter()

    if start_idx < 0:
        start_idx = 0
    if start_idx >= _trace_count:
        print_str("Start index out of range")
        print_newline()
        critical_exit(state)
        return

    # Limit count
    if start_idx + count > _trace_count:
        count = _trace_count - start_idx

    print_str("Trace entries ")
    print_int(start_idx)
    print_str(" to ")
    print_int(start_idx + count - 1)
    print_str(":")
    print_newline()

    # Calculate actual buffer start
    buf_start: int32 = 0
    if _trace_count >= TRACE_BUFFER_SIZE:
        buf_start = _trace_head
    else:
        buf_start = 0

    i: int32 = 0
    while i < count:
        idx: int32 = (buf_start + start_idx + i) & TRACE_BUFFER_MASK
        entry: Ptr[uint8] = _trace_get_entry_ptr(idx)

        ts_ptr: Ptr[uint16] = cast[Ptr[uint16]](&entry[TRACE_ENTRY_TIMESTAMP_OFFSET])
        ts: int32 = cast[int32](ts_ptr[0])
        event: int32 = cast[int32](entry[TRACE_ENTRY_EVENT_OFFSET])
        data_ptr: Ptr[uint32] = cast[Ptr[uint32]](&entry[TRACE_ENTRY_DATA_OFFSET])
        data: uint32 = data_ptr[0]

        _trace_print_padded_int(start_idx + i, 4)
        print_str(": ")
        print_str(_get_event_name(event))
        print_str(" t=")
        print_int(ts)
        print_str(" d=0x")
        print_hex(data)
        print_newline()

        i = i + 1

    critical_exit(state)

def trace_get_last(event_out: Ptr[int32], data_out: Ptr[uint32]) -> bool:
    """Get the most recent trace entry.

    Returns False if buffer is empty.
    """
    state: int32 = critical_enter()

    if _trace_count == 0:
        critical_exit(state)
        return False

    # Last entry is one before head
    idx: int32 = (_trace_head - 1) & TRACE_BUFFER_MASK
    entry: Ptr[uint8] = _trace_get_entry_ptr(idx)

    event_out[0] = cast[int32](entry[TRACE_ENTRY_EVENT_OFFSET])
    data_ptr: Ptr[uint32] = cast[Ptr[uint32]](&entry[TRACE_ENTRY_DATA_OFFSET])
    data_out[0] = data_ptr[0]

    critical_exit(state)
    return True

def trace_count_events(event_type: int32) -> int32:
    """Count occurrences of an event type in the buffer."""
    state: int32 = critical_enter()

    count: int32 = 0

    buf_start: int32 = 0
    if _trace_count >= TRACE_BUFFER_SIZE:
        buf_start = _trace_head

    i: int32 = 0
    while i < _trace_count:
        idx: int32 = (buf_start + i) & TRACE_BUFFER_MASK
        entry: Ptr[uint8] = _trace_get_entry_ptr(idx)
        if cast[int32](entry[TRACE_ENTRY_EVENT_OFFSET]) == event_type:
            count = count + 1
        i = i + 1

    critical_exit(state)
    return count

def trace_find_event(event_type: int32, start_from: int32) -> int32:
    """Find next occurrence of event type starting from index.

    Returns index or -1 if not found.
    """
    state: int32 = critical_enter()

    if start_from < 0:
        start_from = 0
    if start_from >= _trace_count:
        critical_exit(state)
        return -1

    buf_start: int32 = 0
    if _trace_count >= TRACE_BUFFER_SIZE:
        buf_start = _trace_head

    i: int32 = start_from
    while i < _trace_count:
        idx: int32 = (buf_start + i) & TRACE_BUFFER_MASK
        entry: Ptr[uint8] = _trace_get_entry_ptr(idx)
        if cast[int32](entry[TRACE_ENTRY_EVENT_OFFSET]) == event_type:
            critical_exit(state)
            return i
        i = i + 1

    critical_exit(state)
    return -1
