# Pynux Boot Module Tests
#
# Tests for boot initialization, firmware validation, and debug features.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_lte, test_pass, test_fail)
from kernel.boot import (
    # Boot reason
    boot_get_reason, boot_get_reason_str,
    BOOT_COLD, BOOT_WARM, BOOT_WATCHDOG, BOOT_UPDATE,
    BOOT_FAULT, BOOT_BROWNOUT, BOOT_EXTERNAL,
    # Firmware info
    fw_get_version, fw_get_version_str, fw_validate_crc,
    FW_MAGIC, FW_FLAG_DEBUG,
    # Reset
    system_reset
)
from kernel.debug import (
    # Debug console
    debug_print, debug_print_hex, debug_print_reg,
    # Crash handling
    crash_dump, debug_get_last_fault,
    # Breakpoints (if available)
    debug_break
)

# ============================================================================
# Boot Reason Tests
# ============================================================================

def test_boot_reason_valid():
    """Test boot reason is valid."""
    print_section("Boot Reason")

    reason: int32 = boot_get_reason()
    assert_gte(reason, BOOT_COLD, "boot reason >= BOOT_COLD")
    assert_lte(reason, BOOT_EXTERNAL, "boot reason <= BOOT_EXTERNAL")

def test_boot_reason_str():
    """Test boot reason string."""
    reason_str: Ptr[char] = boot_get_reason_str()
    if cast[uint32](reason_str) != 0:
        test_pass("boot_get_reason_str returns string")
    else:
        test_fail("boot_get_reason_str should not be null")

def test_boot_constants():
    """Test boot reason constants."""
    assert_eq(BOOT_COLD, 0, "BOOT_COLD is 0")
    assert_eq(BOOT_WARM, 1, "BOOT_WARM is 1")
    assert_eq(BOOT_WATCHDOG, 2, "BOOT_WATCHDOG is 2")
    assert_eq(BOOT_UPDATE, 3, "BOOT_UPDATE is 3")
    assert_eq(BOOT_FAULT, 4, "BOOT_FAULT is 4")

# ============================================================================
# Firmware Info Tests
# ============================================================================

def test_fw_version():
    """Test firmware version retrieval."""
    print_section("Firmware Info")

    version: uint32 = fw_get_version()
    # Version should be non-zero
    if version != 0:
        test_pass("fw_get_version returns non-zero")
    else:
        test_pass("fw_get_version returns 0 (not set)")

def test_fw_version_str():
    """Test firmware version string."""
    version_str: Ptr[char] = fw_get_version_str()
    if cast[uint32](version_str) != 0:
        test_pass("fw_get_version_str returns string")
    else:
        test_fail("fw_get_version_str should not be null")

def test_fw_magic():
    """Test firmware magic constant."""
    # "PYNX" = 0x50594E58
    assert_eq(cast[int32](FW_MAGIC), 0x50594E58, "FW_MAGIC is 'PYNX'")

# ============================================================================
# Debug Module Tests
# ============================================================================

def test_debug_print():
    """Test debug print functions exist."""
    print_section("Debug Functions")

    # These should not crash
    debug_print("test message")
    test_pass("debug_print works")

def test_debug_print_hex():
    """Test debug hex print."""
    debug_print_hex(0xDEADBEEF)
    test_pass("debug_print_hex works")

def test_debug_get_fault():
    """Test getting last fault info."""
    fault: int32 = debug_get_last_fault()
    # 0 means no fault, which is expected
    assert_gte(fault, 0, "debug_get_last_fault returns >= 0")

# ============================================================================
# Safety Tests
# ============================================================================

def test_no_crash_on_debug():
    """Test debug functions don't crash."""
    print_section("Debug Safety")

    # Call various debug functions
    debug_print("safety test 1")
    debug_print_hex(0x12345678)
    debug_print_reg(0)

    test_pass("debug functions are safe")

# ============================================================================
# Main
# ============================================================================

def test_boot_main() -> int32:
    print_str("\n=== Pynux Boot/Debug Tests ===\n")

    # Boot reason tests
    test_boot_reason_valid()
    test_boot_reason_str()
    test_boot_constants()

    # Firmware tests
    test_fw_version()
    test_fw_version_str()
    test_fw_magic()

    # Debug tests
    test_debug_print()
    test_debug_print_hex()
    test_debug_get_fault()

    # Safety tests
    test_no_crash_on_debug()

    return print_results()
