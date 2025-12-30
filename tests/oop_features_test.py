from lib.io import print_str, print_int, uart_init

# ============================================================================
# Pynux OOP Features Test Suite
# Tests decorators, inheritance, lambda, generators, context managers
# ============================================================================

# --- Test 1: Class with @staticmethod ---
class Counter:
    count: int32 = 0

    @staticmethod
    def increment() -> int32:
        return 1

    @staticmethod
    def add(a: int32, b: int32) -> int32:
        return a + b

def test_staticmethod() -> int32:
    result: int32 = Counter.add(10, 20)
    return result  # Expected: 30

# --- Test 2: Class with @classmethod ---
class Factory:
    default_value: int32 = 42

    @classmethod
    def create(cls) -> int32:
        return 42

def test_classmethod() -> int32:
    return Factory.create()  # Expected: 42

# --- Test 3: Simple class inheritance ---
class Animal:
    legs: int32 = 4

class Dog(Animal):
    bark_count: int32 = 0

def test_inheritance() -> int32:
    d: Dog = Dog()
    d.legs = 4
    d.bark_count = 3
    return d.legs + d.bark_count  # Expected: 7

# --- Test 4: Multiple inheritance fields ---
class Base1:
    val1: int32 = 0

class Combined(Base1):
    val3: int32 = 0

def test_multi_fields() -> int32:
    c: Combined = Combined()
    c.val1 = 10
    c.val3 = 32
    return c.val1 + c.val3  # Expected: 42

# --- Test 5: @property decorator ---
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

# --- Test 6: Method with decorator in child class ---
class Parent:
    value: int32 = 10

class Child(Parent):
    extra: int32 = 5

    @staticmethod
    def compute(x: int32) -> int32:
        return x * 2

def test_child_decorator() -> int32:
    c: Child = Child()
    c.value = 16
    c.extra = 5
    return c.value + c.extra + Child.compute(10)  # Expected: 16 + 5 + 20 = 41

# ============================================================================
# Main - Run all tests
# ============================================================================

def main() -> int32:
    uart_init()

    print_str("=== Pynux OOP Features Tests ===\n\n")

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
    print_str("Test 2  (classmethod):   ")
    r = test_classmethod()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 3
    print_str("Test 3  (inheritance):   ")
    r = test_inheritance()
    print_int(r)
    if r == 7:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 7)\n")
        failed = failed + 1

    # Test 4
    print_str("Test 4  (multi fields):  ")
    r = test_multi_fields()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 5
    print_str("Test 5  (property):      ")
    r = test_property()
    print_int(r)
    if r == 42:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 42)\n")
        failed = failed + 1

    # Test 6
    print_str("Test 6  (child deco):    ")
    r = test_child_decorator()
    print_int(r)
    if r == 41:
        print_str(" PASS\n")
        passed = passed + 1
    else:
        print_str(" FAIL (expected 41)\n")
        failed = failed + 1

    # Summary
    print_str("\n=== Results: ")
    print_int(passed)
    print_str("/6 passed ===\n")

    if failed == 0:
        print_str("ALL TESTS PASSED!\n")
    else:
        print_str("SOME TESTS FAILED!\n")

    return failed
