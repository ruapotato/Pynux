# echo - display a line of text
# Usage: echo [string ...]

from lib.io import print_str, print_newline, uart_putc

# For bare metal, args come from command buffer
# This is called by the shell with parsed arguments

def echo(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    i: int32 = 0
    while i < argc:
        print_str(argv[i])
        if i < argc - 1:
            uart_putc(' ')
        i = i + 1
    print_newline()
    return 0

# Standalone main for testing
def main() -> int32:
    print_str("Hello from echo!\n")
    return 0
