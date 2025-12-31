# Pynux SPI Bus Library
#
# SPI (Serial Peripheral Interface) driver for bare-metal ARM Cortex-M3.
# Provides both hardware access via devfs and register simulation for
# testing without hardware.
#
# Supports:
#   - SPI modes 0-3 (CPOL/CPHA combinations)
#   - Multiple buses (up to 4 SPI buses)
#   - Full-duplex, write-only, and read-only transfers
#   - Multiple chip selects per bus
#   - Configurable clock speed

from lib.memory import memset, memcpy

# ============================================================================
# Constants
# ============================================================================

# SPI modes (CPOL | CPHA)
SPIBUS_MODE_0: uint32 = 0    # CPOL=0, CPHA=0 - Clock idle low, sample on rising edge
SPIBUS_MODE_1: uint32 = 1    # CPOL=0, CPHA=1 - Clock idle low, sample on falling edge
SPIBUS_MODE_2: uint32 = 2    # CPOL=1, CPHA=0 - Clock idle high, sample on falling edge
SPIBUS_MODE_3: uint32 = 3    # CPOL=1, CPHA=1 - Clock idle high, sample on rising edge

# Maximum buses and chip selects supported
MAX_SPI_BUSES: int32 = 4
MAX_CHIP_SELECTS: int32 = 8

# Default clock speeds
SPI_SPEED_1M: uint32 = 1000000
SPI_SPEED_2M: uint32 = 2000000
SPI_SPEED_4M: uint32 = 4000000
SPI_SPEED_8M: uint32 = 8000000
SPI_SPEED_10M: uint32 = 10000000

# System clock (assumed 25MHz for MPS2-AN385)
SPI_SYSCLK: uint32 = 25000000

# Return codes
SPIBUS_OK: int32 = 0
SPIBUS_ERR_TIMEOUT: int32 = -1
SPIBUS_ERR_INVALID: int32 = -2
SPIBUS_ERR_NOT_INIT: int32 = -3
SPIBUS_ERR_BUSY: int32 = -4

# Timeout for bus operations
SPI_TIMEOUT: int32 = 10000

# Devfs paths for SPI buses
# Format: /dev/spi-N where N is bus number
DEVFS_SPI_BASE: Ptr[char] = "/dev/spi-"

# ============================================================================
# Hardware Register Definitions
# ============================================================================

# Base address for SPI peripheral
SPI_BASE_ADDR: uint32 = 0x40020000

# Register offsets
SPI_CTRL_REG: uint32 = 0x00       # Control register
SPI_STATUS_REG: uint32 = 0x04     # Status register
SPI_DATA_REG: uint32 = 0x08       # Data register (TX/RX)
SPI_BAUD_REG: uint32 = 0x0C       # Baud rate divisor
SPI_CS_REG: uint32 = 0x10         # Chip select control

# Instance stride (each SPI instance has 0x100 bytes)
SPIBUS_STRIDE: uint32 = 0x100

# Control register bits
SPIBUS_CTRL_ENABLE: uint32 = 0x01
SPIBUS_CTRL_MASTER: uint32 = 0x02
SPIBUS_CTRL_CPOL: uint32 = 0x04      # Clock polarity
SPIBUS_CTRL_CPHA: uint32 = 0x08      # Clock phase
SPIBUS_CTRL_LSBFIRST: uint32 = 0x10  # LSB first (default MSB)
SPIBUS_CTRL_LOOP: uint32 = 0x20      # Loopback mode

# Status register bits
SPIBUS_STATUS_TX_EMPTY: uint32 = 0x01
SPIBUS_STATUS_TX_FULL: uint32 = 0x02
SPIBUS_STATUS_RX_EMPTY: uint32 = 0x04
SPIBUS_STATUS_RX_FULL: uint32 = 0x08
SPIBUS_STATUS_BUSY: uint32 = 0x10

# ============================================================================
# Simulation State
# ============================================================================
#
# For testing without hardware, we simulate SPI devices with internal
# register maps. Each simulated device has:
#   - Chip select number
#   - 256-byte register space
#   - Optional callback-like behavior via register reads/writes
#
# Maximum simulated devices per bus
SPI_MAX_SIM_DEVICES: int32 = 8

# Simulated device structure:
#   cs: uint8 (offset 0)
#   enabled: uint8 (offset 1)
#   reg_ptr: uint8 (offset 2) - current register pointer
#   mode: uint8 (offset 3) - read/write mode tracking
#   registers: Array[256, uint8] (offset 4)
# Total: 260 bytes per device

SPI_SIM_DEV_SIZE: int32 = 260
SPI_SIM_DEV_CS_OFFSET: int32 = 0
SPI_SIM_DEV_ENABLED_OFFSET: int32 = 1
SPI_SIM_DEV_REGPTR_OFFSET: int32 = 2
SPI_SIM_DEV_MODE_OFFSET: int32 = 3
SPI_SIM_DEV_REG_OFFSET: int32 = 4

# Mode values for simulated device
SPI_SIM_MODE_IDLE: uint8 = 0
SPI_SIM_MODE_CMD: uint8 = 1      # Waiting for command/address
SPI_SIM_MODE_READ: uint8 = 2     # Reading data
SPI_SIM_MODE_WRITE: uint8 = 3    # Writing data

# Simulated bus state
# Each bus: 8 devices * 260 bytes = 2080 bytes
# 4 buses total = 8320 bytes
_spi_sim_devices: Array[8320, uint8]
_spi_sim_device_count: Array[4, int32]

# Bus initialization state
_spi_bus_initialized: Array[4, bool]
_spi_bus_mode: Array[4, uint32]
_spi_bus_speed: Array[4, uint32]
_spi_bus_cs_active: Array[4, int32]       # Currently selected CS (-1 = none)
_spi_sim_mode_enabled: bool = True        # Default to simulation mode

# Loopback buffer for testing
_spi_loopback_enabled: Array[4, bool]
_spi_loopback_buf: Array[256, uint8]      # Shared loopback buffer
_spi_loopback_ptr: int32 = 0

# ============================================================================
# Internal Helpers
# ============================================================================

def _spi_get_base(bus_id: int32) -> uint32:
    """Get hardware base address for SPI bus."""
    return SPI_BASE_ADDR + (cast[uint32](bus_id) * SPIBUS_STRIDE)

def _spi_get_sim_device(bus_id: int32, dev_idx: int32) -> Ptr[uint8]:
    """Get pointer to simulated device data."""
    bus_offset: int32 = bus_id * (SPI_MAX_SIM_DEVICES * SPI_SIM_DEV_SIZE)
    dev_offset: int32 = dev_idx * SPI_SIM_DEV_SIZE
    return &_spi_sim_devices[bus_offset + dev_offset]

def _spi_find_sim_device_by_cs(bus_id: int32, cs: int32) -> Ptr[uint8]:
    """Find simulated device by chip select. Returns NULL if not found."""
    i: int32 = 0
    while i < SPI_MAX_SIM_DEVICES:
        dev: Ptr[uint8] = _spi_get_sim_device(bus_id, i)
        if dev[SPI_SIM_DEV_ENABLED_OFFSET] != 0:
            if cast[int32](dev[SPI_SIM_DEV_CS_OFFSET]) == cs:
                return dev
        i = i + 1
    return cast[Ptr[uint8]](0)

def _spi_mmio_read(addr: uint32) -> uint32:
    """Read from memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def _spi_mmio_write(addr: uint32, val: uint32):
    """Write to memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _spi_delay():
    """Small delay for timing."""
    i: int32 = 0
    while i < 10:
        i = i + 1

def _spi_mode_to_ctrl(mode: uint32) -> uint32:
    """Convert SPI mode to control register bits."""
    ctrl: uint32 = 0
    if mode == SPIBUS_MODE_1:
        ctrl = SPIBUS_CTRL_CPHA
    elif mode == SPIBUS_MODE_2:
        ctrl = SPIBUS_CTRL_CPOL
    elif mode == SPIBUS_MODE_3:
        ctrl = SPIBUS_CTRL_CPOL | SPIBUS_CTRL_CPHA
    return ctrl

# ============================================================================
# Initialization
# ============================================================================

def spibus_init(bus_id: int32, mode: uint32, speed: uint32) -> int32:
    """Initialize SPI bus with specified mode and speed.

    Args:
        bus_id: SPI bus number (0-3)
        mode: SPI mode (SPIBUS_MODE_0 to SPIBUS_MODE_3)
        speed: Bus speed in Hz

    Returns:
        SPIBUS_OK on success, error code on failure
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return SPIBUS_ERR_INVALID
    if mode > 3:
        return SPIBUS_ERR_INVALID

    # Clear simulated devices for this bus
    bus_offset: int32 = bus_id * (SPI_MAX_SIM_DEVICES * SPI_SIM_DEV_SIZE)
    memset(&_spi_sim_devices[bus_offset], 0, SPI_MAX_SIM_DEVICES * SPI_SIM_DEV_SIZE)
    _spi_sim_device_count[bus_id] = 0

    # Store configuration
    _spi_bus_mode[bus_id] = mode
    _spi_bus_speed[bus_id] = speed
    _spi_bus_cs_active[bus_id] = -1
    _spi_loopback_enabled[bus_id] = False

    if not _spi_sim_mode_enabled:
        # Hardware initialization
        base: uint32 = _spi_get_base(bus_id)

        # Disable first
        _spi_mmio_write(base + SPI_CTRL_REG, 0)

        # Calculate baud divisor: divisor = sysclk / (2 * speed)
        baud_div: uint32 = SPI_SYSCLK / (2 * speed)
        if baud_div < 1:
            baud_div = 1
        _spi_mmio_write(base + SPI_BAUD_REG, baud_div)

        # Configure control register
        ctrl: uint32 = SPIBUS_CTRL_ENABLE | SPIBUS_CTRL_MASTER
        ctrl = ctrl | _spi_mode_to_ctrl(mode)
        _spi_mmio_write(base + SPI_CTRL_REG, ctrl)

        # Deselect all chip selects (active low, so write all 1s)
        _spi_mmio_write(base + SPI_CS_REG, 0xFF)

    _spi_bus_initialized[bus_id] = True
    return SPIBUS_OK

def spibus_deinit(bus_id: int32):
    """Deinitialize SPI bus.

    Args:
        bus_id: SPI bus number
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return

    if not _spi_sim_mode_enabled:
        base: uint32 = _spi_get_base(bus_id)
        _spi_mmio_write(base + SPI_CTRL_REG, 0)
        _spi_mmio_write(base + SPI_CS_REG, 0xFF)

    _spi_bus_initialized[bus_id] = False
    _spi_bus_cs_active[bus_id] = -1

def spibus_set_simulation_mode(enabled: bool):
    """Enable or disable simulation mode.

    Args:
        enabled: True for simulation, False for hardware access
    """
    global _spi_sim_mode_enabled
    _spi_sim_mode_enabled = enabled

def spibus_is_initialized(bus_id: int32) -> bool:
    """Check if SPI bus is initialized.

    Args:
        bus_id: SPI bus number

    Returns:
        True if initialized
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return False
    return _spi_bus_initialized[bus_id]

# ============================================================================
# Chip Select Control
# ============================================================================

def spibus_select(bus_id: int32, cs_pin: int32):
    """Assert chip select (active low).

    Args:
        bus_id: SPI bus number
        cs_pin: Chip select pin number (0-7)
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return
    if not _spi_bus_initialized[bus_id]:
        return
    if cs_pin < 0 or cs_pin >= MAX_CHIP_SELECTS:
        return

    _spi_bus_cs_active[bus_id] = cs_pin

    if _spi_sim_mode_enabled:
        # Reset device state when selected
        dev: Ptr[uint8] = _spi_find_sim_device_by_cs(bus_id, cs_pin)
        if cast[uint32](dev) != 0:
            dev[SPI_SIM_DEV_MODE_OFFSET] = SPI_SIM_MODE_CMD
            dev[SPI_SIM_DEV_REGPTR_OFFSET] = 0
    else:
        # Hardware: assert CS (active low)
        base: uint32 = _spi_get_base(bus_id)
        cs_mask: uint32 = ~(1 << cast[uint32](cs_pin)) & 0xFF
        _spi_mmio_write(base + SPI_CS_REG, cs_mask)

def spibus_deselect(bus_id: int32, cs_pin: int32):
    """Deassert chip select.

    Args:
        bus_id: SPI bus number
        cs_pin: Chip select pin number (0-7)
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return
    if not _spi_bus_initialized[bus_id]:
        return

    _spi_bus_cs_active[bus_id] = -1

    if _spi_sim_mode_enabled:
        # Reset device state
        dev: Ptr[uint8] = _spi_find_sim_device_by_cs(bus_id, cs_pin)
        if cast[uint32](dev) != 0:
            dev[SPI_SIM_DEV_MODE_OFFSET] = SPI_SIM_MODE_IDLE
    else:
        # Hardware: deassert all CS lines (all high)
        base: uint32 = _spi_get_base(bus_id)
        _spi_mmio_write(base + SPI_CS_REG, 0xFF)

def spibus_get_selected_cs(bus_id: int32) -> int32:
    """Get currently selected chip select.

    Args:
        bus_id: SPI bus number

    Returns:
        CS pin number or -1 if none selected
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return -1
    return _spi_bus_cs_active[bus_id]

# ============================================================================
# Data Transfer Operations
# ============================================================================

def spibus_transfer(bus_id: int32, tx: Ptr[uint8], rx: Ptr[uint8], length: int32) -> int32:
    """Full-duplex SPI transfer.

    Simultaneously transmits and receives data.

    Args:
        bus_id: SPI bus number
        tx: Pointer to transmit buffer (or NULL to send 0x00)
        rx: Pointer to receive buffer (or NULL to discard)
        length: Number of bytes to transfer

    Returns:
        Number of bytes transferred on success, negative error code on failure
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return SPIBUS_ERR_INVALID
    if not _spi_bus_initialized[bus_id]:
        return SPIBUS_ERR_NOT_INIT
    if length <= 0:
        return SPIBUS_ERR_INVALID

    if _spi_sim_mode_enabled:
        # Simulation mode
        cs: int32 = _spi_bus_cs_active[bus_id]

        # Check for loopback mode
        if _spi_loopback_enabled[bus_id]:
            i: int32 = 0
            while i < length:
                # In loopback, TX goes directly to RX
                tx_byte: uint8 = 0x00
                if cast[uint32](tx) != 0:
                    tx_byte = tx[i]

                if cast[uint32](rx) != 0:
                    rx[i] = tx_byte

                i = i + 1
            return length

        # Find device for current CS
        dev: Ptr[uint8] = _spi_find_sim_device_by_cs(bus_id, cs)

        i: int32 = 0
        while i < length:
            tx_byte: uint8 = 0x00
            if cast[uint32](tx) != 0:
                tx_byte = tx[i]

            rx_byte: uint8 = 0xFF  # Default if no device

            if cast[uint32](dev) != 0:
                reg_ptr: Ptr[uint8] = &dev[SPI_SIM_DEV_REG_OFFSET]
                mode: uint8 = dev[SPI_SIM_DEV_MODE_OFFSET]
                ptr: uint8 = dev[SPI_SIM_DEV_REGPTR_OFFSET]

                if mode == SPI_SIM_MODE_CMD:
                    # First byte is typically address/command
                    # Use upper bit to determine read/write
                    if (tx_byte & 0x80) != 0:
                        dev[SPI_SIM_DEV_MODE_OFFSET] = SPI_SIM_MODE_READ
                    else:
                        dev[SPI_SIM_DEV_MODE_OFFSET] = SPI_SIM_MODE_WRITE
                    dev[SPI_SIM_DEV_REGPTR_OFFSET] = tx_byte & 0x7F
                    rx_byte = 0x00  # Acknowledge
                elif mode == SPI_SIM_MODE_READ:
                    # Read from register
                    rx_byte = reg_ptr[ptr]
                    dev[SPI_SIM_DEV_REGPTR_OFFSET] = ptr + 1
                elif mode == SPI_SIM_MODE_WRITE:
                    # Write to register
                    reg_ptr[ptr] = tx_byte
                    dev[SPI_SIM_DEV_REGPTR_OFFSET] = ptr + 1
                    rx_byte = 0x00

            if cast[uint32](rx) != 0:
                rx[i] = rx_byte

            i = i + 1

        return length
    else:
        # Hardware mode
        base: uint32 = _spi_get_base(bus_id)

        i: int32 = 0
        while i < length:
            # Get TX byte
            tx_byte: uint8 = 0x00
            if cast[uint32](tx) != 0:
                tx_byte = tx[i]

            # Wait for TX empty
            timeout: int32 = SPI_TIMEOUT
            while timeout > 0:
                status: uint32 = _spi_mmio_read(base + SPI_STATUS_REG)
                if (status & SPIBUS_STATUS_TX_FULL) == 0:
                    break
                timeout = timeout - 1
            if timeout == 0:
                return SPIBUS_ERR_TIMEOUT

            # Write TX data
            _spi_mmio_write(base + SPI_DATA_REG, cast[uint32](tx_byte))

            # Wait for transfer complete
            timeout = SPI_TIMEOUT
            while timeout > 0:
                status: uint32 = _spi_mmio_read(base + SPI_STATUS_REG)
                if (status & SPIBUS_STATUS_BUSY) == 0:
                    if (status & SPIBUS_STATUS_RX_EMPTY) == 0:
                        break
                timeout = timeout - 1
            if timeout == 0:
                return SPIBUS_ERR_TIMEOUT

            # Read RX data
            rx_byte: uint8 = cast[uint8](_spi_mmio_read(base + SPI_DATA_REG) & 0xFF)
            if cast[uint32](rx) != 0:
                rx[i] = rx_byte

            i = i + 1

        return length

def spibus_write(bus_id: int32, data: Ptr[uint8], length: int32) -> int32:
    """Write-only SPI transfer.

    Transmits data and discards received data.

    Args:
        bus_id: SPI bus number
        data: Pointer to transmit buffer
        length: Number of bytes to write

    Returns:
        Number of bytes written on success, negative error code on failure
    """
    return spibus_transfer(bus_id, data, cast[Ptr[uint8]](0), length)

def spibus_read(bus_id: int32, buf: Ptr[uint8], length: int32) -> int32:
    """Read-only SPI transfer.

    Sends 0x00 bytes while receiving data.

    Args:
        bus_id: SPI bus number
        buf: Pointer to receive buffer
        length: Number of bytes to read

    Returns:
        Number of bytes read on success, negative error code on failure
    """
    return spibus_transfer(bus_id, cast[Ptr[uint8]](0), buf, length)

def spibus_transfer_byte(bus_id: int32, tx_byte: uint8) -> uint8:
    """Transfer a single byte.

    Args:
        bus_id: SPI bus number
        tx_byte: Byte to transmit

    Returns:
        Received byte (0xFF on error)
    """
    tx_buf: Array[1, uint8]
    rx_buf: Array[1, uint8]
    tx_buf[0] = tx_byte
    rx_buf[0] = 0xFF

    result: int32 = spibus_transfer(bus_id, &tx_buf[0], &rx_buf[0], 1)
    if result != 1:
        return 0xFF

    return rx_buf[0]

def spibus_write_byte(bus_id: int32, byte: uint8) -> int32:
    """Write a single byte.

    Args:
        bus_id: SPI bus number
        byte: Byte to write

    Returns:
        SPIBUS_OK on success, error code on failure
    """
    tx_buf: Array[1, uint8]
    tx_buf[0] = byte

    result: int32 = spibus_write(bus_id, &tx_buf[0], 1)
    if result == 1:
        return SPIBUS_OK
    return result

def spibus_read_byte(bus_id: int32) -> uint8:
    """Read a single byte.

    Args:
        bus_id: SPI bus number

    Returns:
        Received byte (0xFF on error)
    """
    rx_buf: Array[1, uint8]
    rx_buf[0] = 0xFF

    spibus_read(bus_id, &rx_buf[0], 1)
    return rx_buf[0]

# ============================================================================
# Speed Configuration
# ============================================================================

def spibus_set_speed(bus_id: int32, hz: uint32) -> int32:
    """Change SPI clock speed.

    Args:
        bus_id: SPI bus number
        hz: New speed in Hz

    Returns:
        SPIBUS_OK on success, error code on failure
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return SPIBUS_ERR_INVALID
    if not _spi_bus_initialized[bus_id]:
        return SPIBUS_ERR_NOT_INIT
    if hz == 0:
        return SPIBUS_ERR_INVALID

    _spi_bus_speed[bus_id] = hz

    if not _spi_sim_mode_enabled:
        base: uint32 = _spi_get_base(bus_id)

        # Calculate new baud divisor
        baud_div: uint32 = SPI_SYSCLK / (2 * hz)
        if baud_div < 1:
            baud_div = 1

        _spi_mmio_write(base + SPI_BAUD_REG, baud_div)

    return SPIBUS_OK

def spibus_get_speed(bus_id: int32) -> uint32:
    """Get configured bus speed.

    Args:
        bus_id: SPI bus number

    Returns:
        Speed in Hz
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return 0
    return _spi_bus_speed[bus_id]

def spibus_set_mode(bus_id: int32, mode: uint32) -> int32:
    """Change SPI mode.

    Args:
        bus_id: SPI bus number
        mode: New SPI mode (0-3)

    Returns:
        SPIBUS_OK on success, error code on failure
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return SPIBUS_ERR_INVALID
    if not _spi_bus_initialized[bus_id]:
        return SPIBUS_ERR_NOT_INIT
    if mode > 3:
        return SPIBUS_ERR_INVALID

    _spi_bus_mode[bus_id] = mode

    if not _spi_sim_mode_enabled:
        base: uint32 = _spi_get_base(bus_id)

        # Read current control register
        ctrl: uint32 = _spi_mmio_read(base + SPI_CTRL_REG)

        # Clear mode bits and set new ones
        ctrl = ctrl & ~(SPIBUS_CTRL_CPOL | SPIBUS_CTRL_CPHA)
        ctrl = ctrl | _spi_mode_to_ctrl(mode)

        _spi_mmio_write(base + SPI_CTRL_REG, ctrl)

    return SPIBUS_OK

def spibus_get_mode(bus_id: int32) -> uint32:
    """Get configured SPI mode.

    Args:
        bus_id: SPI bus number

    Returns:
        SPI mode (0-3)
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return 0
    return _spi_bus_mode[bus_id]

# ============================================================================
# Loopback Mode (for testing)
# ============================================================================

def spibus_set_loopback(bus_id: int32, enabled: bool):
    """Enable or disable loopback mode.

    In loopback mode, transmitted data is received back.

    Args:
        bus_id: SPI bus number
        enabled: True to enable loopback
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return

    _spi_loopback_enabled[bus_id] = enabled

    if not _spi_sim_mode_enabled:
        base: uint32 = _spi_get_base(bus_id)
        ctrl: uint32 = _spi_mmio_read(base + SPI_CTRL_REG)

        if enabled:
            ctrl = ctrl | SPIBUS_CTRL_LOOP
        else:
            ctrl = ctrl & ~SPIBUS_CTRL_LOOP

        _spi_mmio_write(base + SPI_CTRL_REG, ctrl)

def spibus_is_loopback(bus_id: int32) -> bool:
    """Check if loopback mode is enabled.

    Args:
        bus_id: SPI bus number

    Returns:
        True if loopback enabled
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return False
    return _spi_loopback_enabled[bus_id]

# ============================================================================
# Simulation Device Management
# ============================================================================

def spi_sim_add_device(bus_id: int32, cs: int32) -> int32:
    """Add a simulated device to the bus.

    Args:
        bus_id: SPI bus number
        cs: Chip select number for this device

    Returns:
        Device index on success, -1 if full or invalid
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return -1
    if cs < 0 or cs >= MAX_CHIP_SELECTS:
        return -1

    if _spi_sim_device_count[bus_id] >= SPI_MAX_SIM_DEVICES:
        return -1

    # Check for duplicate CS
    if cast[uint32](_spi_find_sim_device_by_cs(bus_id, cs)) != 0:
        return -1

    # Find free slot
    i: int32 = 0
    while i < SPI_MAX_SIM_DEVICES:
        dev: Ptr[uint8] = _spi_get_sim_device(bus_id, i)
        if dev[SPI_SIM_DEV_ENABLED_OFFSET] == 0:
            dev[SPI_SIM_DEV_CS_OFFSET] = cast[uint8](cs)
            dev[SPI_SIM_DEV_ENABLED_OFFSET] = 1
            dev[SPI_SIM_DEV_MODE_OFFSET] = SPI_SIM_MODE_IDLE
            dev[SPI_SIM_DEV_REGPTR_OFFSET] = 0
            memset(&dev[SPI_SIM_DEV_REG_OFFSET], 0, 256)
            _spi_sim_device_count[bus_id] = _spi_sim_device_count[bus_id] + 1
            return i
        i = i + 1

    return -1

def spi_sim_remove_device(bus_id: int32, cs: int32) -> bool:
    """Remove a simulated device from the bus.

    Args:
        bus_id: SPI bus number
        cs: Chip select of device to remove

    Returns:
        True if device was removed
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return False

    dev: Ptr[uint8] = _spi_find_sim_device_by_cs(bus_id, cs)
    if cast[uint32](dev) == 0:
        return False

    dev[SPI_SIM_DEV_ENABLED_OFFSET] = 0
    _spi_sim_device_count[bus_id] = _spi_sim_device_count[bus_id] - 1
    return True

def spi_sim_set_reg(bus_id: int32, cs: int32, reg: uint8, value: uint8) -> bool:
    """Set a register value in simulated device.

    Args:
        bus_id: SPI bus number
        cs: Chip select of device
        reg: Register address
        value: Value to set

    Returns:
        True on success
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return False

    dev: Ptr[uint8] = _spi_find_sim_device_by_cs(bus_id, cs)
    if cast[uint32](dev) == 0:
        return False

    reg_ptr: Ptr[uint8] = &dev[SPI_SIM_DEV_REG_OFFSET]
    reg_ptr[reg] = value
    return True

def spi_sim_get_reg(bus_id: int32, cs: int32, reg: uint8) -> int32:
    """Get a register value from simulated device.

    Args:
        bus_id: SPI bus number
        cs: Chip select of device
        reg: Register address

    Returns:
        Register value (0-255) or -1 if not found
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return -1

    dev: Ptr[uint8] = _spi_find_sim_device_by_cs(bus_id, cs)
    if cast[uint32](dev) == 0:
        return -1

    reg_ptr: Ptr[uint8] = &dev[SPI_SIM_DEV_REG_OFFSET]
    return cast[int32](reg_ptr[reg])

def spi_sim_set_regs(bus_id: int32, cs: int32, start_reg: uint8,
                     data: Ptr[uint8], length: int32) -> bool:
    """Set multiple register values in simulated device.

    Args:
        bus_id: SPI bus number
        cs: Chip select of device
        start_reg: Starting register address
        data: Data to write
        length: Number of bytes

    Returns:
        True on success
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return False

    dev: Ptr[uint8] = _spi_find_sim_device_by_cs(bus_id, cs)
    if cast[uint32](dev) == 0:
        return False

    reg_ptr: Ptr[uint8] = &dev[SPI_SIM_DEV_REG_OFFSET]

    i: int32 = 0
    reg: uint8 = start_reg
    while i < length:
        reg_ptr[reg] = data[i]
        reg = reg + 1
        i = i + 1

    return True

def spi_sim_clear_all(bus_id: int32):
    """Remove all simulated devices from bus.

    Args:
        bus_id: SPI bus number
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return

    bus_offset: int32 = bus_id * (SPI_MAX_SIM_DEVICES * SPI_SIM_DEV_SIZE)
    memset(&_spi_sim_devices[bus_offset], 0, SPI_MAX_SIM_DEVICES * SPI_SIM_DEV_SIZE)
    _spi_sim_device_count[bus_id] = 0

def spi_sim_get_device_count(bus_id: int32) -> int32:
    """Get number of simulated devices on bus.

    Args:
        bus_id: SPI bus number

    Returns:
        Device count
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return 0
    return _spi_sim_device_count[bus_id]

# ============================================================================
# Status and Information
# ============================================================================

def spibus_is_busy(bus_id: int32) -> bool:
    """Check if bus is busy with a transfer.

    Args:
        bus_id: SPI bus number

    Returns:
        True if bus is busy
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return False
    if not _spi_bus_initialized[bus_id]:
        return False

    if _spi_sim_mode_enabled:
        return False  # Simulation is always synchronous
    else:
        base: uint32 = _spi_get_base(bus_id)
        status: uint32 = _spi_mmio_read(base + SPI_STATUS_REG)
        return (status & SPIBUS_STATUS_BUSY) != 0

def spibus_flush(bus_id: int32):
    """Wait for any pending transfers to complete.

    Args:
        bus_id: SPI bus number
    """
    if bus_id < 0 or bus_id >= MAX_SPI_BUSES:
        return
    if not _spi_bus_initialized[bus_id]:
        return

    if not _spi_sim_mode_enabled:
        base: uint32 = _spi_get_base(bus_id)
        timeout: int32 = SPI_TIMEOUT

        while timeout > 0:
            status: uint32 = _spi_mmio_read(base + SPI_STATUS_REG)
            if (status & SPIBUS_STATUS_BUSY) == 0:
                break
            timeout = timeout - 1

# ============================================================================
# Common Device Helpers
# ============================================================================

def spibus_write_then_read(bus_id: int32, cs: int32, tx: Ptr[uint8], tx_len: int32,
                        rx: Ptr[uint8], rx_len: int32) -> int32:
    """Common pattern: write command bytes, then read response.

    Selects CS, writes tx bytes, reads rx bytes, deselects CS.

    Args:
        bus_id: SPI bus number
        cs: Chip select pin
        tx: Transmit buffer (command bytes)
        tx_len: Number of bytes to write
        rx: Receive buffer
        rx_len: Number of bytes to read

    Returns:
        Total bytes transferred on success, negative error on failure
    """
    spibus_select(bus_id, cs)

    # Write command
    result: int32 = spibus_write(bus_id, tx, tx_len)
    if result < 0:
        spibus_deselect(bus_id, cs)
        return result

    # Read response
    result = spibus_read(bus_id, rx, rx_len)
    if result < 0:
        spibus_deselect(bus_id, cs)
        return result

    spibus_deselect(bus_id, cs)
    return tx_len + rx_len

def spibus_reg_read(bus_id: int32, cs: int32, reg: uint8) -> int32:
    """Read a single register from SPI device.

    Uses convention: write (reg | 0x80), read 1 byte.

    Args:
        bus_id: SPI bus number
        cs: Chip select pin
        reg: Register address

    Returns:
        Register value (0-255) on success, negative error on failure
    """
    tx_buf: Array[1, uint8]
    rx_buf: Array[1, uint8]

    tx_buf[0] = reg | 0x80  # Set read bit

    spibus_select(bus_id, cs)
    spibus_write(bus_id, &tx_buf[0], 1)
    result: int32 = spibus_read(bus_id, &rx_buf[0], 1)
    spibus_deselect(bus_id, cs)

    if result != 1:
        return SPIBUS_ERR_TIMEOUT

    return cast[int32](rx_buf[0])

def spibus_reg_write(bus_id: int32, cs: int32, reg: uint8, value: uint8) -> int32:
    """Write a single register to SPI device.

    Uses convention: write reg (without read bit), write value.

    Args:
        bus_id: SPI bus number
        cs: Chip select pin
        reg: Register address
        value: Value to write

    Returns:
        SPIBUS_OK on success, negative error on failure
    """
    tx_buf: Array[2, uint8]
    tx_buf[0] = reg & 0x7F  # Clear read bit
    tx_buf[1] = value

    spibus_select(bus_id, cs)
    result: int32 = spibus_write(bus_id, &tx_buf[0], 2)
    spibus_deselect(bus_id, cs)

    if result != 2:
        return SPIBUS_ERR_TIMEOUT

    return SPIBUS_OK
