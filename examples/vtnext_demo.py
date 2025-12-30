# VTNext Graphics Demo

from lib.vtnext import *
from lib.io import print_str

def main() -> int32:
    # Initialize VTNext graphics
    vtn_init(800, 600)

    # Draw some shapes
    vtn_clear(0, 0, 64, 255)  # Dark blue background

    # Red rectangle
    vtn_rect(50, 50, 200, 100, 255, 0, 0, 255)

    # Green circle
    vtn_circle(400, 150, 80, 0, 255, 0, 255)

    # Yellow line
    vtn_line(100, 300, 700, 400, 3, 255, 255, 0, 255)

    # White text
    vtn_print("Pynux VTNext Demo", 250, 500)
    vtn_text("ARM Cortex-M3", 280, 540, 1, 200, 200, 200, 255)

    vtn_present()

    print_str("VTNext demo rendered!\n")
    return 0
