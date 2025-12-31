# RP2040 Watchdog Timer Driver
#
# The RP2040 watchdog timer is clocked by the reference clock (typically XOSC).
# Features:
#   - 24-bit countdown timer
#   - Can reset the chip if not refreshed
#   - Can pause during debug
#   - Scratch registers survive watchdog reset
#
# Timeout calculation: time_us = (count * 2) / (clk_ref_freq / 1000000)
# At 12MHz XOSC: count = time_us * 6

# ============================================================================
# Base Addresses
# ============================================================================

WATCHDOG_BASE: uint32 = 0x40058000
PSM_BASE: uint32 = 0x40010000  # Power-on State Machine

# ============================================================================
# Watchdog Register Offsets
# ============================================================================

WATCHDOG_CTRL: uint32 = 0x00      # Control register
WATCHDOG_LOAD: uint32 = 0x04      # Load register (write to reload)
WATCHDOG_REASON: uint32 = 0x08    # Reset reason
WATCHDOG_SCRATCH0: uint32 = 0x0C  # Scratch registers (survive reset)
WATCHDOG_SCRATCH1: uint32 = 0x10
WATCHDOG_SCRATCH2: uint32 = 0x14
WATCHDOG_SCRATCH3: uint32 = 0x18
WATCHDOG_SCRATCH4: uint32 = 0x1C
WATCHDOG_SCRATCH5: uint32 = 0x20
WATCHDOG_SCRATCH6: uint32 = 0x24
WATCHDOG_SCRATCH7: uint32 = 0x28
WATCHDOG_TICK: uint32 = 0x2C      # Tick generator control

# CTRL register bits
WATCHDOG_CTRL_TIME_MASK: uint32 = 0x00FFFFFF  # Current countdown
WATCHDOG_CTRL_PAUSE_JTAG: uint32 = 0x02000000  # Pause when JTAG active
WATCHDOG_CTRL_PAUSE_DBG0: uint32 = 0x04000000  # Pause when debug 0 active
WATCHDOG_CTRL_PAUSE_DBG1: uint32 = 0x08000000  # Pause when debug 1 active
WATCHDOG_CTRL_ENABLE: uint32 = 0x40000000      # Enable watchdog
WATCHDOG_CTRL_TRIGGER: uint32 = 0x80000000     # Trigger reset now

# REASON register bits
WATCHDOG_REASON_TIMER: uint32 = 0x01  # Watchdog timer fired
WATCHDOG_REASON_FORCE: uint32 = 0x02  # Force trigger

# TICK register bits
WATCHDOG_TICK_CYCLES_MASK: uint32 = 0x1FF  # Tick cycles (9 bits)
WATCHDOG_TICK_ENABLE: uint32 = 0x200       # Enable tick generator
WATCHDOG_TICK_RUNNING: uint32 = 0x400      # Tick generator running
WATCHDOG_TICK_COUNT_MASK: uint32 = 0xFF800  # Current tick count

# ============================================================================
# Constants
# ============================================================================

# Reference clock is typically 12MHz XOSC
# Watchdog counts down at clk_ref/cycles, where cycles is programmed in TICK
# Default: cycles=12, so 1MHz tick rate, 1us per tick
# Actual timeout = load_value * 2 microseconds (counts down by 2)

WATCHDOG_MAX_TIMEOUT_US: uint32 = 0x7FFFFF  # ~8.3 seconds at 1MHz tick

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
# Watchdog Configuration
# ============================================================================

def watchdog_init(timeout_us: uint32, pause_on_debug: bool):
    """Initialize watchdog timer.

    Args:
        timeout_us: Timeout in microseconds (max ~8.3s)
        pause_on_debug: Pause countdown during debugging
    """
    # Configure tick generator for 1MHz (clk_ref / 12)
    tick: uint32 = 12 | WATCHDOG_TICK_ENABLE
    mmio_write(WATCHDOG_BASE + WATCHDOG_TICK, tick)

    # Configure control register
    ctrl: uint32 = 0
    if pause_on_debug:
        ctrl = ctrl | WATCHDOG_CTRL_PAUSE_JTAG
        ctrl = ctrl | WATCHDOG_CTRL_PAUSE_DBG0
        ctrl = ctrl | WATCHDOG_CTRL_PAUSE_DBG1

    mmio_write(WATCHDOG_BASE + WATCHDOG_CTRL, ctrl)

    # Load initial timeout
    # The watchdog counts down by 2 each tick, so load = timeout / 2
    load: uint32 = timeout_us / 2
    if load > 0xFFFFFF:
        load = 0xFFFFFF
    mmio_write(WATCHDOG_BASE + WATCHDOG_LOAD, load)

def watchdog_enable():
    """Enable the watchdog timer."""
    ctrl: uint32 = mmio_read(WATCHDOG_BASE + WATCHDOG_CTRL)
    mmio_write(WATCHDOG_BASE + WATCHDOG_CTRL, ctrl | WATCHDOG_CTRL_ENABLE)

def watchdog_disable():
    """Disable the watchdog timer.

    Note: Cannot be disabled once enabled on real RP2040.
    This only works in certain debug configurations.
    """
    ctrl: uint32 = mmio_read(WATCHDOG_BASE + WATCHDOG_CTRL)
    mmio_write(WATCHDOG_BASE + WATCHDOG_CTRL, ctrl & ~WATCHDOG_CTRL_ENABLE)

def watchdog_start(timeout_us: uint32, pause_on_debug: bool):
    """Initialize and start watchdog in one call.

    Args:
        timeout_us: Timeout in microseconds
        pause_on_debug: Pause during debug
    """
    watchdog_init(timeout_us, pause_on_debug)
    watchdog_enable()

# ============================================================================
# Watchdog Refresh
# ============================================================================

def watchdog_update(timeout_us: uint32):
    """Refresh watchdog with new timeout.

    Args:
        timeout_us: New timeout in microseconds
    """
    load: uint32 = timeout_us / 2
    if load > 0xFFFFFF:
        load = 0xFFFFFF
    mmio_write(WATCHDOG_BASE + WATCHDOG_LOAD, load)

def watchdog_feed():
    """Refresh watchdog with previously configured timeout.

    Call this periodically to prevent watchdog reset.
    """
    # Read current CTRL to get the last loaded value concept
    # Actually need to track the timeout ourselves or just reload max
    # For simplicity, reload maximum value
    mmio_write(WATCHDOG_BASE + WATCHDOG_LOAD, 0xFFFFFF)

def watchdog_kick(timeout_us: uint32):
    """Alias for watchdog_update."""
    watchdog_update(timeout_us)

# ============================================================================
# Watchdog Status
# ============================================================================

def watchdog_get_count() -> uint32:
    """Get current countdown value.

    Returns:
        Current countdown (multiply by 2 for microseconds)
    """
    ctrl: uint32 = mmio_read(WATCHDOG_BASE + WATCHDOG_CTRL)
    return ctrl & WATCHDOG_CTRL_TIME_MASK

def watchdog_caused_reboot() -> bool:
    """Check if last reset was caused by watchdog.

    Returns:
        True if watchdog caused the reset
    """
    reason: uint32 = mmio_read(WATCHDOG_BASE + WATCHDOG_REASON)
    return (reason & (WATCHDOG_REASON_TIMER | WATCHDOG_REASON_FORCE)) != 0

def watchdog_enable_caused_reboot() -> bool:
    """Check if watchdog timer specifically caused reset.

    Returns:
        True if watchdog timeout caused reset
    """
    reason: uint32 = mmio_read(WATCHDOG_BASE + WATCHDOG_REASON)
    return (reason & WATCHDOG_REASON_TIMER) != 0

# ============================================================================
# Force Reset
# ============================================================================

def watchdog_reboot(scratch0: uint32, scratch1: uint32, delay_us: uint32):
    """Trigger system reboot via watchdog.

    Args:
        scratch0: Value to preserve in SCRATCH0 across reset
        scratch1: Value to preserve in SCRATCH1 across reset
        delay_us: Delay before reset (0 for immediate)
    """
    # Save values in scratch registers
    mmio_write(WATCHDOG_BASE + WATCHDOG_SCRATCH0, scratch0)
    mmio_write(WATCHDOG_BASE + WATCHDOG_SCRATCH1, scratch1)

    if delay_us > 0:
        # Set short timeout
        load: uint32 = delay_us / 2
        if load > 0xFFFFFF:
            load = 0xFFFFFF
        if load == 0:
            load = 1
        mmio_write(WATCHDOG_BASE + WATCHDOG_LOAD, load)
        watchdog_enable()
    else:
        # Trigger immediate reset
        ctrl: uint32 = mmio_read(WATCHDOG_BASE + WATCHDOG_CTRL)
        mmio_write(WATCHDOG_BASE + WATCHDOG_CTRL, ctrl | WATCHDOG_CTRL_TRIGGER)

def watchdog_force_trigger():
    """Force immediate watchdog reset."""
    ctrl: uint32 = mmio_read(WATCHDOG_BASE + WATCHDOG_CTRL)
    mmio_write(WATCHDOG_BASE + WATCHDOG_CTRL, ctrl | WATCHDOG_CTRL_TRIGGER)

# ============================================================================
# Scratch Registers
# ============================================================================

def watchdog_set_scratch(index: uint32, value: uint32):
    """Write to scratch register.

    Scratch registers survive watchdog resets but not power-on resets.

    Args:
        index: Register index (0-7)
        value: Value to store
    """
    if index > 7:
        return
    mmio_write(WATCHDOG_BASE + WATCHDOG_SCRATCH0 + index * 4, value)

def watchdog_get_scratch(index: uint32) -> uint32:
    """Read from scratch register.

    Args:
        index: Register index (0-7)

    Returns:
        Stored value
    """
    if index > 7:
        return 0
    return mmio_read(WATCHDOG_BASE + WATCHDOG_SCRATCH0 + index * 4)

# ============================================================================
# Convenience Macros
# ============================================================================

def watchdog_start_ms(timeout_ms: uint32, pause_on_debug: bool):
    """Start watchdog with timeout in milliseconds.

    Args:
        timeout_ms: Timeout in milliseconds (max ~8300ms)
        pause_on_debug: Pause during debug
    """
    watchdog_start(timeout_ms * 1000, pause_on_debug)

def watchdog_update_ms(timeout_ms: uint32):
    """Update watchdog with timeout in milliseconds.

    Args:
        timeout_ms: Timeout in milliseconds
    """
    watchdog_update(timeout_ms * 1000)
