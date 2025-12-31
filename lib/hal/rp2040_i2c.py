# RP2040 I2C Hardware Abstraction Layer
#
# Hardware I2C driver for RP2040 using the Synopsys DesignWare I2C.
# Supports I2C0 and I2C1 at standard (100kHz) and fast (400kHz) modes.
#
# Default pins:
#   I2C0: GPIO4 (SDA), GPIO5 (SCL)
#   I2C1: GPIO6 (SDA), GPIO7 (SCL)

# ============================================================================
# Base Addresses
# ============================================================================

I2C0_BASE: uint32 = 0x40044000
I2C1_BASE: uint32 = 0x40048000

IO_BANK0_BASE: uint32 = 0x40014000
RESETS_BASE: uint32 = 0x4000C000

# ============================================================================
# I2C Register Offsets (Synopsys DesignWare)
# ============================================================================

I2C_CON: uint32 = 0x00           # Control register
I2C_TAR: uint32 = 0x04           # Target address
I2C_SAR: uint32 = 0x08           # Slave address
I2C_DATA_CMD: uint32 = 0x10      # Data buffer and command
I2C_SS_SCL_HCNT: uint32 = 0x14   # Standard speed SCL high count
I2C_SS_SCL_LCNT: uint32 = 0x18   # Standard speed SCL low count
I2C_FS_SCL_HCNT: uint32 = 0x1C   # Fast speed SCL high count
I2C_FS_SCL_LCNT: uint32 = 0x20   # Fast speed SCL low count
I2C_INTR_STAT: uint32 = 0x2C     # Interrupt status
I2C_INTR_MASK: uint32 = 0x30     # Interrupt mask
I2C_RAW_INTR_STAT: uint32 = 0x34 # Raw interrupt status
I2C_RX_TL: uint32 = 0x38         # RX FIFO threshold
I2C_TX_TL: uint32 = 0x3C         # TX FIFO threshold
I2C_CLR_INTR: uint32 = 0x40      # Clear combined interrupt
I2C_CLR_RX_UNDER: uint32 = 0x44
I2C_CLR_RX_OVER: uint32 = 0x48
I2C_CLR_TX_OVER: uint32 = 0x4C
I2C_CLR_RD_REQ: uint32 = 0x50
I2C_CLR_TX_ABRT: uint32 = 0x54
I2C_CLR_RX_DONE: uint32 = 0x58
I2C_CLR_ACTIVITY: uint32 = 0x5C
I2C_CLR_STOP_DET: uint32 = 0x60
I2C_CLR_START_DET: uint32 = 0x64
I2C_CLR_GEN_CALL: uint32 = 0x68
I2C_ENABLE: uint32 = 0x6C        # Enable register
I2C_STATUS: uint32 = 0x70        # Status register
I2C_TXFLR: uint32 = 0x74         # TX FIFO level
I2C_RXFLR: uint32 = 0x78         # RX FIFO level
I2C_SDA_HOLD: uint32 = 0x7C      # SDA hold time
I2C_TX_ABRT_SOURCE: uint32 = 0x80
I2C_SDA_SETUP: uint32 = 0x94     # SDA setup time
I2C_FS_SPKLEN: uint32 = 0xA0     # Spike suppression limit

# Control register bits
I2C_CON_MASTER_MODE: uint32 = 0x01
I2C_CON_SPEED_STANDARD: uint32 = 0x02
I2C_CON_SPEED_FAST: uint32 = 0x04
I2C_CON_IC_10BITADDR_SLAVE: uint32 = 0x08
I2C_CON_IC_10BITADDR_MASTER: uint32 = 0x10
I2C_CON_IC_RESTART_EN: uint32 = 0x20
I2C_CON_IC_SLAVE_DISABLE: uint32 = 0x40
I2C_CON_STOP_DET_IFADDRESSED: uint32 = 0x80
I2C_CON_TX_EMPTY_CTRL: uint32 = 0x100

# Status register bits
I2C_STATUS_ACTIVITY: uint32 = 0x01
I2C_STATUS_TFNF: uint32 = 0x02   # TX FIFO not full
I2C_STATUS_TFE: uint32 = 0x04    # TX FIFO empty
I2C_STATUS_RFNE: uint32 = 0x08   # RX FIFO not empty
I2C_STATUS_RFF: uint32 = 0x10    # RX FIFO full
I2C_STATUS_MST_ACTIVITY: uint32 = 0x20

# Data command bits
I2C_DATA_CMD_READ: uint32 = 0x100   # Read command
I2C_DATA_CMD_STOP: uint32 = 0x200   # Issue STOP after byte
I2C_DATA_CMD_RESTART: uint32 = 0x400  # Issue RESTART before byte

# ============================================================================
# Constants
# ============================================================================

I2C_SPEED_STANDARD: uint32 = 100000   # 100 kHz
I2C_SPEED_FAST: uint32 = 400000       # 400 kHz

I2C_OK: int32 = 0
I2C_ERR_NACK: int32 = -1
I2C_ERR_TIMEOUT: int32 = -2
I2C_ERR_ABORT: int32 = -3

# System clock for I2C (125 MHz after PLL init)
I2C_CLK_HZ: uint32 = 125000000

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
    """Get base address for I2C instance."""
    if i2c == 0:
        return I2C0_BASE
    return I2C1_BASE

# ============================================================================
# I2C Initialization
# ============================================================================

def i2c_init(i2c: uint32, speed: uint32):
    """Initialize I2C peripheral.

    Args:
        i2c: I2C instance (0 or 1)
        speed: I2C_SPEED_STANDARD (100kHz) or I2C_SPEED_FAST (400kHz)
    """
    base: uint32 = _i2c_base(i2c)

    # Unreset I2C from RESETS register
    reset_bit: uint32 = 23 if i2c == 0 else 24
    reset_val: uint32 = mmio_read(RESETS_BASE)
    mmio_write(RESETS_BASE, reset_val & ~(1 << reset_bit))

    # Wait for reset done
    timeout: int32 = 10000
    while timeout > 0:
        done: uint32 = mmio_read(RESETS_BASE + 0x08)
        if (done & (1 << reset_bit)) != 0:
            break
        timeout = timeout - 1

    # Disable I2C during configuration
    mmio_write(base + I2C_ENABLE, 0)

    # Configure as master, restart enabled, slave disabled
    con: uint32 = I2C_CON_MASTER_MODE | I2C_CON_IC_SLAVE_DISABLE | I2C_CON_IC_RESTART_EN

    # Set speed mode
    if speed >= I2C_SPEED_FAST:
        con = con | I2C_CON_SPEED_FAST
    else:
        con = con | I2C_CON_SPEED_STANDARD

    mmio_write(base + I2C_CON, con)

    # Calculate timing for selected speed
    # Period = CLK_HZ / speed
    # For 100kHz at 125MHz: period = 1250 cycles, half = 625
    # For 400kHz at 125MHz: period = 312 cycles, half = 156
    period: uint32 = I2C_CLK_HZ / speed
    hcnt: uint32 = period / 2
    lcnt: uint32 = period - hcnt

    if speed >= I2C_SPEED_FAST:
        mmio_write(base + I2C_FS_SCL_HCNT, hcnt)
        mmio_write(base + I2C_FS_SCL_LCNT, lcnt)
    else:
        mmio_write(base + I2C_SS_SCL_HCNT, hcnt)
        mmio_write(base + I2C_SS_SCL_LCNT, lcnt)

    # Set spike suppression (for fast mode)
    mmio_write(base + I2C_FS_SPKLEN, 2)

    # Set SDA hold time
    mmio_write(base + I2C_SDA_HOLD, 1)

    # Set FIFO thresholds
    mmio_write(base + I2C_TX_TL, 0)
    mmio_write(base + I2C_RX_TL, 0)

    # Enable I2C
    mmio_write(base + I2C_ENABLE, 1)

def i2c_set_gpio(i2c: uint32, sda_pin: uint32, scl_pin: uint32):
    """Configure GPIO pins for I2C function.

    Args:
        i2c: I2C instance (0 or 1)
        sda_pin: GPIO pin for SDA
        scl_pin: GPIO pin for SCL
    """
    # Function 3 = I2C for most GPIO pins
    func: uint32 = 3

    # Set SDA pin function
    sda_ctrl: uint32 = IO_BANK0_BASE + 4 + (sda_pin * 8)
    mmio_write(sda_ctrl, func)

    # Set SCL pin function
    scl_ctrl: uint32 = IO_BANK0_BASE + 4 + (scl_pin * 8)
    mmio_write(scl_ctrl, func)

# ============================================================================
# I2C Operations
# ============================================================================

def _i2c_wait_idle(base: uint32) -> int32:
    """Wait for I2C bus to be idle."""
    timeout: int32 = 100000
    while timeout > 0:
        status: uint32 = mmio_read(base + I2C_STATUS)
        if (status & I2C_STATUS_ACTIVITY) == 0:
            return I2C_OK
        timeout = timeout - 1
    return I2C_ERR_TIMEOUT

def _i2c_check_abort(base: uint32) -> int32:
    """Check for abort condition and clear it."""
    abort: uint32 = mmio_read(base + I2C_TX_ABRT_SOURCE)
    if abort != 0:
        # Clear abort
        mmio_read(base + I2C_CLR_TX_ABRT)
        return I2C_ERR_NACK
    return I2C_OK

def i2c_write(i2c: uint32, addr: uint32, data: Ptr[uint8], len: int32) -> int32:
    """Write data to I2C slave.

    Args:
        i2c: I2C instance (0 or 1)
        addr: 7-bit slave address
        data: Data buffer
        len: Number of bytes to write

    Returns:
        I2C_OK on success, negative error code on failure
    """
    base: uint32 = _i2c_base(i2c)

    # Set target address
    mmio_write(base + I2C_TAR, addr & 0x7F)

    # Send data
    i: int32 = 0
    while i < len:
        # Wait for TX FIFO space
        timeout: int32 = 10000
        while timeout > 0:
            if (mmio_read(base + I2C_STATUS) & I2C_STATUS_TFNF) != 0:
                break
            timeout = timeout - 1

        if timeout == 0:
            return I2C_ERR_TIMEOUT

        # Write data, add STOP on last byte
        cmd: uint32 = cast[uint32](data[i])
        if i == len - 1:
            cmd = cmd | I2C_DATA_CMD_STOP
        mmio_write(base + I2C_DATA_CMD, cmd)

        i = i + 1

    # Wait for completion
    result: int32 = _i2c_wait_idle(base)
    if result != I2C_OK:
        return result

    return _i2c_check_abort(base)

def i2c_read(i2c: uint32, addr: uint32, data: Ptr[uint8], len: int32) -> int32:
    """Read data from I2C slave.

    Args:
        i2c: I2C instance (0 or 1)
        addr: 7-bit slave address
        data: Buffer to receive data
        len: Number of bytes to read

    Returns:
        I2C_OK on success, negative error code on failure
    """
    base: uint32 = _i2c_base(i2c)

    # Set target address
    mmio_write(base + I2C_TAR, addr & 0x7F)

    # Issue read commands
    i: int32 = 0
    while i < len:
        # Wait for TX FIFO space (for read command)
        timeout: int32 = 10000
        while timeout > 0:
            if (mmio_read(base + I2C_STATUS) & I2C_STATUS_TFNF) != 0:
                break
            timeout = timeout - 1

        if timeout == 0:
            return I2C_ERR_TIMEOUT

        # Issue read command, add STOP on last byte
        cmd: uint32 = I2C_DATA_CMD_READ
        if i == len - 1:
            cmd = cmd | I2C_DATA_CMD_STOP
        mmio_write(base + I2C_DATA_CMD, cmd)

        i = i + 1

    # Read received data
    i = 0
    while i < len:
        timeout: int32 = 10000
        while timeout > 0:
            if (mmio_read(base + I2C_STATUS) & I2C_STATUS_RFNE) != 0:
                break
            timeout = timeout - 1

        if timeout == 0:
            return I2C_ERR_TIMEOUT

        data[i] = cast[uint8](mmio_read(base + I2C_DATA_CMD) & 0xFF)
        i = i + 1

    return _i2c_check_abort(base)

def i2c_write_read(i2c: uint32, addr: uint32, wr_data: Ptr[uint8], wr_len: int32,
                   rd_data: Ptr[uint8], rd_len: int32) -> int32:
    """Write then read (repeated start) on I2C bus.

    Args:
        i2c: I2C instance (0 or 1)
        addr: 7-bit slave address
        wr_data: Data to write
        wr_len: Number of bytes to write
        rd_data: Buffer for read data
        rd_len: Number of bytes to read

    Returns:
        I2C_OK on success, negative error code on failure
    """
    base: uint32 = _i2c_base(i2c)

    # Set target address
    mmio_write(base + I2C_TAR, addr & 0x7F)

    # Send write data (no STOP)
    i: int32 = 0
    while i < wr_len:
        timeout: int32 = 10000
        while timeout > 0:
            if (mmio_read(base + I2C_STATUS) & I2C_STATUS_TFNF) != 0:
                break
            timeout = timeout - 1

        if timeout == 0:
            return I2C_ERR_TIMEOUT

        mmio_write(base + I2C_DATA_CMD, cast[uint32](wr_data[i]))
        i = i + 1

    # Issue read commands with RESTART on first
    i = 0
    while i < rd_len:
        timeout: int32 = 10000
        while timeout > 0:
            if (mmio_read(base + I2C_STATUS) & I2C_STATUS_TFNF) != 0:
                break
            timeout = timeout - 1

        if timeout == 0:
            return I2C_ERR_TIMEOUT

        cmd: uint32 = I2C_DATA_CMD_READ
        if i == 0:
            cmd = cmd | I2C_DATA_CMD_RESTART
        if i == rd_len - 1:
            cmd = cmd | I2C_DATA_CMD_STOP
        mmio_write(base + I2C_DATA_CMD, cmd)

        i = i + 1

    # Read received data
    i = 0
    while i < rd_len:
        timeout: int32 = 10000
        while timeout > 0:
            if (mmio_read(base + I2C_STATUS) & I2C_STATUS_RFNE) != 0:
                break
            timeout = timeout - 1

        if timeout == 0:
            return I2C_ERR_TIMEOUT

        rd_data[i] = cast[uint8](mmio_read(base + I2C_DATA_CMD) & 0xFF)
        i = i + 1

    return _i2c_check_abort(base)

def i2c_write_reg(i2c: uint32, addr: uint32, reg: uint32, value: uint32) -> int32:
    """Write single byte to register.

    Args:
        i2c: I2C instance
        addr: 7-bit slave address
        reg: Register address
        value: Value to write

    Returns:
        I2C_OK on success
    """
    buf: Array[2, uint8]
    buf[0] = cast[uint8](reg & 0xFF)
    buf[1] = cast[uint8](value & 0xFF)
    return i2c_write(i2c, addr, &buf[0], 2)

def i2c_read_reg(i2c: uint32, addr: uint32, reg: uint32) -> int32:
    """Read single byte from register.

    Args:
        i2c: I2C instance
        addr: 7-bit slave address
        reg: Register address

    Returns:
        Register value (0-255) or negative error code
    """
    reg_byte: uint8 = cast[uint8](reg & 0xFF)
    value: uint8 = 0
    result: int32 = i2c_write_read(i2c, addr, &reg_byte, 1, &value, 1)
    if result != I2C_OK:
        return result
    return cast[int32](value)
