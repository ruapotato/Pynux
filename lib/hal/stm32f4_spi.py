# STM32F4 SPI Hardware Abstraction Layer
#
# Hardware SPI driver for STM32F405/F407 in master mode.
# Supports SPI1, SPI2, SPI3.
#
# Default pins:
#   SPI1: PA5 (SCK), PA6 (MISO), PA7 (MOSI) - APB2
#   SPI2: PB13 (SCK), PB14 (MISO), PB15 (MOSI) - APB1
#   SPI3: PB3 (SCK), PB4 (MISO), PB5 (MOSI) - APB1

# ============================================================================
# Base Addresses
# ============================================================================

SPI1_BASE: uint32 = 0x40013000  # APB2
SPI2_BASE: uint32 = 0x40003800  # APB1
SPI3_BASE: uint32 = 0x40003C00  # APB1

RCC_BASE: uint32 = 0x40023800
GPIOA_BASE: uint32 = 0x40020000
GPIOB_BASE: uint32 = 0x40020400

# ============================================================================
# SPI Register Offsets
# ============================================================================

SPI_CR1: uint32 = 0x00      # Control register 1
SPI_CR2: uint32 = 0x04      # Control register 2
SPI_SR: uint32 = 0x08       # Status register
SPI_DR: uint32 = 0x0C       # Data register
SPI_CRCPR: uint32 = 0x10    # CRC polynomial
SPI_RXCRCR: uint32 = 0x14   # RX CRC
SPI_TXCRCR: uint32 = 0x18   # TX CRC
SPI_I2SCFGR: uint32 = 0x1C  # I2S configuration

# CR1 bits
SPI_CR1_CPHA: uint32 = 0x01     # Clock phase
SPI_CR1_CPOL: uint32 = 0x02     # Clock polarity
SPI_CR1_MSTR: uint32 = 0x04     # Master mode
SPI_CR1_BR_2: uint32 = 0x08     # Baud rate /4
SPI_CR1_BR_4: uint32 = 0x10     # Baud rate /8
SPI_CR1_BR_8: uint32 = 0x18     # Baud rate /16
SPI_CR1_BR_16: uint32 = 0x20    # Baud rate /32
SPI_CR1_BR_32: uint32 = 0x28    # Baud rate /64
SPI_CR1_BR_64: uint32 = 0x30    # Baud rate /128
SPI_CR1_BR_128: uint32 = 0x38   # Baud rate /256
SPI_CR1_SPE: uint32 = 0x40      # SPI enable
SPI_CR1_LSBFIRST: uint32 = 0x80 # LSB first
SPI_CR1_SSI: uint32 = 0x100     # Internal slave select
SPI_CR1_SSM: uint32 = 0x200     # Software slave management
SPI_CR1_RXONLY: uint32 = 0x400  # Receive only
SPI_CR1_DFF: uint32 = 0x800     # Data frame format (0=8-bit, 1=16-bit)
SPI_CR1_CRCNEXT: uint32 = 0x1000  # CRC next
SPI_CR1_CRCEN: uint32 = 0x2000  # CRC enable
SPI_CR1_BIDIOE: uint32 = 0x4000 # Bidirectional output enable
SPI_CR1_BIDIMODE: uint32 = 0x8000  # Bidirectional mode

# CR2 bits
SPI_CR2_RXDMAEN: uint32 = 0x01  # RX DMA enable
SPI_CR2_TXDMAEN: uint32 = 0x02  # TX DMA enable
SPI_CR2_SSOE: uint32 = 0x04     # SS output enable
SPI_CR2_FRF: uint32 = 0x10      # Frame format
SPI_CR2_ERRIE: uint32 = 0x20    # Error interrupt enable
SPI_CR2_RXNEIE: uint32 = 0x40   # RX not empty IE
SPI_CR2_TXEIE: uint32 = 0x80    # TX empty IE

# Status register bits
SPI_SR_RXNE: uint32 = 0x01      # RX not empty
SPI_SR_TXE: uint32 = 0x02       # TX empty
SPI_SR_CHSIDE: uint32 = 0x04    # Channel side
SPI_SR_UDR: uint32 = 0x08       # Underrun
SPI_SR_CRCERR: uint32 = 0x10    # CRC error
SPI_SR_MODF: uint32 = 0x20      # Mode fault
SPI_SR_OVR: uint32 = 0x40       # Overrun
SPI_SR_BSY: uint32 = 0x80       # Busy

# ============================================================================
# SPI Mode Definitions
# ============================================================================

SPI_MODE_0: uint32 = 0x00                    # CPOL=0, CPHA=0
SPI_MODE_1: uint32 = SPI_CR1_CPHA            # CPOL=0, CPHA=1
SPI_MODE_2: uint32 = SPI_CR1_CPOL            # CPOL=1, CPHA=0
SPI_MODE_3: uint32 = SPI_CR1_CPOL | SPI_CR1_CPHA  # CPOL=1, CPHA=1

# RCC register offsets
RCC_AHB1ENR: uint32 = 0x30
RCC_APB1ENR: uint32 = 0x40
RCC_APB2ENR: uint32 = 0x44

# GPIO register offsets
GPIO_MODER: uint32 = 0x00
GPIO_OSPEEDR: uint32 = 0x08
GPIO_AFRL: uint32 = 0x20
GPIO_AFRH: uint32 = 0x24

# APB clocks
APB1_CLOCK: uint32 = 42000000
APB2_CLOCK: uint32 = 84000000

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
    if spi == 1:
        return SPI1_BASE
    elif spi == 2:
        return SPI2_BASE
    return SPI3_BASE

def _spi_clock(spi: uint32) -> uint32:
    if spi == 1:
        return APB2_CLOCK
    return APB1_CLOCK

# ============================================================================
# Clock Enable
# ============================================================================

def spi_enable_clock(spi: uint32):
    """Enable clock for SPI peripheral.

    Args:
        spi: SPI number (1-3)
    """
    if spi == 1:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | (1 << 12))
    elif spi == 2:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 14))
    elif spi == 3:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 15))

# ============================================================================
# SPI Initialization
# ============================================================================

def spi_init(spi: uint32, baudrate: uint32, mode: uint32):
    """Initialize SPI in master mode.

    Args:
        spi: SPI number (1-3)
        baudrate: Desired clock frequency in Hz
        mode: SPI_MODE_0, SPI_MODE_1, SPI_MODE_2, or SPI_MODE_3
    """
    base: uint32 = _spi_base(spi)
    clock: uint32 = _spi_clock(spi)

    # Enable SPI clock
    spi_enable_clock(spi)

    # Disable SPI during configuration
    mmio_write(base + SPI_CR1, 0)

    # Calculate baud rate prescaler
    # BR[2:0] = 000: /2, 001: /4, 010: /8, ... 111: /256
    br: uint32 = 0
    div: uint32 = 2
    while br < 7:
        if (clock / div) <= baudrate:
            break
        div = div * 2
        br = br + 1

    # Configure CR1: master, software SS, 8-bit, mode
    cr1: uint32 = SPI_CR1_MSTR | SPI_CR1_SSM | SPI_CR1_SSI
    cr1 = cr1 | (br << 3)  # Baud rate
    cr1 = cr1 | (mode & 0x03)  # CPOL/CPHA

    mmio_write(base + SPI_CR1, cr1)

    # Configure CR2 (default is fine)
    mmio_write(base + SPI_CR2, 0)

    # Enable SPI
    cr1 = cr1 | SPI_CR1_SPE
    mmio_write(base + SPI_CR1, cr1)

def spi_init_gpio(spi: uint32, sck_port: uint32, sck_pin: uint32,
                  miso_port: uint32, miso_pin: uint32,
                  mosi_port: uint32, mosi_pin: uint32):
    """Configure GPIO pins for SPI.

    Args:
        spi: SPI number (1-3)
        sck_port: SCK port base address
        sck_pin: SCK pin number
        miso_port: MISO port base address
        miso_pin: MISO pin number
        mosi_port: MOSI port base address
        mosi_pin: MOSI pin number
    """
    # SPI1: AF5, SPI2/SPI3: AF5 or AF6 depending on pins
    af: uint32 = 5

    # Configure SCK: AF, high speed
    moder: uint32 = mmio_read(sck_port + GPIO_MODER)
    moder = moder & ~(3 << (sck_pin * 2))
    moder = moder | (2 << (sck_pin * 2))  # AF
    mmio_write(sck_port + GPIO_MODER, moder)

    ospeedr: uint32 = mmio_read(sck_port + GPIO_OSPEEDR)
    ospeedr = ospeedr | (3 << (sck_pin * 2))  # High speed
    mmio_write(sck_port + GPIO_OSPEEDR, ospeedr)

    if sck_pin < 8:
        afr: uint32 = mmio_read(sck_port + GPIO_AFRL)
        afr = afr & ~(0xF << (sck_pin * 4))
        afr = afr | (af << (sck_pin * 4))
        mmio_write(sck_port + GPIO_AFRL, afr)
    else:
        afr: uint32 = mmio_read(sck_port + GPIO_AFRH)
        afr = afr & ~(0xF << ((sck_pin - 8) * 4))
        afr = afr | (af << ((sck_pin - 8) * 4))
        mmio_write(sck_port + GPIO_AFRH, afr)

    # Configure MISO: AF, high speed
    moder = mmio_read(miso_port + GPIO_MODER)
    moder = moder & ~(3 << (miso_pin * 2))
    moder = moder | (2 << (miso_pin * 2))
    mmio_write(miso_port + GPIO_MODER, moder)

    if miso_pin < 8:
        afr = mmio_read(miso_port + GPIO_AFRL)
        afr = afr & ~(0xF << (miso_pin * 4))
        afr = afr | (af << (miso_pin * 4))
        mmio_write(miso_port + GPIO_AFRL, afr)
    else:
        afr = mmio_read(miso_port + GPIO_AFRH)
        afr = afr & ~(0xF << ((miso_pin - 8) * 4))
        afr = afr | (af << ((miso_pin - 8) * 4))
        mmio_write(miso_port + GPIO_AFRH, afr)

    # Configure MOSI: AF, high speed
    moder = mmio_read(mosi_port + GPIO_MODER)
    moder = moder & ~(3 << (mosi_pin * 2))
    moder = moder | (2 << (mosi_pin * 2))
    mmio_write(mosi_port + GPIO_MODER, moder)

    ospeedr = mmio_read(mosi_port + GPIO_OSPEEDR)
    ospeedr = ospeedr | (3 << (mosi_pin * 2))
    mmio_write(mosi_port + GPIO_OSPEEDR, ospeedr)

    if mosi_pin < 8:
        afr = mmio_read(mosi_port + GPIO_AFRL)
        afr = afr & ~(0xF << (mosi_pin * 4))
        afr = afr | (af << (mosi_pin * 4))
        mmio_write(mosi_port + GPIO_AFRL, afr)
    else:
        afr = mmio_read(mosi_port + GPIO_AFRH)
        afr = afr & ~(0xF << ((mosi_pin - 8) * 4))
        afr = afr | (af << ((mosi_pin - 8) * 4))
        mmio_write(mosi_port + GPIO_AFRH, afr)

# ============================================================================
# SPI Data Transfer
# ============================================================================

def spi_write_read(spi: uint32, tx_data: Ptr[uint8], rx_data: Ptr[uint8], len: int32):
    """Full-duplex SPI transfer.

    Args:
        spi: SPI number (1-3)
        tx_data: Data to send (can be NULL)
        rx_data: Buffer for received data (can be NULL)
        len: Number of bytes
    """
    base: uint32 = _spi_base(spi)
    i: int32 = 0

    while i < len:
        # Wait for TXE
        while (mmio_read(base + SPI_SR) & SPI_SR_TXE) == 0:
            pass

        # Send byte
        if tx_data != cast[Ptr[uint8]](0):
            mmio_write(base + SPI_DR, cast[uint32](tx_data[i]))
        else:
            mmio_write(base + SPI_DR, 0)

        # Wait for RXNE
        while (mmio_read(base + SPI_SR) & SPI_SR_RXNE) == 0:
            pass

        # Read byte
        val: uint32 = mmio_read(base + SPI_DR)
        if rx_data != cast[Ptr[uint8]](0):
            rx_data[i] = cast[uint8](val & 0xFF)

        i = i + 1

def spi_write(spi: uint32, data: Ptr[uint8], len: int32):
    """Write-only SPI transfer.

    Args:
        spi: SPI number (1-3)
        data: Data to send
        len: Number of bytes
    """
    spi_write_read(spi, data, cast[Ptr[uint8]](0), len)

def spi_read(spi: uint32, data: Ptr[uint8], len: int32):
    """Read-only SPI transfer.

    Args:
        spi: SPI number (1-3)
        data: Buffer for received data
        len: Number of bytes
    """
    spi_write_read(spi, cast[Ptr[uint8]](0), data, len)

def spi_transfer_byte(spi: uint32, tx: uint8) -> uint8:
    """Transfer single byte.

    Args:
        spi: SPI number (1-3)
        tx: Byte to send

    Returns:
        Received byte
    """
    base: uint32 = _spi_base(spi)

    # Wait for TXE
    while (mmio_read(base + SPI_SR) & SPI_SR_TXE) == 0:
        pass

    mmio_write(base + SPI_DR, cast[uint32](tx))

    # Wait for RXNE
    while (mmio_read(base + SPI_SR) & SPI_SR_RXNE) == 0:
        pass

    return cast[uint8](mmio_read(base + SPI_DR) & 0xFF)

def spi_is_busy(spi: uint32) -> bool:
    """Check if SPI is busy.

    Args:
        spi: SPI number (1-3)

    Returns:
        True if busy
    """
    base: uint32 = _spi_base(spi)
    return (mmio_read(base + SPI_SR) & SPI_SR_BSY) != 0

def spi_flush(spi: uint32):
    """Wait for all transfers to complete.

    Args:
        spi: SPI number (1-3)
    """
    base: uint32 = _spi_base(spi)

    # Wait for TXE and not BSY
    while True:
        sr: uint32 = mmio_read(base + SPI_SR)
        if (sr & SPI_SR_TXE) != 0 and (sr & SPI_SR_BSY) == 0:
            break

    # Clear any pending RX data
    while (mmio_read(base + SPI_SR) & SPI_SR_RXNE) != 0:
        dummy: uint32 = mmio_read(base + SPI_DR)

def spi_set_baudrate(spi: uint32, baudrate: uint32):
    """Change SPI clock rate.

    Args:
        spi: SPI number (1-3)
        baudrate: New clock frequency in Hz
    """
    base: uint32 = _spi_base(spi)
    clock: uint32 = _spi_clock(spi)

    # Disable SPI
    cr1: uint32 = mmio_read(base + SPI_CR1)
    mmio_write(base + SPI_CR1, cr1 & ~SPI_CR1_SPE)

    # Calculate new baud rate prescaler
    br: uint32 = 0
    div: uint32 = 2
    while br < 7:
        if (clock / div) <= baudrate:
            break
        div = div * 2
        br = br + 1

    # Update BR bits
    cr1 = cr1 & ~0x38  # Clear BR[2:0]
    cr1 = cr1 | (br << 3)

    # Re-enable SPI
    mmio_write(base + SPI_CR1, cr1 | SPI_CR1_SPE)
