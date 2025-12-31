# RP2040 PWM Hardware Abstraction Layer
#
# Low-level PWM driver for Raspberry Pi Pico (RP2040).
# The RP2040 has 8 PWM slices, each with 2 output channels (A and B).
# Each GPIO can be mapped to one PWM output.
#
# GPIO to PWM mapping:
#   GPIO 0,1   -> Slice 0 (0=A, 1=B)
#   GPIO 2,3   -> Slice 1 (2=A, 3=B)
#   GPIO 4,5   -> Slice 2 (4=A, 5=B)
#   GPIO 6,7   -> Slice 3 (6=A, 7=B)
#   GPIO 8,9   -> Slice 4 (8=A, 9=B)
#   GPIO 10,11 -> Slice 5 (10=A, 11=B)
#   GPIO 12,13 -> Slice 6 (12=A, 13=B)
#   GPIO 14,15 -> Slice 7 (14=A, 15=B)
#   GPIO 16-25 -> Same pattern repeats (slice = (gpio >> 1) & 7)
#
# Memory Map:
#   PWM_BASE:      0x40050000 - PWM block
#   IO_BANK0_BASE: 0x40014000 - GPIO function select

# ============================================================================
# Base Addresses
# ============================================================================

PWM_BASE: uint32 = 0x40050000
IO_BANK0_BASE: uint32 = 0x40014000
PADS_BANK0_BASE: uint32 = 0x4001C000

# ============================================================================
# PWM Register Offsets (per slice)
# ============================================================================
# Each slice has registers at offset: slice * 0x14

PWM_CH_CSR: uint32 = 0x00      # Control and status register
PWM_CH_DIV: uint32 = 0x04      # Clock divider register
PWM_CH_CTR: uint32 = 0x08      # Direct counter access
PWM_CH_CC: uint32 = 0x0C       # Counter compare values (A in [15:0], B in [31:16])
PWM_CH_TOP: uint32 = 0x10      # Counter wrap value

PWM_SLICE_STRIDE: uint32 = 0x14  # Register stride per slice

# ============================================================================
# Global PWM Registers (after slice registers)
# ============================================================================

PWM_EN: uint32 = 0xA0          # Enable register (1 bit per slice)
PWM_INTR: uint32 = 0xA4        # Raw interrupts
PWM_INTE: uint32 = 0xA8        # Interrupt enable
PWM_INTF: uint32 = 0xAC        # Interrupt force
PWM_INTS: uint32 = 0xB0        # Interrupt status after masking

# ============================================================================
# CSR (Control and Status) Register Bits
# ============================================================================

PWM_CSR_EN: uint32 = 0x01           # Enable slice
PWM_CSR_PH_CORRECT: uint32 = 0x02   # Phase-correct mode
PWM_CSR_A_INV: uint32 = 0x04        # Invert output A
PWM_CSR_B_INV: uint32 = 0x08        # Invert output B
PWM_CSR_DIVMODE_FREE: uint32 = 0x00 # Free-running (bits 5:4 = 00)
PWM_CSR_DIVMODE_LEVEL: uint32 = 0x10  # Level-sensitive (bits 5:4 = 01)
PWM_CSR_DIVMODE_RISE: uint32 = 0x20   # Rising edge (bits 5:4 = 10)
PWM_CSR_DIVMODE_FALL: uint32 = 0x30   # Falling edge (bits 5:4 = 11)
PWM_CSR_PH_RET: uint32 = 0x40       # Retard phase of counter by 1
PWM_CSR_PH_ADV: uint32 = 0x80       # Advance phase of counter by 1

# ============================================================================
# DIV Register Format
# ============================================================================
# Bits [11:4] = Integer part (1-255, 0 means max divisor of 256)
# Bits [3:0]  = Fractional part (0-15, in 1/16ths)

PWM_DIV_INT_SHIFT: uint32 = 4
PWM_DIV_FRAC_MASK: uint32 = 0x0F

# ============================================================================
# CC (Counter Compare) Register Format
# ============================================================================
# Bits [15:0]  = Channel A compare value
# Bits [31:16] = Channel B compare value

PWM_CC_A_MASK: uint32 = 0x0000FFFF
PWM_CC_B_SHIFT: uint32 = 16

# ============================================================================
# Channel Definitions
# ============================================================================

PWM_CHAN_A: uint32 = 0
PWM_CHAN_B: uint32 = 1

# ============================================================================
# GPIO Function Select
# ============================================================================

GPIO_FUNC_PWM: uint32 = 4
IO_BANK0_GPIO_STRIDE: uint32 = 8

# Pad control bits
PAD_OD: uint32 = 0x80           # Output disable
PAD_IE: uint32 = 0x40           # Input enable
PAD_DRIVE_2MA: uint32 = 0x00
PAD_DRIVE_4MA: uint32 = 0x10
PAD_DRIVE_8MA: uint32 = 0x20
PAD_DRIVE_12MA: uint32 = 0x30
PAD_SCHMITT: uint32 = 0x02
PAD_SLEWFAST: uint32 = 0x01

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

def _pwm_slice_base(slice: uint32) -> uint32:
    """Get base address for PWM slice registers.

    Args:
        slice: PWM slice number (0-7)

    Returns:
        Base address for slice registers
    """
    return PWM_BASE + (slice * PWM_SLICE_STRIDE)

# ============================================================================
# GPIO to PWM Mapping Functions
# ============================================================================

def pwm_gpio_to_slice(gpio: uint32) -> uint32:
    """Get PWM slice number for a GPIO pin.

    Args:
        gpio: GPIO pin number (0-29)

    Returns:
        PWM slice number (0-7)
    """
    return (gpio >> 1) & 7

def pwm_gpio_to_channel(gpio: uint32) -> uint32:
    """Get PWM channel for a GPIO pin.

    Args:
        gpio: GPIO pin number (0-29)

    Returns:
        PWM_CHAN_A (0) or PWM_CHAN_B (1)
    """
    return gpio & 1

# ============================================================================
# GPIO Configuration
# ============================================================================

def pwm_gpio_init(gpio: uint32):
    """Configure GPIO pin for PWM function.

    Sets the GPIO to function 4 (PWM) and configures pad settings.

    Args:
        gpio: GPIO pin number (0-29)
    """
    if gpio > 29:
        return

    # Set GPIO function to PWM (function 4)
    ctrl_addr: uint32 = IO_BANK0_BASE + 4 + (gpio * IO_BANK0_GPIO_STRIDE)
    mmio_write(ctrl_addr, GPIO_FUNC_PWM)

    # Configure pad: disable input, enable output, 4mA drive
    pad_addr: uint32 = PADS_BANK0_BASE + 4 + (gpio * 4)
    mmio_write(pad_addr, PAD_DRIVE_4MA | PAD_SLEWFAST)

# ============================================================================
# PWM Initialization and Configuration
# ============================================================================

def pwm_init(slice: uint32, wrap: uint32, clkdiv: uint32):
    """Initialize PWM slice with wrap value and clock divider.

    Args:
        slice: PWM slice number (0-7)
        wrap: Counter wrap value (TOP register, 0-65535)
        clkdiv: Clock divider (integer part, 1-255)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)

    # Disable slice during configuration
    mmio_write(base + PWM_CH_CSR, 0)

    # Set clock divider (integer only, no fractional)
    mmio_write(base + PWM_CH_DIV, clkdiv << PWM_DIV_INT_SHIFT)

    # Set wrap value (TOP)
    mmio_write(base + PWM_CH_TOP, wrap & 0xFFFF)

    # Clear counter
    mmio_write(base + PWM_CH_CTR, 0)

    # Clear compare values
    mmio_write(base + PWM_CH_CC, 0)

def pwm_init_gpio(gpio: uint32, wrap: uint32, clkdiv: uint32):
    """Initialize PWM for a specific GPIO pin.

    Convenience function that configures both GPIO and PWM slice.

    Args:
        gpio: GPIO pin number (0-29)
        wrap: Counter wrap value (0-65535)
        clkdiv: Clock divider (1-255)
    """
    if gpio > 29:
        return

    # Configure GPIO for PWM function
    pwm_gpio_init(gpio)

    # Initialize the corresponding PWM slice
    slice: uint32 = pwm_gpio_to_slice(gpio)
    pwm_init(slice, wrap, clkdiv)

def pwm_set_wrap(slice: uint32, wrap: uint32):
    """Set counter wrap value (TOP register).

    The counter counts from 0 to wrap, then wraps back to 0.
    PWM frequency = sys_clk / (clkdiv * (wrap + 1))

    Args:
        slice: PWM slice number (0-7)
        wrap: Wrap value (0-65535)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    mmio_write(base + PWM_CH_TOP, wrap & 0xFFFF)

def pwm_set_clkdiv(slice: uint32, div_int: uint32, div_frac: uint32):
    """Set clock divider with integer and fractional parts.

    Total divisor = div_int + div_frac/16

    Args:
        slice: PWM slice number (0-7)
        div_int: Integer part (1-255, 0 = 256)
        div_frac: Fractional part (0-15, in 1/16ths)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    divval: uint32 = ((div_int & 0xFF) << PWM_DIV_INT_SHIFT) | (div_frac & PWM_DIV_FRAC_MASK)
    mmio_write(base + PWM_CH_DIV, divval)

def pwm_set_clkdiv_int(slice: uint32, div: uint32):
    """Set clock divider (integer only).

    Args:
        slice: PWM slice number (0-7)
        div: Integer divisor (1-255)
    """
    pwm_set_clkdiv(slice, div, 0)

# ============================================================================
# Duty Cycle / Compare Value Functions
# ============================================================================

def pwm_set_chan_level(slice: uint32, chan: uint32, level: uint32):
    """Set compare level for PWM channel.

    The output is high when counter < level, low when counter >= level.
    Duty cycle = level / (wrap + 1)

    Args:
        slice: PWM slice number (0-7)
        chan: Channel (PWM_CHAN_A or PWM_CHAN_B)
        level: Compare value (0-65535)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    cc: uint32 = mmio_read(base + PWM_CH_CC)

    if chan == PWM_CHAN_A:
        cc = (cc & 0xFFFF0000) | (level & 0xFFFF)
    else:
        cc = (cc & 0x0000FFFF) | ((level & 0xFFFF) << PWM_CC_B_SHIFT)

    mmio_write(base + PWM_CH_CC, cc)

def pwm_set_both_levels(slice: uint32, level_a: uint32, level_b: uint32):
    """Set compare levels for both channels at once.

    Args:
        slice: PWM slice number (0-7)
        level_a: Channel A compare value (0-65535)
        level_b: Channel B compare value (0-65535)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    cc: uint32 = (level_a & 0xFFFF) | ((level_b & 0xFFFF) << PWM_CC_B_SHIFT)
    mmio_write(base + PWM_CH_CC, cc)

def pwm_set_gpio_level(gpio: uint32, level: uint32):
    """Set PWM level by GPIO number.

    Convenience function that determines slice and channel from GPIO.

    Args:
        gpio: GPIO pin number (0-29)
        level: Compare value (0-65535)
    """
    if gpio > 29:
        return

    slice: uint32 = pwm_gpio_to_slice(gpio)
    chan: uint32 = pwm_gpio_to_channel(gpio)
    pwm_set_chan_level(slice, chan, level)

def pwm_get_chan_level(slice: uint32, chan: uint32) -> uint32:
    """Get current compare level for PWM channel.

    Args:
        slice: PWM slice number (0-7)
        chan: Channel (PWM_CHAN_A or PWM_CHAN_B)

    Returns:
        Current compare value
    """
    if slice > 7:
        return 0

    base: uint32 = _pwm_slice_base(slice)
    cc: uint32 = mmio_read(base + PWM_CH_CC)

    if chan == PWM_CHAN_A:
        return cc & 0xFFFF
    else:
        return (cc >> PWM_CC_B_SHIFT) & 0xFFFF

# ============================================================================
# Enable / Disable Functions
# ============================================================================

def pwm_enable(slice: uint32):
    """Enable PWM slice.

    Args:
        slice: PWM slice number (0-7)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    csr: uint32 = mmio_read(base + PWM_CH_CSR)
    mmio_write(base + PWM_CH_CSR, csr | PWM_CSR_EN)

def pwm_disable(slice: uint32):
    """Disable PWM slice.

    Args:
        slice: PWM slice number (0-7)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    csr: uint32 = mmio_read(base + PWM_CH_CSR)
    mmio_write(base + PWM_CH_CSR, csr & ~PWM_CSR_EN)

def pwm_set_enabled(slice: uint32, enabled: bool):
    """Enable or disable PWM slice.

    Args:
        slice: PWM slice number (0-7)
        enabled: True to enable, False to disable
    """
    if enabled:
        pwm_enable(slice)
    else:
        pwm_disable(slice)

def pwm_enable_mask(mask: uint32):
    """Enable multiple PWM slices at once.

    Args:
        mask: Bit mask of slices to enable (bit N = slice N)
    """
    mmio_write(PWM_BASE + PWM_EN, mask & 0xFF)

def pwm_get_enabled() -> uint32:
    """Get currently enabled PWM slices.

    Returns:
        Bit mask of enabled slices
    """
    return mmio_read(PWM_BASE + PWM_EN)

# ============================================================================
# Phase-Correct Mode
# ============================================================================

def pwm_set_phase_correct(slice: uint32, enable: bool):
    """Enable or disable phase-correct mode.

    In phase-correct mode, the counter counts up to TOP then back down to 0.
    This produces center-aligned PWM with half the frequency.

    Args:
        slice: PWM slice number (0-7)
        enable: True for phase-correct mode
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    csr: uint32 = mmio_read(base + PWM_CH_CSR)

    if enable:
        csr = csr | PWM_CSR_PH_CORRECT
    else:
        csr = csr & ~PWM_CSR_PH_CORRECT

    mmio_write(base + PWM_CH_CSR, csr)

# ============================================================================
# Output Inversion
# ============================================================================

def pwm_set_output_polarity(slice: uint32, invert_a: bool, invert_b: bool):
    """Set output polarity for PWM channels.

    Args:
        slice: PWM slice number (0-7)
        invert_a: True to invert channel A output
        invert_b: True to invert channel B output
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    csr: uint32 = mmio_read(base + PWM_CH_CSR)

    csr = csr & ~(PWM_CSR_A_INV | PWM_CSR_B_INV)
    if invert_a:
        csr = csr | PWM_CSR_A_INV
    if invert_b:
        csr = csr | PWM_CSR_B_INV

    mmio_write(base + PWM_CH_CSR, csr)

# ============================================================================
# Counter Access
# ============================================================================

def pwm_get_counter(slice: uint32) -> uint32:
    """Read current counter value.

    Args:
        slice: PWM slice number (0-7)

    Returns:
        Current counter value
    """
    if slice > 7:
        return 0

    base: uint32 = _pwm_slice_base(slice)
    return mmio_read(base + PWM_CH_CTR) & 0xFFFF

def pwm_set_counter(slice: uint32, value: uint32):
    """Set counter value.

    Args:
        slice: PWM slice number (0-7)
        value: Counter value (0-65535)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    mmio_write(base + PWM_CH_CTR, value & 0xFFFF)

def pwm_advance_count(slice: uint32):
    """Advance counter by 1 cycle.

    Args:
        slice: PWM slice number (0-7)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    csr: uint32 = mmio_read(base + PWM_CH_CSR)
    mmio_write(base + PWM_CH_CSR, csr | PWM_CSR_PH_ADV)

def pwm_retard_count(slice: uint32):
    """Retard counter by 1 cycle.

    Args:
        slice: PWM slice number (0-7)
    """
    if slice > 7:
        return

    base: uint32 = _pwm_slice_base(slice)
    csr: uint32 = mmio_read(base + PWM_CH_CSR)
    mmio_write(base + PWM_CH_CSR, csr | PWM_CSR_PH_RET)

# ============================================================================
# Interrupt Functions
# ============================================================================

def pwm_clear_irq(slice: uint32):
    """Clear interrupt flag for PWM slice.

    Args:
        slice: PWM slice number (0-7)
    """
    if slice > 7:
        return

    mmio_write(PWM_BASE + PWM_INTR, 1 << slice)

def pwm_set_irq_enabled(slice: uint32, enabled: bool):
    """Enable or disable interrupt for PWM slice.

    Args:
        slice: PWM slice number (0-7)
        enabled: True to enable interrupt
    """
    if slice > 7:
        return

    inte: uint32 = mmio_read(PWM_BASE + PWM_INTE)
    if enabled:
        inte = inte | (1 << slice)
    else:
        inte = inte & ~(1 << slice)
    mmio_write(PWM_BASE + PWM_INTE, inte)

def pwm_get_irq_status() -> uint32:
    """Get interrupt status for all PWM slices.

    Returns:
        Bit mask of slices with pending interrupts
    """
    return mmio_read(PWM_BASE + PWM_INTS)

# ============================================================================
# Utility Functions
# ============================================================================

def pwm_set_duty_percent(slice: uint32, chan: uint32, wrap: uint32, percent: uint32):
    """Set duty cycle as percentage.

    Args:
        slice: PWM slice number (0-7)
        chan: Channel (PWM_CHAN_A or PWM_CHAN_B)
        wrap: Current wrap value (TOP register value)
        percent: Duty cycle percentage (0-100)
    """
    if percent > 100:
        percent = 100

    # Calculate level: level = (wrap + 1) * percent / 100
    level: uint32 = ((wrap + 1) * percent) / 100
    pwm_set_chan_level(slice, chan, level)

def pwm_calc_wrap(sys_clk: uint32, freq: uint32, clkdiv: uint32) -> uint32:
    """Calculate wrap value for desired frequency.

    PWM frequency = sys_clk / (clkdiv * (wrap + 1))
    wrap = (sys_clk / (clkdiv * freq)) - 1

    Args:
        sys_clk: System clock frequency in Hz (typically 125000000)
        freq: Desired PWM frequency in Hz
        clkdiv: Clock divider value

    Returns:
        Wrap value (clamped to 0-65535)
    """
    if freq == 0 or clkdiv == 0:
        return 65535

    wrap: uint32 = (sys_clk / (clkdiv * freq)) - 1

    if wrap > 65535:
        wrap = 65535

    return wrap
