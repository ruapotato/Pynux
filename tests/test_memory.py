# Pynux Memory Management Tests
#
# Tests for heap allocation, deallocation, and memory operations.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, assert_lt,
                                   assert_not_null, assert_null,
                                   test_pass, test_fail)
from lib.memory import (heap_init, alloc, calloc, free, realloc,
                         memset, memcpy, memmove, memcmp,
                         heap_remaining, heap_total, heap_used)

# ============================================================================
# Allocation Tests
# ============================================================================

def test_basic_alloc():
    """Test basic memory allocation."""
    print_section("Basic Allocation")

    # Allocate small block
    ptr: Ptr[uint8] = alloc(16)
    assert_not_null(cast[Ptr[void]](ptr), "alloc 16 bytes")

    # Should be writable
    ptr[0] = 42
    assert_eq(cast[int32](ptr[0]), 42, "can write to allocated memory")

    free(ptr)

def test_alloc_various_sizes():
    """Test allocating various sizes."""
    # Small
    small: Ptr[uint8] = alloc(4)
    assert_not_null(cast[Ptr[void]](small), "alloc 4 bytes")

    # Medium
    medium: Ptr[uint8] = alloc(64)
    assert_not_null(cast[Ptr[void]](medium), "alloc 64 bytes")

    # Larger
    larger: Ptr[uint8] = alloc(256)
    assert_not_null(cast[Ptr[void]](larger), "alloc 256 bytes")

    # Clean up
    free(small)
    free(medium)
    free(larger)

def test_alloc_zero():
    """Test allocating zero bytes."""
    ptr: Ptr[uint8] = alloc(0)
    # Implementation may return null or small block
    test_pass("alloc(0) doesn't crash")

    if ptr != Ptr[uint8](0):
        free(ptr)

def test_multiple_allocs():
    """Test multiple allocations."""
    ptrs: Array[10, Ptr[uint8]]
    i: int32 = 0

    # Allocate 10 blocks
    while i < 10:
        ptrs[i] = alloc(32)
        i = i + 1

    # All should be valid
    all_valid: bool = True
    i = 0
    while i < 10:
        if ptrs[i] == Ptr[uint8](0):
            all_valid = False
        i = i + 1

    assert_true(all_valid, "allocate 10 blocks")

    # All should be distinct addresses
    all_distinct: bool = True
    i = 0
    while i < 10 and all_distinct:
        j: int32 = i + 1
        while j < 10:
            if cast[uint32](ptrs[i]) == cast[uint32](ptrs[j]):
                all_distinct = False
            j = j + 1
        i = i + 1

    assert_true(all_distinct, "all addresses distinct")

    # Free all
    i = 0
    while i < 10:
        if ptrs[i] != Ptr[uint8](0):
            free(ptrs[i])
        i = i + 1

# ============================================================================
# Calloc Tests
# ============================================================================

def test_calloc():
    """Test calloc zero-initializes memory."""
    print_section("Calloc")

    # Allocate and check zeroed
    ptr: Ptr[uint8] = calloc(16, 1)
    assert_not_null(cast[Ptr[void]](ptr), "calloc 16 bytes")

    # All bytes should be 0
    all_zero: bool = True
    i: int32 = 0
    while i < 16:
        if ptr[i] != 0:
            all_zero = False
        i = i + 1

    assert_true(all_zero, "calloc zeroes memory")

    free(ptr)

def test_calloc_array():
    """Test calloc for array allocation."""
    # Allocate array of 10 int32s (40 bytes)
    ptr: Ptr[uint8] = calloc(10, 4)
    assert_not_null(cast[Ptr[void]](ptr), "calloc array")

    # Cast to int32 pointer and check zeros
    int_ptr: Ptr[int32] = cast[Ptr[int32]](ptr)
    all_zero: bool = True
    i: int32 = 0
    while i < 10:
        if int_ptr[i] != 0:
            all_zero = False
        i = i + 1

    assert_true(all_zero, "calloc array zeroed")

    free(ptr)

# ============================================================================
# Free Tests
# ============================================================================

def test_free():
    """Test memory deallocation."""
    print_section("Free")

    remaining_before: int32 = heap_remaining()

    ptr: Ptr[uint8] = alloc(100)
    assert_not_null(cast[Ptr[void]](ptr), "alloc for free test")

    remaining_during: int32 = heap_remaining()

    free(ptr)

    remaining_after: int32 = heap_remaining()

    # Should have less memory during allocation
    assert_lt(remaining_during, remaining_before, "alloc reduces free memory")

    # Should recover after free (might not be exact due to fragmentation)
    assert_gt(remaining_after, remaining_during, "free increases free memory")

def test_free_null():
    """Test freeing null pointer."""
    free(Ptr[uint8](0))
    test_pass("free(null) doesn't crash")

def test_alloc_after_free():
    """Test that freed memory can be reused."""
    ptr1: Ptr[uint8] = alloc(64)
    addr1: uint32 = cast[uint32](ptr1)
    free(ptr1)

    ptr2: Ptr[uint8] = alloc(64)
    addr2: uint32 = cast[uint32](ptr2)

    # May or may not be same address, but both should be valid
    assert_not_null(cast[Ptr[void]](ptr2), "alloc after free works")

    free(ptr2)

# ============================================================================
# Realloc Tests
# ============================================================================

def test_realloc_grow():
    """Test realloc to larger size."""
    print_section("Realloc")

    # Allocate initial
    ptr: Ptr[uint8] = alloc(16)
    ptr[0] = 'A'
    ptr[15] = 'B'

    # Grow
    new_ptr: Ptr[uint8] = realloc(ptr, 32)
    assert_not_null(cast[Ptr[void]](new_ptr), "realloc grow")

    # Original data should be preserved
    data_ok: bool = (new_ptr[0] == 'A' and new_ptr[15] == 'B')
    assert_true(data_ok, "realloc preserves data")

    # Should be able to use new space
    new_ptr[31] = 'C'
    assert_eq(cast[int32](new_ptr[31]), cast[int32]('C'), "can use new space")

    free(new_ptr)

def test_realloc_shrink():
    """Test realloc to smaller size."""
    ptr: Ptr[uint8] = alloc(64)
    ptr[0] = 'X'
    ptr[31] = 'Y'

    # Shrink
    new_ptr: Ptr[uint8] = realloc(ptr, 32)
    assert_not_null(cast[Ptr[void]](new_ptr), "realloc shrink")

    # Data within new size should be preserved
    data_ok: bool = (new_ptr[0] == 'X' and new_ptr[31] == 'Y')
    assert_true(data_ok, "realloc shrink preserves data")

    free(new_ptr)

def test_realloc_null():
    """Test realloc on null acts like alloc."""
    ptr: Ptr[uint8] = realloc(Ptr[uint8](0), 32)
    assert_not_null(cast[Ptr[void]](ptr), "realloc(null) allocates")

    free(ptr)

# ============================================================================
# Memory Operation Tests
# ============================================================================

def test_memset():
    """Test memset fills memory."""
    print_section("Memory Operations")

    buf: Array[16, uint8]

    # Fill with pattern
    memset(&buf[0], 0xAB, 16)

    all_set: bool = True
    i: int32 = 0
    while i < 16:
        if buf[i] != 0xAB:
            all_set = False
        i = i + 1

    assert_true(all_set, "memset fills correctly")

def test_memset_zero():
    """Test memset to zero."""
    buf: Array[8, uint8]
    buf[0] = 0xFF
    buf[7] = 0xFF

    memset(&buf[0], 0, 8)

    all_zero: bool = (buf[0] == 0 and buf[7] == 0)
    assert_true(all_zero, "memset to 0 works")

def test_memcpy():
    """Test memcpy copies data."""
    src: Array[8, uint8]
    dst: Array[8, uint8]

    src[0] = 'H'
    src[1] = 'E'
    src[2] = 'L'
    src[3] = 'L'
    src[4] = 'O'

    memcpy(&dst[0], &src[0], 5)

    matched: bool = (dst[0] == 'H' and dst[1] == 'E' and
                   dst[2] == 'L' and dst[3] == 'L' and dst[4] == 'O')
    assert_true(matched, "memcpy copies data")

def test_memmove_overlap():
    """Test memmove handles overlapping regions."""
    buf: Array[16, uint8]
    buf[0] = 'A'
    buf[1] = 'B'
    buf[2] = 'C'
    buf[3] = 'D'
    buf[4] = 'E'

    # Move overlapping region: ABCDE -> xxABC (shift right by 2)
    memmove(&buf[2], &buf[0], 5)

    # buf should now be: A B A B C D E
    result_ok: bool = (buf[2] == 'A' and buf[3] == 'B' and buf[4] == 'C')
    assert_true(result_ok, "memmove handles overlap")

def test_memcmp():
    """Test memcmp comparison."""
    a: Array[4, uint8]
    b: Array[4, uint8]

    a[0] = 'A'
    a[1] = 'B'
    a[2] = 'C'
    a[3] = '\0'

    b[0] = 'A'
    b[1] = 'B'
    b[2] = 'C'
    b[3] = '\0'

    # Equal
    result: int32 = memcmp(&a[0], &b[0], 4)
    assert_eq(result, 0, "memcmp equal returns 0")

    # Make different
    b[2] = 'X'
    result = memcmp(&a[0], &b[0], 4)
    assert_neq(result, 0, "memcmp different returns non-0")

# ============================================================================
# Heap Statistics Tests
# ============================================================================

def test_heap_stats():
    """Test heap statistics."""
    print_section("Heap Statistics")

    total: int32 = heap_total()
    assert_gt(total, 0, "heap_total > 0")

    remaining: int32 = heap_remaining()
    assert_gt(remaining, 0, "heap_remaining > 0")

    used: int32 = heap_used()
    assert_gte(used, 0, "heap_used >= 0")

    # Remaining + used should <= total
    sum: int32 = remaining + used
    # Note: might not be exact due to metadata overhead
    if sum <= total + 1024:  # Allow some overhead
        test_pass("heap stats consistent")
    else:
        test_fail("heap stats inconsistent")

def test_heap_usage_tracking():
    """Test that heap usage is tracked."""
    remaining_before: int32 = heap_remaining()

    # Allocate a chunk
    ptr: Ptr[uint8] = alloc(1024)

    remaining_after: int32 = heap_remaining()

    # Should have less remaining
    diff: int32 = remaining_before - remaining_after
    assert_gte(diff, 1024, "heap tracks allocation")

    free(ptr)

# ============================================================================
# Intuitive API Tests
# ============================================================================

def test_intuitive_memory_api():
    """Test that memory API is intuitive."""
    print_section("Intuitive Memory API")

    # alloc returns valid pointer
    ptr: Ptr[uint8] = alloc(32)
    if ptr != Ptr[uint8](0):
        test_pass("alloc returns valid pointer")
    else:
        test_fail("alloc should return pointer")
        return

    # Can write to allocated memory
    ptr[0] = 123
    if ptr[0] == 123:
        test_pass("can use allocated memory")
    else:
        test_fail("should be able to write")

    # realloc preserves data
    ptr[0] = 99
    new_ptr: Ptr[uint8] = realloc(ptr, 64)
    if new_ptr[0] == 99:
        test_pass("realloc preserves data")
    else:
        test_fail("realloc should preserve")

    # free doesn't crash
    free(new_ptr)
    test_pass("free works")

    # calloc returns zeroed memory
    ptr = calloc(8, 1)
    all_zero: bool = True
    i: int32 = 0
    while i < 8:
        if ptr[i] != 0:
            all_zero = False
        i = i + 1

    if all_zero:
        test_pass("calloc returns zeroed memory")
    else:
        test_fail("calloc should zero memory")

    free(ptr)

# ============================================================================
# Stress Tests
# ============================================================================

def test_alloc_stress():
    """Stress test many allocations."""
    print_section("Stress Tests")

    ptrs: Array[50, Ptr[uint8]]
    i: int32 = 0

    # Allocate many small blocks
    while i < 50:
        ptrs[i] = alloc(16)
        i = i + 1

    # Count successful
    count: int32 = 0
    i = 0
    while i < 50:
        if ptrs[i] != Ptr[uint8](0):
            count = count + 1
        i = i + 1

    print_str("  (allocated ")
    print_int(count)
    print_str(" of 50)")
    print_newline()

    assert_gt(count, 0, "stress alloc succeeds")

    # Free all
    i = 0
    while i < 50:
        if ptrs[i] != Ptr[uint8](0):
            free(ptrs[i])
        i = i + 1

    test_pass("stress free succeeds")

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    print_str("\n=== Pynux Memory Management Tests ===\n")

    heap_init()

    test_basic_alloc()
    test_alloc_various_sizes()
    test_alloc_zero()
    test_multiple_allocs()

    test_calloc()
    test_calloc_array()

    test_free()
    test_free_null()
    test_alloc_after_free()

    test_realloc_grow()
    test_realloc_shrink()
    test_realloc_null()

    test_memset()
    test_memset_zero()
    test_memcpy()
    test_memmove_overlap()
    test_memcmp()

    test_heap_stats()
    test_heap_usage_tracking()

    test_intuitive_memory_api()

    test_alloc_stress()

    return print_results()
