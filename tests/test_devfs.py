# Pynux Device Filesystem Tests
#
# Tests for device registration, reading, and writing.

from lib.io import print_str, print_int, print_newline
from lib.string import strcmp, strlen, atoi
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, assert_lt,
                                   assert_not_null, test_pass, test_fail)
from kernel.devfs import (devfs_init, devfs_register, devfs_read, devfs_write,
                           devfs_find_by_name, devfs_find_by_path,
                           devfs_get_count, devfs_get_path,
                           DEV_GPIO, DEV_TEMP, DEV_ADC, DEV_PWM,
                           DEV_ACCEL, DEV_LIGHT, DEV_SERVO)

# ============================================================================
# Device Registration Tests
# ============================================================================

def test_register_device():
    """Test basic device registration."""
    print_section("Device Registration")

    # Register a test GPIO device
    idx: int32 = devfs_register(DEV_GPIO, 0, 10, "test_gpio0")
    assert_gte(idx, 0, "register GPIO returns valid index")

    # Should be able to find by name
    found: int32 = devfs_find_by_name("test_gpio0")
    assert_eq(found, idx, "find by name returns same index")

def test_register_multiple():
    """Test registering multiple devices."""
    idx1: int32 = devfs_register(DEV_GPIO, 1, 11, "multi_gpio1")
    idx2: int32 = devfs_register(DEV_TEMP, 0, 20, "multi_temp0")
    idx3: int32 = devfs_register(DEV_ADC, 0, 30, "multi_adc0")

    all_valid: bool = (idx1 >= 0 and idx2 >= 0 and idx3 >= 0)
    assert_true(all_valid, "register 3 devices")

    # All should be findable
    f1: int32 = devfs_find_by_name("multi_gpio1")
    f2: int32 = devfs_find_by_name("multi_temp0")
    f3: int32 = devfs_find_by_name("multi_adc0")

    all_found: bool = (f1 >= 0 and f2 >= 0 and f3 >= 0)
    assert_true(all_found, "find all 3 devices")

def test_device_count():
    """Test device count tracking."""
    count_before: int32 = devfs_get_count()

    devfs_register(DEV_LIGHT, 0, 40, "count_light0")

    count_after: int32 = devfs_get_count()
    assert_eq(count_after, count_before + 1, "count increases on register")

# ============================================================================
# GPIO Tests
# ============================================================================

def test_gpio_read_write():
    """Test GPIO read and write."""
    print_section("GPIO Devices")

    idx: int32 = devfs_register(DEV_GPIO, 5, 5, "gpio5")
    if idx < 0:
        test_fail("register GPIO for test")
        return

    # Write value
    result: int32 = devfs_write(idx, "1")
    assert_eq(result, 0, "GPIO write succeeds")

    # Read value back
    value: Ptr[char] = devfs_read(idx)
    assert_not_null(cast[Ptr[void]](value), "GPIO read returns value")

    # Should be "1" or similar
    if value[0] == '1' or value[0] == '0':
        test_pass("GPIO returns valid state")
    else:
        test_fail("GPIO should return 0 or 1")

def test_gpio_toggle():
    """Test GPIO toggle behavior."""
    idx: int32 = devfs_register(DEV_GPIO, 6, 6, "gpio6")
    if idx < 0:
        test_fail("register GPIO for toggle")
        return

    # Set to 1
    devfs_write(idx, "1")
    val1: Ptr[char] = devfs_read(idx)
    is_high: bool = (val1[0] == '1')

    # Set to 0
    devfs_write(idx, "0")
    val2: Ptr[char] = devfs_read(idx)
    is_low: bool = (val2[0] == '0')

    assert_true(is_high and is_low, "GPIO toggles correctly")

# ============================================================================
# Temperature Sensor Tests
# ============================================================================

def test_temp_sensor():
    """Test temperature sensor reading."""
    print_section("Temperature Sensors")

    idx: int32 = devfs_register(DEV_TEMP, 0, 25, "temp0")
    if idx < 0:
        test_fail("register temp sensor")
        return

    # Read temperature
    value: Ptr[char] = devfs_read(idx)
    assert_not_null(cast[Ptr[void]](value), "temp read returns value")

    # Temperature should be a reasonable number (not "error")
    if value[0] != 'e':  # Not "error"
        test_pass("temp returns valid reading")

        # Parse and check range (simulated temps are usually 20-30C)
        temp: int32 = atoi(value)
        if temp >= -40 and temp <= 150:
            test_pass("temp in reasonable range")
        else:
            test_fail("temp out of range")
    else:
        test_fail("temp read failed")

def test_multiple_temp_sensors():
    """Test multiple temperature sensors."""
    idx0: int32 = devfs_register(DEV_TEMP, 1, 26, "temp1")
    idx1: int32 = devfs_register(DEV_TEMP, 2, 27, "temp2")

    all_valid: bool = (idx0 >= 0 and idx1 >= 0)
    assert_true(all_valid, "register 2 temp sensors")

    # Both should return readings
    val0: Ptr[char] = devfs_read(idx0)
    val1: Ptr[char] = devfs_read(idx1)

    both_ok: bool = (val0[0] != 'e' and val1[0] != 'e')
    assert_true(both_ok, "both temps readable")

# ============================================================================
# ADC Tests
# ============================================================================

def test_adc_read():
    """Test ADC reading."""
    print_section("ADC Devices")

    idx: int32 = devfs_register(DEV_ADC, 0, 26, "adc0")
    if idx < 0:
        test_fail("register ADC")
        return

    value: Ptr[char] = devfs_read(idx)
    assert_not_null(cast[Ptr[void]](value), "ADC read returns value")

    # ADC should return number in range 0-4095 (12-bit)
    adc_val: int32 = atoi(value)
    if adc_val >= 0 and adc_val <= 4095:
        test_pass("ADC value in 12-bit range")
    else:
        print_str("  (got: ")
        print_int(adc_val)
        print_str(")")
        print_newline()
        test_fail("ADC value out of range")

def test_adc_multiple_reads():
    """Test ADC returns consistent-ish values."""
    idx: int32 = devfs_register(DEV_ADC, 1, 27, "adc1")
    if idx < 0:
        test_fail("register ADC for multi-read")
        return

    # Read multiple times
    readings: Array[5, int32]
    i: int32 = 0
    while i < 5:
        value: Ptr[char] = devfs_read(idx)
        readings[i] = atoi(value)
        i = i + 1

    # All readings should be in valid range
    all_valid: bool = True
    i = 0
    while i < 5:
        if readings[i] < 0 or readings[i] > 4095:
            all_valid = False
        i = i + 1

    assert_true(all_valid, "5 ADC readings all valid")

# ============================================================================
# PWM Tests
# ============================================================================

def test_pwm_write():
    """Test PWM write."""
    print_section("PWM Devices")

    idx: int32 = devfs_register(DEV_PWM, 0, 12, "pwm0")
    if idx < 0:
        test_fail("register PWM")
        return

    # Write duty cycle (0-255)
    result: int32 = devfs_write(idx, "128")
    assert_eq(result, 0, "PWM write 50% succeeds")

    # Read back
    value: Ptr[char] = devfs_read(idx)
    duty: int32 = atoi(value)
    assert_eq(duty, 128, "PWM reads back 128")

def test_pwm_limits():
    """Test PWM clamping."""
    idx: int32 = devfs_register(DEV_PWM, 1, 13, "pwm1")
    if idx < 0:
        test_fail("register PWM for limits")
        return

    # Write 0
    devfs_write(idx, "0")
    val: Ptr[char] = devfs_read(idx)
    assert_eq(atoi(val), 0, "PWM 0 works")

    # Write 255
    devfs_write(idx, "255")
    val = devfs_read(idx)
    assert_eq(atoi(val), 255, "PWM 255 works")

    # Write over max - should clamp
    devfs_write(idx, "300")
    val = devfs_read(idx)
    assert_eq(atoi(val), 255, "PWM clamps to 255")

# ============================================================================
# Servo Tests
# ============================================================================

def test_servo_write():
    """Test servo control."""
    print_section("Servo Devices")

    idx: int32 = devfs_register(DEV_SERVO, 0, 15, "servo0")
    if idx < 0:
        test_fail("register servo")
        return

    # Write angle (0-180)
    result: int32 = devfs_write(idx, "90")
    assert_eq(result, 0, "servo write 90 degrees")

    # Read back
    value: Ptr[char] = devfs_read(idx)
    angle: int32 = atoi(value)
    assert_eq(angle, 90, "servo reads back 90")

# ============================================================================
# Device Path Tests
# ============================================================================

def test_device_paths():
    """Test device path functions."""
    print_section("Device Paths")

    idx: int32 = devfs_register(DEV_GPIO, 7, 7, "path_gpio")
    if idx < 0:
        test_fail("register for path test")
        return

    # Get path
    path: Ptr[char] = devfs_get_path(idx)
    assert_not_null(cast[Ptr[void]](path), "get_path returns path")

    # Find by path
    found: int32 = devfs_find_by_path(path)
    if found >= 0:
        test_pass("find_by_path works")
    else:
        test_fail("find_by_path should find device")

def test_invalid_device():
    """Test invalid device access."""
    # Read from invalid index
    value: Ptr[char] = devfs_read(-1)
    assert_not_null(cast[Ptr[void]](value), "read -1 returns error string")

    # Should contain "error"
    if value[0] == 'e':
        test_pass("invalid read returns error")
    else:
        test_fail("invalid should return error")

    # Find non-existent device
    idx: int32 = devfs_find_by_name("nonexistent_device")
    assert_eq(idx, -1, "find nonexistent returns -1")

# ============================================================================
# Intuitive API Tests
# ============================================================================

def test_intuitive_devfs_api():
    """Test that devfs API is intuitive."""
    print_section("Intuitive Device API")

    # register returns index >= 0 on success
    idx: int32 = devfs_register(DEV_GPIO, 8, 8, "intuitive_gpio")
    if idx >= 0:
        test_pass("devfs_register returns valid index")
    else:
        test_fail("devfs_register should return >= 0")
        return

    # write returns 0 on success
    result: int32 = devfs_write(idx, "1")
    if result == 0:
        test_pass("devfs_write returns 0 on success")
    else:
        test_fail("devfs_write should return 0")

    # read returns non-null string
    value: Ptr[char] = devfs_read(idx)
    if value != Ptr[char](0):
        test_pass("devfs_read returns string")
    else:
        test_fail("devfs_read should return string")

    # find_by_name returns index or -1
    found: int32 = devfs_find_by_name("intuitive_gpio")
    if found == idx:
        test_pass("find_by_name returns correct index")
    else:
        test_fail("find_by_name should return index")

    # find nonexistent returns -1
    not_found: int32 = devfs_find_by_name("not_a_device")
    if not_found == -1:
        test_pass("find_by_name returns -1 for missing")
    else:
        test_fail("missing device should return -1")

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    print_str("\n=== Pynux Device Filesystem Tests ===\n")

    # Initialize devfs
    devfs_init()

    test_register_device()
    test_register_multiple()
    test_device_count()

    test_gpio_read_write()
    test_gpio_toggle()

    test_temp_sensor()
    test_multiple_temp_sensors()

    test_adc_read()
    test_adc_multiple_reads()

    test_pwm_write()
    test_pwm_limits()

    test_servo_write()

    test_device_paths()
    test_invalid_device()

    test_intuitive_devfs_api()

    return print_results()
