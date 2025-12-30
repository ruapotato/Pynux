# factor - print prime factors

from lib.io import print_str, print_int, print_newline, uart_putc

def factor(n: int32):
    print_int(n)
    print_str(": ")

    if n < 2:
        print_newline()
        return

    # Factor out 2s
    while n % 2 == 0:
        print_int(2)
        uart_putc(' ')
        n = n / 2

    # Factor out odd numbers
    i: int32 = 3
    while i * i <= n:
        while n % i == 0:
            print_int(i)
            uart_putc(' ')
            n = n / i
        i = i + 2

    # Remaining prime
    if n > 1:
        print_int(n)

    print_newline()

def main() -> int32:
    print_str("Prime factors:\n")
    factor(12)
    factor(100)
    factor(97)
    factor(360)
    return 0
