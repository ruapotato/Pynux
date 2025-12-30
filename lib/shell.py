# Pynux Text Shell
#
# Simple VT100 text-mode shell for debugging.
# No graphics, just plain serial I/O.

from lib.io import uart_putc, uart_getc, uart_available, print_str, print_int
from lib.string import strcmp, strlen, strcpy, strcat, memset
from kernel.ramfs import ramfs_readdir, ramfs_create, ramfs_delete
from kernel.ramfs import ramfs_read, ramfs_write, ramfs_exists, ramfs_isdir
from lib.memory import heap_remaining, heap_total, heap_used

# Command buffer
shell_cmd: Array[256, char]
shell_cmd_pos: int32 = 0

# Current directory
shell_cwd: Array[128, char]

# Temp buffer for ls
shell_name_buf: Array[64, char]

# Path buffer for building full paths
shell_path_buf: Array[256, char]

# Read buffer for cat
shell_read_buf: Array[512, uint8]

# Number buffer for printing integers
shell_num_buf: Array[16, char]

def shell_putc(c: char):
    uart_putc(c)

def shell_puts(s: Ptr[char]):
    i: int32 = 0
    while s[i] != '\0':
        uart_putc(s[i])
        i = i + 1

def shell_newline():
    uart_putc('\r')
    uart_putc('\n')

def shell_prompt():
    shell_puts("pynux:")
    shell_puts(&shell_cwd[0])
    shell_puts("> ")

def shell_get_arg() -> Ptr[char]:
    """Get the argument part of command (after first space)."""
    i: int32 = 0
    # Skip command name
    while shell_cmd[i] != '\0' and shell_cmd[i] != ' ':
        i = i + 1
    # Skip spaces
    while shell_cmd[i] == ' ':
        i = i + 1
    return &shell_cmd[i]

def shell_starts_with(prefix: Ptr[char]) -> bool:
    """Check if command starts with prefix."""
    i: int32 = 0
    while prefix[i] != '\0':
        if shell_cmd[i] != prefix[i]:
            return False
        i = i + 1
    return shell_cmd[i] == ' ' or shell_cmd[i] == '\0'

def shell_build_path(name: Ptr[char]):
    """Build full path from cwd and name into shell_path_buf."""
    if name[0] == '/':
        strcpy(&shell_path_buf[0], name)
    else:
        strcpy(&shell_path_buf[0], &shell_cwd[0])
        cwd_len: int32 = strlen(&shell_cwd[0])
        if cwd_len > 0 and shell_cwd[cwd_len - 1] != '/':
            strcat(&shell_path_buf[0], "/")
        strcat(&shell_path_buf[0], name)

def shell_int_to_str(n: int32) -> Ptr[char]:
    """Convert integer to string in shell_num_buf."""
    if n == 0:
        shell_num_buf[0] = '0'
        shell_num_buf[1] = '\0'
        return &shell_num_buf[0]

    neg: bool = False
    if n < 0:
        neg = True
        n = -n

    # Build digits in reverse
    i: int32 = 0
    while n > 0:
        shell_num_buf[i] = cast[char](48 + (n % 10))
        n = n / 10
        i = i + 1

    if neg:
        shell_num_buf[i] = '-'
        i = i + 1

    shell_num_buf[i] = '\0'

    # Reverse the string
    j: int32 = 0
    k: int32 = i - 1
    while j < k:
        tmp: char = shell_num_buf[j]
        shell_num_buf[j] = shell_num_buf[k]
        shell_num_buf[k] = tmp
        j = j + 1
        k = k - 1

    return &shell_num_buf[0]

def shell_exec():
    global shell_cmd_pos

    shell_cmd[shell_cmd_pos] = '\0'

    if shell_cmd_pos == 0:
        shell_prompt()
        return

    cmd: Ptr[char] = &shell_cmd[0]

    if strcmp(cmd, "help") == 0:
        shell_newline()
        shell_puts("Pynux Text Shell Commands:")
        shell_newline()
        shell_puts("  help       - Show this help")
        shell_newline()
        shell_puts("  clear      - Clear screen")
        shell_newline()
        shell_puts("  pwd        - Print working directory")
        shell_newline()
        shell_puts("  ls         - List directory")
        shell_newline()
        shell_puts("  cd <dir>   - Change directory")
        shell_newline()
        shell_puts("  cat <file> - Show file contents")
        shell_newline()
        shell_puts("  mkdir <n>  - Create directory")
        shell_newline()
        shell_puts("  touch <n>  - Create empty file")
        shell_newline()
        shell_puts("  rm <name>  - Remove file/dir")
        shell_newline()
        shell_puts("  echo <txt> - Print text")
        shell_newline()
        shell_puts("  uname [-a] - System name")
        shell_newline()
        shell_puts("  free       - Memory usage")
        shell_newline()
        shell_puts("  whoami     - Current user")
        shell_newline()
        shell_puts("  hostname   - System hostname")
        shell_newline()
        shell_puts("  date       - Current date")
        shell_newline()
        shell_puts("  uptime     - System uptime")
        shell_newline()
        shell_puts("  version    - Show version")
        shell_newline()
    elif strcmp(cmd, "pwd") == 0:
        shell_newline()
        shell_puts(&shell_cwd[0])
        shell_newline()
    elif strcmp(cmd, "ls") == 0:
        shell_newline()
        idx: int32 = 0
        result: int32 = ramfs_readdir(&shell_cwd[0], idx, &shell_name_buf[0])
        while result >= 0:
            shell_puts(&shell_name_buf[0])
            if result == 1:
                shell_putc('/')
            shell_puts("  ")
            idx = idx + 1
            result = ramfs_readdir(&shell_cwd[0], idx, &shell_name_buf[0])
        shell_newline()
    elif shell_starts_with("cd"):
        arg: Ptr[char] = shell_get_arg()
        if arg[0] == '\0':
            shell_cwd[0] = '/'
            shell_cwd[1] = '\0'
        elif strcmp(arg, "..") == 0:
            cwd_len: int32 = strlen(&shell_cwd[0])
            if cwd_len > 1:
                i: int32 = cwd_len - 1
                if shell_cwd[i] == '/':
                    i = i - 1
                while i > 0 and shell_cwd[i] != '/':
                    i = i - 1
                if i == 0:
                    shell_cwd[0] = '/'
                    shell_cwd[1] = '\0'
                else:
                    shell_cwd[i] = '\0'
        else:
            shell_build_path(arg)
            if ramfs_exists(&shell_path_buf[0]) and ramfs_isdir(&shell_path_buf[0]):
                strcpy(&shell_cwd[0], &shell_path_buf[0])
            else:
                shell_newline()
                shell_puts("No such directory: ")
                shell_puts(arg)
                shell_newline()
    elif shell_starts_with("cat"):
        arg2: Ptr[char] = shell_get_arg()
        if arg2[0] == '\0':
            shell_newline()
            shell_puts("Usage: cat <file>")
            shell_newline()
        else:
            shell_build_path(arg2)
            if ramfs_exists(&shell_path_buf[0]) and not ramfs_isdir(&shell_path_buf[0]):
                shell_newline()
                bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
                if bytes_read > 0:
                    shell_read_buf[bytes_read] = 0
                    shell_puts(cast[Ptr[char]](&shell_read_buf[0]))
                shell_newline()
            else:
                shell_newline()
                shell_puts("No such file: ")
                shell_puts(arg2)
                shell_newline()
    elif shell_starts_with("mkdir"):
        arg3: Ptr[char] = shell_get_arg()
        if arg3[0] == '\0':
            shell_newline()
            shell_puts("Usage: mkdir <name>")
            shell_newline()
        else:
            shell_build_path(arg3)
            if ramfs_create(&shell_path_buf[0], True) >= 0:
                shell_newline()
                shell_puts("Created: ")
                shell_puts(&shell_path_buf[0])
                shell_newline()
            else:
                shell_newline()
                shell_puts("Failed to create directory")
                shell_newline()
    elif shell_starts_with("touch"):
        arg4: Ptr[char] = shell_get_arg()
        if arg4[0] == '\0':
            shell_newline()
            shell_puts("Usage: touch <name>")
            shell_newline()
        else:
            shell_build_path(arg4)
            if ramfs_create(&shell_path_buf[0], False) >= 0:
                shell_newline()
                shell_puts("Created: ")
                shell_puts(&shell_path_buf[0])
                shell_newline()
            else:
                shell_newline()
                shell_puts("Failed to create file")
                shell_newline()
    elif shell_starts_with("rm"):
        arg5: Ptr[char] = shell_get_arg()
        if arg5[0] == '\0':
            shell_newline()
            shell_puts("Usage: rm <name>")
            shell_newline()
        else:
            shell_build_path(arg5)
            if ramfs_delete(&shell_path_buf[0]) >= 0:
                shell_newline()
                shell_puts("Removed: ")
                shell_puts(&shell_path_buf[0])
                shell_newline()
            else:
                shell_newline()
                shell_puts("Failed to remove")
                shell_newline()
    elif shell_starts_with("echo"):
        arg6: Ptr[char] = shell_get_arg()
        shell_newline()
        shell_puts(arg6)
        shell_newline()
    elif strcmp(cmd, "version") == 0:
        shell_newline()
        shell_puts("Pynux Text Shell v0.1")
        shell_newline()
        shell_puts("ARM Cortex-M3")
        shell_newline()
    elif strcmp(cmd, "clear") == 0:
        # VT100 clear screen
        shell_puts("\x1b[2J\x1b[H")
    elif strcmp(cmd, "uname") == 0 or shell_starts_with("uname"):
        shell_newline()
        arg7: Ptr[char] = shell_get_arg()
        if arg7[0] == '\0' or strcmp(arg7, "-s") == 0:
            shell_puts("Pynux")
        elif strcmp(arg7, "-a") == 0:
            shell_puts("Pynux 0.1.0 armv7m Cortex-M3")
        elif strcmp(arg7, "-r") == 0:
            shell_puts("0.1.0")
        elif strcmp(arg7, "-m") == 0:
            shell_puts("armv7m")
        else:
            shell_puts("Pynux")
        shell_newline()
    elif strcmp(cmd, "free") == 0:
        shell_newline()
        shell_puts("       total     used     free")
        shell_newline()
        shell_puts("Heap:  ")
        shell_puts(shell_int_to_str(heap_total()))
        shell_puts("    ")
        shell_puts(shell_int_to_str(heap_used()))
        shell_puts("    ")
        shell_puts(shell_int_to_str(heap_remaining()))
        shell_newline()
    elif strcmp(cmd, "whoami") == 0:
        shell_newline()
        shell_puts("root")
        shell_newline()
    elif strcmp(cmd, "hostname") == 0:
        shell_newline()
        shell_puts("pynux")
        shell_newline()
    elif strcmp(cmd, "date") == 0:
        shell_newline()
        shell_puts("Jan 1 00:00:00 UTC 2025")
        shell_newline()
    elif strcmp(cmd, "uptime") == 0:
        shell_newline()
        shell_puts("up 0 days, 0:00")
        shell_newline()
    else:
        shell_newline()
        shell_puts("Unknown: ")
        shell_puts(cmd)
        shell_newline()

    shell_newline()
    shell_prompt()
    shell_cmd_pos = 0

def shell_input(c: char):
    global shell_cmd_pos

    if c == '\r' or c == '\n':
        shell_newline()
        shell_exec()
        return

    if c == '\x7f' or c == '\b':
        if shell_cmd_pos > 0:
            shell_cmd_pos = shell_cmd_pos - 1
            # VT100 backspace: move left, space, move left
            shell_puts("\b \b")
        return

    # Ctrl+C
    if c == '\x03':
        shell_puts("^C")
        shell_newline()
        shell_cmd_pos = 0
        shell_prompt()
        return

    # Regular char
    if shell_cmd_pos < 255:
        shell_cmd[shell_cmd_pos] = c
        shell_cmd_pos = shell_cmd_pos + 1
        shell_putc(c)

def shell_init():
    shell_cwd[0] = '/'
    shell_cwd[1] = '\0'
    shell_cmd_pos = 0

def shell_main():
    shell_init()

    shell_newline()
    shell_puts("Pynux Text Shell")
    shell_newline()
    shell_puts("Type 'help' for commands")
    shell_newline()
    shell_newline()
    shell_prompt()

    while True:
        if uart_available():
            c: char = uart_getc()
            shell_input(c)
