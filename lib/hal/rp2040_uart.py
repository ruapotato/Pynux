# RP2040 UART Hardware Abstraction Layer
#
# Full UART driver for RP2040 supporting UART0 and UART1.
# The startup code initializes UART0 at 115200 baud.
# This module provides additional configuration and UART1 support.
#
# UART0: GPIO0 (TX), GPIO1 (RX)
# UART1: GPIO4 (TX), GPIO5 (RX) - can be remapped

# ============================================================================
# Base Addresses
# ============================================================================

UART0_BASE: uint32 = 0x40034000
UART1_BASE: uint32 = 0x40038000

IO_BANK0_BASE: uint32 = 0x40014000
RESETS_BASE: uint32 = 0x4000C000
CLOCKS_BASE: uint32 = 0x40008000

# ============================================================================
# UART Register Offsets (PL011)
# ============================================================================

UART_DR: uint32 = 0x00        # Data register
UART_RSR: uint32 = 0x04       # Receive status / error clear
UART_FR: uint32 = 0x18        # Flag register
UART_ILPR: uint32 = 0x20      # IrDA low-power counter
UART_IBRD: uint32 = 0x24      # Integer baud rate divisor
UART_FBRD: uint32 = 0x28      # Fractional baud rate divisor
UART_LCR_H: uint32 = 0x2C     # Line control register
UART_CR: uint32 = 0x30        # Control register
UART_IFLS: uint32 = 0x34      # Interrupt FIFO level select
UART_IMSC: uint32 = 0x38      # Interrupt mask set/clear
UART_RIS: uint32 = 0x3C       # Raw interrupt status
UART_MIS: uint32 = 0x40       # Masked interrupt status
UART_ICR: uint32 = 0x44       # Interrupt clear register
UART_DMACR: uint32 = 0x48     # DMA control register

# Flag register bits
UART_FR_RXFE: uint32 = 0x10   # RX FIFO empty
UART_FR_TXFF: uint32 = 0x20   # TX FIFO full
UART_FR_RXFF: uint32 = 0x40   # RX FIFO full
UART_FR_TXFE: uint32 = 0x80   # TX FIFO empty
UART_FR_BUSY: uint32 = 0x08   # UART busy

# Line control bits
UART_LCR_H_FEN: uint32 = 0x10   # FIFO enable
UART_LCR_H_WLEN_8: uint32 = 0x60  # 8 data bits

# Control register bits
UART_CR_UARTEN: uint32 = 0x01   # UART enable
UART_CR_TXE: uint32 = 0x100     # TX enable
UART_CR_RXE: uint32 = 0x200     # RX enable

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _uart_base(uart: uint32) -> uint32:
    """Get base address for UART instance."""
    if uart == 0:
        return UART0_BASE
    return UART1_BASE

# ============================================================================
# UART Initialization
# ============================================================================

def uart_init(uart: uint32, baud: uint32):
    """Initialize UART with specified baud rate.

    Args:
        uart: UART instance (0 or 1)
        baud: Baud rate (e.g., 115200)

    Note: Assumes peripheral clock is 125MHz.
    """
    base: uint32 = _uart_base(uart)

    # Unreset UART from RESETS register
    reset_bit: uint32 = 22 if uart == 0 else 23
    reset_val: uint32 = mmio_read(RESETS_BASE)
    mmio_write(RESETS_BASE, reset_val & ~(1 << reset_bit))

    # Wait for reset done
    timeout: int32 = 10000
    while timeout > 0:
        done: uint32 = mmio_read(RESETS_BASE + 0x08)
        if (done & (1 << reset_bit)) != 0:
            break
        timeout = timeout - 1

    # Disable UART during configuration
    mmio_write(base + UART_CR, 0)

    # Calculate baud rate divisors at 125MHz
    # BAUDDIV = UARTCLK / (16 * baud)
    # IBRD = integer part, FBRD = fractional * 64
    peri_clock: uint32 = 125000000
    div: uint32 = (8 * peri_clock) / baud
    ibrd: uint32 = div >> 7
    fbrd: uint32 = ((div & 0x7F) + 1) / 2

    mmio_write(base + UART_IBRD, ibrd)
    mmio_write(base + UART_FBRD, fbrd)

    # 8N1, enable FIFOs
    mmio_write(base + UART_LCR_H, UART_LCR_H_WLEN_8 | UART_LCR_H_FEN)

    # Enable UART, TX, RX
    mmio_write(base + UART_CR, UART_CR_UARTEN | UART_CR_TXE | UART_CR_RXE)

def uart_set_gpio(uart: uint32, tx_pin: uint32, rx_pin: uint32):
    """Configure GPIO pins for UART function.

    Args:
        uart: UART instance (0 or 1)
        tx_pin: GPIO pin for TX (typically 0 or 4 for UART0, 4 or 8 for UART1)
        rx_pin: GPIO pin for RX
    """
    # Function 2 = UART for most GPIO pins
    func: uint32 = 2

    # Set TX pin function
    tx_ctrl: uint32 = IO_BANK0_BASE + 4 + (tx_pin * 8)
    mmio_write(tx_ctrl, func)

    # Set RX pin function
    rx_ctrl: uint32 = IO_BANK0_BASE + 4 + (rx_pin * 8)
    mmio_write(rx_ctrl, func)

# ============================================================================
# UART I/O Functions
# ============================================================================

def uart_putc(uart: uint32, c: uint8):
    """Send one byte over UART.

    Args:
        uart: UART instance (0 or 1)
        c: Character to send
    """
    base: uint32 = _uart_base(uart)

    # Wait for TX FIFO not full
    while (mmio_read(base + UART_FR) & UART_FR_TXFF) != 0:
        pass

    mmio_write(base + UART_DR, cast[uint32](c))

def uart_getc(uart: uint32) -> uint8:
    """Receive one byte from UART (blocking).

    Args:
        uart: UART instance (0 or 1)

    Returns:
        Received byte
    """
    base: uint32 = _uart_base(uart)

    # Wait for RX FIFO not empty
    while (mmio_read(base + UART_FR) & UART_FR_RXFE) != 0:
        pass

    return cast[uint8](mmio_read(base + UART_DR) & 0xFF)

def uart_getc_timeout(uart: uint32, timeout_ms: int32) -> int32:
    """Receive one byte with timeout.

    Args:
        uart: UART instance (0 or 1)
        timeout_ms: Timeout in milliseconds

    Returns:
        Received byte (0-255) or -1 on timeout
    """
    base: uint32 = _uart_base(uart)

    # Approximate timeout using busy loop
    timeout_loops: int32 = timeout_ms * 1000

    while timeout_loops > 0:
        if (mmio_read(base + UART_FR) & UART_FR_RXFE) == 0:
            return cast[int32](mmio_read(base + UART_DR) & 0xFF)
        timeout_loops = timeout_loops - 1

    return -1

def uart_tx_ready(uart: uint32) -> bool:
    """Check if TX FIFO has space.

    Args:
        uart: UART instance (0 or 1)

    Returns:
        True if ready to send
    """
    base: uint32 = _uart_base(uart)
    return (mmio_read(base + UART_FR) & UART_FR_TXFF) == 0

def uart_rx_ready(uart: uint32) -> bool:
    """Check if RX FIFO has data.

    Args:
        uart: UART instance (0 or 1)

    Returns:
        True if data available
    """
    base: uint32 = _uart_base(uart)
    return (mmio_read(base + UART_FR) & UART_FR_RXFE) == 0

def uart_flush_tx(uart: uint32):
    """Wait for all TX data to be sent.

    Args:
        uart: UART instance (0 or 1)
    """
    base: uint32 = _uart_base(uart)

    # Wait for TX FIFO empty and UART not busy
    while True:
        fr: uint32 = mmio_read(base + UART_FR)
        if (fr & UART_FR_TXFE) != 0 and (fr & UART_FR_BUSY) == 0:
            break

def uart_puts(uart: uint32, s: Ptr[char]):
    """Send null-terminated string over UART.

    Args:
        uart: UART instance (0 or 1)
        s: String to send
    """
    i: int32 = 0
    while s[i] != 0:
        uart_putc(uart, cast[uint8](s[i]))
        i = i + 1

def uart_write(uart: uint32, data: Ptr[uint8], len: int32):
    """Send buffer over UART.

    Args:
        uart: UART instance (0 or 1)
        data: Data buffer
        len: Number of bytes to send
    """
    i: int32 = 0
    while i < len:
        uart_putc(uart, data[i])
        i = i + 1

def uart_read(uart: uint32, data: Ptr[uint8], len: int32) -> int32:
    """Read bytes from UART (blocking).

    Args:
        uart: UART instance (0 or 1)
        data: Buffer to fill
        len: Maximum bytes to read

    Returns:
        Number of bytes read
    """
    i: int32 = 0
    while i < len:
        data[i] = uart_getc(uart)
        i = i + 1
    return len
