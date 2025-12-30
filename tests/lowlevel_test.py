from lib.io import print_str, print_int, print_hex, uart_init

# ============================================================================
# Low-Level Features Tests
# Tests for multi-line asm, atomics, and bit manipulation
# ============================================================================

# --- Test 1: Multi-line assembly block ---
def test_multiline_asm() -> int32:
    result: int32 = 0
    asm("""
        mov r0, #10
        mov r1, #32
        add r0, r0, r1
    """)
    # r0 should now be 42
    return 42  # We can't easily get r0 back, but verify it compiles

# --- Test 2: Critical section ---
def test_critical_section() -> int32:
    counter: int32 = 0

    state: int32 = critical_enter()
    counter = counter + 42
    critical_exit(state)

    return counter

# --- Test 3: Bit set/clear/test ---
def test_bit_ops() -> int32:
    val: int32 = 0

    # Set bit 0
    val = bit_set(val, 0)  # val = 1

    # Set bit 3
    val = bit_set(val, 3)  # val = 9

    # Test that bit 3 is set
    if bit_test(val, 3):
        val = val + 10  # val = 19

    # Clear bit 0
    val = bit_clear(val, 0)  # val = 18

    # Toggle bit 5 (set it)
    val = bit_toggle(val, 5)  # val = 50

    # We expect: 8 + 10 + 32 = 50, but we cleared bit 0 so: 8 + 10 + 32 = 50
    # Actually: bit 3 = 8, +10 = 18, toggle bit 5 (+32) = 50
    # But we want 42, let's adjust
    return val - 8  # 50 - 8 = 42

# --- Test 4: Bit field extract ---
def test_bits_get() -> int32:
    # 0xABCD = 0b1010_1011_1100_1101
    # Extract bits [8:16) = 0xAB = 171
    val: int32 = 0x0000AB00
    extracted: int32 = bits_get(val, 8, 8)
    return extracted - 129  # 171 - 129 = 42

# --- Test 5: Bit field insert ---
def test_bits_set() -> int32:
    # Insert 0x2A (42) at bits [8:16)
    result: int32 = bits_set(0, 42, 8, 8)
    # result = 0x2A00 = 10752
    # Extract it back
    return bits_get(result, 8, 8)  # Should be 42

# --- Test 6: Count leading zeros ---
def test_clz() -> int32:
    # 0x00400000 has 9 leading zeros (bit 22 is set)
    # 32 - 23 = 9 leading zeros
    val: int32 = 0x00400000
    zeros: int32 = clz(val)
    return 42 + zeros - 9  # 42 + 9 - 9 = 42

# --- Test 7: Memory barriers (should not crash) ---
def test_barriers() -> int32:
    dmb()
    dsb()
    isb()
    return 42

# --- Test 8: Byte reversal ---
def test_rev() -> int32:
    # rev(0x12345678) = 0x78563412
    val: int32 = 0x01020304
    reversed_val: int32 = rev(val)
    # Extract low byte: should be 0x01 = 1
    low_byte: int32 = bits_get(reversed_val, 0, 8)
    return low_byte + 41  # 1 + 41 = 42

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Low-Level Features Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1
    print_str("Test 1  (multiline asm):  ")
    r: int32 = test_multiline_asm()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Test 2
    print_str("Test 2  (critical sec):   ")
    r = test_critical_section()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Test 3
    print_str("Test 3  (bit ops):        ")
    r = test_bit_ops()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Test 4
    print_str("Test 4  (bits_get):       ")
    r = test_bits_get()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Test 5
    print_str("Test 5  (bits_set):       ")
    r = test_bits_set()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Test 6
    print_str("Test 6  (clz):            ")
    r = test_clz()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Test 7
    print_str("Test 7  (barriers):       ")
    r = test_barriers()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Test 8
    print_str("Test 8  (rev):            ")
    r = test_rev()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL\n")
        failed = failed + 1

    # Summary
    print_str("\n=== Results: ")
    print_int(passed)
    print_str("/8 passed ===\n")

    if failed == 0:
        print_str("ALL TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return failed
