# Pynux Dictionary Library
#
# Hash table implementation for bare-metal ARM.
# Uses open addressing with linear probing.

from lib.memory import alloc, free, memcpy
from lib.string import strlen, strcmp

# Dictionary structure layout:
#   keys: Ptr[int32]      - Array of key pointers (offset 0)
#   values: Ptr[int32]    - Array of value pointers (offset 4)
#   status: Ptr[uint8]    - Array of slot status (offset 8)
#   size: int32           - Number of elements (offset 12)
#   cap: int32            - Capacity (offset 16)
# Total: 20 bytes

DICT_KEYS_OFFSET: int32 = 0
DICT_VALUES_OFFSET: int32 = 4
DICT_STATUS_OFFSET: int32 = 8
DICT_SIZE_OFFSET: int32 = 12
DICT_CAP_OFFSET: int32 = 16
DICT_STRUCT_SIZE: int32 = 20

# Slot status values
SLOT_EMPTY: uint8 = 0
SLOT_OCCUPIED: uint8 = 1
SLOT_DELETED: uint8 = 2

# Default capacity (should be prime for better distribution)
DEFAULT_DICT_CAP: int32 = 17

# Load factor threshold (as percentage)
LOAD_FACTOR_THRESHOLD: int32 = 70

# ============================================================================
# Hash Functions
# ============================================================================

def hash_int(key: int32) -> uint32:
    """Hash function for integers (FNV-1a inspired)."""
    h: uint32 = 2166136261
    h = (h ^ (cast[uint32](key) & 255)) * 16777619
    h = (h ^ ((cast[uint32](key) >> 8) & 255)) * 16777619
    h = (h ^ ((cast[uint32](key) >> 16) & 255)) * 16777619
    h = (h ^ ((cast[uint32](key) >> 24) & 255)) * 16777619
    return h

def hash_str(key: Ptr[char]) -> uint32:
    """Hash function for strings (djb2)."""
    h: uint32 = 5381
    i: int32 = 0
    while key[i] != '\0':
        h = h * 33 + cast[uint32](key[i])
        i = i + 1
    return h

# ============================================================================
# Dictionary Core Functions
# ============================================================================

def dict_init(d: Ptr[int32]):
    """Initialize a new dictionary."""
    cap: int32 = DEFAULT_DICT_CAP

    keys: Ptr[int32] = cast[Ptr[int32]](alloc(cap * 4))
    values: Ptr[int32] = cast[Ptr[int32]](alloc(cap * 4))
    status: Ptr[uint8] = alloc(cap)

    # Clear status array
    i: int32 = 0
    while i < cap:
        status[i] = SLOT_EMPTY
        i = i + 1

    d[0] = cast[int32](keys)
    d[1] = cast[int32](values)
    d[2] = cast[int32](status)
    d[3] = 0  # size
    d[4] = cap

def dict_free(d: Ptr[int32]):
    """Free dictionary memory."""
    keys: Ptr[int32] = cast[Ptr[int32]](d[0])
    values: Ptr[int32] = cast[Ptr[int32]](d[1])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])

    if cast[uint32](keys) != 0:
        free(cast[Ptr[uint8]](keys))
    if cast[uint32](values) != 0:
        free(cast[Ptr[uint8]](values))
    if cast[uint32](status) != 0:
        free(status)

    d[0] = 0
    d[1] = 0
    d[2] = 0
    d[3] = 0
    d[4] = 0

def dict_len(d: Ptr[int32]) -> int32:
    """Return number of items in dictionary."""
    return d[3]

def dict_cap(d: Ptr[int32]) -> int32:
    """Return dictionary capacity."""
    return d[4]

# ============================================================================
# Integer Key Dictionary
# ============================================================================

def _int_dict_find_slot(d: Ptr[int32], key: int32) -> int32:
    """Find slot for key (returns index or -1 if not found)."""
    keys: Ptr[int32] = cast[Ptr[int32]](d[0])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    h: uint32 = hash_int(key)
    idx: int32 = cast[int32](h % cast[uint32](cap))
    start: int32 = idx

    while True:
        if status[idx] == SLOT_EMPTY:
            return -1
        if status[idx] == SLOT_OCCUPIED and keys[idx] == key:
            return idx
        idx = (idx + 1) % cap
        if idx == start:
            return -1

def _int_dict_find_insert_slot(d: Ptr[int32], key: int32) -> int32:
    """Find slot for insertion (empty/deleted or existing key)."""
    keys: Ptr[int32] = cast[Ptr[int32]](d[0])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    h: uint32 = hash_int(key)
    idx: int32 = cast[int32](h % cast[uint32](cap))
    first_deleted: int32 = -1
    start: int32 = idx

    while True:
        if status[idx] == SLOT_EMPTY:
            if first_deleted >= 0:
                return first_deleted
            return idx
        if status[idx] == SLOT_DELETED:
            if first_deleted < 0:
                first_deleted = idx
        elif keys[idx] == key:
            return idx
        idx = (idx + 1) % cap
        if idx == start:
            if first_deleted >= 0:
                return first_deleted
            return -1

def int_dict_resize(d: Ptr[int32]):
    """Resize dictionary to double capacity."""
    old_keys: Ptr[int32] = cast[Ptr[int32]](d[0])
    old_values: Ptr[int32] = cast[Ptr[int32]](d[1])
    old_status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    old_cap: int32 = d[4]

    new_cap: int32 = old_cap * 2 + 1
    new_keys: Ptr[int32] = cast[Ptr[int32]](alloc(new_cap * 4))
    new_values: Ptr[int32] = cast[Ptr[int32]](alloc(new_cap * 4))
    new_status: Ptr[uint8] = alloc(new_cap)

    # Initialize new status
    i: int32 = 0
    while i < new_cap:
        new_status[i] = SLOT_EMPTY
        i = i + 1

    # Update dict struct
    d[0] = cast[int32](new_keys)
    d[1] = cast[int32](new_values)
    d[2] = cast[int32](new_status)
    d[3] = 0  # Will re-count
    d[4] = new_cap

    # Re-insert all items
    i = 0
    while i < old_cap:
        if old_status[i] == SLOT_OCCUPIED:
            int_dict_set(d, old_keys[i], old_values[i])
        i = i + 1

    # Free old arrays
    free(cast[Ptr[uint8]](old_keys))
    free(cast[Ptr[uint8]](old_values))
    free(old_status)

def int_dict_set(d: Ptr[int32], key: int32, value: int32):
    """Set key-value pair in dictionary."""
    # Check if resize needed
    size: int32 = d[3]
    cap: int32 = d[4]
    if size * 100 >= cap * LOAD_FACTOR_THRESHOLD:
        int_dict_resize(d)

    idx: int32 = _int_dict_find_insert_slot(d, key)
    if idx < 0:
        return  # Table full (shouldn't happen with resize)

    keys: Ptr[int32] = cast[Ptr[int32]](d[0])
    values: Ptr[int32] = cast[Ptr[int32]](d[1])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])

    is_new: bool = status[idx] != SLOT_OCCUPIED
    keys[idx] = key
    values[idx] = value
    status[idx] = SLOT_OCCUPIED

    if is_new:
        d[3] = d[3] + 1

def int_dict_get(d: Ptr[int32], key: int32) -> int32:
    """Get value for key (returns 0 if not found)."""
    idx: int32 = _int_dict_find_slot(d, key)
    if idx < 0:
        return 0
    values: Ptr[int32] = cast[Ptr[int32]](d[1])
    return values[idx]

def int_dict_has(d: Ptr[int32], key: int32) -> bool:
    """Check if key exists in dictionary."""
    return _int_dict_find_slot(d, key) >= 0

def int_dict_del(d: Ptr[int32], key: int32) -> bool:
    """Delete key from dictionary. Returns True if key was found."""
    idx: int32 = _int_dict_find_slot(d, key)
    if idx < 0:
        return False

    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    status[idx] = SLOT_DELETED
    d[3] = d[3] - 1
    return True

# ============================================================================
# String Key Dictionary
# ============================================================================

def _str_dict_find_slot(d: Ptr[int32], key: Ptr[char]) -> int32:
    """Find slot for string key (returns index or -1 if not found)."""
    keys: Ptr[Ptr[char]] = cast[Ptr[Ptr[char]]](d[0])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    h: uint32 = hash_str(key)
    idx: int32 = cast[int32](h % cast[uint32](cap))
    start: int32 = idx

    while True:
        if status[idx] == SLOT_EMPTY:
            return -1
        if status[idx] == SLOT_OCCUPIED:
            if strcmp(keys[idx], key) == 0:
                return idx
        idx = (idx + 1) % cap
        if idx == start:
            return -1

def _str_dict_find_insert_slot(d: Ptr[int32], key: Ptr[char]) -> int32:
    """Find slot for string key insertion."""
    keys: Ptr[Ptr[char]] = cast[Ptr[Ptr[char]]](d[0])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    h: uint32 = hash_str(key)
    idx: int32 = cast[int32](h % cast[uint32](cap))
    first_deleted: int32 = -1
    start: int32 = idx

    while True:
        if status[idx] == SLOT_EMPTY:
            if first_deleted >= 0:
                return first_deleted
            return idx
        if status[idx] == SLOT_DELETED:
            if first_deleted < 0:
                first_deleted = idx
        elif strcmp(keys[idx], key) == 0:
            return idx
        idx = (idx + 1) % cap
        if idx == start:
            if first_deleted >= 0:
                return first_deleted
            return -1

def str_dict_resize(d: Ptr[int32]):
    """Resize string dictionary to double capacity."""
    old_keys: Ptr[Ptr[char]] = cast[Ptr[Ptr[char]]](d[0])
    old_values: Ptr[int32] = cast[Ptr[int32]](d[1])
    old_status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    old_cap: int32 = d[4]

    new_cap: int32 = old_cap * 2 + 1
    new_keys: Ptr[Ptr[char]] = cast[Ptr[Ptr[char]]](alloc(new_cap * 4))
    new_values: Ptr[int32] = cast[Ptr[int32]](alloc(new_cap * 4))
    new_status: Ptr[uint8] = alloc(new_cap)

    # Initialize new status
    i: int32 = 0
    while i < new_cap:
        new_status[i] = SLOT_EMPTY
        i = i + 1

    # Update dict struct
    d[0] = cast[int32](new_keys)
    d[1] = cast[int32](new_values)
    d[2] = cast[int32](new_status)
    d[3] = 0
    d[4] = new_cap

    # Re-insert all items
    i = 0
    while i < old_cap:
        if old_status[i] == SLOT_OCCUPIED:
            str_dict_set(d, old_keys[i], old_values[i])
        i = i + 1

    # Free old arrays
    free(cast[Ptr[uint8]](old_keys))
    free(cast[Ptr[uint8]](old_values))
    free(old_status)

def str_dict_set(d: Ptr[int32], key: Ptr[char], value: int32):
    """Set string key-value pair in dictionary."""
    # Check if resize needed
    size: int32 = d[3]
    cap: int32 = d[4]
    if size * 100 >= cap * LOAD_FACTOR_THRESHOLD:
        str_dict_resize(d)

    idx: int32 = _str_dict_find_insert_slot(d, key)
    if idx < 0:
        return

    keys: Ptr[Ptr[char]] = cast[Ptr[Ptr[char]]](d[0])
    values: Ptr[int32] = cast[Ptr[int32]](d[1])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])

    is_new: bool = status[idx] != SLOT_OCCUPIED
    keys[idx] = key
    values[idx] = value
    status[idx] = SLOT_OCCUPIED

    if is_new:
        d[3] = d[3] + 1

def str_dict_get(d: Ptr[int32], key: Ptr[char]) -> int32:
    """Get value for string key (returns 0 if not found)."""
    idx: int32 = _str_dict_find_slot(d, key)
    if idx < 0:
        return 0
    values: Ptr[int32] = cast[Ptr[int32]](d[1])
    return values[idx]

def str_dict_has(d: Ptr[int32], key: Ptr[char]) -> bool:
    """Check if string key exists in dictionary."""
    return _str_dict_find_slot(d, key) >= 0

def str_dict_del(d: Ptr[int32], key: Ptr[char]) -> bool:
    """Delete string key from dictionary. Returns True if found."""
    idx: int32 = _str_dict_find_slot(d, key)
    if idx < 0:
        return False

    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    status[idx] = SLOT_DELETED
    d[3] = d[3] - 1
    return True

# ============================================================================
# Dictionary Iteration
# ============================================================================

def dict_clear(d: Ptr[int32]):
    """Clear all items from dictionary."""
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    i: int32 = 0
    while i < cap:
        status[i] = SLOT_EMPTY
        i = i + 1

    d[3] = 0

def int_dict_keys(d: Ptr[int32], out: Ptr[int32]) -> int32:
    """Copy all keys to output array. Returns count."""
    keys: Ptr[int32] = cast[Ptr[int32]](d[0])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    count: int32 = 0
    i: int32 = 0
    while i < cap:
        if status[i] == SLOT_OCCUPIED:
            out[count] = keys[i]
            count = count + 1
        i = i + 1
    return count

def int_dict_values(d: Ptr[int32], out: Ptr[int32]) -> int32:
    """Copy all values to output array. Returns count."""
    values: Ptr[int32] = cast[Ptr[int32]](d[1])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    count: int32 = 0
    i: int32 = 0
    while i < cap:
        if status[i] == SLOT_OCCUPIED:
            out[count] = values[i]
            count = count + 1
        i = i + 1
    return count

def str_dict_keys(d: Ptr[int32], out: Ptr[Ptr[char]]) -> int32:
    """Copy all string keys to output array. Returns count."""
    keys: Ptr[Ptr[char]] = cast[Ptr[Ptr[char]]](d[0])
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    count: int32 = 0
    i: int32 = 0
    while i < cap:
        if status[i] == SLOT_OCCUPIED:
            out[count] = keys[i]
            count = count + 1
        i = i + 1
    return count

# ============================================================================
# Iteration Helper - get next valid index
# ============================================================================

def dict_next_idx(d: Ptr[int32], start: int32) -> int32:
    """Get next occupied slot index starting from start. Returns -1 if none."""
    status: Ptr[uint8] = cast[Ptr[uint8]](d[2])
    cap: int32 = d[4]

    i: int32 = start
    while i < cap:
        if status[i] == SLOT_OCCUPIED:
            return i
        i = i + 1
    return -1

def int_dict_key_at(d: Ptr[int32], idx: int32) -> int32:
    """Get key at internal index."""
    keys: Ptr[int32] = cast[Ptr[int32]](d[0])
    return keys[idx]

def int_dict_val_at(d: Ptr[int32], idx: int32) -> int32:
    """Get value at internal index."""
    values: Ptr[int32] = cast[Ptr[int32]](d[1])
    return values[idx]

def str_dict_key_at(d: Ptr[int32], idx: int32) -> Ptr[char]:
    """Get string key at internal index."""
    keys: Ptr[Ptr[char]] = cast[Ptr[Ptr[char]]](d[0])
    return keys[idx]
