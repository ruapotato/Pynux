# Pynux Peripherals Library
#
# Hardware abstraction layer for ARM Cortex-M3 peripherals.
# Provides GPIO, SPI, I2C, PWM, and ADC interfaces.
#
# Note: For QEMU MPS2-AN385, these are abstraction layers with
# placeholder base addresses that would work on real hardware.

# ============================================================================
# Base Addresses
# ============================================================================

GPIO_BASE: uint32 = 0x40010000
SPI_BASE: uint32 = 0x40020000
I2C_BASE: uint32 = 0x40030000
PWM_BASE: uint32 = 0x40040000
ADC_BASE: uint32 = 0x40050000

# ============================================================================
# Memory-Mapped I/O Helpers
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    """Read from memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    """Write to memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def mmio_set_bits(addr: uint32, mask: uint32):
    """Set bits in memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = ptr[0] | mask

def mmio_clear_bits(addr: uint32, mask: uint32):
    """Clear bits in memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = ptr[0] & ~mask

def mmio_toggle_bits(addr: uint32, mask: uint32):
    """Toggle bits in memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = ptr[0] ^ mask

# ============================================================================
# GPIO - General Purpose Input/Output
# ============================================================================
#
# GPIO Register Map (per port, 32 pins):
#   Offset 0x00: DATA      - Read/write pin values
#   Offset 0x04: DIR       - Direction (0=input, 1=output)
#   Offset 0x08: INT_EN    - Interrupt enable
#   Offset 0x0C: INT_TYPE  - Interrupt type (0=level, 1=edge)
#   Offset 0x10: INT_POL   - Interrupt polarity (0=low/falling, 1=high/rising)
#   Offset 0x14: INT_STAT  - Interrupt status
#   Offset 0x18: INT_CLR   - Interrupt clear

GPIO_DATA_OFFSET: uint32 = 0x00
GPIO_DIR_OFFSET: uint32 = 0x04
GPIO_INT_EN_OFFSET: uint32 = 0x08
GPIO_INT_TYPE_OFFSET: uint32 = 0x0C
GPIO_INT_POL_OFFSET: uint32 = 0x10
GPIO_INT_STAT_OFFSET: uint32 = 0x14
GPIO_INT_CLR_OFFSET: uint32 = 0x18

# Port stride (each port has 0x100 bytes of register space)
GPIO_PORT_STRIDE: uint32 = 0x100

# Direction constants
GPIO_DIR_INPUT: uint32 = 0
GPIO_DIR_OUTPUT: uint32 = 1

# Internal state tracking for software simulation
_gpio_state: Array[4, uint32]  # 4 ports worth of pin states
_gpio_dir: Array[4, uint32]    # 4 ports worth of direction settings
_gpio_initialized: bool = False

def _gpio_port_base(port: uint32) -> uint32:
    """Get base address for GPIO port."""
    return GPIO_BASE + (port * GPIO_PORT_STRIDE)

def gpio_init(port: uint32):
    """Initialize a GPIO port.

    Args:
        port: GPIO port number (0-3)
    """
    global _gpio_initialized
    if not _gpio_initialized:
        # Initialize state arrays
        i: int32 = 0
        while i < 4:
            _gpio_state[i] = 0
            _gpio_dir[i] = 0
            i = i + 1
        _gpio_initialized = True

    base: uint32 = _gpio_port_base(port)
    # Reset all pins to input
    mmio_write(base + GPIO_DIR_OFFSET, 0)
    # Clear all interrupts
    mmio_write(base + GPIO_INT_CLR_OFFSET, 0xFFFFFFFF)
    # Disable all interrupts
    mmio_write(base + GPIO_INT_EN_OFFSET, 0)
    # Track direction
    if port < 4:
        _gpio_dir[port] = 0

def gpio_set_dir(port: uint32, pin: uint32, direction: uint32):
    """Set direction for a GPIO pin.

    Args:
        port: GPIO port number (0-3)
        pin: Pin number (0-31)
        direction: GPIO_DIR_INPUT (0) or GPIO_DIR_OUTPUT (1)
    """
    if pin >= 32:
        return

    base: uint32 = _gpio_port_base(port)
    mask: uint32 = 1 << pin

    if direction == GPIO_DIR_OUTPUT:
        mmio_set_bits(base + GPIO_DIR_OFFSET, mask)
        if port < 4:
            _gpio_dir[port] = _gpio_dir[port] | mask
    else:
        mmio_clear_bits(base + GPIO_DIR_OFFSET, mask)
        if port < 4:
            _gpio_dir[port] = _gpio_dir[port] & ~mask

def gpio_write(port: uint32, pin: uint32, value: uint32):
    """Write a value to a GPIO pin.

    Args:
        port: GPIO port number (0-3)
        pin: Pin number (0-31)
        value: 0 for low, non-zero for high
    """
    if pin >= 32:
        return

    base: uint32 = _gpio_port_base(port)
    mask: uint32 = 1 << pin

    if value != 0:
        mmio_set_bits(base + GPIO_DATA_OFFSET, mask)
        if port < 4:
            _gpio_state[port] = _gpio_state[port] | mask
    else:
        mmio_clear_bits(base + GPIO_DATA_OFFSET, mask)
        if port < 4:
            _gpio_state[port] = _gpio_state[port] & ~mask

def gpio_read(port: uint32, pin: uint32) -> uint32:
    """Read a GPIO pin value.

    Args:
        port: GPIO port number (0-3)
        pin: Pin number (0-31)

    Returns:
        0 if low, 1 if high
    """
    if pin >= 32:
        return 0

    base: uint32 = _gpio_port_base(port)
    mask: uint32 = 1 << pin
    data: uint32 = mmio_read(base + GPIO_DATA_OFFSET)

    # For simulation, return tracked state if output
    if port < 4:
        if (_gpio_dir[port] & mask) != 0:
            return (_gpio_state[port] >> pin) & 1

    return (data >> pin) & 1

def gpio_toggle(port: uint32, pin: uint32):
    """Toggle a GPIO pin.

    Args:
        port: GPIO port number (0-3)
        pin: Pin number (0-31)
    """
    if pin >= 32:
        return

    base: uint32 = _gpio_port_base(port)
    mask: uint32 = 1 << pin

    mmio_toggle_bits(base + GPIO_DATA_OFFSET, mask)
    if port < 4:
        _gpio_state[port] = _gpio_state[port] ^ mask

def gpio_write_port(port: uint32, value: uint32):
    """Write all pins of a GPIO port at once.

    Args:
        port: GPIO port number (0-3)
        value: 32-bit value for all pins
    """
    base: uint32 = _gpio_port_base(port)
    mmio_write(base + GPIO_DATA_OFFSET, value)
    if port < 4:
        _gpio_state[port] = value

def gpio_read_port(port: uint32) -> uint32:
    """Read all pins of a GPIO port.

    Args:
        port: GPIO port number (0-3)

    Returns:
        32-bit value with pin states
    """
    base: uint32 = _gpio_port_base(port)
    return mmio_read(base + GPIO_DATA_OFFSET)

# ============================================================================
# SPI - Serial Peripheral Interface
# ============================================================================
#
# SPI Register Map:
#   Offset 0x00: CTRL      - Control register
#   Offset 0x04: STATUS    - Status register
#   Offset 0x08: DATA      - Data register (TX/RX)
#   Offset 0x0C: BAUD      - Baud rate divisor
#   Offset 0x10: CS        - Chip select control

SPI_CTRL_OFFSET: uint32 = 0x00
SPI_STATUS_OFFSET: uint32 = 0x04
SPI_DATA_OFFSET: uint32 = 0x08
SPI_BAUD_OFFSET: uint32 = 0x0C
SPI_CS_OFFSET: uint32 = 0x10

# SPI control register bits
SPI_CTRL_ENABLE: uint32 = 0x01
SPI_CTRL_MASTER: uint32 = 0x02
SPI_CTRL_CPOL: uint32 = 0x04     # Clock polarity
SPI_CTRL_CPHA: uint32 = 0x08     # Clock phase
SPI_CTRL_LSBFIRST: uint32 = 0x10

# SPI status register bits
SPI_STATUS_TX_EMPTY: uint32 = 0x01
SPI_STATUS_TX_FULL: uint32 = 0x02
SPI_STATUS_RX_EMPTY: uint32 = 0x04
SPI_STATUS_RX_FULL: uint32 = 0x08
SPI_STATUS_BUSY: uint32 = 0x10

# SPI instance stride
SPI_STRIDE: uint32 = 0x100

# SPI mode definitions (CPOL | CPHA combinations)
SPI_MODE_0: uint32 = 0x00  # CPOL=0, CPHA=0
SPI_MODE_1: uint32 = 0x08  # CPOL=0, CPHA=1
SPI_MODE_2: uint32 = 0x04  # CPOL=1, CPHA=0
SPI_MODE_3: uint32 = 0x0C  # CPOL=1, CPHA=1

def _spi_base(instance: uint32) -> uint32:
    """Get base address for SPI instance."""
    return SPI_BASE + (instance * SPI_STRIDE)

def spi_init(instance: uint32, mode: uint32, baud_div: uint32):
    """Initialize SPI peripheral.

    Args:
        instance: SPI instance number (0-2)
        mode: SPI mode (SPI_MODE_0 to SPI_MODE_3)
        baud_div: Baud rate divisor (higher = slower)
    """
    base: uint32 = _spi_base(instance)

    # Disable SPI first
    mmio_write(base + SPI_CTRL_OFFSET, 0)

    # Set baud rate
    mmio_write(base + SPI_BAUD_OFFSET, baud_div)

    # Configure as master with specified mode
    ctrl: uint32 = SPI_CTRL_ENABLE | SPI_CTRL_MASTER | (mode & 0x0C)
    mmio_write(base + SPI_CTRL_OFFSET, ctrl)

    # Deselect all chip selects
    mmio_write(base + SPI_CS_OFFSET, 0xFF)

def spi_transfer(instance: uint32, tx_data: uint32) -> uint32:
    """Transfer one byte over SPI (full duplex).

    Args:
        instance: SPI instance number
        tx_data: Byte to transmit (0-255)

    Returns:
        Received byte
    """
    base: uint32 = _spi_base(instance)

    # Wait for TX empty
    timeout: int32 = 10000
    while timeout > 0:
        status: uint32 = mmio_read(base + SPI_STATUS_OFFSET)
        if (status & SPI_STATUS_TX_FULL) == 0:
            break
        timeout = timeout - 1

    # Write data to transmit
    mmio_write(base + SPI_DATA_OFFSET, tx_data & 0xFF)

    # Wait for transfer complete (not busy and RX has data)
    timeout = 10000
    while timeout > 0:
        status: uint32 = mmio_read(base + SPI_STATUS_OFFSET)
        if (status & SPI_STATUS_BUSY) == 0:
            if (status & SPI_STATUS_RX_EMPTY) == 0:
                break
        timeout = timeout - 1

    # Read received data
    return mmio_read(base + SPI_DATA_OFFSET) & 0xFF

def spi_write(instance: uint32, data: Ptr[uint8], len: int32):
    """Write multiple bytes over SPI.

    Args:
        instance: SPI instance number
        data: Pointer to data buffer
        len: Number of bytes to write
    """
    i: int32 = 0
    while i < len:
        spi_transfer(instance, cast[uint32](data[i]))
        i = i + 1

def spi_read(instance: uint32, data: Ptr[uint8], len: int32):
    """Read multiple bytes over SPI.

    Sends 0x00 as dummy bytes while reading.

    Args:
        instance: SPI instance number
        data: Pointer to receive buffer
        len: Number of bytes to read
    """
    i: int32 = 0
    while i < len:
        data[i] = cast[uint8](spi_transfer(instance, 0x00))
        i = i + 1

def spi_cs_select(instance: uint32, cs: uint32):
    """Assert chip select (active low).

    Args:
        instance: SPI instance number
        cs: Chip select number (0-7)
    """
    base: uint32 = _spi_base(instance)
    mask: uint32 = ~(1 << cs)
    mmio_write(base + SPI_CS_OFFSET, mask & 0xFF)

def spi_cs_deselect(instance: uint32):
    """Deassert all chip selects.

    Args:
        instance: SPI instance number
    """
    base: uint32 = _spi_base(instance)
    mmio_write(base + SPI_CS_OFFSET, 0xFF)

# ============================================================================
# I2C - Inter-Integrated Circuit
# ============================================================================
#
# I2C Register Map:
#   Offset 0x00: CTRL      - Control register
#   Offset 0x04: STATUS    - Status register
#   Offset 0x08: DATA      - Data register
#   Offset 0x0C: ADDR      - Slave address
#   Offset 0x10: BAUD      - Baud rate divisor
#   Offset 0x14: CMD       - Command register

I2C_CTRL_OFFSET: uint32 = 0x00
I2C_STATUS_OFFSET: uint32 = 0x04
I2C_DATA_OFFSET: uint32 = 0x08
I2C_ADDR_OFFSET: uint32 = 0x0C
I2C_BAUD_OFFSET: uint32 = 0x10
I2C_CMD_OFFSET: uint32 = 0x14

# I2C control register bits
I2C_CTRL_ENABLE: uint32 = 0x01
I2C_CTRL_MASTER: uint32 = 0x02
I2C_CTRL_INT_EN: uint32 = 0x04

# I2C status register bits
I2C_STATUS_BUSY: uint32 = 0x01
I2C_STATUS_ACK: uint32 = 0x02
I2C_STATUS_NACK: uint32 = 0x04
I2C_STATUS_ARB_LOST: uint32 = 0x08
I2C_STATUS_TX_EMPTY: uint32 = 0x10
I2C_STATUS_RX_FULL: uint32 = 0x20

# I2C command register values
I2C_CMD_START: uint32 = 0x01
I2C_CMD_STOP: uint32 = 0x02
I2C_CMD_READ: uint32 = 0x04
I2C_CMD_WRITE: uint32 = 0x08
I2C_CMD_ACK: uint32 = 0x10
I2C_CMD_NACK: uint32 = 0x20

# I2C instance stride
I2C_STRIDE: uint32 = 0x100

# I2C return codes
I2C_OK: int32 = 0
I2C_ERR_NACK: int32 = -1
I2C_ERR_TIMEOUT: int32 = -2
I2C_ERR_ARB_LOST: int32 = -3

def _i2c_base(instance: uint32) -> uint32:
    """Get base address for I2C instance."""
    return I2C_BASE + (instance * I2C_STRIDE)

def i2c_init(instance: uint32, baud_div: uint32):
    """Initialize I2C peripheral.

    Args:
        instance: I2C instance number (0-2)
        baud_div: Baud rate divisor (for ~100kHz or ~400kHz)
    """
    base: uint32 = _i2c_base(instance)

    # Disable I2C first
    mmio_write(base + I2C_CTRL_OFFSET, 0)

    # Set baud rate
    mmio_write(base + I2C_BAUD_OFFSET, baud_div)

    # Enable as master
    ctrl: uint32 = I2C_CTRL_ENABLE | I2C_CTRL_MASTER
    mmio_write(base + I2C_CTRL_OFFSET, ctrl)

def _i2c_wait_idle(base: uint32) -> int32:
    """Wait for I2C bus to be idle."""
    timeout: int32 = 10000
    while timeout > 0:
        status: uint32 = mmio_read(base + I2C_STATUS_OFFSET)
        if (status & I2C_STATUS_BUSY) == 0:
            return I2C_OK
        timeout = timeout - 1
    return I2C_ERR_TIMEOUT

def _i2c_check_ack(base: uint32) -> int32:
    """Check for ACK after transmission."""
    status: uint32 = mmio_read(base + I2C_STATUS_OFFSET)
    if (status & I2C_STATUS_NACK) != 0:
        return I2C_ERR_NACK
    if (status & I2C_STATUS_ARB_LOST) != 0:
        return I2C_ERR_ARB_LOST
    return I2C_OK

def i2c_write(instance: uint32, addr: uint32, data: Ptr[uint8], len: int32) -> int32:
    """Write data to I2C slave.

    Args:
        instance: I2C instance number
        addr: 7-bit slave address
        data: Pointer to data buffer
        len: Number of bytes to write

    Returns:
        I2C_OK on success, negative error code on failure
    """
    base: uint32 = _i2c_base(instance)
    result: int32 = I2C_OK

    # Wait for bus idle
    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        return result

    # Send START and address with write bit (bit 0 = 0)
    mmio_write(base + I2C_DATA_OFFSET, (addr << 1) & 0xFE)
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_START | I2C_CMD_WRITE)

    # Wait and check ACK
    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    result = _i2c_check_ack(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    # Send data bytes
    i: int32 = 0
    while i < len:
        mmio_write(base + I2C_DATA_OFFSET, cast[uint32](data[i]))
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_WRITE)

        result = _i2c_wait_idle(base)
        if result != I2C_OK:
            mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
            return result

        result = _i2c_check_ack(base)
        if result != I2C_OK:
            mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
            return result

        i = i + 1

    # Send STOP
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)

    return I2C_OK

def i2c_read(instance: uint32, addr: uint32, data: Ptr[uint8], len: int32) -> int32:
    """Read data from I2C slave.

    Args:
        instance: I2C instance number
        addr: 7-bit slave address
        data: Pointer to receive buffer
        len: Number of bytes to read

    Returns:
        I2C_OK on success, negative error code on failure
    """
    base: uint32 = _i2c_base(instance)
    result: int32 = I2C_OK

    # Wait for bus idle
    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        return result

    # Send START and address with read bit (bit 0 = 1)
    mmio_write(base + I2C_DATA_OFFSET, ((addr << 1) & 0xFE) | 0x01)
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_START | I2C_CMD_WRITE)

    # Wait and check ACK
    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    result = _i2c_check_ack(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    # Read data bytes
    i: int32 = 0
    while i < len:
        # ACK all bytes except the last one
        if i == len - 1:
            mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_READ | I2C_CMD_NACK)
        else:
            mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_READ | I2C_CMD_ACK)

        result = _i2c_wait_idle(base)
        if result != I2C_OK:
            mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
            return result

        data[i] = cast[uint8](mmio_read(base + I2C_DATA_OFFSET) & 0xFF)
        i = i + 1

    # Send STOP
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)

    return I2C_OK

def i2c_write_reg(instance: uint32, addr: uint32, reg: uint32, value: uint32) -> int32:
    """Write a single byte to a register on I2C slave.

    Args:
        instance: I2C instance number
        addr: 7-bit slave address
        reg: Register address
        value: Value to write

    Returns:
        I2C_OK on success, negative error code on failure
    """
    buf: Array[2, uint8]
    buf[0] = cast[uint8](reg & 0xFF)
    buf[1] = cast[uint8](value & 0xFF)
    return i2c_write(instance, addr, &buf[0], 2)

def i2c_read_reg(instance: uint32, addr: uint32, reg: uint32) -> int32:
    """Read a single byte from a register on I2C slave.

    Args:
        instance: I2C instance number
        addr: 7-bit slave address
        reg: Register address

    Returns:
        Register value (0-255) on success, negative error code on failure
    """
    base: uint32 = _i2c_base(instance)
    result: int32 = I2C_OK

    # Write register address (without stop)
    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        return result

    # Send START and address with write bit
    mmio_write(base + I2C_DATA_OFFSET, (addr << 1) & 0xFE)
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_START | I2C_CMD_WRITE)

    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    result = _i2c_check_ack(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    # Send register address
    mmio_write(base + I2C_DATA_OFFSET, reg & 0xFF)
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_WRITE)

    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    result = _i2c_check_ack(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    # Repeated START and address with read bit
    mmio_write(base + I2C_DATA_OFFSET, ((addr << 1) & 0xFE) | 0x01)
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_START | I2C_CMD_WRITE)

    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    result = _i2c_check_ack(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    # Read one byte with NACK
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_READ | I2C_CMD_NACK)

    result = _i2c_wait_idle(base)
    if result != I2C_OK:
        mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)
        return result

    value: uint32 = mmio_read(base + I2C_DATA_OFFSET) & 0xFF

    # Send STOP
    mmio_write(base + I2C_CMD_OFFSET, I2C_CMD_STOP)

    return cast[int32](value)

# ============================================================================
# PWM - Pulse Width Modulation
# ============================================================================
#
# PWM Register Map (per channel):
#   Offset 0x00: CTRL      - Control register
#   Offset 0x04: PERIOD    - Period value (frequency)
#   Offset 0x08: DUTY      - Duty cycle value
#   Offset 0x0C: COUNT     - Current counter value

PWM_CTRL_OFFSET: uint32 = 0x00
PWM_PERIOD_OFFSET: uint32 = 0x04
PWM_DUTY_OFFSET: uint32 = 0x08
PWM_COUNT_OFFSET: uint32 = 0x0C

# PWM control register bits
PWM_CTRL_ENABLE: uint32 = 0x01
PWM_CTRL_INVERT: uint32 = 0x02
PWM_CTRL_CENTER_ALIGN: uint32 = 0x04

# PWM channel stride
PWM_CHANNEL_STRIDE: uint32 = 0x20

# System clock assumed to be 25MHz for MPS2-AN385
PWM_SYSCLK: uint32 = 25000000

# Internal state for simulation
_pwm_enabled: Array[8, bool]
_pwm_duty: Array[8, uint32]
_pwm_period: Array[8, uint32]

def _pwm_channel_base(channel: uint32) -> uint32:
    """Get base address for PWM channel."""
    return PWM_BASE + (channel * PWM_CHANNEL_STRIDE)

def pwm_init(channel: uint32, freq_hz: uint32):
    """Initialize PWM channel with specified frequency.

    Args:
        channel: PWM channel number (0-7)
        freq_hz: PWM frequency in Hz
    """
    base: uint32 = _pwm_channel_base(channel)

    # Disable channel first
    mmio_write(base + PWM_CTRL_OFFSET, 0)

    # Calculate period for desired frequency
    # period = sysclk / freq - 1
    period: uint32 = 0
    if freq_hz > 0:
        period = (PWM_SYSCLK / freq_hz) - 1

    mmio_write(base + PWM_PERIOD_OFFSET, period)
    mmio_write(base + PWM_DUTY_OFFSET, 0)

    # Track state
    if channel < 8:
        _pwm_enabled[channel] = False
        _pwm_duty[channel] = 0
        _pwm_period[channel] = period

def pwm_set_duty(channel: uint32, duty_percent: uint32):
    """Set PWM duty cycle.

    Args:
        channel: PWM channel number (0-7)
        duty_percent: Duty cycle 0-100 (percentage)
    """
    if duty_percent > 100:
        duty_percent = 100

    base: uint32 = _pwm_channel_base(channel)

    # Get period and calculate duty value
    period: uint32 = mmio_read(base + PWM_PERIOD_OFFSET)
    duty_val: uint32 = (period * duty_percent) / 100

    mmio_write(base + PWM_DUTY_OFFSET, duty_val)

    if channel < 8:
        _pwm_duty[channel] = duty_val

def pwm_set_duty_raw(channel: uint32, duty_val: uint32):
    """Set PWM duty cycle with raw value.

    Args:
        channel: PWM channel number (0-7)
        duty_val: Raw duty cycle value (0 to period)
    """
    base: uint32 = _pwm_channel_base(channel)
    mmio_write(base + PWM_DUTY_OFFSET, duty_val)

    if channel < 8:
        _pwm_duty[channel] = duty_val

def pwm_set_freq(channel: uint32, freq_hz: uint32):
    """Change PWM frequency.

    Note: This may affect duty cycle. Call pwm_set_duty after if needed.

    Args:
        channel: PWM channel number (0-7)
        freq_hz: New frequency in Hz
    """
    base: uint32 = _pwm_channel_base(channel)

    # Calculate new period
    period: uint32 = 0
    if freq_hz > 0:
        period = (PWM_SYSCLK / freq_hz) - 1

    mmio_write(base + PWM_PERIOD_OFFSET, period)

    if channel < 8:
        _pwm_period[channel] = period

def pwm_enable(channel: uint32):
    """Enable PWM output.

    Args:
        channel: PWM channel number (0-7)
    """
    base: uint32 = _pwm_channel_base(channel)
    mmio_set_bits(base + PWM_CTRL_OFFSET, PWM_CTRL_ENABLE)

    if channel < 8:
        _pwm_enabled[channel] = True

def pwm_disable(channel: uint32):
    """Disable PWM output.

    Args:
        channel: PWM channel number (0-7)
    """
    base: uint32 = _pwm_channel_base(channel)
    mmio_clear_bits(base + PWM_CTRL_OFFSET, PWM_CTRL_ENABLE)

    if channel < 8:
        _pwm_enabled[channel] = False

def pwm_is_enabled(channel: uint32) -> bool:
    """Check if PWM channel is enabled.

    Args:
        channel: PWM channel number (0-7)

    Returns:
        True if enabled, False otherwise
    """
    if channel < 8:
        return _pwm_enabled[channel]
    return False

# ============================================================================
# ADC - Analog to Digital Converter
# ============================================================================
#
# ADC Register Map:
#   Offset 0x00: CTRL      - Control register
#   Offset 0x04: STATUS    - Status register
#   Offset 0x08: DATA      - Conversion result
#   Offset 0x0C: CHANNEL   - Channel select
#   Offset 0x10: CONFIG    - Configuration (resolution, sample time)

ADC_CTRL_OFFSET: uint32 = 0x00
ADC_STATUS_OFFSET: uint32 = 0x04
ADC_DATA_OFFSET: uint32 = 0x08
ADC_CHANNEL_OFFSET: uint32 = 0x0C
ADC_CONFIG_OFFSET: uint32 = 0x10

# ADC control register bits
ADC_CTRL_ENABLE: uint32 = 0x01
ADC_CTRL_START: uint32 = 0x02
ADC_CTRL_CONT: uint32 = 0x04    # Continuous mode

# ADC status register bits
ADC_STATUS_READY: uint32 = 0x01
ADC_STATUS_BUSY: uint32 = 0x02
ADC_STATUS_EOC: uint32 = 0x04   # End of conversion

# ADC configuration bits
ADC_CONFIG_12BIT: uint32 = 0x00
ADC_CONFIG_10BIT: uint32 = 0x01
ADC_CONFIG_8BIT: uint32 = 0x02

# ADC reference voltage (millivolts)
ADC_VREF_MV: uint32 = 3300  # 3.3V reference

# Internal state for simulation
_adc_enabled: bool = False
_adc_resolution: uint32 = 12
_adc_last_channel: uint32 = 0

def adc_init(resolution: uint32):
    """Initialize ADC.

    Args:
        resolution: ADC resolution (8, 10, or 12 bits)
    """
    global _adc_enabled, _adc_resolution

    # Disable ADC first
    mmio_write(ADC_BASE + ADC_CTRL_OFFSET, 0)

    # Set resolution
    config: uint32 = ADC_CONFIG_12BIT
    if resolution == 10:
        config = ADC_CONFIG_10BIT
        _adc_resolution = 10
    elif resolution == 8:
        config = ADC_CONFIG_8BIT
        _adc_resolution = 8
    else:
        _adc_resolution = 12

    mmio_write(ADC_BASE + ADC_CONFIG_OFFSET, config)

    # Enable ADC
    mmio_write(ADC_BASE + ADC_CTRL_OFFSET, ADC_CTRL_ENABLE)
    _adc_enabled = True

def adc_read(channel: uint32) -> uint32:
    """Read ADC value from channel.

    Args:
        channel: ADC channel number (0-7)

    Returns:
        ADC value (0 to 2^resolution - 1)
    """
    global _adc_last_channel

    # Select channel
    mmio_write(ADC_BASE + ADC_CHANNEL_OFFSET, channel & 0x07)
    _adc_last_channel = channel

    # Start conversion
    mmio_set_bits(ADC_BASE + ADC_CTRL_OFFSET, ADC_CTRL_START)

    # Wait for conversion complete
    timeout: int32 = 10000
    while timeout > 0:
        status: uint32 = mmio_read(ADC_BASE + ADC_STATUS_OFFSET)
        if (status & ADC_STATUS_EOC) != 0:
            break
        timeout = timeout - 1

    # Read result
    result: uint32 = mmio_read(ADC_BASE + ADC_DATA_OFFSET)

    # Mask to resolution
    if _adc_resolution == 8:
        return result & 0xFF
    elif _adc_resolution == 10:
        return result & 0x3FF
    return result & 0xFFF

def adc_read_mv(channel: uint32) -> uint32:
    """Read ADC value converted to millivolts.

    Args:
        channel: ADC channel number (0-7)

    Returns:
        Voltage in millivolts (0 to VREF)
    """
    raw: uint32 = adc_read(channel)

    # Calculate millivolts: (raw * VREF) / max_value
    max_val: uint32 = 4095  # 12-bit default
    if _adc_resolution == 10:
        max_val = 1023
    elif _adc_resolution == 8:
        max_val = 255

    return (raw * ADC_VREF_MV) / max_val

def adc_read_raw(channel: uint32) -> uint32:
    """Read raw ADC value (alias for adc_read).

    Args:
        channel: ADC channel number (0-7)

    Returns:
        Raw ADC value
    """
    return adc_read(channel)

def adc_set_resolution(resolution: uint32):
    """Change ADC resolution.

    Args:
        resolution: New resolution (8, 10, or 12 bits)
    """
    global _adc_resolution

    config: uint32 = ADC_CONFIG_12BIT
    if resolution == 10:
        config = ADC_CONFIG_10BIT
        _adc_resolution = 10
    elif resolution == 8:
        config = ADC_CONFIG_8BIT
        _adc_resolution = 8
    else:
        _adc_resolution = 12

    mmio_write(ADC_BASE + ADC_CONFIG_OFFSET, config)

def adc_disable():
    """Disable ADC to save power."""
    global _adc_enabled
    mmio_clear_bits(ADC_BASE + ADC_CTRL_OFFSET, ADC_CTRL_ENABLE)
    _adc_enabled = False

def adc_enable():
    """Re-enable ADC after disable."""
    global _adc_enabled
    mmio_set_bits(ADC_BASE + ADC_CTRL_OFFSET, ADC_CTRL_ENABLE)
    _adc_enabled = True
