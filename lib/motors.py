# Pynux Motors Library
#
# Emulated motor control drivers for QEMU ARM Cortex-M3.
# Simulates servo motors, stepper motors, and DC motors.
# Tracks state and outputs actions to console for debugging.
#
# Motors included:
#   - Servo motor (0-180 degree position control)
#   - Stepper motor (full/half step modes)
#   - DC motor with PWM speed control

from lib.io import console_putc, console_puts, console_print_int
from lib.math import abs_int, clamp, sign

# ============================================================================
# Motor Debug Output
# ============================================================================

_motor_debug: bool = True

def motor_set_debug(enabled: bool):
    """Enable or disable motor debug output.

    Args:
        enabled: True to print motor actions to console
    """
    global _motor_debug
    _motor_debug = enabled

def _motor_print(msg: Ptr[char]):
    """Internal: Print motor debug message."""
    if _motor_debug:
        console_puts(msg)
        console_putc('\n')

def _motor_print_val(msg: Ptr[char], val: int32):
    """Internal: Print motor debug message with value."""
    if _motor_debug:
        console_puts(msg)
        console_print_int(val)
        console_putc('\n')

# ============================================================================
# Servo Motor (0-180 degrees)
# ============================================================================
# Standard hobby servo controlled by PWM pulse width
# 1ms pulse = 0 degrees, 2ms pulse = 180 degrees
# Typical period is 20ms (50Hz)

# Maximum servos supported
SERVO_MAX: int32 = 8

# Servo state
_servo_initialized: Array[8, bool]
_servo_angle: Array[8, int32]           # Current angle (0-180)
_servo_target: Array[8, int32]          # Target angle (for smooth movement)
_servo_speed: Array[8, int32]           # Movement speed (degrees per update)
_servo_min_pulse: Array[8, int32]       # Min pulse width in microseconds
_servo_max_pulse: Array[8, int32]       # Max pulse width in microseconds
_servo_smooth: Array[8, bool]           # Smooth movement enabled

# Default pulse widths (microseconds)
SERVO_DEFAULT_MIN_PULSE: int32 = 1000   # 1ms for 0 degrees
SERVO_DEFAULT_MAX_PULSE: int32 = 2000   # 2ms for 180 degrees

def servo_init(id: int32):
    """Initialize a servo motor.

    Args:
        id: Servo ID (0-7)
    """
    if id < 0 or id >= SERVO_MAX:
        return

    _servo_initialized[id] = True
    _servo_angle[id] = 90       # Start at center
    _servo_target[id] = 90
    _servo_speed[id] = 5        # 5 degrees per update
    _servo_min_pulse[id] = SERVO_DEFAULT_MIN_PULSE
    _servo_max_pulse[id] = SERVO_DEFAULT_MAX_PULSE
    _servo_smooth[id] = False

    if _motor_debug:
        console_puts("Servo ")
        console_print_int(id)
        console_puts(" initialized at 90 degrees\n")

def servo_set_angle(id: int32, angle: int32):
    """Set servo angle.

    Args:
        id: Servo ID (0-7)
        angle: Target angle (0-180 degrees)
    """
    if id < 0 or id >= SERVO_MAX:
        return
    if not _servo_initialized[id]:
        servo_init(id)

    angle = clamp(angle, 0, 180)
    _servo_target[id] = angle

    if _servo_smooth[id]:
        # Smooth movement will be handled by servo_update()
        if _motor_debug:
            console_puts("Servo ")
            console_print_int(id)
            console_puts(" moving to ")
            console_print_int(angle)
            console_puts(" degrees (smooth)\n")
    else:
        # Immediate movement
        _servo_angle[id] = angle
        if _motor_debug:
            console_puts("Servo ")
            console_print_int(id)
            console_puts(" set to ")
            console_print_int(angle)
            console_puts(" degrees\n")

def servo_get_angle(id: int32) -> int32:
    """Get current servo angle.

    Args:
        id: Servo ID (0-7)

    Returns:
        Current angle (0-180 degrees)
    """
    if id < 0 or id >= SERVO_MAX:
        return 0
    return _servo_angle[id]

def servo_get_target(id: int32) -> int32:
    """Get target servo angle (for smooth movement).

    Args:
        id: Servo ID (0-7)

    Returns:
        Target angle (0-180 degrees)
    """
    if id < 0 or id >= SERVO_MAX:
        return 0
    return _servo_target[id]

def servo_set_smooth(id: int32, enabled: bool):
    """Enable or disable smooth movement.

    Args:
        id: Servo ID (0-7)
        enabled: True for smooth movement
    """
    if id < 0 or id >= SERVO_MAX:
        return
    _servo_smooth[id] = enabled

def servo_set_speed(id: int32, speed: int32):
    """Set servo movement speed (for smooth mode).

    Args:
        id: Servo ID (0-7)
        speed: Degrees per update (1-180)
    """
    if id < 0 or id >= SERVO_MAX:
        return
    _servo_speed[id] = clamp(speed, 1, 180)

def servo_set_pulse_range(id: int32, min_us: int32, max_us: int32):
    """Set servo pulse width range.

    Args:
        id: Servo ID (0-7)
        min_us: Minimum pulse width in microseconds (0 degrees)
        max_us: Maximum pulse width in microseconds (180 degrees)
    """
    if id < 0 or id >= SERVO_MAX:
        return
    _servo_min_pulse[id] = min_us
    _servo_max_pulse[id] = max_us

def servo_get_pulse(id: int32) -> int32:
    """Get current pulse width for servo.

    Args:
        id: Servo ID (0-7)

    Returns:
        Pulse width in microseconds
    """
    if id < 0 or id >= SERVO_MAX:
        return 0

    angle: int32 = _servo_angle[id]
    min_p: int32 = _servo_min_pulse[id]
    max_p: int32 = _servo_max_pulse[id]

    # Linear interpolation: pulse = min + (max - min) * angle / 180
    return min_p + ((max_p - min_p) * angle) / 180

def servo_is_moving(id: int32) -> bool:
    """Check if servo is still moving to target (smooth mode).

    Args:
        id: Servo ID (0-7)

    Returns:
        True if servo hasn't reached target
    """
    if id < 0 or id >= SERVO_MAX:
        return False
    return _servo_angle[id] != _servo_target[id]

def servo_update(id: int32):
    """Update servo position (for smooth movement).

    Call this periodically when using smooth mode.

    Args:
        id: Servo ID (0-7)
    """
    if id < 0 or id >= SERVO_MAX:
        return
    if not _servo_smooth[id]:
        return

    current: int32 = _servo_angle[id]
    target: int32 = _servo_target[id]
    speed: int32 = _servo_speed[id]

    if current == target:
        return

    diff: int32 = target - current
    step: int32 = clamp(abs_int(diff), 1, speed)

    if diff > 0:
        _servo_angle[id] = current + step
    else:
        _servo_angle[id] = current - step

def servo_update_all():
    """Update all servos (for smooth movement)."""
    i: int32 = 0
    while i < SERVO_MAX:
        if _servo_initialized[i]:
            servo_update(i)
        i = i + 1

# ============================================================================
# Stepper Motor
# ============================================================================
# Bipolar or unipolar stepper motor with full/half step modes
# Tracks position in steps from origin

# Maximum steppers supported
STEPPER_MAX: int32 = 4

# Step modes
STEPPER_MODE_FULL: int32 = 0    # Full step (4 phases)
STEPPER_MODE_HALF: int32 = 1    # Half step (8 phases)

# Direction
STEPPER_DIR_CW: int32 = 1       # Clockwise
STEPPER_DIR_CCW: int32 = -1     # Counter-clockwise

# Stepper state
_stepper_initialized: Array[4, bool]
_stepper_position: Array[4, int32]      # Current position in steps
_stepper_phase: Array[4, int32]         # Current phase (0-3 or 0-7)
_stepper_mode: Array[4, int32]          # Step mode
_stepper_direction: Array[4, int32]     # Current direction
_stepper_steps_per_rev: Array[4, int32] # Steps per revolution
_stepper_speed: Array[4, int32]         # Speed (delay between steps)

# Full step phases (coil patterns)
# Each value represents which coils are energized (bits 0-3 = coils A, B, C, D)
_stepper_full_phases: Array[4, uint8]

# Half step phases
_stepper_half_phases: Array[8, uint8]

def _stepper_init_phases():
    """Initialize step phase patterns."""
    # Full step sequence: AB, BC, CD, DA
    _stepper_full_phases[0] = 0x03  # A+B
    _stepper_full_phases[1] = 0x06  # B+C
    _stepper_full_phases[2] = 0x0C  # C+D
    _stepper_full_phases[3] = 0x09  # D+A

    # Half step sequence
    _stepper_half_phases[0] = 0x01  # A
    _stepper_half_phases[1] = 0x03  # A+B
    _stepper_half_phases[2] = 0x02  # B
    _stepper_half_phases[3] = 0x06  # B+C
    _stepper_half_phases[4] = 0x04  # C
    _stepper_half_phases[5] = 0x0C  # C+D
    _stepper_half_phases[6] = 0x08  # D
    _stepper_half_phases[7] = 0x09  # D+A

def stepper_init(id: int32, steps_per_rev: int32):
    """Initialize a stepper motor.

    Args:
        id: Stepper ID (0-3)
        steps_per_rev: Steps per revolution (e.g., 200 for 1.8 degree motor)
    """
    if id < 0 or id >= STEPPER_MAX:
        return

    _stepper_init_phases()

    _stepper_initialized[id] = True
    _stepper_position[id] = 0
    _stepper_phase[id] = 0
    _stepper_mode[id] = STEPPER_MODE_FULL
    _stepper_direction[id] = STEPPER_DIR_CW
    _stepper_steps_per_rev[id] = steps_per_rev
    _stepper_speed[id] = 1000  # Default delay

    if _motor_debug:
        console_puts("Stepper ")
        console_print_int(id)
        console_puts(" initialized (")
        console_print_int(steps_per_rev)
        console_puts(" steps/rev)\n")

def stepper_set_mode(id: int32, mode: int32):
    """Set stepper step mode.

    Args:
        id: Stepper ID (0-3)
        mode: STEPPER_MODE_FULL or STEPPER_MODE_HALF
    """
    if id < 0 or id >= STEPPER_MAX:
        return
    _stepper_mode[id] = mode
    _stepper_phase[id] = 0  # Reset phase

def stepper_set_direction(id: int32, direction: int32):
    """Set stepper direction.

    Args:
        id: Stepper ID (0-3)
        direction: STEPPER_DIR_CW or STEPPER_DIR_CCW
    """
    if id < 0 or id >= STEPPER_MAX:
        return
    _stepper_direction[id] = direction

def stepper_set_speed(id: int32, speed: int32):
    """Set stepper speed (delay between steps).

    Lower values = faster movement.

    Args:
        id: Stepper ID (0-3)
        speed: Delay value (arbitrary units)
    """
    if id < 0 or id >= STEPPER_MAX:
        return
    _stepper_speed[id] = speed

def stepper_step(id: int32) -> uint8:
    """Execute one step.

    Args:
        id: Stepper ID (0-3)

    Returns:
        Coil pattern for this step
    """
    if id < 0 or id >= STEPPER_MAX:
        return 0
    if not _stepper_initialized[id]:
        stepper_init(id, 200)

    mode: int32 = _stepper_mode[id]
    direction: int32 = _stepper_direction[id]
    phase: int32 = _stepper_phase[id]
    pattern: uint8 = 0

    if mode == STEPPER_MODE_FULL:
        # Full step: 4 phases
        pattern = _stepper_full_phases[phase]
        phase = phase + direction
        if phase >= 4:
            phase = 0
        elif phase < 0:
            phase = 3
    else:
        # Half step: 8 phases
        pattern = _stepper_half_phases[phase]
        phase = phase + direction
        if phase >= 8:
            phase = 0
        elif phase < 0:
            phase = 7

    _stepper_phase[id] = phase
    _stepper_position[id] = _stepper_position[id] + direction

    return pattern

def stepper_steps(id: int32, count: int32):
    """Execute multiple steps.

    Args:
        id: Stepper ID (0-3)
        count: Number of steps (positive for current direction)
    """
    if id < 0 or id >= STEPPER_MAX:
        return
    if not _stepper_initialized[id]:
        stepper_init(id, 200)

    if count < 0:
        # Reverse direction for negative count
        old_dir: int32 = _stepper_direction[id]
        _stepper_direction[id] = -old_dir
        count = -count

        i: int32 = 0
        while i < count:
            stepper_step(id)
            i = i + 1

        _stepper_direction[id] = old_dir
    else:
        i: int32 = 0
        while i < count:
            stepper_step(id)
            i = i + 1

    if _motor_debug:
        console_puts("Stepper ")
        console_print_int(id)
        console_puts(" moved ")
        console_print_int(count)
        console_puts(" steps, position: ")
        console_print_int(_stepper_position[id])
        console_putc('\n')

def stepper_get_position(id: int32) -> int32:
    """Get current stepper position.

    Args:
        id: Stepper ID (0-3)

    Returns:
        Position in steps from origin
    """
    if id < 0 or id >= STEPPER_MAX:
        return 0
    return _stepper_position[id]

def stepper_set_position(id: int32, pos: int32):
    """Set stepper position (doesn't move motor).

    Args:
        id: Stepper ID (0-3)
        pos: New position value
    """
    if id < 0 or id >= STEPPER_MAX:
        return
    _stepper_position[id] = pos

def stepper_get_phase(id: int32) -> uint8:
    """Get current coil pattern.

    Args:
        id: Stepper ID (0-3)

    Returns:
        Current coil energization pattern
    """
    if id < 0 or id >= STEPPER_MAX:
        return 0

    mode: int32 = _stepper_mode[id]
    phase: int32 = _stepper_phase[id]

    if mode == STEPPER_MODE_FULL:
        return _stepper_full_phases[phase]
    else:
        return _stepper_half_phases[phase]

def stepper_rotate(id: int32, degrees: int32):
    """Rotate stepper by degrees.

    Args:
        id: Stepper ID (0-3)
        degrees: Degrees to rotate (positive = CW, negative = CCW)
    """
    if id < 0 or id >= STEPPER_MAX:
        return
    if not _stepper_initialized[id]:
        return

    steps_per_rev: int32 = _stepper_steps_per_rev[id]
    mode: int32 = _stepper_mode[id]

    # In half-step mode, we have 2x the resolution
    if mode == STEPPER_MODE_HALF:
        steps_per_rev = steps_per_rev * 2

    # Calculate steps: steps = degrees * steps_per_rev / 360
    steps: int32 = (degrees * steps_per_rev) / 360

    stepper_steps(id, steps)

def stepper_release(id: int32):
    """Release stepper (de-energize coils).

    Args:
        id: Stepper ID (0-3)
    """
    if id < 0 or id >= STEPPER_MAX:
        return

    if _motor_debug:
        console_puts("Stepper ")
        console_print_int(id)
        console_puts(" released (coils off)\n")

# ============================================================================
# DC Motor with PWM
# ============================================================================
# Brushed DC motor controlled by H-bridge with PWM speed control
# Speed: -100 to +100 (negative = reverse)

# Maximum DC motors supported
DC_MAX: int32 = 4

# DC motor state
_dc_initialized: Array[4, bool]
_dc_speed: Array[4, int32]      # Speed -100 to 100
_dc_braking: Array[4, bool]     # True if braking (vs coasting)
_dc_enabled: Array[4, bool]     # Motor enabled

def dc_init(id: int32):
    """Initialize a DC motor.

    Args:
        id: Motor ID (0-3)
    """
    if id < 0 or id >= DC_MAX:
        return

    _dc_initialized[id] = True
    _dc_speed[id] = 0
    _dc_braking[id] = False
    _dc_enabled[id] = True

    if _motor_debug:
        console_puts("DC motor ")
        console_print_int(id)
        console_puts(" initialized\n")

def dc_set_speed(id: int32, speed: int32):
    """Set DC motor speed.

    Args:
        id: Motor ID (0-3)
        speed: Speed -100 to 100 (negative = reverse)
    """
    if id < 0 or id >= DC_MAX:
        return
    if not _dc_initialized[id]:
        dc_init(id)

    speed = clamp(speed, -100, 100)
    _dc_speed[id] = speed
    _dc_braking[id] = False

    if _motor_debug:
        console_puts("DC motor ")
        console_print_int(id)
        console_puts(" speed: ")
        console_print_int(speed)
        console_puts("%\n")

def dc_get_speed(id: int32) -> int32:
    """Get current DC motor speed.

    Args:
        id: Motor ID (0-3)

    Returns:
        Speed -100 to 100
    """
    if id < 0 or id >= DC_MAX:
        return 0
    return _dc_speed[id]

def dc_brake(id: int32):
    """Apply brake to DC motor (active stopping).

    Args:
        id: Motor ID (0-3)
    """
    if id < 0 or id >= DC_MAX:
        return
    if not _dc_initialized[id]:
        return

    _dc_speed[id] = 0
    _dc_braking[id] = True

    if _motor_debug:
        console_puts("DC motor ")
        console_print_int(id)
        console_puts(" braking\n")

def dc_coast(id: int32):
    """Coast DC motor (passive stopping).

    Args:
        id: Motor ID (0-3)
    """
    if id < 0 or id >= DC_MAX:
        return
    if not _dc_initialized[id]:
        return

    _dc_speed[id] = 0
    _dc_braking[id] = False

    if _motor_debug:
        console_puts("DC motor ")
        console_print_int(id)
        console_puts(" coasting\n")

def dc_stop(id: int32):
    """Stop DC motor (alias for coast).

    Args:
        id: Motor ID (0-3)
    """
    dc_coast(id)

def dc_is_braking(id: int32) -> bool:
    """Check if motor is in braking mode.

    Args:
        id: Motor ID (0-3)

    Returns:
        True if braking
    """
    if id < 0 or id >= DC_MAX:
        return False
    return _dc_braking[id]

def dc_is_running(id: int32) -> bool:
    """Check if motor is running (non-zero speed).

    Args:
        id: Motor ID (0-3)

    Returns:
        True if motor is running
    """
    if id < 0 or id >= DC_MAX:
        return False
    return _dc_speed[id] != 0

def dc_get_direction(id: int32) -> int32:
    """Get motor direction.

    Args:
        id: Motor ID (0-3)

    Returns:
        1 for forward, -1 for reverse, 0 for stopped
    """
    if id < 0 or id >= DC_MAX:
        return 0
    return sign(_dc_speed[id])

def dc_enable(id: int32, enabled: bool):
    """Enable or disable motor.

    Args:
        id: Motor ID (0-3)
        enabled: True to enable motor driver
    """
    if id < 0 or id >= DC_MAX:
        return
    _dc_enabled[id] = enabled

    if _motor_debug:
        console_puts("DC motor ")
        console_print_int(id)
        if enabled:
            console_puts(" enabled\n")
        else:
            console_puts(" disabled\n")

def dc_is_enabled(id: int32) -> bool:
    """Check if motor is enabled.

    Args:
        id: Motor ID (0-3)

    Returns:
        True if enabled
    """
    if id < 0 or id >= DC_MAX:
        return False
    return _dc_enabled[id]

def dc_get_pwm_duty(id: int32) -> int32:
    """Get PWM duty cycle for motor.

    Args:
        id: Motor ID (0-3)

    Returns:
        PWM duty cycle 0-100
    """
    if id < 0 or id >= DC_MAX:
        return 0
    return abs_int(_dc_speed[id])

# ============================================================================
# Motor Status Summary
# ============================================================================

def motors_print_status():
    """Print status of all motors to console."""
    console_puts("=== Motor Status ===\n")

    # Servos
    i: int32 = 0
    while i < SERVO_MAX:
        if _servo_initialized[i]:
            console_puts("Servo ")
            console_print_int(i)
            console_puts(": angle=")
            console_print_int(_servo_angle[i])
            console_puts(", target=")
            console_print_int(_servo_target[i])
            console_putc('\n')
        i = i + 1

    # Steppers
    i = 0
    while i < STEPPER_MAX:
        if _stepper_initialized[i]:
            console_puts("Stepper ")
            console_print_int(i)
            console_puts(": pos=")
            console_print_int(_stepper_position[i])
            console_puts(", mode=")
            if _stepper_mode[i] == STEPPER_MODE_FULL:
                console_puts("full")
            else:
                console_puts("half")
            console_putc('\n')
        i = i + 1

    # DC motors
    i = 0
    while i < DC_MAX:
        if _dc_initialized[i]:
            console_puts("DC ")
            console_print_int(i)
            console_puts(": speed=")
            console_print_int(_dc_speed[i])
            console_puts("%")
            if _dc_braking[i]:
                console_puts(" (braking)")
            console_putc('\n')
        i = i + 1

    console_puts("====================\n")
