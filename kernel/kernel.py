# Pynux Kernel
#
# Bare-metal kernel for ARM Cortex-M3.
# Initializes hardware and provides system services.

from lib.io import print_str, print_int, print_newline, uart_init, uart_available, uart_getc
from lib.memory import heap_init
from kernel.ramfs import ramfs_init, ramfs_create, ramfs_write
from kernel.timer import timer_init
from lib.de import de_main
from lib.shell import shell_main

# Kernel version
KERNEL_VERSION_MAJOR: int32 = 0
KERNEL_VERSION_MINOR: int32 = 1
KERNEL_VERSION_PATCH: int32 = 0

# System state (volatile for potential interrupt access)
kernel_initialized: volatile bool = False
tick_count: volatile int32 = 0

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
    ramfs_create("/dev", True)
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

    # Mark initialization complete with proper synchronization
    state: int32 = critical_enter()
    kernel_initialized = True
    critical_exit(state)

    # Memory barrier to ensure all init writes are visible
    dsb()

    print_str("[kernel] Initialization complete.\n\n")

def kernel_panic(msg: Ptr[char]):
    # Disable interrupts during panic
    state: int32 = critical_enter()

    print_str("\n*** KERNEL PANIC ***\n")
    print_str(msg)
    print_str("\nSystem halted.\n")

    # Memory barrier before halt
    dsb()

    while True:
        pass  # Halt (interrupts remain disabled)

def kernel_uptime() -> int32:
    # Read volatile tick_count with critical section
    state: int32 = critical_enter()
    ticks: int32 = tick_count
    critical_exit(state)
    return ticks

def kernel_tick():
    global tick_count
    # Update tick count in critical section
    state: int32 = critical_enter()
    tick_count = tick_count + 1
    critical_exit(state)

# Main entry point
def main() -> int32:
    kernel_init()

    # Flush any pending UART input from boot process
    while uart_available():
        discard: char = uart_getc()

    # Boot selection: press 's' for shell, any other key or wait for GUI
    print_str("Press 's' for text shell, any other key for desktop...\n")
    print_str("Starting in: ")

    # Countdown with visual feedback
    use_shell: bool = False
    countdown: int32 = 3
    while countdown > 0:
        print_int(countdown)
        print_str(" ")

        # Check for input during each countdown second (~100000 iterations)
        i: int32 = 0
        while i < 100000:
            if uart_available():
                c: char = uart_getc()
                if c == 's' or c == 'S':
                    use_shell = True
                    print_str("\n[shell mode]\n")
                    countdown = 0
                    break
                else:
                    print_str("\n[desktop mode]\n")
                    countdown = 0
                    break
            i = i + 1
        countdown = countdown - 1

    if use_shell:
        shell_main()
    else:
        de_main()

    return 0
