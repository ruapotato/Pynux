# Pynux Kernel
#
# Bare-metal kernel for ARM Cortex-M3.
# Initializes hardware and provides system services.

from lib.io import print_str, print_int, print_newline, uart_init
from lib.memory import heap_init
from kernel.ramfs import ramfs_init, ramfs_create, ramfs_write
from kernel.timer import timer_init
from coreutils.sh import shell_loop

# Kernel version
KERNEL_VERSION_MAJOR: int32 = 0
KERNEL_VERSION_MINOR: int32 = 1
KERNEL_VERSION_PATCH: int32 = 0

# System state
kernel_initialized: bool = False
tick_count: int32 = 0

def kernel_banner():
    print_str("\n")
    print_str("  _____                        \n")
    print_str(" |  __ \\                       \n")
    print_str(" | |__) |   _ _ __  _   ___  __\n")
    print_str(" |  ___/ | | | '_ \\| | | \\ \\/ /\n")
    print_str(" | |   | |_| | | | | |_| |>  < \n")
    print_str(" |_|    \\__, |_| |_|\\__,_/_/\\_\\\n")
    print_str("         __/ |                 \n")
    print_str("        |___/                  \n")
    print_str("\n")
    print_str("Pynux Kernel v")
    print_int(KERNEL_VERSION_MAJOR)
    print_str(".")
    print_int(KERNEL_VERSION_MINOR)
    print_str(".")
    print_int(KERNEL_VERSION_PATCH)
    print_str("\n")
    print_str("ARM Cortex-M3 / QEMU mps2-an385\n")
    print_str("\n")

def kernel_init():
    global kernel_initialized

    # Initialize UART first for debug output
    uart_init()

    kernel_banner()

    print_str("[kernel] Initializing...\n")

    # Initialize heap
    print_str("[kernel] Heap init... ")
    heap_init()
    print_str("OK\n")

    # Initialize timer
    print_str("[kernel] Timer init... ")
    timer_init()
    print_str("OK\n")

    # Initialize RAM filesystem
    print_str("[kernel] RAMFS init... ")
    ramfs_init()
    print_str("OK\n")

    # Create initial filesystem structure
    print_str("[kernel] Creating /dev... ")
    ramfs_create("/dev", True)  # directory
    ramfs_create("/dev/null", False)
    ramfs_create("/dev/zero", False)
    ramfs_create("/dev/tty", False)
    print_str("OK\n")

    print_str("[kernel] Creating /tmp... ")
    ramfs_create("/tmp", True)
    print_str("OK\n")

    print_str("[kernel] Creating /home... ")
    ramfs_create("/home", True)
    print_str("OK\n")

    print_str("[kernel] Creating /etc... ")
    ramfs_create("/etc", True)
    ramfs_create("/etc/motd", False)
    ramfs_write("/etc/motd", "Welcome to Pynux!\n")
    print_str("OK\n")

    kernel_initialized = True
    print_str("[kernel] Initialization complete.\n\n")

def kernel_panic(msg: Ptr[char]):
    print_str("\n*** KERNEL PANIC ***\n")
    print_str(msg)
    print_str("\nSystem halted.\n")
    while True:
        pass  # Halt

def kernel_uptime() -> int32:
    return tick_count

def kernel_tick():
    global tick_count
    tick_count = tick_count + 1

# Main entry point
def main() -> int32:
    kernel_init()

    # Start shell
    shell_loop()

    return 0
