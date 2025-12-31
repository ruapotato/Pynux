# Pynux Bootloader
#
# Improved bootloader with firmware update capability.
# Provides boot mode detection, firmware validation, dual-bank support,
# and UART-based firmware update protocol.

from lib.io import print_str, print_int, print_newline, uart_putc, uart_getc, uart_available
from lib.memory import memset, memcpy, memcmp

# ============================================================================
# Image Header Structure
# ============================================================================
#
# Firmware images must have this header at a fixed offset from the start.
#
# Offset  Size  Field
# 0x00    4     Magic number (0x50594E58 = "PYNX")
# 0x04    4     Version (major << 24 | minor << 16 | patch)
# 0x08    4     Image size (excluding header)
# 0x0C    4     CRC32 of image data
# 0x10    4     Entry point offset (relative to image base)
# 0x14    4     Vector table offset (relative to image base)
# 0x18    4     Flags (reserved for future use)
# 0x1C    4     Header CRC32
#
# ============================================================================

# Image header magic number ("PYNX" in little-endian)
BOOT_MAGIC: uint32 = 0x50594E58

# Header field offsets
HDR_OFF_MAGIC: int32 = 0
HDR_OFF_VERSION: int32 = 4
HDR_OFF_SIZE: int32 = 8
HDR_OFF_CRC: int32 = 12
HDR_OFF_ENTRY: int32 = 16
HDR_OFF_VTOR: int32 = 20
HDR_OFF_FLAGS: int32 = 24
HDR_OFF_HDR_CRC: int32 = 28

HDR_SIZE: int32 = 32  # Total header size

# ============================================================================
# Flash Memory Layout
# ============================================================================
#
# Memory Map for dual-bank support:
#   0x00000000 - 0x00003FFF  Bootloader (16KB)
#   0x00004000 - 0x0003FFFF  Bank 0 (240KB) - Primary application
#   0x00040000 - 0x0007BFFF  Bank 1 (240KB) - Secondary/update slot
#   0x0007C000 - 0x0007FFFF  Config/metadata (16KB)
#
# ============================================================================

BOOTLOADER_BASE: uint32 = 0x00000000
BOOTLOADER_SIZE: uint32 = 0x4000       # 16KB

BANK0_BASE: uint32 = 0x00004000
BANK1_BASE: uint32 = 0x00040000
BANK_SIZE: uint32 = 0x3C000            # 240KB each

CONFIG_BASE: uint32 = 0x0007C000
CONFIG_SIZE: uint32 = 0x4000           # 16KB

# Application header is at start of each bank
APP_HEADER_OFFSET: uint32 = 0x100      # After vector table

# ============================================================================
# Boot Mode Detection
# ============================================================================

# Update request flag location (in backup RAM/register)
# For STM32: Backup SRAM at 0x40024000
# For RP2040: Scratch registers in SIO
UPDATE_FLAG_ADDR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0x40024000)
UPDATE_MAGIC: uint32 = 0x55504454      # "UPDT"

# BOOTSEL button on RP2040 (active low)
RP2040_BOOTSEL_PIN: uint32 = 21

# GPIO registers for button checking
GPIO_IN_ADDR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xD0000004)  # SIO GPIO input

# ============================================================================
# UART Update Protocol Constants
# ============================================================================

# XMODEM-like protocol constants
XMODEM_SOH: uint8 = 0x01       # Start of 128-byte block
XMODEM_STX: uint8 = 0x02       # Start of 1024-byte block
XMODEM_EOT: uint8 = 0x04       # End of transmission
XMODEM_ACK: uint8 = 0x06       # Acknowledge
XMODEM_NAK: uint8 = 0x15       # Negative acknowledge
XMODEM_CAN: uint8 = 0x18       # Cancel
XMODEM_CRC: uint8 = 0x43       # 'C' - Request CRC mode

XMODEM_BLOCK_SIZE: int32 = 128
XMODEM_TIMEOUT_MS: int32 = 3000
XMODEM_MAX_RETRIES: int32 = 10

# ============================================================================
# LED Status Patterns
# ============================================================================

LED_BLINK_FAST: int32 = 100    # Fast blink: receiving data
LED_BLINK_SLOW: int32 = 500    # Slow blink: waiting for update
LED_BLINK_ERROR: int32 = 1000  # Error blink pattern

# LED GPIO (platform-specific)
LED_GPIO_ADDR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xD0000010)  # SIO GPIO output

# ============================================================================
# CRC32 Implementation
# ============================================================================

# CRC32 lookup table (IEEE 802.3 polynomial: 0xEDB88320)
_crc32_table: Array[256, uint32]
_crc32_initialized: bool = False

def crc32_init() -> uint32:
    """Initialize CRC32 calculation, returns initial state."""
    global _crc32_initialized

    # Initialize table if needed
    if not _crc32_initialized:
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
        _crc32_initialized = True

    return 0xFFFFFFFF

def crc32_update(state: uint32, data: Ptr[uint8], length: int32) -> uint32:
    """Update CRC32 with additional data.

    Args:
        state: Current CRC state
        data: Pointer to data buffer
        length: Length in bytes

    Returns:
        Updated CRC state
    """
    crc: uint32 = state
    i: int32 = 0
    while i < length:
        byte_val: uint32 = cast[uint32](data[i])
        table_idx: int32 = cast[int32]((crc ^ byte_val) & 0xFF)
        crc = (crc >> 8) ^ _crc32_table[table_idx]
        i = i + 1
    return crc

def crc32_final(state: uint32) -> uint32:
    """Finalize CRC32 calculation.

    Args:
        state: Current CRC state

    Returns:
        Final CRC32 value
    """
    return state ^ 0xFFFFFFFF

# ============================================================================
# Module State
# ============================================================================

_active_bank: int32 = 0
_bootloader_initialized: bool = False

# Progress callback type: fn(current: int32, total: int32)
_progress_callback: Ptr[void] = cast[Ptr[void]](0)

# ============================================================================
# Boot Mode Detection
# ============================================================================

def bootloader_check_update_requested() -> bool:
    """Check if firmware update was requested.

    Checks for update request flag in backup RAM or magic value
    that was set before a software reset.

    Returns:
        True if update mode was requested
    """
    # Check magic value in backup RAM
    flag: uint32 = UPDATE_FLAG_ADDR[0]
    if flag == UPDATE_MAGIC:
        # Clear the flag
        UPDATE_FLAG_ADDR[0] = 0
        dsb()
        return True

    return False

def bootloader_check_button_held() -> bool:
    """Check if boot button is held at startup.

    On RP2040, checks BOOTSEL button.
    On STM32, could check a user button.

    Returns:
        True if button is held (should enter DFU mode)
    """
    # Read GPIO input register
    gpio_state: uint32 = GPIO_IN_ADDR[0]

    # BOOTSEL is active low on RP2040
    if (gpio_state & (1 << RP2040_BOOTSEL_PIN)) == 0:
        return True

    return False

def bootloader_request_update():
    """Set flag to request update mode on next boot.

    Sets a magic value in backup RAM that survives reset,
    then triggers a software reset.
    """
    # Set update magic in backup RAM
    UPDATE_FLAG_ADDR[0] = UPDATE_MAGIC
    dsb()

    # Trigger software reset via AIRCR
    AIRCR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED0C)
    AIRCR[0] = 0x05FA0004  # VECTKEY + SYSRESETREQ
    dsb()

    # Wait for reset
    while True:
        pass

# ============================================================================
# Firmware Validation
# ============================================================================

def bootloader_validate_image(addr: uint32) -> bool:
    """Validate firmware image at given address.

    Checks:
    1. Magic number is correct
    2. Header CRC is valid
    3. Image CRC matches stored value
    4. Size is reasonable

    Args:
        addr: Base address of firmware image

    Returns:
        True if image is valid
    """
    header: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr + APP_HEADER_OFFSET)

    # Check magic number
    magic: uint32 = header[HDR_OFF_MAGIC / 4]
    if magic != BOOT_MAGIC:
        return False

    # Get size and validate
    img_size: uint32 = header[HDR_OFF_SIZE / 4]
    if img_size == 0 or img_size > BANK_SIZE:
        return False

    # Verify header CRC (covers first 28 bytes of header)
    hdr_data: Ptr[uint8] = cast[Ptr[uint8]](addr + APP_HEADER_OFFSET)
    state: uint32 = crc32_init()
    state = crc32_update(state, hdr_data, 28)
    hdr_crc_calc: uint32 = crc32_final(state)
    hdr_crc_stored: uint32 = header[HDR_OFF_HDR_CRC / 4]

    if hdr_crc_calc != hdr_crc_stored:
        return False

    # Verify image CRC
    img_data: Ptr[uint8] = cast[Ptr[uint8]](addr + APP_HEADER_OFFSET + cast[uint32](HDR_SIZE))
    state = crc32_init()
    state = crc32_update(state, img_data, cast[int32](img_size))
    img_crc_calc: uint32 = crc32_final(state)
    img_crc_stored: uint32 = header[HDR_OFF_CRC / 4]

    if img_crc_calc != img_crc_stored:
        return False

    return True

def bootloader_get_image_version(addr: uint32) -> uint32:
    """Get version number from firmware image.

    Version is packed as: major << 24 | minor << 16 | patch

    Args:
        addr: Base address of firmware image

    Returns:
        Packed version number, or 0 if invalid
    """
    header: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr + APP_HEADER_OFFSET)

    # Check magic first
    magic: uint32 = header[HDR_OFF_MAGIC / 4]
    if magic != BOOT_MAGIC:
        return 0

    return header[HDR_OFF_VERSION / 4]

def _version_major(version: uint32) -> int32:
    """Extract major version number."""
    return cast[int32]((version >> 24) & 0xFF)

def _version_minor(version: uint32) -> int32:
    """Extract minor version number."""
    return cast[int32]((version >> 16) & 0xFF)

def _version_patch(version: uint32) -> int32:
    """Extract patch version number."""
    return cast[int32](version & 0xFFFF)

def bootloader_print_version(version: uint32):
    """Print version in human-readable format."""
    print_int(_version_major(version))
    print_str(".")
    print_int(_version_minor(version))
    print_str(".")
    print_int(_version_patch(version))

# ============================================================================
# Dual Bank Support
# ============================================================================

def bootloader_get_active_bank() -> int32:
    """Get the currently active firmware bank.

    Returns:
        0 for Bank 0, 1 for Bank 1
    """
    return _active_bank

def bootloader_set_active_bank(bank: int32):
    """Set the active bank for next boot.

    Args:
        bank: 0 for Bank 0, 1 for Bank 1
    """
    global _active_bank

    if bank < 0 or bank > 1:
        return

    _active_bank = bank

    # Store in config area for persistence
    # (Simplified - real implementation would write to flash)

def bootloader_get_inactive_bank_addr() -> uint32:
    """Get address of the inactive bank.

    This is the bank that can be safely written with new firmware.

    Returns:
        Base address of inactive bank
    """
    if _active_bank == 0:
        return BANK1_BASE
    return BANK0_BASE

def bootloader_get_bank_addr(bank: int32) -> uint32:
    """Get base address of a specific bank.

    Args:
        bank: 0 or 1

    Returns:
        Base address of the bank
    """
    if bank == 0:
        return BANK0_BASE
    return BANK1_BASE

def bootloader_swap_banks():
    """Swap active and inactive banks.

    Called after successful firmware update to activate new firmware.
    """
    global _active_bank

    if _active_bank == 0:
        _active_bank = 1
    else:
        _active_bank = 0

# ============================================================================
# Flash Operations
# ============================================================================

# Flash controller registers (generic Cortex-M)
FLASH_KEYR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0x40022004)
FLASH_SR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0x4002200C)
FLASH_CR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0x40022010)
FLASH_AR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0x40022014)

FLASH_KEY1: uint32 = 0x45670123
FLASH_KEY2: uint32 = 0xCDEF89AB

FLASH_SR_BSY: uint32 = 0x01
FLASH_SR_PGERR: uint32 = 0x04
FLASH_SR_WRPRTERR: uint32 = 0x10
FLASH_SR_EOP: uint32 = 0x20

FLASH_CR_PG: uint32 = 0x01
FLASH_CR_PER: uint32 = 0x02
FLASH_CR_STRT: uint32 = 0x40
FLASH_CR_LOCK: uint32 = 0x80

FLASH_PAGE_SIZE: uint32 = 1024

def _flash_unlock() -> bool:
    """Unlock flash for programming."""
    cr: uint32 = FLASH_CR[0]
    if (cr & FLASH_CR_LOCK) == 0:
        return True  # Already unlocked

    FLASH_KEYR[0] = FLASH_KEY1
    FLASH_KEYR[0] = FLASH_KEY2
    dsb()

    cr = FLASH_CR[0]
    return (cr & FLASH_CR_LOCK) == 0

def _flash_lock():
    """Lock flash to prevent accidental writes."""
    FLASH_CR[0] = FLASH_CR[0] | FLASH_CR_LOCK
    dsb()

def _flash_wait() -> bool:
    """Wait for flash operation to complete."""
    timeout: int32 = 100000
    while timeout > 0:
        sr: uint32 = FLASH_SR[0]
        if (sr & FLASH_SR_BSY) == 0:
            return True
        timeout = timeout - 1
    return False

def _flash_erase_page(addr: uint32) -> bool:
    """Erase a single flash page."""
    if not _flash_wait():
        return False

    # Clear error flags
    FLASH_SR[0] = FLASH_SR_PGERR | FLASH_SR_WRPRTERR | FLASH_SR_EOP
    dsb()

    # Set page erase
    FLASH_CR[0] = FLASH_CR_PER
    dsb()

    FLASH_AR[0] = addr
    dsb()

    # Start erase
    FLASH_CR[0] = FLASH_CR_PER | FLASH_CR_STRT
    dsb()

    if not _flash_wait():
        FLASH_CR[0] = 0
        return False

    sr: uint32 = FLASH_SR[0]
    FLASH_CR[0] = 0

    return (sr & (FLASH_SR_PGERR | FLASH_SR_WRPRTERR)) == 0

def _flash_write_word(addr: uint32, data: uint32) -> bool:
    """Write a single 32-bit word to flash."""
    if not _flash_wait():
        return False

    # Clear error flags
    FLASH_SR[0] = FLASH_SR_PGERR | FLASH_SR_WRPRTERR | FLASH_SR_EOP
    dsb()

    # Set programming mode
    FLASH_CR[0] = FLASH_CR_PG
    dsb()

    # Write data
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = data
    dsb()

    if not _flash_wait():
        FLASH_CR[0] = 0
        return False

    sr: uint32 = FLASH_SR[0]
    FLASH_CR[0] = 0

    if (sr & (FLASH_SR_PGERR | FLASH_SR_WRPRTERR)) != 0:
        return False

    # Verify
    return ptr[0] == data

# ============================================================================
# Firmware Update from Flash
# ============================================================================

def bootloader_update_from_flash(src: uint32, dst: uint32, size: uint32) -> bool:
    """Copy firmware from one flash region to another.

    Used for updating active bank from inactive bank after download.

    Args:
        src: Source address
        dst: Destination address
        size: Size in bytes

    Returns:
        True on success
    """
    if not _flash_unlock():
        print_str("[boot] Flash unlock failed\n")
        return False

    # Erase destination pages
    pages: int32 = cast[int32]((size + FLASH_PAGE_SIZE - 1) / FLASH_PAGE_SIZE)
    i: int32 = 0
    while i < pages:
        page_addr: uint32 = dst + cast[uint32](i) * FLASH_PAGE_SIZE
        if not _flash_erase_page(page_addr):
            print_str("[boot] Erase failed\n")
            _flash_lock()
            return False

        # Progress callback
        if _progress_callback != cast[Ptr[void]](0):
            cb: fn(int32, int32) = cast[fn(int32, int32)](_progress_callback)
            cb(i, pages * 2)  # First half is erase

        i = i + 1

    # Copy data
    words: int32 = cast[int32](size / 4)
    src_ptr: Ptr[uint32] = cast[Ptr[uint32]](src)
    i = 0
    while i < words:
        word_addr: uint32 = dst + cast[uint32](i * 4)
        if not _flash_write_word(word_addr, src_ptr[i]):
            print_str("[boot] Write failed\n")
            _flash_lock()
            return False

        # Progress callback (every 256 words)
        if (i & 0xFF) == 0 and _progress_callback != cast[Ptr[void]](0):
            cb: fn(int32, int32) = cast[fn(int32, int32)](_progress_callback)
            progress: int32 = pages + (i * pages / words)
            cb(progress, pages * 2)

        i = i + 1

    _flash_lock()

    # Verify
    print_str("[boot] Verifying... ")
    src_data: Ptr[uint8] = cast[Ptr[uint8]](src)
    dst_data: Ptr[uint8] = cast[Ptr[uint8]](dst)

    if memcmp(src_data, dst_data, cast[int32](size)) != 0:
        print_str("FAILED\n")
        return False

    print_str("OK\n")
    return True

# ============================================================================
# UART-based Firmware Update (XMODEM-like protocol)
# ============================================================================

_xmodem_buf: Array[1024, uint8]
_xmodem_block_num: uint8 = 1

def _uart_getc_timeout(timeout_ms: int32) -> int32:
    """Get character from UART with timeout.

    Args:
        timeout_ms: Timeout in milliseconds

    Returns:
        Character received, or -1 on timeout
    """
    # Simple busy-wait timeout (platform-specific timing)
    count: int32 = timeout_ms * 1000
    while count > 0:
        if uart_available():
            c: char = uart_getc()
            return cast[int32](c)
        count = count - 1
    return -1

def _xmodem_receive_block() -> int32:
    """Receive one XMODEM block.

    Returns:
        Number of bytes received (128 or 1024), 0 for EOT, -1 for error
    """
    # Wait for start byte
    start: int32 = _uart_getc_timeout(XMODEM_TIMEOUT_MS)
    if start < 0:
        return -1

    if start == cast[int32](XMODEM_EOT):
        # End of transmission
        uart_putc(cast[char](XMODEM_ACK))
        return 0

    block_size: int32 = 0
    if start == cast[int32](XMODEM_SOH):
        block_size = 128
    elif start == cast[int32](XMODEM_STX):
        block_size = 1024
    else:
        return -1

    # Receive block number and complement
    blk_num: int32 = _uart_getc_timeout(1000)
    blk_cmp: int32 = _uart_getc_timeout(1000)

    if blk_num < 0 or blk_cmp < 0:
        return -1

    # Verify block number
    if (blk_num + blk_cmp) != 255:
        return -1

    # Receive data
    i: int32 = 0
    while i < block_size:
        byte_val: int32 = _uart_getc_timeout(1000)
        if byte_val < 0:
            return -1
        _xmodem_buf[i] = cast[uint8](byte_val)
        i = i + 1

    # Receive CRC (16-bit)
    crc_hi: int32 = _uart_getc_timeout(1000)
    crc_lo: int32 = _uart_getc_timeout(1000)

    if crc_hi < 0 or crc_lo < 0:
        return -1

    # Verify CRC
    state: uint32 = crc32_init()
    state = crc32_update(state, &_xmodem_buf[0], block_size)
    calc_crc: uint32 = crc32_final(state)

    recv_crc: uint32 = (cast[uint32](crc_hi) << 8) | cast[uint32](crc_lo)

    # For XMODEM-CRC, we use CRC-16-CCITT, but simplify with CRC32 lower bits
    if (calc_crc & 0xFFFF) != recv_crc:
        uart_putc(cast[char](XMODEM_NAK))
        return -1

    # Check block sequence
    if cast[uint8](blk_num) != _xmodem_block_num:
        # Duplicate block - ACK but don't process
        if cast[uint8](blk_num) == _xmodem_block_num - 1:
            uart_putc(cast[char](XMODEM_ACK))
            return -1
        uart_putc(cast[char](XMODEM_NAK))
        return -1

    _xmodem_block_num = _xmodem_block_num + 1
    uart_putc(cast[char](XMODEM_ACK))

    return block_size

def bootloader_update_from_uart() -> bool:
    """Receive firmware update via UART using XMODEM protocol.

    Returns:
        True on success
    """
    global _xmodem_block_num

    print_str("[boot] Waiting for XMODEM transfer...\n")

    # Get destination address (inactive bank)
    dst: uint32 = bootloader_get_inactive_bank_addr()

    if not _flash_unlock():
        print_str("[boot] Flash unlock failed\n")
        return False

    # Erase destination bank
    print_str("[boot] Erasing destination bank... ")
    pages: int32 = cast[int32](BANK_SIZE / FLASH_PAGE_SIZE)
    i: int32 = 0
    while i < pages:
        page_addr: uint32 = dst + cast[uint32](i) * FLASH_PAGE_SIZE
        if not _flash_erase_page(page_addr):
            print_str("FAILED\n")
            _flash_lock()
            return False
        i = i + 1
    print_str("OK\n")

    # Start XMODEM transfer
    _xmodem_block_num = 1
    retries: int32 = XMODEM_MAX_RETRIES

    # Send 'C' to request CRC mode
    while retries > 0:
        uart_putc(cast[char](XMODEM_CRC))

        result: int32 = _uart_getc_timeout(3000)
        if result == cast[int32](XMODEM_SOH) or result == cast[int32](XMODEM_STX):
            # Got start byte, put it back by handling it
            break
        retries = retries - 1

    if retries == 0:
        print_str("[boot] No response from sender\n")
        _flash_lock()
        return False

    # Receive blocks
    offset: uint32 = 0
    total_bytes: uint32 = 0

    while True:
        block_len: int32 = _xmodem_receive_block()

        if block_len == 0:
            # EOT received
            break
        elif block_len < 0:
            retries = retries - 1
            if retries == 0:
                print_str("[boot] Too many errors\n")
                _flash_lock()
                return False
            continue

        # Write block to flash
        words: int32 = block_len / 4
        src: Ptr[uint32] = cast[Ptr[uint32]](&_xmodem_buf[0])
        j: int32 = 0
        while j < words:
            word_addr: uint32 = dst + offset + cast[uint32](j * 4)
            if not _flash_write_word(word_addr, src[j]):
                print_str("[boot] Write failed\n")
                _flash_lock()
                return False
            j = j + 1

        offset = offset + cast[uint32](block_len)
        total_bytes = total_bytes + cast[uint32](block_len)

        # Progress indication
        if (total_bytes & 0x1FFF) == 0:
            print_str(".")

        retries = XMODEM_MAX_RETRIES  # Reset retry count on success

    _flash_lock()

    print_str("\n[boot] Received ")
    print_int(cast[int32](total_bytes))
    print_str(" bytes\n")

    # Validate received image
    print_str("[boot] Validating... ")
    if not bootloader_validate_image(dst):
        print_str("FAILED\n")
        return False
    print_str("OK\n")

    return True

def bootloader_set_progress_callback(callback: fn(int32, int32)):
    """Set callback function for update progress.

    Callback receives (current, total) progress values.
    """
    global _progress_callback
    _progress_callback = cast[Ptr[void]](callback)

# ============================================================================
# Boot Flow
# ============================================================================

# External assembly function for jumping to application
extern def _bootloader_jump_to_app_asm(msp: uint32, reset_vector: uint32)

def bootloader_jump_to_app(addr: uint32):
    """Jump to application at given address.

    Deinitializes peripherals, sets MSP and VTOR, then jumps.

    Args:
        addr: Base address of application (vector table)
    """
    header: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr + APP_HEADER_OFFSET)

    # Get entry point and vector table offset
    vtor_off: uint32 = header[HDR_OFF_VTOR / 4]
    entry_off: uint32 = header[HDR_OFF_ENTRY / 4]

    vtor_addr: uint32 = addr + vtor_off
    entry_addr: uint32 = addr + entry_off

    # Read initial MSP and reset vector from vector table
    vtor: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](vtor_addr)
    msp: uint32 = vtor[0]
    reset_handler: uint32 = vtor[1]

    # Use entry point from header if specified, otherwise reset vector
    if entry_addr != addr:
        reset_handler = entry_addr

    print_str("[boot] Jumping to app at 0x")
    print_hex(reset_handler)
    print_newline()

    # Disable interrupts
    state: int32 = critical_enter()

    # Deinitialize peripherals
    _deinit_peripherals()

    # Set VTOR to application vector table
    VTOR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED08)
    VTOR[0] = vtor_addr
    dsb()
    isb()

    # Jump to application (assembly helper)
    _bootloader_jump_to_app_asm(msp, reset_handler)

    # Should never reach here
    while True:
        pass

def _deinit_peripherals():
    """Deinitialize all peripherals before jumping to app."""
    # Disable SysTick
    SYSTICK_CTRL: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E010)
    SYSTICK_CTRL[0] = 0
    dsb()

    # Clear pending interrupts
    NVIC_ICPR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E280)
    i: int32 = 0
    while i < 8:
        NVIC_ICPR[i] = 0xFFFFFFFF
        i = i + 1

    # Disable all interrupts
    NVIC_ICER: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E180)
    i = 0
    while i < 8:
        NVIC_ICER[i] = 0xFFFFFFFF
        i = i + 1

    dsb()

# ============================================================================
# Recovery / DFU Mode
# ============================================================================

def bootloader_enter_dfu_mode():
    """Enter Device Firmware Update mode.

    Blinks LED and waits for UART update.
    Does not return unless update succeeds.
    """
    print_str("\n")
    print_str("*****************************\n")
    print_str("* PYNUX DFU MODE            *\n")
    print_str("*****************************\n")
    print_str("\n")
    print_str("Send firmware via XMODEM...\n")

    # Blink LED pattern
    led_state: bool = False
    blink_count: int32 = 0

    while True:
        # Check for incoming UART data
        if uart_available():
            if bootloader_update_from_uart():
                print_str("[boot] Update successful!\n")
                print_str("[boot] Swapping banks and rebooting...\n")

                bootloader_swap_banks()

                # Reset to boot new firmware
                AIRCR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED0C)
                AIRCR[0] = 0x05FA0004
                dsb()
                while True:
                    pass

        # LED blink
        blink_count = blink_count + 1
        if blink_count >= LED_BLINK_SLOW:
            led_state = not led_state
            if led_state:
                LED_GPIO_ADDR[0] = LED_GPIO_ADDR[0] | (1 << 25)  # LED on
            else:
                LED_GPIO_ADDR[0] = LED_GPIO_ADDR[0] & ~(1 << 25)  # LED off
            blink_count = 0

def _led_blink_error():
    """Blink LED in error pattern."""
    i: int32 = 0
    while i < 6:
        if (i & 1) == 0:
            LED_GPIO_ADDR[0] = LED_GPIO_ADDR[0] | (1 << 25)
        else:
            LED_GPIO_ADDR[0] = LED_GPIO_ADDR[0] & ~(1 << 25)

        # Delay
        delay: int32 = 0
        while delay < 100000:
            delay = delay + 1

        i = i + 1

# ============================================================================
# Main Bootloader Entry Point
# ============================================================================

def bootloader_main():
    """Main bootloader entry point.

    Called from reset handler before main application.
    """
    global _bootloader_initialized

    if _bootloader_initialized:
        return

    # Initialize CRC table early
    crc32_init()

    print_str("[boot] Pynux Bootloader v1.0\n")

    # Check for update request or button held
    enter_dfu: bool = False

    if bootloader_check_update_requested():
        print_str("[boot] Update requested\n")
        enter_dfu = True

    if bootloader_check_button_held():
        print_str("[boot] Boot button held\n")
        enter_dfu = True

    if enter_dfu:
        bootloader_enter_dfu_mode()
        # Does not return unless update succeeds
        return

    # Try to boot active bank
    active_addr: uint32 = bootloader_get_bank_addr(_active_bank)

    print_str("[boot] Checking bank ")
    print_int(_active_bank)
    print_str("... ")

    if bootloader_validate_image(active_addr):
        version: uint32 = bootloader_get_image_version(active_addr)
        print_str("valid (v")
        bootloader_print_version(version)
        print_str(")\n")

        bootloader_jump_to_app(active_addr)
        # Does not return
    else:
        print_str("invalid\n")

    # Try alternate bank
    alt_bank: int32 = 1 - _active_bank
    alt_addr: uint32 = bootloader_get_bank_addr(alt_bank)

    print_str("[boot] Trying bank ")
    print_int(alt_bank)
    print_str("... ")

    if bootloader_validate_image(alt_addr):
        version: uint32 = bootloader_get_image_version(alt_addr)
        print_str("valid (v")
        bootloader_print_version(version)
        print_str(")\n")

        # Switch to this bank
        bootloader_set_active_bank(alt_bank)
        bootloader_jump_to_app(alt_addr)
        # Does not return
    else:
        print_str("invalid\n")

    # No valid firmware - enter DFU mode
    print_str("[boot] No valid firmware found!\n")
    bootloader_enter_dfu_mode()

    _bootloader_initialized = True

# ============================================================================
# Diagnostics
# ============================================================================

def bootloader_print_status():
    """Print bootloader and firmware status."""
    print_str("[boot] Active bank: ")
    print_int(_active_bank)
    print_newline()

    # Bank 0 status
    print_str("[boot] Bank 0: ")
    if bootloader_validate_image(BANK0_BASE):
        version: uint32 = bootloader_get_image_version(BANK0_BASE)
        print_str("v")
        bootloader_print_version(version)
    else:
        print_str("invalid/empty")
    print_newline()

    # Bank 1 status
    print_str("[boot] Bank 1: ")
    if bootloader_validate_image(BANK1_BASE):
        version: uint32 = bootloader_get_image_version(BANK1_BASE)
        print_str("v")
        bootloader_print_version(version)
    else:
        print_str("invalid/empty")
    print_newline()
