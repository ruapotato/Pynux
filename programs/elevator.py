# Elevator Controller
#
# Complex state machine example with multiple states and events.
# Demonstrates FSM, sensors, motors, and real-time control.

from lib.io import console_puts, console_print_int
from lib.fsm import fsm_global_init, fsm_global_add_transition, fsm_global_process_event, fsm_global_get_state
from lib.motors import dc_init, dc_set_speed, dc_brake
from kernel.timer import timer_get_ticks, timer_delay_ms

# Floor range
MIN_FLOOR: int32 = 1
MAX_FLOOR: int32 = 5

# States
STATE_IDLE: int32 = 0
STATE_MOVING_UP: int32 = 1
STATE_MOVING_DOWN: int32 = 2
STATE_DOOR_OPENING: int32 = 3
STATE_DOOR_OPEN: int32 = 4
STATE_DOOR_CLOSING: int32 = 5
STATE_EMERGENCY: int32 = 6

# Events
EVENT_CALL_UP: int32 = 0
EVENT_CALL_DOWN: int32 = 1
EVENT_FLOOR_REACHED: int32 = 2
EVENT_DOOR_OPENED: int32 = 3
EVENT_DOOR_CLOSED: int32 = 4
EVENT_TIMEOUT: int32 = 5
EVENT_EMERGENCY_STOP: int32 = 6
EVENT_EMERGENCY_CLEAR: int32 = 7

# Elevator state
current_floor: int32 = 1
target_floor: int32 = 1
door_timer: int32 = 0
DOOR_OPEN_TIME: int32 = 3000  # 3 seconds

# Call buttons (bitmap)
up_calls: int32 = 0
down_calls: int32 = 0

def state_name(state: int32) -> Ptr[char]:
    """Get state name string."""
    if state == STATE_IDLE:
        return "IDLE"
    elif state == STATE_MOVING_UP:
        return "MOVING_UP"
    elif state == STATE_MOVING_DOWN:
        return "MOVING_DOWN"
    elif state == STATE_DOOR_OPENING:
        return "DOOR_OPENING"
    elif state == STATE_DOOR_OPEN:
        return "DOOR_OPEN"
    elif state == STATE_DOOR_CLOSING:
        return "DOOR_CLOSING"
    elif state == STATE_EMERGENCY:
        return "EMERGENCY"
    return "UNKNOWN"

def set_call(floor: int32, direction: int32):
    """Register a call button press."""
    global up_calls, down_calls
    bit: int32 = 1 << floor
    if direction > 0:
        up_calls = up_calls | bit
    else:
        down_calls = down_calls | bit

def clear_call(floor: int32):
    """Clear calls for a floor."""
    global up_calls, down_calls
    mask: int32 = ~(1 << floor)
    up_calls = up_calls & mask
    down_calls = down_calls & mask

def has_call(floor: int32) -> bool:
    """Check if floor has any call."""
    bit: int32 = 1 << floor
    return ((up_calls | down_calls) & bit) != 0

def find_next_target() -> int32:
    """Find next floor to service."""
    global current_floor

    # Check current floor first
    if has_call(current_floor):
        return current_floor

    # Look up
    f: int32 = current_floor + 1
    while f <= MAX_FLOOR:
        if has_call(f):
            return f
        f = f + 1

    # Look down
    f = current_floor - 1
    while f >= MIN_FLOOR:
        if has_call(f):
            return f
        f = f - 1

    return current_floor  # No calls pending

def on_state_enter(state: int32):
    """Handle state entry actions."""
    global door_timer

    console_puts("\n[Elevator] -> ")
    console_puts(state_name(state))
    console_puts(" (Floor ")
    console_print_int(current_floor)
    console_puts(")\n")

    if state == STATE_MOVING_UP:
        console_puts("  Motor: UP\n")
        dc_set_speed(0, 50)
    elif state == STATE_MOVING_DOWN:
        console_puts("  Motor: DOWN\n")
        dc_set_speed(0, -50)
    elif state == STATE_DOOR_OPENING:
        console_puts("  Opening door...\n")
        dc_brake(0)
    elif state == STATE_DOOR_OPEN:
        door_timer = timer_get_ticks()
        clear_call(current_floor)
        console_puts("  Door OPEN - waiting...\n")
    elif state == STATE_DOOR_CLOSING:
        console_puts("  Closing door...\n")
    elif state == STATE_IDLE:
        dc_brake(0)
        console_puts("  Waiting for calls\n")
    elif state == STATE_EMERGENCY:
        dc_brake(0)
        console_puts("  !!! EMERGENCY STOP !!!\n")

def elevator_init():
    """Initialize elevator system."""
    global current_floor, target_floor

    console_puts("=== Elevator Controller ===\n")
    console_puts("Floors: ")
    console_print_int(MIN_FLOOR)
    console_puts(" to ")
    console_print_int(MAX_FLOOR)
    console_puts("\n\n")

    # Initialize motor
    dc_init(0)

    # Initialize FSM
    fsm_global_init(STATE_IDLE)

    # Define transitions
    # IDLE
    fsm_global_add_transition(STATE_IDLE, EVENT_CALL_UP, STATE_MOVING_UP)
    fsm_global_add_transition(STATE_IDLE, EVENT_CALL_DOWN, STATE_MOVING_DOWN)
    fsm_global_add_transition(STATE_IDLE, EVENT_FLOOR_REACHED, STATE_DOOR_OPENING)

    # MOVING_UP
    fsm_global_add_transition(STATE_MOVING_UP, EVENT_FLOOR_REACHED, STATE_DOOR_OPENING)
    fsm_global_add_transition(STATE_MOVING_UP, EVENT_EMERGENCY_STOP, STATE_EMERGENCY)

    # MOVING_DOWN
    fsm_global_add_transition(STATE_MOVING_DOWN, EVENT_FLOOR_REACHED, STATE_DOOR_OPENING)
    fsm_global_add_transition(STATE_MOVING_DOWN, EVENT_EMERGENCY_STOP, STATE_EMERGENCY)

    # DOOR_OPENING
    fsm_global_add_transition(STATE_DOOR_OPENING, EVENT_DOOR_OPENED, STATE_DOOR_OPEN)
    fsm_global_add_transition(STATE_DOOR_OPENING, EVENT_EMERGENCY_STOP, STATE_EMERGENCY)

    # DOOR_OPEN
    fsm_global_add_transition(STATE_DOOR_OPEN, EVENT_TIMEOUT, STATE_DOOR_CLOSING)
    fsm_global_add_transition(STATE_DOOR_OPEN, EVENT_EMERGENCY_STOP, STATE_EMERGENCY)

    # DOOR_CLOSING
    fsm_global_add_transition(STATE_DOOR_CLOSING, EVENT_DOOR_CLOSED, STATE_IDLE)
    fsm_global_add_transition(STATE_DOOR_CLOSING, EVENT_EMERGENCY_STOP, STATE_EMERGENCY)

    # EMERGENCY
    fsm_global_add_transition(STATE_EMERGENCY, EVENT_EMERGENCY_CLEAR, STATE_IDLE)

    current_floor = 1
    target_floor = 1

    on_state_enter(STATE_IDLE)

def elevator_tick():
    """Process one tick of elevator logic."""
    global current_floor, target_floor

    state: int32 = fsm_global_get_state()
    old_state: int32 = state
    new_state: int32 = state

    if state == STATE_IDLE:
        # Check for pending calls
        target_floor = find_next_target()
        if target_floor > current_floor:
            new_state = fsm_global_process_event(EVENT_CALL_UP)
        elif target_floor < current_floor:
            new_state = fsm_global_process_event(EVENT_CALL_DOWN)
        elif has_call(current_floor):
            new_state = fsm_global_process_event(EVENT_FLOOR_REACHED)

    elif state == STATE_MOVING_UP:
        # Simulate reaching next floor
        current_floor = current_floor + 1
        console_puts("  Passing floor ")
        console_print_int(current_floor)
        console_puts("\n")

        if current_floor >= target_floor or has_call(current_floor):
            new_state = fsm_global_process_event(EVENT_FLOOR_REACHED)

    elif state == STATE_MOVING_DOWN:
        current_floor = current_floor - 1
        console_puts("  Passing floor ")
        console_print_int(current_floor)
        console_puts("\n")

        if current_floor <= target_floor or has_call(current_floor):
            new_state = fsm_global_process_event(EVENT_FLOOR_REACHED)

    elif state == STATE_DOOR_OPENING:
        # Simulate door opening
        new_state = fsm_global_process_event(EVENT_DOOR_OPENED)

    elif state == STATE_DOOR_OPEN:
        # Check timeout
        elapsed: int32 = timer_get_ticks() - door_timer
        if elapsed >= DOOR_OPEN_TIME:
            new_state = fsm_global_process_event(EVENT_TIMEOUT)

    elif state == STATE_DOOR_CLOSING:
        # Simulate door closing
        new_state = fsm_global_process_event(EVENT_DOOR_CLOSED)

    if new_state != old_state:
        on_state_enter(new_state)

def elevator_call(floor: int32, direction: int32):
    """External call button press."""
    console_puts("\n[Call] Floor ")
    console_print_int(floor)
    if direction > 0:
        console_puts(" UP\n")
    else:
        console_puts(" DOWN\n")
    set_call(floor, direction)

def elevator_main(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    """Demo: Simulate elevator operation."""
    elevator_init()

    console_puts("\n=== Simulation Start ===\n")

    # Simulate calls
    elevator_call(3, 1)   # Floor 3, going up
    elevator_call(5, -1)  # Floor 5, going down

    # Run simulation
    ticks: int32 = 0
    while ticks < 30:
        elevator_tick()
        timer_delay_ms(100)
        ticks = ticks + 1

        # Add more calls during simulation
        if ticks == 10:
            elevator_call(2, 1)

    console_puts("\n=== Simulation Complete ===\n")
    return 0
