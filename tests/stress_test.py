# Pynux Stress Test
#
# Tests emulator limits: memory, computation, loops, recursion.

from lib.io import print_str, print_int, print_newline, uart_init
from lib.memory import heap_remaining, heap_used, alloc, free
from lib.math import isqrt, pow_int, rand, srand

# ============================================================================
# Test Results
# ============================================================================

_passed: int32 = 0
_failed: int32 = 0

def pass_test(name: Ptr[char]):
    global _passed
    print_str("[PASS] ")
    print_str(name)
    print_newline()
    _passed = _passed + 1

def fail_test(name: Ptr[char]):
    global _failed
    print_str("[FAIL] ")
    print_str(name)
    print_newline()
    _failed = _failed + 1

# ============================================================================
# Memory Stress Tests
# ============================================================================

def test_memory_alloc_free():
    """Test repeated allocation and freeing."""
    print_str("\n=== Memory Alloc/Free Stress ===\n")

    initial: int32 = heap_remaining()
    print_str("Initial heap: ")
    print_int(initial)
    print_str(" bytes\n")

    # Allocate and free 100 times
    i: int32 = 0
    success: bool = True
    while i < 100:
        ptr: Ptr[uint8] = alloc(1024)
        if ptr == cast[Ptr[uint8]](0):
            success = False
        else:
            free(ptr)
        i = i + 1

    final: int32 = heap_remaining()
    print_str("Final heap: ")
    print_int(final)
    print_str(" bytes\n")

    # Should have same memory (no leaks)
    if success and final >= initial - 100:
        pass_test("alloc/free cycle x100")
    else:
        fail_test("alloc/free cycle x100")

def test_memory_fragmentation():
    """Test memory with fragmented allocations."""
    print_str("\n=== Memory Fragmentation Test ===\n")

    # Allocate 10 blocks of different sizes
    blocks: Array[10, Ptr[uint8]]
    sizes: Array[10, int32]

    sizes[0] = 64
    sizes[1] = 128
    sizes[2] = 32
    sizes[3] = 256
    sizes[4] = 16
    sizes[5] = 512
    sizes[6] = 48
    sizes[7] = 192
    sizes[8] = 80
    sizes[9] = 144

    i: int32 = 0
    all_ok: bool = True
    while i < 10:
        blocks[i] = alloc(sizes[i])
        if blocks[i] == cast[Ptr[uint8]](0):
            all_ok = False
        i = i + 1

    if all_ok:
        pass_test("allocate 10 varied blocks")
    else:
        fail_test("allocate 10 varied blocks")

    # Free every other block
    i = 0
    while i < 10:
        if (i % 2) == 0:
            free(blocks[i])
        i = i + 1

    # Allocate new blocks in gaps
    new_blocks: Array[5, Ptr[uint8]]
    i = 0
    all_ok = True
    while i < 5:
        new_blocks[i] = alloc(50)
        if new_blocks[i] == cast[Ptr[uint8]](0):
            all_ok = False
        i = i + 1

    if all_ok:
        pass_test("reuse fragmented memory")
    else:
        fail_test("reuse fragmented memory")

    # Cleanup
    i = 0
    while i < 10:
        if (i % 2) == 1:
            free(blocks[i])
        i = i + 1
    i = 0
    while i < 5:
        free(new_blocks[i])
        i = i + 1

# ============================================================================
# Computation Stress Tests
# ============================================================================

def test_heavy_math():
    """Test computationally intensive math."""
    print_str("\n=== Heavy Math Test ===\n")

    # Calculate 1000 square roots
    sum: int32 = 0
    i: int32 = 1
    while i <= 1000:
        sum = sum + isqrt(i * 1000)
        i = i + 1

    print_str("Sum of 1000 isqrt: ")
    print_int(sum)
    print_newline()

    if sum > 0:
        pass_test("1000 square roots")
    else:
        fail_test("1000 square roots")

def test_power_calculations():
    """Test power function."""
    print_str("\n=== Power Calculations ===\n")

    # Calculate 2^20
    result: int32 = pow_int(2, 20)
    print_str("2^20 = ")
    print_int(result)
    print_newline()

    if result == 1048576:
        pass_test("2^20 = 1048576")
    else:
        fail_test("2^20 = 1048576")

    # Calculate 3^10
    result = pow_int(3, 10)
    print_str("3^10 = ")
    print_int(result)
    print_newline()

    if result == 59049:
        pass_test("3^10 = 59049")
    else:
        fail_test("3^10 = 59049")

def test_random_sequence():
    """Test random number generator with large sequence."""
    print_str("\n=== Random Sequence Test ===\n")

    srand(42)

    # Generate 10000 random numbers, count distribution
    low: int32 = 0
    high: int32 = 0

    i: int32 = 0
    while i < 10000:
        r: int32 = rand()
        if r < 1073741824:  # Half of INT_MAX
            low = low + 1
        else:
            high = high + 1
        i = i + 1

    print_str("Low: ")
    print_int(low)
    print_str(", High: ")
    print_int(high)
    print_newline()

    # Should be roughly 50/50
    diff: int32 = low - high
    if diff < 0:
        diff = -diff

    if diff < 1000:  # Within 10% tolerance
        pass_test("10000 random numbers balanced")
    else:
        fail_test("10000 random numbers balanced")

# ============================================================================
# Loop Stress Tests
# ============================================================================

def test_nested_loops():
    """Test deeply nested loops."""
    print_str("\n=== Nested Loop Test ===\n")

    count: int32 = 0
    a: int32 = 0
    while a < 10:
        b: int32 = 0
        while b < 10:
            c: int32 = 0
            while c < 10:
                d: int32 = 0
                while d < 10:
                    count = count + 1
                    d = d + 1
                c = c + 1
            b = b + 1
        a = a + 1

    print_str("Nested loop count: ")
    print_int(count)
    print_newline()

    if count == 10000:
        pass_test("10x10x10x10 = 10000 iterations")
    else:
        fail_test("10x10x10x10 = 10000 iterations")

def test_large_loop():
    """Test very large loop."""
    print_str("\n=== Large Loop Test ===\n")

    sum: int32 = 0
    i: int32 = 1
    while i <= 100000:
        sum = sum + 1
        i = i + 1

    print_str("100K loop sum: ")
    print_int(sum)
    print_newline()

    if sum == 100000:
        pass_test("100000 iterations")
    else:
        fail_test("100000 iterations")

# ============================================================================
# Array Stress Tests
# ============================================================================

def test_large_array():
    """Test large array operations."""
    print_str("\n=== Large Array Test ===\n")

    arr: Array[1000, int32]

    # Fill array
    i: int32 = 0
    while i < 1000:
        arr[i] = i * 2
        i = i + 1

    # Sum array
    sum: int32 = 0
    i = 0
    while i < 1000:
        sum = sum + arr[i]
        i = i + 1

    print_str("Sum of 0,2,4,...,1998: ")
    print_int(sum)
    print_newline()

    # Sum should be 2 * (0+1+2+...+999) = 2 * 499500 = 999000
    if sum == 999000:
        pass_test("1000-element array sum")
    else:
        fail_test("1000-element array sum")

# ============================================================================
# Function Call Stress
# ============================================================================

_call_count: int32 = 0

def increment_counter():
    global _call_count
    _call_count = _call_count + 1

def test_many_function_calls():
    """Test many function calls."""
    global _call_count
    print_str("\n=== Function Call Stress ===\n")

    _call_count = 0

    i: int32 = 0
    while i < 10000:
        increment_counter()
        i = i + 1

    print_str("Function calls: ")
    print_int(_call_count)
    print_newline()

    if _call_count == 10000:
        pass_test("10000 function calls")
    else:
        fail_test("10000 function calls")

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("========================================\n")
    print_str("       PYNUX STRESS TEST\n")
    print_str("========================================\n")

    # Memory tests
    test_memory_alloc_free()
    test_memory_fragmentation()

    # Computation tests
    test_heavy_math()
    test_power_calculations()
    test_random_sequence()

    # Loop tests
    test_nested_loops()
    test_large_loop()

    # Array test
    test_large_array()

    # Function call test
    test_many_function_calls()

    # Summary
    print_str("\n========================================\n")
    print_str("RESULTS: ")
    print_int(_passed)
    print_str(" passed, ")
    print_int(_failed)
    print_str(" failed\n")
    print_str("========================================\n")

    if _failed == 0:
        print_str("ALL STRESS TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return _failed
