# uptime - show how long system has been running
# For bare metal: shows cycle count estimate

from lib.io import print_str, print_int, print_newline

# Simple cycle counter (incremented elsewhere)
cycle_count: int32 = 0

def uptime():
    # Estimate uptime based on cycle count
    # Assuming ~100MHz CPU, each cycle is ~10ns
    # This is very approximate without a real timer

    print_str("up ")

    # For demo, just show a static message
    print_str("0 days, 0:00\n")
    print_str("(No real-time clock available)\n")

def main() -> int32:
    uptime()
    return 0
