# Pynux Watchdog Timer Library
#
# Hardware watchdog timer abstraction for ARM Cortex-M3.
# Provides system reset protection and health monitoring.
#
# For QEMU emulation, uses software timer. On real hardware,
# would use hardware watchdog peripheral.

from lib.io import print_str, print_int, print_newline

# ============================================================================
# Watchdog Hardware Registers (placeholder addresses)
# ============================================================================

WDT_BASE: uint32 = 0x40060000

# Register offsets
WDT_CTRL_OFFSET: uint32 = 0x00     # Control register
WDT_LOAD_OFFSET: uint32 = 0x04     # Load/timeout value
WDT_VALUE_OFFSET: uint32 = 0x08    # Current counter value
WDT_INTCLR_OFFSET: uint32 = 0x0C   # Interrupt clear
WDT_RIS_OFFSET: uint32 = 0x10      # Raw interrupt status
WDT_MIS_OFFSET: uint32 = 0x14      # Masked interrupt status
WDT_LOCK_OFFSET: uint32 = 0xC00    # Lock register

# Control register bits
WDT_CTRL_INTEN: uint32 = 0x01      # Interrupt enable
WDT_CTRL_RESEN: uint32 = 0x02      # Reset enable

# Lock register magic values
WDT_UNLOCK: uint32 = 0x1ACCE551    # Unlock key
WDT_LOCK: uint32 = 0x00000001      # Lock (any non-unlock value)

# ============================================================================
# Memory-Mapped I/O Helpers
# ============================================================================

def _wdt_read(offset: uint32) -> uint32:
    """Read from watchdog register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](WDT_BASE + offset)
    return ptr[0]

def _wdt_write(offset: uint32, val: uint32):
    """Write to watchdog register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](WDT_BASE + offset)
    ptr[0] = val

# ============================================================================
# Watchdog State (for emulation mode)
# ============================================================================

# Emulation mode flag (True for QEMU, False for real hardware)
_wdt_emulated: bool = True

# Watchdog enabled flag
_wdt_enabled: bool = False

# Timeout period in milliseconds
_wdt_timeout_ms: int32 = 1000

# Last feed timestamp (kernel ticks)
_wdt_last_feed: int32 = 0

# Warning threshold (percentage of timeout before warning callback)
_wdt_warning_threshold: int32 = 80

# Callback function pointer for pre-reset warning
_wdt_warning_callback: Ptr[void] = Ptr[void](0)

# Health check counters
_wdt_feed_count: int32 = 0
_wdt_warning_count: int32 = 0
_wdt_health_flags: uint32 = 0

# Health flag bits
WDT_HEALTH_OK: uint32 = 0x00
WDT_HEALTH_LATE_FEED: uint32 = 0x01
WDT_HEALTH_MISSED_FEED: uint32 = 0x02
WDT_HEALTH_WARNING_FIRED: uint32 = 0x04

# ============================================================================
# Watchdog Timer Functions
# ============================================================================

def wdt_init(timeout_ms: int32, emulated: bool):
    """Initialize watchdog timer.

    Args:
        timeout_ms: Timeout period in milliseconds
        emulated: True for software timer (QEMU), False for hardware
    """
    global _wdt_emulated, _wdt_enabled, _wdt_timeout_ms
    global _wdt_last_feed, _wdt_feed_count, _wdt_warning_count
    global _wdt_health_flags

    _wdt_emulated = emulated
    _wdt_timeout_ms = timeout_ms
    _wdt_enabled = False
    _wdt_last_feed = 0
    _wdt_feed_count = 0
    _wdt_warning_count = 0
    _wdt_health_flags = WDT_HEALTH_OK

    if not emulated:
        # Hardware watchdog initialization
        # Unlock registers
        _wdt_write(WDT_LOCK_OFFSET, WDT_UNLOCK)

        # Set timeout value (assuming 1kHz WDT clock)
        # Load value = timeout_ms * clock_freq / 1000
        load_val: uint32 = cast[uint32](timeout_ms)
        _wdt_write(WDT_LOAD_OFFSET, load_val)

        # Clear any pending interrupt
        _wdt_write(WDT_INTCLR_OFFSET, 1)

        # Lock registers
        _wdt_write(WDT_LOCK_OFFSET, WDT_LOCK)

def wdt_start():
    """Start the watchdog timer."""
    global _wdt_enabled, _wdt_last_feed

    state: int32 = critical_enter()

    # Get current time from kernel timer
    _wdt_last_feed = timer_get_ticks()
    _wdt_enabled = True

    if not _wdt_emulated:
        # Enable hardware watchdog
        _wdt_write(WDT_LOCK_OFFSET, WDT_UNLOCK)
        _wdt_write(WDT_CTRL_OFFSET, WDT_CTRL_INTEN | WDT_CTRL_RESEN)
        _wdt_write(WDT_LOCK_OFFSET, WDT_LOCK)

    critical_exit(state)

def wdt_stop():
    """Stop the watchdog timer (if allowed by hardware)."""
    global _wdt_enabled

    state: int32 = critical_enter()

    _wdt_enabled = False

    if not _wdt_emulated:
        # Disable hardware watchdog (may not be allowed on some MCUs)
        _wdt_write(WDT_LOCK_OFFSET, WDT_UNLOCK)
        _wdt_write(WDT_CTRL_OFFSET, 0)
        _wdt_write(WDT_LOCK_OFFSET, WDT_LOCK)

    critical_exit(state)

def wdt_feed():
    """Feed/kick the watchdog timer to prevent reset.

    This should be called periodically within the timeout period.
    """
    global _wdt_last_feed, _wdt_feed_count, _wdt_health_flags

    state: int32 = critical_enter()

    if not _wdt_enabled:
        critical_exit(state)
        return

    current_time: int32 = timer_get_ticks()

    # Check if we're feeding late (past warning threshold)
    elapsed: int32 = current_time - _wdt_last_feed
    threshold_time: int32 = (_wdt_timeout_ms * _wdt_warning_threshold) / 100

    if elapsed > threshold_time:
        _wdt_health_flags = _wdt_health_flags | WDT_HEALTH_LATE_FEED

    _wdt_last_feed = current_time
    _wdt_feed_count = _wdt_feed_count + 1

    if not _wdt_emulated:
        # Reload hardware watchdog
        _wdt_write(WDT_LOCK_OFFSET, WDT_UNLOCK)
        _wdt_write(WDT_INTCLR_OFFSET, 1)  # Clear interrupt
        _wdt_write(WDT_LOAD_OFFSET, cast[uint32](_wdt_timeout_ms))
        _wdt_write(WDT_LOCK_OFFSET, WDT_LOCK)

    critical_exit(state)

def wdt_kick():
    """Alias for wdt_feed()."""
    wdt_feed()

def wdt_get_remaining() -> int32:
    """Get time remaining before watchdog reset (in milliseconds).

    Returns:
        Milliseconds remaining, or -1 if watchdog not enabled
    """
    if not _wdt_enabled:
        return -1

    state: int32 = critical_enter()

    remaining: int32 = 0

    if _wdt_emulated:
        # Software calculation
        current_time: int32 = timer_get_ticks()
        elapsed: int32 = current_time - _wdt_last_feed
        remaining = _wdt_timeout_ms - elapsed
        if remaining < 0:
            remaining = 0
    else:
        # Read hardware counter
        current_val: uint32 = _wdt_read(WDT_VALUE_OFFSET)
        remaining = cast[int32](current_val)

    critical_exit(state)
    return remaining

def wdt_get_elapsed() -> int32:
    """Get time elapsed since last feed (in milliseconds).

    Returns:
        Milliseconds elapsed, or -1 if watchdog not enabled
    """
    if not _wdt_enabled:
        return -1

    state: int32 = critical_enter()
    current_time: int32 = timer_get_ticks()
    elapsed: int32 = current_time - _wdt_last_feed
    critical_exit(state)

    return elapsed

def wdt_set_timeout(timeout_ms: int32):
    """Change the watchdog timeout period.

    Args:
        timeout_ms: New timeout in milliseconds
    """
    global _wdt_timeout_ms

    state: int32 = critical_enter()

    _wdt_timeout_ms = timeout_ms

    if not _wdt_emulated and _wdt_enabled:
        # Update hardware
        _wdt_write(WDT_LOCK_OFFSET, WDT_UNLOCK)
        _wdt_write(WDT_LOAD_OFFSET, cast[uint32](timeout_ms))
        _wdt_write(WDT_LOCK_OFFSET, WDT_LOCK)

    critical_exit(state)

def wdt_get_timeout() -> int32:
    """Get current watchdog timeout period.

    Returns:
        Timeout in milliseconds
    """
    return _wdt_timeout_ms

# ============================================================================
# Warning Callback
# ============================================================================

def wdt_set_warning_callback(callback: Ptr[void], threshold_percent: int32):
    """Set callback to be called before watchdog reset.

    The callback is invoked during wdt_check() when elapsed time
    exceeds the threshold percentage of the timeout period.

    Args:
        callback: Function pointer to call (void function())
        threshold_percent: Percentage of timeout before warning (0-100)
    """
    global _wdt_warning_callback, _wdt_warning_threshold

    _wdt_warning_callback = callback
    if threshold_percent < 0:
        threshold_percent = 0
    if threshold_percent > 100:
        threshold_percent = 100
    _wdt_warning_threshold = threshold_percent

def wdt_clear_warning_callback():
    """Clear the warning callback."""
    global _wdt_warning_callback
    _wdt_warning_callback = Ptr[void](0)

# ============================================================================
# Periodic Check (for emulated mode)
# ============================================================================

def wdt_check() -> bool:
    """Check watchdog status and invoke callbacks if needed.

    This should be called periodically in the main loop when using
    emulated mode. In hardware mode, the watchdog handles reset
    automatically.

    Returns:
        True if watchdog is OK, False if timeout expired (in emulated mode)
    """
    global _wdt_warning_count, _wdt_health_flags

    if not _wdt_enabled:
        return True

    state: int32 = critical_enter()

    current_time: int32 = timer_get_ticks()
    elapsed: int32 = current_time - _wdt_last_feed

    # Check warning threshold
    threshold_time: int32 = (_wdt_timeout_ms * _wdt_warning_threshold) / 100

    if elapsed > threshold_time:
        # Fire warning callback if set
        if _wdt_warning_callback != Ptr[void](0):
            _wdt_health_flags = _wdt_health_flags | WDT_HEALTH_WARNING_FIRED
            _wdt_warning_count = _wdt_warning_count + 1
            critical_exit(state)

            # Call the warning callback
            callback_fn: Ptr[def()]  = cast[Ptr[def()]](_wdt_warning_callback)
            callback_fn()

            return True

    # Check timeout expiry (emulated mode only)
    if _wdt_emulated and elapsed >= _wdt_timeout_ms:
        _wdt_health_flags = _wdt_health_flags | WDT_HEALTH_MISSED_FEED
        critical_exit(state)

        # In emulated mode, we return False to indicate timeout
        # Real hardware would reset the system here
        return False

    critical_exit(state)
    return True

def wdt_force_reset():
    """Force an immediate system reset via watchdog.

    In emulated mode, this sets the internal flag.
    In hardware mode, this triggers hardware reset.
    """
    global _wdt_health_flags

    _wdt_health_flags = _wdt_health_flags | WDT_HEALTH_MISSED_FEED

    if not _wdt_emulated:
        # Trigger hardware reset by setting timeout to 0 and not feeding
        _wdt_write(WDT_LOCK_OFFSET, WDT_UNLOCK)
        _wdt_write(WDT_LOAD_OFFSET, 1)  # Minimum timeout
        _wdt_write(WDT_CTRL_OFFSET, WDT_CTRL_RESEN | WDT_CTRL_INTEN)
        _wdt_write(WDT_LOCK_OFFSET, WDT_LOCK)
        # Busy wait for reset
        while True:
            pass

# ============================================================================
# Health Monitoring
# ============================================================================

def wdt_get_feed_count() -> int32:
    """Get total number of times watchdog has been fed.

    Returns:
        Feed count since initialization
    """
    return _wdt_feed_count

def wdt_get_warning_count() -> int32:
    """Get number of times warning callback was fired.

    Returns:
        Warning count since initialization
    """
    return _wdt_warning_count

def wdt_get_health_flags() -> uint32:
    """Get health status flags.

    Returns:
        Bitmask of WDT_HEALTH_* flags
    """
    return _wdt_health_flags

def wdt_clear_health_flags():
    """Clear all health status flags."""
    global _wdt_health_flags
    _wdt_health_flags = WDT_HEALTH_OK

def wdt_is_healthy() -> bool:
    """Check if watchdog system is healthy.

    Returns:
        True if no health issues detected
    """
    return _wdt_health_flags == WDT_HEALTH_OK

def wdt_is_enabled() -> bool:
    """Check if watchdog is currently enabled.

    Returns:
        True if watchdog is running
    """
    return _wdt_enabled

# ============================================================================
# System Health Checks
# ============================================================================

# Health check function pointers (up to 8 checks)
_health_checks: Array[8, Ptr[void]]
_health_check_count: int32 = 0

def wdt_register_health_check(check_fn: Ptr[void]) -> int32:
    """Register a health check function.

    Health check functions should return 0 for OK, non-zero for failure.
    They are called by wdt_run_health_checks().

    Args:
        check_fn: Function pointer (int32 function())

    Returns:
        Index of registered check, or -1 if table full
    """
    global _health_check_count

    if _health_check_count >= 8:
        return -1

    _health_checks[_health_check_count] = check_fn
    idx: int32 = _health_check_count
    _health_check_count = _health_check_count + 1

    return idx

def wdt_clear_health_checks():
    """Clear all registered health check functions."""
    global _health_check_count

    i: int32 = 0
    while i < 8:
        _health_checks[i] = Ptr[void](0)
        i = i + 1

    _health_check_count = 0

def wdt_run_health_checks() -> int32:
    """Run all registered health check functions.

    Returns:
        Number of failed checks (0 = all OK)
    """
    failed: int32 = 0

    i: int32 = 0
    while i < _health_check_count:
        if _health_checks[i] != Ptr[void](0):
            check_fn: Ptr[def() -> int32] = cast[Ptr[def() -> int32]](_health_checks[i])
            result: int32 = check_fn()
            if result != 0:
                failed = failed + 1
        i = i + 1

    return failed

def wdt_health_check_and_feed() -> bool:
    """Run health checks and feed watchdog if all pass.

    This is a convenience function that combines health checking
    with watchdog feeding. Only feeds if all checks pass.

    Returns:
        True if all health checks passed and watchdog was fed
    """
    failed: int32 = wdt_run_health_checks()

    if failed == 0:
        wdt_feed()
        return True

    return False

# ============================================================================
# Debug Functions
# ============================================================================

def wdt_print_status():
    """Print watchdog status information."""
    print_str("Watchdog Status:\n")
    print_str("  Enabled: ")
    if _wdt_enabled:
        print_str("yes\n")
    else:
        print_str("no\n")

    print_str("  Emulated: ")
    if _wdt_emulated:
        print_str("yes\n")
    else:
        print_str("no\n")

    print_str("  Timeout: ")
    print_int(_wdt_timeout_ms)
    print_str(" ms\n")

    if _wdt_enabled:
        print_str("  Remaining: ")
        print_int(wdt_get_remaining())
        print_str(" ms\n")

        print_str("  Elapsed: ")
        print_int(wdt_get_elapsed())
        print_str(" ms\n")

    print_str("  Feed count: ")
    print_int(_wdt_feed_count)
    print_newline()

    print_str("  Warning count: ")
    print_int(_wdt_warning_count)
    print_newline()

    print_str("  Health flags: ")
    print_int(cast[int32](_wdt_health_flags))
    print_newline()

# External timer function reference
extern def timer_get_ticks() -> int32
extern def critical_enter() -> int32
extern def critical_exit(state: int32)
