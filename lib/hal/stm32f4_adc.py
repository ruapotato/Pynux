# STM32F4 ADC Hardware Abstraction Layer
#
# 12-bit ADC with up to 16 external channels + 3 internal:
#   ADC channels 0-15: External pins
#   Channel 16: Internal temperature sensor
#   Channel 17: VREFINT (internal reference)
#   Channel 18: VBAT (battery voltage / 2)
#
# ADC1, ADC2, ADC3 share the same pin mappings
# Max 2.4 MSPS sample rate at 12-bit resolution

# ============================================================================
# Base Addresses
# ============================================================================

ADC1_BASE: uint32 = 0x40012000
ADC2_BASE: uint32 = 0x40012100
ADC3_BASE: uint32 = 0x40012200
ADC_COMMON_BASE: uint32 = 0x40012300

RCC_BASE: uint32 = 0x40023800
GPIOA_BASE: uint32 = 0x40020000
GPIOB_BASE: uint32 = 0x40020400
GPIOC_BASE: uint32 = 0x40020800

# ============================================================================
# ADC Register Offsets
# ============================================================================

ADC_SR: uint32 = 0x00       # Status register
ADC_CR1: uint32 = 0x04      # Control register 1
ADC_CR2: uint32 = 0x08      # Control register 2
ADC_SMPR1: uint32 = 0x0C    # Sample time register 1 (channels 10-18)
ADC_SMPR2: uint32 = 0x10    # Sample time register 2 (channels 0-9)
ADC_JOFR1: uint32 = 0x14    # Injected offset 1
ADC_HTR: uint32 = 0x24      # Watchdog high threshold
ADC_LTR: uint32 = 0x28      # Watchdog low threshold
ADC_SQR1: uint32 = 0x2C     # Regular sequence 1 (13-16)
ADC_SQR2: uint32 = 0x30     # Regular sequence 2 (7-12)
ADC_SQR3: uint32 = 0x34     # Regular sequence 3 (1-6)
ADC_JSQR: uint32 = 0x38     # Injected sequence
ADC_JDR1: uint32 = 0x3C     # Injected data 1
ADC_DR: uint32 = 0x4C       # Regular data

# Common registers
ADC_CCR: uint32 = 0x04      # Common control register

# SR bits
ADC_SR_AWD: uint32 = 0x01   # Analog watchdog
ADC_SR_EOC: uint32 = 0x02   # End of conversion
ADC_SR_JEOC: uint32 = 0x04  # Injected end of conversion
ADC_SR_JSTRT: uint32 = 0x08 # Injected start
ADC_SR_STRT: uint32 = 0x10  # Regular start
ADC_SR_OVR: uint32 = 0x20   # Overrun

# CR1 bits
ADC_CR1_AWDCH_MASK: uint32 = 0x1F     # Watchdog channel
ADC_CR1_EOCIE: uint32 = 0x20          # EOC interrupt enable
ADC_CR1_AWDIE: uint32 = 0x40          # AWD interrupt enable
ADC_CR1_JEOCIE: uint32 = 0x80         # JEOC interrupt enable
ADC_CR1_SCAN: uint32 = 0x100          # Scan mode
ADC_CR1_AWDSGL: uint32 = 0x200        # Watchdog on single channel
ADC_CR1_JAUTO: uint32 = 0x400         # Automatic injected
ADC_CR1_DISCEN: uint32 = 0x800        # Discontinuous mode
ADC_CR1_JDISCEN: uint32 = 0x1000      # Injected discontinuous
ADC_CR1_DISCNUM_SHIFT: uint32 = 13    # Discontinuous count
ADC_CR1_JAWDEN: uint32 = 0x400000     # Injected AWD enable
ADC_CR1_AWDEN: uint32 = 0x800000      # Regular AWD enable
ADC_CR1_RES_12: uint32 = 0x00000000   # 12-bit resolution
ADC_CR1_RES_10: uint32 = 0x01000000   # 10-bit resolution
ADC_CR1_RES_8: uint32 = 0x02000000    # 8-bit resolution
ADC_CR1_RES_6: uint32 = 0x03000000    # 6-bit resolution
ADC_CR1_OVRIE: uint32 = 0x04000000    # Overrun interrupt enable

# CR2 bits
ADC_CR2_ADON: uint32 = 0x01           # ADC enable
ADC_CR2_CONT: uint32 = 0x02           # Continuous conversion
ADC_CR2_DMA: uint32 = 0x100           # DMA enable
ADC_CR2_DDS: uint32 = 0x200           # DMA disable selection
ADC_CR2_EOCS: uint32 = 0x400          # EOC selection
ADC_CR2_ALIGN: uint32 = 0x800         # Data alignment (1=left)
ADC_CR2_JEXTSEL_SHIFT: uint32 = 16    # Injected external trigger
ADC_CR2_JEXTEN_SHIFT: uint32 = 20     # Injected trigger enable
ADC_CR2_JSWSTART: uint32 = 0x400000   # Injected start
ADC_CR2_EXTSEL_SHIFT: uint32 = 24     # Regular external trigger
ADC_CR2_EXTEN_SHIFT: uint32 = 28      # Regular trigger enable
ADC_CR2_SWSTART: uint32 = 0x40000000  # Regular start

# CCR bits
ADC_CCR_ADCPRE_DIV2: uint32 = 0x00000000   # ADC prescaler /2
ADC_CCR_ADCPRE_DIV4: uint32 = 0x00010000   # ADC prescaler /4
ADC_CCR_ADCPRE_DIV6: uint32 = 0x00020000   # ADC prescaler /6
ADC_CCR_ADCPRE_DIV8: uint32 = 0x00030000   # ADC prescaler /8
ADC_CCR_VBATE: uint32 = 0x00400000         # VBAT enable
ADC_CCR_TSVREFE: uint32 = 0x00800000       # Temp sensor/VREF enable

# Sample time values (3 bits per channel)
ADC_SMPR_3: uint32 = 0      # 3 cycles
ADC_SMPR_15: uint32 = 1     # 15 cycles
ADC_SMPR_28: uint32 = 2     # 28 cycles
ADC_SMPR_56: uint32 = 3     # 56 cycles
ADC_SMPR_84: uint32 = 4     # 84 cycles
ADC_SMPR_112: uint32 = 5    # 112 cycles
ADC_SMPR_144: uint32 = 6    # 144 cycles
ADC_SMPR_480: uint32 = 7    # 480 cycles

# RCC register offsets
RCC_AHB1ENR: uint32 = 0x30
RCC_APB2ENR: uint32 = 0x44

# GPIO register offsets
GPIO_MODER: uint32 = 0x00
GPIO_PUPDR: uint32 = 0x0C

# ============================================================================
# Constants
# ============================================================================

ADC_VREF_MV: uint32 = 3300
ADC_MAX_12BIT: uint32 = 4095
ADC_MAX_10BIT: uint32 = 1023
ADC_MAX_8BIT: uint32 = 255

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _adc_base(adc: uint32) -> uint32:
    if adc == 1:
        return ADC1_BASE
    elif adc == 2:
        return ADC2_BASE
    return ADC3_BASE

# ============================================================================
# Clock Enable
# ============================================================================

def adc_enable_clock(adc: uint32):
    """Enable clock for ADC peripheral.

    Args:
        adc: ADC number (1-3)
    """
    val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
    if adc == 1:
        mmio_write(RCC_BASE + RCC_APB2ENR, val | (1 << 8))
    elif adc == 2:
        mmio_write(RCC_BASE + RCC_APB2ENR, val | (1 << 9))
    elif adc == 3:
        mmio_write(RCC_BASE + RCC_APB2ENR, val | (1 << 10))

# ============================================================================
# ADC Initialization
# ============================================================================

def adc_init(adc: uint32):
    """Initialize ADC in single-conversion mode.

    Args:
        adc: ADC number (1-3)
    """
    base: uint32 = _adc_base(adc)

    # Enable ADC clock
    adc_enable_clock(adc)

    # Set ADC prescaler (APB2/4 = 84MHz/4 = 21MHz)
    mmio_write(ADC_COMMON_BASE + ADC_CCR, ADC_CCR_ADCPRE_DIV4)

    # Disable ADC during configuration
    mmio_write(base + ADC_CR2, 0)

    # Configure CR1: 12-bit resolution
    mmio_write(base + ADC_CR1, ADC_CR1_RES_12)

    # Configure CR2: right-aligned, single conversion
    mmio_write(base + ADC_CR2, ADC_CR2_ADON)

    # Set sample time to 84 cycles for all channels
    mmio_write(base + ADC_SMPR1, 0x24924924)  # Channels 10-18
    mmio_write(base + ADC_SMPR2, 0x24924924)  # Channels 0-9

def adc_gpio_init(port: uint32, pin: uint32):
    """Configure GPIO pin for ADC (analog mode).

    Args:
        port: GPIO port base address
        pin: Pin number (0-15)
    """
    # Enable GPIO clock (assuming AHB1)
    # Set pin to analog mode (MODER = 11)
    moder: uint32 = mmio_read(port + GPIO_MODER)
    moder = moder | (3 << (pin * 2))
    mmio_write(port + GPIO_MODER, moder)

    # Disable pull-up/pull-down
    pupdr: uint32 = mmio_read(port + GPIO_PUPDR)
    pupdr = pupdr & ~(3 << (pin * 2))
    mmio_write(port + GPIO_PUPDR, pupdr)

def adc_enable_temp_vref():
    """Enable internal temperature sensor and VREF."""
    ccr: uint32 = mmio_read(ADC_COMMON_BASE + ADC_CCR)
    mmio_write(ADC_COMMON_BASE + ADC_CCR, ccr | ADC_CCR_TSVREFE)

def adc_enable_vbat():
    """Enable VBAT measurement (channel 18)."""
    ccr: uint32 = mmio_read(ADC_COMMON_BASE + ADC_CCR)
    mmio_write(ADC_COMMON_BASE + ADC_CCR, ccr | ADC_CCR_VBATE)

# ============================================================================
# ADC Channel Configuration
# ============================================================================

def adc_set_sample_time(adc: uint32, channel: uint32, sample_time: uint32):
    """Set sample time for channel.

    Args:
        adc: ADC number (1-3)
        channel: Channel number (0-18)
        sample_time: ADC_SMPR_* value
    """
    base: uint32 = _adc_base(adc)

    if channel < 10:
        # SMPR2 for channels 0-9
        offset: uint32 = channel * 3
        smpr: uint32 = mmio_read(base + ADC_SMPR2)
        smpr = smpr & ~(7 << offset)
        smpr = smpr | (sample_time << offset)
        mmio_write(base + ADC_SMPR2, smpr)
    else:
        # SMPR1 for channels 10-18
        offset: uint32 = (channel - 10) * 3
        smpr: uint32 = mmio_read(base + ADC_SMPR1)
        smpr = smpr & ~(7 << offset)
        smpr = smpr | (sample_time << offset)
        mmio_write(base + ADC_SMPR1, smpr)

# ============================================================================
# ADC Reading
# ============================================================================

def adc_read(adc: uint32, channel: uint32) -> uint32:
    """Read single channel.

    Args:
        adc: ADC number (1-3)
        channel: Channel number (0-18)

    Returns:
        12-bit ADC value
    """
    base: uint32 = _adc_base(adc)

    # Set channel in sequence register (single conversion)
    mmio_write(base + ADC_SQR1, 0)  # 1 conversion
    mmio_write(base + ADC_SQR3, channel)

    # Start conversion
    cr2: uint32 = mmio_read(base + ADC_CR2)
    mmio_write(base + ADC_CR2, cr2 | ADC_CR2_SWSTART)

    # Wait for end of conversion
    timeout: int32 = 100000
    while timeout > 0:
        sr: uint32 = mmio_read(base + ADC_SR)
        if (sr & ADC_SR_EOC) != 0:
            break
        timeout = timeout - 1

    # Read result
    return mmio_read(base + ADC_DR) & 0xFFF

def adc_read_mv(adc: uint32, channel: uint32) -> uint32:
    """Read channel in millivolts.

    Args:
        adc: ADC number (1-3)
        channel: Channel number

    Returns:
        Voltage in millivolts
    """
    raw: uint32 = adc_read(adc, channel)
    return (raw * ADC_VREF_MV) / ADC_MAX_12BIT

def adc_read_temp_c() -> int32:
    """Read internal temperature sensor in degrees Celsius.

    Returns:
        Temperature in degrees C
    """
    # Enable temp sensor
    adc_enable_temp_vref()

    # Wait for sensor to stabilize
    delay: int32 = 1000
    while delay > 0:
        delay = delay - 1

    # Read channel 16 (temp sensor) with long sample time
    adc_set_sample_time(1, 16, ADC_SMPR_480)
    raw: uint32 = adc_read(1, 16)

    # Convert using formula from datasheet:
    # Temp = (V_SENSE - V_25) / Avg_Slope + 25
    # V_25 = 0.76V, Avg_Slope = 2.5mV/°C
    # Using mV: Temp = (mV - 760) * 10 / 25 + 25
    mv: uint32 = (raw * ADC_VREF_MV) / ADC_MAX_12BIT

    return ((cast[int32](mv) - 760) * 10) / 25 + 25

def adc_read_temp_mc() -> int32:
    """Read temperature in millidegrees Celsius.

    Returns:
        Temperature in millidegrees C
    """
    adc_enable_temp_vref()

    delay: int32 = 1000
    while delay > 0:
        delay = delay - 1

    adc_set_sample_time(1, 16, ADC_SMPR_480)
    raw: uint32 = adc_read(1, 16)

    mv: uint32 = (raw * ADC_VREF_MV) / ADC_MAX_12BIT

    # millidegrees = (mV - 760) * 10000 / 25 + 25000
    return ((cast[int32](mv) - 760) * 10000) / 25 + 25000

def adc_read_vref_mv() -> uint32:
    """Read internal reference voltage.

    Can be used to calibrate for actual Vdd.

    Returns:
        VREFINT in millivolts (should be ~1.2V)
    """
    adc_enable_temp_vref()

    delay: int32 = 1000
    while delay > 0:
        delay = delay - 1

    raw: uint32 = adc_read(1, 17)
    return (raw * ADC_VREF_MV) / ADC_MAX_12BIT

def adc_read_vbat_mv() -> uint32:
    """Read battery voltage (VBAT/2).

    Returns:
        VBAT in millivolts
    """
    adc_enable_vbat()
    raw: uint32 = adc_read(1, 18)
    # VBAT is divided by 2 internally
    return ((raw * ADC_VREF_MV) / ADC_MAX_12BIT) * 2

# ============================================================================
# Continuous Mode
# ============================================================================

def adc_start_continuous(adc: uint32, channel: uint32):
    """Start continuous conversion on channel.

    Args:
        adc: ADC number (1-3)
        channel: Channel number
    """
    base: uint32 = _adc_base(adc)

    mmio_write(base + ADC_SQR1, 0)
    mmio_write(base + ADC_SQR3, channel)

    cr2: uint32 = mmio_read(base + ADC_CR2)
    cr2 = cr2 | ADC_CR2_CONT | ADC_CR2_SWSTART
    mmio_write(base + ADC_CR2, cr2)

def adc_stop_continuous(adc: uint32):
    """Stop continuous conversion.

    Args:
        adc: ADC number (1-3)
    """
    base: uint32 = _adc_base(adc)
    cr2: uint32 = mmio_read(base + ADC_CR2)
    mmio_write(base + ADC_CR2, cr2 & ~ADC_CR2_CONT)

def adc_is_ready(adc: uint32) -> bool:
    """Check if conversion is complete.

    Args:
        adc: ADC number (1-3)

    Returns:
        True if EOC is set
    """
    base: uint32 = _adc_base(adc)
    sr: uint32 = mmio_read(base + ADC_SR)
    return (sr & ADC_SR_EOC) != 0

def adc_get_result(adc: uint32) -> uint32:
    """Get last conversion result.

    Args:
        adc: ADC number (1-3)

    Returns:
        ADC value
    """
    base: uint32 = _adc_base(adc)
    return mmio_read(base + ADC_DR) & 0xFFF
