# STM32F4 Power Management Driver
#
# Low-level power management for STM32F405/F407 microcontrollers.
# Features:
#   - Sleep modes: Sleep, Stop, Standby
#   - Wake sources: EXTI, RTC alarm, WKUP pins
#   - Voltage regulator scaling
#   - PVD (Programmable Voltage Detector)
#   - Backup domain access
#   - Flash power-down in Stop mode
#
# Memory Map:
#   PWR_BASE:    0x40007000
#   RCC_BASE:    0x40023800
#   SCB_BASE:    0xE000ED00
#   EXTI_BASE:   0x40013C00
#   FLASH_BASE:  0x40023C00

# ============================================================================
# Base Addresses
# ============================================================================

PWR_BASE: uint32 = 0x40007000
RCC_BASE: uint32 = 0x40023800
SCB_BASE: uint32 = 0xE000ED00
EXTI_BASE: uint32 = 0x40013C00
FLASH_BASE: uint32 = 0x40023C00
DBGMCU_BASE: uint32 = 0xE0042000

# ============================================================================
# PWR Register Offsets
# ============================================================================

PWR_CR: uint32 = 0x00     # Power control register
PWR_CSR: uint32 = 0x04    # Power control/status register

# ============================================================================
# PWR_CR Register Bits
# ============================================================================

PWR_CR_LPDS: uint32 = 0x0001       # Low-power deep sleep
PWR_CR_PDDS: uint32 = 0x0002       # Power-down deep sleep (Standby mode)
PWR_CR_CWUF: uint32 = 0x0004       # Clear wakeup flag
PWR_CR_CSBF: uint32 = 0x0008       # Clear standby flag
PWR_CR_PVDE: uint32 = 0x0010       # PVD enable
PWR_CR_PLS_MASK: uint32 = 0x00E0   # PVD level selection
PWR_CR_PLS_SHIFT: uint32 = 5
PWR_CR_DBP: uint32 = 0x0100        # Disable backup domain write protection
PWR_CR_FPDS: uint32 = 0x0200       # Flash power-down in Stop mode
PWR_CR_VOS_MASK: uint32 = 0xC000   # Regulator voltage scaling (bits 14-15)
PWR_CR_VOS_SHIFT: uint32 = 14
PWR_CR_ODEN: uint32 = 0x00010000   # Over-drive enable (F42x/F43x only)
PWR_CR_ODSWEN: uint32 = 0x00020000 # Over-drive switching enable

# Regulator voltage scaling values
VOS_SCALE3: uint32 = 0x01  # Scale 3 mode (lowest power)
VOS_SCALE2: uint32 = 0x02  # Scale 2 mode
VOS_SCALE1: uint32 = 0x03  # Scale 1 mode (highest performance)

# PVD threshold levels (rising edge voltage)
PVD_LEVEL_2_0V: uint32 = 0x00  # 2.0V
PVD_LEVEL_2_1V: uint32 = 0x01  # 2.1V
PVD_LEVEL_2_3V: uint32 = 0x02  # 2.3V
PVD_LEVEL_2_5V: uint32 = 0x03  # 2.5V
PVD_LEVEL_2_6V: uint32 = 0x04  # 2.6V
PVD_LEVEL_2_7V: uint32 = 0x05  # 2.7V
PVD_LEVEL_2_8V: uint32 = 0x06  # 2.8V
PVD_LEVEL_2_9V: uint32 = 0x07  # 2.9V

# ============================================================================
# PWR_CSR Register Bits
# ============================================================================

PWR_CSR_WUF: uint32 = 0x0001       # Wakeup flag
PWR_CSR_SBF: uint32 = 0x0002       # Standby flag
PWR_CSR_PVDO: uint32 = 0x0004      # PVD output (1 = VDD below threshold)
PWR_CSR_BRR: uint32 = 0x0008       # Backup regulator ready
PWR_CSR_EWUP: uint32 = 0x0100      # Enable WKUP pin (PA0)
PWR_CSR_BRE: uint32 = 0x0200       # Backup regulator enable
PWR_CSR_VOSRDY: uint32 = 0x4000    # Regulator voltage scaling ready
PWR_CSR_ODRDY: uint32 = 0x00010000 # Over-drive ready (F42x/F43x)
PWR_CSR_ODSWRDY: uint32 = 0x00020000  # Over-drive switch ready

# ============================================================================
# SCB Register Offsets
# ============================================================================

SCB_SCR: uint32 = 0x10    # System Control Register

# SCB_SCR bits
SCB_SCR_SLEEPONEXIT: uint32 = 0x02  # Sleep on exception return
SCB_SCR_SLEEPDEEP: uint32 = 0x04    # Deep sleep enable
SCB_SCR_SEVONPEND: uint32 = 0x10    # SEV on pending interrupt

# ============================================================================
# RCC Register Offsets (for power management)
# ============================================================================

RCC_APB1ENR: uint32 = 0x40    # APB1 peripheral clock enable
RCC_BDCR: uint32 = 0x70       # Backup domain control register
RCC_CSR: uint32 = 0x74        # Control/status register

RCC_APB1ENR_PWREN: uint32 = 0x10000000  # Power interface clock enable

# ============================================================================
# EXTI Register Offsets (for wake configuration)
# ============================================================================

EXTI_IMR: uint32 = 0x00    # Interrupt mask register
EXTI_EMR: uint32 = 0x04    # Event mask register
EXTI_RTSR: uint32 = 0x08   # Rising trigger selection
EXTI_FTSR: uint32 = 0x0C   # Falling trigger selection
EXTI_PR: uint32 = 0x14     # Pending register

# EXTI lines for wake sources
EXTI_LINE_PVD: uint32 = 16     # PVD output
EXTI_LINE_RTC_ALARM: uint32 = 17  # RTC Alarm
EXTI_LINE_USB_OTG_FS: uint32 = 18  # USB OTG FS wakeup
EXTI_LINE_ETH: uint32 = 19     # Ethernet wakeup
EXTI_LINE_USB_OTG_HS: uint32 = 20  # USB OTG HS wakeup
EXTI_LINE_RTC_TAMPER: uint32 = 21  # RTC Tamper and Timestamp
EXTI_LINE_RTC_WKUP: uint32 = 22    # RTC Wakeup

# ============================================================================
# FLASH Register Offsets
# ============================================================================

FLASH_ACR: uint32 = 0x00   # Flash access control register

FLASH_ACR_SLEEP_PD: uint32 = 0x4000  # Flash interface in sleep mode

# ============================================================================
# DBGMCU Registers (for debug in low-power)
# ============================================================================

DBGMCU_CR: uint32 = 0x04

DBGMCU_CR_DBG_SLEEP: uint32 = 0x01   # Debug in Sleep mode
DBGMCU_CR_DBG_STOP: uint32 = 0x02    # Debug in Stop mode
DBGMCU_CR_DBG_STANDBY: uint32 = 0x04 # Debug in Standby mode

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
# Power Interface Initialization
# ============================================================================

def pwr_init():
    """Initialize power interface.

    Enables PWR peripheral clock. Must be called before using
    other power functions.
    """
    # Enable PWR peripheral clock
    apb1enr: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)
    mmio_write(RCC_BASE + RCC_APB1ENR, apb1enr | RCC_APB1ENR_PWREN)

    # Small delay for clock to stabilize
    dummy: uint32 = mmio_read(RCC_BASE + RCC_APB1ENR)

# ============================================================================
# Sleep Mode (WFI/WFE)
# ============================================================================

def wfi():
    """Wait For Interrupt.

    CPU stops executing until interrupt occurs.
    Use for simple sleep in main loop.
    """
    __wfi()

def wfe():
    """Wait For Event.

    CPU stops executing until event occurs.
    Events can be interrupts or SEV from other sources.
    """
    __wfe()

def sleep_now():
    """Enter Sleep mode immediately.

    CPU clock stops. Peripherals continue running.
    Wake on any enabled interrupt.
    """
    # Clear SLEEPDEEP for normal sleep
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr & ~SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # Data sync and enter sleep
    __dsb()
    __wfi()
    __isb()

def sleep_on_exit(enable: bool):
    """Enable/disable sleep on interrupt return.

    When enabled, processor enters sleep mode automatically
    after handling an interrupt instead of returning to main program.

    Args:
        enable: True to enable sleep on exit
    """
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    if enable:
        scr = scr | SCB_SCR_SLEEPONEXIT
    else:
        scr = scr & ~SCB_SCR_SLEEPONEXIT
    mmio_write(SCB_BASE + SCB_SCR, scr)

def sleep_until_interrupt():
    """Enter sleep mode and return after interrupt handler completes."""
    sleep_on_exit(False)
    sleep_now()

def sleep_until_event():
    """Enter sleep mode and wake on event."""
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr & ~SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    __dsb()
    __wfe()
    __isb()

# ============================================================================
# Stop Mode
# ============================================================================

def stop_mode():
    """Enter Stop mode.

    All clocks in 1.2V domain stopped.
    HSI and HSE oscillators disabled.
    SRAM and register contents preserved.
    Wake by any EXTI line (configured for interrupt/event).

    After waking, HSI is used as system clock. Reconfigure clocks if needed.
    """
    # Set SLEEPDEEP for Stop/Standby
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr | SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # Configure for Stop mode (not Standby)
    # PDDS = 0: Stop mode, LPDS = 0: main regulator on
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    cr = cr & ~(PWR_CR_PDDS | PWR_CR_LPDS)
    mmio_write(PWR_BASE + PWR_CR, cr)

    # Clear wakeup flag
    cr = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr | PWR_CR_CWUF)

    # Enter stop mode
    __dsb()
    __wfi()
    __isb()

    # Clear SLEEPDEEP after wake
    scr = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr & ~SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

def stop_mode_low_power():
    """Enter Stop mode with low-power regulator.

    Same as stop_mode() but uses low-power regulator for
    reduced power consumption. Slightly longer wake-up time.
    """
    # Set SLEEPDEEP
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr | SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # PDDS = 0: Stop mode, LPDS = 1: low-power regulator
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    cr = cr & ~PWR_CR_PDDS
    cr = cr | PWR_CR_LPDS
    mmio_write(PWR_BASE + PWR_CR, cr)

    # Clear wakeup flag
    cr = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr | PWR_CR_CWUF)

    # Enter stop mode
    __dsb()
    __wfi()
    __isb()

    # Clear SLEEPDEEP
    scr = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr & ~SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

def stop_mode_flash_powerdown():
    """Enter Stop mode with Flash in power-down.

    Further reduces power by putting Flash in power-down.
    Longer wake-up time due to Flash wake.
    """
    # Enable Flash power-down in Stop mode
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    cr = cr | PWR_CR_FPDS
    mmio_write(PWR_BASE + PWR_CR, cr)

    # Enter low-power stop mode
    stop_mode_low_power()

    # Flash wakes automatically, optionally disable FPDS
    cr = mmio_read(PWR_BASE + PWR_CR)
    cr = cr & ~PWR_CR_FPDS
    mmio_write(PWR_BASE + PWR_CR, cr)

# ============================================================================
# Standby Mode
# ============================================================================

def standby_mode():
    """Enter Standby mode (lowest power).

    1.2V domain powered off. HSI and HSE off.
    SRAM and register contents LOST (except backup domain).
    Wake by: WKUP pin rising edge, RTC alarm, RTC wakeup,
             RTC tamper/timestamp, NRST pin, IWDG reset.

    After waking, device resets and executes from beginning.
    """
    # Set SLEEPDEEP
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr | SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # Set PDDS for Standby mode
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    cr = cr | PWR_CR_PDDS
    mmio_write(PWR_BASE + PWR_CR, cr)

    # Clear wakeup and standby flags
    cr = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr | PWR_CR_CWUF | PWR_CR_CSBF)

    # Enter standby mode
    __dsb()
    __wfi()

    # Should never reach here - device resets on wake
    while True:
        pass

# ============================================================================
# Wake Source Configuration
# ============================================================================

def wkup_pin_enable():
    """Enable WKUP pin (PA0) as wake source from Standby.

    Rising edge on PA0 will wake from Standby mode.
    """
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    mmio_write(PWR_BASE + PWR_CSR, csr | PWR_CSR_EWUP)

def wkup_pin_disable():
    """Disable WKUP pin wake source."""
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    mmio_write(PWR_BASE + PWR_CSR, csr & ~PWR_CSR_EWUP)

def exti_enable_wake(line: uint32, rising: bool, falling: bool):
    """Configure EXTI line as wake source from Stop mode.

    Args:
        line: EXTI line number (0-22)
        rising: Enable rising edge wake
        falling: Enable falling edge wake
    """
    if line > 22:
        return

    mask: uint32 = 1 << line

    # Configure trigger edges
    rtsr: uint32 = mmio_read(EXTI_BASE + EXTI_RTSR)
    ftsr: uint32 = mmio_read(EXTI_BASE + EXTI_FTSR)

    if rising:
        rtsr = rtsr | mask
    else:
        rtsr = rtsr & ~mask

    if falling:
        ftsr = ftsr | mask
    else:
        ftsr = ftsr & ~mask

    mmio_write(EXTI_BASE + EXTI_RTSR, rtsr)
    mmio_write(EXTI_BASE + EXTI_FTSR, ftsr)

    # Enable event (for Stop mode wake) and interrupt
    emr: uint32 = mmio_read(EXTI_BASE + EXTI_EMR)
    mmio_write(EXTI_BASE + EXTI_EMR, emr | mask)

    imr: uint32 = mmio_read(EXTI_BASE + EXTI_IMR)
    mmio_write(EXTI_BASE + EXTI_IMR, imr | mask)

def exti_disable_wake(line: uint32):
    """Disable EXTI line as wake source.

    Args:
        line: EXTI line number (0-22)
    """
    if line > 22:
        return

    mask: uint32 = 1 << line

    emr: uint32 = mmio_read(EXTI_BASE + EXTI_EMR)
    mmio_write(EXTI_BASE + EXTI_EMR, emr & ~mask)

def rtc_alarm_wake_enable():
    """Enable RTC Alarm as wake source from Stop/Standby."""
    exti_enable_wake(EXTI_LINE_RTC_ALARM, True, False)

def rtc_wakeup_wake_enable():
    """Enable RTC Wakeup timer as wake source from Stop/Standby."""
    exti_enable_wake(EXTI_LINE_RTC_WKUP, True, False)

def clear_wakeup_flag():
    """Clear the wakeup flag.

    Must be cleared to detect next wakeup event.
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr | PWR_CR_CWUF)

def clear_standby_flag():
    """Clear the standby flag.

    Should be cleared after waking from standby.
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr | PWR_CR_CSBF)

def get_wakeup_flag() -> bool:
    """Check if wakeup event occurred.

    Returns:
        True if wakeup flag is set
    """
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    return (csr & PWR_CSR_WUF) != 0

def get_standby_flag() -> bool:
    """Check if device woke from standby.

    Returns:
        True if standby flag is set
    """
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    return (csr & PWR_CSR_SBF) != 0

# ============================================================================
# Voltage Regulator Scaling
# ============================================================================

def vos_set_scale(scale: uint32):
    """Set voltage regulator scaling mode.

    Higher scale = higher voltage = higher max frequency.
    Lower scale = lower voltage = lower power consumption.

    Scale 1: Up to 168 MHz (default)
    Scale 2: Up to 144 MHz
    Scale 3: Up to 120 MHz

    Args:
        scale: VOS_SCALE1, VOS_SCALE2, or VOS_SCALE3
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    cr = cr & ~PWR_CR_VOS_MASK
    cr = cr | ((scale & 0x03) << PWR_CR_VOS_SHIFT)
    mmio_write(PWR_BASE + PWR_CR, cr)

    # Wait for voltage scaling to complete
    timeout: int32 = 10000
    while timeout > 0:
        csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
        if (csr & PWR_CSR_VOSRDY) != 0:
            break
        timeout = timeout - 1

def vos_get_scale() -> uint32:
    """Get current voltage regulator scaling mode.

    Returns:
        Current scale (VOS_SCALE1, VOS_SCALE2, or VOS_SCALE3)
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    return (cr & PWR_CR_VOS_MASK) >> PWR_CR_VOS_SHIFT

def vos_is_ready() -> bool:
    """Check if voltage scaling is complete.

    Returns:
        True if regulator voltage output is stable
    """
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    return (csr & PWR_CSR_VOSRDY) != 0

# ============================================================================
# Programmable Voltage Detector (PVD)
# ============================================================================

def pvd_enable(level: uint32):
    """Enable Programmable Voltage Detector.

    PVD monitors VDD and can generate interrupt when VDD
    crosses the configured threshold.

    Args:
        level: Threshold level (PVD_LEVEL_*)
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    cr = cr & ~PWR_CR_PLS_MASK
    cr = cr | ((level & 0x07) << PWR_CR_PLS_SHIFT)
    cr = cr | PWR_CR_PVDE
    mmio_write(PWR_BASE + PWR_CR, cr)

def pvd_disable():
    """Disable Programmable Voltage Detector."""
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    cr = cr & ~PWR_CR_PVDE
    mmio_write(PWR_BASE + PWR_CR, cr)

def pvd_set_level(level: uint32):
    """Set PVD threshold level.

    Args:
        level: Threshold level (PVD_LEVEL_*)
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    cr = cr & ~PWR_CR_PLS_MASK
    cr = cr | ((level & 0x07) << PWR_CR_PLS_SHIFT)
    mmio_write(PWR_BASE + PWR_CR, cr)

def pvd_get_output() -> bool:
    """Get PVD comparator output.

    Returns:
        True if VDD is below threshold
    """
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    return (csr & PWR_CSR_PVDO) != 0

def pvd_enable_interrupt(rising: bool, falling: bool):
    """Enable PVD EXTI interrupt.

    Args:
        rising: Trigger on VDD rising above threshold
        falling: Trigger on VDD falling below threshold
    """
    exti_enable_wake(EXTI_LINE_PVD, rising, falling)

def pvd_clear_interrupt():
    """Clear PVD pending interrupt."""
    mmio_write(EXTI_BASE + EXTI_PR, 1 << EXTI_LINE_PVD)

# ============================================================================
# Backup Domain Access
# ============================================================================

def backup_domain_enable():
    """Enable write access to backup domain.

    Required before modifying RTC, backup registers, or
    backup SRAM.
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr | PWR_CR_DBP)

    # Wait for access to be enabled
    timeout: int32 = 1000
    while timeout > 0:
        cr = mmio_read(PWR_BASE + PWR_CR)
        if (cr & PWR_CR_DBP) != 0:
            break
        timeout = timeout - 1

def backup_domain_disable():
    """Disable write access to backup domain.

    Protects RTC and backup registers from accidental writes.
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr & ~PWR_CR_DBP)

def backup_regulator_enable():
    """Enable backup regulator.

    Powers backup SRAM in VBAT mode.
    """
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    mmio_write(PWR_BASE + PWR_CSR, csr | PWR_CSR_BRE)

    # Wait for backup regulator ready
    timeout: int32 = 10000
    while timeout > 0:
        csr = mmio_read(PWR_BASE + PWR_CSR)
        if (csr & PWR_CSR_BRR) != 0:
            break
        timeout = timeout - 1

def backup_regulator_disable():
    """Disable backup regulator."""
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    mmio_write(PWR_BASE + PWR_CSR, csr & ~PWR_CSR_BRE)

def backup_regulator_is_ready() -> bool:
    """Check if backup regulator is ready.

    Returns:
        True if backup regulator output is stable
    """
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)
    return (csr & PWR_CSR_BRR) != 0

# ============================================================================
# Flash Power Management
# ============================================================================

def flash_sleep_enable():
    """Enable Flash sleep mode.

    Flash enters low-power mode when not accessed.
    """
    acr: uint32 = mmio_read(FLASH_BASE + FLASH_ACR)
    mmio_write(FLASH_BASE + FLASH_ACR, acr | FLASH_ACR_SLEEP_PD)

def flash_sleep_disable():
    """Disable Flash sleep mode."""
    acr: uint32 = mmio_read(FLASH_BASE + FLASH_ACR)
    mmio_write(FLASH_BASE + FLASH_ACR, acr & ~FLASH_ACR_SLEEP_PD)

def flash_powerdown_stop_enable():
    """Enable Flash power-down in Stop mode.

    Reduces power consumption but increases wake time.
    """
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr | PWR_CR_FPDS)

def flash_powerdown_stop_disable():
    """Disable Flash power-down in Stop mode."""
    cr: uint32 = mmio_read(PWR_BASE + PWR_CR)
    mmio_write(PWR_BASE + PWR_CR, cr & ~PWR_CR_FPDS)

# ============================================================================
# Debug in Low-Power Modes
# ============================================================================

def debug_sleep_enable():
    """Enable debug in Sleep mode.

    Allows debugger access during Sleep mode.
    Increases power consumption.
    """
    cr: uint32 = mmio_read(DBGMCU_BASE + DBGMCU_CR)
    mmio_write(DBGMCU_BASE + DBGMCU_CR, cr | DBGMCU_CR_DBG_SLEEP)

def debug_stop_enable():
    """Enable debug in Stop mode.

    Allows debugger access during Stop mode.
    Significantly increases power consumption.
    """
    cr: uint32 = mmio_read(DBGMCU_BASE + DBGMCU_CR)
    mmio_write(DBGMCU_BASE + DBGMCU_CR, cr | DBGMCU_CR_DBG_STOP)

def debug_standby_enable():
    """Enable debug in Standby mode.

    Allows debugger access during Standby mode.
    Significantly increases power consumption.
    """
    cr: uint32 = mmio_read(DBGMCU_BASE + DBGMCU_CR)
    mmio_write(DBGMCU_BASE + DBGMCU_CR, cr | DBGMCU_CR_DBG_STANDBY)

def debug_lowpower_disable():
    """Disable debug in all low-power modes.

    Restores normal low-power behavior for production.
    """
    mmio_write(DBGMCU_BASE + DBGMCU_CR, 0)

# ============================================================================
# Intrinsic Stubs (implemented by compiler/runtime)
# ============================================================================

def __wfi():
    """Wait For Interrupt - enters low power state."""
    pass

def __wfe():
    """Wait For Event - enters low power state."""
    pass

def __dsb():
    """Data Synchronization Barrier."""
    pass

def __isb():
    """Instruction Synchronization Barrier."""
    pass

def __sev():
    """Send Event - wakes cores in WFE state."""
    pass

# ============================================================================
# Power Profile Presets
# ============================================================================

def power_configure_low_power():
    """Configure for low power operation.

    Reduces voltage scaling and enables power-saving features.
    Maximum clock speed will be reduced.
    """
    pwr_init()
    vos_set_scale(VOS_SCALE3)
    flash_sleep_enable()
    flash_powerdown_stop_enable()

def power_configure_high_performance():
    """Configure for high performance.

    Maximum voltage scaling for highest clock speeds.
    """
    pwr_init()
    vos_set_scale(VOS_SCALE1)
    flash_sleep_disable()
    flash_powerdown_stop_disable()

def power_configure_balanced():
    """Configure for balanced power/performance.

    Good performance with reasonable power consumption.
    """
    pwr_init()
    vos_set_scale(VOS_SCALE2)
    flash_sleep_enable()
    flash_powerdown_stop_disable()

# ============================================================================
# Complete Enter/Exit Sequences
# ============================================================================

def enter_stop_mode_rtc_wake():
    """Enter Stop mode with RTC alarm wake configured.

    RTC alarm must be set before calling this function.
    System clock will be HSI after wake - reconfigure as needed.
    """
    # Enable RTC alarm wake
    rtc_alarm_wake_enable()

    # Clear any pending wake flag
    clear_wakeup_flag()

    # Enter stop mode with low-power regulator
    stop_mode_low_power()

    # After wake: clear interrupt and reconfigure as needed
    pvd_clear_interrupt()

def enter_standby_mode_wkup_wake():
    """Enter Standby mode with WKUP pin (PA0) wake.

    Device will reset after waking from Standby.
    """
    # Enable WKUP pin
    wkup_pin_enable()

    # Clear flags
    clear_wakeup_flag()
    clear_standby_flag()

    # Enter standby (no return)
    standby_mode()

def check_wakeup_source() -> uint32:
    """Determine wake source after reset.

    Returns:
        0: Normal power-on reset
        1: Woke from Stop mode
        2: Woke from Standby mode
    """
    csr: uint32 = mmio_read(PWR_BASE + PWR_CSR)

    if (csr & PWR_CSR_SBF) != 0:
        return 2  # Standby
    elif (csr & PWR_CSR_WUF) != 0:
        return 1  # Stop
    else:
        return 0  # Normal reset
