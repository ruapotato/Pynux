# STM32F4 Real-Time Clock (RTC) Driver
#
# The STM32F4 RTC provides calendar with BCD-coded time/date registers.
# Features:
#   - Full calendar: year (00-99), month, day, day of week, hour, minute, second
#   - Two alarms (Alarm A and Alarm B)
#   - Periodic wakeup timer
#   - Timestamp on tamper event
#   - Backup registers (20 x 32-bit)
#
# Clock sources: LSE (32.768kHz), LSI (~32kHz), HSE/32

# ============================================================================
# Base Addresses
# ============================================================================

RTC_BASE: uint32 = 0x40002800
PWR_BASE: uint32 = 0x40007000
RCC_BASE: uint32 = 0x40023800

# ============================================================================
# RTC Register Offsets
# ============================================================================

RTC_TR: uint32 = 0x00      # Time register
RTC_DR: uint32 = 0x04      # Date register
RTC_CR: uint32 = 0x08      # Control register
RTC_ISR: uint32 = 0x0C     # Initialization and status
RTC_PRER: uint32 = 0x10    # Prescaler register
RTC_WUTR: uint32 = 0x14    # Wakeup timer register
RTC_CALIBR: uint32 = 0x18  # Calibration register
RTC_ALRMAR: uint32 = 0x1C  # Alarm A register
RTC_ALRMBR: uint32 = 0x20  # Alarm B register
RTC_WPR: uint32 = 0x24     # Write protection register
RTC_SSR: uint32 = 0x28     # Sub second register
RTC_SHIFTR: uint32 = 0x2C  # Shift control register
RTC_TSTR: uint32 = 0x30    # Timestamp time register
RTC_TSDR: uint32 = 0x34    # Timestamp date register
RTC_TSSSR: uint32 = 0x38   # Timestamp sub second
RTC_CALR: uint32 = 0x3C    # Calibration register
RTC_TAFCR: uint32 = 0x40   # Tamper and alternate function
RTC_ALRMASSR: uint32 = 0x44  # Alarm A sub second
RTC_ALRMBSSR: uint32 = 0x48  # Alarm B sub second
RTC_BKP0R: uint32 = 0x50   # Backup registers (0-19)

# CR register bits
RTC_CR_WUCKSEL: uint32 = 0x07     # Wakeup clock selection
RTC_CR_TSEDGE: uint32 = 0x08      # Timestamp event edge
RTC_CR_REFCKON: uint32 = 0x10     # Reference clock enable
RTC_CR_BYPSHAD: uint32 = 0x20    # Bypass shadow registers
RTC_CR_FMT: uint32 = 0x40         # Hour format (0=24h, 1=12h)
RTC_CR_ALRAE: uint32 = 0x100      # Alarm A enable
RTC_CR_ALRBE: uint32 = 0x200      # Alarm B enable
RTC_CR_WUTE: uint32 = 0x400       # Wakeup timer enable
RTC_CR_TSE: uint32 = 0x800        # Timestamp enable
RTC_CR_ALRAIE: uint32 = 0x1000    # Alarm A interrupt enable
RTC_CR_ALRBIE: uint32 = 0x2000    # Alarm B interrupt enable
RTC_CR_WUTIE: uint32 = 0x4000     # Wakeup timer interrupt enable
RTC_CR_TSIE: uint32 = 0x8000      # Timestamp interrupt enable
RTC_CR_COE: uint32 = 0x800000     # Calibration output enable

# ISR register bits
RTC_ISR_ALRAWF: uint32 = 0x01     # Alarm A write flag
RTC_ISR_ALRBWF: uint32 = 0x02     # Alarm B write flag
RTC_ISR_WUTWF: uint32 = 0x04      # Wakeup timer write flag
RTC_ISR_SHPF: uint32 = 0x08       # Shift operation pending
RTC_ISR_INITS: uint32 = 0x10      # Initialization status
RTC_ISR_RSF: uint32 = 0x20        # Registers synchronized
RTC_ISR_INITF: uint32 = 0x40      # Initialization flag
RTC_ISR_INIT: uint32 = 0x80       # Initialization mode
RTC_ISR_ALRAF: uint32 = 0x100     # Alarm A flag
RTC_ISR_ALRBF: uint32 = 0x200     # Alarm B flag
RTC_ISR_WUTF: uint32 = 0x400      # Wakeup timer flag
RTC_ISR_TSF: uint32 = 0x800       # Timestamp flag
RTC_ISR_TSOVF: uint32 = 0x1000    # Timestamp overflow

# PWR registers
PWR_CR: uint32 = 0x00
PWR_CR_DBP: uint32 = 0x100  # Disable backup protection

# RCC backup domain
RCC_BDCR: uint32 = 0x70
RCC_BDCR_LSEON: uint32 = 0x01
RCC_BDCR_LSERDY: uint32 = 0x02
RCC_BDCR_RTCSEL_LSE: uint32 = 0x100
RCC_BDCR_RTCEN: uint32 = 0x8000

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _bcd_to_bin(bcd: uint32) -> uint32:
    """Convert BCD to binary."""
    return (bcd & 0x0F) + ((bcd >> 4) * 10)

def _bin_to_bcd(bin: uint32) -> uint32:
    """Convert binary to BCD."""
    return ((bin / 10) << 4) | (bin % 10)

# ============================================================================
# Write Protection
# ============================================================================

def _rtc_disable_write_protection():
    """Disable RTC write protection."""
    mmio_write(RTC_BASE + RTC_WPR, 0xCA)
    mmio_write(RTC_BASE + RTC_WPR, 0x53)

def _rtc_enable_write_protection():
    """Enable RTC write protection."""
    mmio_write(RTC_BASE + RTC_WPR, 0xFF)

# ============================================================================
# RTC Initialization
# ============================================================================

def rtc_init():
    """Initialize the RTC peripheral.

    Enables LSE oscillator and configures RTC clock.
    """
    # Enable power interface clock
    # (assuming already enabled by system init)

    # Enable access to backup domain
    pwr_cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, pwr_cr | PWR_CR_DBP)

    # Enable LSE oscillator
    bdcr: uint32 = mmio_read(RCC_BASE + RCC_BDCR)
    if (bdcr & RCC_BDCR_LSERDY) == 0:
        # Start LSE
        mmio_write(RCC_BASE + RCC_BDCR, bdcr | RCC_BDCR_LSEON)

        # Wait for LSE ready
        timeout: int32 = 100000
        while timeout > 0:
            bdcr = mmio_read(RCC_BASE + RCC_BDCR)
            if (bdcr & RCC_BDCR_LSERDY) != 0:
                break
            timeout = timeout - 1

    # Select LSE as RTC clock and enable RTC
    bdcr = mmio_read(RCC_BASE + RCC_BDCR)
    bdcr = bdcr & ~0x300  # Clear RTCSEL
    bdcr = bdcr | RCC_BDCR_RTCSEL_LSE | RCC_BDCR_RTCEN
    mmio_write(RCC_BASE + RCC_BDCR, bdcr)

    # Configure prescaler for 1Hz from 32.768kHz
    # Async = 127, Sync = 255: 32768 / (128 * 256) = 1Hz
    _rtc_disable_write_protection()

    # Enter initialization mode
    isr: uint32 = mmio_read(RTC_BASE + RTC_ISR)
    mmio_write(RTC_BASE + RTC_ISR, isr | RTC_ISR_INIT)

    # Wait for init mode
    timeout = 10000
    while timeout > 0:
        isr = mmio_read(RTC_BASE + RTC_ISR)
        if (isr & RTC_ISR_INITF) != 0:
            break
        timeout = timeout - 1

    # Set prescaler
    mmio_write(RTC_BASE + RTC_PRER, (127 << 16) | 255)

    # Exit initialization mode
    isr = mmio_read(RTC_BASE + RTC_ISR)
    mmio_write(RTC_BASE + RTC_ISR, isr & ~RTC_ISR_INIT)

    _rtc_enable_write_protection()

def _rtc_enter_init():
    """Enter RTC initialization mode."""
    _rtc_disable_write_protection()
    isr: uint32 = mmio_read(RTC_BASE + RTC_ISR)
    mmio_write(RTC_BASE + RTC_ISR, isr | RTC_ISR_INIT)

    timeout: int32 = 10000
    while timeout > 0:
        isr = mmio_read(RTC_BASE + RTC_ISR)
        if (isr & RTC_ISR_INITF) != 0:
            break
        timeout = timeout - 1

def _rtc_exit_init():
    """Exit RTC initialization mode."""
    isr: uint32 = mmio_read(RTC_BASE + RTC_ISR)
    mmio_write(RTC_BASE + RTC_ISR, isr & ~RTC_ISR_INIT)
    _rtc_enable_write_protection()

# ============================================================================
# Time/Date Setting
# ============================================================================

def rtc_set_time(hour: uint32, min: uint32, sec: uint32):
    """Set RTC time.

    Args:
        hour: Hour (0-23)
        min: Minute (0-59)
        sec: Second (0-59)
    """
    tr: uint32 = (_bin_to_bcd(hour) << 16) | \
                 (_bin_to_bcd(min) << 8) | \
                 _bin_to_bcd(sec)

    _rtc_enter_init()
    mmio_write(RTC_BASE + RTC_TR, tr)
    _rtc_exit_init()

def rtc_set_date(year: uint32, month: uint32, day: uint32, dotw: uint32):
    """Set RTC date.

    Args:
        year: Year (0-99)
        month: Month (1-12)
        day: Day (1-31)
        dotw: Day of week (1=Monday, 7=Sunday)
    """
    dr: uint32 = (_bin_to_bcd(year) << 16) | \
                 (dotw << 13) | \
                 (_bin_to_bcd(month) << 8) | \
                 _bin_to_bcd(day)

    _rtc_enter_init()
    mmio_write(RTC_BASE + RTC_DR, dr)
    _rtc_exit_init()

def rtc_set_datetime(year: uint32, month: uint32, day: uint32,
                     dotw: uint32, hour: uint32, min: uint32, sec: uint32):
    """Set RTC date and time.

    Args:
        year: Year (0-99)
        month: Month (1-12)
        day: Day (1-31)
        dotw: Day of week (1=Monday, 7=Sunday)
        hour: Hour (0-23)
        min: Minute (0-59)
        sec: Second (0-59)
    """
    tr: uint32 = (_bin_to_bcd(hour) << 16) | \
                 (_bin_to_bcd(min) << 8) | \
                 _bin_to_bcd(sec)

    dr: uint32 = (_bin_to_bcd(year) << 16) | \
                 (dotw << 13) | \
                 (_bin_to_bcd(month) << 8) | \
                 _bin_to_bcd(day)

    _rtc_enter_init()
    mmio_write(RTC_BASE + RTC_TR, tr)
    mmio_write(RTC_BASE + RTC_DR, dr)
    _rtc_exit_init()

# ============================================================================
# Time/Date Reading
# ============================================================================

def rtc_get_time(hour: Ptr[uint32], min: Ptr[uint32], sec: Ptr[uint32]):
    """Read RTC time.

    Args:
        hour: Pointer to store hour
        min: Pointer to store minute
        sec: Pointer to store second
    """
    # Wait for RSF if shadow registers enabled
    isr: uint32 = mmio_read(RTC_BASE + RTC_ISR)
    mmio_write(RTC_BASE + RTC_ISR, isr & ~RTC_ISR_RSF)

    timeout: int32 = 1000
    while timeout > 0:
        isr = mmio_read(RTC_BASE + RTC_ISR)
        if (isr & RTC_ISR_RSF) != 0:
            break
        timeout = timeout - 1

    tr: uint32 = mmio_read(RTC_BASE + RTC_TR)

    hour[0] = _bcd_to_bin((tr >> 16) & 0x3F)
    min[0] = _bcd_to_bin((tr >> 8) & 0x7F)
    sec[0] = _bcd_to_bin(tr & 0x7F)

def rtc_get_date(year: Ptr[uint32], month: Ptr[uint32], day: Ptr[uint32], dotw: Ptr[uint32]):
    """Read RTC date.

    Args:
        year: Pointer to store year
        month: Pointer to store month
        day: Pointer to store day
        dotw: Pointer to store day of week
    """
    dr: uint32 = mmio_read(RTC_BASE + RTC_DR)

    year[0] = _bcd_to_bin((dr >> 16) & 0xFF)
    month[0] = _bcd_to_bin((dr >> 8) & 0x1F)
    day[0] = _bcd_to_bin(dr & 0x3F)
    dotw[0] = (dr >> 13) & 0x07

def rtc_get_time_packed() -> uint32:
    """Get time as packed value HHMMSS.

    Returns:
        Packed time (e.g., 143025 for 14:30:25)
    """
    tr: uint32 = mmio_read(RTC_BASE + RTC_TR)

    hour: uint32 = _bcd_to_bin((tr >> 16) & 0x3F)
    min: uint32 = _bcd_to_bin((tr >> 8) & 0x7F)
    sec: uint32 = _bcd_to_bin(tr & 0x7F)

    return hour * 10000 + min * 100 + sec

def rtc_get_date_packed() -> uint32:
    """Get date as packed value YYMMDD.

    Returns:
        Packed date (e.g., 241225 for Dec 25, 2024)
    """
    dr: uint32 = mmio_read(RTC_BASE + RTC_DR)

    year: uint32 = _bcd_to_bin((dr >> 16) & 0xFF)
    month: uint32 = _bcd_to_bin((dr >> 8) & 0x1F)
    day: uint32 = _bcd_to_bin(dr & 0x3F)

    return year * 10000 + month * 100 + day

# ============================================================================
# Alarm A
# ============================================================================

def rtc_set_alarm_a(hour: int32, min: int32, sec: int32, day: int32):
    """Set Alarm A.

    Any field set to -1 is ignored (masked).

    Args:
        hour: Hour to match (-1 for any)
        min: Minute to match (-1 for any)
        sec: Second to match (-1 for any)
        day: Day/date to match (-1 for any)
    """
    alrm: uint32 = 0

    if sec >= 0:
        alrm = alrm | _bin_to_bcd(cast[uint32](sec))
    else:
        alrm = alrm | (1 << 7)  # MSK1 - mask seconds

    if min >= 0:
        alrm = alrm | (_bin_to_bcd(cast[uint32](min)) << 8)
    else:
        alrm = alrm | (1 << 15)  # MSK2 - mask minutes

    if hour >= 0:
        alrm = alrm | (_bin_to_bcd(cast[uint32](hour)) << 16)
    else:
        alrm = alrm | (1 << 23)  # MSK3 - mask hours

    if day >= 0:
        alrm = alrm | (_bin_to_bcd(cast[uint32](day)) << 24)
    else:
        alrm = alrm | (1 << 31)  # MSK4 - mask day

    _rtc_disable_write_protection()

    # Disable Alarm A
    cr: uint32 = mmio_read(RTC_BASE + RTC_CR)
    mmio_write(RTC_BASE + RTC_CR, cr & ~RTC_CR_ALRAE)

    # Wait for write flag
    timeout: int32 = 1000
    while timeout > 0:
        isr: uint32 = mmio_read(RTC_BASE + RTC_ISR)
        if (isr & RTC_ISR_ALRAWF) != 0:
            break
        timeout = timeout - 1

    # Write alarm value
    mmio_write(RTC_BASE + RTC_ALRMAR, alrm)

    _rtc_enable_write_protection()

def rtc_enable_alarm_a():
    """Enable Alarm A with interrupt."""
    _rtc_disable_write_protection()
    cr: uint32 = mmio_read(RTC_BASE + RTC_CR)
    mmio_write(RTC_BASE + RTC_CR, cr | RTC_CR_ALRAE | RTC_CR_ALRAIE)
    _rtc_enable_write_protection()

def rtc_disable_alarm_a():
    """Disable Alarm A."""
    _rtc_disable_write_protection()
    cr: uint32 = mmio_read(RTC_BASE + RTC_CR)
    mmio_write(RTC_BASE + RTC_CR, cr & ~(RTC_CR_ALRAE | RTC_CR_ALRAIE))
    _rtc_enable_write_protection()

def rtc_alarm_a_pending() -> bool:
    """Check if Alarm A triggered."""
    isr: uint32 = mmio_read(RTC_BASE + RTC_ISR)
    return (isr & RTC_ISR_ALRAF) != 0

def rtc_clear_alarm_a():
    """Clear Alarm A flag."""
    isr: uint32 = mmio_read(RTC_BASE + RTC_ISR)
    mmio_write(RTC_BASE + RTC_ISR, isr & ~RTC_ISR_ALRAF)

# ============================================================================
# Alarm B
# ============================================================================

def rtc_set_alarm_b(hour: int32, min: int32, sec: int32, day: int32):
    """Set Alarm B. Same as Alarm A."""
    alrm: uint32 = 0

    if sec >= 0:
        alrm = alrm | _bin_to_bcd(cast[uint32](sec))
    else:
        alrm = alrm | (1 << 7)

    if min >= 0:
        alrm = alrm | (_bin_to_bcd(cast[uint32](min)) << 8)
    else:
        alrm = alrm | (1 << 15)

    if hour >= 0:
        alrm = alrm | (_bin_to_bcd(cast[uint32](hour)) << 16)
    else:
        alrm = alrm | (1 << 23)

    if day >= 0:
        alrm = alrm | (_bin_to_bcd(cast[uint32](day)) << 24)
    else:
        alrm = alrm | (1 << 31)

    _rtc_disable_write_protection()

    cr: uint32 = mmio_read(RTC_BASE + RTC_CR)
    mmio_write(RTC_BASE + RTC_CR, cr & ~RTC_CR_ALRBE)

    timeout: int32 = 1000
    while timeout > 0:
        isr: uint32 = mmio_read(RTC_BASE + RTC_ISR)
        if (isr & RTC_ISR_ALRBWF) != 0:
            break
        timeout = timeout - 1

    mmio_write(RTC_BASE + RTC_ALRMBR, alrm)

    _rtc_enable_write_protection()

def rtc_enable_alarm_b():
    """Enable Alarm B with interrupt."""
    _rtc_disable_write_protection()
    cr: uint32 = mmio_read(RTC_BASE + RTC_CR)
    mmio_write(RTC_BASE + RTC_CR, cr | RTC_CR_ALRBE | RTC_CR_ALRBIE)
    _rtc_enable_write_protection()

def rtc_disable_alarm_b():
    """Disable Alarm B."""
    _rtc_disable_write_protection()
    cr: uint32 = mmio_read(RTC_BASE + RTC_CR)
    mmio_write(RTC_BASE + RTC_CR, cr & ~(RTC_CR_ALRBE | RTC_CR_ALRBIE))
    _rtc_enable_write_protection()

# ============================================================================
# Backup Registers
# ============================================================================

def rtc_write_backup(index: uint32, value: uint32):
    """Write to backup register.

    Args:
        index: Register index (0-19)
        value: Value to write
    """
    if index > 19:
        return
    mmio_write(RTC_BASE + RTC_BKP0R + index * 4, value)

def rtc_read_backup(index: uint32) -> uint32:
    """Read from backup register.

    Args:
        index: Register index (0-19)

    Returns:
        Register value
    """
    if index > 19:
        return 0
    return mmio_read(RTC_BASE + RTC_BKP0R + index * 4)
