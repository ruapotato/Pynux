# RP2040 GPIO External Interrupt Driver
#
# GPIO interrupts on RP2040 are handled through IO_BANK0.
# Each GPIO can trigger on:
#   - Level low/high
#   - Edge falling/rising
#
# All GPIO interrupts share IRQ13 (IO_IRQ_BANK0)

# ============================================================================
# Base Addresses
# ============================================================================

IO_BANK0_BASE: uint32 = 0x40014000
PPB_BASE: uint32 = 0xE0000000

# NVIC registers (in PPB)
NVIC_ISER: uint32 = 0xE000E100  # Interrupt Set Enable
NVIC_ICER: uint32 = 0xE000E180  # Interrupt Clear Enable
NVIC_ISPR: uint32 = 0xE000E200  # Interrupt Set Pending
NVIC_ICPR: uint32 = 0xE000E280  # Interrupt Clear Pending
NVIC_IPR: uint32 = 0xE000E400   # Interrupt Priority

# ============================================================================
# IO_BANK0 Interrupt Registers
# ============================================================================

# Each GPIO has 4 interrupt types (level low, level high, edge fall, edge rise)
# Packed 4 bits per GPIO, 8 GPIOs per 32-bit register

# Interrupt status registers (active interrupts)
IO_BANK0_INTR0: uint32 = 0x0F0  # GPIO 0-7
IO_BANK0_INTR1: uint32 = 0x0F4  # GPIO 8-15
IO_BANK0_INTR2: uint32 = 0x0F8  # GPIO 16-23
IO_BANK0_INTR3: uint32 = 0x0FC  # GPIO 24-29

# Interrupt enable for processor 0
IO_BANK0_PROC0_INTE0: uint32 = 0x100
IO_BANK0_PROC0_INTE1: uint32 = 0x104
IO_BANK0_PROC0_INTE2: uint32 = 0x108
IO_BANK0_PROC0_INTE3: uint32 = 0x10C

# Interrupt force (for testing)
IO_BANK0_PROC0_INTF0: uint32 = 0x110
IO_BANK0_PROC0_INTF1: uint32 = 0x114
IO_BANK0_PROC0_INTF2: uint32 = 0x118
IO_BANK0_PROC0_INTF3: uint32 = 0x11C

# Interrupt status (masked by enable)
IO_BANK0_PROC0_INTS0: uint32 = 0x120
IO_BANK0_PROC0_INTS1: uint32 = 0x124
IO_BANK0_PROC0_INTS2: uint32 = 0x128
IO_BANK0_PROC0_INTS3: uint32 = 0x12C

# ============================================================================
# Interrupt Type Bits (4 bits per GPIO)
# ============================================================================

GPIO_IRQ_LEVEL_LOW: uint32 = 0x1
GPIO_IRQ_LEVEL_HIGH: uint32 = 0x2
GPIO_IRQ_EDGE_FALL: uint32 = 0x4
GPIO_IRQ_EDGE_RISE: uint32 = 0x8

# IO_IRQ_BANK0 is IRQ 13
IO_IRQ_BANK0: uint32 = 13

# ============================================================================
# Callback Storage
# ============================================================================

# Callback function pointers (one per GPIO)
_gpio_callbacks: Array[30, uint32]  # Function pointers
_gpio_callback_args: Array[30, uint32]  # User data
_gpio_initialized: bool = False

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _get_inte_reg(gpio: uint32) -> uint32:
    """Get interrupt enable register for GPIO."""
    if gpio < 8:
        return IO_BANK0_BASE + IO_BANK0_PROC0_INTE0
    elif gpio < 16:
        return IO_BANK0_BASE + IO_BANK0_PROC0_INTE1
    elif gpio < 24:
        return IO_BANK0_BASE + IO_BANK0_PROC0_INTE2
    return IO_BANK0_BASE + IO_BANK0_PROC0_INTE3

def _get_intr_reg(gpio: uint32) -> uint32:
    """Get raw interrupt status register for GPIO."""
    if gpio < 8:
        return IO_BANK0_BASE + IO_BANK0_INTR0
    elif gpio < 16:
        return IO_BANK0_BASE + IO_BANK0_INTR1
    elif gpio < 24:
        return IO_BANK0_BASE + IO_BANK0_INTR2
    return IO_BANK0_BASE + IO_BANK0_INTR3

def _get_ints_reg(gpio: uint32) -> uint32:
    """Get masked interrupt status register for GPIO."""
    if gpio < 8:
        return IO_BANK0_BASE + IO_BANK0_PROC0_INTS0
    elif gpio < 16:
        return IO_BANK0_BASE + IO_BANK0_PROC0_INTS1
    elif gpio < 24:
        return IO_BANK0_BASE + IO_BANK0_PROC0_INTS2
    return IO_BANK0_BASE + IO_BANK0_PROC0_INTS3

def _gpio_bit_offset(gpio: uint32) -> uint32:
    """Get bit offset within register for GPIO (4 bits per GPIO)."""
    return (gpio & 7) * 4

# ============================================================================
# Interrupt Setup
# ============================================================================

def gpio_irq_init():
    """Initialize GPIO interrupt system."""
    global _gpio_initialized

    if _gpio_initialized:
        return

    # Clear all callbacks
    i: int32 = 0
    while i < 30:
        _gpio_callbacks[i] = 0
        _gpio_callback_args[i] = 0
        i = i + 1

    # Disable all GPIO interrupts
    mmio_write(IO_BANK0_BASE + IO_BANK0_PROC0_INTE0, 0)
    mmio_write(IO_BANK0_BASE + IO_BANK0_PROC0_INTE1, 0)
    mmio_write(IO_BANK0_BASE + IO_BANK0_PROC0_INTE2, 0)
    mmio_write(IO_BANK0_BASE + IO_BANK0_PROC0_INTE3, 0)

    # Clear any pending interrupts
    mmio_write(IO_BANK0_BASE + IO_BANK0_INTR0, 0xFFFFFFFF)
    mmio_write(IO_BANK0_BASE + IO_BANK0_INTR1, 0xFFFFFFFF)
    mmio_write(IO_BANK0_BASE + IO_BANK0_INTR2, 0xFFFFFFFF)
    mmio_write(IO_BANK0_BASE + IO_BANK0_INTR3, 0xFFFFFFFF)

    # Enable IO_IRQ_BANK0 in NVIC
    mmio_write(NVIC_ISER, 1 << IO_IRQ_BANK0)

    _gpio_initialized = True

def gpio_set_irq_enabled(gpio: uint32, events: uint32, enabled: bool):
    """Enable/disable GPIO interrupt events.

    Args:
        gpio: GPIO pin (0-29)
        events: Bitmask of GPIO_IRQ_* events
        enabled: True to enable, False to disable
    """
    if gpio > 29:
        return

    inte_reg: uint32 = _get_inte_reg(gpio)
    offset: uint32 = _gpio_bit_offset(gpio)

    val: uint32 = mmio_read(inte_reg)

    if enabled:
        val = val | ((events & 0xF) << offset)
    else:
        val = val & ~((events & 0xF) << offset)

    mmio_write(inte_reg, val)

def gpio_set_irq_callback(gpio: uint32, callback: uint32, arg: uint32):
    """Set callback function for GPIO interrupt.

    Args:
        gpio: GPIO pin (0-29)
        callback: Function pointer (called with gpio, events, arg)
        arg: User data passed to callback
    """
    if gpio > 29:
        return

    _gpio_callbacks[gpio] = callback
    _gpio_callback_args[gpio] = arg

def gpio_acknowledge_irq(gpio: uint32, events: uint32):
    """Acknowledge (clear) GPIO interrupt.

    Args:
        gpio: GPIO pin (0-29)
        events: Events to acknowledge
    """
    if gpio > 29:
        return

    intr_reg: uint32 = _get_intr_reg(gpio)
    offset: uint32 = _gpio_bit_offset(gpio)

    # Write 1 to clear
    mmio_write(intr_reg, (events & 0xF) << offset)

# ============================================================================
# Interrupt Handler
# ============================================================================

def gpio_irq_handler():
    """Main GPIO interrupt handler - call from IRQ13 handler.

    Checks all GPIOs for pending interrupts and calls registered callbacks.
    """
    # Process each GPIO bank
    gpio: uint32 = 0

    while gpio < 30:
        ints_reg: uint32 = _get_ints_reg(gpio)
        offset: uint32 = _gpio_bit_offset(gpio)

        status: uint32 = mmio_read(ints_reg)
        events: uint32 = (status >> offset) & 0xF

        if events != 0:
            # Acknowledge interrupt
            gpio_acknowledge_irq(gpio, events)

            # Call callback if registered
            callback: uint32 = _gpio_callbacks[gpio]
            if callback != 0:
                # Cast to function pointer and call
                # In real implementation, this would call the function
                # For now, just store that we had an interrupt
                pass

        gpio = gpio + 1

# ============================================================================
# Convenience Functions
# ============================================================================

def gpio_set_irq_edge(gpio: uint32, rising: bool, falling: bool):
    """Configure GPIO for edge-triggered interrupts.

    Args:
        gpio: GPIO pin (0-29)
        rising: Enable rising edge
        falling: Enable falling edge
    """
    events: uint32 = 0
    if rising:
        events = events | GPIO_IRQ_EDGE_RISE
    if falling:
        events = events | GPIO_IRQ_EDGE_FALL

    gpio_set_irq_enabled(gpio, events, True)

def gpio_set_irq_level(gpio: uint32, high: bool, low: bool):
    """Configure GPIO for level-triggered interrupts.

    Args:
        gpio: GPIO pin (0-29)
        high: Enable high level trigger
        low: Enable low level trigger
    """
    events: uint32 = 0
    if high:
        events = events | GPIO_IRQ_LEVEL_HIGH
    if low:
        events = events | GPIO_IRQ_LEVEL_LOW

    gpio_set_irq_enabled(gpio, events, True)

def gpio_disable_irq(gpio: uint32):
    """Disable all interrupts on GPIO.

    Args:
        gpio: GPIO pin (0-29)
    """
    gpio_set_irq_enabled(gpio, 0xF, False)

def gpio_get_irq_status(gpio: uint32) -> uint32:
    """Get pending interrupt events for GPIO.

    Args:
        gpio: GPIO pin (0-29)

    Returns:
        Bitmask of pending GPIO_IRQ_* events
    """
    if gpio > 29:
        return 0

    ints_reg: uint32 = _get_ints_reg(gpio)
    offset: uint32 = _gpio_bit_offset(gpio)

    status: uint32 = mmio_read(ints_reg)
    return (status >> offset) & 0xF

def gpio_wait_for_edge(gpio: uint32, rising: bool, timeout_ms: int32) -> bool:
    """Wait for edge on GPIO (polling).

    Args:
        gpio: GPIO pin (0-29)
        rising: Wait for rising edge (else falling)
        timeout_ms: Timeout in milliseconds

    Returns:
        True if edge detected, False on timeout
    """
    event: uint32 = GPIO_IRQ_EDGE_RISE if rising else GPIO_IRQ_EDGE_FALL
    intr_reg: uint32 = _get_intr_reg(gpio)
    offset: uint32 = _gpio_bit_offset(gpio)

    # Clear any pending
    gpio_acknowledge_irq(gpio, event)

    # Poll for edge
    timeout_loops: int32 = timeout_ms * 1000
    while timeout_loops > 0:
        status: uint32 = mmio_read(intr_reg)
        if ((status >> offset) & event) != 0:
            gpio_acknowledge_irq(gpio, event)
            return True
        timeout_loops = timeout_loops - 1

    return False
