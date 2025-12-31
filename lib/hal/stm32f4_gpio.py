# STM32F4 GPIO Hardware Abstraction Layer
#
# Low-level GPIO driver for STM32F405/F407 microcontrollers.
# Each GPIO port (A-I) has 16 pins with configurable modes,
# output types, speeds, and pull-up/pull-down resistors.
#
# Memory Map:
#   GPIOA: 0x40020000
#   GPIOB: 0x40020400
#   GPIOC: 0x40020800
#   GPIOD: 0x40020C00
#   GPIOE: 0x40021000
#   GPIOF: 0x40021400
#   GPIOG: 0x40021800
#   GPIOH: 0x40021C00
#   GPIOI: 0x40022000
#   RCC:   0x40023800 (for enabling GPIO clocks)

# ============================================================================
# Base Addresses
# ============================================================================

GPIOA_BASE: uint32 = 0x40020000
GPIOB_BASE: uint32 = 0x40020400
GPIOC_BASE: uint32 = 0x40020800
GPIOD_BASE: uint32 = 0x40020C00
GPIOE_BASE: uint32 = 0x40021000
GPIOF_BASE: uint32 = 0x40021400
GPIOG_BASE: uint32 = 0x40021800
GPIOH_BASE: uint32 = 0x40021C00
GPIOI_BASE: uint32 = 0x40022000

RCC_BASE: uint32 = 0x40023800

# GPIO port stride (0x400 bytes per port)
GPIO_PORT_STRIDE: uint32 = 0x400

# ============================================================================
# GPIO Register Offsets
# ============================================================================

GPIO_MODER: uint32 = 0x00     # Mode register (2 bits per pin)
GPIO_OTYPER: uint32 = 0x04    # Output type register (1 bit per pin)
GPIO_OSPEEDR: uint32 = 0x08   # Output speed register (2 bits per pin)
GPIO_PUPDR: uint32 = 0x0C     # Pull-up/pull-down register (2 bits per pin)
GPIO_IDR: uint32 = 0x10       # Input data register (read-only)
GPIO_ODR: uint32 = 0x14       # Output data register
GPIO_BSRR: uint32 = 0x18      # Bit set/reset register (atomic set/clear)
GPIO_LCKR: uint32 = 0x1C      # Lock register
GPIO_AFRL: uint32 = 0x20      # Alternate function low (pins 0-7, 4 bits each)
GPIO_AFRH: uint32 = 0x24      # Alternate function high (pins 8-15, 4 bits each)

# ============================================================================
# RCC Register Offsets (for GPIO clock enable)
# ============================================================================

RCC_AHB1ENR: uint32 = 0x30    # AHB1 peripheral clock enable

# GPIO clock enable bits in RCC_AHB1ENR
RCC_GPIOAEN: uint32 = 0x01
RCC_GPIOBEN: uint32 = 0x02
RCC_GPIOCEN: uint32 = 0x04
RCC_GPIODEN: uint32 = 0x08
RCC_GPIOEEN: uint32 = 0x10
RCC_GPIOFEN: uint32 = 0x20
RCC_GPIOGEN: uint32 = 0x40
RCC_GPIOHEN: uint32 = 0x80
RCC_GPIOIEN: uint32 = 0x100

# ============================================================================
# GPIO Mode Values (for MODER register, 2 bits per pin)
# ============================================================================

GPIO_MODE_INPUT: uint32 = 0     # Input mode
GPIO_MODE_OUTPUT: uint32 = 1    # General purpose output
GPIO_MODE_AF: uint32 = 2        # Alternate function
GPIO_MODE_ANALOG: uint32 = 3    # Analog mode

# ============================================================================
# GPIO Output Type (for OTYPER register, 1 bit per pin)
# ============================================================================

GPIO_OTYPE_PP: uint32 = 0       # Push-pull
GPIO_OTYPE_OD: uint32 = 1       # Open-drain

# ============================================================================
# GPIO Speed Values (for OSPEEDR register, 2 bits per pin)
# ============================================================================

GPIO_SPEED_LOW: uint32 = 0      # Low speed (2 MHz)
GPIO_SPEED_MEDIUM: uint32 = 1   # Medium speed (25 MHz)
GPIO_SPEED_FAST: uint32 = 2     # Fast speed (50 MHz)
GPIO_SPEED_HIGH: uint32 = 3     # High speed (100 MHz)

# ============================================================================
# GPIO Pull-up/Pull-down (for PUPDR register, 2 bits per pin)
# ============================================================================

GPIO_PULL_NONE: uint32 = 0      # No pull-up/pull-down
GPIO_PULL_UP: uint32 = 1        # Pull-up
GPIO_PULL_DOWN: uint32 = 2      # Pull-down

# ============================================================================
# Port Names (for convenience)
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

def _gpio_port_base(port: uint32) -> uint32:
    """Get base address for GPIO port."""
    return GPIOA_BASE + (port * GPIO_PORT_STRIDE)

# ============================================================================
# Clock Enable Functions
# ============================================================================

def gpio_enable_clock(port: uint32):
    """Enable clock for GPIO port.

    Must be called before using any GPIO functions on a port.

    Args:
        port: Port number (PORT_A through PORT_I)
    """
    if port > 8:
        return

    rcc_ahb1enr: uint32 = RCC_BASE + RCC_AHB1ENR
    val: uint32 = mmio_read(rcc_ahb1enr)
    val = val | (1 << port)
    mmio_write(rcc_ahb1enr, val)

    # Small delay for clock to stabilize
    dummy: uint32 = mmio_read(rcc_ahb1enr)

def gpio_enable_clocks_all():
    """Enable clocks for all GPIO ports."""
    rcc_ahb1enr: uint32 = RCC_BASE + RCC_AHB1ENR
    val: uint32 = mmio_read(rcc_ahb1enr)
    val = val | 0x1FF  # Enable GPIOA through GPIOI
    mmio_write(rcc_ahb1enr, val)

# ============================================================================
# GPIO Configuration Functions
# ============================================================================

def gpio_set_mode(port: uint32, pin: uint32, mode: uint32):
    """Set GPIO pin mode.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        mode: GPIO_MODE_INPUT, GPIO_MODE_OUTPUT, GPIO_MODE_AF, or GPIO_MODE_ANALOG
    """
    if port > 8 or pin > 15:
        return

    base: uint32 = _gpio_port_base(port)
    moder_addr: uint32 = base + GPIO_MODER

    val: uint32 = mmio_read(moder_addr)
    # Clear 2 bits for this pin
    val = val & ~(0x03 << (pin * 2))
    # Set new mode
    val = val | ((mode & 0x03) << (pin * 2))
    mmio_write(moder_addr, val)

def gpio_set_output_type(port: uint32, pin: uint32, otype: uint32):
    """Set GPIO output type.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        otype: GPIO_OTYPE_PP (push-pull) or GPIO_OTYPE_OD (open-drain)
    """
    if port > 8 or pin > 15:
        return

    base: uint32 = _gpio_port_base(port)
    otyper_addr: uint32 = base + GPIO_OTYPER

    val: uint32 = mmio_read(otyper_addr)
    if otype == GPIO_OTYPE_OD:
        val = val | (1 << pin)
    else:
        val = val & ~(1 << pin)
    mmio_write(otyper_addr, val)

def gpio_set_speed(port: uint32, pin: uint32, speed: uint32):
    """Set GPIO output speed.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        speed: GPIO_SPEED_LOW, GPIO_SPEED_MEDIUM, GPIO_SPEED_FAST, or GPIO_SPEED_HIGH
    """
    if port > 8 or pin > 15:
        return

    base: uint32 = _gpio_port_base(port)
    ospeedr_addr: uint32 = base + GPIO_OSPEEDR

    val: uint32 = mmio_read(ospeedr_addr)
    # Clear 2 bits for this pin
    val = val & ~(0x03 << (pin * 2))
    # Set new speed
    val = val | ((speed & 0x03) << (pin * 2))
    mmio_write(ospeedr_addr, val)

def gpio_set_pull(port: uint32, pin: uint32, pull: uint32):
    """Set GPIO pull-up/pull-down.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        pull: GPIO_PULL_NONE, GPIO_PULL_UP, or GPIO_PULL_DOWN
    """
    if port > 8 or pin > 15:
        return

    base: uint32 = _gpio_port_base(port)
    pupdr_addr: uint32 = base + GPIO_PUPDR

    val: uint32 = mmio_read(pupdr_addr)
    # Clear 2 bits for this pin
    val = val & ~(0x03 << (pin * 2))
    # Set new pull
    val = val | ((pull & 0x03) << (pin * 2))
    mmio_write(pupdr_addr, val)

def gpio_set_af(port: uint32, pin: uint32, af: uint32):
    """Set GPIO alternate function.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        af: Alternate function number (0-15)
    """
    if port > 8 or pin > 15:
        return

    base: uint32 = _gpio_port_base(port)

    # AFR is split into AFRL (pins 0-7) and AFRH (pins 8-15)
    if pin < 8:
        afr_addr: uint32 = base + GPIO_AFRL
        shift: uint32 = pin * 4
    else:
        afr_addr: uint32 = base + GPIO_AFRH
        shift: uint32 = (pin - 8) * 4

    val: uint32 = mmio_read(afr_addr)
    # Clear 4 bits for this pin
    val = val & ~(0x0F << shift)
    # Set new AF
    val = val | ((af & 0x0F) << shift)
    mmio_write(afr_addr, val)

# ============================================================================
# GPIO Initialization (Combined Configuration)
# ============================================================================

def gpio_init(port: uint32, pin: uint32, mode: uint32, otype: uint32,
              speed: uint32, pull: uint32):
    """Initialize GPIO pin with full configuration.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        mode: GPIO_MODE_*
        otype: GPIO_OTYPE_*
        speed: GPIO_SPEED_*
        pull: GPIO_PULL_*
    """
    # Enable clock first
    gpio_enable_clock(port)

    # Configure pin
    gpio_set_mode(port, pin, mode)
    gpio_set_output_type(port, pin, otype)
    gpio_set_speed(port, pin, speed)
    gpio_set_pull(port, pin, pull)

def gpio_init_output(port: uint32, pin: uint32):
    """Initialize GPIO pin as push-pull output with medium speed.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
    """
    gpio_init(port, pin, GPIO_MODE_OUTPUT, GPIO_OTYPE_PP,
              GPIO_SPEED_MEDIUM, GPIO_PULL_NONE)

def gpio_init_input(port: uint32, pin: uint32, pull: uint32):
    """Initialize GPIO pin as input.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        pull: GPIO_PULL_NONE, GPIO_PULL_UP, or GPIO_PULL_DOWN
    """
    gpio_enable_clock(port)
    gpio_set_mode(port, pin, GPIO_MODE_INPUT)
    gpio_set_pull(port, pin, pull)

def gpio_init_af(port: uint32, pin: uint32, af: uint32, otype: uint32,
                 speed: uint32, pull: uint32):
    """Initialize GPIO pin for alternate function.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        af: Alternate function number (0-15)
        otype: GPIO_OTYPE_*
        speed: GPIO_SPEED_*
        pull: GPIO_PULL_*
    """
    gpio_init(port, pin, GPIO_MODE_AF, otype, speed, pull)
    gpio_set_af(port, pin, af)

# ============================================================================
# GPIO Read/Write Functions
# ============================================================================

def gpio_read(port: uint32, pin: uint32) -> bool:
    """Read GPIO pin input value.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)

    Returns:
        True if high, False if low
    """
    if port > 8 or pin > 15:
        return False

    base: uint32 = _gpio_port_base(port)
    val: uint32 = mmio_read(base + GPIO_IDR)
    return ((val >> pin) & 1) != 0

def gpio_write(port: uint32, pin: uint32, value: bool):
    """Set GPIO pin output value.

    Uses BSRR for atomic set/reset.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
        value: True for high, False for low
    """
    if port > 8 or pin > 15:
        return

    base: uint32 = _gpio_port_base(port)

    # BSRR: lower 16 bits set, upper 16 bits reset
    if value:
        mmio_write(base + GPIO_BSRR, 1 << pin)        # Set
    else:
        mmio_write(base + GPIO_BSRR, 1 << (pin + 16)) # Reset

def gpio_toggle(port: uint32, pin: uint32):
    """Toggle GPIO pin output.

    Args:
        port: Port number (PORT_A through PORT_I)
        pin: Pin number (0-15)
    """
    if port > 8 or pin > 15:
        return

    base: uint32 = _gpio_port_base(port)
    val: uint32 = mmio_read(base + GPIO_ODR)
    val = val ^ (1 << pin)
    mmio_write(base + GPIO_ODR, val)

# ============================================================================
# Bulk GPIO Operations
# ============================================================================

def gpio_read_port(port: uint32) -> uint32:
    """Read all 16 pins of a GPIO port.

    Args:
        port: Port number (PORT_A through PORT_I)

    Returns:
        16-bit value with pin states
    """
    if port > 8:
        return 0

    base: uint32 = _gpio_port_base(port)
    return mmio_read(base + GPIO_IDR) & 0xFFFF

def gpio_write_port(port: uint32, value: uint32):
    """Write all 16 pins of a GPIO port.

    Args:
        port: Port number (PORT_A through PORT_I)
        value: 16-bit value for pins
    """
    if port > 8:
        return

    base: uint32 = _gpio_port_base(port)
    mmio_write(base + GPIO_ODR, value & 0xFFFF)

def gpio_set_pins(port: uint32, mask: uint32):
    """Set multiple GPIO pins high (atomic).

    Args:
        port: Port number (PORT_A through PORT_I)
        mask: 16-bit mask of pins to set high
    """
    if port > 8:
        return

    base: uint32 = _gpio_port_base(port)
    mmio_write(base + GPIO_BSRR, mask & 0xFFFF)

def gpio_clear_pins(port: uint32, mask: uint32):
    """Clear multiple GPIO pins (atomic).

    Args:
        port: Port number (PORT_A through PORT_I)
        mask: 16-bit mask of pins to set low
    """
    if port > 8:
        return

    base: uint32 = _gpio_port_base(port)
    mmio_write(base + GPIO_BSRR, (mask & 0xFFFF) << 16)

# ============================================================================
# Common STM32F4 Alternate Function Numbers
# ============================================================================
# These are the AF numbers for common peripherals on STM32F4:
#
# AF0:  System (MCO, JTAG, RTC)
# AF1:  TIM1, TIM2
# AF2:  TIM3, TIM4, TIM5
# AF3:  TIM8, TIM9, TIM10, TIM11
# AF4:  I2C1, I2C2, I2C3
# AF5:  SPI1, SPI2
# AF6:  SPI3
# AF7:  USART1, USART2, USART3
# AF8:  UART4, UART5, USART6
# AF9:  CAN1, CAN2, TIM12, TIM13, TIM14
# AF10: USB OTG FS, USB OTG HS
# AF11: ETH
# AF12: FSMC, SDIO, USB OTG HS
# AF13: DCMI
# AF14: -
# AF15: EVENTOUT

AF_SYSTEM: uint32 = 0
AF_TIM1_TIM2: uint32 = 1
AF_TIM3_TIM4_TIM5: uint32 = 2
AF_TIM8_TIM9_TIM10_TIM11: uint32 = 3
AF_I2C: uint32 = 4
AF_SPI1_SPI2: uint32 = 5
AF_SPI3: uint32 = 6
AF_USART1_2_3: uint32 = 7
AF_UART4_5_USART6: uint32 = 8
AF_CAN: uint32 = 9
AF_USB_OTG: uint32 = 10
AF_ETH: uint32 = 11
AF_FSMC_SDIO: uint32 = 12
AF_DCMI: uint32 = 13
