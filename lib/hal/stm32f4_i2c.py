# STM32F4 I2C Hardware Abstraction Layer
#
# Hardware I2C driver for STM32F405/F407 supporting I2C1, I2C2, I2C3.
# Supports standard (100kHz) and fast (400kHz) modes.
#
# Default pins:
#   I2C1: PB6 (SCL), PB7 (SDA) or PB8 (SCL), PB9 (SDA)
#   I2C2: PB10 (SCL), PB11 (SDA)
#   I2C3: PA8 (SCL), PC9 (SDA)

# ============================================================================
# Base Addresses
# ============================================================================

I2C1_BASE: uint32 = 0x40005400
I2C2_BASE: uint32 = 0x40005800
I2C3_BASE: uint32 = 0x40005C00

RCC_BASE: uint32 = 0x40023800
GPIOA_BASE: uint32 = 0x40020000
GPIOB_BASE: uint32 = 0x40020400
GPIOC_BASE: uint32 = 0x40020800

# ============================================================================
# I2C Register Offsets
# ============================================================================

I2C_CR1: uint32 = 0x00      # Control register 1
I2C_CR2: uint32 = 0x04      # Control register 2
I2C_OAR1: uint32 = 0x08     # Own address register 1
I2C_OAR2: uint32 = 0x0C     # Own address register 2
I2C_DR: uint32 = 0x10       # Data register
I2C_SR1: uint32 = 0x14      # Status register 1
I2C_SR2: uint32 = 0x18      # Status register 2
I2C_CCR: uint32 = 0x1C      # Clock control register
I2C_TRISE: uint32 = 0x20    # Rise time register

# CR1 bits
I2C_CR1_PE: uint32 = 0x01       # Peripheral enable
I2C_CR1_SMBUS: uint32 = 0x02    # SMBus mode
I2C_CR1_SMBTYPE: uint32 = 0x08  # SMBus type
I2C_CR1_ENARP: uint32 = 0x10    # ARP enable
I2C_CR1_ENPEC: uint32 = 0x20    # PEC enable
I2C_CR1_ENGC: uint32 = 0x40     # General call enable
I2C_CR1_NOSTRETCH: uint32 = 0x80  # Clock stretching disable
I2C_CR1_START: uint32 = 0x100   # Start generation
I2C_CR1_STOP: uint32 = 0x200    # Stop generation
I2C_CR1_ACK: uint32 = 0x400     # Acknowledge enable
I2C_CR1_POS: uint32 = 0x800     # Acknowledge/PEC position
I2C_CR1_PEC: uint32 = 0x1000    # Packet error checking
I2C_CR1_ALERT: uint32 = 0x2000  # SMBus alert
I2C_CR1_SWRST: uint32 = 0x8000  # Software reset

# SR1 bits
I2C_SR1_SB: uint32 = 0x01       # Start bit
I2C_SR1_ADDR: uint32 = 0x02     # Address sent/matched
I2C_SR1_BTF: uint32 = 0x04      # Byte transfer finished
I2C_SR1_ADD10: uint32 = 0x08    # 10-bit header sent
I2C_SR1_STOPF: uint32 = 0x10    # Stop detection
I2C_SR1_RXNE: uint32 = 0x40     # Data register not empty
I2C_SR1_TXE: uint32 = 0x80      # Data register empty
I2C_SR1_BERR: uint32 = 0x100    # Bus error
I2C_SR1_ARLO: uint32 = 0x200    # Arbitration lost
I2C_SR1_AF: uint32 = 0x400      # Acknowledge failure
I2C_SR1_OVR: uint32 = 0x800     # Overrun/underrun
I2C_SR1_PECERR: uint32 = 0x1000 # PEC error
I2C_SR1_TIMEOUT: uint32 = 0x4000  # Timeout
I2C_SR1_SMBALERT: uint32 = 0x8000  # SMBus alert

# SR2 bits
I2C_SR2_MSL: uint32 = 0x01      # Master/slave
I2C_SR2_BUSY: uint32 = 0x02     # Bus busy
I2C_SR2_TRA: uint32 = 0x04      # Transmitter/receiver
I2C_SR2_GENCALL: uint32 = 0x10  # General call address
I2C_SR2_DUALF: uint32 = 0x80    # Dual flag

# CCR bits
I2C_CCR_FS: uint32 = 0x8000     # Fast mode
I2C_CCR_DUTY: uint32 = 0x4000   # Fast mode duty cycle

# ============================================================================
# Constants
# ============================================================================

I2C_SPEED_STANDARD: uint32 = 100000
I2C_SPEED_FAST: uint32 = 400000

I2C_OK: int32 = 0
I2C_ERR_NACK: int32 = -1
I2C_ERR_TIMEOUT: int32 = -2
I2C_ERR_BUS: int32 = -3

# APB1 clock (42 MHz max)
APB1_CLOCK: uint32 = 42000000

# RCC register offsets
RCC_AHB1ENR: uint32 = 0x30
RCC_APB1ENR: uint32 = 0x40

# GPIO register offsets
GPIO_MODER: uint32 = 0x00
GPIO_OTYPER: uint32 = 0x04
GPIO_OSPEEDR: uint32 = 0x08
GPIO_PUPDR: uint32 = 0x0C
GPIO_AFRL: uint32 = 0x20
GPIO_AFRH: uint32 = 0x24

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _i2c_base(i2c: uint32) -> uint32:
    """Get base address for I2C instance (1-3)."""
    if i2c == 1:
        return I2C1_BASE
    elif i2c == 2:
        return I2C2_BASE
    return I2C3_BASE

# ============================================================================
# Clock Enable
# ============================================================================

def i2c_enable_clock(i2c: uint32):
    """Enable clock for I2C peripheral.

    Args:
        i2c: I2C number (1-3)
    """
    val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
    if i2c == 1:
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 21))
    elif i2c == 2:
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 22))
    elif i2c == 3:
        mmio_write(RCC_BASE + RCC_APB1ENR, val | (1 << 23))

# ============================================================================
# I2C Initialization
# ============================================================================

def i2c_init(i2c: uint32, speed: uint32):
    """Initialize I2C peripheral.

    Args:
        i2c: I2C number (1-3)
        speed: I2C_SPEED_STANDARD (100kHz) or I2C_SPEED_FAST (400kHz)
    """
    base: uint32 = _i2c_base(i2c)

    # Enable I2C clock
    i2c_enable_clock(i2c)

    # Disable I2C and reset
    mmio_write(base + I2C_CR1, I2C_CR1_SWRST)
    mmio_write(base + I2C_CR1, 0)

    # Set peripheral clock frequency (APB1 = 42MHz)
    freq_mhz: uint32 = APB1_CLOCK / 1000000
    mmio_write(base + I2C_CR2, freq_mhz)

    # Calculate CCR for requested speed
    # Standard mode: CCR = Tscl / (2 * Tpclk) = fPCLK / (2 * fI2C)
    # Fast mode: CCR = Tscl / (3 * Tpclk) for duty=0
    ccr: uint32 = 0
    trise: uint32 = 0

    if speed >= I2C_SPEED_FAST:
        # Fast mode (400 kHz)
        ccr = APB1_CLOCK / (3 * speed)
        if ccr < 1:
            ccr = 1
        ccr = ccr | I2C_CCR_FS
        # Rise time: 300ns max in fast mode
        # TRISE = (300ns / Tpclk) + 1 = (300ns * 42MHz) + 1 = 13
        trise = 13
    else:
        # Standard mode (100 kHz)
        ccr = APB1_CLOCK / (2 * speed)
        if ccr < 4:
            ccr = 4  # Minimum value
        # Rise time: 1000ns max in standard mode
        # TRISE = (1000ns / Tpclk) + 1 = (1000ns * 42MHz) + 1 = 43
        trise = 43

    mmio_write(base + I2C_CCR, ccr)
    mmio_write(base + I2C_TRISE, trise)

    # Enable I2C
    mmio_write(base + I2C_CR1, I2C_CR1_PE)

def i2c_init_gpio(i2c: uint32, scl_port: uint32, scl_pin: uint32,
                  sda_port: uint32, sda_pin: uint32):
    """Configure GPIO pins for I2C (open-drain with pull-ups).

    Args:
        i2c: I2C number (1-3)
        scl_port: SCL GPIO port base address
        scl_pin: SCL pin number (0-15)
        sda_port: SDA GPIO port base address
        sda_pin: SDA pin number (0-15)
    """
    # AF4 for I2C1-3
    af: uint32 = 4

    # Configure SCL pin: AF, open-drain, pull-up
    # MODER = Alternate function (10)
    moder: uint32 = mmio_read(scl_port + GPIO_MODER)
    moder = moder & ~(3 << (scl_pin * 2))
    moder = moder | (2 << (scl_pin * 2))
    mmio_write(scl_port + GPIO_MODER, moder)

    # OTYPER = Open-drain (1)
    otyper: uint32 = mmio_read(scl_port + GPIO_OTYPER)
    otyper = otyper | (1 << scl_pin)
    mmio_write(scl_port + GPIO_OTYPER, otyper)

    # PUPDR = Pull-up (01)
    pupdr: uint32 = mmio_read(scl_port + GPIO_PUPDR)
    pupdr = pupdr & ~(3 << (scl_pin * 2))
    pupdr = pupdr | (1 << (scl_pin * 2))
    mmio_write(scl_port + GPIO_PUPDR, pupdr)

    # Set alternate function
    if scl_pin < 8:
        afr: uint32 = mmio_read(scl_port + GPIO_AFRL)
        afr = afr & ~(0xF << (scl_pin * 4))
        afr = afr | (af << (scl_pin * 4))
        mmio_write(scl_port + GPIO_AFRL, afr)
    else:
        afr: uint32 = mmio_read(scl_port + GPIO_AFRH)
        afr = afr & ~(0xF << ((scl_pin - 8) * 4))
        afr = afr | (af << ((scl_pin - 8) * 4))
        mmio_write(scl_port + GPIO_AFRH, afr)

    # Configure SDA pin same way
    moder = mmio_read(sda_port + GPIO_MODER)
    moder = moder & ~(3 << (sda_pin * 2))
    moder = moder | (2 << (sda_pin * 2))
    mmio_write(sda_port + GPIO_MODER, moder)

    otyper = mmio_read(sda_port + GPIO_OTYPER)
    otyper = otyper | (1 << sda_pin)
    mmio_write(sda_port + GPIO_OTYPER, otyper)

    pupdr = mmio_read(sda_port + GPIO_PUPDR)
    pupdr = pupdr & ~(3 << (sda_pin * 2))
    pupdr = pupdr | (1 << (sda_pin * 2))
    mmio_write(sda_port + GPIO_PUPDR, pupdr)

    if sda_pin < 8:
        afr = mmio_read(sda_port + GPIO_AFRL)
        afr = afr & ~(0xF << (sda_pin * 4))
        afr = afr | (af << (sda_pin * 4))
        mmio_write(sda_port + GPIO_AFRL, afr)
    else:
        afr = mmio_read(sda_port + GPIO_AFRH)
        afr = afr & ~(0xF << ((sda_pin - 8) * 4))
        afr = afr | (af << ((sda_pin - 8) * 4))
        mmio_write(sda_port + GPIO_AFRH, afr)

# ============================================================================
# I2C Low-Level Operations
# ============================================================================

def _i2c_wait_flag(base: uint32, flag: uint32, set_val: bool) -> int32:
    """Wait for flag to reach desired state."""
    timeout: int32 = 100000
    while timeout > 0:
        sr1: uint32 = mmio_read(base + I2C_SR1)
        # Check for errors
        if (sr1 & I2C_SR1_AF) != 0:
            # Clear AF flag
            mmio_write(base + I2C_SR1, sr1 & ~I2C_SR1_AF)
            return I2C_ERR_NACK
        if (sr1 & (I2C_SR1_BERR | I2C_SR1_ARLO)) != 0:
            return I2C_ERR_BUS

        if set_val:
            if (sr1 & flag) != 0:
                return I2C_OK
        else:
            if (sr1 & flag) == 0:
                return I2C_OK

        timeout = timeout - 1

    return I2C_ERR_TIMEOUT

def _i2c_start(base: uint32, addr: uint32, is_read: bool) -> int32:
    """Generate START condition and send address."""
    # Enable ACK
    cr1: uint32 = mmio_read(base + I2C_CR1)
    mmio_write(base + I2C_CR1, cr1 | I2C_CR1_ACK)

    # Generate START
    cr1 = mmio_read(base + I2C_CR1)
    mmio_write(base + I2C_CR1, cr1 | I2C_CR1_START)

    # Wait for SB (start bit)
    result: int32 = _i2c_wait_flag(base, I2C_SR1_SB, True)
    if result != I2C_OK:
        return result

    # Send address
    addr_byte: uint32 = (addr << 1) & 0xFE
    if is_read:
        addr_byte = addr_byte | 0x01
    mmio_write(base + I2C_DR, addr_byte)

    # Wait for ADDR
    result = _i2c_wait_flag(base, I2C_SR1_ADDR, True)
    if result != I2C_OK:
        # Generate STOP on NACK
        cr1 = mmio_read(base + I2C_CR1)
        mmio_write(base + I2C_CR1, cr1 | I2C_CR1_STOP)
        return result

    # Clear ADDR by reading SR1 then SR2
    dummy: uint32 = mmio_read(base + I2C_SR1)
    dummy = mmio_read(base + I2C_SR2)

    return I2C_OK

def _i2c_stop(base: uint32):
    """Generate STOP condition."""
    cr1: uint32 = mmio_read(base + I2C_CR1)
    mmio_write(base + I2C_CR1, cr1 | I2C_CR1_STOP)

# ============================================================================
# I2C Data Transfer
# ============================================================================

def i2c_write(i2c: uint32, addr: uint32, data: Ptr[uint8], len: int32) -> int32:
    """Write data to I2C slave.

    Args:
        i2c: I2C number (1-3)
        addr: 7-bit slave address
        data: Data buffer
        len: Number of bytes

    Returns:
        I2C_OK on success
    """
    base: uint32 = _i2c_base(i2c)

    # Wait for bus not busy
    timeout: int32 = 10000
    while timeout > 0:
        if (mmio_read(base + I2C_SR2) & I2C_SR2_BUSY) == 0:
            break
        timeout = timeout - 1
    if timeout == 0:
        return I2C_ERR_TIMEOUT

    # Send START and address
    result: int32 = _i2c_start(base, addr, False)
    if result != I2C_OK:
        return result

    # Send data bytes
    i: int32 = 0
    while i < len:
        # Wait for TXE
        result = _i2c_wait_flag(base, I2C_SR1_TXE, True)
        if result != I2C_OK:
            _i2c_stop(base)
            return result

        mmio_write(base + I2C_DR, cast[uint32](data[i]))
        i = i + 1

    # Wait for BTF (byte transfer finished)
    result = _i2c_wait_flag(base, I2C_SR1_BTF, True)

    # Generate STOP
    _i2c_stop(base)

    return result

def i2c_read(i2c: uint32, addr: uint32, data: Ptr[uint8], len: int32) -> int32:
    """Read data from I2C slave.

    Args:
        i2c: I2C number (1-3)
        addr: 7-bit slave address
        data: Buffer for received data
        len: Number of bytes

    Returns:
        I2C_OK on success
    """
    base: uint32 = _i2c_base(i2c)

    if len == 0:
        return I2C_OK

    # Wait for bus not busy
    timeout: int32 = 10000
    while timeout > 0:
        if (mmio_read(base + I2C_SR2) & I2C_SR2_BUSY) == 0:
            break
        timeout = timeout - 1
    if timeout == 0:
        return I2C_ERR_TIMEOUT

    # Enable ACK
    cr1: uint32 = mmio_read(base + I2C_CR1)
    mmio_write(base + I2C_CR1, cr1 | I2C_CR1_ACK)

    # Send START and address (read mode)
    result: int32 = _i2c_start(base, addr, True)
    if result != I2C_OK:
        return result

    # Read bytes
    i: int32 = 0
    while i < len:
        if i == len - 1:
            # Last byte: disable ACK, generate STOP
            cr1 = mmio_read(base + I2C_CR1)
            mmio_write(base + I2C_CR1, cr1 & ~I2C_CR1_ACK)
            _i2c_stop(base)

        # Wait for RXNE
        result = _i2c_wait_flag(base, I2C_SR1_RXNE, True)
        if result != I2C_OK:
            return result

        data[i] = cast[uint8](mmio_read(base + I2C_DR) & 0xFF)
        i = i + 1

    return I2C_OK

def i2c_write_read(i2c: uint32, addr: uint32, wr_data: Ptr[uint8], wr_len: int32,
                   rd_data: Ptr[uint8], rd_len: int32) -> int32:
    """Write then read with repeated start.

    Args:
        i2c: I2C number (1-3)
        addr: 7-bit slave address
        wr_data: Data to write
        wr_len: Write length
        rd_data: Buffer for read data
        rd_len: Read length

    Returns:
        I2C_OK on success
    """
    base: uint32 = _i2c_base(i2c)

    # Wait for bus not busy
    timeout: int32 = 10000
    while timeout > 0:
        if (mmio_read(base + I2C_SR2) & I2C_SR2_BUSY) == 0:
            break
        timeout = timeout - 1
    if timeout == 0:
        return I2C_ERR_TIMEOUT

    # Send START and address (write)
    result: int32 = _i2c_start(base, addr, False)
    if result != I2C_OK:
        return result

    # Write data
    i: int32 = 0
    while i < wr_len:
        result = _i2c_wait_flag(base, I2C_SR1_TXE, True)
        if result != I2C_OK:
            _i2c_stop(base)
            return result
        mmio_write(base + I2C_DR, cast[uint32](wr_data[i]))
        i = i + 1

    # Wait for BTF
    result = _i2c_wait_flag(base, I2C_SR1_BTF, True)
    if result != I2C_OK:
        _i2c_stop(base)
        return result

    # Repeated START for read
    result = _i2c_start(base, addr, True)
    if result != I2C_OK:
        return result

    # Read data
    i = 0
    while i < rd_len:
        if i == rd_len - 1:
            cr1: uint32 = mmio_read(base + I2C_CR1)
            mmio_write(base + I2C_CR1, cr1 & ~I2C_CR1_ACK)
            _i2c_stop(base)

        result = _i2c_wait_flag(base, I2C_SR1_RXNE, True)
        if result != I2C_OK:
            return result

        rd_data[i] = cast[uint8](mmio_read(base + I2C_DR) & 0xFF)
        i = i + 1

    return I2C_OK

def i2c_write_reg(i2c: uint32, addr: uint32, reg: uint32, value: uint32) -> int32:
    """Write single byte to register."""
    buf: Array[2, uint8]
    buf[0] = cast[uint8](reg & 0xFF)
    buf[1] = cast[uint8](value & 0xFF)
    return i2c_write(i2c, addr, &buf[0], 2)

def i2c_read_reg(i2c: uint32, addr: uint32, reg: uint32) -> int32:
    """Read single byte from register."""
    reg_byte: uint8 = cast[uint8](reg & 0xFF)
    value: uint8 = 0
    result: int32 = i2c_write_read(i2c, addr, &reg_byte, 1, &value, 1)
    if result != I2C_OK:
        return result
    return cast[int32](value)
