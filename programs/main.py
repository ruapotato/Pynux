# User Main Program
#
# This file auto-runs when Pynux boots (like code.py in CircuitPython).
#
# Two entry points:
#   user_main() - called once at startup (like Arduino setup())
#   user_tick() - called repeatedly from main loop (like Arduino loop())
#
# Output works in both graphical and text modes.

from lib.io import print_str, print_int
from kernel.timer import timer_get_ticks

# State for tick function
last_print_time: int32 = 0

# Called once at startup
def user_main():
    print_str("main.py: Uptime monitor started\n")

# Called repeatedly from main loop (non-blocking!)
def user_tick():
    global last_print_time

    ticks: int32 = timer_get_ticks()

    # Only print once every 5 seconds
    if ticks - last_print_time >= 5000:
        last_print_time = ticks
        secs: int32 = ticks / 1000

        print_str("Uptime: ")
        print_int(secs)
        print_str("s\n")
