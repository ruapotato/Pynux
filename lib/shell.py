# Pynux Text Shell
#
# Simple VT100 text-mode shell for debugging.
# No graphics, just plain serial I/O.

from lib.io import uart_putc, uart_getc, uart_available, print_str, print_int
from lib.string import strcmp, strlen, strcpy, strcat, memset, atoi
from kernel.ramfs import ramfs_readdir, ramfs_create, ramfs_delete
from kernel.ramfs import ramfs_read, ramfs_write, ramfs_exists, ramfs_isdir
from lib.memory import heap_remaining, heap_total, heap_used
from kernel.timer import timer_delay_ms, timer_tick
from programs.main import user_main, user_tick

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

# Copy buffer (char version for ramfs_write)
shell_copy_buf: Array[512, char]

# Number buffer for printing integers
shell_num_buf: Array[16, char]

# Source path buffer for cp command
shell_src_path: Array[256, char]

# Job control
# Job states: 0 = stopped, 1 = running (background), 2 = running (foreground)
SHELL_JOB_STOPPED: int32 = 0
SHELL_JOB_RUNNING: int32 = 1
SHELL_JOB_FOREGROUND: int32 = 2

# Job 1: main.py
job1_state: int32 = 1  # Starts running in background
job1_name: Array[16, char]

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

# ============================================================================
# Shell command handlers - split into small functions to avoid branch distance
# issues in ARM Thumb-2 generated code
# ============================================================================

def shell_exec_job(cmd: Ptr[char]) -> bool:
    """Handle job control commands. Returns True if handled."""
    global job1_state

    if strcmp(cmd, "jobs") == 0:
        shell_newline()
        if job1_state == SHELL_JOB_RUNNING:
            shell_puts("[1]   Running                 main.py &")
        elif job1_state == SHELL_JOB_STOPPED:
            shell_puts("[1]+  Stopped                 main.py")
        else:
            shell_puts("[1]   Running                 main.py")
        shell_newline()
        return True

    if strcmp(cmd, "fg") == 0:
        shell_newline()
        if job1_state == SHELL_JOB_STOPPED:
            job1_state = SHELL_JOB_RUNNING
            shell_puts("main.py: continued")
        else:
            shell_puts("main.py: already running")
        shell_newline()
        return True

    if strcmp(cmd, "bg") == 0:
        shell_newline()
        if job1_state == SHELL_JOB_STOPPED:
            job1_state = SHELL_JOB_RUNNING
            shell_puts("[1]+ main.py &")
        else:
            shell_puts("bg: job already in background")
        shell_newline()
        return True

    return False

def shell_exec_basic(cmd: Ptr[char]) -> bool:
    """Handle basic shell commands. Returns True if handled."""

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
        shell_puts("  jobs/fg/bg - Job control")
        shell_newline()
        shell_puts("  version    - Show version")
        shell_newline()
        return True

    if strcmp(cmd, "pwd") == 0:
        shell_newline()
        shell_puts(&shell_cwd[0])
        shell_newline()
        return True

    if shell_starts_with("echo"):
        arg: Ptr[char] = shell_get_arg()
        shell_newline()
        shell_puts(arg)
        shell_newline()
        return True

    if strcmp(cmd, "version") == 0:
        shell_newline()
        shell_puts("Pynux Text Shell v0.1")
        shell_newline()
        shell_puts("ARM Cortex-M3")
        shell_newline()
        return True

    if strcmp(cmd, "clear") == 0:
        shell_puts("\x1b[2J\x1b[H")
        return True

    if strcmp(cmd, "reset") == 0:
        shell_puts("\x1b[2J\x1b[H")
        return True

    return False

def shell_exec_file(cmd: Ptr[char]) -> bool:
    """Handle file system commands. Returns True if handled."""

    if shell_starts_with("ls"):
        shell_newline()
        ls_arg: Ptr[char] = shell_get_arg()
        ls_path: Ptr[char] = &shell_cwd[0]
        if ls_arg[0] != '\0':
            if ls_arg[0] == '/':
                ls_path = ls_arg
            else:
                shell_build_path(ls_arg)
                ls_path = &shell_path_buf[0]
        if not ramfs_exists(ls_path):
            shell_puts("ls: cannot access '")
            shell_puts(ls_arg)
            shell_puts("': No such file or directory")
            shell_newline()
        elif not ramfs_isdir(ls_path):
            shell_puts(ls_arg)
            shell_newline()
        else:
            idx: int32 = 0
            result: int32 = ramfs_readdir(ls_path, idx, &shell_name_buf[0])
            while result >= 0:
                shell_puts(&shell_name_buf[0])
                if result == 1:
                    shell_putc('/')
                shell_puts("  ")
                idx = idx + 1
                result = ramfs_readdir(ls_path, idx, &shell_name_buf[0])
            shell_newline()
        return True

    if shell_starts_with("cd"):
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
        return True

    if shell_starts_with("cat"):
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
        return True

    if shell_starts_with("mkdir"):
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
        return True

    if shell_starts_with("touch"):
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
        return True

    if shell_starts_with("rm"):
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
        return True

    return False

def shell_exec_sys(cmd: Ptr[char]) -> bool:
    """Handle system info commands. Returns True if handled."""

    if shell_starts_with("uname"):
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
        return True

    if strcmp(cmd, "free") == 0:
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
        return True

    if strcmp(cmd, "whoami") == 0:
        shell_newline()
        shell_puts("root")
        shell_newline()
        return True

    if strcmp(cmd, "hostname") == 0:
        shell_newline()
        shell_puts("pynux")
        shell_newline()
        return True

    if strcmp(cmd, "date") == 0:
        shell_newline()
        shell_puts("Jan 1 00:00:00 UTC 2025")
        shell_newline()
        return True

    if strcmp(cmd, "uptime") == 0:
        shell_newline()
        shell_puts("up 0 days, 0:00")
        shell_newline()
        return True

    if strcmp(cmd, "id") == 0:
        shell_newline()
        shell_puts("uid=0(root) gid=0(root)")
        shell_newline()
        return True

    if strcmp(cmd, "env") == 0:
        shell_newline()
        shell_puts("HOME=/home")
        shell_newline()
        shell_puts("USER=root")
        shell_newline()
        shell_puts("SHELL=/bin/psh")
        shell_newline()
        shell_puts("PWD=")
        shell_puts(&shell_cwd[0])
        shell_newline()
        return True

    if strcmp(cmd, "printenv") == 0:
        shell_newline()
        shell_puts("HOME=/home")
        shell_newline()
        shell_puts("USER=root")
        shell_newline()
        shell_puts("SHELL=/bin/psh")
        shell_newline()
        shell_puts("PATH=/bin")
        shell_newline()
        shell_puts("TERM=vt100")
        shell_newline()
        shell_puts("PWD=")
        shell_puts(&shell_cwd[0])
        shell_newline()
        return True

    if strcmp(cmd, "arch") == 0:
        shell_newline()
        shell_puts("armv7m")
        shell_newline()
        return True

    if strcmp(cmd, "nproc") == 0:
        shell_newline()
        shell_puts("1")
        shell_newline()
        return True

    if strcmp(cmd, "tty") == 0:
        shell_newline()
        shell_puts("/dev/ttyS0")
        shell_newline()
        return True

    if strcmp(cmd, "logname") == 0:
        shell_newline()
        shell_puts("root")
        shell_newline()
        return True

    if strcmp(cmd, "dmesg") == 0:
        shell_newline()
        shell_puts("[    0.000] Pynux kernel booting...")
        shell_newline()
        shell_puts("[    0.001] UART initialized")
        shell_newline()
        shell_puts("[    0.002] Heap initialized (16KB)")
        shell_newline()
        shell_puts("[    0.003] Timer initialized")
        shell_newline()
        shell_puts("[    0.004] RAMFS initialized")
        shell_newline()
        shell_puts("[    0.005] Kernel ready")
        shell_newline()
        return True

    if strcmp(cmd, "lscpu") == 0:
        shell_newline()
        shell_puts("Architecture:    armv7m")
        shell_newline()
        shell_puts("Vendor:          ARM")
        shell_newline()
        shell_puts("Model:           Cortex-M3")
        shell_newline()
        shell_puts("CPU(s):          1")
        shell_newline()
        shell_puts("Max MHz:         25")
        shell_newline()
        return True

    if strcmp(cmd, "df") == 0:
        shell_newline()
        shell_puts("Filesystem  1K-blocks  Used  Available  Use%  Mounted on")
        shell_newline()
        shell_puts("ramfs            16     ")
        used_kb: int32 = heap_used() / 1024
        shell_puts(shell_int_to_str(used_kb))
        shell_puts("         ")
        free_kb: int32 = heap_remaining() / 1024
        shell_puts(shell_int_to_str(free_kb))
        shell_puts("     ")
        pct: int32 = (heap_used() * 100) / heap_total()
        shell_puts(shell_int_to_str(pct))
        shell_puts("%   /")
        shell_newline()
        return True

    if strcmp(cmd, "mount") == 0:
        shell_newline()
        shell_puts("ramfs on / type ramfs (rw)")
        shell_newline()
        return True

    if strcmp(cmd, "umount") == 0:
        shell_newline()
        shell_puts("umount: cannot unmount /: device is busy")
        shell_newline()
        return True

    if strcmp(cmd, "ps") == 0:
        shell_newline()
        shell_puts("  PID TTY      TIME CMD")
        shell_newline()
        shell_puts("    1 ttyS0    0:00 psh")
        shell_newline()
        return True

    if strcmp(cmd, "users") == 0:
        shell_newline()
        shell_puts("root")
        shell_newline()
        return True

    if strcmp(cmd, "groups") == 0:
        shell_newline()
        shell_puts("root")
        shell_newline()
        return True

    if strcmp(cmd, "sync") == 0:
        shell_newline()
        return True

    if strcmp(cmd, "kill") == 0:
        shell_newline()
        shell_puts("kill: No processes to kill")
        shell_newline()
        return True

    return False

def shell_exec_file2(cmd: Ptr[char]) -> bool:
    """Handle more file commands (write, cp, head, tail, wc, stat)."""

    if shell_starts_with("write"):
        arg8: Ptr[char] = shell_get_arg()
        if arg8[0] == '\0':
            shell_newline()
            shell_puts("Usage: write <file> <content>")
            shell_newline()
        else:
            i: int32 = 0
            while arg8[i] != '\0' and arg8[i] != ' ':
                i = i + 1
            if arg8[i] == ' ':
                arg8[i] = '\0'
                content: Ptr[char] = &arg8[i + 1]
                shell_build_path(arg8)
                if not ramfs_exists(&shell_path_buf[0]):
                    ramfs_create(&shell_path_buf[0], False)
                content_len: int32 = strlen(content)
                if ramfs_write(&shell_path_buf[0], content) >= 0:
                    shell_newline()
                    shell_puts("Wrote ")
                    shell_puts(shell_int_to_str(content_len))
                    shell_puts(" bytes to ")
                    shell_puts(&shell_path_buf[0])
                    shell_newline()
                else:
                    shell_newline()
                    shell_puts("Failed to write")
                    shell_newline()
            else:
                shell_newline()
                shell_puts("Usage: write <file> <content>")
                shell_newline()
        return True

    if shell_starts_with("cp"):
        arg9: Ptr[char] = shell_get_arg()
        if arg9[0] == '\0':
            shell_newline()
            shell_puts("Usage: cp <src> <dst>")
            shell_newline()
        else:
            i: int32 = 0
            while arg9[i] != '\0' and arg9[i] != ' ':
                i = i + 1
            if arg9[i] == ' ':
                arg9[i] = '\0'
                dst: Ptr[char] = &arg9[i + 1]
                while dst[0] == ' ':
                    dst = &dst[1]
                if dst[0] != '\0':
                    shell_build_path(arg9)
                    strcpy(&shell_src_path[0], &shell_path_buf[0])
                    if ramfs_exists(&shell_src_path[0]) and not ramfs_isdir(&shell_src_path[0]):
                        bytes_read: int32 = ramfs_read(&shell_src_path[0], &shell_read_buf[0], 511)
                        if bytes_read >= 0:
                            # Copy uint8 buffer to char buffer
                            j: int32 = 0
                            while j < bytes_read:
                                shell_copy_buf[j] = cast[char](shell_read_buf[j])
                                j = j + 1
                            shell_copy_buf[bytes_read] = '\0'
                            shell_build_path(dst)
                            if not ramfs_exists(&shell_path_buf[0]):
                                ramfs_create(&shell_path_buf[0], False)
                            ramfs_write(&shell_path_buf[0], &shell_copy_buf[0])
                            shell_newline()
                            shell_puts("Copied ")
                            shell_puts(&shell_src_path[0])
                            shell_puts(" -> ")
                            shell_puts(&shell_path_buf[0])
                            shell_newline()
                        else:
                            shell_newline()
                            shell_puts("Failed to read source")
                            shell_newline()
                    else:
                        shell_newline()
                        shell_puts("Source not found: ")
                        shell_puts(arg9)
                        shell_newline()
                else:
                    shell_newline()
                    shell_puts("Usage: cp <src> <dst>")
                    shell_newline()
            else:
                shell_newline()
                shell_puts("Usage: cp <src> <dst>")
                shell_newline()
        return True

    if shell_starts_with("head"):
        arg16: Ptr[char] = shell_get_arg()
        if arg16[0] == '\0':
            shell_newline()
            shell_puts("Usage: head <file>")
            shell_newline()
        else:
            shell_build_path(arg16)
            if ramfs_exists(&shell_path_buf[0]) and not ramfs_isdir(&shell_path_buf[0]):
                shell_newline()
                bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
                if bytes_read > 0:
                    shell_read_buf[bytes_read] = 0
                    lines: int32 = 0
                    i: int32 = 0
                    while i < bytes_read and lines < 10:
                        shell_putc(cast[char](shell_read_buf[i]))
                        if shell_read_buf[i] == 10:
                            lines = lines + 1
                        i = i + 1
                shell_newline()
            else:
                shell_newline()
                shell_puts("No such file: ")
                shell_puts(arg16)
                shell_newline()
        return True

    if shell_starts_with("tail"):
        arg17: Ptr[char] = shell_get_arg()
        if arg17[0] == '\0':
            shell_newline()
            shell_puts("Usage: tail <file>")
            shell_newline()
        else:
            shell_build_path(arg17)
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
                shell_puts(arg17)
                shell_newline()
        return True

    return False

def shell_exec_file3(cmd: Ptr[char]) -> bool:
    """Handle wc, stat, mv commands. Returns True if handled."""

    if shell_starts_with("wc"):
        arg18: Ptr[char] = shell_get_arg()
        if arg18[0] == '\0':
            shell_newline()
            shell_puts("Usage: wc <file>")
            shell_newline()
        else:
            shell_build_path(arg18)
            if ramfs_exists(&shell_path_buf[0]) and not ramfs_isdir(&shell_path_buf[0]):
                bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
                lines: int32 = 0
                words: int32 = 0
                chars: int32 = bytes_read
                in_word: bool = False
                i: int32 = 0
                while i < bytes_read:
                    c: char = cast[char](shell_read_buf[i])
                    if c == '\n':
                        lines = lines + 1
                        in_word = False
                    elif c == ' ' or c == '\t':
                        in_word = False
                    else:
                        if not in_word:
                            words = words + 1
                            in_word = True
                    i = i + 1
                shell_newline()
                shell_puts("  ")
                shell_puts(shell_int_to_str(lines))
                shell_puts("  ")
                shell_puts(shell_int_to_str(words))
                shell_puts("  ")
                shell_puts(shell_int_to_str(chars))
                shell_puts(" ")
                shell_puts(arg18)
                shell_newline()
            else:
                shell_newline()
                shell_puts("No such file: ")
                shell_puts(arg18)
                shell_newline()
        return True

    if shell_starts_with("stat"):
        arg19: Ptr[char] = shell_get_arg()
        if arg19[0] == '\0':
            shell_newline()
            shell_puts("Usage: stat <file>")
            shell_newline()
        else:
            shell_build_path(arg19)
            if ramfs_exists(&shell_path_buf[0]):
                shell_newline()
                shell_puts("  File: ")
                shell_puts(&shell_path_buf[0])
                shell_newline()
                if ramfs_isdir(&shell_path_buf[0]):
                    shell_puts("  Type: directory")
                    shell_newline()
                else:
                    shell_puts("  Type: regular file")
                    shell_newline()
                    bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
                    shell_puts("  Size: ")
                    shell_puts(shell_int_to_str(bytes_read))
                    shell_puts(" bytes")
                    shell_newline()
            else:
                shell_newline()
                shell_puts("No such file: ")
                shell_puts(arg19)
                shell_newline()
        return True

    if shell_starts_with("mv"):
        arg20: Ptr[char] = shell_get_arg()
        if arg20[0] == '\0':
            shell_newline()
            shell_puts("Usage: mv <src> <dst>")
            shell_newline()
        else:
            i: int32 = 0
            while arg20[i] != '\0' and arg20[i] != ' ':
                i = i + 1
            if arg20[i] == ' ':
                arg20[i] = '\0'
                dst: Ptr[char] = &arg20[i + 1]
                while dst[0] == ' ':
                    dst = &dst[1]
                if dst[0] != '\0':
                    shell_build_path(arg20)
                    strcpy(&shell_src_path[0], &shell_path_buf[0])
                    if ramfs_exists(&shell_src_path[0]) and not ramfs_isdir(&shell_src_path[0]):
                        bytes_read: int32 = ramfs_read(&shell_src_path[0], &shell_read_buf[0], 511)
                        if bytes_read >= 0:
                            # Copy uint8 buffer to char buffer
                            j: int32 = 0
                            while j < bytes_read:
                                shell_copy_buf[j] = cast[char](shell_read_buf[j])
                                j = j + 1
                            shell_copy_buf[bytes_read] = '\0'
                            shell_build_path(dst)
                            if not ramfs_exists(&shell_path_buf[0]):
                                ramfs_create(&shell_path_buf[0], False)
                            ramfs_write(&shell_path_buf[0], &shell_copy_buf[0])
                            ramfs_delete(&shell_src_path[0])
                            shell_newline()
                            shell_puts("Moved ")
                            shell_puts(&shell_src_path[0])
                            shell_puts(" -> ")
                            shell_puts(&shell_path_buf[0])
                            shell_newline()
                        else:
                            shell_newline()
                            shell_puts("Failed to read source")
                            shell_newline()
                    else:
                        shell_newline()
                        shell_puts("Source not found: ")
                        shell_puts(arg20)
                        shell_newline()
                else:
                    shell_newline()
                    shell_puts("Usage: mv <src> <dst>")
                    shell_newline()
            else:
                shell_newline()
                shell_puts("Usage: mv <src> <dst>")
                shell_newline()
        return True

    return False

def shell_exec_util(cmd: Ptr[char]) -> bool:
    """Handle utility commands. Returns True if handled."""

    if strcmp(cmd, "true") == 0:
        return True

    if strcmp(cmd, "false") == 0:
        shell_newline()
        return True

    if strcmp(cmd, "yes") == 0:
        shell_newline()
        shell_puts("y")
        shell_newline()
        return True

    if shell_starts_with("sleep"):
        arg10: Ptr[char] = shell_get_arg()
        if arg10[0] == '\0':
            shell_newline()
            shell_puts("Usage: sleep <seconds>")
            shell_newline()
        else:
            secs: int32 = atoi(arg10)
            if secs > 0 and secs <= 60:
                shell_newline()
                shell_puts("Sleeping for ")
                shell_puts(shell_int_to_str(secs))
                shell_puts(" seconds...")
                shell_newline()
                timer_delay_ms(secs * 1000)
                shell_puts("Done.")
                shell_newline()
            else:
                shell_newline()
                shell_puts("Invalid sleep time (1-60)")
                shell_newline()
        return True

    if strcmp(cmd, "reboot") == 0:
        shell_newline()
        shell_puts("Rebooting...")
        shell_newline()
        timer_delay_ms(1000)
        NVIC_AIRCR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED0C)
        NVIC_AIRCR[0] = 0x05FA0004
        while True:
            pass

    if strcmp(cmd, "halt") == 0 or strcmp(cmd, "poweroff") == 0 or strcmp(cmd, "exit") == 0:
        shell_newline()
        shell_puts("System halted.")
        shell_newline()
        SEMIHOST_EXIT: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000EDF0)
        SEMIHOST_EXIT[0] = 0x20026
        while True:
            pass

    if shell_starts_with("seq"):
        arg11: Ptr[char] = shell_get_arg()
        if arg11[0] == '\0':
            shell_newline()
            shell_puts("Usage: seq [start] end")
            shell_newline()
        else:
            start: int32 = 1
            end: int32 = 0
            i: int32 = 0
            while arg11[i] != '\0' and arg11[i] != ' ':
                i = i + 1
            if arg11[i] == ' ':
                arg11[i] = '\0'
                start = atoi(arg11)
                end = atoi(&arg11[i + 1])
            else:
                end = atoi(arg11)
            shell_newline()
            j: int32 = start
            while j <= end:
                shell_puts(shell_int_to_str(j))
                shell_newline()
                j = j + 1
        return True

    if shell_starts_with("factor"):
        arg12: Ptr[char] = shell_get_arg()
        if arg12[0] == '\0':
            shell_newline()
            shell_puts("Usage: factor <number>")
            shell_newline()
        else:
            n: int32 = atoi(arg12)
            shell_newline()
            shell_puts(shell_int_to_str(n))
            shell_puts(": ")
            if n >= 2:
                while n % 2 == 0:
                    shell_puts("2 ")
                    n = n / 2
                i: int32 = 3
                while i * i <= n:
                    while n % i == 0:
                        shell_puts(shell_int_to_str(i))
                        shell_putc(' ')
                        n = n / i
                    i = i + 2
                if n > 1:
                    shell_puts(shell_int_to_str(n))
            shell_newline()
        return True

    if strcmp(cmd, "fortune") == 0:
        shell_newline()
        fortunes: Array[10, Ptr[char]]
        fortunes[0] = "The best way to predict the future is to invent it."
        fortunes[1] = "In theory, there is no difference between theory and practice."
        fortunes[2] = "Simplicity is the ultimate sophistication."
        fortunes[3] = "First, solve the problem. Then, write the code."
        fortunes[4] = "Talk is cheap. Show me the code."
        fortunes[5] = "The only way to go fast is to go well."
        fortunes[6] = "Any fool can write code that a computer can understand."
        fortunes[7] = "Debugging is twice as hard as writing the code."
        fortunes[8] = "It works on my machine."
        fortunes[9] = "There are only two hard things: cache invalidation and naming."
        idx: int32 = heap_used() % 10
        shell_puts(fortunes[idx])
        shell_newline()
        return True

    if shell_starts_with("basename"):
        arg13: Ptr[char] = shell_get_arg()
        if arg13[0] == '\0':
            shell_newline()
            shell_puts("Usage: basename <path>")
            shell_newline()
        else:
            i: int32 = strlen(arg13) - 1
            while i >= 0 and arg13[i] != '/':
                i = i - 1
            shell_newline()
            shell_puts(&arg13[i + 1])
            shell_newline()
        return True

    if shell_starts_with("dirname"):
        arg14: Ptr[char] = shell_get_arg()
        if arg14[0] == '\0':
            shell_newline()
            shell_puts("Usage: dirname <path>")
            shell_newline()
        else:
            i: int32 = strlen(arg14) - 1
            while i > 0 and arg14[i] != '/':
                i = i - 1
            shell_newline()
            if i == 0:
                if arg14[0] == '/':
                    shell_putc('/')
                else:
                    shell_putc('.')
            else:
                arg14[i] = '\0'
                shell_puts(arg14)
            shell_newline()
        return True

    if shell_starts_with("banner"):
        arg15: Ptr[char] = shell_get_arg()
        if arg15[0] == '\0':
            shell_newline()
            shell_puts("Usage: banner <text>")
            shell_newline()
        else:
            shell_newline()
            line: int32 = 0
            while line < 5:
                i: int32 = 0
                while arg15[i] != '\0':
                    c: char = arg15[i]
                    j: int32 = 0
                    while j < 5:
                        if c >= 'a' and c <= 'z':
                            shell_putc(cast[char](cast[int32](c) - 32))
                        elif c == ' ':
                            shell_putc(' ')
                        else:
                            shell_putc(c)
                        j = j + 1
                    shell_putc(' ')
                    i = i + 1
                shell_newline()
                line = line + 1
        return True

    if shell_starts_with("cal"):
        shell_newline()
        shell_puts("    January 2025\r\nSu Mo Tu We Th Fr Sa\r\n          1  2  3  4\r\n 5  6  7  8  9 10 11\r\n12 13 14 15 16 17 18\r\n19 20 21 22 23 24 25\r\n26 27 28 29 30 31")
        shell_newline()
        return True

    return False

# ============================================================================
# Main shell_exec dispatcher - calls smaller functions to avoid branch issues
# ============================================================================

def shell_exec():
    global shell_cmd_pos

    shell_cmd[shell_cmd_pos] = '\0'

    if shell_cmd_pos == 0:
        shell_prompt()
        return

    cmd: Ptr[char] = &shell_cmd[0]

    # Try each handler in turn - each returns True if it handled the command
    if shell_exec_job(cmd):
        pass
    elif shell_exec_basic(cmd):
        pass
    elif shell_exec_file(cmd):
        pass
    elif shell_exec_sys(cmd):
        pass
    elif shell_exec_file2(cmd):
        pass
    elif shell_exec_file3(cmd):
        pass
    elif shell_exec_util(cmd):
        pass
    else:
        # Unknown command
        shell_newline()
        shell_puts("Unknown: ")
        shell_puts(cmd)
        shell_newline()

    shell_newline()
    shell_prompt()
    shell_cmd_pos = 0

def shell_input(c: char):
    global shell_cmd_pos, job1_state

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

    # Ctrl+C - cancel current command line
    if c == '\x03':
        shell_puts("^C")
        shell_newline()
        shell_cmd_pos = 0
        shell_prompt()
        return

    # Ctrl+Z - suspend foreground job
    if c == '\x1a':
        shell_puts("^Z")
        shell_newline()
        if job1_state == SHELL_JOB_RUNNING:
            job1_state = SHELL_JOB_STOPPED
            shell_puts("[1]+  Stopped                 main.py")
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
    global job1_state
    shell_init()

    shell_newline()
    shell_puts("Pynux Text Shell")
    shell_newline()
    shell_puts("Type 'help' for commands")
    shell_newline()
    shell_newline()

    # Run user main.py startup
    shell_puts("[1] main.py &")
    shell_newline()
    job1_state = SHELL_JOB_RUNNING
    user_main()
    shell_newline()

    shell_prompt()

    while True:
        # Update timer (must be called regularly for timer_get_ticks to work)
        timer_tick()

        # Call user tick function only if job is running (not stopped)
        if job1_state != SHELL_JOB_STOPPED:
            user_tick()

        if uart_available():
            c: char = uart_getc()
            shell_input(c)
