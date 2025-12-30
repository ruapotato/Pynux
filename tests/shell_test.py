from lib.io import print_str, uart_init

cwd: Array[128, char]

def shell_init():
    cwd[0] = '/'
    cwd[1] = '\0'

def print_prompt():
    print_str("pynux:")
    print_str(&cwd[0])
    print_str("> ")

def main() -> int32:
    uart_init()
    shell_init()
    print_prompt()
    print_str("\nDone!\n")
    return 0
