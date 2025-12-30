from lib.io import print_str, print_int, uart_init

counter: int32 = 0

def increment():
    global counter
    counter = counter + 1

def main() -> int32:
    uart_init()
    print_str("Counter: ")
    print_int(counter)
    print_str("\n")
    increment()
    print_str("After increment: ")
    print_int(counter)
    print_str("\n")
    return 0
