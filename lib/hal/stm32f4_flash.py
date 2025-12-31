# STM32F4 Flash Hardware Abstraction Layer
#
# Internal flash programming driver for STM32F405/F407 microcontrollers.
# The STM32F4 has internal flash with sector-based erase. Sector sizes
# vary depending on the sector number.
#
# Memory Map:
#   FLASH_BASE:     0x08000000 - Flash memory
#   FLASH_REG_BASE: 0x40023C00 - Flash interface registers
#
# Flash organization (STM32F405/407 with 1MB flash):
#   Sector 0-3:   16KB each  (0x08000000 - 0x0800FFFF)
#   Sector 4:     64KB       (0x08010000 - 0x0801FFFF)
#   Sector 5-11:  128KB each (0x08020000 - 0x080FFFFF)

# ============================================================================
# Base Addresses
# ============================================================================

FLASH_BASE: uint32 = 0x08000000         # Flash memory start
FLASH_REG_BASE: uint32 = 0x40023C00     # Flash interface registers
FLASH_END: uint32 = 0x080FFFFF          # End of 1MB flash

# Bootloader protection (first 16KB sector)
BOOTLOADER_SIZE: uint32 = 0x4000        # 16KB bootloader region

# ============================================================================
# Flash Register Offsets
# ============================================================================

FLASH_ACR: uint32 = 0x00    # Flash access control register
FLASH_KEYR: uint32 = 0x04   # Flash key register
FLASH_OPTKEYR: uint32 = 0x08  # Option key register
FLASH_SR: uint32 = 0x0C     # Flash status register
FLASH_CR: uint32 = 0x10     # Flash control register
FLASH_OPTCR: uint32 = 0x14  # Option control register
FLASH_OPTCR1: uint32 = 0x18 # Option control register 1 (F42x/F43x)

# ============================================================================
# Flash Access Control Register (FLASH_ACR) Bits
# ============================================================================

FLASH_ACR_LATENCY_MASK: uint32 = 0x0F   # Latency mask
FLASH_ACR_LATENCY_0WS: uint32 = 0x00    # 0 wait states
FLASH_ACR_LATENCY_1WS: uint32 = 0x01    # 1 wait state
FLASH_ACR_LATENCY_2WS: uint32 = 0x02    # 2 wait states
FLASH_ACR_LATENCY_3WS: uint32 = 0x03    # 3 wait states
FLASH_ACR_LATENCY_4WS: uint32 = 0x04    # 4 wait states
FLASH_ACR_LATENCY_5WS: uint32 = 0x05    # 5 wait states
FLASH_ACR_LATENCY_6WS: uint32 = 0x06    # 6 wait states
FLASH_ACR_LATENCY_7WS: uint32 = 0x07    # 7 wait states
FLASH_ACR_PRFTEN: uint32 = 0x100        # Prefetch enable
FLASH_ACR_ICEN: uint32 = 0x200          # Instruction cache enable
FLASH_ACR_DCEN: uint32 = 0x400          # Data cache enable
FLASH_ACR_ICRST: uint32 = 0x800         # Instruction cache reset
FLASH_ACR_DCRST: uint32 = 0x1000        # Data cache reset

# ============================================================================
# Flash Key Values
# ============================================================================

FLASH_KEY1: uint32 = 0x45670123         # Flash unlock key 1
FLASH_KEY2: uint32 = 0xCDEF89AB         # Flash unlock key 2
FLASH_OPT_KEY1: uint32 = 0x08192A3B     # Option byte unlock key 1
FLASH_OPT_KEY2: uint32 = 0x4C5D6E7F     # Option byte unlock key 2

# ============================================================================
# Flash Status Register (FLASH_SR) Bits
# ============================================================================

FLASH_SR_EOP: uint32 = 0x01         # End of operation
FLASH_SR_OPERR: uint32 = 0x02       # Operation error
FLASH_SR_WRPERR: uint32 = 0x10      # Write protection error
FLASH_SR_PGAERR: uint32 = 0x20      # Programming alignment error
FLASH_SR_PGPERR: uint32 = 0x40      # Programming parallelism error
FLASH_SR_PGSERR: uint32 = 0x80      # Programming sequence error
FLASH_SR_BSY: uint32 = 0x10000      # Busy

# All error flags combined
FLASH_SR_ERRORS: uint32 = 0xF2      # All error bits

# ============================================================================
# Flash Control Register (FLASH_CR) Bits
# ============================================================================

FLASH_CR_PG: uint32 = 0x01          # Programming
FLASH_CR_SER: uint32 = 0x02         # Sector erase
FLASH_CR_MER: uint32 = 0x04         # Mass erase
FLASH_CR_SNB_SHIFT: uint32 = 3      # Sector number shift
FLASH_CR_SNB_MASK: uint32 = 0x78    # Sector number mask (bits 3-6)
FLASH_CR_PSIZE_SHIFT: uint32 = 8    # Program size shift
FLASH_CR_PSIZE_MASK: uint32 = 0x300 # Program size mask
FLASH_CR_PSIZE_X8: uint32 = 0x000   # 8-bit parallelism
FLASH_CR_PSIZE_X16: uint32 = 0x100  # 16-bit parallelism
FLASH_CR_PSIZE_X32: uint32 = 0x200  # 32-bit parallelism
FLASH_CR_PSIZE_X64: uint32 = 0x300  # 64-bit parallelism
FLASH_CR_STRT: uint32 = 0x10000     # Start erase
FLASH_CR_EOPIE: uint32 = 0x1000000  # End of operation interrupt enable
FLASH_CR_ERRIE: uint32 = 0x2000000  # Error interrupt enable
FLASH_CR_LOCK: uint32 = 0x80000000  # Lock

# ============================================================================
# Flash Option Control Register (FLASH_OPTCR) Bits
# ============================================================================

FLASH_OPTCR_OPTLOCK: uint32 = 0x01      # Option lock
FLASH_OPTCR_OPTSTRT: uint32 = 0x02      # Option start
FLASH_OPTCR_BOR_SHIFT: uint32 = 2       # BOR level shift
FLASH_OPTCR_BOR_MASK: uint32 = 0x0C     # BOR level mask
FLASH_OPTCR_BOR_OFF: uint32 = 0x0C      # BOR off
FLASH_OPTCR_BOR_LEV3: uint32 = 0x00     # BOR level 3 (2.70-3.60V)
FLASH_OPTCR_BOR_LEV2: uint32 = 0x04     # BOR level 2 (2.40-2.70V)
FLASH_OPTCR_BOR_LEV1: uint32 = 0x08     # BOR level 1 (2.10-2.40V)
FLASH_OPTCR_WDG_SW: uint32 = 0x20       # Software watchdog
FLASH_OPTCR_nRST_STOP: uint32 = 0x40    # No reset on stop
FLASH_OPTCR_nRST_STDBY: uint32 = 0x80   # No reset on standby
FLASH_OPTCR_RDP_SHIFT: uint32 = 8       # Read protection shift
FLASH_OPTCR_RDP_MASK: uint32 = 0xFF00   # Read protection mask
FLASH_OPTCR_RDP_LEVEL_0: uint32 = 0xAA00  # No protection
FLASH_OPTCR_RDP_LEVEL_1: uint32 = 0x0000  # Read protection
FLASH_OPTCR_RDP_LEVEL_2: uint32 = 0xCC00  # Full protection (irreversible!)
FLASH_OPTCR_nWRP_SHIFT: uint32 = 16     # Write protection shift
FLASH_OPTCR_nWRP_MASK: uint32 = 0x0FFF0000  # Write protection mask

# ============================================================================
# Flash Sector Information
# ============================================================================

# Sector sizes in bytes (STM32F405/407 1MB flash)
FLASH_SECTOR_SIZE_16K: uint32 = 16384   # 16KB
FLASH_SECTOR_SIZE_64K: uint32 = 65536   # 64KB
FLASH_SECTOR_SIZE_128K: uint32 = 131072 # 128KB

# Sector start addresses
FLASH_SECTOR_0_ADDR: uint32 = 0x08000000
FLASH_SECTOR_1_ADDR: uint32 = 0x08004000
FLASH_SECTOR_2_ADDR: uint32 = 0x08008000
FLASH_SECTOR_3_ADDR: uint32 = 0x0800C000
FLASH_SECTOR_4_ADDR: uint32 = 0x08010000
FLASH_SECTOR_5_ADDR: uint32 = 0x08020000
FLASH_SECTOR_6_ADDR: uint32 = 0x08040000
FLASH_SECTOR_7_ADDR: uint32 = 0x08060000
FLASH_SECTOR_8_ADDR: uint32 = 0x08080000
FLASH_SECTOR_9_ADDR: uint32 = 0x080A0000
FLASH_SECTOR_10_ADDR: uint32 = 0x080C0000
FLASH_SECTOR_11_ADDR: uint32 = 0x080E0000

# Total number of sectors
FLASH_SECTOR_COUNT: uint32 = 12

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    """Read from memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    """Write to memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def mmio_read8(addr: uint32) -> uint8:
    """Read byte from memory-mapped I/O."""
    ptr: Ptr[volatile uint8] = cast[Ptr[volatile uint8]](addr)
    return ptr[0]

def mmio_write8(addr: uint32, val: uint8):
    """Write byte to memory-mapped I/O."""
    ptr: Ptr[volatile uint8] = cast[Ptr[volatile uint8]](addr)
    ptr[0] = val

def mmio_read16(addr: uint32) -> uint16:
    """Read halfword from memory-mapped I/O."""
    ptr: Ptr[volatile uint16] = cast[Ptr[volatile uint16]](addr)
    return ptr[0]

def mmio_write16(addr: uint32, val: uint16):
    """Write halfword to memory-mapped I/O."""
    ptr: Ptr[volatile uint16] = cast[Ptr[volatile uint16]](addr)
    ptr[0] = val

# ============================================================================
# Flash Lock/Unlock Functions
# ============================================================================

def flash_unlock() -> bool:
    """Unlock flash for programming/erase operations.

    Must be called before any flash modification operations.
    Flash is locked on reset for protection.

    Returns:
        True if unlock succeeded, False if already unlocked or failed
    """
    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)

    # Check if already unlocked
    if (cr & FLASH_CR_LOCK) == 0:
        return True

    # Write unlock sequence
    mmio_write(FLASH_REG_BASE + FLASH_KEYR, FLASH_KEY1)
    mmio_write(FLASH_REG_BASE + FLASH_KEYR, FLASH_KEY2)

    # Verify unlock
    cr = mmio_read(FLASH_REG_BASE + FLASH_CR)
    return (cr & FLASH_CR_LOCK) == 0

def flash_lock():
    """Lock flash to prevent accidental modifications.

    Should be called after completing flash operations.
    """
    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr | FLASH_CR_LOCK)

def flash_is_locked() -> bool:
    """Check if flash is locked.

    Returns:
        True if flash is locked
    """
    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)
    return (cr & FLASH_CR_LOCK) != 0

# ============================================================================
# Option Byte Lock/Unlock Functions
# ============================================================================

def flash_option_unlock() -> bool:
    """Unlock option bytes for modification.

    Must be called before modifying option bytes.

    Returns:
        True if unlock succeeded
    """
    optcr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_OPTCR)

    # Check if already unlocked
    if (optcr & FLASH_OPTCR_OPTLOCK) == 0:
        return True

    # Write unlock sequence
    mmio_write(FLASH_REG_BASE + FLASH_OPTKEYR, FLASH_OPT_KEY1)
    mmio_write(FLASH_REG_BASE + FLASH_OPTKEYR, FLASH_OPT_KEY2)

    # Verify unlock
    optcr = mmio_read(FLASH_REG_BASE + FLASH_OPTCR)
    return (optcr & FLASH_OPTCR_OPTLOCK) == 0

def flash_option_lock():
    """Lock option bytes."""
    optcr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_OPTCR)
    mmio_write(FLASH_REG_BASE + FLASH_OPTCR, optcr | FLASH_OPTCR_OPTLOCK)

# ============================================================================
# Flash Status and Wait Functions
# ============================================================================

def flash_wait_busy():
    """Wait for flash operation to complete.

    Polls the BSY flag until it clears.
    """
    while (mmio_read(FLASH_REG_BASE + FLASH_SR) & FLASH_SR_BSY) != 0:
        pass

def flash_wait_busy_timeout(timeout: uint32) -> bool:
    """Wait for flash operation with timeout.

    Args:
        timeout: Maximum iterations to wait

    Returns:
        True if operation completed, False if timeout
    """
    count: uint32 = 0
    while (mmio_read(FLASH_REG_BASE + FLASH_SR) & FLASH_SR_BSY) != 0:
        count = count + 1
        if count >= timeout:
            return False
    return True

def flash_clear_errors():
    """Clear all flash error flags.

    Should be called before starting a new operation.
    """
    sr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_SR)
    # Write 1 to clear error flags
    mmio_write(FLASH_REG_BASE + FLASH_SR, sr & FLASH_SR_ERRORS)

def flash_get_error() -> uint32:
    """Get current flash error flags.

    Returns:
        Error flags from status register
    """
    return mmio_read(FLASH_REG_BASE + FLASH_SR) & FLASH_SR_ERRORS

def flash_has_error() -> bool:
    """Check if any flash error occurred.

    Returns:
        True if any error flag is set
    """
    return (mmio_read(FLASH_REG_BASE + FLASH_SR) & FLASH_SR_ERRORS) != 0

# ============================================================================
# Flash Sector Information Functions
# ============================================================================

def flash_get_sector(addr: uint32) -> int32:
    """Get sector number for a given address.

    Args:
        addr: Flash address

    Returns:
        Sector number (0-11), or -1 if address is invalid
    """
    if addr < FLASH_BASE or addr > FLASH_END:
        return -1

    offset: uint32 = addr - FLASH_BASE

    # Sectors 0-3: 16KB each (0x00000 - 0x0FFFF)
    if offset < 0x10000:
        return cast[int32](offset / FLASH_SECTOR_SIZE_16K)

    # Sector 4: 64KB (0x10000 - 0x1FFFF)
    if offset < 0x20000:
        return 4

    # Sectors 5-11: 128KB each (0x20000 - 0xFFFFF)
    return cast[int32](5 + ((offset - 0x20000) / FLASH_SECTOR_SIZE_128K))

def flash_get_sector_size(sector: uint32) -> uint32:
    """Get size of a sector in bytes.

    Args:
        sector: Sector number (0-11)

    Returns:
        Sector size in bytes, or 0 if invalid sector
    """
    if sector > 11:
        return 0

    if sector < 4:
        return FLASH_SECTOR_SIZE_16K    # 16KB
    elif sector == 4:
        return FLASH_SECTOR_SIZE_64K    # 64KB
    else:
        return FLASH_SECTOR_SIZE_128K   # 128KB

def flash_get_sector_address(sector: uint32) -> uint32:
    """Get start address of a sector.

    Args:
        sector: Sector number (0-11)

    Returns:
        Sector start address, or 0 if invalid sector
    """
    if sector > 11:
        return 0

    if sector == 0:
        return FLASH_SECTOR_0_ADDR
    elif sector == 1:
        return FLASH_SECTOR_1_ADDR
    elif sector == 2:
        return FLASH_SECTOR_2_ADDR
    elif sector == 3:
        return FLASH_SECTOR_3_ADDR
    elif sector == 4:
        return FLASH_SECTOR_4_ADDR
    elif sector == 5:
        return FLASH_SECTOR_5_ADDR
    elif sector == 6:
        return FLASH_SECTOR_6_ADDR
    elif sector == 7:
        return FLASH_SECTOR_7_ADDR
    elif sector == 8:
        return FLASH_SECTOR_8_ADDR
    elif sector == 9:
        return FLASH_SECTOR_9_ADDR
    elif sector == 10:
        return FLASH_SECTOR_10_ADDR
    else:
        return FLASH_SECTOR_11_ADDR

# ============================================================================
# Flash Erase Functions
# ============================================================================

def flash_erase_sector(sector: uint32) -> bool:
    """Erase a flash sector.

    Args:
        sector: Sector number (0-11)

    Returns:
        True if erase succeeded, False if error or protection

    Note: Flash must be unlocked before calling this function.

    Safety:
        - Will not erase sector 0 (bootloader) without explicit confirmation
    """
    if sector > 11:
        return False

    # Protect bootloader (sector 0)
    if sector == 0:
        # Bootloader protection - require explicit unlock
        return False

    # Wait for any ongoing operation
    flash_wait_busy()

    # Clear error flags
    flash_clear_errors()

    # Configure for sector erase
    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)

    # Clear sector number and set new sector
    cr = cr & ~FLASH_CR_SNB_MASK
    cr = cr | ((sector << FLASH_CR_SNB_SHIFT) & FLASH_CR_SNB_MASK)

    # Set sector erase and parallelism (32-bit)
    cr = cr | FLASH_CR_SER | FLASH_CR_PSIZE_X32

    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    # Start erase
    cr = cr | FLASH_CR_STRT
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    # Wait for completion
    flash_wait_busy()

    # Clear SER bit
    cr = mmio_read(FLASH_REG_BASE + FLASH_CR)
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr & ~FLASH_CR_SER)

    # Check for errors
    return not flash_has_error()

def flash_erase_sector_force(sector: uint32) -> bool:
    """Erase a flash sector, including bootloader sector.

    DANGER: This can erase the bootloader if sector 0 is specified!
    Use with extreme caution.

    Args:
        sector: Sector number (0-11)

    Returns:
        True if erase succeeded
    """
    if sector > 11:
        return False

    flash_wait_busy()
    flash_clear_errors()

    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)
    cr = cr & ~FLASH_CR_SNB_MASK
    cr = cr | ((sector << FLASH_CR_SNB_SHIFT) & FLASH_CR_SNB_MASK)
    cr = cr | FLASH_CR_SER | FLASH_CR_PSIZE_X32
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    cr = cr | FLASH_CR_STRT
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    flash_wait_busy()

    cr = mmio_read(FLASH_REG_BASE + FLASH_CR)
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr & ~FLASH_CR_SER)

    return not flash_has_error()

def flash_mass_erase() -> bool:
    """Erase entire flash memory.

    DANGER: This erases ALL flash including bootloader!
    Device will be unbootable until reprogrammed via debug interface.

    Returns:
        True if erase succeeded
    """
    flash_wait_busy()
    flash_clear_errors()

    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)
    cr = cr | FLASH_CR_MER | FLASH_CR_PSIZE_X32
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    cr = cr | FLASH_CR_STRT
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    flash_wait_busy()

    cr = mmio_read(FLASH_REG_BASE + FLASH_CR)
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr & ~FLASH_CR_MER)

    return not flash_has_error()

# ============================================================================
# Flash Program Functions
# ============================================================================

def flash_program_word(addr: uint32, data: uint32) -> bool:
    """Program a 32-bit word to flash.

    Flash must be erased (all 0xFF) at the target location.
    Programming can only change 1s to 0s.

    Args:
        addr: Word-aligned flash address
        data: 32-bit data to program

    Returns:
        True if program succeeded, False if error or protection

    Note: Flash must be unlocked before calling this function.

    Safety:
        - Will not program bootloader region (sector 0)
    """
    # Protection check
    sector: int32 = flash_get_sector(addr)
    if sector < 0:
        return False
    if sector == 0:
        # Bootloader protection
        return False

    # Wait for any ongoing operation
    flash_wait_busy()

    # Clear error flags
    flash_clear_errors()

    # Configure for 32-bit programming
    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)
    cr = cr & ~FLASH_CR_PSIZE_MASK
    cr = cr | FLASH_CR_PSIZE_X32 | FLASH_CR_PG
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    # Write data
    mmio_write(addr, data)

    # Wait for completion
    flash_wait_busy()

    # Clear PG bit
    cr = mmio_read(FLASH_REG_BASE + FLASH_CR)
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr & ~FLASH_CR_PG)

    # Verify and check errors
    if flash_has_error():
        return False

    return mmio_read(addr) == data

def flash_program_halfword(addr: uint32, data: uint16) -> bool:
    """Program a 16-bit halfword to flash.

    Args:
        addr: Halfword-aligned flash address
        data: 16-bit data to program

    Returns:
        True if program succeeded
    """
    sector: int32 = flash_get_sector(addr)
    if sector < 0:
        return False
    if sector == 0:
        return False

    flash_wait_busy()
    flash_clear_errors()

    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)
    cr = cr & ~FLASH_CR_PSIZE_MASK
    cr = cr | FLASH_CR_PSIZE_X16 | FLASH_CR_PG
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    mmio_write16(addr, data)

    flash_wait_busy()

    cr = mmio_read(FLASH_REG_BASE + FLASH_CR)
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr & ~FLASH_CR_PG)

    if flash_has_error():
        return False

    return mmio_read16(addr) == data

def flash_program_byte(addr: uint32, data: uint8) -> bool:
    """Program a single byte to flash.

    Args:
        addr: Flash address
        data: Byte to program

    Returns:
        True if program succeeded
    """
    sector: int32 = flash_get_sector(addr)
    if sector < 0:
        return False
    if sector == 0:
        return False

    flash_wait_busy()
    flash_clear_errors()

    cr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_CR)
    cr = cr & ~FLASH_CR_PSIZE_MASK
    cr = cr | FLASH_CR_PSIZE_X8 | FLASH_CR_PG
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr)

    mmio_write8(addr, data)

    flash_wait_busy()

    cr = mmio_read(FLASH_REG_BASE + FLASH_CR)
    mmio_write(FLASH_REG_BASE + FLASH_CR, cr & ~FLASH_CR_PG)

    if flash_has_error():
        return False

    return mmio_read8(addr) == data

# ============================================================================
# Flash Read Functions
# ============================================================================

def flash_read_word(addr: uint32) -> uint32:
    """Read a 32-bit word from flash.

    Args:
        addr: Word-aligned flash address

    Returns:
        32-bit value at address
    """
    return mmio_read(addr)

def flash_read_halfword(addr: uint32) -> uint16:
    """Read a 16-bit halfword from flash.

    Args:
        addr: Halfword-aligned flash address

    Returns:
        16-bit value at address
    """
    return mmio_read16(addr)

def flash_read_byte(addr: uint32) -> uint8:
    """Read a byte from flash.

    Args:
        addr: Flash address

    Returns:
        Byte at address
    """
    return mmio_read8(addr)

def flash_read(addr: uint32, buffer: Ptr[uint8], count: uint32):
    """Read data from flash into buffer.

    Args:
        addr: Start address in flash
        buffer: Destination buffer
        count: Number of bytes to read
    """
    src: Ptr[volatile uint8] = cast[Ptr[volatile uint8]](addr)
    i: uint32 = 0
    while i < count:
        buffer[i] = src[i]
        i = i + 1

# ============================================================================
# Flash Program Buffer Functions
# ============================================================================

def flash_program_buffer(addr: uint32, data: Ptr[uint8], count: uint32) -> bool:
    """Program buffer to flash using optimal word alignment.

    Automatically handles alignment and uses 32-bit writes where possible.

    Args:
        addr: Start address in flash
        data: Data buffer to program
        count: Number of bytes

    Returns:
        True if all programming succeeded
    """
    current_addr: uint32 = addr
    data_idx: uint32 = 0
    remaining: uint32 = count

    # Handle initial unaligned bytes
    while remaining > 0 and (current_addr & 3) != 0:
        if not flash_program_byte(current_addr, data[data_idx]):
            return False
        current_addr = current_addr + 1
        data_idx = data_idx + 1
        remaining = remaining - 1

    # Program aligned words
    while remaining >= 4:
        word: uint32 = cast[uint32](data[data_idx])
        word = word | (cast[uint32](data[data_idx + 1]) << 8)
        word = word | (cast[uint32](data[data_idx + 2]) << 16)
        word = word | (cast[uint32](data[data_idx + 3]) << 24)

        if not flash_program_word(current_addr, word):
            return False

        current_addr = current_addr + 4
        data_idx = data_idx + 4
        remaining = remaining - 4

    # Handle trailing bytes
    while remaining > 0:
        if not flash_program_byte(current_addr, data[data_idx]):
            return False
        current_addr = current_addr + 1
        data_idx = data_idx + 1
        remaining = remaining - 1

    return True

# ============================================================================
# Option Byte Functions
# ============================================================================

def flash_option_read() -> uint32:
    """Read current option control register value.

    Returns:
        FLASH_OPTCR register value
    """
    return mmio_read(FLASH_REG_BASE + FLASH_OPTCR)

def flash_option_get_rdp() -> uint8:
    """Get current read protection level.

    Returns:
        Read protection level byte
    """
    optcr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_OPTCR)
    return cast[uint8]((optcr & FLASH_OPTCR_RDP_MASK) >> FLASH_OPTCR_RDP_SHIFT)

def flash_option_get_wrp() -> uint32:
    """Get write protection bits.

    Returns:
        Write protection bits (bit set = sector NOT protected)
    """
    optcr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_OPTCR)
    return (optcr & FLASH_OPTCR_nWRP_MASK) >> FLASH_OPTCR_nWRP_SHIFT

def flash_option_set_wrp(sectors: uint32) -> bool:
    """Set write protection for sectors.

    Args:
        sectors: Bit mask of sectors to protect (bit set = protected)

    Returns:
        True if successful

    Note: Option bytes must be unlocked first.
    """
    flash_wait_busy()

    optcr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_OPTCR)

    # nWRP bits are inverted (0 = protected)
    wrp_bits: uint32 = ~sectors & 0x0FFF
    optcr = optcr & ~FLASH_OPTCR_nWRP_MASK
    optcr = optcr | ((wrp_bits << FLASH_OPTCR_nWRP_SHIFT) & FLASH_OPTCR_nWRP_MASK)

    mmio_write(FLASH_REG_BASE + FLASH_OPTCR, optcr)

    # Start option byte programming
    optcr = optcr | FLASH_OPTCR_OPTSTRT
    mmio_write(FLASH_REG_BASE + FLASH_OPTCR, optcr)

    flash_wait_busy()

    return not flash_has_error()

def flash_option_set_bor(level: uint32) -> bool:
    """Set brown-out reset level.

    Args:
        level: BOR level (FLASH_OPTCR_BOR_*)

    Returns:
        True if successful
    """
    flash_wait_busy()

    optcr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_OPTCR)
    optcr = optcr & ~FLASH_OPTCR_BOR_MASK
    optcr = optcr | (level & FLASH_OPTCR_BOR_MASK)

    mmio_write(FLASH_REG_BASE + FLASH_OPTCR, optcr)

    optcr = optcr | FLASH_OPTCR_OPTSTRT
    mmio_write(FLASH_REG_BASE + FLASH_OPTCR, optcr)

    flash_wait_busy()

    return not flash_has_error()

# ============================================================================
# Flash Cache Control
# ============================================================================

def flash_enable_cache():
    """Enable instruction and data cache."""
    acr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_ACR)
    acr = acr | FLASH_ACR_ICEN | FLASH_ACR_DCEN
    mmio_write(FLASH_REG_BASE + FLASH_ACR, acr)

def flash_disable_cache():
    """Disable instruction and data cache."""
    acr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_ACR)
    acr = acr & ~(FLASH_ACR_ICEN | FLASH_ACR_DCEN)
    mmio_write(FLASH_REG_BASE + FLASH_ACR, acr)

def flash_flush_cache():
    """Flush and reset caches.

    Should be called after programming flash to ensure
    fresh data is read.
    """
    acr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_ACR)

    # Disable caches
    mmio_write(FLASH_REG_BASE + FLASH_ACR, acr & ~(FLASH_ACR_ICEN | FLASH_ACR_DCEN))

    # Reset caches
    mmio_write(FLASH_REG_BASE + FLASH_ACR, acr | FLASH_ACR_ICRST | FLASH_ACR_DCRST)

    # Re-enable caches
    mmio_write(FLASH_REG_BASE + FLASH_ACR, acr)

def flash_enable_prefetch():
    """Enable prefetch buffer."""
    acr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_ACR)
    mmio_write(FLASH_REG_BASE + FLASH_ACR, acr | FLASH_ACR_PRFTEN)

def flash_set_latency(latency: uint32):
    """Set flash access latency (wait states).

    Required when changing system clock frequency.

    Args:
        latency: Number of wait states (0-7)
    """
    acr: uint32 = mmio_read(FLASH_REG_BASE + FLASH_ACR)
    acr = acr & ~FLASH_ACR_LATENCY_MASK
    acr = acr | (latency & FLASH_ACR_LATENCY_MASK)
    mmio_write(FLASH_REG_BASE + FLASH_ACR, acr)
