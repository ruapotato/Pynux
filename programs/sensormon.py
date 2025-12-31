# Sensor Monitor Demo
#
# Real-time display of all sensor readings.
# Demonstrates the sensors library in action.

from lib.io import print_str, print_int, print_newline, uart_init
from lib.sensors import sensors_seed, sensors_enable_noise, sensors_init_all
from lib.sensors import temp_read, temp_to_fahrenheit
from lib.sensors import accel_read_x, accel_read_y, accel_read_z
from lib.sensors import light_read, light_to_lux
from lib.sensors import humid_read, humid_read_percent
from lib.sensors import press_read, press_to_altitude
from lib.math import abs_int

def smon_divider():
    print_str("----------------------------------------\n")

def print_temp():
    temp_c: int32 = temp_read()
    temp_f: int32 = temp_to_fahrenheit(temp_c)

    print_str("  Temperature: ")
    print_int(temp_c / 100)
    print_str(".")
    t_frac: int32 = abs_int(temp_c % 100)
    if t_frac < 10:
        print_str("0")
    print_int(t_frac)
    print_str(" C  (")
    print_int(temp_f / 100)
    print_str(".")
    f_frac: int32 = abs_int(temp_f % 100)
    if f_frac < 10:
        print_str("0")
    print_int(f_frac)
    print_str(" F)\n")

def print_accel():
    x: int32 = accel_read_x()
    y: int32 = accel_read_y()
    z: int32 = accel_read_z()

    print_str("  Accel X: ")
    print_int(x)
    print_str(" mg\n")
    print_str("  Accel Y: ")
    print_int(y)
    print_str(" mg\n")
    print_str("  Accel Z: ")
    print_int(z)
    print_str(" mg\n")

def print_light():
    raw: int32 = light_read()
    lux: int32 = light_to_lux(raw)

    print_str("  Light: ")
    print_int(raw)
    print_str(" (")
    print_int(lux)
    print_str(" lux)\n")

def print_humidity():
    rh: int32 = humid_read()

    print_str("  Humidity: ")
    print_int(rh / 10)
    print_str(".")
    print_int(rh % 10)
    print_str(" %RH\n")

def print_pressure():
    pa: int32 = press_read()
    alt: int32 = press_to_altitude(pa)

    print_str("  Pressure: ")
    print_int(pa / 100)
    print_str(" hPa  (alt: ")
    print_int(alt)
    print_str(" m)\n")

def show_readings():
    print_str("\n")
    smon_divider()
    print_str("        SENSOR MONITOR\n")
    smon_divider()

    print_temp()
    print_newline()
    print_accel()
    print_newline()
    print_light()
    print_newline()
    print_humidity()
    print_newline()
    print_pressure()

    smon_divider()

def sensormon_main(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    uart_init()

    print_str("=== Sensor Monitor Demo ===\n")
    print_str("Initializing sensors...\n")

    # Initialize with noise for realistic readings
    sensors_seed(12345)
    sensors_enable_noise(True)
    sensors_init_all()

    print_str("Sensors ready!\n")

    # Show multiple readings to demonstrate variation
    i: int32 = 0
    while i < 3:
        show_readings()
        i = i + 1

    print_str("\nDemo complete.\n")
    return 0
