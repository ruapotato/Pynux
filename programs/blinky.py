# Minimal Blinky Test Program
#
# First program to run on real hardware for validation.
# Toggles LED at 1Hz and prints to UART.
#
# LED Pins:
#   RP2040 (Pico):  GPIO25 (onboard LED)
#   STM32F4:        PC13 (Blue Pill) or PA5 (Nucleo)
#   QEMU:           Just UART output

from kernel.timer import timer_get_ticks, timer_delay_ms
from lib.io import console_puts, console_print_int
from lib.peripherals import mmio_read, mmio_write, TARGET_QEMU, TARGET_RP2040, TARGET_STM32F4

# ============================================================================
# Target-specific GPIO Configuration
# ============================================================================

# RP2040 GPIO registers
RP2040_SIO_BASE: uint32 = 0xD0000000
RP2040_SIO_GPIO_OUT_XOR: uint32 = 0x01C
RP2040_SIO_GPIO_OE_SET: uint32 = 0x024
RP2040_IO_BANK0_BASE: uint32 = 0x40014000
RP2040_LED_PIN: uint32 = 25

# STM32F4 GPIO registers
STM32_GPIOC_BASE: uint32 = 0x40020800
STM32_GPIOA_BASE: uint32 = 0x40020000
STM32_RCC_BASE: uint32 = 0x40023800
STM32_RCC_AHB1ENR: uint32 = 0x30
STM32_GPIO_MODER: uint32 = 0x00
STM32_GPIO_ODR: uint32 = 0x14
STM32_LED_PIN: uint32 = 13  # PC13 for Blue Pill

# ============================================================================
# LED Initialization
# ============================================================================

def led_init_rp2040():
    """Initialize GPIO25 as output for RP2040."""
    # Set GPIO25 function to SIO
    ctrl_addr: uint32 = RP2040_IO_BANK0_BASE + 4 + (RP2040_LED_PIN * 8)
    mmio_write(ctrl_addr, 5)  # Function 5 = SIO

    # Enable output
    mmio_write(RP2040_SIO_BASE + RP2040_SIO_GPIO_OE_SET, 1 << RP2040_LED_PIN)

def led_init_stm32f4():
    """Initialize PC13 as output for STM32F4."""
    # Enable GPIOC clock
    rcc_ahb1enr: uint32 = STM32_RCC_BASE + STM32_RCC_AHB1ENR
    val: uint32 = mmio_read(rcc_ahb1enr)
    mmio_write(rcc_ahb1enr, val | (1 << 2))  # GPIOCEN

    # Set PC13 as output (MODER bits [27:26] = 01)
    moder_addr: uint32 = STM32_GPIOC_BASE + STM32_GPIO_MODER
    val = mmio_read(moder_addr)
    val = val & ~(3 << (STM32_LED_PIN * 2))  # Clear mode bits
    val = val | (1 << (STM32_LED_PIN * 2))   # Set as output
    mmio_write(moder_addr, val)

def led_init(target: uint32):
    """Initialize LED based on target."""
    if target == TARGET_RP2040:
        led_init_rp2040()
    elif target == TARGET_STM32F4:
        led_init_stm32f4()
    # QEMU: no GPIO, just UART

# ============================================================================
# LED Toggle
# ============================================================================

def led_toggle_rp2040():
    """Toggle GPIO25 on RP2040."""
    mmio_write(RP2040_SIO_BASE + RP2040_SIO_GPIO_OUT_XOR, 1 << RP2040_LED_PIN)

def led_toggle_stm32f4():
    """Toggle PC13 on STM32F4."""
    odr_addr: uint32 = STM32_GPIOC_BASE + STM32_GPIO_ODR
    val: uint32 = mmio_read(odr_addr)
    mmio_write(odr_addr, val ^ (1 << STM32_LED_PIN))

def led_toggle(target: uint32):
    """Toggle LED based on target."""
    if target == TARGET_RP2040:
        led_toggle_rp2040()
    elif target == TARGET_STM32F4:
        led_toggle_stm32f4()

# ============================================================================
# Main Blinky Program
# ============================================================================

_blinky_target: uint32 = 0
_blinky_count: uint32 = 0
_last_toggle: int32 = 0

def blinky_init(target: uint32):
    """Initialize blinky with target platform."""
    global _blinky_target, _blinky_count, _last_toggle
    _blinky_target = target
    _blinky_count = 0
    _last_toggle = timer_get_ticks()

    led_init(target)

    console_puts("Blinky started on ")
    if target == TARGET_QEMU:
        console_puts("QEMU")
    elif target == TARGET_RP2040:
        console_puts("RP2040")
    elif target == TARGET_STM32F4:
        console_puts("STM32F4")
    console_puts("\n")

def blinky_tick():
    """Called from main loop - toggle LED every 500ms."""
    global _blinky_count, _last_toggle

    now: int32 = timer_get_ticks()
    if now - _last_toggle >= 500:
        _last_toggle = now
        _blinky_count = _blinky_count + 1

        led_toggle(_blinky_target)

        # Print status every 2 seconds (4 toggles)
        if (_blinky_count & 3) == 0:
            console_puts("Blink #")
            console_print_int(cast[int32](_blinky_count / 2))
            console_puts(" at ")
            console_print_int(now / 1000)
            console_puts("s\n")

# ============================================================================
# Standalone Test Entry Point
# ============================================================================

def blinky_main(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    """Standalone blinky entry point."""
    blinky_init(TARGET_QEMU)
    console_puts("Running blinky loop...\n")
    while True:
        blinky_tick()
    return 0
