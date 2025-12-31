# STM32F4 External Interrupt (EXTI) Driver
#
# EXTI lines 0-15 are connected to GPIO pins
# Each line can be mapped to one port (PA, PB, PC, etc.)
# Lines 16-22 are connected to internal peripherals (PVD, RTC, USB, etc.)
#
# IRQ mapping:
#   EXTI0: IRQ6, EXTI1: IRQ7, EXTI2: IRQ8, EXTI3: IRQ9, EXTI4: IRQ10
#   EXTI5-9: IRQ23 (shared), EXTI10-15: IRQ40 (shared)

# ============================================================================
# Base Addresses
# ============================================================================

EXTI_BASE: uint32 = 0x40013C00
SYSCFG_BASE: uint32 = 0x40013800
NVIC_ISER0: uint32 = 0xE000E100  # Interrupt Set Enable
NVIC_ICER0: uint32 = 0xE000E180  # Interrupt Clear Enable
NVIC_ICPR0: uint32 = 0xE000E280  # Interrupt Clear Pending

# ============================================================================
# EXTI Register Offsets
# ============================================================================

EXTI_IMR: uint32 = 0x00    # Interrupt mask register
EXTI_EMR: uint32 = 0x04    # Event mask register
EXTI_RTSR: uint32 = 0x08   # Rising trigger selection
EXTI_FTSR: uint32 = 0x0C   # Falling trigger selection
EXTI_SWIER: uint32 = 0x10  # Software interrupt event
EXTI_PR: uint32 = 0x14     # Pending register

# SYSCFG EXTICR registers (External interrupt configuration)
SYSCFG_EXTICR1: uint32 = 0x08  # EXTI 0-3
SYSCFG_EXTICR2: uint32 = 0x0C  # EXTI 4-7
SYSCFG_EXTICR3: uint32 = 0x10  # EXTI 8-11
SYSCFG_EXTICR4: uint32 = 0x14  # EXTI 12-15

# ============================================================================
# Port Definitions
# ============================================================================

PORT_A: uint32 = 0
PORT_B: uint32 = 1
PORT_C: uint32 = 2
PORT_D: uint32 = 3
PORT_E: uint32 = 4
PORT_F: uint32 = 5
PORT_G: uint32 = 6
PORT_H: uint32 = 7
PORT_I: uint32 = 8

# ============================================================================
# Trigger Mode
# ============================================================================

EXTI_TRIGGER_RISING: uint32 = 0x01
EXTI_TRIGGER_FALLING: uint32 = 0x02
EXTI_TRIGGER_BOTH: uint32 = 0x03

# ============================================================================
# IRQ Numbers
# ============================================================================

EXTI0_IRQ: uint32 = 6
EXTI1_IRQ: uint32 = 7
EXTI2_IRQ: uint32 = 8
EXTI3_IRQ: uint32 = 9
EXTI4_IRQ: uint32 = 10
EXTI9_5_IRQ: uint32 = 23
EXTI15_10_IRQ: uint32 = 40

# ============================================================================
# Callback Storage
# ============================================================================

_exti_callbacks: Array[16, uint32]  # Function pointers
_exti_callback_args: Array[16, uint32]  # User data
_exti_initialized: bool = False

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _get_exticr_reg(line: uint32) -> uint32:
    """Get EXTICR register address for EXTI line."""
    if line < 4:
        return SYSCFG_BASE + SYSCFG_EXTICR1
    elif line < 8:
        return SYSCFG_BASE + SYSCFG_EXTICR2
    elif line < 12:
        return SYSCFG_BASE + SYSCFG_EXTICR3
    return SYSCFG_BASE + SYSCFG_EXTICR4

def _get_irq_number(line: uint32) -> uint32:
    """Get NVIC IRQ number for EXTI line."""
    if line == 0:
        return EXTI0_IRQ
    elif line == 1:
        return EXTI1_IRQ
    elif line == 2:
        return EXTI2_IRQ
    elif line == 3:
        return EXTI3_IRQ
    elif line == 4:
        return EXTI4_IRQ
    elif line < 10:
        return EXTI9_5_IRQ
    return EXTI15_10_IRQ

def _nvic_enable_irq(irq: uint32):
    """Enable interrupt in NVIC."""
    reg: uint32 = NVIC_ISER0 + (irq / 32) * 4
    bit: uint32 = irq & 31
    mmio_write(reg, 1 << bit)

def _nvic_disable_irq(irq: uint32):
    """Disable interrupt in NVIC."""
    reg: uint32 = NVIC_ICER0 + (irq / 32) * 4
    bit: uint32 = irq & 31
    mmio_write(reg, 1 << bit)

# ============================================================================
# Initialization
# ============================================================================

def exti_init():
    """Initialize EXTI system."""
    global _exti_initialized

    if _exti_initialized:
        return

    # Clear all callbacks
    i: int32 = 0
    while i < 16:
        _exti_callbacks[i] = 0
        _exti_callback_args[i] = 0
        i = i + 1

    # Disable all EXTI interrupts
    mmio_write(EXTI_BASE + EXTI_IMR, 0)

    # Clear any pending interrupts
    mmio_write(EXTI_BASE + EXTI_PR, 0xFFFFFFFF)

    _exti_initialized = True

# ============================================================================
# Configuration
# ============================================================================

def exti_set_port(line: uint32, port: uint32):
    """Map EXTI line to GPIO port.

    Args:
        line: EXTI line (0-15)
        port: Port (PORT_A, PORT_B, etc.)
    """
    if line > 15 or port > 8:
        return

    exticr_reg: uint32 = _get_exticr_reg(line)
    shift: uint32 = (line & 3) * 4

    val: uint32 = mmio_read(exticr_reg)
    val = val & ~(0x0F << shift)
    val = val | (port << shift)
    mmio_write(exticr_reg, val)

def exti_set_trigger(line: uint32, trigger: uint32):
    """Set trigger mode for EXTI line.

    Args:
        line: EXTI line (0-15)
        trigger: EXTI_TRIGGER_RISING, FALLING, or BOTH
    """
    if line > 15:
        return

    mask: uint32 = 1 << line

    # Configure rising trigger
    rtsr: uint32 = mmio_read(EXTI_BASE + EXTI_RTSR)
    if (trigger & EXTI_TRIGGER_RISING) != 0:
        rtsr = rtsr | mask
    else:
        rtsr = rtsr & ~mask
    mmio_write(EXTI_BASE + EXTI_RTSR, rtsr)

    # Configure falling trigger
    ftsr: uint32 = mmio_read(EXTI_BASE + EXTI_FTSR)
    if (trigger & EXTI_TRIGGER_FALLING) != 0:
        ftsr = ftsr | mask
    else:
        ftsr = ftsr & ~mask
    mmio_write(EXTI_BASE + EXTI_FTSR, ftsr)

def exti_enable(line: uint32):
    """Enable EXTI interrupt.

    Args:
        line: EXTI line (0-15)
    """
    if line > 15:
        return

    # Enable in EXTI
    imr: uint32 = mmio_read(EXTI_BASE + EXTI_IMR)
    mmio_write(EXTI_BASE + EXTI_IMR, imr | (1 << line))

    # Enable in NVIC
    irq: uint32 = _get_irq_number(line)
    _nvic_enable_irq(irq)

def exti_disable(line: uint32):
    """Disable EXTI interrupt.

    Args:
        line: EXTI line (0-15)
    """
    if line > 15:
        return

    imr: uint32 = mmio_read(EXTI_BASE + EXTI_IMR)
    mmio_write(EXTI_BASE + EXTI_IMR, imr & ~(1 << line))

def exti_set_callback(line: uint32, callback: uint32, arg: uint32):
    """Set callback function for EXTI line.

    Args:
        line: EXTI line (0-15)
        callback: Function pointer
        arg: User data passed to callback
    """
    if line > 15:
        return

    _exti_callbacks[line] = callback
    _exti_callback_args[line] = arg

def exti_clear_pending(line: uint32):
    """Clear pending interrupt for EXTI line.

    Args:
        line: EXTI line (0-15)
    """
    if line > 15:
        return

    # Write 1 to clear
    mmio_write(EXTI_BASE + EXTI_PR, 1 << line)

def exti_is_pending(line: uint32) -> bool:
    """Check if EXTI line has pending interrupt.

    Args:
        line: EXTI line (0-15)

    Returns:
        True if interrupt pending
    """
    if line > 15:
        return False

    pr: uint32 = mmio_read(EXTI_BASE + EXTI_PR)
    return (pr & (1 << line)) != 0

# ============================================================================
# Convenience Functions
# ============================================================================

def exti_configure(port: uint32, pin: uint32, trigger: uint32, callback: uint32, arg: uint32):
    """Configure GPIO pin as external interrupt source.

    Args:
        port: GPIO port (PORT_A, PORT_B, etc.)
        pin: Pin number (0-15)
        trigger: Trigger mode
        callback: Handler function
        arg: User data
    """
    if pin > 15:
        return

    exti_set_port(pin, port)
    exti_set_trigger(pin, trigger)
    exti_set_callback(pin, callback, arg)
    exti_clear_pending(pin)
    exti_enable(pin)

def exti_configure_rising(port: uint32, pin: uint32, callback: uint32, arg: uint32):
    """Configure rising edge interrupt."""
    exti_configure(port, pin, EXTI_TRIGGER_RISING, callback, arg)

def exti_configure_falling(port: uint32, pin: uint32, callback: uint32, arg: uint32):
    """Configure falling edge interrupt."""
    exti_configure(port, pin, EXTI_TRIGGER_FALLING, callback, arg)

def exti_configure_both(port: uint32, pin: uint32, callback: uint32, arg: uint32):
    """Configure both edge interrupt."""
    exti_configure(port, pin, EXTI_TRIGGER_BOTH, callback, arg)

# ============================================================================
# IRQ Handlers
# ============================================================================

def _exti_handler_common(line: uint32):
    """Common handler for single EXTI line."""
    if exti_is_pending(line):
        exti_clear_pending(line)
        callback: uint32 = _exti_callbacks[line]
        if callback != 0:
            # In real implementation, call the callback
            pass

def exti0_handler():
    """EXTI line 0 interrupt handler."""
    _exti_handler_common(0)

def exti1_handler():
    """EXTI line 1 interrupt handler."""
    _exti_handler_common(1)

def exti2_handler():
    """EXTI line 2 interrupt handler."""
    _exti_handler_common(2)

def exti3_handler():
    """EXTI line 3 interrupt handler."""
    _exti_handler_common(3)

def exti4_handler():
    """EXTI line 4 interrupt handler."""
    _exti_handler_common(4)

def exti9_5_handler():
    """EXTI lines 5-9 shared interrupt handler."""
    line: uint32 = 5
    while line <= 9:
        _exti_handler_common(line)
        line = line + 1

def exti15_10_handler():
    """EXTI lines 10-15 shared interrupt handler."""
    line: uint32 = 10
    while line <= 15:
        _exti_handler_common(line)
        line = line + 1

# ============================================================================
# Software Trigger
# ============================================================================

def exti_software_trigger(line: uint32):
    """Trigger interrupt via software.

    Args:
        line: EXTI line (0-22)
    """
    if line > 22:
        return

    mmio_write(EXTI_BASE + EXTI_SWIER, 1 << line)

# ============================================================================
# Event Mode (for wakeup without CPU interrupt)
# ============================================================================

def exti_enable_event(line: uint32):
    """Enable EXTI event (wakeup without interrupt).

    Args:
        line: EXTI line (0-22)
    """
    if line > 22:
        return

    emr: uint32 = mmio_read(EXTI_BASE + EXTI_EMR)
    mmio_write(EXTI_BASE + EXTI_EMR, emr | (1 << line))

def exti_disable_event(line: uint32):
    """Disable EXTI event.

    Args:
        line: EXTI line (0-22)
    """
    if line > 22:
        return

    emr: uint32 = mmio_read(EXTI_BASE + EXTI_EMR)
    mmio_write(EXTI_BASE + EXTI_EMR, emr & ~(1 << line))
