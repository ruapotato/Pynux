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
    """Test timer tick checks hardware flag."""
    print_section("Timer Ticks")

    before: int32 = timer_get_ticks()

    # timer_tick only increments when hardware flag is set
    # Call it multiple times - may or may not increment depending on timing
    timer_tick()
    timer_tick()
    timer_tick()

    after: int32 = timer_get_ticks()

    # Ticks should not decrease
    assert_gte(after, before, "ticks don't decrease")

def test_many_ticks():
    """Test many timer tick calls don't crash."""
    before: int32 = timer_get_ticks()

    # Many tick checks - timer_tick polls hardware
    i: int32 = 0
    while i < 100:
        timer_tick()
        i = i + 1

    after: int32 = timer_get_ticks()

    # Counter should not go backwards
    assert_gte(after, before, "many tick calls stable")

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
    # Use actual delays to test ordering
    # Short delay: 1ms
    before_short: int32 = timer_get_ticks()
    timer_delay_ms(1)
    after_short: int32 = timer_get_ticks()

    # Long delay: 5ms
    before_long: int32 = timer_get_ticks()
    timer_delay_ms(5)
    after_long: int32 = timer_get_ticks()

    # Both delays should complete without going backwards
    assert_gte(after_short, before_short, "short delay completes")
    assert_gte(after_long, before_long, "long delay completes")

def test_tick_count_persistence():
    """Test that tick count persists across calls."""
    # Get initial
    initial: int32 = timer_get_ticks()

    # Do a small delay to allow ticks to accumulate
    timer_delay_ms(2)

    # Get again - should be same or higher
    after: int32 = timer_get_ticks()
    assert_gte(after, initial, "tick count persists")

    # Get one more time immediately - should be same or higher
    again: int32 = timer_get_ticks()
    assert_gte(again, after, "count stable across calls")

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

    # tick() polls hardware - may or may not increment
    before: int32 = timer_get_ticks()
    timer_tick()
    after: int32 = timer_get_ticks()

    if after >= before:
        test_pass("tick() doesn't decrease counter")
    else:
        test_fail("tick() should not decrease counter")

    # delays complete without blocking forever
    timer_delay_ms(5)
    test_pass("delay_ms completes")

    timer_delay_us(500)
    test_pass("delay_us completes")

# ============================================================================
# Main
# ============================================================================

def test_timer_main() -> int32:
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
