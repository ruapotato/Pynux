# Pynux Memory Tracking
#
# Memory allocation tracker for bare-metal ARM Cortex-M3.
# Records allocations with tags for debugging memory usage.
#
# Designed for low overhead and minimal memory footprint.

from lib.io import print_str, print_int, print_hex, print_newline, uart_putc
from lib.string import strcmp, strlen

# ============================================================================
# Configuration
# ============================================================================

# Maximum tracked allocations
MT_MAX_TRACKED_ALLOCS: int32 = 128

# Tag name length limit
MAX_TAG_LEN: int32 = 8

# ============================================================================
# Allocation entry structure (packed in arrays)
# ============================================================================
#
# For each entry:
#   ptr: uint32      - Allocation address (4 bytes)
#   size: int32      - Allocation size (4 bytes)
#   tag: char[8]     - Tag name (8 bytes)
#   active: int32    - 1 if allocated, 0 if freed (4 bytes)
#
# Entry size: 20 bytes

MT_ENTRY_SIZE: int32 = 20
MT_ENTRY_PTR_OFFSET: int32 = 0
MT_MT_ENTRY_SIZE_OFFSET: int32 = 4
MT_ENTRY_TAG_OFFSET: int32 = 8
MT_ENTRY_ACTIVE_OFFSET: int32 = 16

# ============================================================================
# Tracker state
# ============================================================================

# Storage: 128 entries * 20 bytes = 2560 bytes
_track_data: Array[2560, uint8]
_track_count: int32 = 0
_track_enabled: bool = False

# Statistics
_total_allocated: int32 = 0
_peak_allocated: int32 = 0
_current_allocated: int32 = 0
_alloc_count: int32 = 0
_free_count: int32 = 0

# ============================================================================
# Internal helpers
# ============================================================================

def _mt_get_entry_ptr(idx: int32) -> Ptr[uint8]:
    """Get pointer to entry at index."""
    return &_track_data[idx * MT_ENTRY_SIZE]

def _mt_get_entry_uint(entry: Ptr[uint8], offset: int32) -> uint32:
    """Get uint32 field from entry."""
    ptr: Ptr[uint32] = cast[Ptr[uint32]](&entry[offset])
    return ptr[0]

def _mt_get_entry_int(entry: Ptr[uint8], offset: int32) -> int32:
    """Get int32 field from entry."""
    ptr: Ptr[int32] = cast[Ptr[int32]](&entry[offset])
    return ptr[0]

def _mt_set_entry_uint(entry: Ptr[uint8], offset: int32, val: uint32):
    """Set uint32 field in entry."""
    ptr: Ptr[uint32] = cast[Ptr[uint32]](&entry[offset])
    ptr[0] = val

def _mt_set_entry_int(entry: Ptr[uint8], offset: int32, val: int32):
    """Set int32 field in entry."""
    ptr: Ptr[int32] = cast[Ptr[int32]](&entry[offset])
    ptr[0] = val

def _mt_get_entry_tag(entry: Ptr[uint8]) -> Ptr[char]:
    """Get tag field of entry."""
    return cast[Ptr[char]](&entry[MT_ENTRY_TAG_OFFSET])

def _mt_find_entry_by_ptr(ptr: uint32) -> int32:
    """Find entry by allocation pointer. Returns index or -1."""
    i: int32 = 0
    while i < _track_count:
        entry: Ptr[uint8] = _mt_get_entry_ptr(i)
        if _mt_get_entry_uint(entry, MT_ENTRY_PTR_OFFSET) == ptr:
            if _mt_get_entry_int(entry, MT_ENTRY_ACTIVE_OFFSET) == 1:
                return i
        i = i + 1
    return -1

def _mt_find_free_slot() -> int32:
    """Find an unused slot. Returns index or -1 if full."""
    # First, look for inactive entries to reuse
    i: int32 = 0
    while i < _track_count:
        entry: Ptr[uint8] = _mt_get_entry_ptr(i)
        if _mt_get_entry_int(entry, MT_ENTRY_ACTIVE_OFFSET) == 0:
            return i
        i = i + 1

    # No inactive slots, use new slot if available
    if _track_count < MT_MAX_TRACKED_ALLOCS:
        idx: int32 = _track_count
        _track_count = _track_count + 1
        return idx

    return -1

# ============================================================================
# Public API
# ============================================================================

def memtrack_init():
    """Initialize memory tracker. Must be called before use."""
    global _track_count, _track_enabled
    global _total_allocated, _peak_allocated, _current_allocated
    global _alloc_count, _free_count

    state: int32 = critical_enter()

    _track_count = 0
    _track_enabled = True
    _total_allocated = 0
    _peak_allocated = 0
    _current_allocated = 0
    _alloc_count = 0
    _free_count = 0

    # Zero out storage
    i: int32 = 0
    while i < 2560:
        _track_data[i] = 0
        i = i + 1

    critical_exit(state)

def memtrack_alloc(ptr: Ptr[uint8], size: int32, tag: Ptr[char]):
    """Record an allocation.

    Args:
        ptr: Pointer to allocated memory
        size: Size in bytes
        tag: Short tag for identification (max 7 chars)
    """
    global _total_allocated, _peak_allocated, _current_allocated, _alloc_count

    if not _track_enabled:
        return

    if cast[uint32](ptr) == 0:
        return

    state: int32 = critical_enter()

    # Find slot
    idx: int32 = _mt_find_free_slot()
    if idx < 0:
        critical_exit(state)
        return  # No room

    entry: Ptr[uint8] = _mt_get_entry_ptr(idx)

    # Record allocation
    _mt_set_entry_uint(entry, MT_ENTRY_PTR_OFFSET, cast[uint32](ptr))
    _mt_set_entry_int(entry, MT_MT_ENTRY_SIZE_OFFSET, size)
    _mt_set_entry_int(entry, MT_ENTRY_ACTIVE_OFFSET, 1)

    # Copy tag
    entry_tag: Ptr[char] = _mt_get_entry_tag(entry)
    tag_len: int32 = strlen(tag)
    if tag_len >= MAX_TAG_LEN:
        tag_len = MAX_TAG_LEN - 1

    i: int32 = 0
    while i < tag_len:
        entry_tag[i] = tag[i]
        i = i + 1
    entry_tag[tag_len] = '\0'

    # Update statistics
    _alloc_count = _alloc_count + 1
    _total_allocated = _total_allocated + size
    _current_allocated = _current_allocated + size
    if _current_allocated > _peak_allocated:
        _peak_allocated = _current_allocated

    critical_exit(state)

def memtrack_free(ptr: Ptr[uint8]):
    """Record a deallocation.

    Args:
        ptr: Pointer being freed
    """
    global _current_allocated, _free_count

    if not _track_enabled:
        return

    if cast[uint32](ptr) == 0:
        return

    state: int32 = critical_enter()

    idx: int32 = _mt_find_entry_by_ptr(cast[uint32](ptr))
    if idx < 0:
        critical_exit(state)
        return  # Not tracked

    entry: Ptr[uint8] = _mt_get_entry_ptr(idx)
    size: int32 = _mt_get_entry_int(entry, MT_MT_ENTRY_SIZE_OFFSET)

    # Mark as freed
    _mt_set_entry_int(entry, MT_ENTRY_ACTIVE_OFFSET, 0)

    # Update statistics
    _free_count = _free_count + 1
    _current_allocated = _current_allocated - size

    critical_exit(state)

def memtrack_report():
    """Print memory tracking report."""
    state: int32 = critical_enter()

    print_str("=== Memory Tracking Report ===")
    print_newline()
    print_newline()

    # Summary statistics
    print_str("Summary:")
    print_newline()
    print_str("  Allocations:    ")
    print_int(_alloc_count)
    print_newline()
    print_str("  Frees:          ")
    print_int(_free_count)
    print_newline()
    print_str("  Total alloc'd:  ")
    print_int(_total_allocated)
    print_str(" bytes")
    print_newline()
    print_str("  Peak usage:     ")
    print_int(_peak_allocated)
    print_str(" bytes")
    print_newline()
    print_str("  Current usage:  ")
    print_int(_current_allocated)
    print_str(" bytes")
    print_newline()
    print_newline()

    # Count active allocations
    active_count: int32 = 0
    i: int32 = 0
    while i < _track_count:
        entry: Ptr[uint8] = _mt_get_entry_ptr(i)
        if _mt_get_entry_int(entry, MT_ENTRY_ACTIVE_OFFSET) == 1:
            active_count = active_count + 1
        i = i + 1

    if active_count == 0:
        print_str("No active allocations")
        print_newline()
        critical_exit(state)
        return

    # Print active allocations
    print_str("Active Allocations (")
    print_int(active_count)
    print_str("):")
    print_newline()
    print_str("  Address     Size     Tag")
    print_newline()
    print_str("  -------------------------------")
    print_newline()

    i = 0
    while i < _track_count:
        entry: Ptr[uint8] = _mt_get_entry_ptr(i)
        if _mt_get_entry_int(entry, MT_ENTRY_ACTIVE_OFFSET) == 1:
            ptr: uint32 = _mt_get_entry_uint(entry, MT_ENTRY_PTR_OFFSET)
            size: int32 = _mt_get_entry_int(entry, MT_MT_ENTRY_SIZE_OFFSET)
            tag: Ptr[char] = _mt_get_entry_tag(entry)

            print_str("  0x")
            print_hex(ptr)
            print_str("  ")
            _mt_print_padded_int(size, 6)
            print_str("   ")
            print_str(tag)
            print_newline()
        i = i + 1

    print_newline()

    critical_exit(state)

def _mt_print_padded_int(val: int32, width: int32):
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

def memtrack_check_leaks() -> int32:
    """Check for memory leaks.

    Returns: Number of leaked allocations
    """
    state: int32 = critical_enter()

    leak_count: int32 = 0
    leak_bytes: int32 = 0

    print_str("=== Memory Leak Check ===")
    print_newline()

    i: int32 = 0
    while i < _track_count:
        entry: Ptr[uint8] = _mt_get_entry_ptr(i)
        if _mt_get_entry_int(entry, MT_ENTRY_ACTIVE_OFFSET) == 1:
            ptr: uint32 = _mt_get_entry_uint(entry, MT_ENTRY_PTR_OFFSET)
            size: int32 = _mt_get_entry_int(entry, MT_MT_ENTRY_SIZE_OFFSET)
            tag: Ptr[char] = _mt_get_entry_tag(entry)

            print_str("  LEAK: 0x")
            print_hex(ptr)
            print_str(" size=")
            print_int(size)
            print_str(" tag=")
            print_str(tag)
            print_newline()

            leak_count = leak_count + 1
            leak_bytes = leak_bytes + size
        i = i + 1

    if leak_count == 0:
        print_str("  No leaks detected")
        print_newline()
    else:
        print_newline()
        print_str("Total: ")
        print_int(leak_count)
        print_str(" leaks (")
        print_int(leak_bytes)
        print_str(" bytes)")
        print_newline()

    critical_exit(state)
    return leak_count

def memtrack_get_total() -> int32:
    """Get total bytes ever allocated."""
    return _total_allocated

def memtrack_get_peak() -> int32:
    """Get peak memory usage in bytes."""
    return _peak_allocated

def memtrack_get_count() -> int32:
    """Get current number of active allocations."""
    state: int32 = critical_enter()

    count: int32 = 0
    i: int32 = 0
    while i < _track_count:
        entry: Ptr[uint8] = _mt_get_entry_ptr(i)
        if _mt_get_entry_int(entry, MT_ENTRY_ACTIVE_OFFSET) == 1:
            count = count + 1
        i = i + 1

    critical_exit(state)
    return count

def memtrack_get_current() -> int32:
    """Get current allocated bytes."""
    return _current_allocated

def memtrack_enable():
    """Enable memory tracking."""
    global _track_enabled
    _track_enabled = True

def memtrack_disable():
    """Disable memory tracking."""
    global _track_enabled
    _track_enabled = False

def memtrack_is_enabled() -> bool:
    """Check if tracking is enabled."""
    return _track_enabled

def memtrack_get_size(ptr: Ptr[uint8]) -> int32:
    """Get tracked size of an allocation. Returns 0 if not found."""
    state: int32 = critical_enter()

    idx: int32 = _mt_find_entry_by_ptr(cast[uint32](ptr))
    if idx < 0:
        critical_exit(state)
        return 0

    entry: Ptr[uint8] = _mt_get_entry_ptr(idx)
    size: int32 = _mt_get_entry_int(entry, MT_MT_ENTRY_SIZE_OFFSET)

    critical_exit(state)
    return size

def memtrack_get_tag(ptr: Ptr[uint8]) -> Ptr[char]:
    """Get tag of an allocation. Returns empty string if not found."""
    state: int32 = critical_enter()

    idx: int32 = _mt_find_entry_by_ptr(cast[uint32](ptr))
    if idx < 0:
        critical_exit(state)
        return ""

    entry: Ptr[uint8] = _mt_get_entry_ptr(idx)
    tag: Ptr[char] = _mt_get_entry_tag(entry)

    critical_exit(state)
    return tag

def memtrack_reset():
    """Reset all tracking data."""
    global _track_count, _total_allocated, _peak_allocated
    global _current_allocated, _alloc_count, _free_count

    state: int32 = critical_enter()

    _track_count = 0
    _total_allocated = 0
    _peak_allocated = 0
    _current_allocated = 0
    _alloc_count = 0
    _free_count = 0

    # Zero out storage
    i: int32 = 0
    while i < 2560:
        _track_data[i] = 0
        i = i + 1

    critical_exit(state)
