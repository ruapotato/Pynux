# Pynux Memory Allocator
#
# Simple bump allocator for bare-metal ARM.
# Uses a fixed heap region in RAM.

# Heap region (fixed addresses for mps2-an385)
# RAM starts at 0x20000000, we use 16KB at 0x20010000 for heap
HEAP_START: uint32 = 0x20010000
HEAP_SIZE: uint32 = 0x4000  # 16KB

# Allocator state
heap_ptr: uint32 = 0
heap_end: uint32 = 0
heap_initialized: bool = False

# Allocation header (8 bytes)
HEADER_SIZE: int32 = 8

def heap_init():
    global heap_ptr, heap_end, heap_initialized
    heap_ptr = HEAP_START
    heap_end = HEAP_START + HEAP_SIZE
    heap_initialized = True

# Allocate memory (returns null on failure)
def alloc(size: int32) -> Ptr[uint8]:
    if not heap_initialized:
        heap_init()

    # Align size to 4 bytes
    aligned: int32 = (size + 3) & ~3
    total: int32 = aligned + HEADER_SIZE

    if heap_ptr + total > heap_end:
        return Ptr[uint8](0)  # Out of memory

    # Write header (size)
    header: Ptr[int32] = cast[Ptr[int32]](heap_ptr)
    header[0] = total
    header[1] = 1  # In use flag

    # Return pointer after header
    result: Ptr[uint8] = cast[Ptr[uint8]](heap_ptr + HEADER_SIZE)
    heap_ptr = heap_ptr + total

    return result

# Allocate zeroed memory
def calloc(count: int32, size: int32) -> Ptr[uint8]:
    total: int32 = count * size
    ptr: Ptr[uint8] = alloc(total)
    if cast[uint32](ptr) != 0:
        memset(ptr, 0, total)
    return ptr

# Free memory (currently a no-op - bump allocator doesn't free)
def free(ptr: Ptr[uint8]):
    # For a real implementation, mark block as free
    # and coalesce with neighbors
    pass

# Reallocate (allocate new + copy)
def realloc(ptr: Ptr[uint8], new_size: int32) -> Ptr[uint8]:
    if cast[uint32](ptr) == 0:
        return alloc(new_size)

    # Get old size from header
    header: Ptr[int32] = cast[Ptr[int32]](cast[uint32](ptr) - HEADER_SIZE)
    old_size: int32 = header[0] - HEADER_SIZE

    # Allocate new block
    new_ptr: Ptr[uint8] = alloc(new_size)
    if cast[uint32](new_ptr) == 0:
        return Ptr[uint8](0)

    # Copy old data
    copy_size: int32 = old_size
    if new_size < old_size:
        copy_size = new_size
    memcpy(new_ptr, ptr, copy_size)

    return new_ptr

# Memory operations
def memset(dst: Ptr[uint8], val: uint8, size: int32):
    i: int32 = 0
    while i < size:
        dst[i] = val
        i = i + 1

def memcpy(dst: Ptr[uint8], src: Ptr[uint8], size: int32):
    i: int32 = 0
    while i < size:
        dst[i] = src[i]
        i = i + 1

def memmove(dst: Ptr[uint8], src: Ptr[uint8], size: int32):
    if cast[uint32](dst) < cast[uint32](src):
        memcpy(dst, src, size)
    else:
        # Copy backwards
        i: int32 = size - 1
        while i >= 0:
            dst[i] = src[i]
            i = i - 1

def memcmp(a: Ptr[uint8], b: Ptr[uint8], size: int32) -> int32:
    i: int32 = 0
    while i < size:
        if a[i] != b[i]:
            return cast[int32](a[i]) - cast[int32](b[i])
        i = i + 1
    return 0
