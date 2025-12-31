# Pynux FSM Tests
#
# Tests for finite state machine library.

from tests.test_framework import (
    assert_true, assert_false, assert_eq, assert_neq,
    assert_gt, assert_gte, print_section, print_results, reset_counters
)
from lib.io import print_str, print_newline
from lib.fsm import fsm_simple_init, fsm_add_transition_simple, fsm_process_event_simple
from lib.fsm import fsm_simple_get_state, fsm_simple_set_state, fsm_simple_reset

# Test states
FSM_STATE_IDLE: int32 = 0
FSM_STATE_RUNNING: int32 = 1
FSM_STATE_PAUSED: int32 = 2
FSM_STATE_STOPPED: int32 = 3

# Test events
EVENT_START: int32 = 0
EVENT_PAUSE: int32 = 1
EVENT_RESUME: int32 = 2
EVENT_STOP: int32 = 3

def test_fsm_simple_init():
    print_section("FSM Initialization")

    fsm_simple_init(FSM_STATE_IDLE)
    assert_eq(fsm_simple_get_state(), FSM_STATE_IDLE, "initial state is IDLE")

    fsm_simple_init(FSM_STATE_RUNNING)
    assert_eq(fsm_simple_get_state(), FSM_STATE_RUNNING, "init with RUNNING")

def test_fsm_transitions():
    print_section("FSM Transitions")

    fsm_simple_init(FSM_STATE_IDLE)

    # Add transitions
    fsm_add_transition_simple(FSM_STATE_IDLE, EVENT_START, FSM_STATE_RUNNING)
    fsm_add_transition_simple(FSM_STATE_RUNNING, EVENT_PAUSE, FSM_STATE_PAUSED)
    fsm_add_transition_simple(FSM_STATE_PAUSED, EVENT_RESUME, FSM_STATE_RUNNING)
    fsm_add_transition_simple(FSM_STATE_RUNNING, EVENT_STOP, FSM_STATE_STOPPED)
    fsm_add_transition_simple(FSM_STATE_PAUSED, EVENT_STOP, FSM_STATE_STOPPED)

    # Test valid transitions
    new_state: int32 = fsm_process_event_simple(EVENT_START)
    assert_eq(new_state, FSM_STATE_RUNNING, "IDLE -> START -> RUNNING")

    new_state = fsm_process_event_simple(EVENT_PAUSE)
    assert_eq(new_state, FSM_STATE_PAUSED, "RUNNING -> PAUSE -> PAUSED")

    new_state = fsm_process_event_simple(EVENT_RESUME)
    assert_eq(new_state, FSM_STATE_RUNNING, "PAUSED -> RESUME -> RUNNING")

    new_state = fsm_process_event_simple(EVENT_STOP)
    assert_eq(new_state, FSM_STATE_STOPPED, "RUNNING -> STOP -> STOPPED")

def test_fsm_invalid_transition():
    print_section("Invalid Transitions")

    fsm_simple_init(FSM_STATE_IDLE)
    fsm_add_transition_simple(FSM_STATE_IDLE, EVENT_START, FSM_STATE_RUNNING)

    # Invalid event - should stay in current state
    old_state: int32 = fsm_simple_get_state()
    new_state: int32 = fsm_process_event_simple(EVENT_PAUSE)  # No transition defined
    assert_eq(new_state, old_state, "invalid event stays in state")

def test_fsm_simple_set_state():
    print_section("Set State Directly")

    fsm_simple_init(FSM_STATE_IDLE)
    assert_eq(fsm_simple_get_state(), FSM_STATE_IDLE, "starts IDLE")

    fsm_simple_set_state(FSM_STATE_RUNNING)
    assert_eq(fsm_simple_get_state(), FSM_STATE_RUNNING, "set to RUNNING")

    fsm_simple_set_state(FSM_STATE_STOPPED)
    assert_eq(fsm_simple_get_state(), FSM_STATE_STOPPED, "set to STOPPED")

def test_fsm_simple_reset():
    print_section("FSM Reset")

    fsm_simple_init(FSM_STATE_IDLE)
    fsm_add_transition_simple(FSM_STATE_IDLE, EVENT_START, FSM_STATE_RUNNING)

    fsm_process_event_simple(EVENT_START)
    assert_eq(fsm_simple_get_state(), FSM_STATE_RUNNING, "moved to RUNNING")

    fsm_simple_reset()
    assert_eq(fsm_simple_get_state(), FSM_STATE_IDLE, "reset to initial state")

def test_fsm_multiple_transitions():
    print_section("Multiple Transitions from State")

    fsm_simple_init(FSM_STATE_IDLE)

    # Multiple events from same state
    fsm_add_transition_simple(FSM_STATE_IDLE, EVENT_START, FSM_STATE_RUNNING)
    fsm_add_transition_simple(FSM_STATE_IDLE, EVENT_STOP, FSM_STATE_STOPPED)

    # Test first path
    new_state: int32 = fsm_process_event_simple(EVENT_START)
    assert_eq(new_state, FSM_STATE_RUNNING, "IDLE -> START -> RUNNING")

    # Reset and test second path
    fsm_simple_init(FSM_STATE_IDLE)
    fsm_add_transition_simple(FSM_STATE_IDLE, EVENT_STOP, FSM_STATE_STOPPED)
    new_state = fsm_process_event_simple(EVENT_STOP)
    assert_eq(new_state, FSM_STATE_STOPPED, "IDLE -> STOP -> STOPPED")

def test_fsm_self_loop():
    print_section("Self-Loop Transition")

    fsm_simple_init(FSM_STATE_RUNNING)
    fsm_add_transition_simple(FSM_STATE_RUNNING, EVENT_PAUSE, FSM_STATE_RUNNING)  # Stay in RUNNING

    new_state: int32 = fsm_process_event_simple(EVENT_PAUSE)
    assert_eq(new_state, FSM_STATE_RUNNING, "self-loop stays in RUNNING")

def run_fsm_tests():
    print_str("=== Pynux FSM Tests ===")
    print_newline()

    reset_counters()

    test_fsm_simple_init()
    test_fsm_transitions()
    test_fsm_invalid_transition()
    test_fsm_simple_set_state()
    test_fsm_simple_reset()
    test_fsm_multiple_transitions()
    test_fsm_self_loop()

    return print_results()
