# Pynux Finite State Machine Library
#
# Event-driven finite state machine for bare-metal ARM.
# Supports state enter/exit callbacks, transition conditions,
# timeout transitions, and hierarchical states.
#
# Usage:
#   1. Define states with fsm_add_state()
#   2. Define transitions with fsm_add_transition()
#   3. Initialize FSM with fsm_init()
#   4. Call fsm_process_event() or fsm_update() in main loop

from lib.memory import alloc, free

# ============================================================================
# Constants
# ============================================================================

# Maximum number of states per FSM
FSM_MAX_STATES: int32 = 16

# Maximum number of transitions per FSM
FSM_MAX_TRANSITIONS: int32 = 32

# Special event codes
FSM_EVENT_NONE: int32 = 0
FSM_EVENT_ENTER: int32 = -1    # Internal: state entered
FSM_EVENT_EXIT: int32 = -2     # Internal: state exited
FSM_EVENT_TIMEOUT: int32 = -3  # Timeout event
FSM_EVENT_UPDATE: int32 = -4   # Periodic update event

# State IDs
FSM_STATE_NONE: int32 = -1     # No state / invalid

# Transition condition results
FSM_COND_FALSE: int32 = 0
FSM_COND_TRUE: int32 = 1

# ============================================================================
# State Structure
# ============================================================================
#
# Layout (per state):
#   id: int32           - State ID (offset 0)
#   parent: int32       - Parent state ID for hierarchy, -1 if none (offset 4)
#   on_enter: int32     - Enter callback function pointer (offset 8)
#   on_exit: int32      - Exit callback function pointer (offset 12)
#   on_update: int32    - Update callback function pointer (offset 16)
#   timeout_ms: int32   - Timeout in milliseconds, 0 = no timeout (offset 20)
#   timeout_next: int32 - State to transition to on timeout (offset 24)
# Total: 28 bytes per state

STATE_ID_OFFSET: int32 = 0
STATE_PARENT_OFFSET: int32 = 4
STATE_ON_ENTER_OFFSET: int32 = 8
STATE_ON_EXIT_OFFSET: int32 = 12
STATE_ON_UPDATE_OFFSET: int32 = 16
STATE_TIMEOUT_MS_OFFSET: int32 = 20
STATE_TIMEOUT_NEXT_OFFSET: int32 = 24
STATE_STRUCT_SIZE: int32 = 28

# ============================================================================
# Transition Structure
# ============================================================================
#
# Layout (per transition):
#   from_state: int32   - Source state ID (offset 0)
#   to_state: int32     - Destination state ID (offset 4)
#   event: int32        - Event that triggers this transition (offset 8)
#   condition: int32    - Condition function pointer, 0 = always true (offset 12)
#   action: int32       - Action function pointer, 0 = no action (offset 16)
# Total: 20 bytes per transition

TRANS_FROM_OFFSET: int32 = 0
TRANS_TO_OFFSET: int32 = 4
TRANS_EVENT_OFFSET: int32 = 8
TRANS_COND_OFFSET: int32 = 12
TRANS_ACTION_OFFSET: int32 = 16
TRANS_STRUCT_SIZE: int32 = 20

# ============================================================================
# FSM Structure
# ============================================================================
#
# Layout:
#   current_state: int32     - Current state ID (offset 0)
#   num_states: int32        - Number of registered states (offset 4)
#   num_transitions: int32   - Number of registered transitions (offset 8)
#   state_enter_time: int32  - Tick when current state was entered (offset 12)
#   current_tick: int32      - Current system tick (offset 16)
#   states: Ptr[int32]       - Pointer to states array (offset 20)
#   transitions: Ptr[int32]  - Pointer to transitions array (offset 24)
#   user_data: int32         - User data pointer (offset 28)
# Total: 32 bytes

FSM_CURRENT_STATE_OFFSET: int32 = 0
FSM_NUM_STATES_OFFSET: int32 = 4
FSM_NUM_TRANS_OFFSET: int32 = 8
FSM_STATE_ENTER_TIME_OFFSET: int32 = 12
FSM_CURRENT_TICK_OFFSET: int32 = 16
FSM_STATES_PTR_OFFSET: int32 = 20
FSM_TRANS_PTR_OFFSET: int32 = 24
FSM_USER_DATA_OFFSET: int32 = 28
FSM_STRUCT_SIZE: int32 = 32

# ============================================================================
# FSM Initialization and Cleanup
# ============================================================================

def fsm_create() -> Ptr[int32]:
    """Create a new FSM instance.

    Returns:
        Pointer to FSM structure, or null on allocation failure.
    """
    # Allocate FSM structure
    fsm: Ptr[int32] = cast[Ptr[int32]](alloc(FSM_STRUCT_SIZE))
    if cast[uint32](fsm) == 0:
        return cast[Ptr[int32]](0)

    # Allocate states array
    states: Ptr[int32] = cast[Ptr[int32]](alloc(FSM_MAX_STATES * STATE_STRUCT_SIZE))
    if cast[uint32](states) == 0:
        free(cast[Ptr[uint8]](fsm))
        return cast[Ptr[int32]](0)

    # Allocate transitions array
    trans: Ptr[int32] = cast[Ptr[int32]](alloc(FSM_MAX_TRANSITIONS * TRANS_STRUCT_SIZE))
    if cast[uint32](trans) == 0:
        free(cast[Ptr[uint8]](states))
        free(cast[Ptr[uint8]](fsm))
        return cast[Ptr[int32]](0)

    # Initialize FSM
    fsm[0] = FSM_STATE_NONE  # current_state
    fsm[1] = 0               # num_states
    fsm[2] = 0               # num_transitions
    fsm[3] = 0               # state_enter_time
    fsm[4] = 0               # current_tick
    fsm[5] = cast[int32](states)
    fsm[6] = cast[int32](trans)
    fsm[7] = 0               # user_data

    return fsm

def fsm_destroy(fsm: Ptr[int32]):
    """Destroy FSM and free all memory.

    Args:
        fsm: Pointer to FSM structure
    """
    if cast[uint32](fsm) == 0:
        return

    # Free states array
    states: Ptr[int32] = cast[Ptr[int32]](fsm[5])
    if cast[uint32](states) != 0:
        free(cast[Ptr[uint8]](states))

    # Free transitions array
    trans: Ptr[int32] = cast[Ptr[int32]](fsm[6])
    if cast[uint32](trans) != 0:
        free(cast[Ptr[uint8]](trans))

    # Free FSM structure
    free(cast[Ptr[uint8]](fsm))

def fsm_set_user_data(fsm: Ptr[int32], data: int32):
    """Set user data pointer for callbacks.

    Args:
        fsm: Pointer to FSM structure
        data: User data (cast pointer to int32)
    """
    fsm[7] = data

def fsm_get_user_data(fsm: Ptr[int32]) -> int32:
    """Get user data pointer.

    Args:
        fsm: Pointer to FSM structure

    Returns:
        User data as int32 (cast back to pointer as needed)
    """
    return fsm[7]

# ============================================================================
# State Management
# ============================================================================

def _fsm_get_state(fsm: Ptr[int32], state_id: int32) -> Ptr[int32]:
    """Get pointer to state structure by ID.

    Returns null if not found.
    """
    states: Ptr[int32] = cast[Ptr[int32]](fsm[5])
    num_states: int32 = fsm[1]

    i: int32 = 0
    while i < num_states:
        base: int32 = i * (STATE_STRUCT_SIZE / 4)
        if states[base + 0] == state_id:
            return cast[Ptr[int32]](cast[uint32](states) + cast[uint32](base * 4))
        i = i + 1

    return cast[Ptr[int32]](0)

def fsm_add_state(fsm: Ptr[int32], state_id: int32, parent_id: int32,
                   on_enter: int32, on_exit: int32, on_update: int32) -> bool:
    """Add a state to the FSM.

    Args:
        fsm: Pointer to FSM structure
        state_id: Unique state identifier
        parent_id: Parent state ID for hierarchy (-1 for none)
        on_enter: Enter callback function pointer (0 for none)
        on_exit: Exit callback function pointer (0 for none)
        on_update: Update callback function pointer (0 for none)

    Returns:
        True on success, False if FSM is full or state exists
    """
    num_states: int32 = fsm[1]

    # Check capacity
    if num_states >= FSM_MAX_STATES:
        return False

    # Check if state already exists
    if cast[uint32](_fsm_get_state(fsm, state_id)) != 0:
        return False

    # Add new state
    states: Ptr[int32] = cast[Ptr[int32]](fsm[5])
    base: int32 = num_states * (STATE_STRUCT_SIZE / 4)

    states[base + 0] = state_id    # id
    states[base + 1] = parent_id   # parent
    states[base + 2] = on_enter    # on_enter
    states[base + 3] = on_exit     # on_exit
    states[base + 4] = on_update   # on_update
    states[base + 5] = 0           # timeout_ms
    states[base + 6] = FSM_STATE_NONE  # timeout_next

    fsm[1] = num_states + 1
    return True

def fsm_set_state_timeout(fsm: Ptr[int32], state_id: int32,
                          timeout_ms: int32, next_state: int32) -> bool:
    """Set timeout for a state.

    When the state has been active for timeout_ms, automatically
    transition to next_state.

    Args:
        fsm: Pointer to FSM structure
        state_id: State to set timeout for
        timeout_ms: Timeout in milliseconds (0 to disable)
        next_state: State to transition to on timeout

    Returns:
        True on success, False if state not found
    """
    state: Ptr[int32] = _fsm_get_state(fsm, state_id)
    if cast[uint32](state) == 0:
        return False

    state[5] = timeout_ms
    state[6] = next_state
    return True

# ============================================================================
# Transition Management
# ============================================================================

def fsm_add_transition(fsm: Ptr[int32], from_state: int32, to_state: int32,
                       event: int32, condition: int32, action: int32) -> bool:
    """Add a transition to the FSM.

    Args:
        fsm: Pointer to FSM structure
        from_state: Source state ID
        to_state: Destination state ID
        event: Event that triggers this transition
        condition: Condition function pointer (0 = always true)
                   Signature: fn(fsm: Ptr[int32]) -> int32
        action: Action function pointer (0 = no action)
                Signature: fn(fsm: Ptr[int32])

    Returns:
        True on success, False if FSM transitions array is full
    """
    num_trans: int32 = fsm[2]

    # Check capacity
    if num_trans >= FSM_MAX_TRANSITIONS:
        return False

    # Add new transition
    trans: Ptr[int32] = cast[Ptr[int32]](fsm[6])
    base: int32 = num_trans * (TRANS_STRUCT_SIZE / 4)

    trans[base + 0] = from_state
    trans[base + 1] = to_state
    trans[base + 2] = event
    trans[base + 3] = condition
    trans[base + 4] = action

    fsm[2] = num_trans + 1
    return True

# ============================================================================
# State Transitions
# ============================================================================

def _fsm_call_callback(callback: int32, fsm: Ptr[int32]):
    """Call a state callback if not null."""
    if callback != 0:
        # Cast to function pointer and call
        fn: Fn[void, Ptr[int32]] = cast[Fn[void, Ptr[int32]]](callback)
        fn(fsm)

def _fsm_call_condition(condition: int32, fsm: Ptr[int32]) -> int32:
    """Call a condition function if not null."""
    if condition == 0:
        return FSM_COND_TRUE

    fn: Fn[int32, Ptr[int32]] = cast[Fn[int32, Ptr[int32]]](condition)
    return fn(fsm)

def _fsm_exit_state(fsm: Ptr[int32], state_id: int32):
    """Exit a state and all parent states if hierarchical."""
    if state_id == FSM_STATE_NONE:
        return

    state: Ptr[int32] = _fsm_get_state(fsm, state_id)
    if cast[uint32](state) == 0:
        return

    # Call exit callback
    _fsm_call_callback(state[3], fsm)

    # Exit parent state if hierarchical
    parent_id: int32 = state[1]
    if parent_id != FSM_STATE_NONE:
        _fsm_exit_state(fsm, parent_id)

def _fsm_enter_state(fsm: Ptr[int32], state_id: int32):
    """Enter a state and all parent states if hierarchical."""
    if state_id == FSM_STATE_NONE:
        return

    state: Ptr[int32] = _fsm_get_state(fsm, state_id)
    if cast[uint32](state) == 0:
        return

    # Enter parent state first if hierarchical
    parent_id: int32 = state[1]
    if parent_id != FSM_STATE_NONE:
        _fsm_enter_state(fsm, parent_id)

    # Call enter callback
    _fsm_call_callback(state[2], fsm)

def fsm_transition_to(fsm: Ptr[int32], new_state: int32) -> bool:
    """Force transition to a new state.

    Calls exit callback on current state and enter callback on new state.

    Args:
        fsm: Pointer to FSM structure
        new_state: State ID to transition to

    Returns:
        True on success, False if new_state doesn't exist
    """
    # Verify new state exists
    if cast[uint32](_fsm_get_state(fsm, new_state)) == 0:
        return False

    current: int32 = fsm[0]

    # Exit current state
    if current != FSM_STATE_NONE:
        _fsm_exit_state(fsm, current)

    # Update state
    fsm[0] = new_state
    fsm[3] = fsm[4]  # Record state enter time

    # Enter new state
    _fsm_enter_state(fsm, new_state)

    return True

def fsm_init(fsm: Ptr[int32], initial_state: int32) -> bool:
    """Initialize FSM with initial state.

    Args:
        fsm: Pointer to FSM structure
        initial_state: Initial state ID

    Returns:
        True on success, False if initial_state doesn't exist
    """
    fsm[0] = FSM_STATE_NONE
    fsm[3] = 0
    fsm[4] = 0

    return fsm_transition_to(fsm, initial_state)

# ============================================================================
# Event Processing
# ============================================================================

def fsm_process_event(fsm: Ptr[int32], event: int32) -> bool:
    """Process an event and perform transitions if applicable.

    Searches for a matching transition from the current state
    with the given event, checks condition, and performs transition.

    Args:
        fsm: Pointer to FSM structure
        event: Event code to process

    Returns:
        True if a transition occurred, False otherwise
    """
    current: int32 = fsm[0]
    if current == FSM_STATE_NONE:
        return False

    trans: Ptr[int32] = cast[Ptr[int32]](fsm[6])
    num_trans: int32 = fsm[2]

    # Search for matching transition
    i: int32 = 0
    while i < num_trans:
        base: int32 = i * (TRANS_STRUCT_SIZE / 4)
        from_state: int32 = trans[base + 0]
        to_state: int32 = trans[base + 1]
        trans_event: int32 = trans[base + 2]
        condition: int32 = trans[base + 3]
        action: int32 = trans[base + 4]

        # Check if transition matches
        if from_state == current and trans_event == event:
            # Check condition
            if _fsm_call_condition(condition, fsm) == FSM_COND_TRUE:
                # Call action before transition
                _fsm_call_callback(action, fsm)

                # Perform transition
                fsm_transition_to(fsm, to_state)
                return True

        i = i + 1

    return False

def fsm_update(fsm: Ptr[int32], tick_ms: int32):
    """Update FSM with current time tick.

    Handles timeouts and calls state update callbacks.
    Call this regularly from main loop.

    Args:
        fsm: Pointer to FSM structure
        tick_ms: Current system time in milliseconds
    """
    fsm[4] = tick_ms
    current: int32 = fsm[0]

    if current == FSM_STATE_NONE:
        return

    state: Ptr[int32] = _fsm_get_state(fsm, current)
    if cast[uint32](state) == 0:
        return

    # Check for timeout
    timeout_ms: int32 = state[5]
    if timeout_ms > 0:
        elapsed: int32 = tick_ms - fsm[3]
        if elapsed >= timeout_ms:
            # Timeout occurred
            next_state: int32 = state[6]
            if next_state != FSM_STATE_NONE:
                # Generate timeout event for transition
                fsm_process_event(fsm, FSM_EVENT_TIMEOUT)
                # If no timeout transition defined, force transition
                if fsm[0] == current:
                    fsm_transition_to(fsm, next_state)
                return

    # Call update callback
    _fsm_call_callback(state[4], fsm)

# ============================================================================
# Query Functions
# ============================================================================

def fsm_get_current_state(fsm: Ptr[int32]) -> int32:
    """Get current state ID.

    Args:
        fsm: Pointer to FSM structure

    Returns:
        Current state ID, or FSM_STATE_NONE if not initialized
    """
    return fsm[0]

def fsm_get_state_time(fsm: Ptr[int32]) -> int32:
    """Get time in current state.

    Args:
        fsm: Pointer to FSM structure

    Returns:
        Milliseconds since entering current state
    """
    return fsm[4] - fsm[3]

def fsm_is_in_state(fsm: Ptr[int32], state_id: int32) -> bool:
    """Check if FSM is in a specific state.

    For hierarchical states, also returns true if in a child state.

    Args:
        fsm: Pointer to FSM structure
        state_id: State ID to check

    Returns:
        True if in state or child of state
    """
    current: int32 = fsm[0]

    while current != FSM_STATE_NONE:
        if current == state_id:
            return True

        # Check parent
        state: Ptr[int32] = _fsm_get_state(fsm, current)
        if cast[uint32](state) == 0:
            break
        current = state[1]  # parent

    return False

# ============================================================================
# Example: Traffic Light FSM
# ============================================================================
#
# States:
#   STATE_RED = 0       (30 second duration)
#   STATE_GREEN = 1     (25 second duration)
#   STATE_YELLOW = 2    (5 second duration)
#
# Transitions (all timeout-based):
#   RED -> GREEN (timeout)
#   GREEN -> YELLOW (timeout)
#   YELLOW -> RED (timeout)
#
# Usage:
#   fsm: Ptr[int32] = fsm_create()
#
#   # Add states
#   fsm_add_state(fsm, 0, -1, on_red_enter, on_red_exit, 0)
#   fsm_add_state(fsm, 1, -1, on_green_enter, on_green_exit, 0)
#   fsm_add_state(fsm, 2, -1, on_yellow_enter, on_yellow_exit, 0)
#
#   # Set timeouts
#   fsm_set_state_timeout(fsm, 0, 30000, 1)  # RED -> GREEN after 30s
#   fsm_set_state_timeout(fsm, 1, 25000, 2)  # GREEN -> YELLOW after 25s
#   fsm_set_state_timeout(fsm, 2, 5000, 0)   # YELLOW -> RED after 5s
#
#   # Initialize
#   fsm_init(fsm, 0)  # Start in RED
#
#   # Main loop
#   while True:
#       tick: int32 = get_system_tick_ms()
#       fsm_update(fsm, tick)
#
# ============================================================================
# Example: Door Lock FSM
# ============================================================================
#
# States:
#   STATE_LOCKED = 0
#   STATE_UNLOCKED = 1
#   STATE_ERROR = 2
#
# Events:
#   EVENT_CORRECT_CODE = 1
#   EVENT_WRONG_CODE = 2
#   EVENT_LOCK_BUTTON = 3
#   EVENT_TIMEOUT = FSM_EVENT_TIMEOUT
#
# Transitions:
#   LOCKED + CORRECT_CODE -> UNLOCKED
#   LOCKED + WRONG_CODE -> ERROR (with attempt counter condition)
#   UNLOCKED + LOCK_BUTTON -> LOCKED
#   UNLOCKED + TIMEOUT -> LOCKED (auto-lock after 30s)
#   ERROR + TIMEOUT -> LOCKED (cooldown)
#
# Usage:
#   fsm: Ptr[int32] = fsm_create()
#
#   # Add states
#   fsm_add_state(fsm, 0, -1, on_locked_enter, 0, 0)
#   fsm_add_state(fsm, 1, -1, on_unlocked_enter, 0, 0)
#   fsm_add_state(fsm, 2, -1, on_error_enter, 0, 0)
#
#   # Add transitions
#   fsm_add_transition(fsm, 0, 1, 1, 0, unlock_action)       # LOCKED -> UNLOCKED
#   fsm_add_transition(fsm, 0, 2, 2, too_many_attempts, 0)   # LOCKED -> ERROR
#   fsm_add_transition(fsm, 1, 0, 3, 0, lock_action)         # UNLOCKED -> LOCKED
#
#   # Set timeouts
#   fsm_set_state_timeout(fsm, 1, 30000, 0)  # Auto-lock after 30s
#   fsm_set_state_timeout(fsm, 2, 10000, 0)  # Error cooldown 10s
#
#   # Initialize
#   fsm_init(fsm, 0)  # Start locked
