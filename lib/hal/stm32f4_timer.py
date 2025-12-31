# STM32F4 General Purpose Timer Hardware Abstraction Layer
#
# Driver for STM32F405/F407 general purpose timers.
# Supports TIM2-TIM5 (32-bit) and TIM9-TIM14 (16-bit).
#
# Timer Types:
#   TIM2, TIM5: 32-bit, 4 channels, up/down/center-aligned
#   TIM3, TIM4: 16-bit, 4 channels, up/down/center-aligned
#   TIM9, TIM12: 16-bit, 2 channels, up only
#   TIM10, TIM11, TIM13, TIM14: 16-bit, 1 channel, up only
#
# Features:
#   - Basic timer counting (up, down, center-aligned)
#   - Input capture (measure pulse width, frequency)
#   - Output compare (generate pulses, PWM)
#   - One-pulse mode
#   - Interrupt on update event
#
# Memory Map:
#   TIM2:  0x40000000 (APB1)
#   TIM3:  0x40000400 (APB1)
#   TIM4:  0x40000800 (APB1)
#   TIM5:  0x40000C00 (APB1)
#   TIM9:  0x40014000 (APB2)
#   TIM10: 0x40014400 (APB2)
#   TIM11: 0x40014800 (APB2)
#   TIM12: 0x40001800 (APB1)
#   TIM13: 0x40001C00 (APB1)
#   TIM14: 0x40002000 (APB1)

# ============================================================================
# Base Addresses
# ============================================================================

TIM2_BASE: uint32 = 0x40000000
TIM3_BASE: uint32 = 0x40000400
TIM4_BASE: uint32 = 0x40000800
TIM5_BASE: uint32 = 0x40000C00
TIM9_BASE: uint32 = 0x40014000
TIM10_BASE: uint32 = 0x40014400
TIM11_BASE: uint32 = 0x40014800
TIM12_BASE: uint32 = 0x40001800
TIM13_BASE: uint32 = 0x40001C00
TIM14_BASE: uint32 = 0x40002000

RCC_BASE: uint32 = 0x40023800

# ============================================================================
# Timer Register Offsets
# ============================================================================

TIMx_CR1: uint32 = 0x00      # Control register 1
TIMx_CR2: uint32 = 0x04      # Control register 2
TIMx_SMCR: uint32 = 0x08     # Slave mode control register
TIMx_DIER: uint32 = 0x0C     # DMA/interrupt enable register
TIMx_SR: uint32 = 0x10       # Status register
TIMx_EGR: uint32 = 0x14      # Event generation register
TIMx_CCMR1: uint32 = 0x18    # Capture/compare mode register 1
TIMx_CCMR2: uint32 = 0x1C    # Capture/compare mode register 2
TIMx_CCER: uint32 = 0x20     # Capture/compare enable register
TIMx_CNT: uint32 = 0x24      # Counter register
TIMx_PSC: uint32 = 0x28      # Prescaler register
TIMx_ARR: uint32 = 0x2C      # Auto-reload register
TIMx_CCR1: uint32 = 0x34     # Capture/compare register 1
TIMx_CCR2: uint32 = 0x38     # Capture/compare register 2
TIMx_CCR3: uint32 = 0x3C     # Capture/compare register 3
TIMx_CCR4: uint32 = 0x40     # Capture/compare register 4
TIMx_DCR: uint32 = 0x48      # DMA control register
TIMx_DMAR: uint32 = 0x4C     # DMA address for full transfer
TIMx_OR: uint32 = 0x50       # Option register (TIM2, TIM5)

# ============================================================================
# CR1 Register Bits
# ============================================================================

TIM_CR1_CEN: uint32 = 0x0001      # Counter enable
TIM_CR1_UDIS: uint32 = 0x0002     # Update disable
TIM_CR1_URS: uint32 = 0x0004      # Update request source
TIM_CR1_OPM: uint32 = 0x0008      # One-pulse mode
TIM_CR1_DIR: uint32 = 0x0010      # Direction (0=up, 1=down)
TIM_CR1_CMS_MASK: uint32 = 0x0060 # Center-aligned mode selection
TIM_CR1_CMS_EDGE: uint32 = 0x0000 # Edge-aligned mode
TIM_CR1_CMS_CENTER1: uint32 = 0x0020  # Center-aligned mode 1
TIM_CR1_CMS_CENTER2: uint32 = 0x0040  # Center-aligned mode 2
TIM_CR1_CMS_CENTER3: uint32 = 0x0060  # Center-aligned mode 3
TIM_CR1_ARPE: uint32 = 0x0080     # Auto-reload preload enable
TIM_CR1_CKD_MASK: uint32 = 0x0300 # Clock division
TIM_CR1_CKD_DIV1: uint32 = 0x0000 # tDTS = tCK_INT
TIM_CR1_CKD_DIV2: uint32 = 0x0100 # tDTS = 2 * tCK_INT
TIM_CR1_CKD_DIV4: uint32 = 0x0200 # tDTS = 4 * tCK_INT

# ============================================================================
# CR2 Register Bits
# ============================================================================

TIM_CR2_CCDS: uint32 = 0x0008     # Capture/compare DMA selection
TIM_CR2_MMS_MASK: uint32 = 0x0070 # Master mode selection
TIM_CR2_MMS_RESET: uint32 = 0x0000    # Reset - UG bit used as trigger
TIM_CR2_MMS_ENABLE: uint32 = 0x0010   # Enable - CNT_EN used as trigger
TIM_CR2_MMS_UPDATE: uint32 = 0x0020   # Update - update event as trigger
TIM_CR2_MMS_COMPARE: uint32 = 0x0030  # Compare pulse
TIM_CR2_MMS_OC1REF: uint32 = 0x0040   # OC1REF as trigger
TIM_CR2_MMS_OC2REF: uint32 = 0x0050   # OC2REF as trigger
TIM_CR2_MMS_OC3REF: uint32 = 0x0060   # OC3REF as trigger
TIM_CR2_MMS_OC4REF: uint32 = 0x0070   # OC4REF as trigger
TIM_CR2_TI1S: uint32 = 0x0080     # TI1 selection

# ============================================================================
# SMCR Register Bits (Slave Mode Control)
# ============================================================================

TIM_SMCR_SMS_MASK: uint32 = 0x0007    # Slave mode selection
TIM_SMCR_SMS_DISABLED: uint32 = 0x0000
TIM_SMCR_SMS_ENCODER1: uint32 = 0x0001
TIM_SMCR_SMS_ENCODER2: uint32 = 0x0002
TIM_SMCR_SMS_ENCODER3: uint32 = 0x0003
TIM_SMCR_SMS_RESET: uint32 = 0x0004
TIM_SMCR_SMS_GATED: uint32 = 0x0005
TIM_SMCR_SMS_TRIGGER: uint32 = 0x0006
TIM_SMCR_SMS_EXTERNAL: uint32 = 0x0007
TIM_SMCR_TS_MASK: uint32 = 0x0070     # Trigger selection
TIM_SMCR_MSM: uint32 = 0x0080         # Master/slave mode
TIM_SMCR_ETF_MASK: uint32 = 0x0F00    # External trigger filter
TIM_SMCR_ETPS_MASK: uint32 = 0x3000   # External trigger prescaler
TIM_SMCR_ECE: uint32 = 0x4000         # External clock enable
TIM_SMCR_ETP: uint32 = 0x8000         # External trigger polarity

# ============================================================================
# DIER Register Bits (DMA/Interrupt Enable)
# ============================================================================

TIM_DIER_UIE: uint32 = 0x0001     # Update interrupt enable
TIM_DIER_CC1IE: uint32 = 0x0002   # CC1 interrupt enable
TIM_DIER_CC2IE: uint32 = 0x0004   # CC2 interrupt enable
TIM_DIER_CC3IE: uint32 = 0x0008   # CC3 interrupt enable
TIM_DIER_CC4IE: uint32 = 0x0010   # CC4 interrupt enable
TIM_DIER_TIE: uint32 = 0x0040     # Trigger interrupt enable
TIM_DIER_UDE: uint32 = 0x0100     # Update DMA request enable
TIM_DIER_CC1DE: uint32 = 0x0200   # CC1 DMA request enable
TIM_DIER_CC2DE: uint32 = 0x0400   # CC2 DMA request enable
TIM_DIER_CC3DE: uint32 = 0x0800   # CC3 DMA request enable
TIM_DIER_CC4DE: uint32 = 0x1000   # CC4 DMA request enable
TIM_DIER_TDE: uint32 = 0x4000     # Trigger DMA request enable

# ============================================================================
# SR Register Bits (Status)
# ============================================================================

TIM_SR_UIF: uint32 = 0x0001       # Update interrupt flag
TIM_SR_CC1IF: uint32 = 0x0002     # CC1 interrupt flag
TIM_SR_CC2IF: uint32 = 0x0004     # CC2 interrupt flag
TIM_SR_CC3IF: uint32 = 0x0008     # CC3 interrupt flag
TIM_SR_CC4IF: uint32 = 0x0010     # CC4 interrupt flag
TIM_SR_TIF: uint32 = 0x0040       # Trigger interrupt flag
TIM_SR_CC1OF: uint32 = 0x0200     # CC1 overcapture flag
TIM_SR_CC2OF: uint32 = 0x0400     # CC2 overcapture flag
TIM_SR_CC3OF: uint32 = 0x0800     # CC3 overcapture flag
TIM_SR_CC4OF: uint32 = 0x1000     # CC4 overcapture flag

# ============================================================================
# EGR Register Bits (Event Generation)
# ============================================================================

TIM_EGR_UG: uint32 = 0x01         # Update generation
TIM_EGR_CC1G: uint32 = 0x02       # CC1 generation
TIM_EGR_CC2G: uint32 = 0x04       # CC2 generation
TIM_EGR_CC3G: uint32 = 0x08       # CC3 generation
TIM_EGR_CC4G: uint32 = 0x10       # CC4 generation
TIM_EGR_TG: uint32 = 0x40         # Trigger generation

# ============================================================================
# CCMR Register Bits (Capture/Compare Mode)
# ============================================================================

# Output compare mode (when channel configured as output)
TIM_CCMR_OC_FROZEN: uint32 = 0x00     # Frozen (no effect)
TIM_CCMR_OC_ACTIVE: uint32 = 0x10     # Set active on match
TIM_CCMR_OC_INACTIVE: uint32 = 0x20   # Set inactive on match
TIM_CCMR_OC_TOGGLE: uint32 = 0x30     # Toggle on match
TIM_CCMR_OC_FORCE_LOW: uint32 = 0x40  # Force inactive
TIM_CCMR_OC_FORCE_HIGH: uint32 = 0x50 # Force active
TIM_CCMR_OC_PWM1: uint32 = 0x60       # PWM mode 1
TIM_CCMR_OC_PWM2: uint32 = 0x70       # PWM mode 2

TIM_CCMR_OCxPE: uint32 = 0x08         # Output compare preload enable
TIM_CCMR_OCxFE: uint32 = 0x04         # Output compare fast enable

# Input capture mode (when channel configured as input)
TIM_CCMR_IC_DIRECT: uint32 = 0x01     # IC mapped on TI1
TIM_CCMR_IC_INDIRECT: uint32 = 0x02   # IC mapped on TI2
TIM_CCMR_IC_TRC: uint32 = 0x03        # IC mapped on TRC

TIM_CCMR_IC_PSC_MASK: uint32 = 0x0C   # Input capture prescaler
TIM_CCMR_IC_PSC_1: uint32 = 0x00      # No prescaler
TIM_CCMR_IC_PSC_2: uint32 = 0x04      # Capture every 2 events
TIM_CCMR_IC_PSC_4: uint32 = 0x08      # Capture every 4 events
TIM_CCMR_IC_PSC_8: uint32 = 0x0C      # Capture every 8 events

TIM_CCMR_IC_FILTER_MASK: uint32 = 0xF0  # Input capture filter

# ============================================================================
# CCER Register Bits (Capture/Compare Enable)
# ============================================================================

TIM_CCER_CC1E: uint32 = 0x0001    # CC1 output enable
TIM_CCER_CC1P: uint32 = 0x0002    # CC1 output polarity
TIM_CCER_CC1NP: uint32 = 0x0008   # CC1 complementary polarity
TIM_CCER_CC2E: uint32 = 0x0010    # CC2 output enable
TIM_CCER_CC2P: uint32 = 0x0020    # CC2 output polarity
TIM_CCER_CC2NP: uint32 = 0x0080   # CC2 complementary polarity
TIM_CCER_CC3E: uint32 = 0x0100    # CC3 output enable
TIM_CCER_CC3P: uint32 = 0x0200    # CC3 output polarity
TIM_CCER_CC3NP: uint32 = 0x0800   # CC3 complementary polarity
TIM_CCER_CC4E: uint32 = 0x1000    # CC4 output enable
TIM_CCER_CC4P: uint32 = 0x2000    # CC4 output polarity
TIM_CCER_CC4NP: uint32 = 0x8000   # CC4 complementary polarity

# ============================================================================
# Timer Instance IDs
# ============================================================================

TIMER_2: uint32 = 2
TIMER_3: uint32 = 3
TIMER_4: uint32 = 4
TIMER_5: uint32 = 5
TIMER_9: uint32 = 9
TIMER_10: uint32 = 10
TIMER_11: uint32 = 11
TIMER_12: uint32 = 12
TIMER_13: uint32 = 13
TIMER_14: uint32 = 14

# Channel IDs
CHANNEL_1: uint32 = 1
CHANNEL_2: uint32 = 2
CHANNEL_3: uint32 = 3
CHANNEL_4: uint32 = 4

# Input capture edge selection
IC_EDGE_RISING: uint32 = 0
IC_EDGE_FALLING: uint32 = 1
IC_EDGE_BOTH: uint32 = 2

# ============================================================================
# RCC Register Offsets
# ============================================================================

RCC_APB1ENR: uint32 = 0x40
RCC_APB2ENR: uint32 = 0x44

# RCC enable bits
RCC_TIM2EN: uint32 = 0x01
RCC_TIM3EN: uint32 = 0x02
RCC_TIM4EN: uint32 = 0x04
RCC_TIM5EN: uint32 = 0x08
RCC_TIM12EN: uint32 = 0x40
RCC_TIM13EN: uint32 = 0x80
RCC_TIM14EN: uint32 = 0x100
RCC_TIM9EN: uint32 = 0x10000
RCC_TIM10EN: uint32 = 0x20000
RCC_TIM11EN: uint32 = 0x40000

# ============================================================================
# Clock Configuration
# ============================================================================

APB1_CLOCK: uint32 = 42000000    # APB1 timer clock (84 MHz / 2, but x2 for timers)
APB2_CLOCK: uint32 = 84000000    # APB2 timer clock

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

def _timer_base(timer: uint32) -> uint32:
    """Get base address for timer instance."""
    if timer == 2:
        return TIM2_BASE
    elif timer == 3:
        return TIM3_BASE
    elif timer == 4:
        return TIM4_BASE
    elif timer == 5:
        return TIM5_BASE
    elif timer == 9:
        return TIM9_BASE
    elif timer == 10:
        return TIM10_BASE
    elif timer == 11:
        return TIM11_BASE
    elif timer == 12:
        return TIM12_BASE
    elif timer == 13:
        return TIM13_BASE
    elif timer == 14:
        return TIM14_BASE
    else:
        return TIM2_BASE

def _timer_clock(timer: uint32) -> uint32:
    """Get clock frequency for timer."""
    # TIM9, TIM10, TIM11 are on APB2
    if timer == 9 or timer == 10 or timer == 11:
        return APB2_CLOCK
    # All others are on APB1
    return APB1_CLOCK

def _timer_is_32bit(timer: uint32) -> bool:
    """Check if timer is 32-bit (TIM2, TIM5)."""
    return timer == 2 or timer == 5

def _timer_num_channels(timer: uint32) -> uint32:
    """Get number of channels for timer."""
    if timer == 2 or timer == 3 or timer == 4 or timer == 5:
        return 4
    elif timer == 9 or timer == 12:
        return 2
    else:
        return 1

# ============================================================================
# Callback Storage
# ============================================================================

# Update interrupt callbacks (one per timer)
_update_callbacks: Array[15, Ptr[void]]
_update_callbacks_set: Array[15, bool]

def _init_callbacks():
    """Initialize callback arrays."""
    i: uint32 = 0
    while i < 15:
        _update_callbacks_set[i] = False
        i = i + 1

# ============================================================================
# Clock Enable Functions
# ============================================================================

def timer_enable_clock(timer: uint32):
    """Enable clock for timer peripheral.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    if timer == 2:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_TIM2EN)
    elif timer == 3:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_TIM3EN)
    elif timer == 4:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_TIM4EN)
    elif timer == 5:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_TIM5EN)
    elif timer == 9:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | RCC_TIM9EN)
    elif timer == 10:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | RCC_TIM10EN)
    elif timer == 11:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB2ENR)
        mmio_write(RCC_BASE + RCC_APB2ENR, val | RCC_TIM11EN)
    elif timer == 12:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_TIM12EN)
    elif timer == 13:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_TIM13EN)
    elif timer == 14:
        val: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
        mmio_write(RCC_BASE + RCC_APB1ENR, val | RCC_TIM14EN)

# ============================================================================
# Basic Timer Functions
# ============================================================================

def timer_init(timer: uint32, prescaler: uint32, period: uint32):
    """Initialize timer with prescaler and auto-reload value.

    Timer frequency = clock / ((prescaler + 1) * (period + 1))

    Args:
        timer: Timer number (2-5, 9-14)
        prescaler: Prescaler value (0-65535)
        period: Auto-reload value (0-65535 for 16-bit, 0-0xFFFFFFFF for 32-bit)
    """
    base: uint32 = _timer_base(timer)

    # Enable clock
    timer_enable_clock(timer)

    # Disable timer
    mmio_write(base + TIMx_CR1, 0)

    # Set prescaler
    mmio_write(base + TIMx_PSC, prescaler)

    # Set auto-reload value
    mmio_write(base + TIMx_ARR, period)

    # Clear counter
    mmio_write(base + TIMx_CNT, 0)

    # Generate update event to load prescaler immediately
    mmio_write(base + TIMx_EGR, TIM_EGR_UG)

    # Clear update flag (set by EGR write)
    mmio_write(base + TIMx_SR, ~TIM_SR_UIF)

    # Configure: upcounting, auto-reload preload enabled
    mmio_write(base + TIMx_CR1, TIM_CR1_ARPE)

def timer_init_us(timer: uint32, period_us: uint32):
    """Initialize timer for microsecond period.

    Args:
        timer: Timer number (2-5, 9-14)
        period_us: Period in microseconds
    """
    clock: uint32 = _timer_clock(timer)

    # Calculate prescaler for 1 MHz tick (1 us resolution)
    prescaler: uint32 = (clock / 1000000) - 1

    # Period in microseconds
    period: uint32 = period_us - 1

    timer_init(timer, prescaler, period)

def timer_init_ms(timer: uint32, period_ms: uint32):
    """Initialize timer for millisecond period.

    Args:
        timer: Timer number (2-5, 9-14)
        period_ms: Period in milliseconds
    """
    clock: uint32 = _timer_clock(timer)

    # Calculate prescaler for 1 kHz tick (1 ms resolution)
    prescaler: uint32 = (clock / 1000) - 1

    # Period in milliseconds
    period: uint32 = period_ms - 1

    timer_init(timer, prescaler, period)

def timer_start(timer: uint32):
    """Start timer counting.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    base: uint32 = _timer_base(timer)
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    mmio_write(base + TIMx_CR1, cr1 | TIM_CR1_CEN)

def timer_stop(timer: uint32):
    """Stop timer counting.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    base: uint32 = _timer_base(timer)
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    mmio_write(base + TIMx_CR1, cr1 & ~TIM_CR1_CEN)

def timer_is_running(timer: uint32) -> bool:
    """Check if timer is running.

    Args:
        timer: Timer number

    Returns:
        True if timer is counting
    """
    base: uint32 = _timer_base(timer)
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    return (cr1 & TIM_CR1_CEN) != 0

def timer_get_counter(timer: uint32) -> uint32:
    """Get current counter value.

    Args:
        timer: Timer number (2-5, 9-14)

    Returns:
        Current counter value
    """
    base: uint32 = _timer_base(timer)
    return mmio_read(base + TIMx_CNT)

def timer_set_counter(timer: uint32, value: uint32):
    """Set counter value.

    Args:
        timer: Timer number (2-5, 9-14)
        value: New counter value
    """
    base: uint32 = _timer_base(timer)
    mmio_write(base + TIMx_CNT, value)

def timer_set_prescaler(timer: uint32, prescaler: uint32):
    """Set prescaler value.

    New value takes effect at next update event.

    Args:
        timer: Timer number (2-5, 9-14)
        prescaler: Prescaler value (0-65535)
    """
    base: uint32 = _timer_base(timer)
    mmio_write(base + TIMx_PSC, prescaler)

def timer_set_period(timer: uint32, period: uint32):
    """Set auto-reload (period) value.

    Args:
        timer: Timer number (2-5, 9-14)
        period: Period value
    """
    base: uint32 = _timer_base(timer)
    mmio_write(base + TIMx_ARR, period)

def timer_get_period(timer: uint32) -> uint32:
    """Get auto-reload (period) value.

    Args:
        timer: Timer number

    Returns:
        Period value
    """
    base: uint32 = _timer_base(timer)
    return mmio_read(base + TIMx_ARR)

# ============================================================================
# Counter Direction
# ============================================================================

def timer_set_direction_up(timer: uint32):
    """Set timer to count up.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    base: uint32 = _timer_base(timer)
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    mmio_write(base + TIMx_CR1, cr1 & ~TIM_CR1_DIR)

def timer_set_direction_down(timer: uint32):
    """Set timer to count down.

    Only supported on TIM2-TIM5.

    Args:
        timer: Timer number (2-5)
    """
    base: uint32 = _timer_base(timer)
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    mmio_write(base + TIMx_CR1, cr1 | TIM_CR1_DIR)

def timer_set_center_aligned(timer: uint32, mode: uint32):
    """Set timer to center-aligned mode.

    Only supported on TIM2-TIM5.

    Args:
        timer: Timer number (2-5)
        mode: 1, 2, or 3 for center-aligned mode selection
    """
    base: uint32 = _timer_base(timer)
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    cr1 = cr1 & ~TIM_CR1_CMS_MASK

    if mode == 1:
        cr1 = cr1 | TIM_CR1_CMS_CENTER1
    elif mode == 2:
        cr1 = cr1 | TIM_CR1_CMS_CENTER2
    elif mode == 3:
        cr1 = cr1 | TIM_CR1_CMS_CENTER3

    mmio_write(base + TIMx_CR1, cr1)

# ============================================================================
# One-Pulse Mode
# ============================================================================

def timer_enable_one_pulse(timer: uint32):
    """Enable one-pulse mode.

    Timer stops after generating one update event.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    base: uint32 = _timer_base(timer)
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    mmio_write(base + TIMx_CR1, cr1 | TIM_CR1_OPM)

def timer_disable_one_pulse(timer: uint32):
    """Disable one-pulse mode.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    base: uint32 = _timer_base(timer)
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    mmio_write(base + TIMx_CR1, cr1 & ~TIM_CR1_OPM)

def timer_one_shot(timer: uint32, prescaler: uint32, delay: uint32):
    """Configure timer for single delayed pulse.

    Args:
        timer: Timer number
        prescaler: Prescaler value
        delay: Delay count until trigger
    """
    base: uint32 = _timer_base(timer)

    # Enable clock and stop timer
    timer_enable_clock(timer)
    mmio_write(base + TIMx_CR1, 0)

    # Configure prescaler and period
    mmio_write(base + TIMx_PSC, prescaler)
    mmio_write(base + TIMx_ARR, delay)
    mmio_write(base + TIMx_CNT, 0)

    # Load values
    mmio_write(base + TIMx_EGR, TIM_EGR_UG)
    mmio_write(base + TIMx_SR, ~TIM_SR_UIF)

    # Enable one-pulse mode and start
    mmio_write(base + TIMx_CR1, TIM_CR1_OPM | TIM_CR1_ARPE | TIM_CR1_CEN)

# ============================================================================
# Interrupt Control
# ============================================================================

def timer_set_callback(timer: uint32, callback: Ptr[void]):
    """Set callback for timer update interrupt.

    Args:
        timer: Timer number (2-5, 9-14)
        callback: Function to call on update event
    """
    if timer <= 14:
        _update_callbacks[timer] = callback
        _update_callbacks_set[timer] = (callback != cast[Ptr[void]](0))

def timer_enable_irq(timer: uint32):
    """Enable timer update interrupt.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    base: uint32 = _timer_base(timer)
    dier: uint32 = mmio_read(base + TIMx_DIER)
    mmio_write(base + TIMx_DIER, dier | TIM_DIER_UIE)

def timer_disable_irq(timer: uint32):
    """Disable timer update interrupt.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    base: uint32 = _timer_base(timer)
    dier: uint32 = mmio_read(base + TIMx_DIER)
    mmio_write(base + TIMx_DIER, dier & ~TIM_DIER_UIE)

def timer_irq_pending(timer: uint32) -> bool:
    """Check if update interrupt is pending.

    Args:
        timer: Timer number

    Returns:
        True if update flag is set
    """
    base: uint32 = _timer_base(timer)
    sr: uint32 = mmio_read(base + TIMx_SR)
    return (sr & TIM_SR_UIF) != 0

def timer_clear_irq(timer: uint32):
    """Clear timer update interrupt flag.

    Args:
        timer: Timer number (2-5, 9-14)
    """
    base: uint32 = _timer_base(timer)
    mmio_write(base + TIMx_SR, ~TIM_SR_UIF)

def timer_enable_cc_irq(timer: uint32, channel: uint32):
    """Enable capture/compare interrupt for channel.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
    """
    base: uint32 = _timer_base(timer)
    dier: uint32 = mmio_read(base + TIMx_DIER)

    if channel == 1:
        dier = dier | TIM_DIER_CC1IE
    elif channel == 2:
        dier = dier | TIM_DIER_CC2IE
    elif channel == 3:
        dier = dier | TIM_DIER_CC3IE
    elif channel == 4:
        dier = dier | TIM_DIER_CC4IE

    mmio_write(base + TIMx_DIER, dier)

def timer_disable_cc_irq(timer: uint32, channel: uint32):
    """Disable capture/compare interrupt for channel.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
    """
    base: uint32 = _timer_base(timer)
    dier: uint32 = mmio_read(base + TIMx_DIER)

    if channel == 1:
        dier = dier & ~TIM_DIER_CC1IE
    elif channel == 2:
        dier = dier & ~TIM_DIER_CC2IE
    elif channel == 3:
        dier = dier & ~TIM_DIER_CC3IE
    elif channel == 4:
        dier = dier & ~TIM_DIER_CC4IE

    mmio_write(base + TIMx_DIER, dier)

# ============================================================================
# Input Capture Mode
# ============================================================================

def timer_input_capture_init(timer: uint32, channel: uint32, edge: uint32):
    """Initialize channel for input capture.

    Args:
        timer: Timer number (2-5, 9-14)
        channel: Channel number (1-4, depending on timer)
        edge: IC_EDGE_RISING, IC_EDGE_FALLING, or IC_EDGE_BOTH
    """
    base: uint32 = _timer_base(timer)

    # Determine which CCMR register and bit positions
    if channel <= 2:
        ccmr_addr: uint32 = base + TIMx_CCMR1
        shift: uint32 = (channel - 1) * 8
    else:
        ccmr_addr: uint32 = base + TIMx_CCMR2
        shift: uint32 = (channel - 3) * 8

    # Configure as input capture (direct mapping)
    ccmr: uint32 = mmio_read(ccmr_addr)
    ccmr = ccmr & ~(0xFF << shift)
    ccmr = ccmr | (TIM_CCMR_IC_DIRECT << shift)  # CC mapped on TI
    mmio_write(ccmr_addr, ccmr)

    # Configure polarity in CCER
    ccer: uint32 = mmio_read(base + TIMx_CCER)
    cce_shift: uint32 = (channel - 1) * 4

    # Clear polarity bits
    ccer = ccer & ~(0x0A << cce_shift)

    if edge == IC_EDGE_FALLING:
        ccer = ccer | (0x02 << cce_shift)  # CC1P = 1, CC1NP = 0
    elif edge == IC_EDGE_BOTH:
        ccer = ccer | (0x0A << cce_shift)  # CC1P = 1, CC1NP = 1

    # Enable channel
    ccer = ccer | (0x01 << cce_shift)
    mmio_write(base + TIMx_CCER, ccer)

def timer_input_capture_set_filter(timer: uint32, channel: uint32, filter: uint32):
    """Set input capture filter.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
        filter: Filter value (0-15)
    """
    base: uint32 = _timer_base(timer)

    if channel <= 2:
        ccmr_addr: uint32 = base + TIMx_CCMR1
        shift: uint32 = (channel - 1) * 8 + 4
    else:
        ccmr_addr: uint32 = base + TIMx_CCMR2
        shift: uint32 = (channel - 3) * 8 + 4

    ccmr: uint32 = mmio_read(ccmr_addr)
    ccmr = ccmr & ~(0x0F << shift)
    ccmr = ccmr | ((filter & 0x0F) << shift)
    mmio_write(ccmr_addr, ccmr)

def timer_input_capture_set_prescaler(timer: uint32, channel: uint32, prescaler: uint32):
    """Set input capture prescaler.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
        prescaler: 0=1x, 1=2x, 2=4x, 3=8x
    """
    base: uint32 = _timer_base(timer)

    if channel <= 2:
        ccmr_addr: uint32 = base + TIMx_CCMR1
        shift: uint32 = (channel - 1) * 8 + 2
    else:
        ccmr_addr: uint32 = base + TIMx_CCMR2
        shift: uint32 = (channel - 3) * 8 + 2

    ccmr: uint32 = mmio_read(ccmr_addr)
    ccmr = ccmr & ~(0x03 << shift)
    ccmr = ccmr | ((prescaler & 0x03) << shift)
    mmio_write(ccmr_addr, ccmr)

def timer_get_capture(timer: uint32, channel: uint32) -> uint32:
    """Read captured value.

    Args:
        timer: Timer number
        channel: Channel number (1-4)

    Returns:
        Captured counter value
    """
    base: uint32 = _timer_base(timer)

    if channel == 1:
        return mmio_read(base + TIMx_CCR1)
    elif channel == 2:
        return mmio_read(base + TIMx_CCR2)
    elif channel == 3:
        return mmio_read(base + TIMx_CCR3)
    elif channel == 4:
        return mmio_read(base + TIMx_CCR4)
    else:
        return 0

def timer_capture_flag(timer: uint32, channel: uint32) -> bool:
    """Check if capture event occurred.

    Args:
        timer: Timer number
        channel: Channel number (1-4)

    Returns:
        True if capture flag is set
    """
    base: uint32 = _timer_base(timer)
    sr: uint32 = mmio_read(base + TIMx_SR)

    if channel == 1:
        return (sr & TIM_SR_CC1IF) != 0
    elif channel == 2:
        return (sr & TIM_SR_CC2IF) != 0
    elif channel == 3:
        return (sr & TIM_SR_CC3IF) != 0
    elif channel == 4:
        return (sr & TIM_SR_CC4IF) != 0
    else:
        return False

def timer_clear_capture_flag(timer: uint32, channel: uint32):
    """Clear capture flag.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
    """
    base: uint32 = _timer_base(timer)

    if channel == 1:
        mmio_write(base + TIMx_SR, ~TIM_SR_CC1IF)
    elif channel == 2:
        mmio_write(base + TIMx_SR, ~TIM_SR_CC2IF)
    elif channel == 3:
        mmio_write(base + TIMx_SR, ~TIM_SR_CC3IF)
    elif channel == 4:
        mmio_write(base + TIMx_SR, ~TIM_SR_CC4IF)

# ============================================================================
# Output Compare Mode
# ============================================================================

def timer_output_compare_init(timer: uint32, channel: uint32, mode: uint32):
    """Initialize channel for output compare.

    Args:
        timer: Timer number (2-5, 9-14)
        channel: Channel number (1-4, depending on timer)
        mode: TIM_CCMR_OC_* mode value
    """
    base: uint32 = _timer_base(timer)

    # Determine which CCMR register and bit positions
    if channel <= 2:
        ccmr_addr: uint32 = base + TIMx_CCMR1
        shift: uint32 = (channel - 1) * 8
    else:
        ccmr_addr: uint32 = base + TIMx_CCMR2
        shift: uint32 = (channel - 3) * 8

    # Configure output compare mode
    ccmr: uint32 = mmio_read(ccmr_addr)
    ccmr = ccmr & ~(0xFF << shift)
    # Mode in bits 6:4, preload enable in bit 3
    ccmr = ccmr | ((mode | TIM_CCMR_OCxPE) << shift)
    mmio_write(ccmr_addr, ccmr)

    # Enable output in CCER
    ccer: uint32 = mmio_read(base + TIMx_CCER)
    cce_shift: uint32 = (channel - 1) * 4
    ccer = ccer | (0x01 << cce_shift)
    mmio_write(base + TIMx_CCER, ccer)

def timer_set_compare(timer: uint32, channel: uint32, value: uint32):
    """Set compare value for channel.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
        value: Compare value
    """
    base: uint32 = _timer_base(timer)

    if channel == 1:
        mmio_write(base + TIMx_CCR1, value)
    elif channel == 2:
        mmio_write(base + TIMx_CCR2, value)
    elif channel == 3:
        mmio_write(base + TIMx_CCR3, value)
    elif channel == 4:
        mmio_write(base + TIMx_CCR4, value)

def timer_get_compare(timer: uint32, channel: uint32) -> uint32:
    """Get compare value for channel.

    Args:
        timer: Timer number
        channel: Channel number (1-4)

    Returns:
        Compare value
    """
    return timer_get_capture(timer, channel)

def timer_set_output_polarity(timer: uint32, channel: uint32, active_low: bool):
    """Set output polarity.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
        active_low: True for active low output
    """
    base: uint32 = _timer_base(timer)
    ccer: uint32 = mmio_read(base + TIMx_CCER)
    cce_shift: uint32 = (channel - 1) * 4 + 1

    if active_low:
        ccer = ccer | (1 << cce_shift)
    else:
        ccer = ccer & ~(1 << cce_shift)

    mmio_write(base + TIMx_CCER, ccer)

# ============================================================================
# PWM Functions
# ============================================================================

def timer_pwm_init(timer: uint32, channel: uint32, period: uint32, duty: uint32):
    """Initialize PWM output on channel.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
        period: PWM period (auto-reload value)
        duty: Initial duty cycle (compare value)
    """
    # Configure as PWM mode 1
    timer_output_compare_init(timer, channel, TIM_CCMR_OC_PWM1)
    timer_set_compare(timer, channel, duty)

def timer_pwm_set_duty(timer: uint32, channel: uint32, duty: uint32):
    """Set PWM duty cycle.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
        duty: Duty cycle value (0 to period)
    """
    timer_set_compare(timer, channel, duty)

def timer_pwm_set_duty_percent(timer: uint32, channel: uint32, percent: uint32):
    """Set PWM duty cycle as percentage.

    Args:
        timer: Timer number
        channel: Channel number (1-4)
        percent: Duty cycle percentage (0-100)
    """
    period: uint32 = timer_get_period(timer)
    duty: uint32 = (period * percent) / 100
    timer_set_compare(timer, channel, duty)

# ============================================================================
# IRQ Handler
# ============================================================================

def timer_irq_handler(timer: uint32):
    """Timer interrupt handler.

    Should be called from the appropriate TIMx_IRQHandler.

    Args:
        timer: Timer number that triggered interrupt
    """
    base: uint32 = _timer_base(timer)
    sr: uint32 = mmio_read(base + TIMx_SR)

    # Handle update interrupt
    if (sr & TIM_SR_UIF) != 0:
        # Clear flag
        mmio_write(base + TIMx_SR, ~TIM_SR_UIF)

        # Call callback if registered
        if timer <= 14 and _update_callbacks_set[timer]:
            cb: Ptr[void] = _update_callbacks[timer]
            if cb != cast[Ptr[void]](0):
                fn: Ptr[() -> void] = cast[Ptr[() -> void]](cb)
                fn()

# ============================================================================
# Utility Functions
# ============================================================================

def timer_generate_update(timer: uint32):
    """Generate software update event.

    Forces reload of prescaler and auto-reload values.

    Args:
        timer: Timer number
    """
    base: uint32 = _timer_base(timer)
    mmio_write(base + TIMx_EGR, TIM_EGR_UG)

def timer_get_clock_freq(timer: uint32) -> uint32:
    """Get timer input clock frequency.

    Args:
        timer: Timer number

    Returns:
        Clock frequency in Hz
    """
    return _timer_clock(timer)

def timer_calc_prescaler(timer: uint32, freq_hz: uint32) -> uint32:
    """Calculate prescaler for desired tick frequency.

    Args:
        timer: Timer number
        freq_hz: Desired tick frequency

    Returns:
        Prescaler value
    """
    clock: uint32 = _timer_clock(timer)
    return (clock / freq_hz) - 1

def timer_delay_us(timer: uint32, us: uint32):
    """Blocking delay using timer.

    Timer must already be initialized.

    Args:
        timer: Timer number
        us: Delay in microseconds
    """
    base: uint32 = _timer_base(timer)
    clock: uint32 = _timer_clock(timer)

    # Set prescaler for 1 MHz (1 us ticks)
    prescaler: uint32 = (clock / 1000000) - 1
    mmio_write(base + TIMx_PSC, prescaler)
    mmio_write(base + TIMx_ARR, us)
    mmio_write(base + TIMx_CNT, 0)

    # Load values and clear flag
    mmio_write(base + TIMx_EGR, TIM_EGR_UG)
    mmio_write(base + TIMx_SR, ~TIM_SR_UIF)

    # Enable one-pulse mode and start
    cr1: uint32 = mmio_read(base + TIMx_CR1)
    mmio_write(base + TIMx_CR1, cr1 | TIM_CR1_OPM | TIM_CR1_CEN)

    # Wait for update flag
    while (mmio_read(base + TIMx_SR) & TIM_SR_UIF) == 0:
        pass

    # Clear flag and disable one-pulse
    mmio_write(base + TIMx_SR, ~TIM_SR_UIF)
    mmio_write(base + TIMx_CR1, cr1)
