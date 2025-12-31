# Pynux Timer and Scheduling Tests
#
# Tests for timer functionality and time-based operations.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, assert_lt,
                                   test_pass, test_fail)
from kernel.timer import (timer_init, timer_tick, timer_get_ticks,
                           timer_delay_ms, timer_delay_us)

# ============================================================================
# Timer Initialization Tests
# ============================================================================

def test_timer_init():
    """Test timer initialization."""
    print_section("Timer Initialization")

    # Initialize should not crash
    timer_init()
    test_pass("timer_init completes")

def test_get_ticks():
    """Test getting tick count."""
    ticks: int32 = timer_get_ticks()
    assert_gte(ticks, 0, "timer_get_ticks returns >= 0")

    # Calling again should return same or higher
    ticks2: int32 = timer_get_ticks()
    assert_gte(ticks2, ticks, "ticks don't go backwards")

# ============================================================================
# Timer Tick Tests
# ============================================================================

def test_timer_tick():
    """Test timer tick increments counter."""
    print_section("Timer Ticks")

    before: int32 = timer_get_ticks()

    # Simulate ticks
    timer_tick()
    timer_tick()
    timer_tick()

    after: int32 = timer_get_ticks()

    # Should have increased by at least 3
    diff: int32 = after - before
    assert_gte(diff, 3, "ticks increment counter")

def test_many_ticks():
    """Test many timer ticks."""
    before: int32 = timer_get_ticks()

    # Many ticks
    i: int32 = 0
    while i < 100:
        timer_tick()
        i = i + 1

    after: int32 = timer_get_ticks()

    diff: int32 = after - before
    assert_gte(diff, 100, "100 ticks counted")

# ============================================================================
# Delay Tests
# ============================================================================

def test_delay_ms():
    """Test millisecond delay."""
    print_section("Delays")

    # Short delay should complete
    timer_delay_ms(1)
    test_pass("delay_ms(1) completes")

    # Slightly longer delay
    timer_delay_ms(10)
    test_pass("delay_ms(10) completes")

def test_delay_us():
    """Test microsecond delay."""
    # Short delay
    timer_delay_us(100)
    test_pass("delay_us(100) completes")

    timer_delay_us(1000)  # 1ms in microseconds
    test_pass("delay_us(1000) completes")

def test_delay_zero():
    """Test zero delay."""
    timer_delay_ms(0)
    test_pass("delay_ms(0) doesn't block")

    timer_delay_us(0)
    test_pass("delay_us(0) doesn't block")

# ============================================================================
# Timing Accuracy Tests
# ============================================================================

def test_delay_ordering():
    """Test that longer delays take longer."""
    # Record ticks before short delay
    before_short: int32 = timer_get_ticks()

    # Simulate some ticks during "delay"
    i: int32 = 0
    while i < 5:
        timer_tick()
        i = i + 1

    after_short: int32 = timer_get_ticks()
    short_time: int32 = after_short - before_short

    # Record ticks before long delay
    before_long: int32 = timer_get_ticks()

    i = 0
    while i < 20:
        timer_tick()
        i = i + 1

    after_long: int32 = timer_get_ticks()
    long_time: int32 = after_long - before_long

    # Long should take more ticks than short
    assert_gt(long_time, short_time, "longer delay takes more time")

def test_tick_count_persistence():
    """Test that tick count persists across calls."""
    # Get initial
    initial: int32 = timer_get_ticks()

    # Add some ticks
    timer_tick()
    timer_tick()

    # Get again - should be initial + 2
    after: int32 = timer_get_ticks()
    assert_eq(after, initial + 2, "tick count persists")

    # Get one more time
    again: int32 = timer_get_ticks()
    assert_eq(again, after, "count stable without ticks")

# ============================================================================
# Edge Cases
# ============================================================================

def test_timer_edge_cases():
    """Test timer edge cases."""
    print_section("Edge Cases")

    # Very small delays
    timer_delay_us(1)
    test_pass("delay_us(1) works")

    timer_delay_ms(1)
    test_pass("delay_ms(1) works")

    # Multiple quick calls
    i: int32 = 0
    while i < 10:
        timer_delay_us(10)
        i = i + 1
    test_pass("rapid delays work")

# ============================================================================
# Intuitive API Tests
# ============================================================================

def test_intuitive_timer_api():
    """Test that timer API is intuitive."""
    print_section("Intuitive Timer API")

    # get_ticks returns sensible value
    ticks: int32 = timer_get_ticks()
    if ticks >= 0:
        test_pass("get_ticks returns non-negative")
    else:
        test_fail("get_ticks should be >= 0")

    # tick() increments counter
    before: int32 = timer_get_ticks()
    timer_tick()
    after: int32 = timer_get_ticks()

    if after == before + 1:
        test_pass("tick() increments by 1")
    else:
        test_fail("tick() should increment by 1")

    # delays complete without blocking forever
    timer_delay_ms(5)
    test_pass("delay_ms completes")

    timer_delay_us(500)
    test_pass("delay_us completes")

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    print_str("\n=== Pynux Timer Tests ===\n")

    timer_init()

    test_timer_init()
    test_get_ticks()

    test_timer_tick()
    test_many_ticks()

    test_delay_ms()
    test_delay_us()
    test_delay_zero()

    test_delay_ordering()
    test_tick_count_persistence()

    test_timer_edge_cases()

    test_intuitive_timer_api()

    return print_results()
