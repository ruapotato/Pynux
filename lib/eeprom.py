# Pynux EEPROM Emulation Library
#
# EEPROM storage emulation for ARM Cortex-M3.
# Provides persistent byte/word storage with page organization,
# simple wear leveling, and CRC integrity checking.
#
# Emulated via ramfs file on QEMU, would use hardware EEPROM
# or flash on real hardware.

from lib.io import print_str, print_int, print_newline
from lib.memory import alloc, free, memset, memcpy
from lib.string import strlen, strcpy

# ============================================================================
# EEPROM Hardware Registers (placeholder for real hardware)
# ============================================================================

EEPROM_BASE: uint32 = 0x40080000

# Register offsets
EEPROM_CTRL_OFFSET: uint32 = 0x00    # Control register
EEPROM_STATUS_OFFSET: uint32 = 0x04  # Status register
EEPROM_ADDR_OFFSET: uint32 = 0x08    # Address register
EEPROM_DATA_OFFSET: uint32 = 0x0C    # Data register
EEPROM_CMD_OFFSET: uint32 = 0x10     # Command register

# Control bits
EEPROM_CTRL_ENABLE: uint32 = 0x01
EEPROM_CTRL_WRITE: uint32 = 0x02
EEPROM_CTRL_ERASE: uint32 = 0x04

# Status bits
EEPROM_STATUS_BUSY: uint32 = 0x01
EEPROM_STATUS_ERROR: uint32 = 0x02
EEPROM_STATUS_READY: uint32 = 0x04

# ============================================================================
# EEPROM Configuration
# ============================================================================

# Default EEPROM size (1KB)
EEPROM_DEFAULT_SIZE: int32 = 1024

# Page size for write operations
EEPROM_PAGE_SIZE: int32 = 32

# Maximum EEPROM size (8KB)
EEPROM_MAX_SIZE: int32 = 8192

# Header size for metadata
EEPROM_HEADER_SIZE: int32 = 16

# Magic number for validity check
EEPROM_MAGIC: uint32 = 0xEE01EE01

# ============================================================================
# EEPROM State
# ============================================================================

# Emulation mode flag
_eeprom_emulated: bool = True

# EEPROM data buffer (used for emulation)
_eeprom_buffer: Ptr[uint8] = Ptr[uint8](0)

# Configuration
_eeprom_size: int32 = 0
_eeprom_page_count: int32 = 0
_eeprom_initialized: bool = False

# File path for persistence
_eeprom_file_path: Array[64, char]
_eeprom_file_enabled: bool = False

# Wear leveling: write count per page
_page_write_counts: Ptr[int32] = Ptr[int32](0)

# Statistics
_eeprom_read_count: int32 = 0
_eeprom_write_count: int32 = 0
_eeprom_erase_count: int32 = 0

# ============================================================================
# CRC-16 Implementation
# ============================================================================

# CRC-16 CCITT polynomial
CRC16_POLY: uint32 = 0x1021

def crc16_byte(crc: uint32, data: uint8) -> uint32:
    """Update CRC-16 with one byte."""
    crc = crc ^ (cast[uint32](data) << 8)

    i: int32 = 0
    while i < 8:
        if (crc & 0x8000) != 0:
            crc = (crc << 1) ^ CRC16_POLY
        else:
            crc = crc << 1
        crc = crc & 0xFFFF
        i = i + 1

    return crc

def crc16_calc(data: Ptr[uint8], length: int32) -> uint32:
    """Calculate CRC-16 over data.

    Args:
        data: Pointer to data
        length: Number of bytes

    Returns:
        16-bit CRC value
    """
    crc: uint32 = 0xFFFF

    i: int32 = 0
    while i < length:
        crc = crc16_byte(crc, data[i])
        i = i + 1

    return crc

# ============================================================================
# Initialization
# ============================================================================

def eeprom_init(size: int32, emulated: bool) -> bool:
    """Initialize EEPROM emulation.

    Args:
        size: EEPROM size in bytes (will be page-aligned)
        emulated: True for software emulation via ramfs

    Returns:
        True if initialization successful
    """
    global _eeprom_buffer, _eeprom_size, _eeprom_page_count
    global _eeprom_emulated, _eeprom_initialized
    global _page_write_counts
    global _eeprom_read_count, _eeprom_write_count, _eeprom_erase_count

    if _eeprom_initialized:
        return True

    # Validate size
    if size <= 0:
        size = EEPROM_DEFAULT_SIZE
    if size > EEPROM_MAX_SIZE:
        size = EEPROM_MAX_SIZE

    # Align to page size
    _eeprom_size = ((size + EEPROM_PAGE_SIZE - 1) / EEPROM_PAGE_SIZE) * EEPROM_PAGE_SIZE
    _eeprom_page_count = _eeprom_size / EEPROM_PAGE_SIZE
    _eeprom_emulated = emulated

    state: int32 = critical_enter()

    if emulated:
        # Allocate buffer for emulation
        _eeprom_buffer = alloc(_eeprom_size)
        if _eeprom_buffer == Ptr[uint8](0):
            critical_exit(state)
            return False

        # Initialize buffer to 0xFF (erased state)
        memset(_eeprom_buffer, 0xFF, _eeprom_size)

        # Allocate wear leveling counters
        _page_write_counts = cast[Ptr[int32]](alloc(_eeprom_page_count * 4))
        if _page_write_counts == Ptr[int32](0):
            free(_eeprom_buffer)
            _eeprom_buffer = Ptr[uint8](0)
            critical_exit(state)
            return False

        # Initialize write counts
        i: int32 = 0
        while i < _eeprom_page_count:
            _page_write_counts[i] = 0
            i = i + 1
    else:
        # Hardware EEPROM - enable peripheral
        ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_CTRL_OFFSET)
        ptr[0] = EEPROM_CTRL_ENABLE

    # Reset statistics
    _eeprom_read_count = 0
    _eeprom_write_count = 0
    _eeprom_erase_count = 0

    _eeprom_initialized = True

    critical_exit(state)
    return True

def eeprom_deinit():
    """Deinitialize EEPROM and free resources."""
    global _eeprom_buffer, _eeprom_initialized
    global _page_write_counts

    if not _eeprom_initialized:
        return

    # Save to file if enabled
    if _eeprom_file_enabled:
        eeprom_save_to_file()

    state: int32 = critical_enter()

    if _eeprom_emulated:
        if _eeprom_buffer != Ptr[uint8](0):
            free(_eeprom_buffer)
            _eeprom_buffer = Ptr[uint8](0)

        if _page_write_counts != Ptr[int32](0):
            free(cast[Ptr[uint8]](_page_write_counts))
            _page_write_counts = Ptr[int32](0)
    else:
        # Disable hardware
        ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_CTRL_OFFSET)
        ptr[0] = 0

    _eeprom_initialized = False

    critical_exit(state)

# ============================================================================
# Byte Operations
# ============================================================================

def eeprom_read_byte(addr: int32) -> int32:
    """Read a single byte from EEPROM.

    Args:
        addr: Address to read from

    Returns:
        Byte value (0-255), or -1 on error
    """
    global _eeprom_read_count

    if not _eeprom_initialized:
        return -1

    if addr < 0 or addr >= _eeprom_size:
        return -1

    _eeprom_read_count = _eeprom_read_count + 1

    if _eeprom_emulated:
        return cast[int32](_eeprom_buffer[addr])
    else:
        # Hardware read
        addr_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_ADDR_OFFSET)
        data_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_DATA_OFFSET)

        addr_ptr[0] = cast[uint32](addr)
        return cast[int32](data_ptr[0] & 0xFF)

def eeprom_write_byte(addr: int32, value: uint8) -> bool:
    """Write a single byte to EEPROM.

    Args:
        addr: Address to write to
        value: Byte value to write

    Returns:
        True if write successful
    """
    global _eeprom_write_count

    if not _eeprom_initialized:
        return False

    if addr < 0 or addr >= _eeprom_size:
        return False

    _eeprom_write_count = _eeprom_write_count + 1

    if _eeprom_emulated:
        _eeprom_buffer[addr] = value

        # Update wear leveling counter
        page: int32 = addr / EEPROM_PAGE_SIZE
        if _page_write_counts != Ptr[int32](0):
            _page_write_counts[page] = _page_write_counts[page] + 1

        return True
    else:
        # Hardware write
        state: int32 = critical_enter()

        addr_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_ADDR_OFFSET)
        data_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_DATA_OFFSET)
        ctrl_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_CTRL_OFFSET)
        status_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_STATUS_OFFSET)

        addr_ptr[0] = cast[uint32](addr)
        data_ptr[0] = cast[uint32](value)
        ctrl_ptr[0] = EEPROM_CTRL_ENABLE | EEPROM_CTRL_WRITE

        # Wait for write to complete
        timeout: int32 = 10000
        while timeout > 0:
            if (status_ptr[0] & EEPROM_STATUS_BUSY) == 0:
                break
            timeout = timeout - 1

        critical_exit(state)

        return timeout > 0

def eeprom_read_bytes(addr: int32, buf: Ptr[uint8], count: int32) -> int32:
    """Read multiple bytes from EEPROM.

    Args:
        addr: Starting address
        buf: Buffer to read into
        count: Number of bytes to read

    Returns:
        Number of bytes read, or -1 on error
    """
    if not _eeprom_initialized:
        return -1

    if addr < 0 or addr >= _eeprom_size:
        return -1

    # Limit count to available data
    if addr + count > _eeprom_size:
        count = _eeprom_size - addr

    if count <= 0:
        return 0

    if _eeprom_emulated:
        memcpy(buf, &_eeprom_buffer[addr], count)
    else:
        i: int32 = 0
        while i < count:
            val: int32 = eeprom_read_byte(addr + i)
            if val < 0:
                return i
            buf[i] = cast[uint8](val)
            i = i + 1

    return count

def eeprom_write_bytes(addr: int32, data: Ptr[uint8], count: int32) -> int32:
    """Write multiple bytes to EEPROM.

    Args:
        addr: Starting address
        data: Data to write
        count: Number of bytes to write

    Returns:
        Number of bytes written, or -1 on error
    """
    if not _eeprom_initialized:
        return -1

    if addr < 0 or addr >= _eeprom_size:
        return -1

    # Limit count to available space
    if addr + count > _eeprom_size:
        count = _eeprom_size - addr

    if count <= 0:
        return 0

    if _eeprom_emulated:
        memcpy(&_eeprom_buffer[addr], data, count)

        # Update wear leveling counters
        start_page: int32 = addr / EEPROM_PAGE_SIZE
        end_page: int32 = (addr + count - 1) / EEPROM_PAGE_SIZE

        p: int32 = start_page
        while p <= end_page:
            if _page_write_counts != Ptr[int32](0):
                _page_write_counts[p] = _page_write_counts[p] + 1
            p = p + 1

        return count
    else:
        i: int32 = 0
        while i < count:
            if not eeprom_write_byte(addr + i, data[i]):
                return i
            i = i + 1
        return count

# ============================================================================
# Integer Operations
# ============================================================================

def eeprom_read_int32(addr: int32) -> int32:
    """Read a 32-bit integer from EEPROM.

    Args:
        addr: Address (must be 4-byte aligned for efficiency)

    Returns:
        Integer value, or 0 on error
    """
    if addr < 0 or addr + 4 > _eeprom_size:
        return 0

    b0: int32 = eeprom_read_byte(addr)
    b1: int32 = eeprom_read_byte(addr + 1)
    b2: int32 = eeprom_read_byte(addr + 2)
    b3: int32 = eeprom_read_byte(addr + 3)

    if b0 < 0 or b1 < 0 or b2 < 0 or b3 < 0:
        return 0

    # Little-endian
    return b0 | (b1 << 8) | (b2 << 16) | (b3 << 24)

def eeprom_write_int32(addr: int32, value: int32) -> bool:
    """Write a 32-bit integer to EEPROM.

    Args:
        addr: Address (must be 4-byte aligned for efficiency)
        value: Integer value to write

    Returns:
        True if write successful
    """
    if addr < 0 or addr + 4 > _eeprom_size:
        return False

    # Little-endian
    ok: bool = True
    ok = ok and eeprom_write_byte(addr, cast[uint8](value & 0xFF))
    ok = ok and eeprom_write_byte(addr + 1, cast[uint8]((value >> 8) & 0xFF))
    ok = ok and eeprom_write_byte(addr + 2, cast[uint8]((value >> 16) & 0xFF))
    ok = ok and eeprom_write_byte(addr + 3, cast[uint8]((value >> 24) & 0xFF))

    return ok

def eeprom_read_uint32(addr: int32) -> uint32:
    """Read an unsigned 32-bit integer from EEPROM.

    Args:
        addr: Address

    Returns:
        Unsigned integer value
    """
    return cast[uint32](eeprom_read_int32(addr))

def eeprom_write_uint32(addr: int32, value: uint32) -> bool:
    """Write an unsigned 32-bit integer to EEPROM.

    Args:
        addr: Address
        value: Unsigned integer value

    Returns:
        True if write successful
    """
    return eeprom_write_int32(addr, cast[int32](value))

def eeprom_read_int16(addr: int32) -> int32:
    """Read a 16-bit integer from EEPROM.

    Args:
        addr: Address

    Returns:
        Integer value (signed 16-bit, sign-extended)
    """
    if addr < 0 or addr + 2 > _eeprom_size:
        return 0

    b0: int32 = eeprom_read_byte(addr)
    b1: int32 = eeprom_read_byte(addr + 1)

    if b0 < 0 or b1 < 0:
        return 0

    value: int32 = b0 | (b1 << 8)

    # Sign extend
    if (value & 0x8000) != 0:
        value = value | 0xFFFF0000

    return value

def eeprom_write_int16(addr: int32, value: int32) -> bool:
    """Write a 16-bit integer to EEPROM.

    Args:
        addr: Address
        value: Integer value (lower 16 bits used)

    Returns:
        True if write successful
    """
    if addr < 0 or addr + 2 > _eeprom_size:
        return False

    ok: bool = True
    ok = ok and eeprom_write_byte(addr, cast[uint8](value & 0xFF))
    ok = ok and eeprom_write_byte(addr + 1, cast[uint8]((value >> 8) & 0xFF))

    return ok

# ============================================================================
# Page Operations
# ============================================================================

def eeprom_read_page(page: int32, buf: Ptr[uint8]) -> bool:
    """Read an entire page from EEPROM.

    Args:
        page: Page number
        buf: Buffer to read into (must be EEPROM_PAGE_SIZE bytes)

    Returns:
        True if read successful
    """
    if page < 0 or page >= _eeprom_page_count:
        return False

    addr: int32 = page * EEPROM_PAGE_SIZE
    count: int32 = eeprom_read_bytes(addr, buf, EEPROM_PAGE_SIZE)

    return count == EEPROM_PAGE_SIZE

def eeprom_write_page(page: int32, data: Ptr[uint8]) -> bool:
    """Write an entire page to EEPROM.

    Args:
        page: Page number
        data: Data to write (must be EEPROM_PAGE_SIZE bytes)

    Returns:
        True if write successful
    """
    if page < 0 or page >= _eeprom_page_count:
        return False

    addr: int32 = page * EEPROM_PAGE_SIZE
    count: int32 = eeprom_write_bytes(addr, data, EEPROM_PAGE_SIZE)

    return count == EEPROM_PAGE_SIZE

def eeprom_erase_page(page: int32) -> bool:
    """Erase a page (set all bytes to 0xFF).

    Args:
        page: Page number

    Returns:
        True if erase successful
    """
    global _eeprom_erase_count

    if page < 0 or page >= _eeprom_page_count:
        return False

    _eeprom_erase_count = _eeprom_erase_count + 1

    if _eeprom_emulated:
        addr: int32 = page * EEPROM_PAGE_SIZE
        memset(&_eeprom_buffer[addr], 0xFF, EEPROM_PAGE_SIZE)
        return True
    else:
        # Hardware page erase
        state: int32 = critical_enter()

        addr_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_ADDR_OFFSET)
        ctrl_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_CTRL_OFFSET)
        status_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](EEPROM_BASE + EEPROM_STATUS_OFFSET)

        addr_ptr[0] = cast[uint32](page * EEPROM_PAGE_SIZE)
        ctrl_ptr[0] = EEPROM_CTRL_ENABLE | EEPROM_CTRL_ERASE

        # Wait for erase to complete
        timeout: int32 = 100000  # Erase takes longer
        while timeout > 0:
            if (status_ptr[0] & EEPROM_STATUS_BUSY) == 0:
                break
            timeout = timeout - 1

        critical_exit(state)

        return timeout > 0

def eeprom_erase_all() -> bool:
    """Erase entire EEPROM (set all bytes to 0xFF).

    Returns:
        True if erase successful
    """
    global _eeprom_erase_count

    if not _eeprom_initialized:
        return False

    _eeprom_erase_count = _eeprom_erase_count + _eeprom_page_count

    if _eeprom_emulated:
        memset(_eeprom_buffer, 0xFF, _eeprom_size)

        # Reset wear leveling counters
        i: int32 = 0
        while i < _eeprom_page_count:
            if _page_write_counts != Ptr[int32](0):
                _page_write_counts[i] = 0
            i = i + 1

        return True
    else:
        i: int32 = 0
        while i < _eeprom_page_count:
            if not eeprom_erase_page(i):
                return False
            i = i + 1
        return True

# ============================================================================
# Wear Leveling
# ============================================================================

def eeprom_get_page_writes(page: int32) -> int32:
    """Get write count for a specific page.

    Args:
        page: Page number

    Returns:
        Write count, or -1 on error
    """
    if not _eeprom_emulated or page < 0 or page >= _eeprom_page_count:
        return -1

    if _page_write_counts == Ptr[int32](0):
        return -1

    return _page_write_counts[page]

def eeprom_find_least_worn_page() -> int32:
    """Find the page with the least number of writes.

    Useful for wear leveling when allocating new data.

    Returns:
        Page number with least writes, or -1 on error
    """
    if not _eeprom_emulated or _page_write_counts == Ptr[int32](0):
        return -1

    min_writes: int32 = 0x7FFFFFFF
    min_page: int32 = 0

    i: int32 = 0
    while i < _eeprom_page_count:
        if _page_write_counts[i] < min_writes:
            min_writes = _page_write_counts[i]
            min_page = i
        i = i + 1

    return min_page

def eeprom_find_most_worn_page() -> int32:
    """Find the page with the most number of writes.

    Returns:
        Page number with most writes, or -1 on error
    """
    if not _eeprom_emulated or _page_write_counts == Ptr[int32](0):
        return -1

    max_writes: int32 = 0
    max_page: int32 = 0

    i: int32 = 0
    while i < _eeprom_page_count:
        if _page_write_counts[i] > max_writes:
            max_writes = _page_write_counts[i]
            max_page = i
        i = i + 1

    return max_page

def eeprom_get_wear_variance() -> int32:
    """Get variance in page wear (max - min writes).

    Low variance indicates good wear leveling.

    Returns:
        Difference between most and least worn pages
    """
    if not _eeprom_emulated or _page_write_counts == Ptr[int32](0):
        return -1

    min_writes: int32 = 0x7FFFFFFF
    max_writes: int32 = 0

    i: int32 = 0
    while i < _eeprom_page_count:
        if _page_write_counts[i] < min_writes:
            min_writes = _page_write_counts[i]
        if _page_write_counts[i] > max_writes:
            max_writes = _page_write_counts[i]
        i = i + 1

    return max_writes - min_writes

# ============================================================================
# CRC Integrity Functions
# ============================================================================

def eeprom_read_with_crc(addr: int32, buf: Ptr[uint8], count: int32) -> bool:
    """Read data with CRC verification.

    The data format is: [data][crc16_hi][crc16_lo]
    So the actual data is count-2 bytes.

    Args:
        addr: Starting address
        buf: Buffer to read into
        count: Number of data bytes (CRC is stored after)

    Returns:
        True if data valid (CRC matches)
    """
    if count <= 0:
        return False

    # Read data and CRC
    data_count: int32 = eeprom_read_bytes(addr, buf, count)
    if data_count != count:
        return False

    # Read stored CRC
    crc_hi: int32 = eeprom_read_byte(addr + count)
    crc_lo: int32 = eeprom_read_byte(addr + count + 1)

    if crc_hi < 0 or crc_lo < 0:
        return False

    stored_crc: uint32 = cast[uint32](crc_hi << 8) | cast[uint32](crc_lo)

    # Calculate CRC of data
    calc_crc: uint32 = crc16_calc(buf, count)

    return calc_crc == stored_crc

def eeprom_write_with_crc(addr: int32, data: Ptr[uint8], count: int32) -> bool:
    """Write data with CRC for integrity verification.

    Writes data followed by 2-byte CRC.

    Args:
        addr: Starting address
        data: Data to write
        count: Number of data bytes

    Returns:
        True if write successful
    """
    if count <= 0 or addr + count + 2 > _eeprom_size:
        return False

    # Calculate CRC
    crc: uint32 = crc16_calc(data, count)

    # Write data
    written: int32 = eeprom_write_bytes(addr, data, count)
    if written != count:
        return False

    # Write CRC
    if not eeprom_write_byte(addr + count, cast[uint8]((crc >> 8) & 0xFF)):
        return False
    if not eeprom_write_byte(addr + count + 1, cast[uint8](crc & 0xFF)):
        return False

    return True

def eeprom_verify_crc(addr: int32, count: int32) -> bool:
    """Verify CRC of stored data without reading into buffer.

    Args:
        addr: Starting address of data
        count: Number of data bytes (CRC stored after)

    Returns:
        True if CRC valid
    """
    if count <= 0 or addr + count + 2 > _eeprom_size:
        return False

    # Calculate CRC of data in place
    crc: uint32 = 0xFFFF

    i: int32 = 0
    while i < count:
        val: int32 = eeprom_read_byte(addr + i)
        if val < 0:
            return False
        crc = crc16_byte(crc, cast[uint8](val))
        i = i + 1

    # Read stored CRC
    crc_hi: int32 = eeprom_read_byte(addr + count)
    crc_lo: int32 = eeprom_read_byte(addr + count + 1)

    if crc_hi < 0 or crc_lo < 0:
        return False

    stored_crc: uint32 = cast[uint32](crc_hi << 8) | cast[uint32](crc_lo)

    return crc == stored_crc

# ============================================================================
# File Persistence
# ============================================================================

def eeprom_set_file(path: Ptr[char]):
    """Set file path for EEPROM persistence.

    Args:
        path: Path to ramfs file
    """
    global _eeprom_file_enabled

    i: int32 = 0
    while path[i] != '\0' and i < 62:
        _eeprom_file_path[i] = path[i]
        i = i + 1
    _eeprom_file_path[i] = '\0'

    _eeprom_file_enabled = True

def eeprom_save_to_file() -> bool:
    """Save EEPROM contents to ramfs file.

    Returns:
        True if save successful
    """
    if not _eeprom_file_enabled or not _eeprom_emulated:
        return False

    if _eeprom_buffer == Ptr[uint8](0):
        return False

    # Write binary data as hex string (simple approach)
    # Format: size as hex, then data bytes as hex
    result: int32 = ramfs_write_binary(&_eeprom_file_path[0], _eeprom_buffer, _eeprom_size)

    return result == _eeprom_size

def eeprom_load_from_file() -> bool:
    """Load EEPROM contents from ramfs file.

    Returns:
        True if load successful
    """
    if not _eeprom_file_enabled or not _eeprom_emulated:
        return False

    if _eeprom_buffer == Ptr[uint8](0):
        return False

    result: int32 = ramfs_read_binary(&_eeprom_file_path[0], _eeprom_buffer, _eeprom_size)

    return result > 0

# ============================================================================
# Statistics and Debug
# ============================================================================

def eeprom_get_size() -> int32:
    """Get EEPROM size in bytes."""
    return _eeprom_size

def eeprom_get_page_count() -> int32:
    """Get number of pages."""
    return _eeprom_page_count

def eeprom_get_page_size() -> int32:
    """Get page size in bytes."""
    return EEPROM_PAGE_SIZE

def eeprom_get_read_count() -> int32:
    """Get total read operation count."""
    return _eeprom_read_count

def eeprom_get_write_count() -> int32:
    """Get total write operation count."""
    return _eeprom_write_count

def eeprom_get_erase_count() -> int32:
    """Get total erase operation count."""
    return _eeprom_erase_count

def eeprom_is_initialized() -> bool:
    """Check if EEPROM is initialized."""
    return _eeprom_initialized

def eeprom_print_status():
    """Print EEPROM status information."""
    print_str("EEPROM Status:\n")

    print_str("  Initialized: ")
    if _eeprom_initialized:
        print_str("yes\n")
    else:
        print_str("no\n")
        return

    print_str("  Emulated: ")
    if _eeprom_emulated:
        print_str("yes\n")
    else:
        print_str("no\n")

    print_str("  Size: ")
    print_int(_eeprom_size)
    print_str(" bytes\n")

    print_str("  Pages: ")
    print_int(_eeprom_page_count)
    print_str(" x ")
    print_int(EEPROM_PAGE_SIZE)
    print_str(" bytes\n")

    print_str("  Read count: ")
    print_int(_eeprom_read_count)
    print_newline()

    print_str("  Write count: ")
    print_int(_eeprom_write_count)
    print_newline()

    print_str("  Erase count: ")
    print_int(_eeprom_erase_count)
    print_newline()

    if _eeprom_emulated and _page_write_counts != Ptr[int32](0):
        print_str("  Wear variance: ")
        print_int(eeprom_get_wear_variance())
        print_newline()

        print_str("  Least worn page: ")
        print_int(eeprom_find_least_worn_page())
        print_newline()

        print_str("  Most worn page: ")
        print_int(eeprom_find_most_worn_page())
        print_newline()

    if _eeprom_file_enabled:
        print_str("  Persistence file: ")
        print_str(&_eeprom_file_path[0])
        print_newline()

def eeprom_hexdump(start: int32, count: int32):
    """Print hex dump of EEPROM contents.

    Args:
        start: Starting address
        count: Number of bytes to dump
    """
    if not _eeprom_initialized:
        print_str("EEPROM not initialized\n")
        return

    if start < 0:
        start = 0
    if start >= _eeprom_size:
        return
    if start + count > _eeprom_size:
        count = _eeprom_size - start

    print_str("EEPROM dump @ ")
    print_int(start)
    print_str(", ")
    print_int(count)
    print_str(" bytes:\n")

    i: int32 = 0
    while i < count:
        # Print address every 16 bytes
        if (i % 16) == 0:
            print_int(start + i)
            print_str(": ")

        # Read and print byte
        val: int32 = eeprom_read_byte(start + i)
        if val >= 0:
            hex_chars: Array[17, char]
            hex_chars[0] = '0'
            hex_chars[1] = '1'
            hex_chars[2] = '2'
            hex_chars[3] = '3'
            hex_chars[4] = '4'
            hex_chars[5] = '5'
            hex_chars[6] = '6'
            hex_chars[7] = '7'
            hex_chars[8] = '8'
            hex_chars[9] = '9'
            hex_chars[10] = 'A'
            hex_chars[11] = 'B'
            hex_chars[12] = 'C'
            hex_chars[13] = 'D'
            hex_chars[14] = 'E'
            hex_chars[15] = 'F'
            hex_chars[16] = '\0'

            buf: Array[4, char]
            buf[0] = hex_chars[(val >> 4) & 0x0F]
            buf[1] = hex_chars[val & 0x0F]
            buf[2] = ' '
            buf[3] = '\0'
            print_str(&buf[0])
        else:
            print_str("?? ")

        # Newline every 16 bytes
        if ((i + 1) % 16) == 0 or i == count - 1:
            print_newline()

        i = i + 1

# External function references
extern def critical_enter() -> int32
extern def critical_exit(state: int32)
extern def ramfs_write_binary(path: Ptr[char], data: Ptr[uint8], size: int32) -> int32
extern def ramfs_read_binary(path: Ptr[char], buf: Ptr[uint8], size: int32) -> int32
