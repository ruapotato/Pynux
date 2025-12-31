# RP2040 Real-Time Clock (RTC) Driver
#
# The RP2040 RTC runs from a 1Hz clock derived from the external crystal.
# Features:
#   - Full calendar: year, month, day, day of week, hour, minute, second
#   - Alarm with match on any/all fields
#   - Interrupt on alarm match
#
# Clock source: 12MHz XOSC / 12000000 = 1Hz (configured in clk_rtc)

# ============================================================================
# Base Addresses
# ============================================================================

RTC_BASE: uint32 = 0x4005C000
CLOCKS_BASE: uint32 = 0x40008000
RESETS_BASE: uint32 = 0x4000C000

# ============================================================================
# RTC Register Offsets
# ============================================================================

RTC_CLKDIV_M1: uint32 = 0x00    # Clock divider minus 1
RTC_SETUP_0: uint32 = 0x04      # Year, month, day
RTC_SETUP_1: uint32 = 0x08      # Day of week, hour, min, sec
RTC_CTRL: uint32 = 0x0C         # Control register
RTC_IRQ_SETUP_0: uint32 = 0x10  # Alarm year, month, day
RTC_IRQ_SETUP_1: uint32 = 0x14  # Alarm dow, hour, min, sec
RTC_RTC_1: uint32 = 0x18        # Read: year, month, day
RTC_RTC_0: uint32 = 0x1C        # Read: dow, hour, min, sec
RTC_INTR: uint32 = 0x20         # Raw interrupt
RTC_INTE: uint32 = 0x24         # Interrupt enable
RTC_INTF: uint32 = 0x28         # Interrupt force
RTC_INTS: uint32 = 0x2C         # Interrupt status

# CTRL register bits
RTC_CTRL_ENABLE: uint32 = 0x01
RTC_CTRL_LOAD: uint32 = 0x10
RTC_CTRL_RTC_ACTIVE: uint32 = 0x02
RTC_CTRL_FORCE_NOTLEAPYEAR: uint32 = 0x100

# SETUP_0 field positions
RTC_SETUP0_YEAR_SHIFT: uint32 = 12
RTC_SETUP0_MONTH_SHIFT: uint32 = 8
RTC_SETUP0_DAY_SHIFT: uint32 = 0

# SETUP_1 field positions
RTC_SETUP1_DOTW_SHIFT: uint32 = 24
RTC_SETUP1_HOUR_SHIFT: uint32 = 16
RTC_SETUP1_MIN_SHIFT: uint32 = 8
RTC_SETUP1_SEC_SHIFT: uint32 = 0

# IRQ_SETUP match enable bits
RTC_IRQ_MATCH_ENA: uint32 = 0x10000000

# ============================================================================
# Clock Configuration
# ============================================================================

CLK_RTC_CTRL: uint32 = 0x6C
CLK_RTC_DIV: uint32 = 0x70

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
# RTC Initialization
# ============================================================================

def rtc_init():
    """Initialize the RTC peripheral.

    Configures the RTC clock divider for 1Hz operation from 12MHz XOSC.
    """
    # Unreset RTC
    reset_val: uint32 = mmio_read(RESETS_BASE)
    mmio_write(RESETS_BASE, reset_val & ~(1 << 25))  # RTC reset bit

    # Wait for reset done
    timeout: int32 = 10000
    while timeout > 0:
        done: uint32 = mmio_read(RESETS_BASE + 0x08)
        if (done & (1 << 25)) != 0:
            break
        timeout = timeout - 1

    # Configure clock divider: 12MHz / 1Hz - 1 = 11999999
    # The RTC needs 1Hz input
    mmio_write(RTC_BASE + RTC_CLKDIV_M1, 12000000 - 1)

    # Disable RTC while configuring
    mmio_write(RTC_BASE + RTC_CTRL, 0)

def rtc_set_datetime(year: uint32, month: uint32, day: uint32,
                     dotw: uint32, hour: uint32, min: uint32, sec: uint32):
    """Set the RTC date and time.

    Args:
        year: Year (0-4095)
        month: Month (1-12)
        day: Day of month (1-31)
        dotw: Day of week (0=Sunday, 6=Saturday)
        hour: Hour (0-23)
        min: Minute (0-59)
        sec: Second (0-59)
    """
    # Disable RTC
    mmio_write(RTC_BASE + RTC_CTRL, 0)

    # Set date: year, month, day
    setup_0: uint32 = ((year & 0xFFF) << RTC_SETUP0_YEAR_SHIFT) | \
                      ((month & 0x0F) << RTC_SETUP0_MONTH_SHIFT) | \
                      ((day & 0x1F) << RTC_SETUP0_DAY_SHIFT)
    mmio_write(RTC_BASE + RTC_SETUP_0, setup_0)

    # Set time: day of week, hour, minute, second
    setup_1: uint32 = ((dotw & 0x07) << RTC_SETUP1_DOTW_SHIFT) | \
                      ((hour & 0x1F) << RTC_SETUP1_HOUR_SHIFT) | \
                      ((min & 0x3F) << RTC_SETUP1_MIN_SHIFT) | \
                      ((sec & 0x3F) << RTC_SETUP1_SEC_SHIFT)
    mmio_write(RTC_BASE + RTC_SETUP_1, setup_1)

    # Load values into RTC
    mmio_write(RTC_BASE + RTC_CTRL, RTC_CTRL_LOAD)

    # Enable RTC
    mmio_write(RTC_BASE + RTC_CTRL, RTC_CTRL_ENABLE)

    # Wait for RTC to become active
    timeout: int32 = 10000
    while timeout > 0:
        ctrl: uint32 = mmio_read(RTC_BASE + RTC_CTRL)
        if (ctrl & RTC_CTRL_RTC_ACTIVE) != 0:
            break
        timeout = timeout - 1

def rtc_get_datetime(year: Ptr[uint32], month: Ptr[uint32], day: Ptr[uint32],
                     dotw: Ptr[uint32], hour: Ptr[uint32], min: Ptr[uint32], sec: Ptr[uint32]):
    """Read the current RTC date and time.

    Args:
        year: Pointer to store year
        month: Pointer to store month
        day: Pointer to store day
        dotw: Pointer to store day of week
        hour: Pointer to store hour
        min: Pointer to store minute
        sec: Pointer to store second
    """
    # Read RTC_1 first (latches RTC_0)
    rtc_1: uint32 = mmio_read(RTC_BASE + RTC_RTC_1)
    rtc_0: uint32 = mmio_read(RTC_BASE + RTC_RTC_0)

    # Extract date fields
    year[0] = (rtc_1 >> 12) & 0xFFF
    month[0] = (rtc_1 >> 8) & 0x0F
    day[0] = rtc_1 & 0x1F

    # Extract time fields
    dotw[0] = (rtc_0 >> 24) & 0x07
    hour[0] = (rtc_0 >> 16) & 0x1F
    min[0] = (rtc_0 >> 8) & 0x3F
    sec[0] = rtc_0 & 0x3F

def rtc_get_time_packed() -> uint32:
    """Get time as packed value HHMMSS (BCD-like).

    Returns:
        Packed time (e.g., 143025 for 14:30:25)
    """
    rtc_1: uint32 = mmio_read(RTC_BASE + RTC_RTC_1)
    rtc_0: uint32 = mmio_read(RTC_BASE + RTC_RTC_0)

    hour: uint32 = (rtc_0 >> 16) & 0x1F
    min: uint32 = (rtc_0 >> 8) & 0x3F
    sec: uint32 = rtc_0 & 0x3F

    return hour * 10000 + min * 100 + sec

def rtc_get_date_packed() -> uint32:
    """Get date as packed value YYYYMMDD.

    Returns:
        Packed date (e.g., 20241225 for Dec 25, 2024)
    """
    rtc_1: uint32 = mmio_read(RTC_BASE + RTC_RTC_1)

    year: uint32 = (rtc_1 >> 12) & 0xFFF
    month: uint32 = (rtc_1 >> 8) & 0x0F
    day: uint32 = rtc_1 & 0x1F

    return year * 10000 + month * 100 + day

# ============================================================================
# RTC Alarm
# ============================================================================

def rtc_set_alarm(year: int32, month: int32, day: int32,
                  dotw: int32, hour: int32, min: int32, sec: int32):
    """Set RTC alarm.

    Any field set to -1 is ignored (wildcard match).

    Args:
        year: Year to match (-1 for any)
        month: Month to match (-1 for any)
        day: Day to match (-1 for any)
        dotw: Day of week to match (-1 for any)
        hour: Hour to match (-1 for any)
        min: Minute to match (-1 for any)
        sec: Second to match (-1 for any)
    """
    # Build IRQ_SETUP_0: year, month, day with match enables
    irq_0: uint32 = 0
    if year >= 0:
        irq_0 = irq_0 | (cast[uint32](year) & 0xFFF) << 12
        irq_0 = irq_0 | (1 << 26)  # YEAR_ENA
    if month >= 0:
        irq_0 = irq_0 | (cast[uint32](month) & 0x0F) << 8
        irq_0 = irq_0 | (1 << 25)  # MONTH_ENA
    if day >= 0:
        irq_0 = irq_0 | (cast[uint32](day) & 0x1F)
        irq_0 = irq_0 | (1 << 24)  # DAY_ENA

    mmio_write(RTC_BASE + RTC_IRQ_SETUP_0, irq_0)

    # Build IRQ_SETUP_1: dotw, hour, min, sec with match enables
    irq_1: uint32 = 0
    if dotw >= 0:
        irq_1 = irq_1 | (cast[uint32](dotw) & 0x07) << 24
        irq_1 = irq_1 | (1 << 31)  # DOTW_ENA
    if hour >= 0:
        irq_1 = irq_1 | (cast[uint32](hour) & 0x1F) << 16
        irq_1 = irq_1 | (1 << 30)  # HOUR_ENA
    if min >= 0:
        irq_1 = irq_1 | (cast[uint32](min) & 0x3F) << 8
        irq_1 = irq_1 | (1 << 29)  # MIN_ENA
    if sec >= 0:
        irq_1 = irq_1 | (cast[uint32](sec) & 0x3F)
        irq_1 = irq_1 | (1 << 28)  # SEC_ENA

    mmio_write(RTC_BASE + RTC_IRQ_SETUP_1, irq_1)

def rtc_enable_alarm():
    """Enable RTC alarm interrupt."""
    # Set global match enable
    irq_0: uint32 = mmio_read(RTC_BASE + RTC_IRQ_SETUP_0)
    mmio_write(RTC_BASE + RTC_IRQ_SETUP_0, irq_0 | RTC_IRQ_MATCH_ENA)

    # Enable interrupt
    mmio_write(RTC_BASE + RTC_INTE, 1)

def rtc_disable_alarm():
    """Disable RTC alarm interrupt."""
    irq_0: uint32 = mmio_read(RTC_BASE + RTC_IRQ_SETUP_0)
    mmio_write(RTC_BASE + RTC_IRQ_SETUP_0, irq_0 & ~RTC_IRQ_MATCH_ENA)
    mmio_write(RTC_BASE + RTC_INTE, 0)

def rtc_alarm_pending() -> bool:
    """Check if alarm interrupt is pending.

    Returns:
        True if alarm triggered
    """
    ints: uint32 = mmio_read(RTC_BASE + RTC_INTS)
    return (ints & 1) != 0

def rtc_clear_alarm():
    """Clear alarm interrupt."""
    # Disable and re-enable to clear
    irq_0: uint32 = mmio_read(RTC_BASE + RTC_IRQ_SETUP_0)
    mmio_write(RTC_BASE + RTC_IRQ_SETUP_0, irq_0 & ~RTC_IRQ_MATCH_ENA)
    mmio_write(RTC_BASE + RTC_IRQ_SETUP_0, irq_0)

# ============================================================================
# Convenience Functions
# ============================================================================

def rtc_set_time(hour: uint32, min: uint32, sec: uint32):
    """Set only the time (preserves date).

    Args:
        hour: Hour (0-23)
        min: Minute (0-59)
        sec: Second (0-59)
    """
    # Read current date
    rtc_1: uint32 = mmio_read(RTC_BASE + RTC_RTC_1)
    rtc_0: uint32 = mmio_read(RTC_BASE + RTC_RTC_0)

    year: uint32 = (rtc_1 >> 12) & 0xFFF
    month: uint32 = (rtc_1 >> 8) & 0x0F
    day: uint32 = rtc_1 & 0x1F
    dotw: uint32 = (rtc_0 >> 24) & 0x07

    rtc_set_datetime(year, month, day, dotw, hour, min, sec)

def rtc_set_date(year: uint32, month: uint32, day: uint32, dotw: uint32):
    """Set only the date (preserves time).

    Args:
        year: Year (0-4095)
        month: Month (1-12)
        day: Day (1-31)
        dotw: Day of week (0-6)
    """
    # Read current time
    rtc_1: uint32 = mmio_read(RTC_BASE + RTC_RTC_1)
    rtc_0: uint32 = mmio_read(RTC_BASE + RTC_RTC_0)

    hour: uint32 = (rtc_0 >> 16) & 0x1F
    min: uint32 = (rtc_0 >> 8) & 0x3F
    sec: uint32 = rtc_0 & 0x3F

    rtc_set_datetime(year, month, day, dotw, hour, min, sec)

def rtc_running() -> bool:
    """Check if RTC is running.

    Returns:
        True if RTC is active
    """
    ctrl: uint32 = mmio_read(RTC_BASE + RTC_CTRL)
    return (ctrl & RTC_CTRL_RTC_ACTIVE) != 0
