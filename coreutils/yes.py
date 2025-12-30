# yes - repeatedly output a line

from lib.io import print_str, print_newline

def yes(msg: Ptr[char]):
    while True:
        print_str(msg)
        print_newline()

def main() -> int32:
    yes("y")
    return 0
