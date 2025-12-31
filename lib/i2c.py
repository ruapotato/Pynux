# Pynux I2C/TWI Bus Library
#
# I2C (Inter-Integrated Circuit) / TWI (Two-Wire Interface) driver
# for bare-metal ARM Cortex-M3. Provides both hardware access via
# devfs and register simulation for testing without hardware.
#
# Supports:
#   - Standard mode (100 kHz)
#   - Fast mode (400 kHz)
#   - 7-bit addressing
#   - Multi-bus support (up to 4 I2C buses)
#   - Register read/write operations
#   - Bus scanning

from lib.memory import memset, memcpy
from lib.io import print_str, print_hex, print_newline

# ============================================================================
# Constants
# ============================================================================

# I2C speeds
I2C_SPEED_100K: uint32 = 100000    # Standard mode
I2C_SPEED_400K: uint32 = 400000    # Fast mode

# Maximum buses supported
MAX_I2C_BUSES: int32 = 4

# I2C address range
I2C_ADDR_MIN: uint32 = 0x08        # First valid address
I2C_ADDR_MAX: uint32 = 0x77        # Last valid address

# Return codes
I2CBUS_OK: int32 = 0
I2CBUS_ERR_NACK: int32 = -1
I2CBUS_ERR_TIMEOUT: int32 = -2
I2CBUS_ERR_BUS: int32 = -3
I2CBUS_ERR_ARB_LOST: int32 = -4
I2CBUS_ERR_INVALID: int32 = -5
I2CBUS_ERR_NOT_INIT: int32 = -6

# Timeout for bus operations (iterations)
I2C_TIMEOUT: int32 = 10000

# Devfs paths for I2C buses
# Format: /dev/i2c-N where N is bus number
DEVFS_I2C_BASE: Ptr[char] = "/dev/i2c-"

# ============================================================================
# Hardware Register Definitions
# ============================================================================

# Base address for I2C peripheral (memory-mapped)
I2C_BASE_ADDR: uint32 = 0x40030000

# Register offsets
I2CBUS_CTRL_REG: uint32 = 0x00       # Control register
I2CBUS_STATUS_REG: uint32 = 0x04     # Status register
I2CBUS_DATA_REG: uint32 = 0x08       # Data register
I2CBUS_ADDR_REG: uint32 = 0x0C       # Address register
I2CBUS_BAUD_REG: uint32 = 0x10       # Baud rate divisor
I2CBUS_CMD_REG: uint32 = 0x14        # Command register

# Instance stride (each I2C instance has 0x100 bytes)
I2CBUS_STRIDE: uint32 = 0x100

# Control register bits
I2CBUS_CTRL_ENABLE: uint32 = 0x01
I2CBUS_CTRL_MASTER: uint32 = 0x02
I2CBUS_CTRL_INT_EN: uint32 = 0x04

# Status register bits
I2CBUS_STATUS_BUSY: uint32 = 0x01
I2CBUS_STATUS_ACK: uint32 = 0x02
I2CBUS_STATUS_NACK: uint32 = 0x04
I2CBUS_STATUS_ARB_LOST: uint32 = 0x08
I2CBUS_STATUS_TX_EMPTY: uint32 = 0x10
I2CBUS_STATUS_RX_FULL: uint32 = 0x20

# Command register values
I2CBUS_CMD_START: uint32 = 0x01
I2CBUS_CMD_STOP: uint32 = 0x02
I2CBUS_CMD_READ: uint32 = 0x04
I2CBUS_CMD_WRITE: uint32 = 0x08
I2CBUS_CMD_ACK: uint32 = 0x10
I2CBUS_CMD_NACK: uint32 = 0x20

# ============================================================================
# Simulation State
# ============================================================================
#
# For testing without hardware, we simulate I2C devices with internal
# register maps. Each simulated device has:
#   - 7-bit address
#   - 256-byte register space
#
# Maximum simulated devices per bus
I2C_MAX_SIM_DEVICES: int32 = 8

# Simulated device structure (per device):
#   address: uint8 (offset 0)
#   enabled: uint8 (offset 1)
#   registers: Array[256, uint8] (offset 2)
# Total: 258 bytes per device

I2C_SIM_DEV_SIZE: int32 = 258
I2C_SIM_DEV_ADDR_OFFSET: int32 = 0
I2C_SIM_DEV_ENABLED_OFFSET: int32 = 1
I2C_SIM_DEV_REG_OFFSET: int32 = 2

# Simulated bus state
# Each bus: 8 devices * 258 bytes = 2064 bytes
# 4 buses total = 8256 bytes
_i2c_sim_devices: Array[8256, uint8]
_i2c_sim_device_count: Array[4, int32]

# Bus initialization state
_i2c_bus_initialized: Array[4, bool]
_i2c_bus_speed: Array[4, uint32]
_i2c_sim_mode_enabled: bool = True    # Default to simulation mode

# Current transaction state per bus
_i2c_bus_in_transaction: Array[4, bool]
_i2c_bus_current_addr: Array[4, uint8]
_i2c_bus_current_reg: Array[4, uint8]
_i2c_bus_reg_selected: Array[4, bool]

# ============================================================================
# Internal Helpers
# ============================================================================

def _i2c_get_base(bus_id: int32) -> uint32:
    """Get hardware base address for I2C bus."""
    return I2C_BASE_ADDR + (cast[uint32](bus_id) * I2CBUS_STRIDE)

def _i2c_get_sim_device(bus_id: int32, dev_idx: int32) -> Ptr[uint8]:
    """Get pointer to simulated device data."""
    bus_offset: int32 = bus_id * (I2C_MAX_SIM_DEVICES * I2C_SIM_DEV_SIZE)
    dev_offset: int32 = dev_idx * I2C_SIM_DEV_SIZE
    return &_i2c_sim_devices[bus_offset + dev_offset]

def _i2c_find_sim_device(bus_id: int32, addr: uint8) -> Ptr[uint8]:
    """Find simulated device by address. Returns NULL if not found."""
    i: int32 = 0
    while i < I2C_MAX_SIM_DEVICES:
        dev: Ptr[uint8] = _i2c_get_sim_device(bus_id, i)
        if dev[I2C_SIM_DEV_ENABLED_OFFSET] != 0:
            if dev[I2C_SIM_DEV_ADDR_OFFSET] == addr:
                return dev
        i = i + 1
    return cast[Ptr[uint8]](0)

def _i2c_mmio_read(addr: uint32) -> uint32:
    """Read from memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def _i2c_mmio_write(addr: uint32, val: uint32):
    """Write to memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _i2c_delay():
    """Small delay for timing."""
    i: int32 = 0
    while i < 10:
        i = i + 1

# ============================================================================
# Initialization
# ============================================================================

def i2cbus_init(bus_id: int32, speed: uint32) -> int32:
    """Initialize I2C bus with specified speed.

    Args:
        bus_id: I2C bus number (0-3)
        speed: Bus speed in Hz (I2C_SPEED_100K or I2C_SPEED_400K)

    Returns:
        I2CBUS_OK on success, error code on failure
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return I2CBUS_ERR_INVALID

    # Clear simulated devices for this bus
    bus_offset: int32 = bus_id * (I2C_MAX_SIM_DEVICES * I2C_SIM_DEV_SIZE)
    memset(&_i2c_sim_devices[bus_offset], 0, I2C_MAX_SIM_DEVICES * I2C_SIM_DEV_SIZE)
    _i2c_sim_device_count[bus_id] = 0

    # Reset transaction state
    _i2c_bus_in_transaction[bus_id] = False
    _i2c_bus_current_addr[bus_id] = 0
    _i2c_bus_current_reg[bus_id] = 0
    _i2c_bus_reg_selected[bus_id] = False

    # Store speed
    _i2c_bus_speed[bus_id] = speed

    if not _i2c_sim_mode_enabled:
        # Hardware initialization
        base: uint32 = _i2c_get_base(bus_id)

        # Disable first
        _i2c_mmio_write(base + I2CBUS_CTRL_REG, 0)

        # Calculate baud divisor
        # For 25MHz system clock:
        #   100kHz: divisor = 25000000 / (4 * 100000) = 62
        #   400kHz: divisor = 25000000 / (4 * 400000) = 15
        baud_div: uint32 = 62
        if speed == I2C_SPEED_400K:
            baud_div = 15

        _i2c_mmio_write(base + I2CBUS_BAUD_REG, baud_div)

        # Enable as master
        _i2c_mmio_write(base + I2CBUS_CTRL_REG, I2CBUS_CTRL_ENABLE | I2CBUS_CTRL_MASTER)

    _i2c_bus_initialized[bus_id] = True
    return I2CBUS_OK

def i2cbus_deinit(bus_id: int32):
    """Deinitialize I2C bus.

    Args:
        bus_id: I2C bus number (0-3)
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return

    if not _i2c_sim_mode_enabled:
        base: uint32 = _i2c_get_base(bus_id)
        _i2c_mmio_write(base + I2CBUS_CTRL_REG, 0)

    _i2c_bus_initialized[bus_id] = False

def i2cbus_set_simulation_mode(enabled: bool):
    """Enable or disable simulation mode.

    Args:
        enabled: True for simulation, False for hardware access
    """
    global _i2c_sim_mode_enabled
    _i2c_sim_mode_enabled = enabled

def i2cbus_is_initialized(bus_id: int32) -> bool:
    """Check if I2C bus is initialized.

    Args:
        bus_id: I2C bus number

    Returns:
        True if initialized
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return False
    return _i2c_bus_initialized[bus_id]

# ============================================================================
# Low-Level Bus Operations
# ============================================================================

def i2cbus_start(bus_id: int32) -> bool:
    """Send I2C start condition.

    Args:
        bus_id: I2C bus number

    Returns:
        True on success
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return False
    if not _i2c_bus_initialized[bus_id]:
        return False

    if _i2c_sim_mode_enabled:
        # In simulation, just mark transaction started
        _i2c_bus_in_transaction[bus_id] = True
        _i2c_bus_reg_selected[bus_id] = False
        return True
    else:
        # Hardware: send start condition
        base: uint32 = _i2c_get_base(bus_id)
        _i2c_mmio_write(base + I2CBUS_CMD_REG, I2CBUS_CMD_START)

        # Wait for bus ready
        timeout: int32 = I2C_TIMEOUT
        while timeout > 0:
            status: uint32 = _i2c_mmio_read(base + I2CBUS_STATUS_REG)
            if (status & I2CBUS_STATUS_BUSY) == 0:
                return True
            timeout = timeout - 1

        return False

def i2cbus_stop(bus_id: int32):
    """Send I2C stop condition.

    Args:
        bus_id: I2C bus number
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return
    if not _i2c_bus_initialized[bus_id]:
        return

    if _i2c_sim_mode_enabled:
        # In simulation, mark transaction ended
        _i2c_bus_in_transaction[bus_id] = False
        _i2c_bus_reg_selected[bus_id] = False
    else:
        # Hardware: send stop condition
        base: uint32 = _i2c_get_base(bus_id)
        _i2c_mmio_write(base + I2CBUS_CMD_REG, I2CBUS_CMD_STOP)
        _i2c_delay()

def i2cbus_write_byte(bus_id: int32, byte: uint8) -> bool:
    """Write a single byte to I2C bus.

    Args:
        bus_id: I2C bus number
        byte: Byte to write

    Returns:
        True if ACK received, False if NACK
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return False
    if not _i2c_bus_initialized[bus_id]:
        return False

    if _i2c_sim_mode_enabled:
        if not _i2c_bus_in_transaction[bus_id]:
            return False

        # Check if this is address byte (R/W bit in LSB)
        if not _i2c_bus_reg_selected[bus_id]:
            # First byte after start could be address or register
            addr: uint8 = byte >> 1
            rw: uint8 = byte & 0x01

            # Check if device exists
            dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
            if cast[uint32](dev) == 0:
                return False  # NACK - no device

            _i2c_bus_current_addr[bus_id] = addr
            return True  # ACK
        else:
            # Writing to register
            dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, _i2c_bus_current_addr[bus_id])
            if cast[uint32](dev) == 0:
                return False

            reg_ptr: Ptr[uint8] = &dev[I2C_SIM_DEV_REG_OFFSET]
            reg_ptr[_i2c_bus_current_reg[bus_id]] = byte
            _i2c_bus_current_reg[bus_id] = _i2c_bus_current_reg[bus_id] + 1
            return True  # ACK
    else:
        # Hardware write
        base: uint32 = _i2c_get_base(bus_id)

        # Write data
        _i2c_mmio_write(base + I2CBUS_DATA_REG, cast[uint32](byte))
        _i2c_mmio_write(base + I2CBUS_CMD_REG, I2CBUS_CMD_WRITE)

        # Wait for completion
        timeout: int32 = I2C_TIMEOUT
        while timeout > 0:
            status: uint32 = _i2c_mmio_read(base + I2CBUS_STATUS_REG)
            if (status & I2CBUS_STATUS_BUSY) == 0:
                # Check for ACK/NACK
                if (status & I2CBUS_STATUS_NACK) != 0:
                    return False
                return True
            timeout = timeout - 1

        return False

def i2cbus_read_byte(bus_id: int32, ack: bool) -> uint8:
    """Read a single byte from I2C bus.

    Args:
        bus_id: I2C bus number
        ack: True to send ACK, False to send NACK

    Returns:
        Byte read from bus
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return 0xFF
    if not _i2c_bus_initialized[bus_id]:
        return 0xFF

    if _i2c_sim_mode_enabled:
        if not _i2c_bus_in_transaction[bus_id]:
            return 0xFF

        dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, _i2c_bus_current_addr[bus_id])
        if cast[uint32](dev) == 0:
            return 0xFF

        reg_ptr: Ptr[uint8] = &dev[I2C_SIM_DEV_REG_OFFSET]
        value: uint8 = reg_ptr[_i2c_bus_current_reg[bus_id]]
        _i2c_bus_current_reg[bus_id] = _i2c_bus_current_reg[bus_id] + 1
        return value
    else:
        # Hardware read
        base: uint32 = _i2c_get_base(bus_id)

        # Issue read command with ACK or NACK
        cmd: uint32 = I2CBUS_CMD_READ
        if ack:
            cmd = cmd | I2CBUS_CMD_ACK
        else:
            cmd = cmd | I2CBUS_CMD_NACK

        _i2c_mmio_write(base + I2CBUS_CMD_REG, cmd)

        # Wait for completion
        timeout: int32 = I2C_TIMEOUT
        while timeout > 0:
            status: uint32 = _i2c_mmio_read(base + I2CBUS_STATUS_REG)
            if (status & I2CBUS_STATUS_BUSY) == 0:
                break
            timeout = timeout - 1

        # Read received byte
        return cast[uint8](_i2c_mmio_read(base + I2CBUS_DATA_REG) & 0xFF)

# ============================================================================
# High-Level Transfer Operations
# ============================================================================

def i2cbus_write(bus_id: int32, addr: uint8, data: Ptr[uint8], length: int32) -> int32:
    """Write data to I2C device.

    Args:
        bus_id: I2C bus number
        addr: 7-bit device address
        data: Pointer to data buffer
        length: Number of bytes to write

    Returns:
        Number of bytes written on success, negative error code on failure
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return I2CBUS_ERR_INVALID
    if not _i2c_bus_initialized[bus_id]:
        return I2CBUS_ERR_NOT_INIT
    if length <= 0:
        return I2CBUS_ERR_INVALID

    if _i2c_sim_mode_enabled:
        # Find device
        dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
        if cast[uint32](dev) == 0:
            return I2CBUS_ERR_NACK

        # First byte is register address
        reg: uint8 = data[0]
        reg_ptr: Ptr[uint8] = &dev[I2C_SIM_DEV_REG_OFFSET]

        # Write remaining bytes to consecutive registers
        i: int32 = 1
        while i < length:
            reg_ptr[reg] = data[i]
            reg = reg + 1
            i = i + 1

        return length
    else:
        # Hardware write
        if not i2cbus_start(bus_id):
            return I2CBUS_ERR_BUS

        # Send address with write bit
        addr_byte: uint8 = (addr << 1) & 0xFE
        if not i2cbus_write_byte(bus_id, addr_byte):
            i2cbus_stop(bus_id)
            return I2CBUS_ERR_NACK

        # Send data
        i: int32 = 0
        while i < length:
            if not i2cbus_write_byte(bus_id, data[i]):
                i2cbus_stop(bus_id)
                return i  # Return bytes written
            i = i + 1

        i2cbus_stop(bus_id)
        return length

def i2cbus_read(bus_id: int32, addr: uint8, buf: Ptr[uint8], length: int32) -> int32:
    """Read data from I2C device.

    Args:
        bus_id: I2C bus number
        addr: 7-bit device address
        buf: Pointer to receive buffer
        length: Number of bytes to read

    Returns:
        Number of bytes read on success, negative error code on failure
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return I2CBUS_ERR_INVALID
    if not _i2c_bus_initialized[bus_id]:
        return I2CBUS_ERR_NOT_INIT
    if length <= 0:
        return I2CBUS_ERR_INVALID

    if _i2c_sim_mode_enabled:
        # Find device
        dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
        if cast[uint32](dev) == 0:
            return I2CBUS_ERR_NACK

        # Read from current register pointer (default 0)
        reg: uint8 = _i2c_bus_current_reg[bus_id]
        reg_ptr: Ptr[uint8] = &dev[I2C_SIM_DEV_REG_OFFSET]

        i: int32 = 0
        while i < length:
            buf[i] = reg_ptr[reg]
            reg = reg + 1
            i = i + 1

        return length
    else:
        # Hardware read
        if not i2cbus_start(bus_id):
            return I2CBUS_ERR_BUS

        # Send address with read bit
        addr_byte: uint8 = ((addr << 1) & 0xFE) | 0x01
        if not i2cbus_write_byte(bus_id, addr_byte):
            i2cbus_stop(bus_id)
            return I2CBUS_ERR_NACK

        # Read data (ACK all except last byte)
        i: int32 = 0
        while i < length:
            ack: bool = (i < length - 1)
            buf[i] = i2cbus_read_byte(bus_id, ack)
            i = i + 1

        i2cbus_stop(bus_id)
        return length

# ============================================================================
# Register Operations
# ============================================================================

def i2cbus_write_reg(bus_id: int32, addr: uint8, reg: uint8, value: uint8) -> bool:
    """Write a single byte to a device register.

    Args:
        bus_id: I2C bus number
        addr: 7-bit device address
        reg: Register address
        value: Value to write

    Returns:
        True on success
    """
    buf: Array[2, uint8]
    buf[0] = reg
    buf[1] = value

    result: int32 = i2cbus_write(bus_id, addr, &buf[0], 2)
    return result == 2

def i2cbus_read_reg(bus_id: int32, addr: uint8, reg: uint8) -> int32:
    """Read a single byte from a device register.

    Args:
        bus_id: I2C bus number
        addr: 7-bit device address
        reg: Register address

    Returns:
        Register value (0-255) on success, negative error code on failure
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return I2CBUS_ERR_INVALID
    if not _i2c_bus_initialized[bus_id]:
        return I2CBUS_ERR_NOT_INIT

    if _i2c_sim_mode_enabled:
        # Find device
        dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
        if cast[uint32](dev) == 0:
            return I2CBUS_ERR_NACK

        reg_ptr: Ptr[uint8] = &dev[I2C_SIM_DEV_REG_OFFSET]
        return cast[int32](reg_ptr[reg])
    else:
        # Hardware: write register address, then read
        if not i2cbus_start(bus_id):
            return I2CBUS_ERR_BUS

        # Write address + register
        addr_byte: uint8 = (addr << 1) & 0xFE
        if not i2cbus_write_byte(bus_id, addr_byte):
            i2cbus_stop(bus_id)
            return I2CBUS_ERR_NACK

        if not i2cbus_write_byte(bus_id, reg):
            i2cbus_stop(bus_id)
            return I2CBUS_ERR_NACK

        # Repeated start
        if not i2cbus_start(bus_id):
            i2cbus_stop(bus_id)
            return I2CBUS_ERR_BUS

        # Read address
        addr_byte = ((addr << 1) & 0xFE) | 0x01
        if not i2cbus_write_byte(bus_id, addr_byte):
            i2cbus_stop(bus_id)
            return I2CBUS_ERR_NACK

        # Read one byte with NACK
        value: uint8 = i2cbus_read_byte(bus_id, False)

        i2cbus_stop(bus_id)
        return cast[int32](value)

def i2cbus_write_reg16(bus_id: int32, addr: uint8, reg: uint8, value: uint16) -> bool:
    """Write 16-bit value to device register (big-endian).

    Args:
        bus_id: I2C bus number
        addr: 7-bit device address
        reg: Register address
        value: 16-bit value to write

    Returns:
        True on success
    """
    buf: Array[3, uint8]
    buf[0] = reg
    buf[1] = cast[uint8]((value >> 8) & 0xFF)  # MSB first
    buf[2] = cast[uint8](value & 0xFF)         # LSB

    result: int32 = i2cbus_write(bus_id, addr, &buf[0], 3)
    return result == 3

def i2cbus_read_reg16(bus_id: int32, addr: uint8, reg: uint8) -> int32:
    """Read 16-bit value from device register (big-endian).

    Args:
        bus_id: I2C bus number
        addr: 7-bit device address
        reg: Register address

    Returns:
        16-bit value on success, negative error code on failure
    """
    # Write register address
    reg_buf: Array[1, uint8]
    reg_buf[0] = reg
    result: int32 = i2cbus_write(bus_id, addr, &reg_buf[0], 1)
    if result < 0:
        return result

    # Read 2 bytes
    buf: Array[2, uint8]
    result = i2cbus_read(bus_id, addr, &buf[0], 2)
    if result != 2:
        return I2CBUS_ERR_NACK

    # Combine MSB:LSB
    value: int32 = (cast[int32](buf[0]) << 8) | cast[int32](buf[1])
    return value

# ============================================================================
# Bus Scanning
# ============================================================================

def i2cbus_scan(bus_id: int32):
    """Scan I2C bus for devices and print found addresses.

    Args:
        bus_id: I2C bus number
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        print_str("Invalid bus ID")
        print_newline()
        return

    if not _i2c_bus_initialized[bus_id]:
        print_str("Bus not initialized")
        print_newline()
        return

    print_str("Scanning I2C bus ")
    print_hex(cast[uint32](bus_id))
    print_str("...")
    print_newline()

    found: int32 = 0
    addr: uint32 = I2C_ADDR_MIN

    while addr <= I2C_ADDR_MAX:
        present: bool = False

        if _i2c_sim_mode_enabled:
            dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, cast[uint8](addr))
            present = cast[uint32](dev) != 0
        else:
            # Try to start transaction with device
            if i2cbus_start(bus_id):
                addr_byte: uint8 = (cast[uint8](addr) << 1) & 0xFE
                present = i2cbus_write_byte(bus_id, addr_byte)
                i2cbus_stop(bus_id)

        if present:
            print_str("  Found device at 0x")
            print_hex(addr)
            print_newline()
            found = found + 1

        addr = addr + 1

    print_str("Scan complete: ")
    print_hex(cast[uint32](found))
    print_str(" device(s) found")
    print_newline()

def i2cbus_probe(bus_id: int32, addr: uint8) -> bool:
    """Check if device exists at address.

    Args:
        bus_id: I2C bus number
        addr: 7-bit device address

    Returns:
        True if device responds
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return False
    if not _i2c_bus_initialized[bus_id]:
        return False

    if _i2c_sim_mode_enabled:
        dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
        return cast[uint32](dev) != 0
    else:
        if i2cbus_start(bus_id):
            addr_byte: uint8 = (addr << 1) & 0xFE
            result: bool = i2cbus_write_byte(bus_id, addr_byte)
            i2cbus_stop(bus_id)
            return result
        return False

# ============================================================================
# Simulation Device Management
# ============================================================================

def i2c_sim_add_device(bus_id: int32, addr: uint8) -> int32:
    """Add a simulated device to the bus.

    Args:
        bus_id: I2C bus number
        addr: 7-bit device address

    Returns:
        Device index on success, -1 if full or invalid
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return -1

    if _i2c_sim_device_count[bus_id] >= I2C_MAX_SIM_DEVICES:
        return -1

    # Check for duplicate address
    if cast[uint32](_i2c_find_sim_device(bus_id, addr)) != 0:
        return -1

    # Find free slot
    i: int32 = 0
    while i < I2C_MAX_SIM_DEVICES:
        dev: Ptr[uint8] = _i2c_get_sim_device(bus_id, i)
        if dev[I2C_SIM_DEV_ENABLED_OFFSET] == 0:
            dev[I2C_SIM_DEV_ADDR_OFFSET] = addr
            dev[I2C_SIM_DEV_ENABLED_OFFSET] = 1
            memset(&dev[I2C_SIM_DEV_REG_OFFSET], 0, 256)
            _i2c_sim_device_count[bus_id] = _i2c_sim_device_count[bus_id] + 1
            return i
        i = i + 1

    return -1

def i2c_sim_remove_device(bus_id: int32, addr: uint8) -> bool:
    """Remove a simulated device from the bus.

    Args:
        bus_id: I2C bus number
        addr: Device address to remove

    Returns:
        True if device was removed
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return False

    dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
    if cast[uint32](dev) == 0:
        return False

    dev[I2C_SIM_DEV_ENABLED_OFFSET] = 0
    _i2c_sim_device_count[bus_id] = _i2c_sim_device_count[bus_id] - 1
    return True

def i2c_sim_set_reg(bus_id: int32, addr: uint8, reg: uint8, value: uint8) -> bool:
    """Set a register value in simulated device.

    Args:
        bus_id: I2C bus number
        addr: Device address
        reg: Register address
        value: Value to set

    Returns:
        True on success
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return False

    dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
    if cast[uint32](dev) == 0:
        return False

    reg_ptr: Ptr[uint8] = &dev[I2C_SIM_DEV_REG_OFFSET]
    reg_ptr[reg] = value
    return True

def i2c_sim_get_reg(bus_id: int32, addr: uint8, reg: uint8) -> int32:
    """Get a register value from simulated device.

    Args:
        bus_id: I2C bus number
        addr: Device address
        reg: Register address

    Returns:
        Register value (0-255) or -1 if not found
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return -1

    dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
    if cast[uint32](dev) == 0:
        return -1

    reg_ptr: Ptr[uint8] = &dev[I2C_SIM_DEV_REG_OFFSET]
    return cast[int32](reg_ptr[reg])

def i2c_sim_set_regs(bus_id: int32, addr: uint8, start_reg: uint8,
                     data: Ptr[uint8], length: int32) -> bool:
    """Set multiple register values in simulated device.

    Args:
        bus_id: I2C bus number
        addr: Device address
        start_reg: Starting register address
        data: Data to write
        length: Number of bytes

    Returns:
        True on success
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return False

    dev: Ptr[uint8] = _i2c_find_sim_device(bus_id, addr)
    if cast[uint32](dev) == 0:
        return False

    reg_ptr: Ptr[uint8] = &dev[I2C_SIM_DEV_REG_OFFSET]

    i: int32 = 0
    reg: uint8 = start_reg
    while i < length and reg < 256:
        reg_ptr[reg] = data[i]
        reg = reg + 1
        i = i + 1

    return True

def i2c_sim_clear_all(bus_id: int32):
    """Remove all simulated devices from bus.

    Args:
        bus_id: I2C bus number
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return

    bus_offset: int32 = bus_id * (I2C_MAX_SIM_DEVICES * I2C_SIM_DEV_SIZE)
    memset(&_i2c_sim_devices[bus_offset], 0, I2C_MAX_SIM_DEVICES * I2C_SIM_DEV_SIZE)
    _i2c_sim_device_count[bus_id] = 0

def i2c_sim_get_device_count(bus_id: int32) -> int32:
    """Get number of simulated devices on bus.

    Args:
        bus_id: I2C bus number

    Returns:
        Device count
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return 0
    return _i2c_sim_device_count[bus_id]

# ============================================================================
# Status and Information
# ============================================================================

def i2cbus_get_speed(bus_id: int32) -> uint32:
    """Get configured bus speed.

    Args:
        bus_id: I2C bus number

    Returns:
        Speed in Hz
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return 0
    return _i2c_bus_speed[bus_id]

def i2cbus_is_busy(bus_id: int32) -> bool:
    """Check if bus is busy.

    Args:
        bus_id: I2C bus number

    Returns:
        True if bus is busy
    """
    if bus_id < 0 or bus_id >= MAX_I2C_BUSES:
        return False
    if not _i2c_bus_initialized[bus_id]:
        return False

    if _i2c_sim_mode_enabled:
        return _i2c_bus_in_transaction[bus_id]
    else:
        base: uint32 = _i2c_get_base(bus_id)
        status: uint32 = _i2c_mmio_read(base + I2CBUS_STATUS_REG)
        return (status & I2CBUS_STATUS_BUSY) != 0
