# STM32F4 PWM Hardware Abstraction Layer
#
# PWM driver for STM32F405/F407 using general-purpose and advanced timers.
# Supports TIM1-TIM14 for PWM generation with configurable frequency and duty.
#
# Timer Types:
#   TIM1, TIM8     - Advanced timers (complementary outputs, break, etc.)
#   TIM2, TIM3, TIM4, TIM5 - General purpose (32-bit for TIM2/TIM5)
#   TIM9, TIM10, TIM11, TIM12, TIM13, TIM14 - Basic timers
#
# Timer Clocks:
#   APB1 timers (TIM2-7, TIM12-14): 84 MHz (2x APB1 when APB1 prescaler > 1)
#   APB2 timers (TIM1, TIM8-11): 168 MHz (2x APB2 when APB2 prescaler > 1)
#
# Common GPIO AF mappings for PWM:
#   TIM1/TIM2: AF1
#   TIM3/TIM4/TIM5: AF2
#   TIM8/TIM9/TIM10/TIM11: AF3
#   TIM12/TIM13/TIM14: AF9

# ============================================================================
# Base Addresses
# ============================================================================

TIM1_BASE: uint32 = 0x40010000   # APB2
TIM2_BASE: uint32 = 0x40000000   # APB1
TIM3_BASE: uint32 = 0x40000400   # APB1
TIM4_BASE: uint32 = 0x40000800   # APB1
TIM5_BASE: uint32 = 0x40000C00   # APB1
TIM6_BASE: uint32 = 0x40001000   # APB1 (basic, no PWM)
TIM7_BASE: uint32 = 0x40001400   # APB1 (basic, no PWM)
TIM8_BASE: uint32 = 0x40010400   # APB2
TIM9_BASE: uint32 = 0x40014000   # APB2
TIM10_BASE: uint32 = 0x40014400  # APB2
TIM11_BASE: uint32 = 0x40014800  # APB2
TIM12_BASE: uint32 = 0x40001800  # APB1
TIM13_BASE: uint32 = 0x40001C00  # APB1
TIM14_BASE: uint32 = 0x40002000  # APB1

RCC_BASE: uint32 = 0x40023800
GPIOA_BASE: uint32 = 0x40020000
GPIOB_BASE: uint32 = 0x40020400
GPIOC_BASE: uint32 = 0x40020800
GPIOD_BASE: uint32 = 0x40020C00
GPIOE_BASE: uint32 = 0x40021000

# ============================================================================
# Timer Register Offsets
# ============================================================================

TIM_CR1: uint32 = 0x00       # Control register 1
TIM_CR2: uint32 = 0x04       # Control register 2
TIM_SMCR: uint32 = 0x08      # Slave mode control
TIM_DIER: uint32 = 0x0C      # DMA/interrupt enable
TIM_SR: uint32 = 0x10        # Status register
TIM_EGR: uint32 = 0x14       # Event generation
TIM_CCMR1: uint32 = 0x18     # Capture/compare mode 1 (CH1, CH2)
TIM_CCMR2: uint32 = 0x1C     # Capture/compare mode 2 (CH3, CH4)
TIM_CCER: uint32 = 0x20      # Capture/compare enable
TIM_CNT: uint32 = 0x24       # Counter
TIM_PSC: uint32 = 0x28       # Prescaler
TIM_ARR: uint32 = 0x2C       # Auto-reload register (period)
TIM_RCR: uint32 = 0x30       # Repetition counter (TIM1/TIM8 only)
TIM_CCR1: uint32 = 0x34      # Capture/compare register 1
TIM_CCR2: uint32 = 0x38      # Capture/compare register 2
TIM_CCR3: uint32 = 0x3C      # Capture/compare register 3
TIM_CCR4: uint32 = 0x40      # Capture/compare register 4
TIM_BDTR: uint32 = 0x44      # Break and dead-time (TIM1/TIM8 only)
TIM_DCR: uint32 = 0x48       # DMA control register
TIM_DMAR: uint32 = 0x4C      # DMA address for full transfer

# ============================================================================
# CR1 (Control Register 1) Bits
# ============================================================================

TIM_CR1_CEN: uint32 = 0x0001     # Counter enable
TIM_CR1_UDIS: uint32 = 0x0002    # Update disable
TIM_CR1_URS: uint32 = 0x0004     # Update request source
TIM_CR1_OPM: uint32 = 0x0008     # One-pulse mode
TIM_CR1_DIR: uint32 = 0x0010     # Direction (0=up, 1=down)
TIM_CR1_CMS_EDGE: uint32 = 0x0000     # Edge-aligned mode
TIM_CR1_CMS_CENTER1: uint32 = 0x0020  # Center-aligned mode 1
TIM_CR1_CMS_CENTER2: uint32 = 0x0040  # Center-aligned mode 2
TIM_CR1_CMS_CENTER3: uint32 = 0x0060  # Center-aligned mode 3
TIM_CR1_ARPE: uint32 = 0x0080    # Auto-reload preload enable
TIM_CR1_CKD_1: uint32 = 0x0000   # Clock division = 1
TIM_CR1_CKD_2: uint32 = 0x0100   # Clock division = 2
TIM_CR1_CKD_4: uint32 = 0x0200   # Clock division = 4

# ============================================================================
# CCMR (Capture/Compare Mode Register) Bits
# ============================================================================

# Output compare mode (bits 6:4 for CH1/CH3, bits 14:12 for CH2/CH4)
TIM_CCMR_OCM_FROZEN: uint32 = 0x00     # Frozen
TIM_CCMR_OCM_ACTIVE: uint32 = 0x10     # Active on match
TIM_CCMR_OCM_INACTIVE: uint32 = 0x20   # Inactive on match
TIM_CCMR_OCM_TOGGLE: uint32 = 0x30     # Toggle on match
TIM_CCMR_OCM_FORCE_LOW: uint32 = 0x40  # Force inactive
TIM_CCMR_OCM_FORCE_HIGH: uint32 = 0x50 # Force active
TIM_CCMR_OCM_PWM1: uint32 = 0x60       # PWM mode 1
TIM_CCMR_OCM_PWM2: uint32 = 0x70       # PWM mode 2

TIM_CCMR_OC1PE: uint32 = 0x0008   # Output compare 1 preload enable
TIM_CCMR_OC1FE: uint32 = 0x0004   # Output compare 1 fast enable
TIM_CCMR_OC2PE: uint32 = 0x0800   # Output compare 2 preload enable
TIM_CCMR_OC2FE: uint32 = 0x0400   # Output compare 2 fast enable

# Shift values for channel modes in CCMR registers
TIM_CCMR_OC1M_SHIFT: uint32 = 4
TIM_CCMR_OC2M_SHIFT: uint32 = 12

# ============================================================================
# CCER (Capture/Compare Enable Register) Bits
# ============================================================================

TIM_CCER_CC1E: uint32 = 0x0001   # Capture/Compare 1 output enable
TIM_CCER_CC1P: uint32 = 0x0002   # Capture/Compare 1 output polarity
TIM_CCER_CC1NE: uint32 = 0x0004  # Capture/Compare 1 complementary enable
TIM_CCER_CC1NP: uint32 = 0x0008  # Capture/Compare 1 complementary polarity
TIM_CCER_CC2E: uint32 = 0x0010   # Capture/Compare 2 output enable
TIM_CCER_CC2P: uint32 = 0x0020   # Capture/Compare 2 output polarity
TIM_CCER_CC2NE: uint32 = 0x0040  # Capture/Compare 2 complementary enable
TIM_CCER_CC2NP: uint32 = 0x0080  # Capture/Compare 2 complementary polarity
TIM_CCER_CC3E: uint32 = 0x0100   # Capture/Compare 3 output enable
TIM_CCER_CC3P: uint32 = 0x0200   # Capture/Compare 3 output polarity
TIM_CCER_CC3NE: uint32 = 0x0400  # Capture/Compare 3 complementary enable
TIM_CCER_CC3NP: uint32 = 0x0800  # Capture/Compare 3 complementary polarity
TIM_CCER_CC4E: uint32 = 0x1000   # Capture/Compare 4 output enable
TIM_CCER_CC4P: uint32 = 0x2000   # Capture/Compare 4 output polarity

# ============================================================================
# BDTR (Break and Dead-Time Register) Bits - TIM1/TIM8 only
# ============================================================================

TIM_BDTR_MOE: uint32 = 0x8000    # Main output enable
TIM_BDTR_AOE: uint32 = 0x4000    # Automatic output enable
TIM_BDTR_BKP: uint32 = 0x2000    # Break polarity
TIM_BDTR_BKE: uint32 = 0x1000    # Break enable
TIM_BDTR_OSSR: uint32 = 0x0800   # Off-state selection run mode
TIM_BDTR_OSSI: uint32 = 0x0400   # Off-state selection idle mode

# ============================================================================
# RCC Register Offsets
# ============================================================================

RCC_AHB1ENR: uint32 = 0x30
RCC_APB1ENR: uint32 = 0x40
RCC_APB2ENR: uint32 = 0x44

# Timer clock enable bits
RCC_APB2ENR_TIM1EN: uint32 = 0x0001
RCC_APB2ENR_TIM8EN: uint32 = 0x0002
RCC_APB2ENR_TIM9EN: uint32 = 0x10000
RCC_APB2ENR_TIM10EN: uint32 = 0x20000
RCC_APB2ENR_TIM11EN: uint32 = 0x40000

RCC_APB1ENR_TIM2EN: uint32 = 0x0001
RCC_APB1ENR_TIM3EN: uint32 = 0x0002
RCC_APB1ENR_TIM4EN: uint32 = 0x0004
RCC_APB1ENR_TIM5EN: uint32 = 0x0008
RCC_APB1ENR_TIM6EN: uint32 = 0x0010
RCC_APB1ENR_TIM7EN: uint32 = 0x0020
RCC_APB1ENR_TIM12EN: uint32 = 0x0040
RCC_APB1ENR_TIM13EN: uint32 = 0x0080
RCC_APB1ENR_TIM14EN: uint32 = 0x0100

# ============================================================================
# GPIO Configuration
# ============================================================================

GPIO_MODER: uint32 = 0x00
GPIO_OTYPER: uint32 = 0x04
GPIO_OSPEEDR: uint32 = 0x08
GPIO_PUPDR: uint32 = 0x0C
GPIO_AFRL: uint32 = 0x20
GPIO_AFRH: uint32 = 0x24

GPIO_MODE_AF: uint32 = 2
GPIO_SPEED_HIGH: uint32 = 3
GPIO_OTYPE_PP: uint32 = 0
GPIO_PULL_NONE: uint32 = 0

# Alternate function numbers for timers
AF_TIM1_TIM2: uint32 = 1
AF_TIM3_TIM4_TIM5: uint32 = 2
AF_TIM8_TIM9_TIM10_TIM11: uint32 = 3
AF_TIM12_TIM13_TIM14: uint32 = 9

# ============================================================================
# Clock Configuration
# ============================================================================

APB1_TIMER_CLOCK: uint32 = 84000000   # 84 MHz (APB1 clock x2)
APB2_TIMER_CLOCK: uint32 = 168000000  # 168 MHz (APB2 clock x2)

# ============================================================================
# Channel Definitions
# ============================================================================

PWM_CHANNEL_1: uint32 = 1
PWM_CHANNEL_2: uint32 = 2
PWM_CHANNEL_3: uint32 = 3
PWM_CHANNEL_4: uint32 = 4

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

# Timer lookup tables
_tim_bases: Array[14, uint32]
_tim_clocks: Array[14, uint32]
_tim_initialized: bool = False

def _init_tim_tables():
    """Initialize timer lookup tables."""
    global _tim_initialized
    if _tim_initialized:
        return

    _tim_bases[0] = TIM1_BASE
    _tim_bases[1] = TIM2_BASE
    _tim_bases[2] = TIM3_BASE
    _tim_bases[3] = TIM4_BASE
    _tim_bases[4] = TIM5_BASE
    _tim_bases[5] = TIM6_BASE
    _tim_bases[6] = TIM7_BASE
    _tim_bases[7] = TIM8_BASE
    _tim_bases[8] = TIM9_BASE
    _tim_bases[9] = TIM10_BASE
    _tim_bases[10] = TIM11_BASE
    _tim_bases[11] = TIM12_BASE
    _tim_bases[12] = TIM13_BASE
    _tim_bases[13] = TIM14_BASE

    _tim_clocks[0] = APB2_TIMER_CLOCK   # TIM1
    _tim_clocks[1] = APB1_TIMER_CLOCK   # TIM2
    _tim_clocks[2] = APB1_TIMER_CLOCK   # TIM3
    _tim_clocks[3] = APB1_TIMER_CLOCK   # TIM4
    _tim_clocks[4] = APB1_TIMER_CLOCK   # TIM5
    _tim_clocks[5] = APB1_TIMER_CLOCK   # TIM6
    _tim_clocks[6] = APB1_TIMER_CLOCK   # TIM7
    _tim_clocks[7] = APB2_TIMER_CLOCK   # TIM8
    _tim_clocks[8] = APB2_TIMER_CLOCK   # TIM9
    _tim_clocks[9] = APB2_TIMER_CLOCK   # TIM10
    _tim_clocks[10] = APB2_TIMER_CLOCK  # TIM11
    _tim_clocks[11] = APB1_TIMER_CLOCK  # TIM12
    _tim_clocks[12] = APB1_TIMER_CLOCK  # TIM13
    _tim_clocks[13] = APB1_TIMER_CLOCK  # TIM14

    _tim_initialized = True

def _tim_base(timer: uint32) -> uint32:
    """Get base address for timer (1-14)."""
    _init_tim_tables()
    if timer < 1 or timer > 14:
        return TIM1_BASE
    return _tim_bases[timer - 1]

def _tim_clock(timer: uint32) -> uint32:
    """Get timer clock frequency."""
    _init_tim_tables()
    if timer < 1 or timer > 14:
        return APB2_TIMER_CLOCK
    return _tim_clocks[timer - 1]

def _tim_is_advanced(timer: uint32) -> bool:
    """Check if timer is an advanced timer (TIM1 or TIM8)."""
    return timer == 1 or timer == 8

def _tim_is_32bit(timer: uint32) -> bool:
    """Check if timer is 32-bit (TIM2 or TIM5)."""
    return timer == 2 or timer == 5

def _ccr_offset(channel: uint32) -> uint32:
    """Get CCRx register offset for channel."""
    if channel == 1:
        return TIM_CCR1
    elif channel == 2:
        return TIM_CCR2
    elif channel == 3:
        return TIM_CCR3
    else:
        return TIM_CCR4

# ============================================================================
# Clock Enable Functions
# ============================================================================

def pwm_enable_clock(timer: uint32):
    """Enable clock for timer peripheral.

    Args:
        timer: Timer number (1-14)
    """
    if timer == 1:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | RCC_APB2ENR_TIM1EN)
    elif timer == 2:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_APB1ENR_TIM2EN)
    elif timer == 3:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_APB1ENR_TIM3EN)
    elif timer == 4:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_APB1ENR_TIM4EN)
    elif timer == 5:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_APB1ENR_TIM5EN)
    elif timer == 8:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | RCC_APB2ENR_TIM8EN)
    elif timer == 9:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | RCC_APB2ENR_TIM9EN)
    elif timer == 10:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | RCC_APB2ENR_TIM10EN)
    elif timer == 11:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | RCC_APB2ENR_TIM11EN)
    elif timer == 12:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_APB1ENR_TIM12EN)
    elif timer == 13:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_APB1ENR_TIM13EN)
    elif timer == 14:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_APB1ENR_TIM14EN)

# ============================================================================
# GPIO Configuration for PWM Output
# ============================================================================

def pwm_init_gpio(port_base: uint32, pin: uint32, af: uint32):
    """Configure GPIO pin for timer PWM output.

    Args:
        port_base: GPIO port base address (e.g., GPIOA_BASE)
        pin: Pin number (0-15)
        af: Alternate function number (1-3 or 9 depending on timer)
    """
    if pin > 15:
        return

    # Set mode to alternate function
    moder: uint32 = mmio_read(port_base + GPIO_MODER)
    moder = moder & ~(3 << (pin * 2))
    moder = moder | (GPIO_MODE_AF << (pin * 2))
    mmio_write(port_base + GPIO_MODER, moder)

    # Set high speed
    ospeedr: uint32 = mmio_read(port_base + GPIO_OSPEEDR)
    ospeedr = ospeedr & ~(3 << (pin * 2))
    ospeedr = ospeedr | (GPIO_SPEED_HIGH << (pin * 2))
    mmio_write(port_base + GPIO_OSPEEDR, ospeedr)

    # Set push-pull output type
    otyper: uint32 = mmio_read(port_base + GPIO_OTYPER)
    otyper = otyper & ~(1 << pin)
    mmio_write(port_base + GPIO_OTYPER, otyper)

    # No pull-up/pull-down
    pupdr: uint32 = mmio_read(port_base + GPIO_PUPDR)
    pupdr = pupdr & ~(3 << (pin * 2))
    mmio_write(port_base + GPIO_PUPDR, pupdr)

    # Set alternate function
    if pin < 8:
        afr: uint32 = mmio_read(port_base + GPIO_AFRL)
        afr = afr & ~(0xF << (pin * 4))
        afr = afr | ((af & 0xF) << (pin * 4))
        mmio_write(port_base + GPIO_AFRL, afr)
    else:
        afr: uint32 = mmio_read(port_base + GPIO_AFRH)
        afr = afr & ~(0xF << ((pin - 8) * 4))
        afr = afr | ((af & 0xF) << ((pin - 8) * 4))
        mmio_write(port_base + GPIO_AFRH, afr)

def pwm_get_timer_af(timer: uint32) -> uint32:
    """Get the alternate function number for a timer.

    Args:
        timer: Timer number (1-14)

    Returns:
        Alternate function number
    """
    if timer == 1 or timer == 2:
        return AF_TIM1_TIM2
    elif timer == 3 or timer == 4 or timer == 5:
        return AF_TIM3_TIM4_TIM5
    elif timer == 8 or timer == 9 or timer == 10 or timer == 11:
        return AF_TIM8_TIM9_TIM10_TIM11
    else:
        return AF_TIM12_TIM13_TIM14

# ============================================================================
# PWM Initialization
# ============================================================================

def pwm_init(timer: uint32, channel: uint32, freq: uint32, duty: uint32):
    """Initialize timer channel for PWM output.

    Args:
        timer: Timer number (1-14, excluding 6 and 7)
        channel: PWM channel (1-4)
        freq: PWM frequency in Hz
        duty: Initial duty cycle (0-100 percent)
    """
    if timer < 1 or timer > 14 or timer == 6 or timer == 7:
        return
    if channel < 1 or channel > 4:
        return

    base: uint32 = _tim_base(timer)
    clock: uint32 = _tim_clock(timer)

    # Enable peripheral clock
    pwm_enable_clock(timer)

    # Stop timer during configuration
    mmio_write(base + TIM_CR1, 0)

    # Calculate prescaler and auto-reload for desired frequency
    # freq = timer_clk / ((PSC + 1) * (ARR + 1))
    # For simplicity, use PSC = 0 if possible, then increase if ARR overflows

    arr: uint32 = 0
    psc: uint32 = 0

    if freq > 0:
        # Start with no prescaler
        arr = (clock / freq) - 1

        # If ARR is too large, increase prescaler
        while arr > 65535 and psc < 65535:
            psc = psc + 1
            arr = (clock / ((psc + 1) * freq)) - 1

        if arr > 65535:
            arr = 65535

    mmio_write(base + TIM_PSC, psc)
    mmio_write(base + TIM_ARR, arr)

    # Configure output compare mode for PWM mode 1
    # PWM mode 1: active while CNT < CCR
    _pwm_configure_channel(base, channel)

    # Set initial duty cycle
    ccr: uint32 = ((arr + 1) * duty) / 100
    mmio_write(base + _ccr_offset(channel), ccr)

    # Enable auto-reload preload
    cr1: uint32 = mmio_read(base + TIM_CR1)
    mmio_write(base + TIM_CR1, cr1 | TIM_CR1_ARPE)

    # For advanced timers (TIM1/TIM8), enable main output
    if _tim_is_advanced(timer):
        mmio_write(base + TIM_BDTR, TIM_BDTR_MOE)

def _pwm_configure_channel(base: uint32, channel: uint32):
    """Configure channel for PWM mode 1 with preload.

    Args:
        base: Timer base address
        channel: Channel number (1-4)
    """
    if channel == 1:
        ccmr: uint32 = mmio_read(base + TIM_CCMR1)
        ccmr = ccmr & 0xFF00  # Clear CH1 bits
        ccmr = ccmr | TIM_CCMR_OCM_PWM1 | TIM_CCMR_OC1PE
        mmio_write(base + TIM_CCMR1, ccmr)
    elif channel == 2:
        ccmr: uint32 = mmio_read(base + TIM_CCMR1)
        ccmr = ccmr & 0x00FF  # Clear CH2 bits
        ccmr = ccmr | (TIM_CCMR_OCM_PWM1 << 8) | TIM_CCMR_OC2PE
        mmio_write(base + TIM_CCMR1, ccmr)
    elif channel == 3:
        ccmr: uint32 = mmio_read(base + TIM_CCMR2)
        ccmr = ccmr & 0xFF00  # Clear CH3 bits
        ccmr = ccmr | TIM_CCMR_OCM_PWM1 | TIM_CCMR_OC1PE
        mmio_write(base + TIM_CCMR2, ccmr)
    elif channel == 4:
        ccmr: uint32 = mmio_read(base + TIM_CCMR2)
        ccmr = ccmr & 0x00FF  # Clear CH4 bits
        ccmr = ccmr | (TIM_CCMR_OCM_PWM1 << 8) | TIM_CCMR_OC2PE
        mmio_write(base + TIM_CCMR2, ccmr)

# ============================================================================
# PWM Frequency and Duty Cycle
# ============================================================================

def pwm_set_frequency(timer: uint32, freq: uint32):
    """Set PWM frequency.

    Changes the timer auto-reload value. Note that this affects all channels
    on the same timer.

    Args:
        timer: Timer number (1-14)
        freq: Frequency in Hz
    """
    if timer < 1 or timer > 14:
        return

    base: uint32 = _tim_base(timer)
    clock: uint32 = _tim_clock(timer)

    # Get current prescaler
    psc: uint32 = mmio_read(base + TIM_PSC)

    # Calculate new ARR
    arr: uint32 = 0
    if freq > 0:
        arr = (clock / ((psc + 1) * freq)) - 1
        if arr > 65535:
            arr = 65535

    mmio_write(base + TIM_ARR, arr)

def pwm_set_duty(timer: uint32, channel: uint32, duty_percent: uint32):
    """Set duty cycle as percentage.

    Args:
        timer: Timer number (1-14)
        channel: PWM channel (1-4)
        duty_percent: Duty cycle (0-100)
    """
    if timer < 1 or timer > 14:
        return
    if channel < 1 or channel > 4:
        return
    if duty_percent > 100:
        duty_percent = 100

    base: uint32 = _tim_base(timer)

    # Get current ARR value
    arr: uint32 = mmio_read(base + TIM_ARR)

    # Calculate CCR value
    ccr: uint32 = ((arr + 1) * duty_percent) / 100
    mmio_write(base + _ccr_offset(channel), ccr)

def pwm_set_compare(timer: uint32, channel: uint32, value: uint32):
    """Set raw compare value.

    Args:
        timer: Timer number (1-14)
        channel: PWM channel (1-4)
        value: Compare value (should be <= ARR)
    """
    if timer < 1 or timer > 14:
        return
    if channel < 1 or channel > 4:
        return

    base: uint32 = _tim_base(timer)
    mmio_write(base + _ccr_offset(channel), value)

def pwm_get_compare(timer: uint32, channel: uint32) -> uint32:
    """Get current compare value.

    Args:
        timer: Timer number (1-14)
        channel: PWM channel (1-4)

    Returns:
        Current CCR value
    """
    if timer < 1 or timer > 14:
        return 0
    if channel < 1 or channel > 4:
        return 0

    base: uint32 = _tim_base(timer)
    return mmio_read(base + _ccr_offset(channel))

def pwm_set_arr(timer: uint32, arr: uint32):
    """Set auto-reload register (period).

    Args:
        timer: Timer number (1-14)
        arr: Auto-reload value
    """
    if timer < 1 or timer > 14:
        return

    base: uint32 = _tim_base(timer)
    mmio_write(base + TIM_ARR, arr)

def pwm_get_arr(timer: uint32) -> uint32:
    """Get auto-reload register value.

    Args:
        timer: Timer number (1-14)

    Returns:
        Current ARR value
    """
    if timer < 1 or timer > 14:
        return 0

    base: uint32 = _tim_base(timer)
    return mmio_read(base + TIM_ARR)

def pwm_set_prescaler(timer: uint32, psc: uint32):
    """Set timer prescaler.

    Args:
        timer: Timer number (1-14)
        psc: Prescaler value (timer clock is divided by PSC + 1)
    """
    if timer < 1 or timer > 14:
        return

    base: uint32 = _tim_base(timer)
    mmio_write(base + TIM_PSC, psc)

# ============================================================================
# Enable / Disable Functions
# ============================================================================

def pwm_enable(timer: uint32, channel: uint32):
    """Enable PWM output on specified channel.

    Args:
        timer: Timer number (1-14)
        channel: PWM channel (1-4)
    """
    if timer < 1 or timer > 14:
        return
    if channel < 1 or channel > 4:
        return

    base: uint32 = _tim_base(timer)

    # Enable channel output in CCER
    ccer: uint32 = mmio_read(base + TIM_CCER)
    if channel == 1:
        ccer = ccer | TIM_CCER_CC1E
    elif channel == 2:
        ccer = ccer | TIM_CCER_CC2E
    elif channel == 3:
        ccer = ccer | TIM_CCER_CC3E
    elif channel == 4:
        ccer = ccer | TIM_CCER_CC4E
    mmio_write(base + TIM_CCER, ccer)

    # Enable counter
    cr1: uint32 = mmio_read(base + TIM_CR1)
    mmio_write(base + TIM_CR1, cr1 | TIM_CR1_CEN)

def pwm_disable(timer: uint32, channel: uint32):
    """Disable PWM output on specified channel.

    Args:
        timer: Timer number (1-14)
        channel: PWM channel (1-4)
    """
    if timer < 1 or timer > 14:
        return
    if channel < 1 or channel > 4:
        return

    base: uint32 = _tim_base(timer)

    # Disable channel output in CCER
    ccer: uint32 = mmio_read(base + TIM_CCER)
    if channel == 1:
        ccer = ccer & ~TIM_CCER_CC1E
    elif channel == 2:
        ccer = ccer & ~TIM_CCER_CC2E
    elif channel == 3:
        ccer = ccer & ~TIM_CCER_CC3E
    elif channel == 4:
        ccer = ccer & ~TIM_CCER_CC4E
    mmio_write(base + TIM_CCER, ccer)

def pwm_start_timer(timer: uint32):
    """Start the timer counter.

    Args:
        timer: Timer number (1-14)
    """
    if timer < 1 or timer > 14:
        return

    base: uint32 = _tim_base(timer)
    cr1: uint32 = mmio_read(base + TIM_CR1)
    mmio_write(base + TIM_CR1, cr1 | TIM_CR1_CEN)

def pwm_stop_timer(timer: uint32):
    """Stop the timer counter.

    Args:
        timer: Timer number (1-14)
    """
    if timer < 1 or timer > 14:
        return

    base: uint32 = _tim_base(timer)
    cr1: uint32 = mmio_read(base + TIM_CR1)
    mmio_write(base + TIM_CR1, cr1 & ~TIM_CR1_CEN)

# ============================================================================
# Polarity Control
# ============================================================================

def pwm_set_polarity(timer: uint32, channel: uint32, active_high: bool):
    """Set output polarity for PWM channel.

    Args:
        timer: Timer number (1-14)
        channel: PWM channel (1-4)
        active_high: True for active-high (default), False for active-low
    """
    if timer < 1 or timer > 14:
        return
    if channel < 1 or channel > 4:
        return

    base: uint32 = _tim_base(timer)
    ccer: uint32 = mmio_read(base + TIM_CCER)

    if channel == 1:
        if active_high:
            ccer = ccer & ~TIM_CCER_CC1P
        else:
            ccer = ccer | TIM_CCER_CC1P
    elif channel == 2:
        if active_high:
            ccer = ccer & ~TIM_CCER_CC2P
        else:
            ccer = ccer | TIM_CCER_CC2P
    elif channel == 3:
        if active_high:
            ccer = ccer & ~TIM_CCER_CC3P
        else:
            ccer = ccer | TIM_CCER_CC3P
    elif channel == 4:
        if active_high:
            ccer = ccer & ~TIM_CCER_CC4P
        else:
            ccer = ccer | TIM_CCER_CC4P

    mmio_write(base + TIM_CCER, ccer)

# ============================================================================
# Center-Aligned (Phase-Correct) Mode
# ============================================================================

def pwm_set_center_aligned(timer: uint32, enable: bool):
    """Enable or disable center-aligned (phase-correct) mode.

    In center-aligned mode, the counter counts up to ARR then back down to 0,
    producing center-aligned PWM with half the frequency.

    Args:
        timer: Timer number (1-14)
        enable: True for center-aligned mode
    """
    if timer < 1 or timer > 14:
        return

    base: uint32 = _tim_base(timer)
    cr1: uint32 = mmio_read(base + TIM_CR1)

    # Clear CMS bits
    cr1 = cr1 & ~0x0060

    if enable:
        # Set center-aligned mode 1 (interrupt on down-count)
        cr1 = cr1 | TIM_CR1_CMS_CENTER1

    mmio_write(base + TIM_CR1, cr1)

# ============================================================================
# Advanced Timer Features (TIM1/TIM8)
# ============================================================================

def pwm_set_deadtime(timer: uint32, deadtime: uint32):
    """Set dead-time for advanced timers (TIM1/TIM8).

    Dead-time is the delay between complementary outputs.

    Args:
        timer: Timer number (must be 1 or 8)
        deadtime: Dead-time value (0-255, encoding depends on clock)
    """
    if not _tim_is_advanced(timer):
        return

    base: uint32 = _tim_base(timer)
    bdtr: uint32 = mmio_read(base + TIM_BDTR)
    bdtr = (bdtr & 0xFF00) | (deadtime & 0xFF)
    mmio_write(base + TIM_BDTR, bdtr)

def pwm_enable_complementary(timer: uint32, channel: uint32, enable: bool):
    """Enable complementary output for advanced timers.

    Args:
        timer: Timer number (must be 1 or 8)
        channel: PWM channel (1-3, channel 4 has no complementary)
        enable: True to enable complementary output
    """
    if not _tim_is_advanced(timer):
        return
    if channel < 1 or channel > 3:
        return

    base: uint32 = _tim_base(timer)
    ccer: uint32 = mmio_read(base + TIM_CCER)

    if channel == 1:
        if enable:
            ccer = ccer | TIM_CCER_CC1NE
        else:
            ccer = ccer & ~TIM_CCER_CC1NE
    elif channel == 2:
        if enable:
            ccer = ccer | TIM_CCER_CC2NE
        else:
            ccer = ccer & ~TIM_CCER_CC2NE
    elif channel == 3:
        if enable:
            ccer = ccer | TIM_CCER_CC3NE
        else:
            ccer = ccer & ~TIM_CCER_CC3NE

    mmio_write(base + TIM_CCER, ccer)

def pwm_set_break(timer: uint32, enable: bool, polarity_high: bool):
    """Configure break input for advanced timers.

    Break input can be used to disable PWM outputs on fault.

    Args:
        timer: Timer number (must be 1 or 8)
        enable: True to enable break function
        polarity_high: True for active-high break input
    """
    if not _tim_is_advanced(timer):
        return

    base: uint32 = _tim_base(timer)
    bdtr: uint32 = mmio_read(base + TIM_BDTR)

    if enable:
        bdtr = bdtr | TIM_BDTR_BKE
    else:
        bdtr = bdtr & ~TIM_BDTR_BKE

    if polarity_high:
        bdtr = bdtr | TIM_BDTR_BKP
    else:
        bdtr = bdtr & ~TIM_BDTR_BKP

    mmio_write(base + TIM_BDTR, bdtr)

# ============================================================================
# Counter Access
# ============================================================================

def pwm_get_counter(timer: uint32) -> uint32:
    """Get current counter value.

    Args:
        timer: Timer number (1-14)

    Returns:
        Current counter value
    """
    if timer < 1 or timer > 14:
        return 0

    base: uint32 = _tim_base(timer)
    return mmio_read(base + TIM_CNT)

def pwm_set_counter(timer: uint32, value: uint32):
    """Set counter value.

    Args:
        timer: Timer number (1-14)
        value: Counter value
    """
    if timer < 1 or timer > 14:
        return

    base: uint32 = _tim_base(timer)
    mmio_write(base + TIM_CNT, value)

# ============================================================================
# Utility Functions
# ============================================================================

def pwm_calc_prescaler_arr(timer_clk: uint32, freq: uint32,
                            psc_out: Ptr[uint32], arr_out: Ptr[uint32]):
    """Calculate prescaler and ARR for desired frequency.

    Args:
        timer_clk: Timer clock frequency in Hz
        freq: Desired PWM frequency in Hz
        psc_out: Pointer to store prescaler value
        arr_out: Pointer to store ARR value
    """
    if freq == 0:
        psc_out[0] = 0
        arr_out[0] = 65535
        return

    # Try to find smallest prescaler that gives valid ARR
    psc: uint32 = 0
    arr: uint32 = (timer_clk / freq) - 1

    while arr > 65535 and psc < 65535:
        psc = psc + 1
        arr = (timer_clk / ((psc + 1) * freq)) - 1

    if arr > 65535:
        arr = 65535

    psc_out[0] = psc
    arr_out[0] = arr
