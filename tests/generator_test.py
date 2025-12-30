from lib.io import print_str, print_int, uart_init

# ============================================================================
# Generator and Context Manager Tests
# ============================================================================

# --- Test 1: Simple generator that yields numbers ---
# For now, we implement generators as simple iterators
# A full coroutine implementation would require stack switching

class NumberIterator:
    current: int32 = 0
    end: int32 = 0

    def init(self, start: int32, stop: int32) -> int32:
        self.current = start
        self.end = stop
        return 0

    def has_next(self) -> int32:
        if self.current < self.end:
            return 1
        return 0

    def next(self) -> int32:
        val: int32 = self.current
        self.current = self.current + 1
        return val

def test_iterator() -> int32:
    it: NumberIterator = NumberIterator()
    it.init(1, 5)
    total: int32 = 0
    while it.has_next():
        total = total + it.next()
    # 1 + 2 + 3 + 4 = 10
    return total

# --- Test 2: Context manager pattern ---
# Context managers need __enter__ and __exit__ methods
# Simplified implementation using explicit calls

class Resource:
    value: int32 = 0
    is_open: int32 = 0

    def open(self) -> int32:
        self.is_open = 1
        self.value = 10
        return self.value

    def close(self) -> int32:
        result: int32 = self.value
        self.is_open = 0
        self.value = 0
        return result

def test_resource() -> int32:
    r: Resource = Resource()
    # Manual context manager pattern
    enter_val: int32 = r.open()
    # Use resource
    r.value = r.value + 32
    # Exit
    result: int32 = r.close()
    return result  # Expected: 42

# --- Test 3: Range iterator pattern ---
class RangeIter:
    i: int32 = 0
    n: int32 = 0

    def init(self, limit: int32) -> int32:
        self.i = 0
        self.n = limit
        return 0

    def has_next(self) -> int32:
        if self.i < self.n:
            return 1
        return 0

    def next(self) -> int32:
        val: int32 = self.i
        self.i = self.i + 1
        return val

def test_range_iter() -> int32:
    r: RangeIter = RangeIter()
    r.init(6)
    total: int32 = 0
    while r.has_next():
        total = total + r.next()
    # 0 + 1 + 2 + 3 + 4 + 5 = 15
    return total

# ============================================================================
# Main
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Generator/Context Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1
    print_str("Test 1  (iterator):      ")
    r: int32 = test_iterator()
    print_int(r)
    if r == 10:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 10)\n")
        failed = failed + 1

    # Test 2
    print_str("Test 2  (resource):      ")
    r = test_resource()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 3
    print_str("Test 3  (range iter):    ")
    r = test_range_iter()
    print_int(r)
    if r == 15:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 15)\n")
        failed = failed + 1

    # Summary
    print_str("\n=== Results: ")
    print_int(passed)
    print_str("/3 passed ===\n")

    if failed == 0:
        print_str("ALL TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return failed
