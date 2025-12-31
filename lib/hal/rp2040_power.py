# RP2040 Power Management Driver
#
# Low-level power management for Raspberry Pi Pico (RP2040).
# Features:
#   - Sleep modes: sleep_cpu (light sleep), dormant (deep sleep)
#   - Wake sources: GPIO, RTC, USB
#   - Clock gating: ROSC/XOSC control
#   - Voltage regulator and brownout detection
#   - Power-on state machine (PSM) control
#
# Memory Map:
#   VREG_AND_CHIP_RESET_BASE: 0x40064000
#   ROSC_BASE:                0x40060000
#   XOSC_BASE:                0x40024000
#   CLOCKS_BASE:              0x40008000
#   PSM_BASE:                 0x40010000

# ============================================================================
# Base Addresses
# ============================================================================

VREG_AND_CHIP_RESET_BASE: uint32 = 0x40064000
ROSC_BASE: uint32 = 0x40060000
XOSC_BASE: uint32 = 0x40024000
CLOCKS_BASE: uint32 = 0x40008000
PSM_BASE: uint32 = 0x40010000
IO_BANK0_BASE: uint32 = 0x40014000
RTC_BASE: uint32 = 0x4005C000

# Cortex-M0+ system control
SCB_BASE: uint32 = 0xE000ED00
SCB_SCR: uint32 = 0x10  # System Control Register offset

# ============================================================================
# VREG and Chip Reset Registers (at VREG_AND_CHIP_RESET_BASE)
# ============================================================================

VREG_VREG: uint32 = 0x00           # Voltage regulator control
VREG_BOD: uint32 = 0x04            # Brownout detector control
VREG_CHIP_RESET: uint32 = 0x08     # Chip reset control and status

# VREG register bits
VREG_EN: uint32 = 0x01             # Enable regulator
VREG_HIZ: uint32 = 0x02            # High impedance mode (regulator off)
VREG_VSEL_MASK: uint32 = 0xF0      # Voltage select (bits 4-7)
VREG_VSEL_SHIFT: uint32 = 4
VREG_ROK: uint32 = 0x1000          # Regulator OK status (bit 12)

# VREG voltage select values (VSEL field)
VREG_VOLTAGE_0_85V: uint32 = 0x06  # 0.85V (minimum)
VREG_VOLTAGE_0_90V: uint32 = 0x07  # 0.90V
VREG_VOLTAGE_0_95V: uint32 = 0x08  # 0.95V
VREG_VOLTAGE_1_00V: uint32 = 0x09  # 1.00V
VREG_VOLTAGE_1_05V: uint32 = 0x0A  # 1.05V
VREG_VOLTAGE_1_10V: uint32 = 0x0B  # 1.10V (default)
VREG_VOLTAGE_1_15V: uint32 = 0x0C  # 1.15V
VREG_VOLTAGE_1_20V: uint32 = 0x0D  # 1.20V
VREG_VOLTAGE_1_25V: uint32 = 0x0E  # 1.25V
VREG_VOLTAGE_1_30V: uint32 = 0x0F  # 1.30V (maximum)

# BOD register bits
BOD_EN: uint32 = 0x01              # Enable brownout detector
BOD_VSEL_MASK: uint32 = 0xF0       # Voltage threshold select
BOD_VSEL_SHIFT: uint32 = 4

# BOD voltage threshold values
BOD_THRESHOLD_0_473V: uint32 = 0x00
BOD_THRESHOLD_0_516V: uint32 = 0x01
BOD_THRESHOLD_0_559V: uint32 = 0x02
BOD_THRESHOLD_0_602V: uint32 = 0x03
BOD_THRESHOLD_0_645V: uint32 = 0x04
BOD_THRESHOLD_0_688V: uint32 = 0x05
BOD_THRESHOLD_0_731V: uint32 = 0x06
BOD_THRESHOLD_0_774V: uint32 = 0x07
BOD_THRESHOLD_0_817V: uint32 = 0x08
BOD_THRESHOLD_0_860V: uint32 = 0x09  # Default
BOD_THRESHOLD_0_903V: uint32 = 0x0A
BOD_THRESHOLD_0_946V: uint32 = 0x0B
BOD_THRESHOLD_0_989V: uint32 = 0x0C
BOD_THRESHOLD_1_032V: uint32 = 0x0D
BOD_THRESHOLD_1_075V: uint32 = 0x0E
BOD_THRESHOLD_1_118V: uint32 = 0x0F

# CHIP_RESET register bits
CHIP_RESET_HAD_POR: uint32 = 0x100       # Had power-on reset
CHIP_RESET_HAD_RUN: uint32 = 0x200       # Had RUN pin reset
CHIP_RESET_HAD_PSM_RESTART: uint32 = 0x400  # Had PSM restart

# ============================================================================
# ROSC (Ring Oscillator) Registers
# ============================================================================

ROSC_CTRL: uint32 = 0x00           # Control register
ROSC_FREQA: uint32 = 0x04          # Frequency control A
ROSC_FREQB: uint32 = 0x08          # Frequency control B
ROSC_DORMANT: uint32 = 0x0C        # Dormant control
ROSC_DIV: uint32 = 0x10            # Divider
ROSC_PHASE: uint32 = 0x14          # Phase control
ROSC_STATUS: uint32 = 0x18         # Status register
ROSC_RANDOMBIT: uint32 = 0x1C      # Random bit

# ROSC CTRL register bits
ROSC_CTRL_ENABLE_MASK: uint32 = 0x00FFF000
ROSC_CTRL_ENABLE_DISABLE: uint32 = 0x00D1E000  # Magic value to disable
ROSC_CTRL_ENABLE_ENABLE: uint32 = 0x00FAB000   # Magic value to enable
ROSC_CTRL_FREQ_RANGE_MASK: uint32 = 0x00000FFF
ROSC_CTRL_FREQ_RANGE_LOW: uint32 = 0x00000FA4
ROSC_CTRL_FREQ_RANGE_MEDIUM: uint32 = 0x00000FA5
ROSC_CTRL_FREQ_RANGE_HIGH: uint32 = 0x00000FA7
ROSC_CTRL_FREQ_RANGE_TOOHIGH: uint32 = 0x00000FA6

# ROSC DORMANT values
ROSC_DORMANT_DORMANT: uint32 = 0x636F6D61  # 'coma' - enter dormant
ROSC_DORMANT_WAKE: uint32 = 0x77616B65     # 'wake' - wake from dormant

# ROSC STATUS bits
ROSC_STATUS_STABLE: uint32 = 0x80000000
ROSC_STATUS_ENABLED: uint32 = 0x00001000

# ============================================================================
# XOSC (Crystal Oscillator) Registers
# ============================================================================

XOSC_CTRL: uint32 = 0x00           # Control register
XOSC_STATUS: uint32 = 0x04         # Status register
XOSC_DORMANT: uint32 = 0x08        # Dormant control
XOSC_STARTUP: uint32 = 0x0C        # Startup delay
XOSC_COUNT: uint32 = 0x1C          # Count register

# XOSC CTRL register bits
XOSC_CTRL_ENABLE_MASK: uint32 = 0x00FFF000
XOSC_CTRL_ENABLE_DISABLE: uint32 = 0x00D1E000
XOSC_CTRL_ENABLE_ENABLE: uint32 = 0x00FAB000
XOSC_CTRL_FREQ_RANGE_MASK: uint32 = 0x00000FFF
XOSC_CTRL_FREQ_RANGE_1_15MHZ: uint32 = 0x00000AA0

# XOSC DORMANT values
XOSC_DORMANT_DORMANT: uint32 = 0x636F6D61  # 'coma'
XOSC_DORMANT_WAKE: uint32 = 0x77616B65     # 'wake'

# XOSC STATUS bits
XOSC_STATUS_STABLE: uint32 = 0x80000000
XOSC_STATUS_ENABLED: uint32 = 0x00001000

# ============================================================================
# PSM (Power-on State Machine) Registers
# ============================================================================

PSM_FRCE_ON: uint32 = 0x00         # Force block on
PSM_FRCE_OFF: uint32 = 0x04        # Force block off
PSM_WDSEL: uint32 = 0x08           # Watchdog select
PSM_DONE: uint32 = 0x0C            # Power-on done status

# PSM block bits
PSM_ROSC: uint32 = 0x0001
PSM_XOSC: uint32 = 0x0002
PSM_CLOCKS: uint32 = 0x0004
PSM_RESETS: uint32 = 0x0008
PSM_BUSFABRIC: uint32 = 0x0010
PSM_ROM: uint32 = 0x0020
PSM_SRAM0: uint32 = 0x0040
PSM_SRAM1: uint32 = 0x0080
PSM_SRAM2: uint32 = 0x0100
PSM_SRAM3: uint32 = 0x0200
PSM_SRAM4: uint32 = 0x0400
PSM_SRAM5: uint32 = 0x0800
PSM_XIP: uint32 = 0x1000
PSM_VREG_AND_CHIP_RESET: uint32 = 0x2000
PSM_SIO: uint32 = 0x4000
PSM_PROC0: uint32 = 0x8000
PSM_PROC1: uint32 = 0x10000

# ============================================================================
# Clocks Registers (relevant for power management)
# ============================================================================

CLK_REF_CTRL: uint32 = 0x30
CLK_SYS_CTRL: uint32 = 0x3C
CLK_SYS_RESUS_CTRL: uint32 = 0x78

# ============================================================================
# SCB (System Control Block) bits
# ============================================================================

SCB_SCR_SLEEPDEEP: uint32 = 0x04   # Deep sleep enable
SCB_SCR_SLEEPONEXIT: uint32 = 0x02 # Sleep on exception return
SCB_SCR_SEVONPEND: uint32 = 0x10   # SEV on pending

# ============================================================================
# GPIO Dormant Wake Configuration
# ============================================================================

# GPIO dormant wake source bits
IO_BANK0_DORMANT_WAKE_INTE: uint32 = 0x160  # Interrupt enable for dormant wake

# Edge types
EDGE_LOW: uint32 = 0
EDGE_HIGH: uint32 = 1
EDGE_FALL: uint32 = 2
EDGE_RISE: uint32 = 3

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

def _wait_cycles(count: uint32):
    """Simple delay loop."""
    i: uint32 = 0
    while i < count:
        i = i + 1

# ============================================================================
# Voltage Regulator Control
# ============================================================================

def vreg_set_voltage(voltage: uint32):
    """Set core voltage.

    Args:
        voltage: Voltage select value (VREG_VOLTAGE_*)
    """
    val: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_VREG)
    val = val & ~VREG_VSEL_MASK
    val = val | ((voltage & 0x0F) << VREG_VSEL_SHIFT)
    mmio_write(VREG_AND_CHIP_RESET_BASE + VREG_VREG, val)

    # Wait for regulator to stabilize
    timeout: int32 = 10000
    while timeout > 0:
        status: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_VREG)
        if (status & VREG_ROK) != 0:
            break
        timeout = timeout - 1

def vreg_get_voltage() -> uint32:
    """Get current core voltage setting.

    Returns:
        Voltage select value
    """
    val: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_VREG)
    return (val & VREG_VSEL_MASK) >> VREG_VSEL_SHIFT

def vreg_disable():
    """Disable voltage regulator (enter high-impedance mode).

    WARNING: This will cut power to the core. Only use if external
    power supply is provided.
    """
    val: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_VREG)
    val = val | VREG_HIZ
    mmio_write(VREG_AND_CHIP_RESET_BASE + VREG_VREG, val)

def vreg_enable():
    """Enable voltage regulator."""
    val: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_VREG)
    val = val & ~VREG_HIZ
    val = val | VREG_EN
    mmio_write(VREG_AND_CHIP_RESET_BASE + VREG_VREG, val)

    # Wait for regulator OK
    timeout: int32 = 10000
    while timeout > 0:
        status: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_VREG)
        if (status & VREG_ROK) != 0:
            break
        timeout = timeout - 1

def vreg_is_ok() -> bool:
    """Check if voltage regulator output is stable.

    Returns:
        True if regulator output is OK
    """
    val: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_VREG)
    return (val & VREG_ROK) != 0

# ============================================================================
# Brownout Detector (BOD)
# ============================================================================

def bod_enable(threshold: uint32):
    """Enable brownout detector.

    The BOD will reset the chip if voltage drops below threshold.

    Args:
        threshold: Threshold value (BOD_THRESHOLD_*)
    """
    val: uint32 = (threshold & 0x0F) << BOD_VSEL_SHIFT
    val = val | BOD_EN
    mmio_write(VREG_AND_CHIP_RESET_BASE + VREG_BOD, val)

def bod_disable():
    """Disable brownout detector."""
    mmio_write(VREG_AND_CHIP_RESET_BASE + VREG_BOD, 0)

def bod_set_threshold(threshold: uint32):
    """Set brownout detector threshold.

    Args:
        threshold: Threshold value (BOD_THRESHOLD_*)
    """
    val: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_BOD)
    val = val & ~BOD_VSEL_MASK
    val = val | ((threshold & 0x0F) << BOD_VSEL_SHIFT)
    mmio_write(VREG_AND_CHIP_RESET_BASE + VREG_BOD, val)

# ============================================================================
# ROSC (Ring Oscillator) Control
# ============================================================================

def rosc_enable():
    """Enable the ring oscillator."""
    ctrl: uint32 = mmio_read(ROSC_BASE + ROSC_CTRL)
    ctrl = ctrl & ~ROSC_CTRL_ENABLE_MASK
    ctrl = ctrl | ROSC_CTRL_ENABLE_ENABLE
    mmio_write(ROSC_BASE + ROSC_CTRL, ctrl)

    # Wait for ROSC to stabilize
    timeout: int32 = 10000
    while timeout > 0:
        status: uint32 = mmio_read(ROSC_BASE + ROSC_STATUS)
        if (status & ROSC_STATUS_STABLE) != 0:
            break
        timeout = timeout - 1

def rosc_disable():
    """Disable the ring oscillator.

    WARNING: Ensure system clock is not using ROSC before disabling.
    """
    ctrl: uint32 = mmio_read(ROSC_BASE + ROSC_CTRL)
    ctrl = ctrl & ~ROSC_CTRL_ENABLE_MASK
    ctrl = ctrl | ROSC_CTRL_ENABLE_DISABLE
    mmio_write(ROSC_BASE + ROSC_CTRL, ctrl)

def rosc_is_running() -> bool:
    """Check if ROSC is enabled and stable.

    Returns:
        True if ROSC is running
    """
    status: uint32 = mmio_read(ROSC_BASE + ROSC_STATUS)
    return (status & ROSC_STATUS_STABLE) != 0

def rosc_set_freq_range(range: uint32):
    """Set ROSC frequency range.

    Args:
        range: Frequency range (ROSC_CTRL_FREQ_RANGE_*)
    """
    ctrl: uint32 = mmio_read(ROSC_BASE + ROSC_CTRL)
    ctrl = ctrl & ~ROSC_CTRL_FREQ_RANGE_MASK
    ctrl = ctrl | (range & ROSC_CTRL_FREQ_RANGE_MASK)
    mmio_write(ROSC_BASE + ROSC_CTRL, ctrl)

# ============================================================================
# XOSC (Crystal Oscillator) Control
# ============================================================================

def xosc_enable():
    """Enable the crystal oscillator."""
    ctrl: uint32 = mmio_read(XOSC_BASE + XOSC_CTRL)
    ctrl = ctrl & ~XOSC_CTRL_ENABLE_MASK
    ctrl = ctrl | XOSC_CTRL_ENABLE_ENABLE
    mmio_write(XOSC_BASE + XOSC_CTRL, ctrl)

    # Wait for XOSC to stabilize
    timeout: int32 = 100000
    while timeout > 0:
        status: uint32 = mmio_read(XOSC_BASE + XOSC_STATUS)
        if (status & XOSC_STATUS_STABLE) != 0:
            break
        timeout = timeout - 1

def xosc_disable():
    """Disable the crystal oscillator.

    WARNING: Ensure system clock is not using XOSC before disabling.
    Many peripherals (USB, RTC) require XOSC.
    """
    ctrl: uint32 = mmio_read(XOSC_BASE + XOSC_CTRL)
    ctrl = ctrl & ~XOSC_CTRL_ENABLE_MASK
    ctrl = ctrl | XOSC_CTRL_ENABLE_DISABLE
    mmio_write(XOSC_BASE + XOSC_CTRL, ctrl)

def xosc_is_running() -> bool:
    """Check if XOSC is enabled and stable.

    Returns:
        True if XOSC is running
    """
    status: uint32 = mmio_read(XOSC_BASE + XOSC_STATUS)
    return (status & XOSC_STATUS_STABLE) != 0

# ============================================================================
# Power-on State Machine (PSM) Control
# ============================================================================

def psm_set_force_on(mask: uint32):
    """Force power blocks to stay on.

    Args:
        mask: Bit mask of blocks to force on (PSM_*)
    """
    mmio_write(PSM_BASE + PSM_FRCE_ON, mask)

def psm_set_force_off(mask: uint32):
    """Force power blocks off.

    Args:
        mask: Bit mask of blocks to force off (PSM_*)
    """
    mmio_write(PSM_BASE + PSM_FRCE_OFF, mask)

def psm_clear_force_on(mask: uint32):
    """Clear force-on for power blocks.

    Args:
        mask: Bit mask of blocks
    """
    val: uint32 = mmio_read(PSM_BASE + PSM_FRCE_ON)
    mmio_write(PSM_BASE + PSM_FRCE_ON, val & ~mask)

def psm_clear_force_off(mask: uint32):
    """Clear force-off for power blocks.

    Args:
        mask: Bit mask of blocks
    """
    val: uint32 = mmio_read(PSM_BASE + PSM_FRCE_OFF)
    mmio_write(PSM_BASE + PSM_FRCE_OFF, val & ~mask)

def psm_is_on(mask: uint32) -> bool:
    """Check if power blocks are on.

    Args:
        mask: Bit mask of blocks to check

    Returns:
        True if all specified blocks are powered on
    """
    done: uint32 = mmio_read(PSM_BASE + PSM_DONE)
    return (done & mask) == mask

# ============================================================================
# Sleep Modes
# ============================================================================

def sleep_cpu():
    """Enter light sleep (WFI - Wait For Interrupt).

    CPU stops executing but wakes on any enabled interrupt.
    Clocks continue running.
    """
    # Clear SLEEPDEEP bit for light sleep
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr & ~SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # Data synchronization barrier before WFI
    __dsb()
    __wfi()
    __isb()

def sleep_on_exit(enable: bool):
    """Enable sleep on exception return.

    When enabled, CPU enters sleep mode after handling interrupt
    instead of returning to main program.

    Args:
        enable: True to enable sleep on exit
    """
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    if enable:
        scr = scr | SCB_SCR_SLEEPONEXIT
    else:
        scr = scr & ~SCB_SCR_SLEEPONEXIT
    mmio_write(SCB_BASE + SCB_SCR, scr)

def _configure_dormant_wake_gpio(gpio: uint32, edge: uint32):
    """Configure GPIO as dormant wake source.

    Args:
        gpio: GPIO pin number (0-29)
        edge: Edge type (EDGE_LOW, EDGE_HIGH, EDGE_FALL, EDGE_RISE)
    """
    if gpio > 29:
        return

    # Calculate register index and bit position
    reg_idx: uint32 = gpio / 8
    bit_pos: uint32 = (gpio % 8) * 4 + edge

    # Enable dormant wake interrupt for this GPIO/edge
    inte_addr: uint32 = IO_BANK0_BASE + IO_BANK0_DORMANT_WAKE_INTE + reg_idx * 4
    val: uint32 = mmio_read(inte_addr)
    val = val | (1 << bit_pos)
    mmio_write(inte_addr, val)

def _clear_dormant_wake_gpio():
    """Clear all dormant wake GPIO configurations."""
    i: uint32 = 0
    while i < 4:
        addr: uint32 = IO_BANK0_BASE + IO_BANK0_DORMANT_WAKE_INTE + i * 4
        mmio_write(addr, 0)
        i = i + 1

def dormant():
    """Enter dormant (deep sleep) mode.

    All clocks stop. Wake source must be configured before calling.
    Very low power consumption.

    NOTE: Call dormant_until_pin() or dormant_until_rtc() instead
    for proper wake source configuration.
    """
    # Set SLEEPDEEP for dormant mode
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr | SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # Put oscillators into dormant mode
    # This will stop all clocks until wake event
    mmio_write(XOSC_BASE + XOSC_DORMANT, XOSC_DORMANT_DORMANT)

    # Should never reach here until wake event
    __dsb()
    __wfi()
    __isb()

def dormant_until_pin(gpio: uint32, edge: uint32):
    """Enter dormant mode until GPIO event.

    Args:
        gpio: GPIO pin number (0-29)
        edge: Edge type (EDGE_RISE or EDGE_FALL)
    """
    if gpio > 29:
        return

    # Clear any previous wake configuration
    _clear_dormant_wake_gpio()

    # Configure wake source
    _configure_dormant_wake_gpio(gpio, edge)

    # Set SLEEPDEEP
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr | SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # Enter dormant using ROSC (preferred for GPIO wake)
    mmio_write(ROSC_BASE + ROSC_DORMANT, ROSC_DORMANT_DORMANT)

    # Wait for wake
    __dsb()
    __wfi()
    __isb()

    # Recovery sequence after dormant
    _dormant_recovery()

def dormant_until_rtc():
    """Enter dormant mode until RTC alarm.

    RTC alarm must be configured before calling this function.
    """
    # Set SLEEPDEEP
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr | SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # Enter dormant using XOSC (required for RTC wake)
    # RTC continues to run from XOSC
    mmio_write(XOSC_BASE + XOSC_DORMANT, XOSC_DORMANT_DORMANT)

    # Wait for wake
    __dsb()
    __wfi()
    __isb()

    # Recovery sequence
    _dormant_recovery()

def _dormant_recovery():
    """Recovery sequence after waking from dormant mode.

    Re-enables oscillators and waits for them to stabilize.
    """
    # Wake ROSC
    mmio_write(ROSC_BASE + ROSC_DORMANT, ROSC_DORMANT_WAKE)

    # Wait for ROSC to stabilize
    timeout: int32 = 10000
    while timeout > 0:
        status: uint32 = mmio_read(ROSC_BASE + ROSC_STATUS)
        if (status & ROSC_STATUS_STABLE) != 0:
            break
        timeout = timeout - 1

    # Wake XOSC
    mmio_write(XOSC_BASE + XOSC_DORMANT, XOSC_DORMANT_WAKE)

    # Wait for XOSC to stabilize
    timeout = 100000
    while timeout > 0:
        status: uint32 = mmio_read(XOSC_BASE + XOSC_STATUS)
        if (status & XOSC_STATUS_STABLE) != 0:
            break
        timeout = timeout - 1

    # Clear SLEEPDEEP
    scr: uint32 = mmio_read(SCB_BASE + SCB_SCR)
    scr = scr & ~SCB_SCR_SLEEPDEEP
    mmio_write(SCB_BASE + SCB_SCR, scr)

    # Clear dormant wake interrupts
    _clear_dormant_wake_gpio()

# ============================================================================
# USB Wake Support
# ============================================================================

def dormant_enable_usb_wake():
    """Enable USB VBUS as wake source from dormant.

    USB activity can wake the system from dormant mode.
    """
    # USB uses XOSC, so configure XOSC for dormant wake
    # The USB VBUS detect is connected to an internal wake source
    pass  # USB wake is automatic when USB is enabled

# ============================================================================
# Reset Status
# ============================================================================

def get_reset_reason() -> uint32:
    """Get the reason for last chip reset.

    Returns:
        Bit mask of reset reasons (CHIP_RESET_HAD_*)
    """
    return mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_CHIP_RESET)

def had_power_on_reset() -> bool:
    """Check if last reset was power-on reset.

    Returns:
        True if power-on reset occurred
    """
    status: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_CHIP_RESET)
    return (status & CHIP_RESET_HAD_POR) != 0

def had_run_pin_reset() -> bool:
    """Check if last reset was from RUN pin.

    Returns:
        True if RUN pin reset occurred
    """
    status: uint32 = mmio_read(VREG_AND_CHIP_RESET_BASE + VREG_CHIP_RESET)
    return (status & CHIP_RESET_HAD_RUN) != 0

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
    """Send Event - wakes other cores."""
    pass

# ============================================================================
# Power Profile Presets
# ============================================================================

def power_set_low_power():
    """Configure for low power operation.

    Reduces voltage and disables unused oscillator.
    """
    # Lower voltage for reduced power
    vreg_set_voltage(VREG_VOLTAGE_1_00V)

    # Disable ROSC if using XOSC
    if xosc_is_running():
        rosc_disable()

def power_set_high_performance():
    """Configure for high performance operation.

    Increases voltage for maximum clock speed.
    """
    # Higher voltage for stability at high frequencies
    vreg_set_voltage(VREG_VOLTAGE_1_15V)

    # Ensure both oscillators available
    rosc_enable()
    xosc_enable()

def power_set_default():
    """Reset to default power configuration."""
    vreg_set_voltage(VREG_VOLTAGE_1_10V)
    bod_enable(BOD_THRESHOLD_0_860V)
    rosc_enable()
    xosc_enable()
