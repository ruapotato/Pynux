# RP2040 Timer Hardware Abstraction Layer
#
# The RP2040 has a 64-bit microsecond timer with 4 alarm comparators.
# The timer runs from the system clock (typically 1 MHz after divider).
#
# Features:
#   - 64-bit free-running counter at 1 MHz (1us resolution)
#   - 4 independent alarm comparators (ALARM0-3)
#   - Interrupt generation on alarm match
#   - Read-safe high/low register pairs
#
# Memory Map:
#   TIMER_BASE: 0x40054000

# ============================================================================
# Base Addresses
# ============================================================================

TIMER_BASE: uint32 = 0x40054000
RESETS_BASE: uint32 = 0x4000C000

# ============================================================================
# Timer Register Offsets
# ============================================================================

# Write to bits 63:32 of timer (latches write to TIMELW)
TIMER_TIMEHW: uint32 = 0x00
# Write to bits 31:0 of timer (triggers latched write from TIMEHW)
TIMER_TIMELW: uint32 = 0x04
# Read from bits 63:32 of timer (latches read to TIMELR)
TIMER_TIMEHR: uint32 = 0x08
# Read from bits 31:0 of timer (returns latched value from TIMEHR)
TIMER_TIMELR: uint32 = 0x0C

# Alarm registers (write target time to trigger)
TIMER_ALARM0: uint32 = 0x10
TIMER_ALARM1: uint32 = 0x14
TIMER_ALARM2: uint32 = 0x18
TIMER_ALARM3: uint32 = 0x1C

# Armed status (bit per alarm, write 1 to disarm)
TIMER_ARMED: uint32 = 0x20

# Raw read of timer (no latching, may be inconsistent)
TIMER_TIMERAWH: uint32 = 0x24
TIMER_TIMERAWL: uint32 = 0x28

# Debug pause control
TIMER_DBGPAUSE: uint32 = 0x2C

# Pause during debug
TIMER_PAUSE: uint32 = 0x30

# Interrupt registers
TIMER_INTR: uint32 = 0x34    # Raw interrupts (write 1 to clear)
TIMER_INTE: uint32 = 0x38    # Interrupt enable
TIMER_INTF: uint32 = 0x3C    # Interrupt force
TIMER_INTS: uint32 = 0x40    # Interrupt status (masked)

# ============================================================================
# Constants
# ============================================================================

# Number of alarm comparators
NUM_ALARMS: uint32 = 4

# Timer IRQ number in NVIC
TIMER_IRQ_0: uint32 = 0
TIMER_IRQ_1: uint32 = 1
TIMER_IRQ_2: uint32 = 2
TIMER_IRQ_3: uint32 = 3

# Reset bit for timer in RESETS register
TIMER_RESET_BIT: uint32 = 21

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
# Alarm Callbacks
# ============================================================================

# Callback function pointers for each alarm
_alarm_callbacks: Array[4, Ptr[void]]
_alarm_callbacks_set: Array[4, bool]

def _init_callbacks():
    """Initialize callback arrays."""
    i: uint32 = 0
    while i < 4:
        _alarm_callbacks_set[i] = False
        i = i + 1

# ============================================================================
# Timer Initialization
# ============================================================================

def timer_init():
    """Initialize the hardware timer.

    Brings timer out of reset and ensures it's running.
    The timer counts microseconds from boot.
    """
    # Unreset timer peripheral
    reset_val: uint32 = mmio_read(RESETS_BASE)
    mmio_write(RESETS_BASE, reset_val & ~(1 << TIMER_RESET_BIT))

    # Wait for reset done
    timeout: int32 = 10000
    while timeout > 0:
        done: uint32 = mmio_read(RESETS_BASE + 0x08)
        if (done & (1 << TIMER_RESET_BIT)) != 0:
            break
        timeout = timeout - 1

    # Initialize callback state
    _init_callbacks()

    # Disable all alarm interrupts initially
    mmio_write(TIMER_BASE + TIMER_INTE, 0)

    # Clear any pending alarm interrupts
    mmio_write(TIMER_BASE + TIMER_INTR, 0x0F)

    # Disarm all alarms
    mmio_write(TIMER_BASE + TIMER_ARMED, 0x0F)

def timer_reset():
    """Reset the timer to zero.

    Stops and restarts the timer from zero.
    Cancels all pending alarms.
    """
    # Disarm all alarms
    mmio_write(TIMER_BASE + TIMER_ARMED, 0x0F)

    # Clear all interrupts
    mmio_write(TIMER_BASE + TIMER_INTR, 0x0F)

    # Write zero to timer (write high first, then low triggers)
    mmio_write(TIMER_BASE + TIMER_TIMEHW, 0)
    mmio_write(TIMER_BASE + TIMER_TIMELW, 0)

# ============================================================================
# Time Reading Functions
# ============================================================================

def timer_get_us() -> uint64:
    """Get current timer value in microseconds.

    Uses latched read for consistent 64-bit value.
    Reading TIMEHR latches the value, then read TIMELR.

    Returns:
        Microseconds since timer started
    """
    # Read high first (latches the value)
    hi: uint32 = mmio_read(TIMER_BASE + TIMER_TIMEHR)
    lo: uint32 = mmio_read(TIMER_BASE + TIMER_TIMELR)

    return (cast[uint64](hi) << 32) | cast[uint64](lo)

def timer_get_us_32() -> uint32:
    """Get lower 32 bits of timer (faster, good for short intervals).

    Returns:
        Lower 32 bits of microsecond counter (wraps every ~71 minutes)
    """
    return mmio_read(TIMER_BASE + TIMER_TIMERAWL)

def timer_get_ms() -> uint32:
    """Get current timer value in milliseconds.

    Returns:
        Milliseconds since timer started (wraps at ~49 days)
    """
    us: uint64 = timer_get_us()
    return cast[uint32](us / 1000)

def timer_get_ms_64() -> uint64:
    """Get current timer value in milliseconds (64-bit).

    Returns:
        Milliseconds since timer started
    """
    return timer_get_us() / 1000

# ============================================================================
# Busy Wait Functions
# ============================================================================

def timer_busy_wait_us(us: uint32):
    """Blocking delay for specified microseconds.

    Args:
        us: Delay in microseconds
    """
    target: uint64 = timer_get_us() + cast[uint64](us)
    while timer_get_us() < target:
        pass

def timer_busy_wait_us_32(us: uint32):
    """Fast blocking delay using 32-bit compare.

    Only accurate for delays up to ~70 minutes.
    More efficient than 64-bit version for short delays.

    Args:
        us: Delay in microseconds
    """
    start: uint32 = timer_get_us_32()
    while (timer_get_us_32() - start) < us:
        pass

def timer_busy_wait_ms(ms: uint32):
    """Blocking delay for specified milliseconds.

    Args:
        ms: Delay in milliseconds
    """
    timer_busy_wait_us(ms * 1000)

def timer_delay_us(us: uint32):
    """Alias for timer_busy_wait_us."""
    timer_busy_wait_us(us)

def timer_delay_ms(ms: uint32):
    """Alias for timer_busy_wait_ms."""
    timer_busy_wait_ms(ms)

# ============================================================================
# Alarm Functions
# ============================================================================

def timer_set_alarm(alarm: uint32, time_us: uint64, callback: Ptr[void]) -> bool:
    """Set an alarm to fire at absolute time.

    The alarm fires when the lower 32 bits of the timer match
    the alarm register. Callback is stored for IRQ handler.

    Args:
        alarm: Alarm number (0-3)
        time_us: Absolute time in microseconds
        callback: Function to call when alarm fires (optional)

    Returns:
        True if alarm was set successfully
    """
    if alarm >= NUM_ALARMS:
        return False

    # Store callback
    _alarm_callbacks[alarm] = callback
    _alarm_callbacks_set[alarm] = (callback != cast[Ptr[void]](0))

    # Calculate alarm register address
    alarm_reg: uint32 = TIMER_BASE + TIMER_ALARM0 + (alarm * 4)

    # Write target time (lower 32 bits)
    # Writing to ALARM register arms the alarm
    target: uint32 = cast[uint32](time_us & 0xFFFFFFFF)
    mmio_write(alarm_reg, target)

    return True

def timer_set_alarm_in_us(alarm: uint32, delay_us: uint32, callback: Ptr[void]) -> bool:
    """Set an alarm to fire after specified delay.

    Args:
        alarm: Alarm number (0-3)
        delay_us: Delay from now in microseconds
        callback: Function to call when alarm fires

    Returns:
        True if alarm was set successfully
    """
    target: uint64 = timer_get_us() + cast[uint64](delay_us)
    return timer_set_alarm(alarm, target, callback)

def timer_set_alarm_in_ms(alarm: uint32, delay_ms: uint32, callback: Ptr[void]) -> bool:
    """Set an alarm to fire after specified delay in milliseconds.

    Args:
        alarm: Alarm number (0-3)
        delay_ms: Delay from now in milliseconds
        callback: Function to call when alarm fires

    Returns:
        True if alarm was set successfully
    """
    return timer_set_alarm_in_us(alarm, delay_ms * 1000, callback)

def timer_cancel_alarm(alarm: uint32):
    """Cancel a pending alarm.

    Args:
        alarm: Alarm number (0-3)
    """
    if alarm >= NUM_ALARMS:
        return

    # Write 1 to ARMED register bit to disarm
    mmio_write(TIMER_BASE + TIMER_ARMED, 1 << alarm)

    # Clear callback
    _alarm_callbacks_set[alarm] = False

    # Clear any pending interrupt
    mmio_write(TIMER_BASE + TIMER_INTR, 1 << alarm)

def timer_alarm_pending(alarm: uint32) -> bool:
    """Check if alarm is armed and pending.

    Args:
        alarm: Alarm number (0-3)

    Returns:
        True if alarm is armed
    """
    if alarm >= NUM_ALARMS:
        return False

    armed: uint32 = mmio_read(TIMER_BASE + TIMER_ARMED)
    return (armed & (1 << alarm)) != 0

def timer_alarm_fired(alarm: uint32) -> bool:
    """Check if alarm interrupt has fired.

    Args:
        alarm: Alarm number (0-3)

    Returns:
        True if alarm interrupt is pending
    """
    if alarm >= NUM_ALARMS:
        return False

    ints: uint32 = mmio_read(TIMER_BASE + TIMER_INTS)
    return (ints & (1 << alarm)) != 0

def timer_clear_alarm(alarm: uint32):
    """Clear alarm interrupt flag.

    Args:
        alarm: Alarm number (0-3)
    """
    if alarm >= NUM_ALARMS:
        return

    # Write 1 to clear interrupt
    mmio_write(TIMER_BASE + TIMER_INTR, 1 << alarm)

# ============================================================================
# Interrupt Control
# ============================================================================

def timer_set_irq_enabled(alarm: uint32, enable: bool):
    """Enable or disable alarm interrupt.

    Args:
        alarm: Alarm number (0-3)
        enable: True to enable, False to disable
    """
    if alarm >= NUM_ALARMS:
        return

    inte: uint32 = mmio_read(TIMER_BASE + TIMER_INTE)

    if enable:
        inte = inte | (1 << alarm)
    else:
        inte = inte & ~(1 << alarm)

    mmio_write(TIMER_BASE + TIMER_INTE, inte)

def timer_enable_irq(alarm: uint32):
    """Enable interrupt for alarm."""
    timer_set_irq_enabled(alarm, True)

def timer_disable_irq(alarm: uint32):
    """Disable interrupt for alarm."""
    timer_set_irq_enabled(alarm, False)

def timer_get_irq_status() -> uint32:
    """Get masked interrupt status.

    Returns:
        Bit mask of pending interrupts (bit N = alarm N)
    """
    return mmio_read(TIMER_BASE + TIMER_INTS)

def timer_get_irq_raw() -> uint32:
    """Get raw (unmasked) interrupt status.

    Returns:
        Bit mask of raw interrupts
    """
    return mmio_read(TIMER_BASE + TIMER_INTR)

def timer_force_irq(alarm: uint32):
    """Force an alarm interrupt (for testing).

    Args:
        alarm: Alarm number (0-3)
    """
    if alarm >= NUM_ALARMS:
        return

    mmio_write(TIMER_BASE + TIMER_INTF, 1 << alarm)

# ============================================================================
# IRQ Handler
# ============================================================================

def timer_irq_handler():
    """Timer interrupt handler.

    Should be called from the TIMER_IRQ_0 through TIMER_IRQ_3 handlers.
    Checks all alarms and calls registered callbacks.
    """
    ints: uint32 = mmio_read(TIMER_BASE + TIMER_INTS)

    alarm: uint32 = 0
    while alarm < 4:
        if (ints & (1 << alarm)) != 0:
            # Clear the interrupt
            mmio_write(TIMER_BASE + TIMER_INTR, 1 << alarm)

            # Call callback if registered
            if _alarm_callbacks_set[alarm]:
                cb: Ptr[void] = _alarm_callbacks[alarm]
                if cb != cast[Ptr[void]](0):
                    # Cast to function pointer and call
                    fn: Ptr[() -> void] = cast[Ptr[() -> void]](cb)
                    fn()

        alarm = alarm + 1

# ============================================================================
# Debug Control
# ============================================================================

def timer_pause_on_debug(pause: bool):
    """Configure timer behavior during debug.

    Args:
        pause: True to pause timer when debugger halts CPU
    """
    if pause:
        mmio_write(TIMER_BASE + TIMER_DBGPAUSE, 0x07)
    else:
        mmio_write(TIMER_BASE + TIMER_DBGPAUSE, 0x00)

def timer_is_paused() -> bool:
    """Check if timer is currently paused.

    Returns:
        True if timer is paused
    """
    pause: uint32 = mmio_read(TIMER_BASE + TIMER_PAUSE)
    return pause != 0

# ============================================================================
# Utility Functions
# ============================================================================

def timer_time_reached(target: uint64) -> bool:
    """Check if target time has been reached.

    Args:
        target: Target time in microseconds

    Returns:
        True if current time >= target
    """
    return timer_get_us() >= target

def timer_time_reached_32(target: uint32) -> bool:
    """Check if target time has been reached (32-bit).

    Uses signed comparison to handle wraparound.

    Args:
        target: Target time (lower 32 bits of timer)

    Returns:
        True if current time >= target (accounting for wrap)
    """
    now: uint32 = timer_get_us_32()
    diff: int32 = cast[int32](target - now)
    return diff <= 0

def timer_us_to_ms(us: uint64) -> uint32:
    """Convert microseconds to milliseconds.

    Args:
        us: Time in microseconds

    Returns:
        Time in milliseconds (truncated)
    """
    return cast[uint32](us / 1000)

def timer_ms_to_us(ms: uint32) -> uint64:
    """Convert milliseconds to microseconds.

    Args:
        ms: Time in milliseconds

    Returns:
        Time in microseconds
    """
    return cast[uint64](ms) * 1000
