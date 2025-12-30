# seq - print sequence of numbers

from lib.io import print_int, print_newline

def seq(start: int32, end: int32, step: int32):
    i: int32 = start
    if step > 0:
        while i <= end:
            print_int(i)
            print_newline()
            i = i + step
    else:
        while i >= end:
            print_int(i)
            print_newline()
            i = i + step

def main() -> int32:
    seq(1, 10, 1)
    return 0
