# STM32F4 UART Hardware Abstraction Layer
#
# Full USART driver for STM32F405/F407 supporting USART1-6 and UART4-5.
# The startup code initializes USART1 at 115200 baud on PA9/PA10.
#
# USART1: PA9 (TX), PA10 (RX) - APB2, up to 10.5 Mbps
# USART2: PA2 (TX), PA3 (RX) - APB1
# USART3: PB10 (TX), PB11 (RX) - APB1
# UART4: PA0 (TX), PA1 (RX) - APB1
# UART5: PC12 (TX), PD2 (RX) - APB1
# USART6: PC6 (TX), PC7 (RX) - APB2

# ============================================================================
# Base Addresses
# ============================================================================

USART1_BASE: uint32 = 0x40011000  # APB2
USART2_BASE: uint32 = 0x40004400  # APB1
USART3_BASE: uint32 = 0x40004800  # APB1
UART4_BASE: uint32 = 0x40004C00   # APB1
UART5_BASE: uint32 = 0x40005000   # APB1
USART6_BASE: uint32 = 0x40011400  # APB2

RCC_BASE: uint32 = 0x40023800
GPIOA_BASE: uint32 = 0x40020000
GPIOB_BASE: uint32 = 0x40020400
GPIOC_BASE: uint32 = 0x40020800
GPIOD_BASE: uint32 = 0x40020C00

# ============================================================================
# USART Register Offsets
# ============================================================================

USART_SR: uint32 = 0x00       # Status register
USART_DR: uint32 = 0x04       # Data register
USART_BRR: uint32 = 0x08      # Baud rate register
USART_CR1: uint32 = 0x0C      # Control register 1
USART_CR2: uint32 = 0x10      # Control register 2
USART_CR3: uint32 = 0x14      # Control register 3
USART_GTPR: uint32 = 0x18     # Guard time and prescaler

# Status register bits
USART_SR_PE: uint32 = 0x01    # Parity error
USART_SR_FE: uint32 = 0x02    # Framing error
USART_SR_NE: uint32 = 0x04    # Noise error
USART_SR_ORE: uint32 = 0x08   # Overrun error
USART_SR_IDLE: uint32 = 0x10  # IDLE line detected
USART_SR_RXNE: uint32 = 0x20  # Read data register not empty
USART_SR_TC: uint32 = 0x40    # Transmission complete
USART_SR_TXE: uint32 = 0x80   # Transmit data register empty

# Control register 1 bits
USART_CR1_SBK: uint32 = 0x01     # Send break
USART_CR1_RWU: uint32 = 0x02     # Receiver wakeup
USART_CR1_RE: uint32 = 0x04      # Receiver enable
USART_CR1_TE: uint32 = 0x08      # Transmitter enable
USART_CR1_IDLEIE: uint32 = 0x10  # IDLE interrupt enable
USART_CR1_RXNEIE: uint32 = 0x20  # RXNE interrupt enable
USART_CR1_TCIE: uint32 = 0x40    # Transmission complete IE
USART_CR1_TXEIE: uint32 = 0x80   # TXE interrupt enable
USART_CR1_PEIE: uint32 = 0x100   # Parity error IE
USART_CR1_PS: uint32 = 0x200     # Parity selection
USART_CR1_PCE: uint32 = 0x400    # Parity control enable
USART_CR1_WAKE: uint32 = 0x800   # Wakeup method
USART_CR1_M: uint32 = 0x1000     # Word length
USART_CR1_UE: uint32 = 0x2000    # USART enable
USART_CR1_OVER8: uint32 = 0x8000 # Oversampling mode

# RCC register offsets
RCC_AHB1ENR: uint32 = 0x30
RCC_APB1ENR: uint32 = 0x40
RCC_APB2ENR: uint32 = 0x44

# GPIO register offsets
GPIO_MODER: uint32 = 0x00
GPIO_OTYPER: uint32 = 0x04
GPIO_OSPEEDR: uint32 = 0x08
GPIO_PUPDR: uint32 = 0x0C
GPIO_AFRL: uint32 = 0x20
GPIO_AFRH: uint32 = 0x24

# ============================================================================
# Clock Configuration
# ============================================================================
# APB1 clock = 42 MHz (max)
# APB2 clock = 84 MHz (max)

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

# USART instance to base address mapping
_usart_bases: Array[6, uint32]
_usart_apb_clocks: Array[6, uint32]
_usart_initialized: bool = False

def _init_usart_tables():
    """Initialize USART lookup tables."""
    global _usart_initialized
    if _usart_initialized:
        return

    _usart_bases[0] = USART1_BASE
    _usart_bases[1] = USART2_BASE
    _usart_bases[2] = USART3_BASE
    _usart_bases[3] = UART4_BASE
    _usart_bases[4] = UART5_BASE
    _usart_bases[5] = USART6_BASE

    _usart_apb_clocks[0] = APB2_CLOCK  # USART1 on APB2
    _usart_apb_clocks[1] = APB1_CLOCK  # USART2 on APB1
    _usart_apb_clocks[2] = APB1_CLOCK  # USART3 on APB1
    _usart_apb_clocks[3] = APB1_CLOCK  # UART4 on APB1
    _usart_apb_clocks[4] = APB1_CLOCK  # UART5 on APB1
    _usart_apb_clocks[5] = APB2_CLOCK  # USART6 on APB2

    _usart_initialized = True

def _usart_base(usart: uint32) -> uint32:
    """Get base address for USART instance (1-6)."""
    _init_usart_tables()
    if usart < 1 or usart > 6:
        return USART1_BASE
    return _usart_bases[usart - 1]

def _usart_clock(usart: uint32) -> uint32:
    """Get APB clock for USART instance."""
    _init_usart_tables()
    if usart < 1 or usart > 6:
        return APB2_CLOCK
    return _usart_apb_clocks[usart - 1]

# ============================================================================
# Clock Enable Functions
# ============================================================================

def usart_enable_clock(usart: uint32):
    """Enable clock for USART peripheral.

    Args:
        usart: USART number (1-6)
    """
    if usart == 1:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | (1 << 4))
    elif usart == 2:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 17))
    elif usart == 3:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 18))
    elif usart == 4:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 19))
    elif usart == 5:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 20))
    elif usart == 6:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | (1 << 5))

# ============================================================================
# USART Initialization
# ============================================================================

def usart_init(usart: uint32, baud: uint32):
    """Initialize USART with specified baud rate.

    Args:
        usart: USART number (1-6)
        baud: Baud rate (e.g., 115200)

    Note: GPIO pins must be configured separately.
    """
    base: uint32 = _usart_base(usart)
    clock: uint32 = _usart_clock(usart)

    # Enable peripheral clock
    usart_enable_clock(usart)

    # Disable USART during configuration
    mmio_write(base + USART_CR1, 0)

    # Calculate baud rate register value
    # BRR = fCK / baud (for OVER8=0)
    # Mantissa = BRR >> 4, Fraction = BRR & 0xF
    brr: uint32 = clock / baud
    mmio_write(base + USART_BRR, brr)

    # Configure: 8N1, no parity
    # CR2 defaults are fine (1 stop bit)
    mmio_write(base + USART_CR2, 0)

    # No flow control
    mmio_write(base + USART_CR3, 0)

    # Enable USART, TX, RX
    mmio_write(base + USART_CR1, USART_CR1_UE | USART_CR1_TE | USART_CR1_RE)

def usart_init_gpio(usart: uint32, tx_port: uint32, tx_pin: uint32,
                    rx_port: uint32, rx_pin: uint32):
    """Configure GPIO pins for USART.

    Args:
        usart: USART number (1-6)
        tx_port: TX GPIO port base address
        tx_pin: TX pin number (0-15)
        rx_port: RX GPIO port base address
        rx_pin: RX pin number (0-15)
    """
    # Determine AF number
    # USART1-3: AF7
    # UART4-5, USART6: AF8
    af: uint32 = 7 if usart <= 3 else 8

    # Configure TX pin
    # MODER = Alternate function (10)
    moder: uint32 = mmio_read(tx_port + GPIO_MODER)
    moder = moder & ~(3 << (tx_pin * 2))
    moder = moder | (2 << (tx_pin * 2))
    mmio_write(tx_port + GPIO_MODER, moder)

    # Set alternate function
    if tx_pin < 8:
        afr: uint32 = mmio_read(tx_port + GPIO_AFRL)
        afr = afr & ~(0xF << (tx_pin * 4))
        afr = afr | (af << (tx_pin * 4))
        mmio_write(tx_port + GPIO_AFRL, afr)
    else:
        afr: uint32 = mmio_read(tx_port + GPIO_AFRH)
        afr = afr & ~(0xF << ((tx_pin - 8) * 4))
        afr = afr | (af << ((tx_pin - 8) * 4))
        mmio_write(tx_port + GPIO_AFRH, afr)

    # Configure RX pin
    moder = mmio_read(rx_port + GPIO_MODER)
    moder = moder & ~(3 << (rx_pin * 2))
    moder = moder | (2 << (rx_pin * 2))
    mmio_write(rx_port + GPIO_MODER, moder)

    if rx_pin < 8:
        afr = mmio_read(rx_port + GPIO_AFRL)
        afr = afr & ~(0xF << (rx_pin * 4))
        afr = afr | (af << (rx_pin * 4))
        mmio_write(rx_port + GPIO_AFRL, afr)
    else:
        afr = mmio_read(rx_port + GPIO_AFRH)
        afr = afr & ~(0xF << ((rx_pin - 8) * 4))
        afr = afr | (af << ((rx_pin - 8) * 4))
        mmio_write(rx_port + GPIO_AFRH, afr)

# ============================================================================
# USART I/O Functions
# ============================================================================

def usart_putc(usart: uint32, c: uint8):
    """Send one byte over USART.

    Args:
        usart: USART number (1-6)
        c: Character to send
    """
    base: uint32 = _usart_base(usart)

    # Wait for TXE (transmit register empty)
    while (mmio_read(base + USART_SR) & USART_SR_TXE) == 0:
        pass

    mmio_write(base + USART_DR, cast[uint32](c))

def usart_getc(usart: uint32) -> uint8:
    """Receive one byte from USART (blocking).

    Args:
        usart: USART number (1-6)

    Returns:
        Received byte
    """
    base: uint32 = _usart_base(usart)

    # Wait for RXNE (data received)
    while (mmio_read(base + USART_SR) & USART_SR_RXNE) == 0:
        pass

    return cast[uint8](mmio_read(base + USART_DR) & 0xFF)

def usart_getc_timeout(usart: uint32, timeout_ms: int32) -> int32:
    """Receive one byte with timeout.

    Args:
        usart: USART number (1-6)
        timeout_ms: Timeout in milliseconds

    Returns:
        Received byte (0-255) or -1 on timeout
    """
    base: uint32 = _usart_base(usart)

    # Approximate timeout using busy loop
    timeout_loops: int32 = timeout_ms * 1000

    while timeout_loops > 0:
        if (mmio_read(base + USART_SR) & USART_SR_RXNE) != 0:
            return cast[int32](mmio_read(base + USART_DR) & 0xFF)
        timeout_loops = timeout_loops - 1

    return -1

def usart_tx_ready(usart: uint32) -> bool:
    """Check if ready to transmit.

    Args:
        usart: USART number (1-6)

    Returns:
        True if TXE is set
    """
    base: uint32 = _usart_base(usart)
    return (mmio_read(base + USART_SR) & USART_SR_TXE) != 0

def usart_rx_ready(usart: uint32) -> bool:
    """Check if data is available.

    Args:
        usart: USART number (1-6)

    Returns:
        True if RXNE is set
    """
    base: uint32 = _usart_base(usart)
    return (mmio_read(base + USART_SR) & USART_SR_RXNE) != 0

def usart_flush_tx(usart: uint32):
    """Wait for transmission complete.

    Args:
        usart: USART number (1-6)
    """
    base: uint32 = _usart_base(usart)

    # Wait for TC (transmission complete)
    while (mmio_read(base + USART_SR) & USART_SR_TC) == 0:
        pass

def usart_puts(usart: uint32, s: Ptr[char]):
    """Send null-terminated string.

    Args:
        usart: USART number (1-6)
        s: String to send
    """
    i: int32 = 0
    while s[i] != 0:
        usart_putc(usart, cast[uint8](s[i]))
        i = i + 1

def usart_write(usart: uint32, data: Ptr[uint8], len: int32):
    """Send buffer over USART.

    Args:
        usart: USART number (1-6)
        data: Data buffer
        len: Number of bytes
    """
    i: int32 = 0
    while i < len:
        usart_putc(usart, data[i])
        i = i + 1

def usart_read(usart: uint32, data: Ptr[uint8], len: int32) -> int32:
    """Read bytes from USART (blocking).

    Args:
        usart: USART number (1-6)
        data: Buffer to fill
        len: Maximum bytes to read

    Returns:
        Number of bytes read
    """
    i: int32 = 0
    while i < len:
        data[i] = usart_getc(usart)
        i = i + 1
    return len
