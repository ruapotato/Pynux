# Pynux Hardware Drivers Test
#
# Tests for sensors, display, and motors libraries.
# Run in QEMU emulator to verify simulation behavior.

from lib.io import print_str, print_int, uart_init
from lib.sensors import sensors_seed, sensors_enable_noise, sensors_init_all
from lib.sensors import temp_init, temp_read, temp_set_base, temp_to_fahrenheit, temp_get_raw
from lib.sensors import accel_init, accel_read_x, accel_read_y, accel_read_z, accel_set_base
from lib.sensors import light_init, light_read, light_set_base, light_to_lux
from lib.sensors import humid_init, humid_read, humid_read_percent, humid_set_base
from lib.sensors import press_init, press_read, press_read_hpa, press_to_altitude, press_set_base
from lib.display import display_set_mode, DISPLAY_MODE_CONSOLE
from lib.display import lcd_init, lcd_clear, lcd_set_cursor, lcd_print_str, lcd_print_int
from lib.display import oled_init, oled_clear, oled_set_pixel, oled_draw_line, oled_draw_rect
from lib.display import oled_draw_string, oled_get_pixel, oled_update
from lib.display import seg7_init, seg7_set_number, seg7_set_hex, seg7_clear
from lib.motors import motor_set_debug
from lib.motors import servo_init, servo_set_angle, servo_get_angle, servo_get_pulse, servo_is_moving
from lib.motors import stepper_init, stepper_step, stepper_steps, stepper_get_position
from lib.motors import STEPPER_MODE_FULL, STEPPER_MODE_HALF, stepper_set_mode
from lib.motors import dc_init, dc_set_speed, dc_get_speed, dc_brake, dc_coast, dc_is_running
from lib.math import abs_int

# ============================================================================
# Test Helpers
# ============================================================================

_tests_passed: int32 = 0
_tests_failed: int32 = 0

def test_pass(name: Ptr[char]):
    global _tests_passed
    print_str("  [PASS] ")
    print_str(name)
    print_str("\n")
    _tests_passed = _tests_passed + 1

def test_fail(name: Ptr[char], expected: int32, got: int32):
    global _tests_failed
    print_str("  [FAIL] ")
    print_str(name)
    print_str(" - expected ")
    print_int(expected)
    print_str(", got ")
    print_int(got)
    print_str("\n")
    _tests_failed = _tests_failed + 1

def test_bool_fail(name: Ptr[char], expected: bool):
    global _tests_failed
    print_str("  [FAIL] ")
    print_str(name)
    print_str(" - expected ")
    if expected:
        print_str("true")
    else:
        print_str("false")
    print_str("\n")
    _tests_failed = _tests_failed + 1

# ============================================================================
# Sensor Tests
# ============================================================================

def test_sensors():
    print_str("\n=== Sensor Tests ===\n")

    # Disable noise for deterministic testing
    sensors_seed(42)
    sensors_enable_noise(False)

    # Temperature sensor
    temp_init()
    temp_set_base(2500)  # 25.00 C
    reading: int32 = temp_read()
    # Without noise, should be close to 2500 (may have resolution rounding)
    if abs_int(reading - 2500) < 10:
        test_pass("temp_read base value")
    else:
        test_fail("temp_read base value", 2500, reading)

    # Temperature conversion
    fahrenheit: int32 = temp_to_fahrenheit(2500)  # 25C = 77F
    if abs_int(fahrenheit - 7700) < 10:
        test_pass("temp_to_fahrenheit")
    else:
        test_fail("temp_to_fahrenheit", 7700, fahrenheit)

    # Raw value should be in 12-bit range
    raw: int32 = temp_get_raw()
    if raw >= 0 and raw <= 4095:
        test_pass("temp_get_raw range")
    else:
        test_fail("temp_get_raw range (0-4095)", 2000, raw)

    # Accelerometer
    accel_init()
    accel_set_base(0, 0, 1000)  # At rest: 0, 0, 1g
    x: int32 = accel_read_x()
    y: int32 = accel_read_y()
    z: int32 = accel_read_z()
    if abs_int(x) < 50:
        test_pass("accel_read_x near zero")
    else:
        test_fail("accel_read_x near zero", 0, x)
    if abs_int(z - 1000) < 50:
        test_pass("accel_read_z gravity")
    else:
        test_fail("accel_read_z gravity", 1000, z)

    # Light sensor
    light_init()
    light_set_base(512)
    light_val: int32 = light_read()
    if abs_int(light_val - 512) < 20:
        test_pass("light_read base value")
    else:
        test_fail("light_read base value", 512, light_val)

    lux: int32 = light_to_lux(512)
    if lux >= 50 and lux <= 150:
        test_pass("light_to_lux conversion")
    else:
        test_fail("light_to_lux conversion", 100, lux)

    # Humidity sensor
    humid_init()
    humid_set_base(650)  # 65.0% RH
    rh: int32 = humid_read()
    if abs_int(rh - 650) < 30:
        test_pass("humid_read base value")
    else:
        test_fail("humid_read base value", 650, rh)

    rh_pct: int32 = humid_read_percent()
    if rh_pct >= 60 and rh_pct <= 70:
        test_pass("humid_read_percent")
    else:
        test_fail("humid_read_percent", 65, rh_pct)

    # Pressure sensor
    press_init()
    press_set_base(101325)  # 1 atm
    pressure: int32 = press_read()
    if abs_int(pressure - 101325) < 100:
        test_pass("press_read base value")
    else:
        test_fail("press_read base value", 101325, pressure)

    altitude: int32 = press_to_altitude(101325)
    if abs_int(altitude) < 50:  # Should be near 0 at sea level
        test_pass("press_to_altitude sea level")
    else:
        test_fail("press_to_altitude sea level", 0, altitude)

    # High altitude test
    altitude = press_to_altitude(90000)  # ~1100m
    if altitude > 800 and altitude < 1200:
        test_pass("press_to_altitude high")
    else:
        test_fail("press_to_altitude high", 900, altitude)

# ============================================================================
# Display Tests
# ============================================================================

def test_displays():
    print_str("\n=== Display Tests ===\n")

    # Use console mode for testing
    display_set_mode(DISPLAY_MODE_CONSOLE)

    # LCD test
    lcd_init(16, 2)
    lcd_clear()
    lcd_set_cursor(0, 0)
    lcd_print_str("Hello")
    lcd_set_cursor(0, 1)
    lcd_print_int(12345)
    test_pass("lcd_init and print")

    # OLED test
    oled_init()
    oled_clear()

    # Test pixel set/get
    oled_set_pixel(10, 10, True)
    if oled_get_pixel(10, 10):
        test_pass("oled pixel set/get on")
    else:
        test_bool_fail("oled pixel set/get on", True)

    if not oled_get_pixel(11, 11):
        test_pass("oled pixel get unset")
    else:
        test_bool_fail("oled pixel get unset", False)

    # Test drawing primitives
    oled_draw_line(0, 0, 20, 20, True)
    if oled_get_pixel(10, 10):
        test_pass("oled draw_line")
    else:
        test_bool_fail("oled draw_line", True)

    oled_clear()
    oled_draw_rect(5, 5, 20, 10, True)
    # Top edge should be set
    if oled_get_pixel(10, 5):
        test_pass("oled draw_rect top edge")
    else:
        test_bool_fail("oled draw_rect top edge", True)
    # Inside should be clear
    if not oled_get_pixel(10, 10):
        test_pass("oled draw_rect inside clear")
    else:
        test_bool_fail("oled draw_rect inside clear", False)

    oled_draw_string(0, 0, "TEST", True)
    test_pass("oled draw_string")

    oled_update()

    # 7-segment test
    seg7_init(4)
    seg7_set_number(1234)
    test_pass("seg7 set_number")

    seg7_set_hex(0xABCD)
    test_pass("seg7 set_hex")

    seg7_clear()
    test_pass("seg7 clear")

# ============================================================================
# Motor Tests
# ============================================================================

def test_motors():
    print_str("\n=== Motor Tests ===\n")

    # Enable debug for visual verification
    motor_set_debug(True)

    # Servo test
    servo_init(0)
    servo_set_angle(0, 45)
    angle: int32 = servo_get_angle(0)
    if angle == 45:
        test_pass("servo set/get angle")
    else:
        test_fail("servo set/get angle", 45, angle)

    pulse: int32 = servo_get_pulse(0)
    # 45 degrees should be about 1250us (1000 + 250)
    if pulse > 1200 and pulse < 1300:
        test_pass("servo get_pulse")
    else:
        test_fail("servo get_pulse", 1250, pulse)

    # Stepper test
    stepper_init(0, 200)  # 200 steps per rev (1.8 deg motor)
    stepper_steps(0, 50)
    pos: int32 = stepper_get_position(0)
    if pos == 50:
        test_pass("stepper steps and position")
    else:
        test_fail("stepper steps and position", 50, pos)

    # Reverse direction
    stepper_steps(0, -25)
    pos = stepper_get_position(0)
    if pos == 25:
        test_pass("stepper reverse")
    else:
        test_fail("stepper reverse", 25, pos)

    # DC motor test
    dc_init(0)
    dc_set_speed(0, 75)
    speed: int32 = dc_get_speed(0)
    if speed == 75:
        test_pass("dc set/get speed")
    else:
        test_fail("dc set/get speed", 75, speed)

    if dc_is_running(0):
        test_pass("dc is_running true")
    else:
        test_bool_fail("dc is_running true", True)

    dc_brake(0)
    speed = dc_get_speed(0)
    if speed == 0:
        test_pass("dc brake stops motor")
    else:
        test_fail("dc brake stops motor", 0, speed)

    if not dc_is_running(0):
        test_pass("dc is_running after brake")
    else:
        test_bool_fail("dc is_running after brake", False)

    # Test negative speed (reverse)
    dc_set_speed(0, -50)
    speed = dc_get_speed(0)
    if speed == -50:
        test_pass("dc reverse speed")
    else:
        test_fail("dc reverse speed", -50, speed)

    dc_coast(0)
    test_pass("dc coast")

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Pynux Hardware Drivers Test ===\n")

    test_sensors()
    test_displays()
    test_motors()

    # Summary
    print_str("\n=== Results ===\n")
    print_str("Passed: ")
    print_int(_tests_passed)
    print_str("\nFailed: ")
    print_int(_tests_failed)
    print_str("\n")

    if _tests_failed == 0:
        print_str("\nALL TESTS PASSED!\n")
    else:
        print_str("\nSOME TESTS FAILED!\n")

    return _tests_failed
