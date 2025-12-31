# Pynux Function Timing Profiler
#
# Lightweight profiling for bare-metal ARM Cortex-M3.
# Tracks timing statistics for named code sections.
#
# Uses SysTick CVR for cycle-accurate timing.

from lib.io import print_str, print_int, print_newline, uart_putc
from lib.string import strcmp, strlen, strcpy

# ============================================================================
# Configuration
# ============================================================================

# Maximum number of profiled sections
MAX_PROFILE_ENTRIES: int32 = 32

# Name length limit
MAX_NAME_LEN: int32 = 16

# ============================================================================
# SysTick access for cycle counting
# ============================================================================

PROF_SYST_CVR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E018)
PROF_SYST_RVR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E014)

# ============================================================================
# Profile entry structure (packed in arrays)
# ============================================================================
#
# For each entry:
#   name: char[16]     - Section name (16 bytes)
#   calls: int32       - Number of calls (4 bytes)
#   total: int32       - Total time in cycles (4 bytes)
#   max_time: int32    - Maximum call time (4 bytes)
#   start: int32       - Start timestamp (4 bytes, transient)
#   active: int32      - 1 if timing active (4 bytes)
#
# Entry size: 36 bytes

PROF_ENTRY_SIZE: int32 = 36
PROF_ENTRY_NAME_OFFSET: int32 = 0
PROF_ENTRY_CALLS_OFFSET: int32 = 16
PROF_ENTRY_TOTAL_OFFSET: int32 = 20
PROF_ENTRY_MAX_OFFSET: int32 = 24
PROF_ENTRY_START_OFFSET: int32 = 28
PROF_ENTRY_ACTIVE_OFFSET: int32 = 32

# ============================================================================
# Profiler state
# ============================================================================

# Storage: 32 entries * 36 bytes = 1152 bytes
_profile_data: Array[1152, uint8]
_profile_count: int32 = 0
_profile_enabled: bool = False
_profile_overhead: int32 = 0

# ============================================================================
# Internal helpers
# ============================================================================

def _prof_get_entry_ptr(idx: int32) -> Ptr[uint8]:
    """Get pointer to entry at index."""
    return &_profile_data[idx * PROF_ENTRY_SIZE]

def _prof_get_entry_name(entry: Ptr[uint8]) -> Ptr[char]:
    """Get name field of entry."""
    return cast[Ptr[char]](&entry[PROF_ENTRY_NAME_OFFSET])

def _prof_get_entry_int(entry: Ptr[uint8], offset: int32) -> int32:
    """Get int32 field from entry."""
    ptr: Ptr[int32] = cast[Ptr[int32]](&entry[offset])
    return ptr[0]

def _prof_set_entry_int(entry: Ptr[uint8], offset: int32, val: int32):
    """Set int32 field in entry."""
    ptr: Ptr[int32] = cast[Ptr[int32]](&entry[offset])
    ptr[0] = val

def _prof_find_entry(name: Ptr[char]) -> int32:
    """Find entry by name. Returns index or -1 if not found."""
    i: int32 = 0
    while i < _profile_count:
        entry: Ptr[uint8] = _prof_get_entry_ptr(i)
        entry_name: Ptr[char] = _prof_get_entry_name(entry)
        if strcmp(entry_name, name) == 0:
            return i
        i = i + 1
    return -1

def _prof_create_entry(name: Ptr[char]) -> int32:
    """Create new entry. Returns index or -1 if full."""
    if _profile_count >= MAX_PROFILE_ENTRIES:
        return -1

    idx: int32 = _profile_count
    entry: Ptr[uint8] = _prof_get_entry_ptr(idx)

    # Copy name (truncate if needed)
    entry_name: Ptr[char] = _prof_get_entry_name(entry)
    name_len: int32 = strlen(name)
    if name_len >= MAX_NAME_LEN:
        name_len = MAX_NAME_LEN - 1

    i: int32 = 0
    while i < name_len:
        entry_name[i] = name[i]
        i = i + 1
    entry_name[name_len] = '\0'

    # Initialize stats
    _prof_set_entry_int(entry, PROF_ENTRY_CALLS_OFFSET, 0)
    _prof_set_entry_int(entry, PROF_ENTRY_TOTAL_OFFSET, 0)
    _prof_set_entry_int(entry, PROF_ENTRY_MAX_OFFSET, 0)
    _prof_set_entry_int(entry, PROF_ENTRY_START_OFFSET, 0)
    _prof_set_entry_int(entry, PROF_ENTRY_ACTIVE_OFFSET, 0)

    _profile_count = _profile_count + 1
    return idx

def _get_cycles() -> int32:
    """Get current cycle count from SysTick CVR.

    Note: CVR counts down, so we invert for increasing time.
    """
    reload: uint32 = PROF_SYST_RVR[0]
    current: uint32 = PROF_SYST_CVR[0]
    return cast[int32](reload - current)

def _calibrate_overhead():
    """Measure profiler overhead for compensation."""
    global _profile_overhead

    # Measure overhead of start/stop sequence
    start: int32 = _get_cycles()
    end: int32 = _get_cycles()

    _profile_overhead = end - start
    if _profile_overhead < 0:
        _profile_overhead = 0

# ============================================================================
# Public API
# ============================================================================

def profile_init():
    """Initialize the profiler. Must be called before use."""
    global _profile_count, _profile_enabled, _profile_overhead

    state: int32 = critical_enter()

    # Clear all entries
    _profile_count = 0
    _profile_enabled = True

    # Zero out storage
    i: int32 = 0
    while i < 1152:
        _profile_data[i] = 0
        i = i + 1

    # Calibrate overhead
    _calibrate_overhead()

    critical_exit(state)

def profile_start(name: Ptr[char]):
    """Start timing a named section.

    If section doesn't exist, creates it.
    Nested calls to same section are ignored.
    """
    if not _profile_enabled:
        return

    state: int32 = critical_enter()

    # Find or create entry
    idx: int32 = _prof_find_entry(name)
    if idx < 0:
        idx = _prof_create_entry(name)
        if idx < 0:
            critical_exit(state)
            return  # No room

    entry: Ptr[uint8] = _prof_get_entry_ptr(idx)

    # Check if already active (nested call)
    if _prof_get_entry_int(entry, PROF_ENTRY_ACTIVE_OFFSET) != 0:
        critical_exit(state)
        return

    # Mark active and record start time
    _prof_set_entry_int(entry, PROF_ENTRY_ACTIVE_OFFSET, 1)
    _prof_set_entry_int(entry, PROF_ENTRY_START_OFFSET, _get_cycles())

    critical_exit(state)

def profile_stop(name: Ptr[char]):
    """Stop timing a named section.

    Records duration and updates statistics.
    """
    if not _profile_enabled:
        return

    # Get end time immediately for accuracy
    end_time: int32 = _get_cycles()

    state: int32 = critical_enter()

    idx: int32 = _prof_find_entry(name)
    if idx < 0:
        critical_exit(state)
        return  # Not found

    entry: Ptr[uint8] = _prof_get_entry_ptr(idx)

    # Check if active
    if _prof_get_entry_int(entry, PROF_ENTRY_ACTIVE_OFFSET) == 0:
        critical_exit(state)
        return  # Not active

    # Calculate duration
    start_time: int32 = _prof_get_entry_int(entry, PROF_ENTRY_START_OFFSET)
    duration: int32 = end_time - start_time

    # Handle wrap-around
    if duration < 0:
        reload: int32 = cast[int32](PROF_SYST_RVR[0])
        duration = duration + reload

    # Subtract overhead
    duration = duration - _profile_overhead
    if duration < 0:
        duration = 0

    # Update statistics
    calls: int32 = _prof_get_entry_int(entry, PROF_ENTRY_CALLS_OFFSET) + 1
    total: int32 = _prof_get_entry_int(entry, PROF_ENTRY_TOTAL_OFFSET) + duration
    max_time: int32 = _prof_get_entry_int(entry, PROF_ENTRY_MAX_OFFSET)

    if duration > max_time:
        max_time = duration

    _prof_set_entry_int(entry, PROF_ENTRY_CALLS_OFFSET, calls)
    _prof_set_entry_int(entry, PROF_ENTRY_TOTAL_OFFSET, total)
    _prof_set_entry_int(entry, PROF_ENTRY_MAX_OFFSET, max_time)
    _prof_set_entry_int(entry, PROF_ENTRY_ACTIVE_OFFSET, 0)

    critical_exit(state)

def profile_reset():
    """Clear all profiling data."""
    global _profile_count

    state: int32 = critical_enter()

    _profile_count = 0

    # Zero out storage
    i: int32 = 0
    while i < 1152:
        _profile_data[i] = 0
        i = i + 1

    critical_exit(state)

def profile_report():
    """Print timing report for all profiled sections."""
    state: int32 = critical_enter()

    print_str("=== Profile Report ===")
    print_newline()
    print_str("Overhead: ")
    print_int(_profile_overhead)
    print_str(" cycles")
    print_newline()
    print_newline()

    if _profile_count == 0:
        print_str("  No data collected")
        print_newline()
        critical_exit(state)
        return

    # Header
    print_str("Name            Calls      Total        Avg        Max")
    print_newline()
    print_str("------------------------------------------------------")
    print_newline()

    i: int32 = 0
    while i < _profile_count:
        entry: Ptr[uint8] = _prof_get_entry_ptr(i)
        entry_name: Ptr[char] = _prof_get_entry_name(entry)
        calls: int32 = _prof_get_entry_int(entry, PROF_ENTRY_CALLS_OFFSET)
        total: int32 = _prof_get_entry_int(entry, PROF_ENTRY_TOTAL_OFFSET)
        max_time: int32 = _prof_get_entry_int(entry, PROF_ENTRY_MAX_OFFSET)

        # Calculate average
        avg: int32 = 0
        if calls > 0:
            avg = total / calls

        # Print name (padded to 16 chars)
        print_str(entry_name)
        name_len: int32 = strlen(entry_name)
        spaces: int32 = 16 - name_len
        while spaces > 0:
            uart_putc(' ')
            spaces = spaces - 1

        # Print stats (right-aligned)
        _prof_print_padded_int(calls, 6)
        _prof_print_padded_int(total, 10)
        _prof_print_padded_int(avg, 10)
        _prof_print_padded_int(max_time, 10)
        print_newline()

        i = i + 1

    print_newline()

    critical_exit(state)

def _prof_print_padded_int(val: int32, width: int32):
    """Print integer right-padded to width."""
    # Count digits
    digits: int32 = 1
    tmp: int32 = val
    if tmp < 0:
        tmp = -tmp
        digits = digits + 1  # For minus sign
    while tmp >= 10:
        tmp = tmp / 10
        digits = digits + 1

    # Print leading spaces
    spaces: int32 = width - digits
    while spaces > 0:
        uart_putc(' ')
        spaces = spaces - 1

    print_int(val)

def profile_get_calls(name: Ptr[char]) -> int32:
    """Get call count for named section."""
    state: int32 = critical_enter()

    idx: int32 = _prof_find_entry(name)
    if idx < 0:
        critical_exit(state)
        return 0

    entry: Ptr[uint8] = _prof_get_entry_ptr(idx)
    result: int32 = _prof_get_entry_int(entry, PROF_ENTRY_CALLS_OFFSET)

    critical_exit(state)
    return result

def profile_get_total(name: Ptr[char]) -> int32:
    """Get total time (cycles) for named section."""
    state: int32 = critical_enter()

    idx: int32 = _prof_find_entry(name)
    if idx < 0:
        critical_exit(state)
        return 0

    entry: Ptr[uint8] = _prof_get_entry_ptr(idx)
    result: int32 = _prof_get_entry_int(entry, PROF_ENTRY_TOTAL_OFFSET)

    critical_exit(state)
    return result

def profile_get_avg(name: Ptr[char]) -> int32:
    """Get average time (cycles) for named section."""
    state: int32 = critical_enter()

    idx: int32 = _prof_find_entry(name)
    if idx < 0:
        critical_exit(state)
        return 0

    entry: Ptr[uint8] = _prof_get_entry_ptr(idx)
    calls: int32 = _prof_get_entry_int(entry, PROF_ENTRY_CALLS_OFFSET)
    total: int32 = _prof_get_entry_int(entry, PROF_ENTRY_TOTAL_OFFSET)

    critical_exit(state)

    if calls == 0:
        return 0
    return total / calls

def profile_get_max(name: Ptr[char]) -> int32:
    """Get maximum time (cycles) for named section."""
    state: int32 = critical_enter()

    idx: int32 = _prof_find_entry(name)
    if idx < 0:
        critical_exit(state)
        return 0

    entry: Ptr[uint8] = _prof_get_entry_ptr(idx)
    result: int32 = _prof_get_entry_int(entry, PROF_ENTRY_MAX_OFFSET)

    critical_exit(state)
    return result

def profile_enable():
    """Enable profiling."""
    global _profile_enabled
    _profile_enabled = True

def profile_disable():
    """Disable profiling (start/stop become no-ops)."""
    global _profile_enabled
    _profile_enabled = False

def profile_is_enabled() -> bool:
    """Check if profiling is enabled."""
    return _profile_enabled

def profile_get_count() -> int32:
    """Get number of profiled sections."""
    return _profile_count
