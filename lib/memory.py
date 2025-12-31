# Pynux Memory Allocator
#
# Free-list based allocator for bare-metal ARM.
# Supports allocation, deallocation, and coalescing.

# Heap region (fixed addresses for mps2-an385)
# RAM starts at 0x20000000, we use 16KB at 0x20010000 for heap
HEAP_START: uint32 = 0x20010000
HEAP_SIZE: uint32 = 0x4000  # 16KB

# Allocator state
heap_initialized: bool = False

# Allocation header (8 bytes)
# header[0] = size (including header)
# header[1] = in_use flag (1 = in use, 0 = free)
HEADER_SIZE: int32 = 8

# Free list head pointer (stored as uint32 for address math)
free_list_head: uint32 = 0

def heap_init():
    global heap_initialized, free_list_head
    # Initialize with one big free block spanning entire heap
    header: Ptr[int32] = cast[Ptr[int32]](HEAP_START)
    header[0] = cast[int32](HEAP_SIZE)  # Size of entire heap
    header[1] = 0  # Free
    free_list_head = HEAP_START
    heap_initialized = True

# Find a free block of at least 'size' bytes (first-fit)
def find_free_block(size: int32) -> uint32:
    addr: uint32 = HEAP_START
    heap_end: uint32 = HEAP_START + HEAP_SIZE
    while addr < heap_end:
        header: Ptr[int32] = cast[Ptr[int32]](addr)
        block_size: int32 = header[0]
        in_use: int32 = header[1]
        if block_size <= 0:
            break  # Corrupted or end of heap
        if in_use == 0 and block_size >= size:
            return addr
        addr = addr + cast[uint32](block_size)
    return 0  # No suitable block found

# Split a block if it's significantly larger than needed
def split_block(addr: uint32, needed: int32):
    header: Ptr[int32] = cast[Ptr[int32]](addr)
    block_size: int32 = header[0]
    # Only split if remaining space can hold another block (header + some data)
    min_split: int32 = HEADER_SIZE + 16  # Minimum useful block
    if block_size >= needed + min_split:
        # Create new free block after this one
        new_addr: uint32 = addr + cast[uint32](needed)
        new_header: Ptr[int32] = cast[Ptr[int32]](new_addr)
        new_header[0] = block_size - needed
        new_header[1] = 0  # Free
        # Update original block size
        header[0] = needed

# Allocate memory (returns null on failure)
def alloc(size: int32) -> Ptr[uint8]:
    state: int32 = critical_enter()

    if not heap_initialized:
        heap_init()

    # Align size to 4 bytes
    aligned: int32 = (size + 3) & ~3
    total: int32 = aligned + HEADER_SIZE

    # Find a free block
    addr: uint32 = find_free_block(total)
    if addr == 0:
        critical_exit(state)
        return Ptr[uint8](0)  # Out of memory

    # Split block if needed
    split_block(addr, total)

    # Mark as in use
    header: Ptr[int32] = cast[Ptr[int32]](addr)
    header[1] = 1  # In use

    # Return pointer after header
    result: Ptr[uint8] = cast[Ptr[uint8]](addr + HEADER_SIZE)

    critical_exit(state)
    return result

# Allocate zeroed memory
def calloc(count: int32, size: int32) -> Ptr[uint8]:
    total: int32 = count * size
    ptr: Ptr[uint8] = alloc(total)
    if cast[uint32](ptr) != 0:
        memset(ptr, 0, total)
    return ptr

# Coalesce adjacent free blocks
def coalesce():
    addr: uint32 = HEAP_START
    heap_end: uint32 = HEAP_START + HEAP_SIZE
    while addr < heap_end:
        header: Ptr[int32] = cast[Ptr[int32]](addr)
        block_size: int32 = header[0]
        in_use: int32 = header[1]
        if block_size <= 0:
            break
        if in_use == 0:
            # Try to merge with next block if it's also free
            next_addr: uint32 = addr + cast[uint32](block_size)
            while next_addr < heap_end:
                next_header: Ptr[int32] = cast[Ptr[int32]](next_addr)
                next_size: int32 = next_header[0]
                next_in_use: int32 = next_header[1]
                if next_size <= 0:
                    break
                if next_in_use == 0:
                    # Merge: add next block's size to current
                    header[0] = header[0] + next_size
                    next_addr = next_addr + cast[uint32](next_size)
                else:
                    break
        addr = addr + cast[uint32](header[0])

# Free memory
def free(ptr: Ptr[uint8]):
    if cast[uint32](ptr) == 0:
        return

    state: int32 = critical_enter()

    # Validate pointer is above HEADER_SIZE to prevent underflow
    ptr_val: uint32 = cast[uint32](ptr)
    if ptr_val < HEADER_SIZE:
        critical_exit(state)
        return

    # Get header
    addr: uint32 = ptr_val - HEADER_SIZE
    header: Ptr[int32] = cast[Ptr[int32]](addr)

    # Validate pointer is in heap range
    if addr < HEAP_START or addr >= HEAP_START + HEAP_SIZE:
        critical_exit(state)
        return

    # Validate this is actually an allocated block (not already free or corrupted)
    if header[1] != 1:
        critical_exit(state)
        return  # Already free or invalid

    # Validate block size is reasonable
    block_size: int32 = header[0]
    if block_size <= HEADER_SIZE or block_size > cast[int32](HEAP_SIZE):
        critical_exit(state)
        return  # Corrupted header

    # Mark as free
    header[1] = 0

    # Coalesce adjacent free blocks
    coalesce()

    critical_exit(state)

# Reallocate (smart: don't copy if shrinking)
def realloc(ptr: Ptr[uint8], new_size: int32) -> Ptr[uint8]:
    if cast[uint32](ptr) == 0:
        return alloc(new_size)

    if new_size <= 0:
        free(ptr)
        return Ptr[uint8](0)

    state: int32 = critical_enter()

    # Get old size from header
    header: Ptr[int32] = cast[Ptr[int32]](cast[uint32](ptr) - HEADER_SIZE)
    old_total: int32 = header[0]
    old_size: int32 = old_total - HEADER_SIZE

    # Align new size
    aligned_new: int32 = (new_size + 3) & ~3
    new_total: int32 = aligned_new + HEADER_SIZE

    # If shrinking or same size, just update block (maybe split)
    if new_total <= old_total:
        split_block(cast[uint32](ptr) - HEADER_SIZE, new_total)
        critical_exit(state)
        return ptr

    critical_exit(state)

    # Growing: need to allocate new block
    new_ptr: Ptr[uint8] = alloc(new_size)
    if cast[uint32](new_ptr) == 0:
        return Ptr[uint8](0)

    # Copy old data
    memcpy(new_ptr, ptr, old_size)

    # Free old block
    free(ptr)

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

# Get remaining heap space (approximate - counts free blocks)
def heap_remaining() -> int32:
    state: int32 = critical_enter()
    remaining: int32 = 0
    addr: uint32 = HEAP_START
    heap_end: uint32 = HEAP_START + HEAP_SIZE
    while addr < heap_end:
        header: Ptr[int32] = cast[Ptr[int32]](addr)
        block_size: int32 = header[0]
        in_use: int32 = header[1]
        if block_size <= 0:
            break
        if in_use == 0:
            remaining = remaining + block_size - HEADER_SIZE
        addr = addr + cast[uint32](block_size)
    critical_exit(state)
    return remaining

# Get heap size
def heap_total() -> int32:
    return cast[int32](HEAP_SIZE)

# Get used heap space
def heap_used() -> int32:
    state: int32 = critical_enter()
    used: int32 = 0
    addr: uint32 = HEAP_START
    heap_end: uint32 = HEAP_START + HEAP_SIZE
    while addr < heap_end:
        header: Ptr[int32] = cast[Ptr[int32]](addr)
        block_size: int32 = header[0]
        in_use: int32 = header[1]
        if block_size <= 0:
            break
        if in_use == 1:
            used = used + block_size
        addr = addr + cast[uint32](block_size)
    critical_exit(state)
    return used
