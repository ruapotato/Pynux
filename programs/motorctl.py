# Motor Controller Demo
#
# Demonstrates servo, stepper, and DC motor control.
# Shows motor state transitions and status.

from lib.io import print_str, print_int, print_newline, uart_init
from lib.motors import motor_set_debug
from lib.motors import servo_init, servo_set_angle, servo_get_angle, servo_get_pulse
from lib.motors import servo_set_smooth, servo_set_speed, servo_update, servo_is_moving
from lib.motors import stepper_init, stepper_steps, stepper_rotate, stepper_get_position
from lib.motors import stepper_set_mode, STEPPER_MODE_FULL, STEPPER_MODE_HALF, stepper_release
from lib.motors import dc_init, dc_set_speed, dc_get_speed, dc_brake, dc_coast
from lib.motors import dc_is_running, dc_get_direction, motors_print_status

def mctl_divider():
    print_str("========================================\n")

def demo_servo():
    mctl_divider()
    print_str("       SERVO MOTOR DEMO\n")
    mctl_divider()

    print_str("\nInitializing servo 0...\n")
    servo_init(0)

    print_str("\nMoving to 0 degrees...\n")
    servo_set_angle(0, 0)
    print_str("  Angle: ")
    print_int(servo_get_angle(0))
    print_str(" deg, Pulse: ")
    print_int(servo_get_pulse(0))
    print_str(" us\n")

    print_str("\nMoving to 90 degrees...\n")
    servo_set_angle(0, 90)
    print_str("  Angle: ")
    print_int(servo_get_angle(0))
    print_str(" deg, Pulse: ")
    print_int(servo_get_pulse(0))
    print_str(" us\n")

    print_str("\nMoving to 180 degrees...\n")
    servo_set_angle(0, 180)
    print_str("  Angle: ")
    print_int(servo_get_angle(0))
    print_str(" deg, Pulse: ")
    print_int(servo_get_pulse(0))
    print_str(" us\n")

    # Demo smooth movement
    print_str("\nEnabling smooth movement mode...\n")
    servo_set_smooth(0, True)
    servo_set_speed(0, 15)  # 15 degrees per update

    print_str("Moving smoothly to 45 degrees...\n")
    servo_set_angle(0, 45)

    steps: int32 = 0
    while servo_is_moving(0) and steps < 20:
        servo_update(0)
        print_str("  -> ")
        print_int(servo_get_angle(0))
        print_str(" deg\n")
        steps = steps + 1

    print_str("Servo demo complete.\n\n")

def demo_stepper():
    mctl_divider()
    print_str("      STEPPER MOTOR DEMO\n")
    mctl_divider()

    print_str("\nInitializing stepper 0 (200 steps/rev)...\n")
    stepper_init(0, 200)

    print_str("\nFull step mode:\n")
    stepper_set_mode(0, STEPPER_MODE_FULL)

    print_str("  Moving 50 steps forward...\n")
    stepper_steps(0, 50)
    print_str("  Position: ")
    print_int(stepper_get_position(0))
    print_str(" steps\n")

    print_str("  Moving 25 steps backward...\n")
    stepper_steps(0, -25)
    print_str("  Position: ")
    print_int(stepper_get_position(0))
    print_str(" steps\n")

    print_str("\nHalf step mode (2x resolution):\n")
    stepper_set_mode(0, STEPPER_MODE_HALF)

    print_str("  Rotating 90 degrees...\n")
    stepper_rotate(0, 90)
    print_str("  Position: ")
    print_int(stepper_get_position(0))
    print_str(" steps\n")

    print_str("  Rotating -45 degrees...\n")
    stepper_rotate(0, -45)
    print_str("  Position: ")
    print_int(stepper_get_position(0))
    print_str(" steps\n")

    print_str("\nReleasing stepper (coils off)...\n")
    stepper_release(0)

    print_str("Stepper demo complete.\n\n")

def demo_dc():
    mctl_divider()
    print_str("       DC MOTOR DEMO\n")
    mctl_divider()

    print_str("\nInitializing DC motor 0...\n")
    dc_init(0)

    print_str("\nSpeed ramp up:\n")
    speed: int32 = 0
    while speed <= 100:
        dc_set_speed(0, speed)
        print_str("  Speed: ")
        print_int(speed)
        print_str("% ")
        if dc_is_running(0):
            print_str("[RUNNING]")
        print_str("\n")
        speed = speed + 25

    print_str("\nBraking...\n")
    dc_brake(0)
    print_str("  Speed: ")
    print_int(dc_get_speed(0))
    print_str("% [BRAKED]\n")

    print_str("\nReverse direction:\n")
    speed = -25
    while speed >= -100:
        dc_set_speed(0, speed)
        print_str("  Speed: ")
        print_int(speed)
        print_str("% ")
        dir: int32 = dc_get_direction(0)
        if dir < 0:
            print_str("[REVERSE]")
        print_str("\n")
        speed = speed - 25

    print_str("\nCoasting to stop...\n")
    dc_coast(0)

    print_str("DC motor demo complete.\n\n")

def motorctl_main(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    uart_init()

    print_str("=== Motor Controller Demo ===\n")
    print_str("Demonstrating servo, stepper, and DC motors\n\n")

    # Enable debug output
    motor_set_debug(True)

    demo_servo()
    demo_stepper()
    demo_dc()

    mctl_divider()
    print_str("    FINAL MOTOR STATUS\n")
    mctl_divider()
    motors_print_status()

    print_str("\nAll motor demos complete!\n")
    return 0
