# Fibonacci on bare metal ARM

def fib(n: int32) -> int32:
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

def main() -> int32:
    print_str("Fibonacci sequence:\n")
    i: int32 = 0
    while i < 10:
        result: int32 = fib(i)
        print_str("fib(")
        print_int(i)
        print_str(") = ")
        print_int(result)
        print_str("\n")
        i = i + 1
    return 0
