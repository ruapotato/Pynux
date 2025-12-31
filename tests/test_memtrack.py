# Pynux Memory Tracking Tests
#
# Tests for the memory allocation tracking module.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, assert_lt,
                                   test_pass, test_fail)
from lib.memtrack import (memtrack_init, memtrack_alloc, memtrack_free,
                          memtrack_enable, memtrack_disable, memtrack_is_enabled,
                          memtrack_get_total, memtrack_get_peak, memtrack_get_current,
                          memtrack_get_count, memtrack_get_size, memtrack_get_tag,
                          memtrack_check_leaks, memtrack_reset)
from lib.string import strcmp

# Simulated memory buffer for testing
_test_mem: Array[1024, uint8]

# ============================================================================
# Initialization Tests
# ============================================================================

def test_memtrack_init():
    """Test memtrack initialization."""
    print_section("Memtrack Initialization")

    memtrack_init()
    test_pass("memtrack_init completes")

    # Should be enabled after init
    assert_true(memtrack_is_enabled(), "enabled after init")

    # All stats should be 0
    assert_eq(memtrack_get_total(), 0, "total is 0")
    assert_eq(memtrack_get_peak(), 0, "peak is 0")
    assert_eq(memtrack_get_current(), 0, "current is 0")
    assert_eq(memtrack_get_count(), 0, "count is 0")

def test_memtrack_enable_disable():
    """Test enable/disable."""
    memtrack_init()

    memtrack_disable()
    assert_false(memtrack_is_enabled(), "disabled after disable")

    memtrack_enable()
    assert_true(memtrack_is_enabled(), "enabled after enable")

# ============================================================================
# Basic Tracking Tests
# ============================================================================

def test_memtrack_alloc_basic():
    """Test basic allocation tracking."""
    print_section("Basic Tracking")

    memtrack_init()

    # Track an allocation
    ptr: Ptr[uint8] = &_test_mem[0]
    memtrack_alloc(ptr, 256, "test")

    # Check stats
    assert_eq(memtrack_get_count(), 1, "1 allocation tracked")
    assert_eq(memtrack_get_total(), 256, "total is 256")
    assert_eq(memtrack_get_current(), 256, "current is 256")
    assert_eq(memtrack_get_peak(), 256, "peak is 256")

def test_memtrack_free_basic():
    """Test basic free tracking."""
    memtrack_init()

    ptr: Ptr[uint8] = &_test_mem[0]
    memtrack_alloc(ptr, 128, "free_test")

    # Free it
    memtrack_free(ptr)

    # Current should be 0, but total and peak remain
    assert_eq(memtrack_get_count(), 0, "0 active allocations")
    assert_eq(memtrack_get_current(), 0, "current is 0 after free")
    assert_eq(memtrack_get_total(), 128, "total is still 128")
    assert_eq(memtrack_get_peak(), 128, "peak is still 128")

def test_memtrack_multiple_allocs():
    """Test multiple allocations."""
    print_section("Multiple Allocations")

    memtrack_init()

    ptr1: Ptr[uint8] = &_test_mem[0]
    ptr2: Ptr[uint8] = &_test_mem[256]
    ptr3: Ptr[uint8] = &_test_mem[512]

    memtrack_alloc(ptr1, 100, "alloc1")
    memtrack_alloc(ptr2, 200, "alloc2")
    memtrack_alloc(ptr3, 300, "alloc3")

    assert_eq(memtrack_get_count(), 3, "3 allocations")
    assert_eq(memtrack_get_total(), 600, "total is 600")
    assert_eq(memtrack_get_current(), 600, "current is 600")
    assert_eq(memtrack_get_peak(), 600, "peak is 600")

    # Free one
    memtrack_free(ptr2)

    assert_eq(memtrack_get_count(), 2, "2 allocations after free")
    assert_eq(memtrack_get_current(), 400, "current is 400")
    assert_eq(memtrack_get_peak(), 600, "peak still 600")

# ============================================================================
# Peak Tracking Tests
# ============================================================================

def test_memtrack_peak():
    """Test peak memory tracking."""
    print_section("Peak Tracking")

    memtrack_init()

    ptr1: Ptr[uint8] = &_test_mem[0]
    ptr2: Ptr[uint8] = &_test_mem[256]

    # Allocate 256
    memtrack_alloc(ptr1, 256, "peak1")
    assert_eq(memtrack_get_peak(), 256, "peak is 256")

    # Allocate more (512 total)
    memtrack_alloc(ptr2, 256, "peak2")
    assert_eq(memtrack_get_peak(), 512, "peak is 512")

    # Free one (256 current)
    memtrack_free(ptr1)
    assert_eq(memtrack_get_peak(), 512, "peak still 512")
    assert_eq(memtrack_get_current(), 256, "current is 256")

    # Free other (0 current)
    memtrack_free(ptr2)
    assert_eq(memtrack_get_peak(), 512, "peak still 512")
    assert_eq(memtrack_get_current(), 0, "current is 0")

# ============================================================================
# Tag and Size Query Tests
# ============================================================================

def test_memtrack_get_size():
    """Test getting allocation size."""
    print_section("Size Query")

    memtrack_init()

    ptr: Ptr[uint8] = &_test_mem[0]
    memtrack_alloc(ptr, 512, "sized")

    size: int32 = memtrack_get_size(ptr)
    assert_eq(size, 512, "get_size returns 512")

    # Unknown pointer returns 0
    unknown: Ptr[uint8] = &_test_mem[900]
    size = memtrack_get_size(unknown)
    assert_eq(size, 0, "unknown ptr returns 0")

def test_memtrack_get_tag():
    """Test getting allocation tag."""
    memtrack_init()

    ptr: Ptr[uint8] = &_test_mem[0]
    memtrack_alloc(ptr, 64, "mytag")

    tag: Ptr[char] = memtrack_get_tag(ptr)
    result: int32 = strcmp(tag, "mytag")
    assert_eq(result, 0, "tag is 'mytag'")

# ============================================================================
# Disabled State Tests
# ============================================================================

def test_memtrack_disabled():
    """Test tracking when disabled."""
    print_section("Disabled State")

    memtrack_init()
    memtrack_disable()

    ptr: Ptr[uint8] = &_test_mem[0]
    memtrack_alloc(ptr, 100, "disabled")

    # Should not have tracked
    assert_eq(memtrack_get_count(), 0, "no tracking when disabled")
    assert_eq(memtrack_get_total(), 0, "total is 0")

# ============================================================================
# Leak Detection Tests
# ============================================================================

def test_memtrack_check_leaks():
    """Test leak detection."""
    print_section("Leak Detection")

    memtrack_init()

    # No leaks initially
    leaks: int32 = memtrack_check_leaks()
    assert_eq(leaks, 0, "no leaks initially")

    # Create some allocations
    ptr1: Ptr[uint8] = &_test_mem[0]
    ptr2: Ptr[uint8] = &_test_mem[128]
    memtrack_alloc(ptr1, 64, "leak1")
    memtrack_alloc(ptr2, 64, "leak2")

    # Should report 2 leaks
    leaks = memtrack_check_leaks()
    assert_eq(leaks, 2, "2 leaks detected")

    # Free one
    memtrack_free(ptr1)
    leaks = memtrack_check_leaks()
    assert_eq(leaks, 1, "1 leak after partial free")

    # Free other
    memtrack_free(ptr2)
    leaks = memtrack_check_leaks()
    assert_eq(leaks, 0, "no leaks after all freed")

# ============================================================================
# Reset Tests
# ============================================================================

def test_memtrack_reset():
    """Test resetting tracking data."""
    print_section("Reset")

    memtrack_init()

    ptr: Ptr[uint8] = &_test_mem[0]
    memtrack_alloc(ptr, 256, "reset_test")

    assert_gt(memtrack_get_total(), 0, "has data before reset")

    memtrack_reset()

    assert_eq(memtrack_get_total(), 0, "total 0 after reset")
    assert_eq(memtrack_get_peak(), 0, "peak 0 after reset")
    assert_eq(memtrack_get_current(), 0, "current 0 after reset")
    assert_eq(memtrack_get_count(), 0, "count 0 after reset")

# ============================================================================
# Null Pointer Tests
# ============================================================================

def test_memtrack_null_ptr():
    """Test handling of null pointers."""
    print_section("Null Pointer")

    memtrack_init()

    # Null alloc should be ignored
    memtrack_alloc(cast[Ptr[uint8]](0), 100, "null")
    assert_eq(memtrack_get_count(), 0, "null alloc ignored")

    # Null free should be ignored
    memtrack_free(cast[Ptr[uint8]](0))
    test_pass("null free ignored")

# ============================================================================
# Slot Reuse Tests
# ============================================================================

def test_memtrack_slot_reuse():
    """Test that freed slots can be reused."""
    print_section("Slot Reuse")

    memtrack_init()

    # Allocate and free many times
    ptr: Ptr[uint8] = &_test_mem[0]

    i: int32 = 0
    while i < 10:
        memtrack_alloc(ptr, 32, "reuse")
        memtrack_free(ptr)
        i = i + 1

    # Should have 0 active allocations
    assert_eq(memtrack_get_count(), 0, "0 active after alloc/free cycle")

    # Total should be 320 (10 * 32)
    assert_eq(memtrack_get_total(), 320, "total is 320")

# ============================================================================
# Main
# ============================================================================

def test_memtrack_main() -> int32:
    print_str("\n=== Pynux Memory Tracking Tests ===\n")

    test_memtrack_init()
    test_memtrack_enable_disable()

    test_memtrack_alloc_basic()
    test_memtrack_free_basic()
    test_memtrack_multiple_allocs()

    test_memtrack_peak()

    test_memtrack_get_size()
    test_memtrack_get_tag()

    test_memtrack_disabled()

    test_memtrack_check_leaks()

    test_memtrack_reset()

    test_memtrack_null_ptr()

    test_memtrack_slot_reuse()

    return print_results()
