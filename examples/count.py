# Count on bare metal ARM

def main() -> int32:
    print_str("Counting to 10:\n")
    i: int32 = 1
    while i <= 10:
        print_int(i)
        print_str("\n")
        i = i + 1
    print_str("Done!\n")
    return 0
