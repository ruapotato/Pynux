# Pynux Timer for ARM Cortex-M3
#
# Uses SysTick timer for basic timing.
# SysTick is available on all Cortex-M cores.

from lib.io import print_str, print_int

# SysTick registers (standard Cortex-M)
# Base: 0xE000E010
SYST_CSR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E010)   # Control and Status
SYST_RVR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E014)   # Reload Value
SYST_CVR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000E018)   # Current Value

# CSR bits
SYST_CSR_ENABLE: uint32 = 0x01
SYST_CSR_TICKINT: uint32 = 0x02
SYST_CSR_CLKSOURCE: uint32 = 0x04
SYST_CSR_COUNTFLAG: uint32 = 0x10000

# System clock frequencies (Hz) - set by BSP
# QEMU mps2-an385: 25MHz
# RP2040:          125MHz
# STM32F4:         168MHz
SYSTEM_CLOCK: int32 = 25000000
TICKS_PER_MS: int32 = 25000

def timer_set_clock(clock_hz: int32):
    """Set system clock frequency. Called by BSP init."""
    global SYSTEM_CLOCK, TICKS_PER_MS
    SYSTEM_CLOCK = clock_hz
    TICKS_PER_MS = clock_hz / 1000

# Timer state (shared, requires critical section)
timer_ticks: volatile int32 = 0

def timer_init():
    """Initialize SysTick timer for 1ms tick with interrupt."""
    global timer_ticks

    state: int32 = critical_enter()
    timer_ticks = 0
    critical_exit(state)

    # Set reload value for 1ms tick
    SYST_RVR[0] = cast[uint32](TICKS_PER_MS - 1)
    dsb()

    # Clear current value
    SYST_CVR[0] = 0
    dsb()

    # Enable SysTick with processor clock AND interrupt
    # SysTick_Handler will call timer_tick() on each interrupt
    SYST_CSR[0] = SYST_CSR_ENABLE | SYST_CSR_CLKSOURCE | SYST_CSR_TICKINT
    dsb()

def timer_init_poll():
    """Initialize SysTick timer for polling mode (no interrupt)."""
    global timer_ticks

    state: int32 = critical_enter()
    timer_ticks = 0
    critical_exit(state)

    # Set reload value for 1ms tick
    SYST_RVR[0] = cast[uint32](TICKS_PER_MS - 1)
    dsb()

    # Clear current value
    SYST_CVR[0] = 0
    dsb()

    # Enable SysTick with processor clock, no interrupt
    SYST_CSR[0] = SYST_CSR_ENABLE | SYST_CSR_CLKSOURCE
    dsb()

def timer_tick():
    """Called from SysTick interrupt handler or polling loop."""
    global timer_ticks
    # When called from interrupt, just increment
    # When polling, check COUNTFLAG first
    csr_val: uint32 = SYST_CSR[0]
    dmb()
    # COUNTFLAG is cleared by reading CSR, so always increment if set
    # For interrupt mode, COUNTFLAG will always be set when handler runs
    if (csr_val & SYST_CSR_COUNTFLAG) != 0:
        state: int32 = critical_enter()
        timer_ticks = timer_ticks + 1
        critical_exit(state)

def timer_tick_isr():
    """Called from SysTick interrupt handler - unconditional increment."""
    global timer_ticks
    # In interrupt context, just increment directly
    # Critical section not needed as interrupts are already disabled
    timer_ticks = timer_ticks + 1

def timer_get_ticks() -> int32:
    state: int32 = critical_enter()
    ticks: int32 = timer_ticks
    critical_exit(state)
    return ticks

def timer_delay_ms(ms: int32):
    # Simple busy-wait delay
    i: int32 = 0
    while i < ms:
        # Wait for one SysTick cycle
        csr_val: uint32 = SYST_CSR[0]
        dmb()
        while (csr_val & SYST_CSR_COUNTFLAG) == 0:
            csr_val = SYST_CSR[0]
            dmb()
        i = i + 1

def timer_delay_us(us: int32):
    # Approximate microsecond delay using busy loop
    # At 25MHz, ~25 cycles per microsecond
    cycles: int32 = us * 25
    i: int32 = 0
    while i < cycles:
        i = i + 1
