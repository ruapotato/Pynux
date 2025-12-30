# sleep - delay for specified time
# For bare metal: simple busy wait

from lib.io import print_str

def sleep_ms(ms: int32):
    # Simple delay loop (very approximate)
    # Assumes ~1MHz effective loop speed
    cycles: int32 = ms * 1000
    i: int32 = 0
    while i < cycles:
        i = i + 1

def main() -> int32:
    print_str("Sleeping 1 second...\n")
    sleep_ms(1000)
    print_str("Done!\n")
    return 0
