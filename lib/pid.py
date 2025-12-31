# Pynux PID Controller Library
#
# Integer/fixed-point PID controller for bare-metal ARM.
# Supports multiple controller instances, anti-windup,
# output clamping, and derivative filtering.
#
# Uses 16.16 fixed-point format for precision.

from lib.memory import alloc, free

# ============================================================================
# Constants
# ============================================================================

# Fixed-point scale (16.16 format)
PID_FP_SHIFT: int32 = 16
PID_FP_ONE: int32 = 65536      # 1.0 in 16.16 fixed-point
PID_FP_HALF: int32 = 32768     # 0.5 in 16.16 fixed-point

# Anti-windup modes
PID_WINDUP_NONE: int32 = 0     # No anti-windup
PID_WINDUP_CLAMP: int32 = 1    # Clamp integral term
PID_WINDUP_BACK_CALC: int32 = 2  # Back-calculation

# Controller modes
PID_MODE_MANUAL: int32 = 0     # Manual output control
PID_MODE_AUTO: int32 = 1       # Automatic PID control

# Default derivative filter coefficient (0.1 in fixed-point)
PID_DEFAULT_DERIV_FILTER: int32 = 6554  # ~0.1 * 65536

# ============================================================================
# PID Controller Structure
# ============================================================================
#
# Layout:
#   kp: int32           - Proportional gain (16.16 FP) (offset 0)
#   ki: int32           - Integral gain (16.16 FP) (offset 4)
#   kd: int32           - Derivative gain (16.16 FP) (offset 8)
#   setpoint: int32     - Target setpoint (offset 12)
#   output: int32       - Controller output (offset 16)
#   integral: int32     - Integral accumulator (offset 20)
#   prev_error: int32   - Previous error for derivative (offset 24)
#   prev_input: int32   - Previous input for deriv on measurement (offset 28)
#   deriv_filtered: int32 - Filtered derivative term (offset 32)
#   output_min: int32   - Minimum output limit (offset 36)
#   output_max: int32   - Maximum output limit (offset 40)
#   integral_min: int32 - Minimum integral limit (offset 44)
#   integral_max: int32 - Maximum integral limit (offset 48)
#   deriv_filter: int32 - Derivative filter coefficient (offset 52)
#   windup_mode: int32  - Anti-windup mode (offset 56)
#   mode: int32         - Controller mode (manual/auto) (offset 60)
#   dt_ms: int32        - Sample time in milliseconds (offset 64)
#   last_time: int32    - Last update time (offset 68)
# Total: 72 bytes

PID_KP_OFFSET: int32 = 0
PID_KI_OFFSET: int32 = 4
PID_KD_OFFSET: int32 = 8
PID_SETPOINT_OFFSET: int32 = 12
PID_OUTPUT_OFFSET: int32 = 16
PID_INTEGRAL_OFFSET: int32 = 20
PID_PREV_ERROR_OFFSET: int32 = 24
PID_PREV_INPUT_OFFSET: int32 = 28
PID_DERIV_FILTERED_OFFSET: int32 = 32
PID_OUTPUT_MIN_OFFSET: int32 = 36
PID_OUTPUT_MAX_OFFSET: int32 = 40
PID_INTEGRAL_MIN_OFFSET: int32 = 44
PID_INTEGRAL_MAX_OFFSET: int32 = 48
PID_DERIV_FILTER_OFFSET: int32 = 52
PID_WINDUP_MODE_OFFSET: int32 = 56
PID_MODE_OFFSET: int32 = 60
PID_DT_MS_OFFSET: int32 = 64
PID_LAST_TIME_OFFSET: int32 = 68
PID_STRUCT_SIZE: int32 = 72

# ============================================================================
# Fixed-Point Math Helpers
# ============================================================================

def _pid_fp_mul(a: int32, b: int32) -> int32:
    """Multiply two 16.16 fixed-point numbers.

    Uses 8-bit pre-shift to avoid overflow in 32-bit math.
    Result may lose some precision for very large values.
    """
    # Shift both operands down by 8 bits before multiply
    # Result: (a >> 8) * (b >> 8) gives a 16.16 result
    return (a >> 8) * (b >> 8)

def _pid_fp_div(a: int32, b: int32) -> int32:
    """Divide two 16.16 fixed-point numbers."""
    if b == 0:
        if a >= 0:
            return 2147483647  # INT_MAX
        return -2147483648     # INT_MIN
    # Shift a up by 8, divide, then shift result up by 8
    return ((a << 8) / (b >> 8))

def _pid_fp_from_int(x: int32) -> int32:
    """Convert integer to 16.16 fixed-point."""
    return x << PID_FP_SHIFT

def _pid_fp_to_int(x: int32) -> int32:
    """Convert 16.16 fixed-point to integer (truncate)."""
    return x >> PID_FP_SHIFT

def _pid_clamp(val: int32, min_val: int32, max_val: int32) -> int32:
    """Clamp value between min and max."""
    if val < min_val:
        return min_val
    if val > max_val:
        return max_val
    return val

def _pid_abs(x: int32) -> int32:
    """Absolute value."""
    if x < 0:
        return -x
    return x

# ============================================================================
# PID Controller Creation and Configuration
# ============================================================================

def pid_create() -> Ptr[int32]:
    """Create a new PID controller instance.

    Returns:
        Pointer to PID structure, or null on allocation failure.
    """
    pid: Ptr[int32] = cast[Ptr[int32]](alloc(PID_STRUCT_SIZE))
    if cast[uint32](pid) == 0:
        return cast[Ptr[int32]](0)

    # Initialize with defaults
    pid[0] = PID_FP_ONE        # kp = 1.0
    pid[1] = 0                 # ki = 0
    pid[2] = 0                 # kd = 0
    pid[3] = 0                 # setpoint
    pid[4] = 0                 # output
    pid[5] = 0                 # integral
    pid[6] = 0                 # prev_error
    pid[7] = 0                 # prev_input
    pid[8] = 0                 # deriv_filtered
    pid[9] = -2147483648       # output_min (INT_MIN)
    pid[10] = 2147483647       # output_max (INT_MAX)
    pid[11] = -2147483648      # integral_min
    pid[12] = 2147483647       # integral_max
    pid[13] = PID_DEFAULT_DERIV_FILTER  # deriv_filter
    pid[14] = PID_WINDUP_CLAMP # windup_mode
    pid[15] = PID_MODE_AUTO    # mode
    pid[16] = 10               # dt_ms = 10ms default
    pid[17] = 0                # last_time

    return pid

def pid_destroy(pid: Ptr[int32]):
    """Destroy PID controller and free memory.

    Args:
        pid: Pointer to PID structure
    """
    if cast[uint32](pid) != 0:
        free(cast[Ptr[uint8]](pid))

def pid_set_gains(pid: Ptr[int32], kp: int32, ki: int32, kd: int32):
    """Set PID gains (all in 16.16 fixed-point format).

    Args:
        pid: Pointer to PID structure
        kp: Proportional gain
        ki: Integral gain
        kd: Derivative gain
    """
    pid[0] = kp
    pid[1] = ki
    pid[2] = kd

def pid_set_gains_int(pid: Ptr[int32], kp: int32, ki: int32, kd: int32):
    """Set PID gains from integer values.

    Args:
        pid: Pointer to PID structure
        kp: Proportional gain (integer, will be converted)
        ki: Integral gain (integer, will be converted)
        kd: Derivative gain (integer, will be converted)
    """
    pid[0] = _pid_fp_from_int(kp)
    pid[1] = _pid_fp_from_int(ki)
    pid[2] = _pid_fp_from_int(kd)

def pid_set_gains_scaled(pid: Ptr[int32], kp_x100: int32, ki_x100: int32, kd_x100: int32):
    """Set PID gains from values scaled by 100.

    Useful for setting fractional gains without fixed-point math.
    Example: kp_x100 = 150 means kp = 1.5

    Args:
        pid: Pointer to PID structure
        kp_x100: Proportional gain * 100
        ki_x100: Integral gain * 100
        kd_x100: Derivative gain * 100
    """
    # Convert from x100 to 16.16 fixed-point
    # FP = (x100 * 65536) / 100 = x100 * 655.36 ~= x100 * 655
    pid[0] = kp_x100 * 655
    pid[1] = ki_x100 * 655
    pid[2] = kd_x100 * 655

def pid_set_setpoint(pid: Ptr[int32], setpoint: int32):
    """Set target setpoint.

    Args:
        pid: Pointer to PID structure
        setpoint: Target value
    """
    pid[3] = setpoint

def pid_set_output_limits(pid: Ptr[int32], min_out: int32, max_out: int32):
    """Set output limits for clamping.

    Args:
        pid: Pointer to PID structure
        min_out: Minimum output value
        max_out: Maximum output value
    """
    pid[9] = min_out
    pid[10] = max_out

    # Also clamp current output
    pid[4] = _pid_clamp(pid[4], min_out, max_out)

def pid_set_integral_limits(pid: Ptr[int32], min_int: int32, max_int: int32):
    """Set integral term limits for anti-windup.

    Args:
        pid: Pointer to PID structure
        min_int: Minimum integral value
        max_int: Maximum integral value
    """
    pid[11] = min_int
    pid[12] = max_int

    # Clamp current integral
    pid[5] = _pid_clamp(pid[5], min_int, max_int)

def pid_set_sample_time(pid: Ptr[int32], dt_ms: int32):
    """Set sample time in milliseconds.

    Args:
        pid: Pointer to PID structure
        dt_ms: Sample time in milliseconds
    """
    if dt_ms > 0:
        pid[16] = dt_ms

def pid_set_deriv_filter(pid: Ptr[int32], filter_coeff: int32):
    """Set derivative filter coefficient (16.16 fixed-point).

    Lower values = more filtering (smoother but slower response).
    Typical range: 0.05 to 0.2 (3277 to 13107 in fixed-point).

    Args:
        pid: Pointer to PID structure
        filter_coeff: Filter coefficient (0 to PID_FP_ONE)
    """
    pid[13] = _pid_clamp(filter_coeff, 0, PID_FP_ONE)

def pid_set_windup_mode(pid: Ptr[int32], mode: int32):
    """Set anti-windup mode.

    Args:
        pid: Pointer to PID structure
        mode: PID_WINDUP_NONE, PID_WINDUP_CLAMP, or PID_WINDUP_BACK_CALC
    """
    pid[14] = mode

def pid_set_mode(pid: Ptr[int32], mode: int32):
    """Set controller mode.

    Args:
        pid: Pointer to PID structure
        mode: PID_MODE_MANUAL or PID_MODE_AUTO
    """
    # When switching to auto, reset integral to prevent bump
    if mode == PID_MODE_AUTO and pid[15] == PID_MODE_MANUAL:
        pid[5] = 0  # Reset integral

    pid[15] = mode

# ============================================================================
# PID Controller Core Functions
# ============================================================================

def pid_compute(pid: Ptr[int32], input: int32) -> int32:
    """Compute PID output for given input.

    Call this at regular intervals (at sample_time rate).

    Args:
        pid: Pointer to PID structure
        input: Current process variable (measured value)

    Returns:
        Controller output (clamped to output limits)
    """
    # Check mode
    if pid[15] == PID_MODE_MANUAL:
        return pid[4]

    # Get parameters
    kp: int32 = pid[0]
    ki: int32 = pid[1]
    kd: int32 = pid[2]
    setpoint: int32 = pid[3]
    dt_ms: int32 = pid[16]

    # Calculate error
    error: int32 = setpoint - input

    # Proportional term
    p_term: int32 = _pid_fp_mul(kp, _pid_fp_from_int(error))

    # Integral term
    # integral += ki * error * dt
    # Convert dt from ms to seconds (scaled by FP_ONE)
    dt_fp: int32 = (dt_ms * PID_FP_ONE) / 1000
    i_increment: int32 = _pid_fp_mul(_pid_fp_mul(ki, _pid_fp_from_int(error)), dt_fp)
    integral: int32 = pid[5] + i_increment

    # Apply anti-windup to integral
    windup_mode: int32 = pid[14]
    if windup_mode == PID_WINDUP_CLAMP:
        integral = _pid_clamp(integral, pid[11], pid[12])

    pid[5] = integral

    # Derivative term (on measurement to avoid derivative kick)
    # d_term = kd * (input - prev_input) / dt
    d_input: int32 = input - pid[7]
    d_term_raw: int32 = 0
    if dt_ms > 0:
        d_term_raw = _pid_fp_mul(kd, _pid_fp_div(_pid_fp_from_int(d_input), dt_fp))
        d_term_raw = -d_term_raw  # Negative because derivative on measurement

    # Apply derivative filter (low-pass)
    # filtered = alpha * raw + (1 - alpha) * prev_filtered
    alpha: int32 = pid[13]
    prev_deriv: int32 = pid[8]
    d_term: int32 = _pid_fp_mul(alpha, d_term_raw) + _pid_fp_mul(PID_FP_ONE - alpha, prev_deriv)
    pid[8] = d_term

    # Calculate output
    output: int32 = _pid_fp_to_int(p_term + integral + d_term)

    # Clamp output
    output_min: int32 = pid[9]
    output_max: int32 = pid[10]
    output = _pid_clamp(output, output_min, output_max)

    # Back-calculation anti-windup
    if windup_mode == PID_WINDUP_BACK_CALC:
        # If output is saturated, adjust integral
        if output == output_max or output == output_min:
            # Reduce integral to prevent further windup
            pid[5] = pid[5] - i_increment

    # Store values for next iteration
    pid[4] = output
    pid[6] = error
    pid[7] = input

    return output

def pid_compute_timed(pid: Ptr[int32], input: int32, current_time: int32) -> int32:
    """Compute PID output with automatic timing.

    Automatically calculates dt based on time since last call.

    Args:
        pid: Pointer to PID structure
        input: Current process variable
        current_time: Current time in milliseconds

    Returns:
        Controller output (clamped to output limits)
    """
    last_time: int32 = pid[17]
    dt: int32 = current_time - last_time

    # Update sample time if reasonable
    if dt > 0 and dt < 10000:
        pid[16] = dt

    pid[17] = current_time

    return pid_compute(pid, input)

def pid_reset(pid: Ptr[int32]):
    """Reset PID controller state.

    Clears integral, derivative, and previous values.
    Call this when starting a new control sequence.

    Args:
        pid: Pointer to PID structure
    """
    pid[4] = 0   # output
    pid[5] = 0   # integral
    pid[6] = 0   # prev_error
    pid[7] = 0   # prev_input
    pid[8] = 0   # deriv_filtered
    pid[17] = 0  # last_time

def pid_set_output(pid: Ptr[int32], output: int32):
    """Manually set output (for manual mode or bumpless transfer).

    Args:
        pid: Pointer to PID structure
        output: Output value
    """
    pid[4] = _pid_clamp(output, pid[9], pid[10])

# ============================================================================
# Query Functions
# ============================================================================

def pid_get_output(pid: Ptr[int32]) -> int32:
    """Get current output value.

    Args:
        pid: Pointer to PID structure

    Returns:
        Current output
    """
    return pid[4]

def pid_get_integral(pid: Ptr[int32]) -> int32:
    """Get current integral term value.

    Args:
        pid: Pointer to PID structure

    Returns:
        Current integral accumulator
    """
    return pid[5]

def pid_get_error(pid: Ptr[int32]) -> int32:
    """Get last error value.

    Args:
        pid: Pointer to PID structure

    Returns:
        setpoint - last input
    """
    return pid[6]

def pid_get_setpoint(pid: Ptr[int32]) -> int32:
    """Get current setpoint.

    Args:
        pid: Pointer to PID structure

    Returns:
        Current setpoint
    """
    return pid[3]

def pid_get_kp(pid: Ptr[int32]) -> int32:
    """Get proportional gain (fixed-point).

    Args:
        pid: Pointer to PID structure

    Returns:
        Kp in 16.16 fixed-point
    """
    return pid[0]

def pid_get_ki(pid: Ptr[int32]) -> int32:
    """Get integral gain (fixed-point).

    Args:
        pid: Pointer to PID structure

    Returns:
        Ki in 16.16 fixed-point
    """
    return pid[1]

def pid_get_kd(pid: Ptr[int32]) -> int32:
    """Get derivative gain (fixed-point).

    Args:
        pid: Pointer to PID structure

    Returns:
        Kd in 16.16 fixed-point
    """
    return pid[2]

# ============================================================================
# Tuning Helpers
# ============================================================================

def pid_autotune_step(pid: Ptr[int32], input: int32, output_high: int32,
                      output_low: int32) -> int32:
    """Relay auto-tuning step function.

    Implements relay feedback method for auto-tuning.
    Call this in a loop until stable oscillation is detected.

    Args:
        pid: Pointer to PID structure
        input: Current process variable
        output_high: High output value for relay
        output_low: Low output value for relay

    Returns:
        Current relay output (output_high or output_low)
    """
    setpoint: int32 = pid[3]

    # Simple relay control
    if input < setpoint:
        return output_high
    return output_low

# ============================================================================
# Example Usage: Motor Speed Control
# ============================================================================
#
# # Create PID controller
# pid: Ptr[int32] = pid_create()
#
# # Configure gains (Kp=2.0, Ki=0.5, Kd=0.1)
# pid_set_gains_scaled(pid, 200, 50, 10)  # Values * 100
#
# # Set target speed (e.g., 1000 RPM)
# pid_set_setpoint(pid, 1000)
#
# # Set output limits (PWM duty cycle 0-100)
# pid_set_output_limits(pid, 0, 100)
#
# # Set sample time (10ms)
# pid_set_sample_time(pid, 10)
#
# # Main control loop
# while True:
#     # Read current speed from encoder
#     current_speed: int32 = read_encoder_rpm()
#
#     # Compute PID output
#     pwm_duty: int32 = pid_compute(pid, current_speed)
#
#     # Apply to motor
#     set_motor_pwm(pwm_duty)
#
#     # Wait for next sample
#     delay_ms(10)
#
# ============================================================================
# Example Usage: Temperature Control
# ============================================================================
#
# # Create PID controller
# pid: Ptr[int32] = pid_create()
#
# # Configure for slow thermal process
# pid_set_gains_scaled(pid, 100, 10, 500)  # Kp=1.0, Ki=0.1, Kd=5.0
#
# # Set target temperature (250 degrees * 10 for 0.1 degree resolution)
# pid_set_setpoint(pid, 2500)  # 250.0 degrees
#
# # Set output limits (heater power 0-100%)
# pid_set_output_limits(pid, 0, 100)
#
# # Set longer sample time for thermal (1 second)
# pid_set_sample_time(pid, 1000)
#
# # Set integral limits to prevent excessive windup
# pid_set_integral_limits(pid, -500000, 500000)
#
# # Increase derivative filtering for noisy sensor
# pid_set_deriv_filter(pid, 3277)  # ~0.05 coefficient
#
# # Main control loop
# while True:
#     # Read temperature (in 0.1 degree units)
#     temp: int32 = read_temperature_x10()
#
#     # Compute PID output
#     heater_power: int32 = pid_compute(pid, temp)
#
#     # Apply to heater
#     set_heater_power(heater_power)
#
#     # Wait for next sample
#     delay_ms(1000)

# ============================================================================
# Global Instance API (for simple single-PID use)
# ============================================================================

# Global PID controller instance
_global_pid: Ptr[int32] = cast[Ptr[int32]](0)

def _ensure_global_pid():
    """Create global PID if not exists."""
    global _global_pid
    if _global_pid == cast[Ptr[int32]](0):
        _global_pid = pid_create()

def pid_global_init(kp: int32, ki: int32, kd: int32):
    """Initialize global PID with gains (scaled by 100)."""
    _ensure_global_pid()
    pid_set_gains_scaled(_global_pid, kp, ki, kd)
    pid_set_output_limits(_global_pid, -32767, 32767)
    pid_set_integral_limits(_global_pid, -1000000, 1000000)

def pid_global_set_setpoint(setpoint: int32):
    """Set global PID setpoint."""
    _ensure_global_pid()
    _global_pid[PID_SETPOINT_OFFSET // 4] = setpoint

def pid_global_set_limits(min_out: int32, max_out: int32):
    """Set global PID output limits."""
    _ensure_global_pid()
    pid_set_output_limits(_global_pid, min_out, max_out)

def pid_global_set_gains(kp: int32, ki: int32, kd: int32):
    """Set global PID gains (scaled by 100)."""
    _ensure_global_pid()
    pid_set_gains_scaled(_global_pid, kp, ki, kd)

def pid_global_update(input_val: int32) -> int32:
    """Compute global PID output."""
    if _global_pid == cast[Ptr[int32]](0):
        return 0
    return pid_compute(_global_pid, input_val)

def pid_global_get_error() -> int32:
    """Get current error from global PID."""
    if _global_pid == cast[Ptr[int32]](0):
        return 0
    return _global_pid[PID_PREV_ERROR_OFFSET // 4]

def pid_global_reset():
    """Reset global PID controller."""
    if _global_pid != cast[Ptr[int32]](0):
        pid_reset(_global_pid)

# ============================================================================
# Simple Aliases for Test Compatibility
# ============================================================================
# These functions provide a simpler API using the global instance.
# They match the signatures expected by test files.

def pid_simple_init(kp: int32, ki: int32, kd: int32):
    """Initialize PID with gains (scaled by 100) - uses global instance."""
    pid_global_init(kp, ki, kd)

def pid_simple_set_setpoint(setpoint: int32):
    """Set target setpoint - uses global instance."""
    pid_global_set_setpoint(setpoint)

def pid_simple_set_limits(min_out: int32, max_out: int32):
    """Set output limits - uses global instance."""
    pid_global_set_limits(min_out, max_out)

def pid_simple_update(input_val: int32) -> int32:
    """Compute PID output - uses global instance."""
    return pid_global_update(input_val)

def pid_simple_get_error() -> int32:
    """Get current error - uses global instance."""
    return pid_global_get_error()

def pid_simple_reset():
    """Reset PID controller - uses global instance."""
    pid_global_reset()

def pid_simple_set_gains(kp: int32, ki: int32, kd: int32):
    """Set PID gains (scaled by 100) - uses global instance."""
    pid_global_set_gains(kp, ki, kd)
