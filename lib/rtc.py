# Pynux Real-Time Clock Library
#
# RTC abstraction for ARM Cortex-M3.
# Provides time/date tracking, alarms, and calendar utilities.
#
# For QEMU emulation, uses kernel timer ticks to track time.
# On real hardware, would use hardware RTC peripheral.

from lib.io import print_str, print_int, print_newline

# ============================================================================
# RTC Hardware Registers (placeholder addresses)
# ============================================================================

RTC_BASE: uint32 = 0x40070000

# Register offsets
RTC_DR_OFFSET: uint32 = 0x00      # Data register (date/time)
RTC_MR_OFFSET: uint32 = 0x04      # Match register (alarm)
RTC_LR_OFFSET: uint32 = 0x08      # Load register
RTC_CR_OFFSET: uint32 = 0x0C      # Control register
RTC_IMSC_OFFSET: uint32 = 0x10    # Interrupt mask
RTC_RIS_OFFSET: uint32 = 0x14     # Raw interrupt status
RTC_MIS_OFFSET: uint32 = 0x18     # Masked interrupt status
RTC_ICR_OFFSET: uint32 = 0x1C     # Interrupt clear

# Control register bits
RTC_CR_START: uint32 = 0x01       # RTC enable

# ============================================================================
# Memory-Mapped I/O Helpers
# ============================================================================

def _rtc_read(offset: uint32) -> uint32:
    """Read from RTC register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](RTC_BASE + offset)
    return ptr[0]

def _rtc_write(offset: uint32, val: uint32):
    """Write to RTC register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](RTC_BASE + offset)
    ptr[0] = val

# ============================================================================
# RTC State (for emulation mode)
# ============================================================================

# Emulation mode flag
_rtc_emulated: bool = True

# Current time components (24-hour format)
_rtc_hours: int32 = 0
_rtc_minutes: int32 = 0
_rtc_seconds: int32 = 0

# Current date components
_rtc_year: int32 = 2024
_rtc_month: int32 = 1
_rtc_day: int32 = 1

# Tick tracking for emulation
_rtc_last_tick: int32 = 0
_rtc_tick_accum: int32 = 0    # Accumulated milliseconds
_rtc_initialized: bool = False

# Uptime tracking (seconds since init)
_rtc_uptime: int32 = 0

# Alarm settings
_rtc_alarm_enabled: bool = False
_rtc_alarm_hours: int32 = 0
_rtc_alarm_minutes: int32 = 0
_rtc_alarm_seconds: int32 = 0
_rtc_alarm_callback: Ptr[void] = Ptr[void](0)
_rtc_alarm_triggered: bool = False

# Days in each month (index 0 unused, 1=Jan, 12=Dec)
_days_in_month: Array[13, int32]

# ============================================================================
# Calendar Utilities
# ============================================================================

def _init_days_in_month():
    """Initialize days-in-month table."""
    global _days_in_month
    _days_in_month[0] = 0   # Unused
    _days_in_month[1] = 31  # January
    _days_in_month[2] = 28  # February (non-leap)
    _days_in_month[3] = 31  # March
    _days_in_month[4] = 30  # April
    _days_in_month[5] = 31  # May
    _days_in_month[6] = 30  # June
    _days_in_month[7] = 31  # July
    _days_in_month[8] = 31  # August
    _days_in_month[9] = 30  # September
    _days_in_month[10] = 31 # October
    _days_in_month[11] = 30 # November
    _days_in_month[12] = 31 # December

def rtc_is_leap_year(year: int32) -> bool:
    """Check if a year is a leap year.

    Args:
        year: 4-digit year

    Returns:
        True if leap year
    """
    if (year % 400) == 0:
        return True
    if (year % 100) == 0:
        return False
    if (year % 4) == 0:
        return True
    return False

def rtc_days_in_month(year: int32, month: int32) -> int32:
    """Get number of days in a given month.

    Args:
        year: 4-digit year
        month: Month (1-12)

    Returns:
        Number of days in the month
    """
    if month < 1 or month > 12:
        return 0

    days: int32 = _days_in_month[month]

    # Adjust February for leap years
    if month == 2 and rtc_is_leap_year(year):
        days = 29

    return days

def rtc_day_of_week(year: int32, month: int32, day: int32) -> int32:
    """Calculate day of week using Zeller's congruence.

    Args:
        year: 4-digit year
        month: Month (1-12)
        day: Day of month (1-31)

    Returns:
        Day of week (0=Sunday, 1=Monday, ..., 6=Saturday)
    """
    # Adjust for Zeller's formula (Jan/Feb are months 13/14 of previous year)
    m: int32 = month
    y: int32 = year

    if m < 3:
        m = m + 12
        y = y - 1

    k: int32 = y % 100
    j: int32 = y / 100

    # Zeller's formula
    h: int32 = day + ((13 * (m + 1)) / 5) + k + (k / 4) + (j / 4) - (2 * j)

    # Convert to 0-6 range (0=Sunday)
    dow: int32 = ((h % 7) + 7) % 7

    # Zeller gives Saturday=0, adjust to Sunday=0
    dow = (dow + 6) % 7

    return dow

def rtc_day_of_year(year: int32, month: int32, day: int32) -> int32:
    """Calculate day of year (1-366).

    Args:
        year: 4-digit year
        month: Month (1-12)
        day: Day of month (1-31)

    Returns:
        Day of year (1-366)
    """
    doy: int32 = 0
    m: int32 = 1

    while m < month:
        doy = doy + rtc_days_in_month(year, m)
        m = m + 1

    doy = doy + day

    return doy

def rtc_is_valid_date(year: int32, month: int32, day: int32) -> bool:
    """Validate a date.

    Args:
        year: 4-digit year
        month: Month (1-12)
        day: Day of month (1-31)

    Returns:
        True if valid date
    """
    if year < 1 or year > 9999:
        return False
    if month < 1 or month > 12:
        return False
    if day < 1:
        return False
    if day > rtc_days_in_month(year, month):
        return False
    return True

def rtc_is_valid_time(hours: int32, minutes: int32, seconds: int32) -> bool:
    """Validate a time.

    Args:
        hours: Hours (0-23)
        minutes: Minutes (0-59)
        seconds: Seconds (0-59)

    Returns:
        True if valid time
    """
    if hours < 0 or hours > 23:
        return False
    if minutes < 0 or minutes > 59:
        return False
    if seconds < 0 or seconds > 59:
        return False
    return True

# ============================================================================
# RTC Initialization
# ============================================================================

def rtc_init(emulated: bool):
    """Initialize the RTC.

    Args:
        emulated: True for software timer (QEMU), False for hardware
    """
    global _rtc_emulated, _rtc_initialized, _rtc_last_tick
    global _rtc_tick_accum, _rtc_uptime

    _init_days_in_month()

    _rtc_emulated = emulated
    _rtc_last_tick = timer_get_ticks()
    _rtc_tick_accum = 0
    _rtc_uptime = 0
    _rtc_initialized = True

    if not emulated:
        # Enable hardware RTC
        _rtc_write(RTC_CR_OFFSET, RTC_CR_START)

def rtc_deinit():
    """Deinitialize the RTC."""
    global _rtc_initialized, _rtc_alarm_enabled

    _rtc_initialized = False
    _rtc_alarm_enabled = False

    if not _rtc_emulated:
        _rtc_write(RTC_CR_OFFSET, 0)

# ============================================================================
# Time Functions
# ============================================================================

def rtc_set_time(hours: int32, minutes: int32, seconds: int32) -> bool:
    """Set the current time.

    Args:
        hours: Hours (0-23)
        minutes: Minutes (0-59)
        seconds: Seconds (0-59)

    Returns:
        True if time was valid and set
    """
    global _rtc_hours, _rtc_minutes, _rtc_seconds

    if not rtc_is_valid_time(hours, minutes, seconds):
        return False

    state: int32 = critical_enter()

    _rtc_hours = hours
    _rtc_minutes = minutes
    _rtc_seconds = seconds

    if not _rtc_emulated:
        # Pack time into hardware register format
        # Format: HH:MM:SS as BCD or binary depending on hardware
        time_val: uint32 = cast[uint32](seconds)
        time_val = time_val | (cast[uint32](minutes) << 8)
        time_val = time_val | (cast[uint32](hours) << 16)
        _rtc_write(RTC_LR_OFFSET, time_val)

    critical_exit(state)
    return True

def rtc_get_hours() -> int32:
    """Get current hours (0-23)."""
    return _rtc_hours

def rtc_get_minutes() -> int32:
    """Get current minutes (0-59)."""
    return _rtc_minutes

def rtc_get_seconds() -> int32:
    """Get current seconds (0-59)."""
    return _rtc_seconds

def rtc_get_time(hours: Ptr[int32], minutes: Ptr[int32], seconds: Ptr[int32]):
    """Get current time.

    Args:
        hours: Pointer to store hours
        minutes: Pointer to store minutes
        seconds: Pointer to store seconds
    """
    state: int32 = critical_enter()
    hours[0] = _rtc_hours
    minutes[0] = _rtc_minutes
    seconds[0] = _rtc_seconds
    critical_exit(state)

# ============================================================================
# Date Functions
# ============================================================================

def rtc_set_date(year: int32, month: int32, day: int32) -> bool:
    """Set the current date.

    Args:
        year: 4-digit year
        month: Month (1-12)
        day: Day of month (1-31)

    Returns:
        True if date was valid and set
    """
    global _rtc_year, _rtc_month, _rtc_day

    if not rtc_is_valid_date(year, month, day):
        return False

    state: int32 = critical_enter()

    _rtc_year = year
    _rtc_month = month
    _rtc_day = day

    critical_exit(state)
    return True

def rtc_get_year() -> int32:
    """Get current year."""
    return _rtc_year

def rtc_get_month() -> int32:
    """Get current month (1-12)."""
    return _rtc_month

def rtc_get_day() -> int32:
    """Get current day of month (1-31)."""
    return _rtc_day

def rtc_get_date(year: Ptr[int32], month: Ptr[int32], day: Ptr[int32]):
    """Get current date.

    Args:
        year: Pointer to store year
        month: Pointer to store month
        day: Pointer to store day
    """
    state: int32 = critical_enter()
    year[0] = _rtc_year
    month[0] = _rtc_month
    day[0] = _rtc_day
    critical_exit(state)

def rtc_get_day_of_week() -> int32:
    """Get current day of week (0=Sunday, 6=Saturday)."""
    return rtc_day_of_week(_rtc_year, _rtc_month, _rtc_day)

def rtc_get_day_of_year() -> int32:
    """Get current day of year (1-366)."""
    return rtc_day_of_year(_rtc_year, _rtc_month, _rtc_day)

# ============================================================================
# Timestamp Functions
# ============================================================================

def rtc_to_timestamp() -> int32:
    """Convert current date/time to Unix-like timestamp.

    Returns seconds since 2000-01-01 00:00:00 (epoch for embedded systems).

    Returns:
        Seconds since epoch
    """
    # Calculate days since 2000-01-01
    days: int32 = 0

    # Add days for complete years
    y: int32 = 2000
    while y < _rtc_year:
        if rtc_is_leap_year(y):
            days = days + 366
        else:
            days = days + 365
        y = y + 1

    # Add days for complete months in current year
    m: int32 = 1
    while m < _rtc_month:
        days = days + rtc_days_in_month(_rtc_year, m)
        m = m + 1

    # Add days in current month
    days = days + (_rtc_day - 1)

    # Convert to seconds and add time
    timestamp: int32 = days * 86400  # 24 * 60 * 60
    timestamp = timestamp + (_rtc_hours * 3600)
    timestamp = timestamp + (_rtc_minutes * 60)
    timestamp = timestamp + _rtc_seconds

    return timestamp

def rtc_from_timestamp(timestamp: int32):
    """Set date/time from Unix-like timestamp.

    Expects seconds since 2000-01-01 00:00:00.

    Args:
        timestamp: Seconds since epoch
    """
    global _rtc_year, _rtc_month, _rtc_day
    global _rtc_hours, _rtc_minutes, _rtc_seconds

    state: int32 = critical_enter()

    # Extract time components
    _rtc_seconds = timestamp % 60
    timestamp = timestamp / 60
    _rtc_minutes = timestamp % 60
    timestamp = timestamp / 60
    _rtc_hours = timestamp % 24
    days: int32 = timestamp / 24

    # Calculate year
    _rtc_year = 2000
    while True:
        days_in_year: int32 = 365
        if rtc_is_leap_year(_rtc_year):
            days_in_year = 366
        if days < days_in_year:
            break
        days = days - days_in_year
        _rtc_year = _rtc_year + 1

    # Calculate month
    _rtc_month = 1
    while _rtc_month <= 12:
        dim: int32 = rtc_days_in_month(_rtc_year, _rtc_month)
        if days < dim:
            break
        days = days - dim
        _rtc_month = _rtc_month + 1

    # Day
    _rtc_day = days + 1

    critical_exit(state)

def rtc_get_timestamp() -> int32:
    """Get current timestamp (alias for rtc_to_timestamp)."""
    return rtc_to_timestamp()

# ============================================================================
# Uptime Functions
# ============================================================================

def rtc_get_uptime() -> int32:
    """Get system uptime in seconds since RTC initialization.

    Returns:
        Uptime in seconds
    """
    return _rtc_uptime

def rtc_get_uptime_ms() -> int32:
    """Get system uptime in milliseconds.

    Returns:
        Uptime in milliseconds (may wrap around)
    """
    return (_rtc_uptime * 1000) + _rtc_tick_accum

# ============================================================================
# Alarm Functions
# ============================================================================

def rtc_set_alarm(hours: int32, minutes: int32, seconds: int32) -> bool:
    """Set an alarm time.

    Args:
        hours: Hours (0-23)
        minutes: Minutes (0-59)
        seconds: Seconds (0-59)

    Returns:
        True if alarm was set
    """
    global _rtc_alarm_hours, _rtc_alarm_minutes, _rtc_alarm_seconds
    global _rtc_alarm_enabled, _rtc_alarm_triggered

    if not rtc_is_valid_time(hours, minutes, seconds):
        return False

    state: int32 = critical_enter()

    _rtc_alarm_hours = hours
    _rtc_alarm_minutes = minutes
    _rtc_alarm_seconds = seconds
    _rtc_alarm_enabled = True
    _rtc_alarm_triggered = False

    if not _rtc_emulated:
        # Set hardware alarm register
        alarm_val: uint32 = cast[uint32](seconds)
        alarm_val = alarm_val | (cast[uint32](minutes) << 8)
        alarm_val = alarm_val | (cast[uint32](hours) << 16)
        _rtc_write(RTC_MR_OFFSET, alarm_val)
        # Enable alarm interrupt
        _rtc_write(RTC_IMSC_OFFSET, 1)

    critical_exit(state)
    return True

def rtc_clear_alarm():
    """Disable/clear the alarm."""
    global _rtc_alarm_enabled, _rtc_alarm_triggered

    state: int32 = critical_enter()

    _rtc_alarm_enabled = False
    _rtc_alarm_triggered = False

    if not _rtc_emulated:
        _rtc_write(RTC_IMSC_OFFSET, 0)

    critical_exit(state)

def rtc_set_alarm_callback(callback: Ptr[void]):
    """Set callback function for alarm.

    Args:
        callback: Function pointer (void function())
    """
    global _rtc_alarm_callback
    _rtc_alarm_callback = callback

def rtc_alarm_triggered() -> bool:
    """Check if alarm has triggered.

    Returns:
        True if alarm has fired since last clear
    """
    return _rtc_alarm_triggered

def rtc_get_alarm(hours: Ptr[int32], minutes: Ptr[int32], seconds: Ptr[int32]):
    """Get current alarm time.

    Args:
        hours: Pointer to store hours
        minutes: Pointer to store minutes
        seconds: Pointer to store seconds
    """
    hours[0] = _rtc_alarm_hours
    minutes[0] = _rtc_alarm_minutes
    seconds[0] = _rtc_alarm_seconds

def rtc_alarm_enabled() -> bool:
    """Check if alarm is enabled."""
    return _rtc_alarm_enabled

# ============================================================================
# Tick Update (for emulation mode)
# ============================================================================

def rtc_tick():
    """Update RTC time based on kernel timer ticks.

    This should be called periodically (e.g., in main loop) when using
    emulated mode. It accumulates tick time and updates the clock.
    """
    global _rtc_last_tick, _rtc_tick_accum, _rtc_uptime
    global _rtc_seconds, _rtc_minutes, _rtc_hours
    global _rtc_day, _rtc_month, _rtc_year
    global _rtc_alarm_triggered

    if not _rtc_initialized:
        return

    state: int32 = critical_enter()

    current_tick: int32 = timer_get_ticks()
    elapsed_ms: int32 = current_tick - _rtc_last_tick
    _rtc_last_tick = current_tick

    # Accumulate milliseconds
    _rtc_tick_accum = _rtc_tick_accum + elapsed_ms

    # Update seconds when we've accumulated 1000ms
    while _rtc_tick_accum >= 1000:
        _rtc_tick_accum = _rtc_tick_accum - 1000
        _rtc_uptime = _rtc_uptime + 1
        _rtc_seconds = _rtc_seconds + 1

        # Roll over seconds
        if _rtc_seconds >= 60:
            _rtc_seconds = 0
            _rtc_minutes = _rtc_minutes + 1

            # Roll over minutes
            if _rtc_minutes >= 60:
                _rtc_minutes = 0
                _rtc_hours = _rtc_hours + 1

                # Roll over hours
                if _rtc_hours >= 24:
                    _rtc_hours = 0
                    _rtc_day = _rtc_day + 1

                    # Roll over day
                    dim: int32 = rtc_days_in_month(_rtc_year, _rtc_month)
                    if _rtc_day > dim:
                        _rtc_day = 1
                        _rtc_month = _rtc_month + 1

                        # Roll over month
                        if _rtc_month > 12:
                            _rtc_month = 1
                            _rtc_year = _rtc_year + 1

        # Check alarm
        if _rtc_alarm_enabled and not _rtc_alarm_triggered:
            if _rtc_hours == _rtc_alarm_hours:
                if _rtc_minutes == _rtc_alarm_minutes:
                    if _rtc_seconds == _rtc_alarm_seconds:
                        _rtc_alarm_triggered = True
                        critical_exit(state)

                        # Call alarm callback
                        if _rtc_alarm_callback != Ptr[void](0):
                            callback_fn: Fn[void] = cast[Fn[void]](_rtc_alarm_callback)
                            callback_fn()

                        return

    critical_exit(state)

# ============================================================================
# Formatting Functions
# ============================================================================

def rtc_format_time(buf: Ptr[char]) -> int32:
    """Format current time as HH:MM:SS string.

    Args:
        buf: Buffer to write to (at least 9 bytes)

    Returns:
        Length of string
    """
    # Hours
    buf[0] = cast[char](48 + (_rtc_hours / 10))
    buf[1] = cast[char](48 + (_rtc_hours % 10))
    buf[2] = ':'
    # Minutes
    buf[3] = cast[char](48 + (_rtc_minutes / 10))
    buf[4] = cast[char](48 + (_rtc_minutes % 10))
    buf[5] = ':'
    # Seconds
    buf[6] = cast[char](48 + (_rtc_seconds / 10))
    buf[7] = cast[char](48 + (_rtc_seconds % 10))
    buf[8] = '\0'

    return 8

def rtc_format_date(buf: Ptr[char]) -> int32:
    """Format current date as YYYY-MM-DD string.

    Args:
        buf: Buffer to write to (at least 11 bytes)

    Returns:
        Length of string
    """
    # Year
    y: int32 = _rtc_year
    buf[0] = cast[char](48 + (y / 1000))
    y = y % 1000
    buf[1] = cast[char](48 + (y / 100))
    y = y % 100
    buf[2] = cast[char](48 + (y / 10))
    buf[3] = cast[char](48 + (y % 10))
    buf[4] = '-'
    # Month
    buf[5] = cast[char](48 + (_rtc_month / 10))
    buf[6] = cast[char](48 + (_rtc_month % 10))
    buf[7] = '-'
    # Day
    buf[8] = cast[char](48 + (_rtc_day / 10))
    buf[9] = cast[char](48 + (_rtc_day % 10))
    buf[10] = '\0'

    return 10

def rtc_format_datetime(buf: Ptr[char]) -> int32:
    """Format current date and time as YYYY-MM-DD HH:MM:SS string.

    Args:
        buf: Buffer to write to (at least 20 bytes)

    Returns:
        Length of string
    """
    rtc_format_date(buf)
    buf[10] = ' '
    rtc_format_time(&buf[11])

    return 19

# ============================================================================
# Debug Functions
# ============================================================================

def rtc_print_time():
    """Print current time."""
    buf: Array[12, char]
    rtc_format_time(&buf[0])
    print_str(&buf[0])

def rtc_print_date():
    """Print current date."""
    buf: Array[12, char]
    rtc_format_date(&buf[0])
    print_str(&buf[0])

def rtc_print_datetime():
    """Print current date and time."""
    buf: Array[24, char]
    rtc_format_datetime(&buf[0])
    print_str(&buf[0])

def rtc_print_status():
    """Print RTC status information."""
    print_str("RTC Status:\n")
    print_str("  Date: ")
    rtc_print_date()
    print_newline()

    print_str("  Time: ")
    rtc_print_time()
    print_newline()

    print_str("  Day of week: ")
    dow: int32 = rtc_get_day_of_week()
    dow_names: Array[7, Ptr[char]]
    dow_names[0] = "Sunday"
    dow_names[1] = "Monday"
    dow_names[2] = "Tuesday"
    dow_names[3] = "Wednesday"
    dow_names[4] = "Thursday"
    dow_names[5] = "Friday"
    dow_names[6] = "Saturday"
    print_str(dow_names[dow])
    print_newline()

    print_str("  Day of year: ")
    print_int(rtc_get_day_of_year())
    print_newline()

    print_str("  Uptime: ")
    print_int(_rtc_uptime)
    print_str(" seconds\n")

    print_str("  Timestamp: ")
    print_int(rtc_to_timestamp())
    print_newline()

    if _rtc_alarm_enabled:
        print_str("  Alarm: ")
        buf: Array[12, char]
        buf[0] = cast[char](48 + (_rtc_alarm_hours / 10))
        buf[1] = cast[char](48 + (_rtc_alarm_hours % 10))
        buf[2] = ':'
        buf[3] = cast[char](48 + (_rtc_alarm_minutes / 10))
        buf[4] = cast[char](48 + (_rtc_alarm_minutes % 10))
        buf[5] = ':'
        buf[6] = cast[char](48 + (_rtc_alarm_seconds / 10))
        buf[7] = cast[char](48 + (_rtc_alarm_seconds % 10))
        buf[8] = '\0'
        print_str(&buf[0])
        if _rtc_alarm_triggered:
            print_str(" (triggered)")
        print_newline()

# External function references
extern def timer_get_ticks() -> int32
extern def critical_enter() -> int32
extern def critical_exit(state: int32)
