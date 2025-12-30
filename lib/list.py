# Pynux Dynamic List Library
#
# Generic growable array implementation.

from lib.memory import alloc, free, realloc, memcpy

# List structure layout:
#   data: Ptr[T]     - Pointer to elements (offset 0)
#   len: int32       - Number of elements (offset 4)
#   cap: int32       - Capacity (offset 8)
#   elem_size: int32 - Size of each element (offset 12)
# Total: 16 bytes

LIST_DATA_OFFSET: int32 = 0
LIST_LEN_OFFSET: int32 = 4
LIST_CAP_OFFSET: int32 = 8
LIST_ELEM_SIZE_OFFSET: int32 = 12
LIST_STRUCT_SIZE: int32 = 16

DEFAULT_CAP: int32 = 8
GROWTH_FACTOR: int32 = 2

# Get list fields
def list_data(lst: Ptr[int32]) -> Ptr[uint8]:
    return cast[Ptr[uint8]](lst[0])

def list_len(lst: Ptr[int32]) -> int32:
    return lst[1]

def list_cap(lst: Ptr[int32]) -> int32:
    return lst[2]

def list_elem_size(lst: Ptr[int32]) -> int32:
    return lst[3]

# Initialize a new list
def list_init(lst: Ptr[int32], elem_size: int32):
    data: Ptr[uint8] = alloc(DEFAULT_CAP * elem_size)
    lst[0] = cast[int32](data)
    lst[1] = 0  # len
    lst[2] = DEFAULT_CAP  # cap
    lst[3] = elem_size

# Free list memory
def list_free(lst: Ptr[int32]):
    data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])
    if cast[uint32](data) != 0:
        free(data)
    lst[0] = 0
    lst[1] = 0
    lst[2] = 0

# Grow list capacity
def list_grow(lst: Ptr[int32]):
    old_cap: int32 = lst[2]
    new_cap: int32 = old_cap * GROWTH_FACTOR
    elem_size: int32 = lst[3]

    old_data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])
    new_data: Ptr[uint8] = alloc(new_cap * elem_size)

    if cast[uint32](new_data) != 0:
        memcpy(new_data, old_data, lst[1] * elem_size)
        free(old_data)
        lst[0] = cast[int32](new_data)
        lst[2] = new_cap

# Push element to end (takes pointer to element)
def list_push(lst: Ptr[int32], elem: Ptr[uint8]):
    if lst[1] >= lst[2]:
        list_grow(lst)

    elem_size: int32 = lst[3]
    data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])
    offset: int32 = lst[1] * elem_size

    memcpy(&data[offset], elem, elem_size)
    lst[1] = lst[1] + 1

# Pop element from end (returns pointer to element, or null)
def list_pop(lst: Ptr[int32]) -> Ptr[uint8]:
    if lst[1] == 0:
        return Ptr[uint8](0)

    lst[1] = lst[1] - 1
    elem_size: int32 = lst[3]
    data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])
    return &data[lst[1] * elem_size]

# Get element at index
def list_get(lst: Ptr[int32], index: int32) -> Ptr[uint8]:
    if index < 0 or index >= lst[1]:
        return Ptr[uint8](0)

    elem_size: int32 = lst[3]
    data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])
    return &data[index * elem_size]

# Set element at index
def list_set(lst: Ptr[int32], index: int32, elem: Ptr[uint8]):
    if index < 0 or index >= lst[1]:
        return

    elem_size: int32 = lst[3]
    data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])
    memcpy(&data[index * elem_size], elem, elem_size)

# Insert element at index
def list_insert(lst: Ptr[int32], index: int32, elem: Ptr[uint8]):
    if index < 0 or index > lst[1]:
        return

    if lst[1] >= lst[2]:
        list_grow(lst)

    elem_size: int32 = lst[3]
    data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])

    # Shift elements right
    i: int32 = lst[1]
    while i > index:
        memcpy(&data[i * elem_size], &data[(i - 1) * elem_size], elem_size)
        i = i - 1

    memcpy(&data[index * elem_size], elem, elem_size)
    lst[1] = lst[1] + 1

# Remove element at index
def list_remove(lst: Ptr[int32], index: int32):
    if index < 0 or index >= lst[1]:
        return

    elem_size: int32 = lst[3]
    data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])

    # Shift elements left
    i: int32 = index
    while i < lst[1] - 1:
        memcpy(&data[i * elem_size], &data[(i + 1) * elem_size], elem_size)
        i = i + 1

    lst[1] = lst[1] - 1

# Clear list (keep capacity)
def list_clear(lst: Ptr[int32]):
    lst[1] = 0

# Reverse list in place
def list_reverse(lst: Ptr[int32]):
    length: int32 = lst[1]
    if length < 2:
        return

    elem_size: int32 = lst[3]
    data: Ptr[uint8] = cast[Ptr[uint8]](lst[0])
    temp: Ptr[uint8] = alloc(elem_size)

    i: int32 = 0
    j: int32 = length - 1
    while i < j:
        memcpy(temp, &data[i * elem_size], elem_size)
        memcpy(&data[i * elem_size], &data[j * elem_size], elem_size)
        memcpy(&data[j * elem_size], temp, elem_size)
        i = i + 1
        j = j - 1

    free(temp)

# ============================================================================
# Specialized int32 list for convenience
# ============================================================================

def int_list_init(lst: Ptr[int32]):
    list_init(lst, 4)

def int_list_push(lst: Ptr[int32], val: int32):
    list_push(lst, cast[Ptr[uint8]](&val))

def int_list_get(lst: Ptr[int32], index: int32) -> int32:
    ptr: Ptr[int32] = cast[Ptr[int32]](list_get(lst, index))
    if cast[uint32](ptr) == 0:
        return 0
    return ptr[0]

def int_list_set(lst: Ptr[int32], index: int32, val: int32):
    list_set(lst, index, cast[Ptr[uint8]](&val))

# ============================================================================
# Specialized Ptr list (for string arrays, etc.)
# ============================================================================

def ptr_list_init(lst: Ptr[int32]):
    list_init(lst, 4)

def ptr_list_push(lst: Ptr[int32], ptr: Ptr[uint8]):
    val: int32 = cast[int32](ptr)
    list_push(lst, cast[Ptr[uint8]](&val))

def ptr_list_get(lst: Ptr[int32], index: int32) -> Ptr[uint8]:
    ptr: Ptr[int32] = cast[Ptr[int32]](list_get(lst, index))
    if cast[uint32](ptr) == 0:
        return Ptr[uint8](0)
    return cast[Ptr[uint8]](ptr[0])
