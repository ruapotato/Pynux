# State Machine Example
#
# Traffic light controller using finite state machine.
# Demonstrates: FSM library, GPIO, timer

from lib.io import console_puts, console_print_int
from lib.fsm import fsm_global_init, fsm_global_add_transition, fsm_global_process_event
from lib.fsm import fsm_global_get_state, fsm_global_set_state
from lib.peripherals import gpio_init, gpio_write
from kernel.timer import timer_get_ticks, timer_delay_ms

# States
STATE_RED: int32 = 0
STATE_RED_YELLOW: int32 = 1
STATE_GREEN: int32 = 2
STATE_YELLOW: int32 = 3

# Events
EVENT_TIMER: int32 = 0
EVENT_PEDESTRIAN: int32 = 1
EVENT_EMERGENCY: int32 = 2

# GPIO pins for lights (simulated)
PIN_RED: int32 = 0
PIN_YELLOW: int32 = 1
PIN_GREEN: int32 = 2

# Timing (in ticks for demo)
state_enter_time: int32 = 0

def traffic_state_name(state: int32) -> Ptr[char]:
    """Get human-readable state name."""
    if state == STATE_RED:
        return "RED"
    elif state == STATE_RED_YELLOW:
        return "RED+YELLOW"
    elif state == STATE_GREEN:
        return "GREEN"
    elif state == STATE_YELLOW:
        return "YELLOW"
    return "UNKNOWN"

def set_lights(red: int32, yellow: int32, green: int32):
    """Set traffic light outputs."""
    gpio_write(PIN_RED, red)
    gpio_write(PIN_YELLOW, yellow)
    gpio_write(PIN_GREEN, green)

    # Visual display
    console_puts("  Lights: [")
    if red:
        console_puts("R")
    else:
        console_puts("-")
    if yellow:
        console_puts("Y")
    else:
        console_puts("-")
    if green:
        console_puts("G")
    else:
        console_puts("-")
    console_puts("]\n")

def traffic_on_state_enter(state: int32):
    """Called when entering a new state."""
    global state_enter_time

    state_enter_time = timer_get_ticks()

    console_puts("\n-> Entering state: ")
    console_puts(traffic_state_name(state))
    console_puts("\n")

    if state == STATE_RED:
        set_lights(1, 0, 0)
    elif state == STATE_RED_YELLOW:
        set_lights(1, 1, 0)
    elif state == STATE_GREEN:
        set_lights(0, 0, 1)
    elif state == STATE_YELLOW:
        set_lights(0, 1, 0)

def traffic_init():
    """Initialize traffic light controller."""
    console_puts("Traffic Light: Initializing...\n")

    # Initialize GPIO for lights
    gpio_init(PIN_RED, 1)     # Output
    gpio_init(PIN_YELLOW, 1)  # Output
    gpio_init(PIN_GREEN, 1)   # Output

    # Initialize FSM starting at RED
    fsm_global_init(STATE_RED)

    # Add state transitions
    # RED -> timer -> RED_YELLOW (prepare to go)
    fsm_global_add_transition(STATE_RED, EVENT_TIMER, STATE_RED_YELLOW)

    # RED_YELLOW -> timer -> GREEN
    fsm_global_add_transition(STATE_RED_YELLOW, EVENT_TIMER, STATE_GREEN)

    # GREEN -> timer -> YELLOW (prepare to stop)
    fsm_global_add_transition(STATE_GREEN, EVENT_TIMER, STATE_YELLOW)

    # YELLOW -> timer -> RED
    fsm_global_add_transition(STATE_YELLOW, EVENT_TIMER, STATE_RED)

    # Emergency: any state -> RED
    fsm_global_add_transition(STATE_RED_YELLOW, EVENT_EMERGENCY, STATE_RED)
    fsm_global_add_transition(STATE_GREEN, EVENT_EMERGENCY, STATE_RED)
    fsm_global_add_transition(STATE_YELLOW, EVENT_EMERGENCY, STATE_RED)

    # Pedestrian button: extend RED or shorten GREEN
    fsm_global_add_transition(STATE_GREEN, EVENT_PEDESTRIAN, STATE_YELLOW)

    traffic_on_state_enter(STATE_RED)
    console_puts("Traffic Light: Ready\n")

def traffic_tick():
    """Process timer tick - advances FSM when appropriate."""
    state: int32 = fsm_global_get_state()
    elapsed: int32 = timer_get_ticks() - state_enter_time

    # State durations (ms)
    duration: int32 = 0
    if state == STATE_RED:
        duration = 3000
    elif state == STATE_RED_YELLOW:
        duration = 1000
    elif state == STATE_GREEN:
        duration = 4000
    elif state == STATE_YELLOW:
        duration = 2000

    if elapsed >= duration:
        old_state: int32 = state
        new_state: int32 = fsm_global_process_event(EVENT_TIMER)
        if new_state != old_state:
            traffic_on_state_enter(new_state)

def traffic_emergency():
    """Handle emergency event."""
    console_puts("\n!!! EMERGENCY !!!\n")
    old_state: int32 = fsm_global_get_state()
    new_state: int32 = fsm_global_process_event(EVENT_EMERGENCY)
    if new_state != old_state:
        traffic_on_state_enter(new_state)

def traffic_pedestrian():
    """Handle pedestrian button press."""
    console_puts("\n[Pedestrian button pressed]\n")
    old_state: int32 = fsm_global_get_state()
    new_state: int32 = fsm_global_process_event(EVENT_PEDESTRIAN)
    if new_state != old_state:
        traffic_on_state_enter(new_state)

def statemachine_main(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    """Standalone demo mode."""
    traffic_init()

    console_puts("\n=== Traffic Light Demo ===\n")
    console_puts("Running through 2 complete cycles...\n")

    # Run through states
    cycles: int32 = 0
    ticks: int32 = 0
    while cycles < 2:
        traffic_tick()

        # Track cycle completion (back to RED)
        if fsm_global_get_state() == STATE_RED and ticks > 0:
            prev_ticks: int32 = ticks - 1
            if prev_ticks > 0:
                cycles = cycles + 1
                console_puts("\n--- Cycle ")
                console_print_int(cycles)
                console_puts(" complete ---\n")

        timer_delay_ms(100)
        ticks = ticks + 1

        # Demo pedestrian button in second cycle
        if cycles == 1 and ticks == 5:
            traffic_pedestrian()

    console_puts("\nDemo complete.\n")
    return 0
