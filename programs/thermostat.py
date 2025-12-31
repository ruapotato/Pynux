# Thermostat with PID Control
#
# Practical example showing closed-loop temperature control.
# Uses: sensors, PID controller, DC motor (fan)

from lib.io import console_puts, console_print_int
from lib.sensors import temp_read, sensors_init_all, sensors_seed
from lib.motors import dc_init, dc_set_speed
from lib.pid import pid_init, pid_set_setpoint, pid_update, pid_reset
from lib.pid import pid_set_limits, pid_set_gains, pid_get_error
from kernel.timer import timer_get_ticks, timer_delay_ms

# State
target_temp: int32 = 2200       # Target: 22.00 C (in centidegrees)
fan_speed: int32 = 0
last_update: int32 = 0
UPDATE_INTERVAL: int32 = 1000   # Update every 1 second

def thermostat_init():
    """Initialize thermostat system."""
    console_puts("Thermostat: Initializing...\n")

    # Initialize sensors
    sensors_seed(42)
    sensors_init_all()

    # Initialize fan (DC motor 0)
    dc_init(0)

    # Initialize PID controller
    # Gains scaled by 100: Kp=150, Ki=10, Kd=50
    pid_init(150, 10, 50)
    pid_set_setpoint(target_temp)
    pid_set_limits(0, 100)  # Fan speed 0-100%

    console_puts("  Target: ")
    console_print_int(target_temp / 100)
    console_puts(".")
    console_print_int(target_temp % 100)
    console_puts(" C\n")
    console_puts("  PID: Kp=1.5 Ki=0.1 Kd=0.5\n")
    console_puts("Thermostat: Ready\n\n")

def thermostat_update():
    """Called periodically to update control loop."""
    global fan_speed, last_update

    now: int32 = timer_get_ticks()
    if now - last_update < UPDATE_INTERVAL:
        return
    last_update = now

    # Read current temperature
    current: int32 = temp_read()

    # Update PID controller
    output: int32 = pid_update(current)
    fan_speed = output

    # Apply to fan
    dc_set_speed(0, fan_speed)

    # Display status
    error: int32 = pid_get_error()

    console_puts("Temp: ")
    console_print_int(current / 100)
    console_puts(".")
    if (current % 100) < 10:
        console_puts("0")
    console_print_int(current % 100)
    console_puts("C | Target: ")
    console_print_int(target_temp / 100)
    console_puts("C | Fan: ")
    console_print_int(fan_speed)
    console_puts("% | Err: ")
    console_print_int(error / 100)
    console_puts("\n")

def thermostat_set_target(temp_c: int32):
    """Set target temperature in centidegrees."""
    global target_temp
    target_temp = temp_c
    pid_set_setpoint(target_temp)
    pid_reset()  # Reset integral term

    console_puts("New target: ")
    console_print_int(temp_c / 100)
    console_puts(" C\n")

def thermostat_main(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    """Standalone demo mode."""
    thermostat_init()

    console_puts("=== Thermostat Demo ===\n")
    console_puts("Running control loop for 10 cycles...\n\n")

    # Run 10 update cycles
    i: int32 = 0
    while i < 10:
        thermostat_update()
        timer_delay_ms(100)  # Simulate time passing
        i = i + 1

    console_puts("\nDemo complete.\n")
    return 0
