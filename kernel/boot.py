# Pynux Bootloader
#
# Early hardware initialization and boot services.
# Validates firmware, provides version info, and detects boot reason.

from lib.io import print_str, print_int, print_newline
from lib.memory import memcpy, memcmp

# ============================================================================
# Boot Reason Codes
# ============================================================================

BOOT_COLD: int32 = 0        # Cold boot (power on)
BOOT_WARM: int32 = 1        # Warm reset (software reset)
BOOT_WATCHDOG: int32 = 2    # Watchdog timeout triggered reset
BOOT_UPDATE: int32 = 3      # Reset after firmware update
BOOT_FAULT: int32 = 4       # Reset due to hard fault
BOOT_BROWNOUT: int32 = 5    # Reset due to low voltage
BOOT_EXTERNAL: int32 = 6    # External reset pin triggered

# ============================================================================
# ARM Cortex-M3 Reset Control Registers
# ============================================================================

# Reset and Clock Control (RCC) - for STM32-style or generic Cortex-M
RCC_BASE: uint32 = 0x40021000
RCC_CSR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0x40021024)  # Control/Status Register

# Reset Status Flags (typical Cortex-M layout)
RCC_CSR_LPWRRSTF: uint32 = 0x80000000   # Low-power reset
RCC_CSR_WWDGRSTF: uint32 = 0x40000000   # Window watchdog reset
RCC_CSR_IWDGRSTF: uint32 = 0x20000000   # Independent watchdog reset
RCC_CSR_SFTRSTF: uint32 = 0x10000000    # Software reset
RCC_CSR_PORRSTF: uint32 = 0x08000000    # Power-on reset
RCC_CSR_PINRSTF: uint32 = 0x04000000    # NRST pin reset
RCC_CSR_BORRSTF: uint32 = 0x02000000    # Brownout reset
RCC_CSR_RMVF: uint32 = 0x01000000       # Remove reset flags

# NVIC System Reset registers
AIRCR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED0C)
AIRCR_VECTKEY: uint32 = 0x05FA0000
AIRCR_SYSRESETREQ: uint32 = 0x00000004

# ============================================================================
# Firmware Header Structure
# ============================================================================
# Located at a fixed offset in flash (typically after vector table)
#
# Offset  Size  Field
# 0x00    4     Magic number (0x50594E58 = "PYNX")
# 0x04    4     CRC32 of firmware (excluding header)
# 0x08    4     Firmware size in bytes
# 0x0C    4     Version (major.minor.patch packed)
# 0x10    16    Build date string (null-terminated)
# 0x20    16    Version string (null-terminated)
# 0x30    4     Entry point address
# 0x34    4     Load address
# 0x38    4     Flags (encrypted, compressed, etc.)
# 0x3C    4     Header CRC32

FW_HEADER_ADDR: uint32 = 0x00000100    # After vector table (0x100 = 256 bytes)
FW_MAGIC: uint32 = 0x50594E58          # "PYNX" in ASCII

# Header offsets
FW_OFF_MAGIC: int32 = 0
FW_OFF_CRC: int32 = 4
FW_OFF_SIZE: int32 = 8
FW_OFF_VERSION: int32 = 12
FW_OFF_BUILD_DATE: int32 = 16
FW_OFF_VERSION_STR: int32 = 32
FW_OFF_ENTRY: int32 = 48
FW_OFF_LOAD: int32 = 52
FW_OFF_FLAGS: int32 = 56
FW_OFF_HEADER_CRC: int32 = 60

# Firmware flags
FW_FLAG_ENCRYPTED: uint32 = 0x01
FW_FLAG_COMPRESSED: uint32 = 0x02
FW_FLAG_VERIFIED: uint32 = 0x04
FW_FLAG_DEBUG: uint32 = 0x08

# ============================================================================
# CRC32 Implementation (IEEE 802.3 polynomial)
# ============================================================================

# CRC32 lookup table (IEEE 802.3 polynomial: 0xEDB88320)
_crc32_table: Array[256, uint32]
_crc32_table_init: bool = False

def _crc32_init_table():
    """Initialize CRC32 lookup table."""
    global _crc32_table_init

    if _crc32_table_init:
        return

    i: int32 = 0
    while i < 256:
        crc: uint32 = cast[uint32](i)
        j: int32 = 0
        while j < 8:
            if (crc & 1) != 0:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc = crc >> 1
            j = j + 1
        _crc32_table[i] = crc
        i = i + 1

    _crc32_table_init = True

def crc32_calc(data: Ptr[uint8], length: int32) -> uint32:
    """Calculate CRC32 checksum of data buffer.

    Args:
        data: Pointer to data buffer
        length: Length of data in bytes

    Returns:
        CRC32 checksum
    """
    _crc32_init_table()

    crc: uint32 = 0xFFFFFFFF
    i: int32 = 0
    while i < length:
        byte_val: uint32 = cast[uint32](data[i])
        table_idx: int32 = cast[int32]((crc ^ byte_val) & 0xFF)
        crc = (crc >> 8) ^ _crc32_table[table_idx]
        i = i + 1

    return crc ^ 0xFFFFFFFF

def crc32_update(crc: uint32, data: Ptr[uint8], length: int32) -> uint32:
    """Update running CRC32 with additional data.

    Args:
        crc: Current CRC value (use 0xFFFFFFFF to start)
        data: Pointer to data buffer
        length: Length of data in bytes

    Returns:
        Updated CRC32 value
    """
    _crc32_init_table()

    i: int32 = 0
    while i < length:
        byte_val: uint32 = cast[uint32](data[i])
        table_idx: int32 = cast[int32]((crc ^ byte_val) & 0xFF)
        crc = (crc >> 8) ^ _crc32_table[table_idx]
        i = i + 1

    return crc

def crc32_finalize(crc: uint32) -> uint32:
    """Finalize CRC32 calculation.

    Args:
        crc: Running CRC value

    Returns:
        Final CRC32 checksum
    """
    return crc ^ 0xFFFFFFFF

# ============================================================================
# Boot State
# ============================================================================

_boot_reason: int32 = BOOT_COLD
_boot_initialized: bool = False

# Static buffers for version strings
_version_str: Array[32, char]
_build_date_str: Array[32, char]

# ============================================================================
# Low-Level Hardware Access
# ============================================================================

def _read_reset_flags() -> uint32:
    """Read reset status flags from RCC_CSR."""
    # Memory barrier before reading
    dmb()
    flags: uint32 = RCC_CSR[0]
    return flags

def _clear_reset_flags():
    """Clear reset status flags."""
    RCC_CSR[0] = RCC_CSR[0] | RCC_CSR_RMVF
    dsb()

def _detect_boot_reason() -> int32:
    """Detect the reason for this boot/reset.

    Returns:
        One of BOOT_* constants
    """
    flags: uint32 = _read_reset_flags()

    # Check flags in priority order
    if (flags & RCC_CSR_IWDGRSTF) != 0:
        return BOOT_WATCHDOG
    if (flags & RCC_CSR_WWDGRSTF) != 0:
        return BOOT_WATCHDOG
    if (flags & RCC_CSR_SFTRSTF) != 0:
        # Software reset - could be warm boot or update
        # Check for update flag in backup domain
        return BOOT_WARM
    if (flags & RCC_CSR_BORRSTF) != 0:
        return BOOT_BROWNOUT
    if (flags & RCC_CSR_PINRSTF) != 0:
        return BOOT_EXTERNAL
    if (flags & RCC_CSR_PORRSTF) != 0:
        return BOOT_COLD

    # Default to cold boot
    return BOOT_COLD

# ============================================================================
# Firmware Header Access
# ============================================================================

def _read_fw_header_u32(offset: int32) -> uint32:
    """Read a 32-bit value from firmware header."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](FW_HEADER_ADDR + cast[uint32](offset))
    return ptr[0]

def _read_fw_header_str(offset: int32, dest: Ptr[char], max_len: int32):
    """Read a string from firmware header."""
    src: Ptr[char] = cast[Ptr[char]](FW_HEADER_ADDR + cast[uint32](offset))
    i: int32 = 0
    while i < max_len - 1:
        dest[i] = src[i]
        if src[i] == '\0':
            break
        i = i + 1
    dest[max_len - 1] = '\0'

# ============================================================================
# Public Boot API
# ============================================================================

def boot_init():
    """Early hardware initialization.

    This should be called as early as possible after reset.
    Initializes critical hardware and detects boot reason.
    """
    global _boot_reason, _boot_initialized

    if _boot_initialized:
        return

    # Initialize CRC table (needed for firmware validation)
    _crc32_init_table()

    # Detect why we booted
    _boot_reason = _detect_boot_reason()

    # Clear reset flags so next boot can detect fresh
    _clear_reset_flags()

    # Initialize static string buffers
    i: int32 = 0
    while i < 32:
        _version_str[i] = '\0'
        _build_date_str[i] = '\0'
        i = i + 1

    # Read version and build date from firmware header
    magic: uint32 = _read_fw_header_u32(FW_OFF_MAGIC)
    if magic == FW_MAGIC:
        _read_fw_header_str(FW_OFF_VERSION_STR, &_version_str[0], 32)
        _read_fw_header_str(FW_OFF_BUILD_DATE, &_build_date_str[0], 32)
    else:
        # No valid header - use defaults
        _version_str[0] = '0'
        _version_str[1] = '.'
        _version_str[2] = '0'
        _version_str[3] = '.'
        _version_str[4] = '0'
        _version_str[5] = '\0'

        _build_date_str[0] = 'u'
        _build_date_str[1] = 'n'
        _build_date_str[2] = 'k'
        _build_date_str[3] = 'n'
        _build_date_str[4] = 'o'
        _build_date_str[5] = 'w'
        _build_date_str[6] = 'n'
        _build_date_str[7] = '\0'

    _boot_initialized = True

def boot_check_firmware() -> bool:
    """Validate firmware CRC.

    Checks the firmware image integrity by comparing calculated
    CRC32 against the stored value in the firmware header.

    Returns:
        True if firmware is valid, False otherwise
    """
    # Read header magic
    magic: uint32 = _read_fw_header_u32(FW_OFF_MAGIC)
    if magic != FW_MAGIC:
        return False

    # Read expected CRC and size
    expected_crc: uint32 = _read_fw_header_u32(FW_OFF_CRC)
    fw_size: uint32 = _read_fw_header_u32(FW_OFF_SIZE)

    # Sanity check size (max 256KB)
    if fw_size > 262144:
        return False
    if fw_size == 0:
        return False

    # Read load address (where firmware data starts)
    load_addr: uint32 = _read_fw_header_u32(FW_OFF_LOAD)

    # Calculate CRC of firmware data
    fw_data: Ptr[uint8] = cast[Ptr[uint8]](load_addr)
    calculated_crc: uint32 = crc32_calc(fw_data, cast[int32](fw_size))

    return calculated_crc == expected_crc

def boot_get_version() -> Ptr[char]:
    """Get firmware version string.

    Returns:
        Pointer to null-terminated version string (e.g., "1.2.3")
    """
    if not _boot_initialized:
        boot_init()

    return &_version_str[0]

def boot_get_build_date() -> Ptr[char]:
    """Get firmware build timestamp.

    Returns:
        Pointer to null-terminated build date string
    """
    if not _boot_initialized:
        boot_init()

    return &_build_date_str[0]

def boot_reason() -> int32:
    """Get boot reason code.

    Returns:
        One of BOOT_COLD, BOOT_WARM, BOOT_WATCHDOG, BOOT_UPDATE,
        BOOT_FAULT, BOOT_BROWNOUT, or BOOT_EXTERNAL
    """
    if not _boot_initialized:
        boot_init()

    return _boot_reason

def boot_reason_str() -> Ptr[char]:
    """Get human-readable boot reason string.

    Returns:
        Pointer to static string describing boot reason
    """
    reason: int32 = boot_reason()

    if reason == BOOT_COLD:
        return "cold boot"
    elif reason == BOOT_WARM:
        return "warm reset"
    elif reason == BOOT_WATCHDOG:
        return "watchdog reset"
    elif reason == BOOT_UPDATE:
        return "firmware update"
    elif reason == BOOT_FAULT:
        return "hard fault"
    elif reason == BOOT_BROWNOUT:
        return "brownout reset"
    elif reason == BOOT_EXTERNAL:
        return "external reset"
    else:
        return "unknown"

# ============================================================================
# System Reset Functions
# ============================================================================

def boot_reset():
    """Perform a software system reset."""
    # Ensure all memory writes are complete
    dsb()

    # Request system reset via AIRCR
    AIRCR[0] = AIRCR_VECTKEY | AIRCR_SYSRESETREQ

    # Wait for reset
    dsb()
    while True:
        pass

def boot_reset_to_bootloader():
    """Reset into bootloader/DFU mode.

    Sets a flag in backup domain before resetting so the
    bootloader knows to stay in DFU mode.
    """
    # Set magic value in backup SRAM to signal DFU mode
    # (Implementation depends on specific MCU)
    boot_reset()

# ============================================================================
# Firmware Header Utilities
# ============================================================================

def boot_get_fw_size() -> uint32:
    """Get firmware size in bytes."""
    magic: uint32 = _read_fw_header_u32(FW_OFF_MAGIC)
    if magic != FW_MAGIC:
        return 0
    return _read_fw_header_u32(FW_OFF_SIZE)

def boot_get_fw_entry() -> uint32:
    """Get firmware entry point address."""
    magic: uint32 = _read_fw_header_u32(FW_OFF_MAGIC)
    if magic != FW_MAGIC:
        return 0
    return _read_fw_header_u32(FW_OFF_ENTRY)

def boot_get_fw_flags() -> uint32:
    """Get firmware flags."""
    magic: uint32 = _read_fw_header_u32(FW_OFF_MAGIC)
    if magic != FW_MAGIC:
        return 0
    return _read_fw_header_u32(FW_OFF_FLAGS)

def boot_is_debug_build() -> bool:
    """Check if firmware is a debug build."""
    flags: uint32 = boot_get_fw_flags()
    return (flags & FW_FLAG_DEBUG) != 0

# ============================================================================
# Boot Diagnostics
# ============================================================================

def boot_print_info():
    """Print boot information to console."""
    print_str("[boot] Version: ")
    print_str(boot_get_version())
    print_newline()

    print_str("[boot] Build: ")
    print_str(boot_get_build_date())
    print_newline()

    print_str("[boot] Reason: ")
    print_str(boot_reason_str())
    print_newline()

    print_str("[boot] Firmware size: ")
    print_int(cast[int32](boot_get_fw_size()))
    print_str(" bytes\n")

    if boot_check_firmware():
        print_str("[boot] Firmware CRC: OK\n")
    else:
        print_str("[boot] Firmware CRC: INVALID\n")
