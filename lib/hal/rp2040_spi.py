# RP2040 SPI Hardware Abstraction Layer
#
# Hardware SPI driver for RP2040 using PL022 SPI controller.
# Supports SPI0 and SPI1 in master mode.
#
# Default pins:
#   SPI0: GPIO16 (RX/MISO), GPIO17 (CSn), GPIO18 (SCK), GPIO19 (TX/MOSI)
#   SPI1: GPIO8 (RX/MISO), GPIO9 (CSn), GPIO10 (SCK), GPIO11 (TX/MOSI)

# ============================================================================
# Base Addresses
# ============================================================================

SPI0_BASE: uint32 = 0x4003C000
SPI1_BASE: uint32 = 0x40040000

IO_BANK0_BASE: uint32 = 0x40014000
RESETS_BASE: uint32 = 0x4000C000

# ============================================================================
# SPI Register Offsets (PL022)
# ============================================================================

SPI_SSPCR0: uint32 = 0x00     # Control register 0
SPI_SSPCR1: uint32 = 0x04     # Control register 1
SPI_SSPDR: uint32 = 0x08      # Data register
SPI_SSPSR: uint32 = 0x0C      # Status register
SPI_SSPCPSR: uint32 = 0x10    # Clock prescaler
SPI_SSPIMSC: uint32 = 0x14    # Interrupt mask set/clear
SPI_SSPRIS: uint32 = 0x18     # Raw interrupt status
SPI_SSPMIS: uint32 = 0x1C     # Masked interrupt status
SPI_SSPICR: uint32 = 0x20     # Interrupt clear register
SPI_SSPDMACR: uint32 = 0x24   # DMA control register

# CR0 bits
SPI_CR0_DSS_8: uint32 = 0x07    # 8-bit data (7 = 8 bits)
SPI_CR0_FRF_SPI: uint32 = 0x00  # Motorola SPI frame format
SPI_CR0_SPO: uint32 = 0x40      # CPOL
SPI_CR0_SPH: uint32 = 0x80      # CPHA
SPI_CR0_SCR_SHIFT: uint32 = 8   # Serial clock rate shift

# CR1 bits
SPI_CR1_LBM: uint32 = 0x01      # Loopback mode
SPI_CR1_SSE: uint32 = 0x02      # SPI enable
SPI_CR1_MS: uint32 = 0x04       # Master/slave (0=master)
SPI_CR1_SOD: uint32 = 0x08      # Slave output disable

# Status register bits
SPI_SR_TFE: uint32 = 0x01       # TX FIFO empty
SPI_SR_TNF: uint32 = 0x02       # TX FIFO not full
SPI_SR_RNE: uint32 = 0x04       # RX FIFO not empty
SPI_SR_RFF: uint32 = 0x08       # RX FIFO full
SPI_SR_BSY: uint32 = 0x10       # SPI busy

# ============================================================================
# SPI Mode Definitions
# ============================================================================

SPI_MODE_0: uint32 = 0x00       # CPOL=0, CPHA=0
SPI_MODE_1: uint32 = 0x80       # CPOL=0, CPHA=1
SPI_MODE_2: uint32 = 0x40       # CPOL=1, CPHA=0
SPI_MODE_3: uint32 = 0xC0       # CPOL=1, CPHA=1

# System clock (125 MHz)
SPI_CLK_HZ: uint32 = 125000000

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _spi_base(spi: uint32) -> uint32:
    if spi == 0:
        return SPI0_BASE
    return SPI1_BASE

# ============================================================================
# SPI Initialization
# ============================================================================

def spi_init(spi: uint32, baudrate: uint32, mode: uint32):
    """Initialize SPI peripheral.

    Args:
        spi: SPI instance (0 or 1)
        baudrate: Clock frequency in Hz (e.g., 1000000 for 1MHz)
        mode: SPI_MODE_0, SPI_MODE_1, SPI_MODE_2, or SPI_MODE_3
    """
    base: uint32 = _spi_base(spi)

    # Unreset SPI
    reset_bit: uint32 = 16 if spi == 0 else 17
    reset_val: uint32 = mmio_read(RESETS_BASE)
    mmio_write(RESETS_BASE, reset_val & ~(1 << reset_bit))

    # Wait for reset done
    timeout: int32 = 10000
    while timeout > 0:
        done: uint32 = mmio_read(RESETS_BASE + 0x08)
        if (done & (1 << reset_bit)) != 0:
            break
        timeout = timeout - 1

    # Disable SPI during configuration
    mmio_write(base + SPI_SSPCR1, 0)

    # Calculate prescaler and divider
    # Baudrate = SPI_CLK / (CPSR * (1 + SCR))
    # where CPSR is prescaler (2-254, even) and SCR is 0-255
    # Start with CPSR = 2 and find SCR
    cpsr: uint32 = 2
    scr: uint32 = 0

    while cpsr <= 254:
        scr = (SPI_CLK_HZ / (cpsr * baudrate)) - 1
        if scr <= 255:
            break
        cpsr = cpsr + 2

    if scr > 255:
        scr = 255

    # Set prescaler
    mmio_write(base + SPI_SSPCPSR, cpsr)

    # Configure CR0: 8-bit, SPI format, mode, SCR
    cr0: uint32 = SPI_CR0_DSS_8 | SPI_CR0_FRF_SPI
    cr0 = cr0 | (mode & 0xC0)  # CPOL/CPHA
    cr0 = cr0 | (scr << SPI_CR0_SCR_SHIFT)
    mmio_write(base + SPI_SSPCR0, cr0)

    # Enable SPI as master
    mmio_write(base + SPI_SSPCR1, SPI_CR1_SSE)

def spi_set_gpio(spi: uint32, miso_pin: uint32, mosi_pin: uint32,
                 sck_pin: uint32, csn_pin: uint32):
    """Configure GPIO pins for SPI.

    Args:
        spi: SPI instance (0 or 1)
        miso_pin: MISO/RX pin
        mosi_pin: MOSI/TX pin
        sck_pin: SCK pin
        csn_pin: CS pin (or -1 if using GPIO)
    """
    # Function 1 = SPI for most GPIO pins
    func: uint32 = 1

    # Configure each pin
    miso_ctrl: uint32 = IO_BANK0_BASE + 4 + (miso_pin * 8)
    mmio_write(miso_ctrl, func)

    mosi_ctrl: uint32 = IO_BANK0_BASE + 4 + (mosi_pin * 8)
    mmio_write(mosi_ctrl, func)

    sck_ctrl: uint32 = IO_BANK0_BASE + 4 + (sck_pin * 8)
    mmio_write(sck_ctrl, func)

    if csn_pin < 30:
        csn_ctrl: uint32 = IO_BANK0_BASE + 4 + (csn_pin * 8)
        mmio_write(csn_ctrl, func)

# ============================================================================
# SPI Data Transfer
# ============================================================================

def spi_write_read(spi: uint32, tx_data: Ptr[uint8], rx_data: Ptr[uint8], len: int32):
    """Full-duplex SPI transfer.

    Args:
        spi: SPI instance
        tx_data: Data to send (can be NULL to send zeros)
        rx_data: Buffer for received data (can be NULL to discard)
        len: Number of bytes
    """
    base: uint32 = _spi_base(spi)
    i: int32 = 0

    while i < len:
        # Wait for TX FIFO space
        while (mmio_read(base + SPI_SSPSR) & SPI_SR_TNF) == 0:
            pass

        # Send byte
        if tx_data != cast[Ptr[uint8]](0):
            mmio_write(base + SPI_SSPDR, cast[uint32](tx_data[i]))
        else:
            mmio_write(base + SPI_SSPDR, 0)

        # Wait for RX data
        while (mmio_read(base + SPI_SSPSR) & SPI_SR_RNE) == 0:
            pass

        # Read byte
        val: uint32 = mmio_read(base + SPI_SSPDR)
        if rx_data != cast[Ptr[uint8]](0):
            rx_data[i] = cast[uint8](val & 0xFF)

        i = i + 1

def spi_write(spi: uint32, data: Ptr[uint8], len: int32):
    """Write-only SPI transfer (discards received data).

    Args:
        spi: SPI instance
        data: Data to send
        len: Number of bytes
    """
    spi_write_read(spi, data, cast[Ptr[uint8]](0), len)

def spi_read(spi: uint32, data: Ptr[uint8], len: int32):
    """Read-only SPI transfer (sends zeros).

    Args:
        spi: SPI instance
        data: Buffer for received data
        len: Number of bytes
    """
    spi_write_read(spi, cast[Ptr[uint8]](0), data, len)

def spi_transfer_byte(spi: uint32, tx: uint8) -> uint8:
    """Transfer single byte.

    Args:
        spi: SPI instance
        tx: Byte to send

    Returns:
        Received byte
    """
    base: uint32 = _spi_base(spi)

    # Wait for TX ready
    while (mmio_read(base + SPI_SSPSR) & SPI_SR_TNF) == 0:
        pass

    mmio_write(base + SPI_SSPDR, cast[uint32](tx))

    # Wait for RX
    while (mmio_read(base + SPI_SSPSR) & SPI_SR_RNE) == 0:
        pass

    return cast[uint8](mmio_read(base + SPI_SSPDR) & 0xFF)

def spi_is_busy(spi: uint32) -> bool:
    """Check if SPI is busy.

    Args:
        spi: SPI instance

    Returns:
        True if busy
    """
    base: uint32 = _spi_base(spi)
    return (mmio_read(base + SPI_SSPSR) & SPI_SR_BSY) != 0

def spi_flush(spi: uint32):
    """Wait for all pending transfers to complete and drain RX FIFO.

    Args:
        spi: SPI instance
    """
    base: uint32 = _spi_base(spi)

    # Wait for not busy
    while (mmio_read(base + SPI_SSPSR) & SPI_SR_BSY) != 0:
        pass

    # Drain RX FIFO
    while (mmio_read(base + SPI_SSPSR) & SPI_SR_RNE) != 0:
        dummy: uint32 = mmio_read(base + SPI_SSPDR)

def spi_set_baudrate(spi: uint32, baudrate: uint32):
    """Change SPI clock rate.

    Args:
        spi: SPI instance
        baudrate: New clock frequency in Hz
    """
    base: uint32 = _spi_base(spi)

    # Disable SPI
    mmio_write(base + SPI_SSPCR1, 0)

    # Recalculate dividers
    cpsr: uint32 = 2
    scr: uint32 = 0

    while cpsr <= 254:
        scr = (SPI_CLK_HZ / (cpsr * baudrate)) - 1
        if scr <= 255:
            break
        cpsr = cpsr + 2

    if scr > 255:
        scr = 255

    mmio_write(base + SPI_SSPCPSR, cpsr)

    # Update SCR in CR0
    cr0: uint32 = mmio_read(base + SPI_SSPCR0)
    cr0 = cr0 & 0xFF  # Clear SCR
    cr0 = cr0 | (scr << SPI_CR0_SCR_SHIFT)
    mmio_write(base + SPI_SSPCR0, cr0)

    # Re-enable SPI
    mmio_write(base + SPI_SSPCR1, SPI_CR1_SSE)
