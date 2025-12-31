# RP2040 Flash Hardware Abstraction Layer
#
# Flash programming driver for RP2040 using external QSPI flash.
# The RP2040 uses execute-in-place (XIP) from external flash memory
# connected via QSPI. Flash operations must be performed from RAM
# with XIP disabled.
#
# Memory Map:
#   XIP_BASE:      0x10000000 - Flash execute-in-place region
#   XIP_SSI_BASE:  0x18000000 - SSI (Synchronous Serial Interface)
#   XIP_CTRL_BASE: 0x14000000 - XIP cache control
#
# Flash characteristics:
#   - Sector size: 4096 bytes (4KB minimum erase)
#   - Page size: 256 bytes (maximum write per operation)
#   - Total size: Typically 2MB (W25Q16) on Pico board

# ============================================================================
# Base Addresses
# ============================================================================

XIP_BASE: uint32 = 0x10000000           # Flash memory-mapped region
XIP_SSI_BASE: uint32 = 0x18000000       # SSI controller for QSPI
XIP_CTRL_BASE: uint32 = 0x14000000      # XIP cache control

# Bootloader resides in first 256 bytes, protect it
BOOTLOADER_SIZE: uint32 = 0x100         # 256 bytes protected region
FLASH_START: uint32 = 0x00000000        # Flash offset start

# ============================================================================
# SSI Register Offsets (Synopsys DW_apb_ssi)
# ============================================================================

SSI_CTRLR0: uint32 = 0x00       # Control register 0
SSI_CTRLR1: uint32 = 0x04       # Control register 1
SSI_SSIENR: uint32 = 0x08       # SSI enable
SSI_MWCR: uint32 = 0x0C         # Microwire control
SSI_SER: uint32 = 0x10          # Slave enable
SSI_BAUDR: uint32 = 0x14        # Baud rate
SSI_TXFTLR: uint32 = 0x18       # TX FIFO threshold
SSI_RXFTLR: uint32 = 0x1C       # RX FIFO threshold
SSI_TXFLR: uint32 = 0x20        # TX FIFO level
SSI_RXFLR: uint32 = 0x24        # RX FIFO level
SSI_SR: uint32 = 0x28           # Status register
SSI_IMR: uint32 = 0x2C          # Interrupt mask
SSI_ISR: uint32 = 0x30          # Interrupt status
SSI_RISR: uint32 = 0x34         # Raw interrupt status
SSI_TXOICR: uint32 = 0x38       # TX FIFO overflow clear
SSI_RXOICR: uint32 = 0x3C       # RX FIFO overflow clear
SSI_RXUICR: uint32 = 0x40       # RX FIFO underflow clear
SSI_MSTICR: uint32 = 0x44       # Multi-master clear
SSI_ICR: uint32 = 0x48          # Interrupt clear
SSI_DMACR: uint32 = 0x4C        # DMA control
SSI_DMATDLR: uint32 = 0x50      # DMA TX data level
SSI_DMARDLR: uint32 = 0x54      # DMA RX data level
SSI_IDR: uint32 = 0x58          # Identification register
SSI_VERSION: uint32 = 0x5C      # Version register
SSI_DR0: uint32 = 0x60          # Data register 0
SSI_RX_SAMPLE_DLY: uint32 = 0xF0  # RX sample delay
SSI_SPI_CTRLR0: uint32 = 0xF4   # SPI control register

# ============================================================================
# XIP Control Registers
# ============================================================================

XIP_CTRL: uint32 = 0x00         # XIP control
XIP_FLUSH: uint32 = 0x04        # Cache flush
XIP_STAT: uint32 = 0x08         # Cache status

# ============================================================================
# SSI Status Register Bits
# ============================================================================

SSI_SR_BUSY: uint32 = 0x01      # SSI busy
SSI_SR_TFNF: uint32 = 0x02      # TX FIFO not full
SSI_SR_TFE: uint32 = 0x04       # TX FIFO empty
SSI_SR_RFNE: uint32 = 0x08      # RX FIFO not empty
SSI_SR_RFF: uint32 = 0x10       # RX FIFO full
SSI_SR_TXE: uint32 = 0x20       # Transmission error
SSI_SR_DCOL: uint32 = 0x40      # Data collision

# ============================================================================
# Flash Commands (Standard SPI NOR Flash)
# ============================================================================

FLASH_CMD_WRITE_ENABLE: uint8 = 0x06    # Write enable
FLASH_CMD_WRITE_DISABLE: uint8 = 0x04   # Write disable
FLASH_CMD_READ_STATUS: uint8 = 0x05     # Read status register 1
FLASH_CMD_READ_STATUS2: uint8 = 0x35    # Read status register 2
FLASH_CMD_WRITE_STATUS: uint8 = 0x01    # Write status register
FLASH_CMD_PAGE_PROGRAM: uint8 = 0x02    # Page program (256 bytes max)
FLASH_CMD_READ_DATA: uint8 = 0x03       # Read data
FLASH_CMD_FAST_READ: uint8 = 0x0B       # Fast read
FLASH_CMD_SECTOR_ERASE: uint8 = 0x20    # Sector erase (4KB)
FLASH_CMD_BLOCK_ERASE_32K: uint8 = 0x52 # Block erase (32KB)
FLASH_CMD_BLOCK_ERASE_64K: uint8 = 0xD8 # Block erase (64KB)
FLASH_CMD_CHIP_ERASE: uint8 = 0xC7      # Chip erase
FLASH_CMD_POWER_DOWN: uint8 = 0xB9      # Power down
FLASH_CMD_RELEASE_POWER: uint8 = 0xAB   # Release power down
FLASH_CMD_DEVICE_ID: uint8 = 0x90       # Manufacturer/device ID
FLASH_CMD_JEDEC_ID: uint8 = 0x9F        # JEDEC ID
FLASH_CMD_UNIQUE_ID: uint8 = 0x4B       # Unique ID (64-bit)

# ============================================================================
# Flash Status Register Bits
# ============================================================================

FLASH_STATUS_BUSY: uint8 = 0x01     # Write in progress
FLASH_STATUS_WEL: uint8 = 0x02      # Write enable latch
FLASH_STATUS_BP0: uint8 = 0x04      # Block protect bit 0
FLASH_STATUS_BP1: uint8 = 0x08      # Block protect bit 1
FLASH_STATUS_BP2: uint8 = 0x10      # Block protect bit 2
FLASH_STATUS_TB: uint8 = 0x20       # Top/bottom protect
FLASH_STATUS_SEC: uint8 = 0x40      # Sector protect
FLASH_STATUS_SRP: uint8 = 0x80      # Status register protect

# ============================================================================
# Flash Size Constants
# ============================================================================

FLASH_SECTOR_SIZE: uint32 = 4096    # 4KB sector (minimum erase)
FLASH_PAGE_SIZE: uint32 = 256       # 256 byte page (maximum program)
FLASH_BLOCK_SIZE_32K: uint32 = 32768
FLASH_BLOCK_SIZE_64K: uint32 = 65536

# Default flash size (2MB on Pico)
FLASH_SIZE_DEFAULT: uint32 = 2 * 1024 * 1024

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

# ============================================================================
# Internal SSI/Flash Communication (must run from RAM)
# ============================================================================

def _flash_wait_ssi_ready():
    """Wait for SSI to be idle."""
    while (mmio_read(XIP_SSI_BASE + SSI_SR) & SSI_SR_BUSY) != 0:
        pass

def _flash_wait_tx_empty():
    """Wait for TX FIFO to be empty."""
    while (mmio_read(XIP_SSI_BASE + SSI_SR) & SSI_SR_TFE) == 0:
        pass

def _flash_drain_rx():
    """Drain any data from RX FIFO."""
    while (mmio_read(XIP_SSI_BASE + SSI_SR) & SSI_SR_RFNE) != 0:
        dummy: uint32 = mmio_read(XIP_SSI_BASE + SSI_DR0)

def _flash_cs_force(high: bool):
    """Force chip select high or low.

    Note: In XIP mode, CS is automatic. For direct access,
    we control it via SSI enable/disable.
    """
    if high:
        # Disable SSI to deassert CS
        mmio_write(XIP_SSI_BASE + SSI_SSIENR, 0)
    else:
        # Enable SSI to assert CS
        mmio_write(XIP_SSI_BASE + SSI_SSIENR, 1)

def _flash_put_get(tx: uint8) -> uint8:
    """Send byte and receive response."""
    # Wait for TX FIFO space
    while (mmio_read(XIP_SSI_BASE + SSI_SR) & SSI_SR_TFNF) == 0:
        pass

    mmio_write(XIP_SSI_BASE + SSI_DR0, cast[uint32](tx))

    # Wait for RX data
    while (mmio_read(XIP_SSI_BASE + SSI_SR) & SSI_SR_RFNE) == 0:
        pass

    return cast[uint8](mmio_read(XIP_SSI_BASE + SSI_DR0) & 0xFF)

def _flash_do_cmd(cmd: uint8):
    """Execute single-byte flash command."""
    _flash_cs_force(False)
    _flash_put_get(cmd)
    _flash_wait_ssi_ready()
    _flash_cs_force(True)

# ============================================================================
# XIP Control Functions
# ============================================================================

def flash_xip_disable():
    """Disable XIP mode for direct flash access.

    CRITICAL: Must be called before any flash erase/program operations.
    Code calling this must be running from RAM, not flash!

    Disables interrupts as flash access will fail during XIP disable.
    """
    # Disable SSI
    mmio_write(XIP_SSI_BASE + SSI_SSIENR, 0)

    # Configure SSI for 1-bit SPI mode (standard SPI for commands)
    # CTRLR0: 8-bit data, SPI mode 0
    mmio_write(XIP_SSI_BASE + SSI_CTRLR0, 0x00070000)

    # Set baud rate divider (conservative for flash operations)
    mmio_write(XIP_SSI_BASE + SSI_BAUDR, 4)

    # Configure for TX/RX mode
    mmio_write(XIP_SSI_BASE + SSI_CTRLR1, 0)

    # Enable SSI
    mmio_write(XIP_SSI_BASE + SSI_SSIENR, 1)

def flash_xip_enable():
    """Re-enable XIP mode after flash operations.

    Restores normal execute-in-place operation.
    """
    # Disable SSI for reconfiguration
    mmio_write(XIP_SSI_BASE + SSI_SSIENR, 0)

    # Configure for QSPI XIP mode
    # This restores the boot configuration for XIP

    # CTRLR0: QSPI mode, 32-bit frames for address + data
    mmio_write(XIP_SSI_BASE + SSI_CTRLR0, 0x001F0300)

    # SPI_CTRLR0: Configure for QSPI read (command 0xEB)
    # 24-bit address, 8 wait cycles, QSPI mode
    mmio_write(XIP_SSI_BASE + SSI_SPI_CTRLR0, 0x03000218)

    # Enable SSI
    mmio_write(XIP_SSI_BASE + SSI_SSIENR, 1)

    # Flush XIP cache
    mmio_write(XIP_CTRL_BASE + XIP_FLUSH, 1)

def flash_flush_cache():
    """Flush XIP cache to ensure fresh reads after programming."""
    mmio_write(XIP_CTRL_BASE + XIP_FLUSH, 1)
    # Wait for flush complete
    while (mmio_read(XIP_CTRL_BASE + XIP_STAT) & 0x02) != 0:
        pass

# ============================================================================
# Flash Status Functions
# ============================================================================

def _flash_read_status() -> uint8:
    """Read flash status register."""
    _flash_cs_force(False)
    _flash_put_get(FLASH_CMD_READ_STATUS)
    status: uint8 = _flash_put_get(0)
    _flash_wait_ssi_ready()
    _flash_cs_force(True)
    return status

def _flash_wait_ready():
    """Wait for flash to complete current operation."""
    while (_flash_read_status() & FLASH_STATUS_BUSY) != 0:
        pass

def _flash_write_enable():
    """Enable write operations on flash."""
    _flash_do_cmd(FLASH_CMD_WRITE_ENABLE)

# ============================================================================
# Flash Information Functions
# ============================================================================

def flash_sector_size() -> uint32:
    """Get flash sector size (minimum erase unit).

    Returns:
        Sector size in bytes (4096)
    """
    return FLASH_SECTOR_SIZE

def flash_page_size() -> uint32:
    """Get flash page size (maximum program unit).

    Returns:
        Page size in bytes (256)
    """
    return FLASH_PAGE_SIZE

def flash_get_jedec_id() -> uint32:
    """Read JEDEC manufacturer and device ID.

    Returns:
        JEDEC ID (manufacturer in byte 0, memory type in byte 1, capacity in byte 2)

    Note: XIP must be disabled before calling this function.
    """
    _flash_cs_force(False)
    _flash_put_get(FLASH_CMD_JEDEC_ID)
    manufacturer: uint8 = _flash_put_get(0)
    mem_type: uint8 = _flash_put_get(0)
    capacity: uint8 = _flash_put_get(0)
    _flash_wait_ssi_ready()
    _flash_cs_force(True)

    jedec_id: uint32 = cast[uint32](manufacturer)
    jedec_id = jedec_id | (cast[uint32](mem_type) << 8)
    jedec_id = jedec_id | (cast[uint32](capacity) << 16)
    return jedec_id

def flash_unique_id(buffer: Ptr[uint8]):
    """Read 64-bit unique ID from flash.

    Args:
        buffer: Pointer to 8-byte buffer to receive unique ID

    Note: XIP must be disabled before calling this function.
    """
    _flash_cs_force(False)
    _flash_put_get(FLASH_CMD_UNIQUE_ID)

    # Send 4 dummy bytes (required by command)
    _flash_put_get(0)
    _flash_put_get(0)
    _flash_put_get(0)
    _flash_put_get(0)

    # Read 8 bytes of unique ID
    i: int32 = 0
    while i < 8:
        buffer[i] = _flash_put_get(0)
        i = i + 1

    _flash_wait_ssi_ready()
    _flash_cs_force(True)

# ============================================================================
# Flash Read Function
# ============================================================================

def flash_read(offset: uint32, buffer: Ptr[uint8], count: uint32):
    """Read data from flash.

    Can be used in either XIP mode (direct memory read) or
    with XIP disabled (SPI command read).

    Args:
        offset: Offset from flash start (0 = first byte of flash)
        buffer: Buffer to receive data
        count: Number of bytes to read

    Note: When XIP is enabled, this reads directly from memory.
          When XIP is disabled, it uses SPI read command.
    """
    # Check if XIP is enabled by checking SSI config
    ssi_enabled: uint32 = mmio_read(XIP_SSI_BASE + SSI_SSIENR)

    if ssi_enabled != 0:
        # XIP disabled, use SPI read command
        _flash_cs_force(False)
        _flash_put_get(FLASH_CMD_READ_DATA)

        # Send 24-bit address
        _flash_put_get(cast[uint8]((offset >> 16) & 0xFF))
        _flash_put_get(cast[uint8]((offset >> 8) & 0xFF))
        _flash_put_get(cast[uint8](offset & 0xFF))

        # Read data
        i: uint32 = 0
        while i < count:
            buffer[i] = _flash_put_get(0)
            i = i + 1

        _flash_wait_ssi_ready()
        _flash_cs_force(True)
    else:
        # XIP enabled, read directly from memory
        flash_addr: uint32 = XIP_BASE + offset
        src: Ptr[volatile uint8] = cast[Ptr[volatile uint8]](flash_addr)
        i: uint32 = 0
        while i < count:
            buffer[i] = src[i]
            i = i + 1

# ============================================================================
# Flash Erase Functions
# ============================================================================

def _flash_sector_erase(offset: uint32):
    """Erase single 4KB sector (internal, no safety checks).

    Args:
        offset: Sector-aligned offset from flash start
    """
    _flash_write_enable()

    _flash_cs_force(False)
    _flash_put_get(FLASH_CMD_SECTOR_ERASE)

    # Send 24-bit address
    _flash_put_get(cast[uint8]((offset >> 16) & 0xFF))
    _flash_put_get(cast[uint8]((offset >> 8) & 0xFF))
    _flash_put_get(cast[uint8](offset & 0xFF))

    _flash_wait_ssi_ready()
    _flash_cs_force(True)

    # Wait for erase to complete
    _flash_wait_ready()

def flash_range_erase(offset: uint32, count: uint32) -> bool:
    """Erase range of flash sectors.

    Erases flash in 4KB sectors. The offset and count will be
    aligned to sector boundaries.

    Args:
        offset: Starting offset (will be aligned down to sector)
        count: Number of bytes to erase (will be aligned up to sector)

    Returns:
        True if erase succeeded, False if protection violation

    Note: XIP MUST be disabled before calling this function.
          This function should be called from RAM code.

    Safety:
        - Will not erase bootloader region (first 256 bytes)
        - Caller must ensure XIP is disabled and interrupts are off
    """
    # Align offset down to sector boundary
    sector_offset: uint32 = offset & ~(FLASH_SECTOR_SIZE - 1)

    # Protect bootloader region
    if sector_offset < BOOTLOADER_SIZE:
        # Cannot erase bootloader sector
        return False

    # Calculate end offset, aligned up
    end_offset: uint32 = offset + count
    if (end_offset & (FLASH_SECTOR_SIZE - 1)) != 0:
        end_offset = (end_offset + FLASH_SECTOR_SIZE) & ~(FLASH_SECTOR_SIZE - 1)

    # Erase sectors
    current: uint32 = sector_offset
    while current < end_offset:
        _flash_sector_erase(current)
        current = current + FLASH_SECTOR_SIZE

    return True

def flash_block_erase_32k(offset: uint32):
    """Erase 32KB block.

    Args:
        offset: Block-aligned offset (must be 32KB aligned)

    Note: XIP must be disabled. Does not check bootloader protection.
    """
    _flash_write_enable()

    _flash_cs_force(False)
    _flash_put_get(FLASH_CMD_BLOCK_ERASE_32K)

    _flash_put_get(cast[uint8]((offset >> 16) & 0xFF))
    _flash_put_get(cast[uint8]((offset >> 8) & 0xFF))
    _flash_put_get(cast[uint8](offset & 0xFF))

    _flash_wait_ssi_ready()
    _flash_cs_force(True)

    _flash_wait_ready()

def flash_block_erase_64k(offset: uint32):
    """Erase 64KB block.

    Args:
        offset: Block-aligned offset (must be 64KB aligned)

    Note: XIP must be disabled. Does not check bootloader protection.
    """
    _flash_write_enable()

    _flash_cs_force(False)
    _flash_put_get(FLASH_CMD_BLOCK_ERASE_64K)

    _flash_put_get(cast[uint8]((offset >> 16) & 0xFF))
    _flash_put_get(cast[uint8]((offset >> 8) & 0xFF))
    _flash_put_get(cast[uint8](offset & 0xFF))

    _flash_wait_ssi_ready()
    _flash_cs_force(True)

    _flash_wait_ready()

# ============================================================================
# Flash Program Functions
# ============================================================================

def _flash_page_program(offset: uint32, data: Ptr[uint8], len: uint32):
    """Program single page (internal, no safety checks).

    Args:
        offset: Page-aligned offset
        data: Data to write
        len: Number of bytes (must not cross page boundary)
    """
    _flash_write_enable()

    _flash_cs_force(False)
    _flash_put_get(FLASH_CMD_PAGE_PROGRAM)

    # Send 24-bit address
    _flash_put_get(cast[uint8]((offset >> 16) & 0xFF))
    _flash_put_get(cast[uint8]((offset >> 8) & 0xFF))
    _flash_put_get(cast[uint8](offset & 0xFF))

    # Send data
    i: uint32 = 0
    while i < len:
        _flash_put_get(data[i])
        i = i + 1

    _flash_wait_ssi_ready()
    _flash_cs_force(True)

    # Wait for program to complete
    _flash_wait_ready()

def flash_range_program(offset: uint32, data: Ptr[uint8], count: uint32) -> bool:
    """Program data to flash.

    Programs data in 256-byte pages. Flash must be erased first
    (all 0xFF). Programming can only change 1s to 0s.

    Args:
        offset: Starting offset (does not need to be page-aligned)
        data: Data to program
        count: Number of bytes to program

    Returns:
        True if program succeeded, False if protection violation

    Note: XIP MUST be disabled before calling this function.
          This function should be called from RAM code.

    Safety:
        - Will not program bootloader region (first 256 bytes)
        - Caller must ensure XIP is disabled and interrupts are off
    """
    # Protect bootloader region
    if offset < BOOTLOADER_SIZE:
        return False

    current_offset: uint32 = offset
    data_index: uint32 = 0
    remaining: uint32 = count

    while remaining > 0:
        # Calculate bytes to page boundary
        page_offset: uint32 = current_offset & (FLASH_PAGE_SIZE - 1)
        page_remaining: uint32 = FLASH_PAGE_SIZE - page_offset

        # Program up to end of page or end of data
        write_len: uint32 = remaining
        if write_len > page_remaining:
            write_len = page_remaining

        # Program this chunk
        data_ptr: Ptr[uint8] = cast[Ptr[uint8]](cast[uint32](data) + data_index)
        _flash_page_program(current_offset, data_ptr, write_len)

        current_offset = current_offset + write_len
        data_index = data_index + write_len
        remaining = remaining - write_len

    return True

# ============================================================================
# Flash Convenience Functions
# ============================================================================

def flash_erase_sector(sector: uint32) -> bool:
    """Erase a single sector by sector number.

    Args:
        sector: Sector number (sector 0 is at offset 0)

    Returns:
        True if erase succeeded, False if protection violation
    """
    offset: uint32 = sector * FLASH_SECTOR_SIZE

    # Protect bootloader
    if offset < BOOTLOADER_SIZE:
        return False

    _flash_sector_erase(offset)
    return True

def flash_program_page(page: uint32, data: Ptr[uint8]) -> bool:
    """Program a full 256-byte page.

    Args:
        page: Page number (page 0 is at offset 0)
        data: Pointer to 256 bytes of data

    Returns:
        True if program succeeded, False if protection violation
    """
    offset: uint32 = page * FLASH_PAGE_SIZE

    # Protect bootloader
    if offset < BOOTLOADER_SIZE:
        return False

    _flash_page_program(offset, data, FLASH_PAGE_SIZE)
    return True

def flash_write_byte(offset: uint32, value: uint8) -> bool:
    """Program single byte (inefficient, use for small updates only).

    Note: The sector containing this byte must already be erased.
    This is inefficient as flash can only be written in pages.

    Args:
        offset: Byte offset
        value: Value to write

    Returns:
        True if program succeeded
    """
    if offset < BOOTLOADER_SIZE:
        return False

    _flash_write_enable()

    _flash_cs_force(False)
    _flash_put_get(FLASH_CMD_PAGE_PROGRAM)

    _flash_put_get(cast[uint8]((offset >> 16) & 0xFF))
    _flash_put_get(cast[uint8]((offset >> 8) & 0xFF))
    _flash_put_get(cast[uint8](offset & 0xFF))
    _flash_put_get(value)

    _flash_wait_ssi_ready()
    _flash_cs_force(True)

    _flash_wait_ready()
    return True

# ============================================================================
# Power Management
# ============================================================================

def flash_power_down():
    """Put flash into low-power mode.

    Flash will not respond to commands until flash_power_up() is called.
    """
    _flash_do_cmd(FLASH_CMD_POWER_DOWN)

def flash_power_up():
    """Wake flash from low-power mode.

    Should wait a few microseconds after this before issuing commands.
    """
    _flash_do_cmd(FLASH_CMD_RELEASE_POWER)
