# Pynux PID Controller Tests
#
# Tests for PID control library.

from tests.test_framework import (
    assert_true, assert_false, assert_eq, assert_neq,
    assert_gt, assert_gte, assert_lt, assert_lte,
    print_section, print_results, reset_counters
)
from lib.io import print_str, print_int, print_newline
from lib.pid import pid_init, pid_set_setpoint, pid_update, pid_reset
from lib.pid import pid_set_limits, pid_get_error, pid_set_gains

def test_pid_init():
    print_section("PID Initialization")

    # Gains scaled by 100: Kp=100, Ki=10, Kd=5
    pid_init(100, 10, 5)
    pid_set_setpoint(1000)

    # Should have no error yet
    assert_true(True, "pid_init completes")

def test_pid_proportional():
    print_section("Proportional Control")

    # Pure P control: Ki=0, Kd=0
    pid_init(100, 0, 0)  # Kp = 1.0
    pid_set_setpoint(1000)
    pid_set_limits(-1000, 1000)

    # Error = setpoint - pv = 1000 - 500 = 500
    # Output = Kp * error = 1.0 * 500 = 500
    output: int32 = pid_update(500)
    assert_gt(output, 0, "positive error gives positive output")

    # Zero error should give zero output
    pid_reset()
    output = pid_update(1000)
    assert_eq(output, 0, "zero error gives zero output")

    # Negative error (overshooting)
    output = pid_update(1200)
    assert_lt(output, 0, "negative error gives negative output")

def test_pid_limits():
    print_section("PID Output Limits")

    pid_init(1000, 0, 0)  # Large Kp for big output
    pid_set_setpoint(1000)
    pid_set_limits(0, 100)  # Clamp to 0-100

    # Large error should be clamped
    output: int32 = pid_update(0)
    assert_lte(output, 100, "output clamped to max")
    assert_gte(output, 0, "output clamped to min")

    # Negative output should be clamped to min
    output = pid_update(2000)
    assert_gte(output, 0, "negative output clamped to 0")

def test_pid_integral():
    print_section("Integral Control")

    # Pure I control: Kp=0, Kd=0
    pid_init(0, 100, 0)  # Ki = 1.0
    pid_set_setpoint(1000)
    pid_set_limits(-10000, 10000)

    # First update with error=500
    output1: int32 = pid_update(500)

    # Second update - integral should accumulate
    output2: int32 = pid_update(500)
    assert_gt(output2, output1, "integral accumulates")

    # Third update
    output3: int32 = pid_update(500)
    assert_gt(output3, output2, "integral continues to grow")

def test_pid_reset():
    print_section("PID Reset")

    pid_init(100, 100, 0)
    pid_set_setpoint(1000)
    pid_set_limits(-10000, 10000)

    # Build up some integral
    pid_update(500)
    pid_update(500)
    pid_update(500)

    # Reset clears integral
    pid_reset()
    output1: int32 = pid_update(500)

    # Compare with fresh start
    pid_init(100, 100, 0)
    pid_set_setpoint(1000)
    pid_set_limits(-10000, 10000)
    output2: int32 = pid_update(500)

    assert_eq(output1, output2, "reset clears state")

def test_pid_error():
    print_section("PID Error Tracking")

    pid_init(100, 0, 0)
    pid_set_setpoint(1000)
    pid_set_limits(-10000, 10000)

    pid_update(600)  # Error = 1000 - 600 = 400
    error: int32 = pid_get_error()
    assert_eq(error, 400, "error is setpoint - pv")

    pid_update(1200)  # Error = 1000 - 1200 = -200
    error = pid_get_error()
    assert_eq(error, -200, "negative error when overshooting")

def test_pid_setpoint_change():
    print_section("Setpoint Change")

    pid_init(100, 0, 0)
    pid_set_setpoint(1000)
    pid_set_limits(-10000, 10000)

    output1: int32 = pid_update(500)  # Error = 500

    pid_set_setpoint(500)  # Change setpoint to match PV
    output2: int32 = pid_update(500)  # Error = 0

    assert_gt(output1, output2, "changing setpoint affects output")
    assert_eq(output2, 0, "zero error at new setpoint")

def test_pid_convergence():
    print_section("PID Convergence Simulation")

    # Simulate simple system converging to setpoint
    pid_init(50, 10, 5)  # Kp=0.5, Ki=0.1, Kd=0.05
    pid_set_setpoint(1000)
    pid_set_limits(0, 100)

    pv: int32 = 0  # Process variable starts at 0

    # Run 10 iterations
    i: int32 = 0
    while i < 10:
        output: int32 = pid_update(pv)
        # Simple plant model: pv changes by output/10
        pv = pv + output / 2
        if pv > 1000:
            pv = 1000
        i = i + 1

    # After iterations, should be closer to setpoint
    assert_gt(pv, 500, "PV increases toward setpoint")

def run_pid_tests():
    print_str("=== Pynux PID Controller Tests ===")
    print_newline()

    reset_counters()

    test_pid_init()
    test_pid_proportional()
    test_pid_limits()
    test_pid_integral()
    test_pid_reset()
    test_pid_error()
    test_pid_setpoint_change()
    test_pid_convergence()

    return print_results()
