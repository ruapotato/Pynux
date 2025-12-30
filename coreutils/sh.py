# sh - Pynux Shell
#
# Simple shell for bare-metal ARM.
# Supports built-in commands and filesystem operations.

from lib.io import print_str, print_int, print_newline, uart_putc, uart_getc
from lib.string import strcmp, strlen, strcpy, strncpy, isspace, strcat, atoi
from lib.memory import alloc, memset
from lib.vtnext import vtn_init, vtn_clear, vtn_rect, vtn_circle, vtn_line
from lib.vtnext import vtn_text, vtn_print, vtn_present, vtn_flush
from kernel.ramfs import ramfs_init, ramfs_create, ramfs_delete, ramfs_write
from kernel.ramfs import ramfs_read, ramfs_exists, ramfs_isdir, ramfs_size
from kernel.ramfs import ramfs_readdir, ramfs_lookup

# Command buffer
CMD_BUF_SIZE: int32 = 256
MAX_ARGS: int32 = 16

# Global buffers
cmd_buffer: Array[256, char]
arg_ptrs: Array[16, Ptr[char]]

# Current working directory
cwd: Array[128, char]

# Shell state
running: bool = True

def shell_init():
    cwd[0] = '/'
    cwd[1] = '\0'

# Print shell prompt
def print_prompt():
    print_str("pynux:")
    print_str(&cwd[0])
    print_str("> ")

# Read a line from UART with editing support
def read_line() -> Ptr[char]:
    global running
    pos: int32 = 0

    while True:
        c: char = uart_getc()

        # Enter
        if c == '\r' or c == '\n':
            cmd_buffer[pos] = '\0'
            print_newline()
            return &cmd_buffer[0]

        # Backspace
        if c == '\b' or c == '\x7f':
            if pos > 0:
                pos = pos - 1
                print_str("\b \b")
            continue

        # Ctrl+C - cancel line
        if c == '\x03':
            print_str("^C\n")
            return ""

        # Ctrl+D - exit
        if c == '\x04':
            if pos == 0:
                running = False
                return ""
            continue

        # Regular character
        if pos < CMD_BUF_SIZE - 1:
            cmd_buffer[pos] = c
            pos = pos + 1
            uart_putc(c)

    return &cmd_buffer[0]

# Parse command line into argc/argv
def parse_args(line: Ptr[char]) -> int32:
    argc: int32 = 0
    i: int32 = 0
    in_arg: bool = False

    while line[i] != '\0' and argc < MAX_ARGS:
        if isspace(line[i]):
            if in_arg:
                line[i] = '\0'  # Terminate argument
                in_arg = False
        else:
            if not in_arg:
                arg_ptrs[argc] = &line[i]
                argc = argc + 1
                in_arg = True
        i = i + 1

    return argc

# Build full path from relative or absolute
def build_path(arg: Ptr[char], out: Ptr[char]):
    if arg[0] == '/':
        # Absolute path
        strcpy(out, arg)
    else:
        # Relative to cwd
        strcpy(out, &cwd[0])
        if cwd[0] != '/' or cwd[1] != '\0':
            strcat(out, "/")
        strcat(out, arg)

# ============================================================================
# Built-in commands
# ============================================================================

def cmd_help():
    print_str("Pynux Shell Commands:\n")
    print_str("  help      - Show this help\n")
    print_str("  echo      - Print arguments\n")
    print_str("  clear     - Clear screen\n")
    print_str("  version   - Show version\n")
    print_str("  exit      - Exit shell\n")
    print_str("  demo      - Run demo\n")
    print_str("  vtnext    - VTNext graphics demo\n")
    print_str("  calc      - Simple calculator\n")
    print_str("\nFilesystem:\n")
    print_str("  ls [dir]  - List directory\n")
    print_str("  cat file  - Show file contents\n")
    print_str("  mkdir dir - Create directory\n")
    print_str("  touch f   - Create empty file\n")
    print_str("  rm file   - Remove file\n")
    print_str("  rmdir dir - Remove directory\n")
    print_str("  pwd       - Print working directory\n")
    print_str("  cd dir    - Change directory\n")
    print_str("  write f   - Write text to file\n")

def cmd_echo(argc: int32):
    i: int32 = 1
    while i < argc:
        print_str(arg_ptrs[i])
        if i < argc - 1:
            uart_putc(' ')
        i = i + 1
    print_newline()

def cmd_clear():
    # VT100 clear screen
    print_str("\x1b[2J\x1b[H")

def cmd_version():
    print_str("Pynux Shell v0.1\n")
    print_str("ARM Cortex-M3 bare metal\n")
    print_str("Python syntax, native speed.\n")

def cmd_demo():
    print_str("\n=== Pynux Demo ===\n\n")

    # Counting
    print_str("Counting: ")
    i: int32 = 1
    while i <= 5:
        print_int(i)
        uart_putc(' ')
        i = i + 1
    print_newline()

    # Arithmetic
    print_str("10 + 25 = ")
    print_int(10 + 25)
    print_newline()

    print_str("100 / 7 = ")
    print_int(100 / 7)
    print_newline()

    # Fibonacci
    print_str("\nFibonacci: ")
    a: int32 = 0
    b: int32 = 1
    i = 0
    while i < 10:
        print_int(a)
        uart_putc(' ')
        c: int32 = a + b
        a = b
        b = c
        i = i + 1
    print_newline()

    print_str("\n=== Demo Complete ===\n")

def cmd_vtnext():
    print_str("VTNext Graphics Demo\n")
    print_str("(Pipe output to vtnext/renderer.py)\n\n")

    # Initialize VTNext
    vtn_init(800, 600)

    # Clear to dark blue
    vtn_clear(20, 40, 80, 255)

    # Draw some rectangles
    vtn_rect(50, 50, 200, 150, 255, 100, 100, 255)
    vtn_rect(300, 100, 150, 100, 100, 255, 100, 255)
    vtn_rect(500, 50, 100, 200, 100, 100, 255, 255)

    # Draw circles
    vtn_circle(150, 400, 80, 255, 255, 0, 255)
    vtn_circle(400, 400, 60, 0, 255, 255, 255)
    vtn_circle(600, 400, 100, 255, 0, 255, 255)

    # Draw lines
    vtn_line(50, 550, 750, 550, 3, 255, 255, 255, 255)
    vtn_line(400, 300, 400, 500, 2, 200, 200, 200, 255)

    # Draw text
    vtn_text("Pynux VTNext Demo", 250, 20, 2, 255, 255, 255, 255)
    vtn_print("Shapes and colors!", 300, 520)

    # Present the frame
    vtn_present()
    vtn_flush()

    print_str("Graphics sent!\n")

def cmd_calc(argc: int32):
    if argc < 4:
        print_str("Usage: calc <num> <op> <num>\n")
        print_str("  ops: + - * / %\n")
        return

    # Parse numbers
    a: int32 = atoi(arg_ptrs[1])
    b: int32 = atoi(arg_ptrs[3])
    op: char = arg_ptrs[2][0]

    result: int32 = 0
    if op == '+':
        result = a + b
    elif op == '-':
        result = a - b
    elif op == '*':
        result = a * b
    elif op == '/':
        if b != 0:
            result = a / b
        else:
            print_str("Error: division by zero\n")
            return
    elif op == '%':
        if b != 0:
            result = a % b
        else:
            print_str("Error: division by zero\n")
            return
    else:
        print_str("Unknown operator\n")
        return

    print_int(result)
    print_newline()

# ============================================================================
# Filesystem commands
# ============================================================================

def cmd_ls(argc: int32):
    path: Array[128, char]

    if argc > 1:
        build_path(arg_ptrs[1], &path[0])
    else:
        strcpy(&path[0], &cwd[0])

    if not ramfs_exists(&path[0]):
        print_str("ls: cannot access '")
        print_str(&path[0])
        print_str("': No such file or directory\n")
        return

    if not ramfs_isdir(&path[0]):
        print_str(&path[0])
        print_newline()
        return

    name_buf: Array[32, char]
    index: int32 = 0

    while True:
        result: int32 = ramfs_readdir(&path[0], index, &name_buf[0])
        if result < 0:
            break

        print_str(&name_buf[0])
        if result == 1:  # Directory
            print_str("/")
        print_newline()
        index = index + 1

def cmd_cat(argc: int32):
    if argc < 2:
        print_str("Usage: cat <file>\n")
        return

    path: Array[128, char]
    build_path(arg_ptrs[1], &path[0])

    if not ramfs_exists(&path[0]):
        print_str("cat: ")
        print_str(&path[0])
        print_str(": No such file\n")
        return

    if ramfs_isdir(&path[0]):
        print_str("cat: ")
        print_str(&path[0])
        print_str(": Is a directory\n")
        return

    size: int32 = ramfs_size(&path[0])
    if size <= 0:
        return

    buf: Array[4096, uint8]
    bytes_read: int32 = ramfs_read(&path[0], &buf[0], size)

    i: int32 = 0
    while i < bytes_read:
        uart_putc(cast[char](buf[i]))
        i = i + 1

def cmd_mkdir(argc: int32):
    if argc < 2:
        print_str("Usage: mkdir <dir>\n")
        return

    path: Array[128, char]
    build_path(arg_ptrs[1], &path[0])

    if ramfs_exists(&path[0]):
        print_str("mkdir: ")
        print_str(&path[0])
        print_str(": File exists\n")
        return

    if ramfs_create(&path[0], True) < 0:
        print_str("mkdir: cannot create '")
        print_str(&path[0])
        print_str("'\n")

def cmd_touch(argc: int32):
    if argc < 2:
        print_str("Usage: touch <file>\n")
        return

    path: Array[128, char]
    build_path(arg_ptrs[1], &path[0])

    if ramfs_exists(&path[0]):
        return  # Already exists

    if ramfs_create(&path[0], False) < 0:
        print_str("touch: cannot touch '")
        print_str(&path[0])
        print_str("'\n")

def cmd_rm(argc: int32):
    if argc < 2:
        print_str("Usage: rm <file>\n")
        return

    path: Array[128, char]
    build_path(arg_ptrs[1], &path[0])

    if not ramfs_exists(&path[0]):
        print_str("rm: ")
        print_str(&path[0])
        print_str(": No such file\n")
        return

    if ramfs_isdir(&path[0]):
        print_str("rm: ")
        print_str(&path[0])
        print_str(": Is a directory\n")
        return

    if ramfs_delete(&path[0]) < 0:
        print_str("rm: cannot remove '")
        print_str(&path[0])
        print_str("'\n")

def cmd_rmdir(argc: int32):
    if argc < 2:
        print_str("Usage: rmdir <dir>\n")
        return

    path: Array[128, char]
    build_path(arg_ptrs[1], &path[0])

    if not ramfs_exists(&path[0]):
        print_str("rmdir: ")
        print_str(&path[0])
        print_str(": No such directory\n")
        return

    if not ramfs_isdir(&path[0]):
        print_str("rmdir: ")
        print_str(&path[0])
        print_str(": Not a directory\n")
        return

    if ramfs_delete(&path[0]) < 0:
        print_str("rmdir: ")
        print_str(&path[0])
        print_str(": Directory not empty\n")

def cmd_pwd():
    print_str(&cwd[0])
    print_newline()

def cmd_cd(argc: int32):
    if argc < 2:
        # cd with no args goes to root
        cwd[0] = '/'
        cwd[1] = '\0'
        return

    path: Array[128, char]
    build_path(arg_ptrs[1], &path[0])

    if not ramfs_exists(&path[0]):
        print_str("cd: ")
        print_str(&path[0])
        print_str(": No such directory\n")
        return

    if not ramfs_isdir(&path[0]):
        print_str("cd: ")
        print_str(&path[0])
        print_str(": Not a directory\n")
        return

    strcpy(&cwd[0], &path[0])

def cmd_write(argc: int32):
    if argc < 2:
        print_str("Usage: write <file>\n")
        print_str("Enter text (Ctrl+D to save):\n")
        return

    path: Array[128, char]
    build_path(arg_ptrs[1], &path[0])

    print_str("Enter text (Ctrl+D to save):\n")

    # Read input
    buf: Array[4096, char]
    pos: int32 = 0

    while pos < 4095:
        c: char = uart_getc()
        if c == '\x04':  # Ctrl+D
            break
        buf[pos] = c
        pos = pos + 1
        uart_putc(c)
        if c == '\r':
            uart_putc('\n')
            buf[pos - 1] = '\n'

    buf[pos] = '\0'
    print_newline()

    if ramfs_write(&path[0], &buf[0]) < 0:
        print_str("write: error writing to '")
        print_str(&path[0])
        print_str("'\n")
    else:
        print_str("Saved ")
        print_int(pos)
        print_str(" bytes.\n")

# Execute command
def execute(argc: int32) -> int32:
    global running

    if argc == 0:
        return 0

    cmd: Ptr[char] = arg_ptrs[0]

    # Built-in commands
    if strcmp(cmd, "help") == 0:
        cmd_help()
    elif strcmp(cmd, "echo") == 0:
        cmd_echo(argc)
    elif strcmp(cmd, "clear") == 0:
        cmd_clear()
    elif strcmp(cmd, "version") == 0:
        cmd_version()
    elif strcmp(cmd, "exit") == 0 or strcmp(cmd, "quit") == 0:
        running = False
    elif strcmp(cmd, "demo") == 0:
        cmd_demo()
    elif strcmp(cmd, "vtnext") == 0:
        cmd_vtnext()
    elif strcmp(cmd, "calc") == 0:
        cmd_calc(argc)
    # Filesystem commands
    elif strcmp(cmd, "ls") == 0:
        cmd_ls(argc)
    elif strcmp(cmd, "cat") == 0:
        cmd_cat(argc)
    elif strcmp(cmd, "mkdir") == 0:
        cmd_mkdir(argc)
    elif strcmp(cmd, "touch") == 0:
        cmd_touch(argc)
    elif strcmp(cmd, "rm") == 0:
        cmd_rm(argc)
    elif strcmp(cmd, "rmdir") == 0:
        cmd_rmdir(argc)
    elif strcmp(cmd, "pwd") == 0:
        cmd_pwd()
    elif strcmp(cmd, "cd") == 0:
        cmd_cd(argc)
    elif strcmp(cmd, "write") == 0:
        cmd_write(argc)
    else:
        print_str("Unknown command: ")
        print_str(cmd)
        print_str("\nType 'help' for commands.\n")

    return 0

# Shell main loop
def shell_loop():
    shell_init()
    print_str("\nPynux Shell\n")
    print_str("Type 'help' for commands, 'exit' to quit.\n\n")

    while running:
        print_prompt()
        line: Ptr[char] = read_line()

        if not running:
            break

        if line[0] != '\0':
            argc: int32 = parse_args(line)
            execute(argc)

    print_str("Goodbye!\n")
