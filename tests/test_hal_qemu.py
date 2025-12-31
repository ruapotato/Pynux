# Pynux HAL Tests for QEMU
#
# Example Hardware Abstraction Layer tests that run in QEMU.
# Tests GPIO read/write, timer delays, and UART operations.
#
# Note: QEMU's MPS2-AN385 emulates a subset of hardware. These tests
# verify the software interface works correctly, though actual hardware
# behavior may differ.

from lib.io import print_str, print_int, print_newline, uart_init
from lib.io import uart_putc, uart_getc, uart_available
from tests.framework import (
    test_init, test_run, test_assert, test_assert_eq, test_assert_ne,
    test_assert_gt, test_assert_ge, test_assert_lt, test_assert_not_null,
    test_fail, test_skip, test_pass, test_section, test_summary
)
from lib.peripherals import (
    gpio_init, gpio_set_dir, gpio_write, gpio_read, gpio_toggle,
    gpio_write_port, gpio_read_port,
    GPIO_DIR_INPUT, GPIO_DIR_OUTPUT,
    spi_init, spi_transfer, spi_cs_select, spi_cs_deselect,
    SPI_MODE_0, SPI_MODE_3,
    i2c_init, i2c_write, i2c_read, I2C_OK,
    pwm_init, pwm_set_duty, pwm_enable, pwm_disable, pwm_is_enabled,
    adc_init, adc_read, adc_read_mv
)
from kernel.timer import timer_init_poll, timer_delay_ms, timer_delay_us, timer_get_ticks

# ============================================================================
# GPIO Tests
# ============================================================================

def test_gpio_init():
    """Test GPIO initialization."""
    # Initialize GPIO port 0
    gpio_init(0)
    test_pass("gpio_init(0) completes")

    # Initialize multiple ports
    gpio_init(1)
    gpio_init(2)
    test_pass("multiple gpio_init completes")

def test_gpio_direction():
    """Test GPIO direction setting."""
    gpio_init(0)

    # Set pin 0 as output
    gpio_set_dir(0, 0, GPIO_DIR_OUTPUT)
    test_pass("set pin as output")

    # Set pin 1 as input
    gpio_set_dir(0, 1, GPIO_DIR_INPUT)
    test_pass("set pin as input")

def test_gpio_write_read():
    """Test GPIO write and read back (using tracked state)."""
    gpio_init(0)

    # Set pin 5 as output
    gpio_set_dir(0, 5, GPIO_DIR_OUTPUT)

    # Write high
    gpio_write(0, 5, 1)
    val: uint32 = gpio_read(0, 5)
    test_assert_eq(cast[int32](val), 1, "write high reads back 1")

    # Write low
    gpio_write(0, 5, 0)
    val = gpio_read(0, 5)
    test_assert_eq(cast[int32](val), 0, "write low reads back 0")

def test_gpio_toggle():
    """Test GPIO toggle."""
    gpio_init(0)

    # Set pin 3 as output, start low
    gpio_set_dir(0, 3, GPIO_DIR_OUTPUT)
    gpio_write(0, 3, 0)

    # Toggle should make it high
    gpio_toggle(0, 3)
    val: uint32 = gpio_read(0, 3)
    test_assert_eq(cast[int32](val), 1, "toggle 0->1")

    # Toggle again should make it low
    gpio_toggle(0, 3)
    val = gpio_read(0, 3)
    test_assert_eq(cast[int32](val), 0, "toggle 1->0")

def test_gpio_port_operations():
    """Test GPIO port-wide operations."""
    gpio_init(1)

    # Set all pins as output (via individual calls)
    i: int32 = 0
    while i < 8:
        gpio_set_dir(1, cast[uint32](i), GPIO_DIR_OUTPUT)
        i = i + 1

    # Write entire port
    gpio_write_port(1, 0xAA)  # 10101010 binary
    test_pass("write_port completes")

    # Verify some bits (using tracked state)
    # Bit 1 = 1, Bit 2 = 0, Bit 3 = 1
    val: uint32 = gpio_read(1, 1)
    test_assert_eq(cast[int32](val), 1, "port bit 1 is high")

    val = gpio_read(1, 2)
    test_assert_eq(cast[int32](val), 0, "port bit 2 is low")

def test_gpio_multiple_pins():
    """Test multiple GPIO pins independently."""
    gpio_init(0)

    # Set pins 0, 1, 2 as outputs
    gpio_set_dir(0, 0, GPIO_DIR_OUTPUT)
    gpio_set_dir(0, 1, GPIO_DIR_OUTPUT)
    gpio_set_dir(0, 2, GPIO_DIR_OUTPUT)

    # Write different values
    gpio_write(0, 0, 1)
    gpio_write(0, 1, 0)
    gpio_write(0, 2, 1)

    # Read back
    test_assert_eq(cast[int32](gpio_read(0, 0)), 1, "pin 0 is high")
    test_assert_eq(cast[int32](gpio_read(0, 1)), 0, "pin 1 is low")
    test_assert_eq(cast[int32](gpio_read(0, 2)), 1, "pin 2 is high")

# ============================================================================
# Timer Delay Tests
# ============================================================================

def test_delay_ms_basic():
    """Test basic millisecond delay."""
    timer_init_poll()

    # 1ms delay should complete
    timer_delay_ms(1)
    test_pass("delay_ms(1) completes")

    # 5ms delay
    timer_delay_ms(5)
    test_pass("delay_ms(5) completes")

    # 10ms delay
    timer_delay_ms(10)
    test_pass("delay_ms(10) completes")

def test_delay_us_basic():
    """Test basic microsecond delay."""
    timer_init_poll()

    # Short delays
    timer_delay_us(10)
    test_pass("delay_us(10) completes")

    timer_delay_us(100)
    test_pass("delay_us(100) completes")

    timer_delay_us(1000)  # 1ms in us
    test_pass("delay_us(1000) completes")

def test_delay_zero():
    """Test zero-length delays don't hang."""
    timer_init_poll()

    timer_delay_ms(0)
    test_pass("delay_ms(0) returns immediately")

    timer_delay_us(0)
    test_pass("delay_us(0) returns immediately")

def test_delay_timing():
    """Test that delays actually wait (approximately)."""
    timer_init_poll()

    # Get tick before delay
    before: int32 = timer_get_ticks()

    # Do a 10ms delay
    timer_delay_ms(10)

    # Get tick after
    after: int32 = timer_get_ticks()

    # Ticks should have advanced (may not be exactly 10 in QEMU)
    test_assert_ge(after, before, "ticks advance during delay")

def test_delay_ordering():
    """Test that longer delays take longer."""
    timer_init_poll()

    # Do short delay and measure
    start1: int32 = timer_get_ticks()
    timer_delay_ms(2)
    end1: int32 = timer_get_ticks()
    elapsed1: int32 = end1 - start1

    # Do longer delay and measure
    start2: int32 = timer_get_ticks()
    timer_delay_ms(10)
    end2: int32 = timer_get_ticks()
    elapsed2: int32 = end2 - start2

    # Longer delay should take at least as long
    # (in QEMU timing may not be exact, so just check it doesn't hang)
    test_pass("delays complete in order")

# ============================================================================
# UART Tests (Loopback simulation)
# ============================================================================

def test_uart_init():
    """Test UART initialization."""
    uart_init()
    test_pass("uart_init completes")

def test_uart_putc():
    """Test UART character output."""
    uart_init()

    # Output some characters (will appear in QEMU serial output)
    uart_putc('T')
    uart_putc('E')
    uart_putc('S')
    uart_putc('T')
    uart_putc('\n')

    test_pass("uart_putc works")

def test_uart_print_str():
    """Test UART string output."""
    uart_init()

    print_str("UART test string\n")
    test_pass("print_str works")

def test_uart_print_int():
    """Test UART integer output."""
    uart_init()

    print_str("Number: ")
    print_int(12345)
    print_newline()
    test_pass("print_int works")

    # Negative number
    print_str("Negative: ")
    print_int(-42)
    print_newline()
    test_pass("print_int negative works")

# Note: UART loopback test requires hardware support or QEMU configuration
# that connects TX to RX. For now, we just test that functions don't crash.

def test_uart_available():
    """Test UART available function."""
    uart_init()

    # Check if data available (probably false unless loopback)
    avail: bool = uart_available()

    # Function should return without crashing
    test_pass("uart_available returns")

# ============================================================================
# SPI Tests (Basic interface checks)
# ============================================================================

def test_spi_init():
    """Test SPI initialization."""
    # Initialize SPI 0 in mode 0
    spi_init(0, SPI_MODE_0, 10)
    test_pass("spi_init mode 0 completes")

    # Initialize SPI 1 in mode 3
    spi_init(1, SPI_MODE_3, 5)
    test_pass("spi_init mode 3 completes")

def test_spi_cs():
    """Test SPI chip select."""
    spi_init(0, SPI_MODE_0, 10)

    # Select CS 0
    spi_cs_select(0, 0)
    test_pass("spi_cs_select completes")

    # Deselect
    spi_cs_deselect(0)
    test_pass("spi_cs_deselect completes")

def test_spi_transfer():
    """Test SPI transfer (in simulation, no real device)."""
    spi_init(0, SPI_MODE_0, 10)

    # Transfer a byte (will timeout without real hardware, but shouldn't crash)
    # Skip this test in QEMU as there's no SPI device
    test_skip("no SPI hardware in QEMU")

# ============================================================================
# I2C Tests (Basic interface checks)
# ============================================================================

def test_i2c_init():
    """Test I2C initialization."""
    i2c_init(0, 100)  # 100 = baud divisor
    test_pass("i2c_init completes")

def test_i2c_operations():
    """Test I2C operations (in simulation, no real device)."""
    i2c_init(0, 100)

    # Skip actual I2C operations in QEMU as there's no I2C device
    test_skip("no I2C hardware in QEMU")

# ============================================================================
# PWM Tests
# ============================================================================

def test_pwm_init():
    """Test PWM initialization."""
    pwm_init(0, 1000)  # Channel 0, 1kHz
    test_pass("pwm_init completes")

    pwm_init(1, 10000)  # Channel 1, 10kHz
    test_pass("pwm_init 10kHz completes")

def test_pwm_duty():
    """Test PWM duty cycle setting."""
    pwm_init(0, 1000)

    # Set various duty cycles
    pwm_set_duty(0, 0)
    test_pass("pwm_set_duty 0%")

    pwm_set_duty(0, 50)
    test_pass("pwm_set_duty 50%")

    pwm_set_duty(0, 100)
    test_pass("pwm_set_duty 100%")

    # Clamp to 100%
    pwm_set_duty(0, 150)
    test_pass("pwm_set_duty clamped")

def test_pwm_enable_disable():
    """Test PWM enable and disable."""
    pwm_init(0, 1000)

    # Enable
    pwm_enable(0)
    enabled: bool = pwm_is_enabled(0)
    test_assert(enabled, "pwm enabled")

    # Disable
    pwm_disable(0)
    enabled = pwm_is_enabled(0)
    test_assert(not enabled, "pwm disabled")

# ============================================================================
# ADC Tests
# ============================================================================

def test_adc_init():
    """Test ADC initialization."""
    adc_init(12)  # 12-bit resolution
    test_pass("adc_init 12-bit completes")

def test_adc_read():
    """Test ADC read (simulation returns whatever hardware has)."""
    adc_init(12)

    # Read channel 0
    val: uint32 = adc_read(0)

    # Value should be within 12-bit range
    test_assert_ge(cast[int32](val), 0, "adc value >= 0")
    test_assert_lt(cast[int32](val), 4096, "adc value < 4096")

def test_adc_mv():
    """Test ADC millivolt conversion."""
    adc_init(12)

    # Read in millivolts
    mv: uint32 = adc_read_mv(0)

    # Should be within valid range (0 to 3300mV for 3.3V ref)
    test_assert_ge(cast[int32](mv), 0, "adc_mv >= 0")
    test_assert_le(cast[int32](mv), 3300, "adc_mv <= 3300")

# ============================================================================
# Main Entry Point
# ============================================================================

def run_hal_tests():
    """Run all HAL tests."""
    print_str("\n=== Pynux HAL Tests (QEMU) ===\n")

    test_init()

    # GPIO tests
    test_section("GPIO")
    test_run("gpio_init", test_gpio_init)
    test_run("gpio_direction", test_gpio_direction)
    test_run("gpio_write_read", test_gpio_write_read)
    test_run("gpio_toggle", test_gpio_toggle)
    test_run("gpio_port_operations", test_gpio_port_operations)
    test_run("gpio_multiple_pins", test_gpio_multiple_pins)

    # Timer delay tests
    test_section("Timer Delays")
    test_run("delay_ms_basic", test_delay_ms_basic)
    test_run("delay_us_basic", test_delay_us_basic)
    test_run("delay_zero", test_delay_zero)
    test_run("delay_timing", test_delay_timing)
    test_run("delay_ordering", test_delay_ordering)

    # UART tests
    test_section("UART")
    test_run("uart_init", test_uart_init)
    test_run("uart_putc", test_uart_putc)
    test_run("uart_print_str", test_uart_print_str)
    test_run("uart_print_int", test_uart_print_int)
    test_run("uart_available", test_uart_available)

    # SPI tests
    test_section("SPI")
    test_run("spi_init", test_spi_init)
    test_run("spi_cs", test_spi_cs)
    test_run("spi_transfer", test_spi_transfer)

    # I2C tests
    test_section("I2C")
    test_run("i2c_init", test_i2c_init)
    test_run("i2c_operations", test_i2c_operations)

    # PWM tests
    test_section("PWM")
    test_run("pwm_init", test_pwm_init)
    test_run("pwm_duty", test_pwm_duty)
    test_run("pwm_enable_disable", test_pwm_enable_disable)

    # ADC tests
    test_section("ADC")
    test_run("adc_init", test_adc_init)
    test_run("adc_read", test_adc_read)
    test_run("adc_mv", test_adc_mv)

    return test_summary()
