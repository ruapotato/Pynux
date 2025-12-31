# Pynux Filter Tests
#
# Tests for signal filtering library.

from tests.test_framework import (
    assert_true, assert_false, assert_eq, assert_neq,
    assert_gt, assert_gte, assert_lt, assert_lte,
    print_section, print_results, reset_counters
)
from lib.io import print_str, print_int, print_newline
from lib.filters import lpf_init, lpf_update, lpf_reset, lpf_get_value
from lib.filters import mavg_init, mavg_update, mavg_reset, mavg_get_value
from lib.filters import kalman_init, kalman_update, kalman_reset

def test_lpf_basic():
    print_section("Low-Pass Filter Basic")

    # Initialize with alpha=50 (50% smoothing)
    lpf_init(50)

    # First value should be output directly
    output: int32 = lpf_update(1000)
    assert_eq(output, 1000, "first value passed through")

    # Second value should be smoothed
    output = lpf_update(2000)
    # output = alpha * new + (100-alpha) * old = 50 * 2000 + 50 * 1000 / 100 = 1500
    assert_gt(output, 1000, "smoothed toward new value")
    assert_lt(output, 2000, "but not fully at new value")

def test_lpf_smoothing():
    print_section("LPF Smoothing Strength")

    # Test high smoothing (low alpha)
    lpf_init(10)  # 10% new, 90% old
    lpf_update(0)
    output: int32 = lpf_update(1000)
    assert_lt(output, 500, "high smoothing resists change")

    lpf_reset()

    # Test low smoothing (high alpha)
    lpf_init(90)  # 90% new, 10% old
    lpf_update(0)
    output = lpf_update(1000)
    assert_gt(output, 500, "low smoothing follows input")

def test_lpf_convergence():
    print_section("LPF Convergence")

    lpf_init(50)
    lpf_update(0)

    # Apply constant input, should converge
    i: int32 = 0
    output: int32 = 0
    while i < 10:
        output = lpf_update(1000)
        i = i + 1

    # Should be close to 1000 after 10 iterations
    assert_gt(output, 900, "converges to constant input")

def test_lpf_noise_reduction():
    print_section("LPF Noise Reduction")

    lpf_init(30)

    # Simulate noisy signal around 1000
    values: Array[8, int32]
    values[0] = 950
    values[1] = 1050
    values[2] = 980
    values[3] = 1020
    values[4] = 960
    values[5] = 1040
    values[6] = 990
    values[7] = 1010

    # First value
    lpf_update(values[0])

    # Filter the noisy values
    min_out: int32 = 10000
    max_out: int32 = -10000

    i: int32 = 1
    while i < 8:
        output: int32 = lpf_update(values[i])
        if output < min_out:
            min_out = output
        if output > max_out:
            max_out = output
        i = i + 1

    range_out: int32 = max_out - min_out
    # Input range is 100 (950-1050), filtered should be less
    assert_lt(range_out, 100, "filter reduces noise range")

def test_mavg_basic():
    print_section("Moving Average Basic")

    # Window size of 4
    mavg_init(4)

    # Fill window
    output: int32 = mavg_update(100)
    assert_eq(output, 100, "first value")

    output = mavg_update(200)
    # Average of [100, 200] = 150
    assert_eq(output, 150, "two values averaged")

    output = mavg_update(300)
    # Average of [100, 200, 300] = 200
    assert_eq(output, 200, "three values averaged")

    output = mavg_update(400)
    # Average of [100, 200, 300, 400] = 250
    assert_eq(output, 250, "four values averaged")

def test_mavg_sliding():
    print_section("Moving Average Sliding")

    mavg_init(3)

    mavg_update(100)
    mavg_update(200)
    mavg_update(300)
    # [100, 200, 300] avg = 200

    output: int32 = mavg_update(600)
    # [200, 300, 600] avg = 366
    assert_gt(output, 300, "window slides")
    assert_lt(output, 600, "still averaging")

def test_mavg_reset():
    print_section("Moving Average Reset")

    mavg_init(4)

    mavg_update(100)
    mavg_update(200)
    mavg_update(300)

    mavg_reset()
    output: int32 = mavg_update(500)
    assert_eq(output, 500, "reset clears history")

def test_kalman_basic():
    print_section("Kalman Filter Basic")

    # Q=1 (process noise), R=10 (measurement noise)
    kalman_init(1, 10)

    output: int32 = kalman_update(1000)
    assert_eq(output, 1000, "first measurement accepted")

    # Second measurement should be filtered
    output = kalman_update(1100)
    assert_gt(output, 1000, "moves toward new measurement")
    assert_lt(output, 1100, "but with smoothing")

def test_kalman_noise_rejection():
    print_section("Kalman Noise Rejection")

    # High measurement noise - trust prediction more
    kalman_init(1, 100)

    kalman_update(1000)

    # Noisy measurement should be largely rejected
    output: int32 = kalman_update(2000)  # Spike!
    assert_lt(output, 1500, "spike largely rejected")

    # With low measurement noise - trust measurements more
    kalman_reset()
    kalman_init(1, 1)
    kalman_update(1000)
    output = kalman_update(2000)
    assert_gt(output, 1500, "measurement trusted more")

def test_kalman_tracking():
    print_section("Kalman Tracking")

    kalman_init(10, 10)  # Balanced Q and R

    # Track a changing signal
    kalman_update(0)
    i: int32 = 0
    output: int32 = 0
    while i < 5:
        output = kalman_update(i * 100)
        i = i + 1

    # Should track the rising signal
    assert_gt(output, 200, "tracks rising signal")

def run_filter_tests():
    print_str("=== Pynux Filter Tests ===")
    print_newline()

    reset_counters()

    test_lpf_basic()
    test_lpf_smoothing()
    test_lpf_convergence()
    test_lpf_noise_reduction()
    test_mavg_basic()
    test_mavg_sliding()
    test_mavg_reset()
    test_kalman_basic()
    test_kalman_noise_rejection()
    test_kalman_tracking()

    return print_results()
