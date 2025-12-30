# Pynux Timer for ARM Cortex-M3
#
# Uses SysTick timer for basic timing.
# SysTick is available on all Cortex-M cores.

from lib.io import print_str, print_int

# SysTick registers (standard Cortex-M)
# Base: 0xE000E010
SYST_CSR: Ptr[uint32] = Ptr[uint32](0xE000E010)   # Control and Status
SYST_RVR: Ptr[uint32] = Ptr[uint32](0xE000E014)   # Reload Value
SYST_CVR: Ptr[uint32] = Ptr[uint32](0xE000E018)   # Current Value

# CSR bits
SYST_CSR_ENABLE: uint32 = 0x01
SYST_CSR_TICKINT: uint32 = 0x02
SYST_CSR_CLKSOURCE: uint32 = 0x04
SYST_CSR_COUNTFLAG: uint32 = 0x10000

# System clock (QEMU mps2-an385 runs at 25MHz)
SYSTEM_CLOCK: int32 = 25000000
TICKS_PER_MS: int32 = 25000

# Timer state
timer_ticks: int32 = 0

def timer_init():
    global timer_ticks
    timer_ticks = 0

    # Set reload value for 1ms tick
    SYST_RVR[0] = cast[uint32](TICKS_PER_MS - 1)

    # Clear current value
    SYST_CVR[0] = 0

    # Enable SysTick with processor clock, no interrupt
    # We'll poll for simplicity (no interrupt handler needed)
    SYST_CSR[0] = SYST_CSR_ENABLE | SYST_CSR_CLKSOURCE

def timer_tick():
    global timer_ticks
    # Check if countflag is set (timer wrapped)
    if (SYST_CSR[0] & SYST_CSR_COUNTFLAG) != 0:
        timer_ticks = timer_ticks + 1

def timer_get_ticks() -> int32:
    return timer_ticks

def timer_delay_ms(ms: int32):
    # Simple busy-wait delay
    i: int32 = 0
    while i < ms:
        # Wait for one SysTick cycle
        while (SYST_CSR[0] & SYST_CSR_COUNTFLAG) == 0:
            pass
        i = i + 1

def timer_delay_us(us: int32):
    # Approximate microsecond delay using busy loop
    # At 25MHz, ~25 cycles per microsecond
    cycles: int32 = us * 25
    i: int32 = 0
    while i < cycles:
        i = i + 1
