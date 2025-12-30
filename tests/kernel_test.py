from lib.io import print_str, print_int, uart_init

def main() -> int32:
    uart_init()
    print_str("Kernel starting...\n")
    print_str("Test: ")
    print_int(42)
    print_str("\n")
    print_str("Done!\n")
    return 0
