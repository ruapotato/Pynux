# STM32F4 Watchdog Timer Driver
#
# STM32F4 has two watchdog timers:
#
# 1. IWDG (Independent Watchdog):
#    - Clocked by LSI (~32kHz)
#    - Cannot be disabled once started
#    - Simple countdown timer
#    - Typical use: system hang detection
#
# 2. WWDG (Window Watchdog):
#    - Clocked by APB1 (PCLK1)
#    - Must be refreshed within a window
#    - Early wakeup interrupt available
#    - Typical use: timing-critical refresh

# ============================================================================
# Base Addresses
# ============================================================================

IWDG_BASE: uint32 = 0x40003000
WWDG_BASE: uint32 = 0x40002C00
RCC_BASE: uint32 = 0x40023800
DBGMCU_BASE: uint32 = 0xE0042000

# ============================================================================
# IWDG Register Offsets
# ============================================================================

IWDG_KR: uint32 = 0x00   # Key register
IWDG_PR: uint32 = 0x04   # Prescaler register
IWDG_RLR: uint32 = 0x08  # Reload register
IWDG_SR: uint32 = 0x0C   # Status register

# IWDG Key values
IWDG_KEY_RELOAD: uint32 = 0xAAAA   # Reload the counter
IWDG_KEY_ENABLE: uint32 = 0xCCCC   # Start watchdog
IWDG_KEY_ACCESS: uint32 = 0x5555   # Enable register access

# IWDG Prescaler values
IWDG_PR_DIV4: uint32 = 0     # LSI / 4
IWDG_PR_DIV8: uint32 = 1     # LSI / 8
IWDG_PR_DIV16: uint32 = 2    # LSI / 16
IWDG_PR_DIV32: uint32 = 3    # LSI / 32
IWDG_PR_DIV64: uint32 = 4    # LSI / 64
IWDG_PR_DIV128: uint32 = 5   # LSI / 128
IWDG_PR_DIV256: uint32 = 6   # LSI / 256

# IWDG Status bits
IWDG_SR_PVU: uint32 = 0x01  # Prescaler value update
IWDG_SR_RVU: uint32 = 0x02  # Reload value update

# ============================================================================
# WWDG Register Offsets
# ============================================================================

WWDG_CR: uint32 = 0x00   # Control register
WWDG_CFR: uint32 = 0x04  # Configuration register
WWDG_SR: uint32 = 0x08   # Status register

# WWDG CR bits
WWDG_CR_T_MASK: uint32 = 0x7F    # Counter value (7 bits)
WWDG_CR_WDGA: uint32 = 0x80      # Watchdog activation

# WWDG CFR bits
WWDG_CFR_W_MASK: uint32 = 0x7F   # Window value
WWDG_CFR_WDGTB_SHIFT: uint32 = 7 # Timer base prescaler shift
WWDG_CFR_EWI: uint32 = 0x200     # Early wakeup interrupt

# WWDG SR bits
WWDG_SR_EWIF: uint32 = 0x01      # Early wakeup interrupt flag

# ============================================================================
# Constants
# ============================================================================

# LSI is approximately 32kHz (can vary 17-47kHz)
LSI_FREQ: uint32 = 32000

# IWDG max timeout with prescaler 256 and reload 4095:
# timeout = (4095 * 256) / 32000 = ~32.7 seconds

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
# IWDG (Independent Watchdog)
# ============================================================================

def iwdg_init(prescaler: uint32, reload: uint32):
    """Initialize independent watchdog.

    Args:
        prescaler: IWDG_PR_DIVx value (0-6)
        reload: Reload value (0-4095)
    """
    # Enable register access
    mmio_write(IWDG_BASE + IWDG_KR, IWDG_KEY_ACCESS)

    # Set prescaler
    mmio_write(IWDG_BASE + IWDG_PR, prescaler & 0x07)

    # Wait for prescaler update
    timeout: int32 = 10000
    while timeout > 0:
        sr: uint32 = mmio_read(IWDG_BASE + IWDG_SR)
        if (sr & IWDG_SR_PVU) == 0:
            break
        timeout = timeout - 1

    # Set reload value
    mmio_write(IWDG_BASE + IWDG_RLR, reload & 0x0FFF)

    # Wait for reload update
    timeout = 10000
    while timeout > 0:
        sr: uint32 = mmio_read(IWDG_BASE + IWDG_SR)
        if (sr & IWDG_SR_RVU) == 0:
            break
        timeout = timeout - 1

def iwdg_start():
    """Start the independent watchdog.

    WARNING: Once started, IWDG cannot be stopped!
    """
    mmio_write(IWDG_BASE + IWDG_KR, IWDG_KEY_ENABLE)

def iwdg_refresh():
    """Refresh independent watchdog to prevent reset."""
    mmio_write(IWDG_BASE + IWDG_KR, IWDG_KEY_RELOAD)

def iwdg_feed():
    """Alias for iwdg_refresh."""
    iwdg_refresh()

def iwdg_start_ms(timeout_ms: uint32):
    """Start IWDG with timeout in milliseconds.

    Args:
        timeout_ms: Desired timeout (max ~32700ms)
    """
    # Calculate prescaler and reload
    # timeout_ms = (reload * prescaler) / (LSI / 1000)
    # reload = timeout_ms * LSI / (prescaler * 1000)

    prescaler: uint32 = 0
    reload: uint32 = 0

    # Try each prescaler until reload fits in 12 bits
    div: uint32 = 4
    pr: uint32 = 0
    while pr < 7:
        reload = (timeout_ms * LSI) / (div * 1000)
        if reload <= 4095:
            prescaler = pr
            break
        div = div * 2
        pr = pr + 1

    if reload > 4095:
        reload = 4095
        prescaler = 6

    iwdg_init(prescaler, reload)
    iwdg_start()

# ============================================================================
# WWDG (Window Watchdog)
# ============================================================================

def wwdg_init(counter: uint32, window: uint32, prescaler: uint32):
    """Initialize window watchdog.

    Args:
        counter: Initial counter value (0x40-0x7F)
        window: Window value (counter must be > window to refresh)
        prescaler: Timer base prescaler (0-3)
    """
    # Enable WWDG clock
    apb1enr: uint32 = mmio_read(RCC_BASE + 0x40)
    mmio_write(RCC_BASE + 0x40, apb1enr | (1 << 11))

    # Configure window and prescaler
    cfr: uint32 = (window & WWDG_CFR_W_MASK) | \
                  ((prescaler & 0x03) << WWDG_CFR_WDGTB_SHIFT)
    mmio_write(WWDG_BASE + WWDG_CFR, cfr)

    # Set counter (but don't enable yet)
    mmio_write(WWDG_BASE + WWDG_CR, counter & WWDG_CR_T_MASK)

def wwdg_enable():
    """Enable window watchdog."""
    cr: uint32 = mmio_read(WWDG_BASE + WWDG_CR)
    mmio_write(WWDG_BASE + WWDG_CR, cr | WWDG_CR_WDGA)

def wwdg_start(counter: uint32, window: uint32, prescaler: uint32):
    """Initialize and start window watchdog.

    Args:
        counter: Initial counter value (0x40-0x7F)
        window: Window value
        prescaler: Timer base prescaler
    """
    wwdg_init(counter, window, prescaler)
    wwdg_enable()

def wwdg_refresh(counter: uint32):
    """Refresh window watchdog.

    Must be called when counter > window and counter >= 0x40.

    Args:
        counter: New counter value (0x40-0x7F)
    """
    cr: uint32 = mmio_read(WWDG_BASE + WWDG_CR)
    cr = (cr & WWDG_CR_WDGA) | (counter & WWDG_CR_T_MASK)
    mmio_write(WWDG_BASE + WWDG_CR, cr)

def wwdg_get_counter() -> uint32:
    """Get current WWDG counter value.

    Returns:
        Counter value (0x40-0x7F when active)
    """
    cr: uint32 = mmio_read(WWDG_BASE + WWDG_CR)
    return cr & WWDG_CR_T_MASK

def wwdg_enable_ewi():
    """Enable early wakeup interrupt.

    Triggers interrupt when counter reaches 0x40.
    """
    cfr: uint32 = mmio_read(WWDG_BASE + WWDG_CFR)
    mmio_write(WWDG_BASE + WWDG_CFR, cfr | WWDG_CFR_EWI)

def wwdg_clear_ewi():
    """Clear early wakeup interrupt flag."""
    mmio_write(WWDG_BASE + WWDG_SR, 0)

def wwdg_ewi_pending() -> bool:
    """Check if early wakeup interrupt is pending.

    Returns:
        True if EWI flag set
    """
    sr: uint32 = mmio_read(WWDG_BASE + WWDG_SR)
    return (sr & WWDG_SR_EWIF) != 0

# ============================================================================
# Reset Detection
# ============================================================================

def watchdog_caused_reboot() -> bool:
    """Check if last reset was caused by watchdog.

    Returns:
        True if IWDG or WWDG caused reset
    """
    # Check RCC_CSR for reset flags
    csr: uint32 = mmio_read(RCC_BASE + 0x74)
    iwdg_rst: bool = (csr & (1 << 29)) != 0  # IWDGRST
    wwdg_rst: bool = (csr & (1 << 30)) != 0  # WWDGRST
    return iwdg_rst or wwdg_rst

def iwdg_caused_reboot() -> bool:
    """Check if IWDG caused the reset."""
    csr: uint32 = mmio_read(RCC_BASE + 0x74)
    return (csr & (1 << 29)) != 0

def wwdg_caused_reboot() -> bool:
    """Check if WWDG caused the reset."""
    csr: uint32 = mmio_read(RCC_BASE + 0x74)
    return (csr & (1 << 30)) != 0

def clear_reset_flags():
    """Clear all reset flags in RCC_CSR."""
    csr: uint32 = mmio_read(RCC_BASE + 0x74)
    mmio_write(RCC_BASE + 0x74, csr | (1 << 24))  # RMVF

# ============================================================================
# Debug Freeze
# ============================================================================

def iwdg_freeze_in_debug(freeze: bool):
    """Freeze IWDG when debugger halts CPU.

    Args:
        freeze: True to freeze during debug
    """
    apb1fz: uint32 = mmio_read(DBGMCU_BASE + 0x08)
    if freeze:
        apb1fz = apb1fz | (1 << 12)
    else:
        apb1fz = apb1fz & ~(1 << 12)
    mmio_write(DBGMCU_BASE + 0x08, apb1fz)

def wwdg_freeze_in_debug(freeze: bool):
    """Freeze WWDG when debugger halts CPU.

    Args:
        freeze: True to freeze during debug
    """
    apb1fz: uint32 = mmio_read(DBGMCU_BASE + 0x08)
    if freeze:
        apb1fz = apb1fz | (1 << 11)
    else:
        apb1fz = apb1fz & ~(1 << 11)
    mmio_write(DBGMCU_BASE + 0x08, apb1fz)

# ============================================================================
# Convenience Functions
# ============================================================================

def watchdog_start_ms(timeout_ms: uint32):
    """Start watchdog with timeout in milliseconds.

    Uses IWDG for simplicity.

    Args:
        timeout_ms: Timeout in milliseconds
    """
    iwdg_start_ms(timeout_ms)

def watchdog_refresh():
    """Refresh watchdog (IWDG)."""
    iwdg_refresh()

def watchdog_feed():
    """Alias for watchdog_refresh."""
    iwdg_refresh()
