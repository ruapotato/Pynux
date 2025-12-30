from lib.io import print_str, print_int, uart_init

# ============================================================================
# Pynux Simple OOP Test - Basic features only
# ============================================================================

# --- Test 1: Class with @staticmethod ---
class Counter:
    count: int32 = 0

    @staticmethod
    def add(a: int32, b: int32) -> int32:
        return a + b

def test_staticmethod() -> int32:
    result: int32 = Counter.add(10, 20)
    return result  # Expected: 30

# --- Test 2: Simple class inheritance ---
class Animal:
    legs: int32 = 0

class Dog(Animal):
    bark_count: int32 = 0

def test_inheritance() -> int32:
    d: Dog = Dog()
    d.legs = 4
    d.bark_count = 3
    return d.legs + d.bark_count  # Expected: 7

# --- Test 3: @property decorator ---
class Rectangle:
    width: int32 = 0
    height: int32 = 0

    @property
    def area(self) -> int32:
        return self.width * self.height

def test_property() -> int32:
    r: Rectangle = Rectangle()
    r.width = 6
    r.height = 7
    return r.area  # Expected: 42

# ============================================================================
# Main - Run all tests
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Pynux OOP Simple Tests ===\n\n")

    passed: int32 = 0
    failed: int32 = 0

    # Test 1
    print_str("Test 1  (staticmethod):  ")
    r: int32 = test_staticmethod()
    print_int(r)
    if r == 30:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 30)\n")
        failed = failed + 1

    # Test 2
    print_str("Test 2  (inheritance):   ")
    r = test_inheritance()
    print_int(r)
    if r == 7:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 7)\n")
        failed = failed + 1

    # Test 3
    print_str("Test 3  (property):      ")
    r = test_property()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
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
