# RP2040 ADC Hardware Abstraction Layer
#
# 12-bit SAR ADC with 5 inputs:
#   ADC0: GPIO26
#   ADC1: GPIO27
#   ADC2: GPIO28
#   ADC3: GPIO29 (used for VSYS/3 on Pico)
#   ADC4: Internal temperature sensor
#
# 500 ksps max sample rate, 3.3V reference

# ============================================================================
# Base Addresses
# ============================================================================

ADC_BASE: uint32 = 0x4004C000
IO_BANK0_BASE: uint32 = 0x40014000
PADS_BANK0_BASE: uint32 = 0x4001C000
RESETS_BASE: uint32 = 0x4000C000

# ============================================================================
# ADC Register Offsets
# ============================================================================

ADC_CS: uint32 = 0x00        # Control and status
ADC_RESULT: uint32 = 0x04    # Result register
ADC_FCS: uint32 = 0x08       # FIFO control and status
ADC_FIFO: uint32 = 0x0C      # FIFO data
ADC_DIV: uint32 = 0x10       # Clock divider
ADC_INTR: uint32 = 0x14      # Raw interrupts
ADC_INTE: uint32 = 0x18      # Interrupt enable
ADC_INTF: uint32 = 0x1C      # Interrupt force
ADC_INTS: uint32 = 0x20      # Interrupt status

# CS register bits
ADC_CS_EN: uint32 = 0x01         # Enable
ADC_CS_TS_EN: uint32 = 0x02      # Temperature sensor enable
ADC_CS_START_ONCE: uint32 = 0x04 # Start single conversion
ADC_CS_START_MANY: uint32 = 0x08 # Start free-running
ADC_CS_READY: uint32 = 0x100     # Conversion ready
ADC_CS_ERR: uint32 = 0x200       # Error (written while conversion)
ADC_CS_ERR_STICKY: uint32 = 0x400  # Sticky error
ADC_CS_AINSEL_SHIFT: uint32 = 12   # Input select shift
ADC_CS_AINSEL_MASK: uint32 = 0x07  # Input select mask
ADC_CS_RROBIN_SHIFT: uint32 = 16   # Round-robin mask shift

# FCS register bits
ADC_FCS_EN: uint32 = 0x01        # FIFO enable
ADC_FCS_SHIFT: uint32 = 0x02     # Right-shift results
ADC_FCS_ERR: uint32 = 0x04       # Error flag
ADC_FCS_DREQ_EN: uint32 = 0x08   # DMA enable
ADC_FCS_EMPTY: uint32 = 0x100    # FIFO empty
ADC_FCS_FULL: uint32 = 0x200     # FIFO full
ADC_FCS_UNDER: uint32 = 0x400    # FIFO underflow
ADC_FCS_OVER: uint32 = 0x800     # FIFO overflow
ADC_FCS_LEVEL_SHIFT: uint32 = 16 # FIFO level shift

# ============================================================================
# Constants
# ============================================================================

ADC_VREF_MV: uint32 = 3300    # 3.3V reference
ADC_MAX_VALUE: uint32 = 4095  # 12-bit

# Temperature sensor constants
# Formula: T = 27 - (ADC_voltage - 0.706) / 0.001721
# ADC_voltage = (ADC_value / 4095) * 3.3

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

# ============================================================================
# ADC Initialization
# ============================================================================

def adc_init():
    """Initialize ADC peripheral."""
    # Unreset ADC
    reset_val: uint32 = mmio_read(RESETS_BASE)
    mmio_write(RESETS_BASE, reset_val & ~(1 << 0))  # ADC reset bit

    # Wait for reset done
    timeout: int32 = 10000
    while timeout > 0:
        done: uint32 = mmio_read(RESETS_BASE + 0x08)
        if (done & (1 << 0)) != 0:
            break
        timeout = timeout - 1

    # Enable ADC
    mmio_write(ADC_BASE + ADC_CS, ADC_CS_EN)

def adc_gpio_init(gpio: uint32):
    """Configure GPIO pin for ADC input.

    Args:
        gpio: GPIO pin (26-29)
    """
    if gpio < 26 or gpio > 29:
        return

    # Disable digital input for analog pin
    # Set GPIO function to NULL (31)
    ctrl_addr: uint32 = IO_BANK0_BASE + 4 + (gpio * 8)
    mmio_write(ctrl_addr, 31)

    # Disable input buffer in pad control
    pad_addr: uint32 = PADS_BANK0_BASE + 4 + (gpio * 4)
    pad: uint32 = mmio_read(pad_addr)
    pad = pad & ~0x40  # Clear IE (input enable)
    mmio_write(pad_addr, pad)

def adc_select_input(input: uint32):
    """Select ADC input channel.

    Args:
        input: Channel 0-4 (0-3 = GPIO26-29, 4 = temp sensor)
    """
    if input > 4:
        return

    cs: uint32 = mmio_read(ADC_BASE + ADC_CS)
    cs = cs & ~(ADC_CS_AINSEL_MASK << ADC_CS_AINSEL_SHIFT)
    cs = cs | (input << ADC_CS_AINSEL_SHIFT)
    mmio_write(ADC_BASE + ADC_CS, cs)

def adc_enable_temp_sensor():
    """Enable internal temperature sensor (channel 4)."""
    cs: uint32 = mmio_read(ADC_BASE + ADC_CS)
    mmio_write(ADC_BASE + ADC_CS, cs | ADC_CS_TS_EN)

def adc_disable_temp_sensor():
    """Disable internal temperature sensor."""
    cs: uint32 = mmio_read(ADC_BASE + ADC_CS)
    mmio_write(ADC_BASE + ADC_CS, cs & ~ADC_CS_TS_EN)

# ============================================================================
# ADC Reading
# ============================================================================

def adc_read() -> uint32:
    """Start conversion and read result.

    Returns:
        12-bit ADC value (0-4095)
    """
    # Start single conversion
    cs: uint32 = mmio_read(ADC_BASE + ADC_CS)
    mmio_write(ADC_BASE + ADC_CS, cs | ADC_CS_START_ONCE)

    # Wait for conversion complete
    timeout: int32 = 10000
    while timeout > 0:
        cs = mmio_read(ADC_BASE + ADC_CS)
        if (cs & ADC_CS_READY) != 0:
            break
        timeout = timeout - 1

    return mmio_read(ADC_BASE + ADC_RESULT) & 0xFFF

def adc_read_channel(channel: uint32) -> uint32:
    """Select channel and read ADC value.

    Args:
        channel: ADC channel (0-4)

    Returns:
        12-bit ADC value
    """
    adc_select_input(channel)
    return adc_read()

def adc_read_mv(channel: uint32) -> uint32:
    """Read ADC value in millivolts.

    Args:
        channel: ADC channel (0-4)

    Returns:
        Voltage in millivolts (0-3300)
    """
    raw: uint32 = adc_read_channel(channel)
    return (raw * ADC_VREF_MV) / ADC_MAX_VALUE

def adc_read_temp_c() -> int32:
    """Read temperature sensor in degrees Celsius.

    Returns:
        Temperature in degrees C (typically 20-50)
    """
    # Enable temp sensor
    adc_enable_temp_sensor()

    # Read temperature channel (4)
    raw: uint32 = adc_read_channel(4)

    # Convert to voltage: V = raw * 3.3 / 4095
    # Using millivolts: mV = raw * 3300 / 4095
    mv: uint32 = (raw * 3300) / 4095

    # Convert to temperature: T = 27 - (V - 0.706) / 0.001721
    # In millivolts: T = 27 - (mV - 706) / 1.721
    # Multiply by 1000 for fixed point: T = 27000 - (mV - 706) * 1000 / 1721
    temp_milli: int32 = 27000 - (cast[int32](mv) - 706) * 1000 / 1721

    return temp_milli / 1000

def adc_read_temp_mc() -> int32:
    """Read temperature sensor in millidegrees Celsius.

    Returns:
        Temperature in millidegrees C (e.g., 25000 = 25.0°C)
    """
    adc_enable_temp_sensor()
    raw: uint32 = adc_read_channel(4)
    mv: uint32 = (raw * 3300) / 4095
    temp_milli: int32 = 27000 - (cast[int32](mv) - 706) * 1000 / 1721
    return temp_milli

# ============================================================================
# Free-Running Mode
# ============================================================================

def adc_run_once():
    """Start single conversion (non-blocking)."""
    cs: uint32 = mmio_read(ADC_BASE + ADC_CS)
    mmio_write(ADC_BASE + ADC_CS, cs | ADC_CS_START_ONCE)

def adc_run_start():
    """Start free-running mode."""
    cs: uint32 = mmio_read(ADC_BASE + ADC_CS)
    mmio_write(ADC_BASE + ADC_CS, cs | ADC_CS_START_MANY)

def adc_run_stop():
    """Stop free-running mode."""
    cs: uint32 = mmio_read(ADC_BASE + ADC_CS)
    mmio_write(ADC_BASE + ADC_CS, cs & ~ADC_CS_START_MANY)

def adc_is_ready() -> bool:
    """Check if conversion is complete.

    Returns:
        True if result is ready
    """
    cs: uint32 = mmio_read(ADC_BASE + ADC_CS)
    return (cs & ADC_CS_READY) != 0

def adc_get_result() -> uint32:
    """Get last conversion result.

    Returns:
        12-bit ADC value
    """
    return mmio_read(ADC_BASE + ADC_RESULT) & 0xFFF

# ============================================================================
# FIFO Mode
# ============================================================================

def adc_fifo_setup(en: bool, dreq_en: bool, thresh: uint32, shift: bool):
    """Configure ADC FIFO.

    Args:
        en: Enable FIFO
        dreq_en: Enable DMA requests
        thresh: FIFO threshold (0-15)
        shift: Right-shift results to 8-bit
    """
    fcs: uint32 = 0
    if en:
        fcs = fcs | ADC_FCS_EN
    if dreq_en:
        fcs = fcs | ADC_FCS_DREQ_EN
    if shift:
        fcs = fcs | ADC_FCS_SHIFT
    fcs = fcs | (thresh << 24)  # THRESH field

    mmio_write(ADC_BASE + ADC_FCS, fcs)

def adc_fifo_drain():
    """Drain ADC FIFO."""
    while True:
        fcs: uint32 = mmio_read(ADC_BASE + ADC_FCS)
        if (fcs & ADC_FCS_EMPTY) != 0:
            break
        dummy: uint32 = mmio_read(ADC_BASE + ADC_FIFO)

def adc_fifo_get_level() -> uint32:
    """Get number of samples in FIFO.

    Returns:
        FIFO level (0-4)
    """
    fcs: uint32 = mmio_read(ADC_BASE + ADC_FCS)
    return (fcs >> ADC_FCS_LEVEL_SHIFT) & 0x0F

def adc_fifo_get() -> uint32:
    """Read sample from FIFO.

    Returns:
        ADC sample
    """
    return mmio_read(ADC_BASE + ADC_FIFO) & 0xFFF

def adc_set_clkdiv(div: uint32):
    """Set ADC clock divider.

    Args:
        div: Divider value (48MHz / div = sample rate)
    """
    mmio_write(ADC_BASE + ADC_DIV, div << 8)
