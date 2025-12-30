# wc - word, line, character count
# For bare metal: counts from UART input until Ctrl+D

from lib.io import print_str, print_int, print_newline, uart_getc

def wc_stdin():
    lines: int32 = 0
    words: int32 = 0
    chars: int32 = 0
    in_word: bool = False

    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF
            break

        chars = chars + 1

        if c == '\n' or c == '\r':
            lines = lines + 1
            in_word = False
        elif c == ' ' or c == '\t':
            in_word = False
        else:
            if not in_word:
                words = words + 1
                in_word = True

    # Print results
    print_str("  ")
    print_int(lines)
    print_str("  ")
    print_int(words)
    print_str("  ")
    print_int(chars)
    print_newline()

def wc(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    wc_stdin()
    return 0

def main() -> int32:
    print_str("wc: counting from UART (Ctrl+D to end)\n")
    wc_stdin()
    return 0
