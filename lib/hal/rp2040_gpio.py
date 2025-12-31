# RP2040 GPIO Hardware Abstraction Layer
#
# Low-level GPIO driver for Raspberry Pi Pico (RP2040).
# Uses SIO (Single-cycle IO) for fast GPIO access and IO_BANK0 for
# function selection.
#
# Memory Map:
#   SIO_BASE:      0xD0000000 - Single-cycle IO block
#   IO_BANK0_BASE: 0x40014000 - GPIO control and status
#   PADS_BANK0:    0x4001C000 - Pad control (drive strength, pull-ups)

# ============================================================================
# Base Addresses
# ============================================================================

SIO_BASE: uint32 = 0xD0000000
IO_BANK0_BASE: uint32 = 0x40014000
PADS_BANK0_BASE: uint32 = 0x4001C000

# ============================================================================
# SIO GPIO Registers (at SIO_BASE)
# ============================================================================
# SIO provides atomic set/clear/xor operations in single cycle

SIO_GPIO_IN: uint32 = 0x004           # GPIO input value
SIO_GPIO_HI_IN: uint32 = 0x008        # QSPI GPIO input (GPIO 26-29)
SIO_GPIO_OUT: uint32 = 0x010          # GPIO output value
SIO_GPIO_OUT_SET: uint32 = 0x014      # GPIO output set (atomic)
SIO_GPIO_OUT_CLR: uint32 = 0x018      # GPIO output clear (atomic)
SIO_GPIO_OUT_XOR: uint32 = 0x01C      # GPIO output XOR (atomic)
SIO_GPIO_OE: uint32 = 0x020           # GPIO output enable
SIO_GPIO_OE_SET: uint32 = 0x024       # Output enable set (atomic)
SIO_GPIO_OE_CLR: uint32 = 0x028       # Output enable clear (atomic)
SIO_GPIO_OE_XOR: uint32 = 0x02C       # Output enable XOR (atomic)

# ============================================================================
# IO_BANK0 Registers (GPIO function select and interrupt control)
# ============================================================================
# Each GPIO has STATUS and CTRL registers

# GPIO function select values (for GPIO_CTRL)
GPIO_FUNC_XIP: uint32 = 0
GPIO_FUNC_SPI: uint32 = 1
GPIO_FUNC_UART: uint32 = 2
GPIO_FUNC_I2C: uint32 = 3
GPIO_FUNC_PWM: uint32 = 4
GPIO_FUNC_SIO: uint32 = 5      # Software IO (normal GPIO)
GPIO_FUNC_PIO0: uint32 = 6
GPIO_FUNC_PIO1: uint32 = 7
GPIO_FUNC_GPCK: uint32 = 8     # Clock
GPIO_FUNC_USB: uint32 = 9
GPIO_FUNC_NULL: uint32 = 31    # Disable

# Register stride per GPIO
IO_BANK0_GPIO_STRIDE: uint32 = 8

# ============================================================================
# PADS_BANK0 Registers (electrical characteristics)
# ============================================================================

PADS_GPIO_STRIDE: uint32 = 4

# Pad control bits
PAD_OD: uint32 = 0x80           # Output disable
PAD_IE: uint32 = 0x40           # Input enable
PAD_DRIVE_2MA: uint32 = 0x00    # Drive strength
PAD_DRIVE_4MA: uint32 = 0x10
PAD_DRIVE_8MA: uint32 = 0x20
PAD_DRIVE_12MA: uint32 = 0x30
PAD_PUE: uint32 = 0x08          # Pull-up enable
PAD_PDE: uint32 = 0x04          # Pull-down enable
PAD_SCHMITT: uint32 = 0x02      # Schmitt trigger
PAD_SLEWFAST: uint32 = 0x01     # Fast slew rate

# Default pad configuration
PAD_DEFAULT: uint32 = 0x56      # IE | DRIVE_4MA | SCHMITT

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

# ============================================================================
# GPIO Functions
# ============================================================================

def gpio_init(pin: uint32):
    """Initialize a GPIO pin for software control.

    Configures pin for SIO function (normal GPIO), enables input,
    sets default pad configuration.

    Args:
        pin: GPIO pin number (0-29)
    """
    if pin > 29:
        return

    # Set function to SIO (software IO)
    ctrl_addr: uint32 = IO_BANK0_BASE + 4 + (pin * IO_BANK0_GPIO_STRIDE)
    mmio_write(ctrl_addr, GPIO_FUNC_SIO)

    # Configure pad: input enable, 4mA drive, schmitt trigger
    pad_addr: uint32 = PADS_BANK0_BASE + 4 + (pin * PADS_GPIO_STRIDE)
    mmio_write(pad_addr, PAD_DEFAULT)

    # Disable output by default (input mode)
    mmio_write(SIO_BASE + SIO_GPIO_OE_CLR, 1 << pin)

def gpio_set_function(pin: uint32, func: uint32):
    """Set GPIO pin function.

    Args:
        pin: GPIO pin number (0-29)
        func: Function number (GPIO_FUNC_*)
    """
    if pin > 29:
        return

    ctrl_addr: uint32 = IO_BANK0_BASE + 4 + (pin * IO_BANK0_GPIO_STRIDE)
    mmio_write(ctrl_addr, func & 0x1F)

def gpio_set_dir(pin: uint32, output: bool):
    """Set GPIO pin direction.

    Args:
        pin: GPIO pin number (0-29)
        output: True for output, False for input
    """
    if pin > 29:
        return

    mask: uint32 = 1 << pin
    if output:
        mmio_write(SIO_BASE + SIO_GPIO_OE_SET, mask)
    else:
        mmio_write(SIO_BASE + SIO_GPIO_OE_CLR, mask)

def gpio_set_dir_out(pin: uint32):
    """Set GPIO pin as output."""
    gpio_set_dir(pin, True)

def gpio_set_dir_in(pin: uint32):
    """Set GPIO pin as input."""
    gpio_set_dir(pin, False)

def gpio_put(pin: uint32, value: bool):
    """Set GPIO pin output value.

    Args:
        pin: GPIO pin number (0-29)
        value: True for high, False for low
    """
    if pin > 29:
        return

    mask: uint32 = 1 << pin
    if value:
        mmio_write(SIO_BASE + SIO_GPIO_OUT_SET, mask)
    else:
        mmio_write(SIO_BASE + SIO_GPIO_OUT_CLR, mask)

def gpio_get(pin: uint32) -> bool:
    """Read GPIO pin input value.

    Args:
        pin: GPIO pin number (0-29)

    Returns:
        True if high, False if low
    """
    if pin > 29:
        return False

    val: uint32 = mmio_read(SIO_BASE + SIO_GPIO_IN)
    return ((val >> pin) & 1) != 0

def gpio_toggle(pin: uint32):
    """Toggle GPIO pin output.

    Args:
        pin: GPIO pin number (0-29)
    """
    if pin > 29:
        return

    mmio_write(SIO_BASE + SIO_GPIO_OUT_XOR, 1 << pin)

def gpio_set_pulls(pin: uint32, up: bool, down: bool):
    """Configure GPIO pull-up/pull-down resistors.

    Args:
        pin: GPIO pin number (0-29)
        up: Enable pull-up
        down: Enable pull-down
    """
    if pin > 29:
        return

    pad_addr: uint32 = PADS_BANK0_BASE + 4 + (pin * PADS_GPIO_STRIDE)
    val: uint32 = mmio_read(pad_addr)

    # Clear pull bits
    val = val & ~(PAD_PUE | PAD_PDE)

    # Set requested pulls
    if up:
        val = val | PAD_PUE
    if down:
        val = val | PAD_PDE

    mmio_write(pad_addr, val)

def gpio_pull_up(pin: uint32):
    """Enable pull-up resistor on GPIO pin."""
    gpio_set_pulls(pin, True, False)

def gpio_pull_down(pin: uint32):
    """Enable pull-down resistor on GPIO pin."""
    gpio_set_pulls(pin, False, True)

def gpio_disable_pulls(pin: uint32):
    """Disable all pull resistors on GPIO pin."""
    gpio_set_pulls(pin, False, False)

def gpio_set_drive(pin: uint32, drive: uint32):
    """Set GPIO drive strength.

    Args:
        pin: GPIO pin number (0-29)
        drive: PAD_DRIVE_2MA, PAD_DRIVE_4MA, PAD_DRIVE_8MA, or PAD_DRIVE_12MA
    """
    if pin > 29:
        return

    pad_addr: uint32 = PADS_BANK0_BASE + 4 + (pin * PADS_GPIO_STRIDE)
    val: uint32 = mmio_read(pad_addr)

    # Clear drive bits and set new value
    val = (val & ~0x30) | (drive & 0x30)
    mmio_write(pad_addr, val)

def gpio_set_slew_fast(pin: uint32, fast: bool):
    """Set GPIO slew rate.

    Args:
        pin: GPIO pin number (0-29)
        fast: True for fast slew rate
    """
    if pin > 29:
        return

    pad_addr: uint32 = PADS_BANK0_BASE + 4 + (pin * PADS_GPIO_STRIDE)
    val: uint32 = mmio_read(pad_addr)

    if fast:
        val = val | PAD_SLEWFAST
    else:
        val = val & ~PAD_SLEWFAST

    mmio_write(pad_addr, val)

# ============================================================================
# Bulk GPIO Operations (for efficiency)
# ============================================================================

def gpio_put_all(mask: uint32):
    """Set multiple GPIO pins at once.

    Args:
        mask: Bit mask of values (bit N = GPIO N value)
    """
    mmio_write(SIO_BASE + SIO_GPIO_OUT, mask)

def gpio_get_all() -> uint32:
    """Read all GPIO pins at once.

    Returns:
        Bit mask of GPIO input values
    """
    return mmio_read(SIO_BASE + SIO_GPIO_IN)

def gpio_set_mask(mask: uint32):
    """Set GPIO pins high (atomic).

    Args:
        mask: Bit mask of pins to set high
    """
    mmio_write(SIO_BASE + SIO_GPIO_OUT_SET, mask)

def gpio_clr_mask(mask: uint32):
    """Set GPIO pins low (atomic).

    Args:
        mask: Bit mask of pins to set low
    """
    mmio_write(SIO_BASE + SIO_GPIO_OUT_CLR, mask)

def gpio_xor_mask(mask: uint32):
    """Toggle GPIO pins (atomic).

    Args:
        mask: Bit mask of pins to toggle
    """
    mmio_write(SIO_BASE + SIO_GPIO_OUT_XOR, mask)

def gpio_set_dir_all(mask: uint32):
    """Set direction for all GPIO pins.

    Args:
        mask: Bit mask (1 = output, 0 = input)
    """
    mmio_write(SIO_BASE + SIO_GPIO_OE, mask)

def gpio_set_dir_out_masked(mask: uint32):
    """Set multiple GPIO pins as outputs (atomic).

    Args:
        mask: Bit mask of pins to set as outputs
    """
    mmio_write(SIO_BASE + SIO_GPIO_OE_SET, mask)

def gpio_set_dir_in_masked(mask: uint32):
    """Set multiple GPIO pins as inputs (atomic).

    Args:
        mask: Bit mask of pins to set as inputs
    """
    mmio_write(SIO_BASE + SIO_GPIO_OE_CLR, mask)
