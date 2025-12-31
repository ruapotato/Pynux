# Pynux Text Shell
#
# Simple VT100 text-mode shell for debugging.
# No graphics, just plain serial I/O.

from lib.io import uart_putc, uart_getc, uart_available, print_str, print_int
from lib.string import strcmp, strlen, strcpy, strcat, memset, atoi
from kernel.ramfs import ramfs_readdir, ramfs_create, ramfs_delete
from kernel.ramfs import ramfs_read, ramfs_write, ramfs_exists, ramfs_isdir, ramfs_size
from kernel.devfs import devfs_find_by_path, devfs_read, devfs_write, devfs_list_drivers
from kernel.devfs import devfs_scan_drivers, devfs_get_count, devfs_get_path, devfs_get_type
from lib.memory import heap_remaining, heap_total, heap_used
from kernel.timer import timer_delay_ms, timer_tick
from programs.main import user_main, user_tick
from programs.calc import calc_main
from programs.clock import clock_main
from programs.hexview import hexview_main
from programs.imgview import imgview_main
from programs.sensormon import sensormon_main
from programs.motorctl import motorctl_main
from lib.sensors import sensors_seed, sensors_enable_noise, sensors_init_all
from lib.sensors import temp_read, temp_to_fahrenheit
from lib.sensors import accel_read_x, accel_read_y, accel_read_z
from lib.sensors import light_read, humid_read, press_read, press_to_altitude
from lib.motors import servo_init, servo_set_angle, servo_get_angle
from lib.motors import stepper_init, stepper_steps, stepper_get_position
from lib.motors import dc_init, dc_set_speed, dc_get_speed, dc_brake
from lib.math import abs_int

# Command buffer
shell_cmd: Array[256, char]
shell_cmd_pos: int32 = 0

# Command history (10 commands, 256 chars each)
HISTORY_SIZE: int32 = 10
shell_history: Array[2560, char]  # 10 * 256
shell_history_count: int32 = 0
shell_history_pos: int32 = 0  # Current position when navigating
shell_history_idx: int32 = 0  # Next write position (circular)

# Escape sequence state for arrow keys (using array for reliable global storage)
shell_esc: Array[4, int32]  # [0]=state: 0=normal, 1=got ESC, 2=got [

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

# Grep pattern buffer
shell_grep_pat: Array[64, char]

# Line buffer for grep
shell_line_buf: Array[256, char]

# Find command buffers
shell_find_pat: Array[64, char]
shell_find_path: Array[256, char]
shell_find_buf: Array[64, char]  # for readdir names

# Sed command buffers
shell_sed_old: Array[64, char]
shell_sed_new: Array[64, char]
shell_sed_out: Array[512, char]

# Tab completion buffers
shell_tab_prefix: Array[64, char]
shell_tab_match: Array[64, char]
shell_tab_dir: Array[256, char]

# Job control
# Job states: 0 = stopped, 1 = running (background), 2 = running (foreground), 3 = terminated
SHELL_JOB_STOPPED: int32 = 0
SHELL_JOB_RUNNING: int32 = 1
SHELL_JOB_FOREGROUND: int32 = 2
SHELL_JOB_TERMINATED: int32 = 3

# Job 1: main.py
job1_state: int32 = 1  # Starts running in background
job1_name: Array[16, char]

# Flag to track if we're in foreground mode (for Ctrl+C handling)
shell_fg_mode: int32 = 0  # 0 = normal shell, 1 = fg running

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

def str_contains(haystack: Ptr[char], needle: Ptr[char]) -> bool:
    """Check if haystack contains needle."""
    if needle[0] == '\0':
        return True
    hi: int32 = 0
    while haystack[hi] != '\0':
        # Try to match needle starting at position hi
        ni: int32 = 0
        found: bool = True
        while needle[ni] != '\0' and found:
            if haystack[hi + ni] == '\0' or haystack[hi + ni] != needle[ni]:
                found = False
            ni = ni + 1
        if found:
            return True
        hi = hi + 1
    return False

# ============================================================================
# Command history functions
# ============================================================================

def history_add(cmd: Ptr[char]):
    """Add command to history."""
    global shell_history_count, shell_history_idx

    # Don't add empty commands
    if cmd[0] == '\0':
        return

    # Don't add if same as previous command
    if shell_history_count > 0:
        prev_idx: int32 = (shell_history_idx - 1 + HISTORY_SIZE) % HISTORY_SIZE
        prev_base: int32 = prev_idx * 256
        if strcmp(cmd, &shell_history[prev_base]) == 0:
            return

    # Copy command to history at current index
    base: int32 = shell_history_idx * 256
    i: int32 = 0
    while i < 255 and cmd[i] != '\0':
        shell_history[base + i] = cmd[i]
        i = i + 1
    shell_history[base + i] = '\0'

    # Advance index (circular)
    shell_history_idx = (shell_history_idx + 1) % HISTORY_SIZE

    # Track count (max HISTORY_SIZE)
    if shell_history_count < HISTORY_SIZE:
        shell_history_count = shell_history_count + 1

def history_get(index: int32) -> Ptr[char]:
    """Get command from history. 0 = most recent."""
    if index < 0 or index >= shell_history_count:
        return Ptr[char](0)

    # Calculate actual position (going backwards from last)
    pos: int32 = (shell_history_idx - 1 - index + HISTORY_SIZE) % HISTORY_SIZE
    base: int32 = pos * 256
    return &shell_history[base]

def history_reset_pos():
    """Reset history navigation position."""
    global shell_history_pos
    shell_history_pos = -1

def shell_clear_line():
    """Clear current command line on screen."""
    global shell_cmd_pos
    # Move cursor to start of input and clear to end of line
    while shell_cmd_pos > 0:
        shell_putc('\b')
        shell_cmd_pos = shell_cmd_pos - 1
    # VT100: clear from cursor to end of line
    shell_puts("\x1b[K")

def shell_set_cmd(s: Ptr[char]):
    """Set command buffer and display it."""
    global shell_cmd_pos
    # NULL check to prevent crash
    if cast[uint32](s) == 0:
        return
    shell_clear_line()
    i: int32 = 0
    while i < 255 and s[i] != '\0':
        shell_cmd[i] = s[i]
        shell_putc(s[i])
        i = i + 1
    shell_cmd[i] = '\0'
    shell_cmd_pos = i

def shell_tab_complete():
    """Handle tab completion for file/directory names."""
    global shell_cmd_pos

    # Find start of current word
    word_start: int32 = shell_cmd_pos
    while word_start > 0 and shell_cmd[word_start - 1] != ' ':
        word_start = word_start - 1

    # Extract current word as prefix
    prefix_len: int32 = shell_cmd_pos - word_start
    if prefix_len > 63:
        prefix_len = 63
    i: int32 = 0
    while i < prefix_len:
        shell_tab_prefix[i] = shell_cmd[word_start + i]
        i = i + 1
    shell_tab_prefix[prefix_len] = '\0'

    # Determine directory to search and file prefix
    dir_path: Ptr[char] = &shell_cwd[0]
    file_prefix: Ptr[char] = &shell_tab_prefix[0]

    # Check if prefix contains /
    last_slash: int32 = -1
    i = 0
    while shell_tab_prefix[i] != '\0':
        if shell_tab_prefix[i] == '/':
            last_slash = i
        i = i + 1

    if last_slash >= 0:
        # Has path component
        strcpy(&shell_tab_dir[0], &shell_tab_prefix[0])
        shell_tab_dir[last_slash + 1] = '\0'
        shell_build_path(&shell_tab_dir[0])
        dir_path = &shell_path_buf[0]
        file_prefix = &shell_tab_prefix[last_slash + 1]

    # Count and find matches
    match_count: int32 = 0
    idx: int32 = 0
    result: int32 = ramfs_readdir(dir_path, idx, &shell_name_buf[0])
    while result >= 0:
        # Check if name starts with prefix
        j: int32 = 0
        is_match: bool = True
        while file_prefix[j] != '\0' and is_match:
            if shell_name_buf[j] != file_prefix[j]:
                is_match = False
            j = j + 1

        if is_match:
            match_count = match_count + 1
            strcpy(&shell_tab_match[0], &shell_name_buf[0])

        idx = idx + 1
        result = ramfs_readdir(dir_path, idx, &shell_name_buf[0])

    if match_count == 1:
        # Single match - complete it
        # Calculate how much to add
        prefix_file_len: int32 = strlen(file_prefix)
        match_len: int32 = strlen(&shell_tab_match[0])
        add_len: int32 = match_len - prefix_file_len

        # Add remaining characters to command
        j: int32 = 0
        while j < add_len and shell_cmd_pos < 255:
            shell_cmd[shell_cmd_pos] = shell_tab_match[prefix_file_len + j]
            shell_putc(shell_tab_match[prefix_file_len + j])
            shell_cmd_pos = shell_cmd_pos + 1
            j = j + 1
        shell_cmd[shell_cmd_pos] = '\0'

        # Add trailing / for directories or space for files
        if last_slash >= 0:
            strcpy(&shell_tab_dir[0], &shell_tab_prefix[0])
            shell_tab_dir[last_slash + 1] = '\0'
            strcat(&shell_tab_dir[0], &shell_tab_match[0])
            shell_build_path(&shell_tab_dir[0])
        else:
            shell_build_path(&shell_tab_match[0])

        if ramfs_isdir(&shell_path_buf[0]):
            if shell_cmd_pos < 255:
                shell_cmd[shell_cmd_pos] = '/'
                shell_putc('/')
                shell_cmd_pos = shell_cmd_pos + 1
                shell_cmd[shell_cmd_pos] = '\0'
        else:
            if shell_cmd_pos < 255:
                shell_cmd[shell_cmd_pos] = ' '
                shell_putc(' ')
                shell_cmd_pos = shell_cmd_pos + 1
                shell_cmd[shell_cmd_pos] = '\0'

    elif match_count > 1:
        # Multiple matches - show them
        shell_newline()
        idx = 0
        result = ramfs_readdir(dir_path, idx, &shell_name_buf[0])
        while result >= 0:
            j: int32 = 0
            is_match: bool = True
            while file_prefix[j] != '\0' and is_match:
                if shell_name_buf[j] != file_prefix[j]:
                    is_match = False
                j = j + 1

            if is_match:
                shell_puts(&shell_name_buf[0])
                if result == 1:
                    shell_putc('/')
                shell_puts("  ")

            idx = idx + 1
            result = ramfs_readdir(dir_path, idx, &shell_name_buf[0])

        shell_newline()
        shell_prompt()
        # Re-display current command
        i = 0
        while i < shell_cmd_pos:
            shell_putc(shell_cmd[i])
            i = i + 1

# ============================================================================
# Shell command handlers - split into small functions to avoid branch distance
# issues in ARM Thumb-2 generated code
# ============================================================================

def shell_exec_job(cmd: Ptr[char]) -> bool:
    """Handle job control commands. Returns True if handled."""
    global job1_state, shell_fg_mode

    if strcmp(cmd, "jobs") == 0:
        shell_newline()
        if job1_state == SHELL_JOB_RUNNING:
            shell_puts("[1]   Running                 main.py &")
        elif job1_state == SHELL_JOB_STOPPED:
            shell_puts("[1]+  Stopped                 main.py")
        elif job1_state == SHELL_JOB_TERMINATED:
            shell_puts("[1]   Terminated              main.py")
        elif job1_state == SHELL_JOB_FOREGROUND:
            shell_puts("[1]   Running                 main.py")
        shell_newline()
        return True

    if strcmp(cmd, "fg") == 0:
        shell_newline()
        if job1_state == SHELL_JOB_TERMINATED:
            shell_puts("fg: job has terminated")
        elif job1_state == SHELL_JOB_STOPPED or job1_state == SHELL_JOB_RUNNING:
            job1_state = SHELL_JOB_FOREGROUND
            shell_fg_mode = 1
            shell_puts("main.py")
            shell_newline()
            shell_puts("(Press Ctrl+C to stop)")
        else:
            shell_puts("main.py: already in foreground")
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
        shell_puts("Hardware:")
        shell_newline()
        shell_puts("  sensors    - Read all sensors")
        shell_newline()
        shell_puts("  servo N A  - Set servo N to angle A")
        shell_newline()
        shell_puts("  stepper N S- Move stepper N by S steps")
        shell_newline()
        shell_puts("  motor N S  - Set motor N to speed S")
        shell_newline()
        shell_puts("Apps: calc, clock, sensormon, motorctl")
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

        # Check for redirection: echo VALUE > /path
        redir_pos: int32 = -1
        i: int32 = 0
        while arg[i] != '\0':
            if arg[i] == '>':
                redir_pos = i
                break
            i = i + 1

        if redir_pos > 0:
            # Extract value (before >)
            value_buf: Array[64, char]
            j: int32 = 0
            while j < redir_pos and j < 63:
                value_buf[j] = arg[j]
                j = j + 1
            # Trim trailing spaces
            while j > 0 and value_buf[j - 1] == ' ':
                j = j - 1
            value_buf[j] = '\0'

            # Extract path (after >)
            k: int32 = redir_pos + 1
            while arg[k] == ' ':
                k = k + 1
            shell_build_path(&arg[k])

            # Check if device file
            dev_idx: int32 = devfs_find_by_path(&shell_path_buf[0])
            if dev_idx >= 0:
                devfs_write(dev_idx, &value_buf[0])
                shell_puts("OK")
            else:
                # Write to regular file
                ramfs_write(&shell_path_buf[0], &value_buf[0])
                shell_puts("OK")
        else:
            # No redirection, just print
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

    if strcmp(cmd, "calc") == 0:
        shell_newline()
        shell_puts("Calculator (text mode not supported, requires VTNext)")
        shell_newline()
        return True

    if strcmp(cmd, "clock") == 0:
        shell_newline()
        shell_puts("Clock (text mode not supported, requires VTNext)")
        shell_newline()
        return True

    if shell_starts_with("hexview"):
        shell_newline()
        shell_puts("Hex Viewer (text mode not supported, requires VTNext)")
        shell_newline()
        return True

    if shell_starts_with("imgview"):
        shell_newline()
        shell_puts("Image Viewer (text mode not supported, requires VTNext)")
        shell_newline()
        return True

    return False

def shell_exec_file(cmd: Ptr[char]) -> bool:
    """Handle file system commands. Returns True if handled."""

    if shell_starts_with("ls"):
        shell_newline()
        ls_arg: Ptr[char] = shell_get_arg()
        ls_long: bool = False
        ls_path: Ptr[char] = &shell_cwd[0]

        # Check for -l flag
        if ls_arg[0] == '-' and ls_arg[1] == 'l':
            ls_long = True
            # Skip to next argument
            ls_arg = &ls_arg[2]
            while ls_arg[0] == ' ':
                ls_arg = &ls_arg[1]

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
            if ls_long:
                shell_puts("-rw-r--r-- ")
                fsize: int32 = ramfs_size(ls_path)
                shell_puts(shell_int_to_str(fsize))
                shell_puts(" ")
            shell_puts(ls_arg)
            shell_newline()
        else:
            idx: int32 = 0
            result: int32 = ramfs_readdir(ls_path, idx, &shell_name_buf[0])
            while result >= 0:
                if ls_long:
                    # Build full path for size lookup
                    strcpy(&shell_src_path[0], ls_path)
                    if shell_src_path[strlen(&shell_src_path[0]) - 1] != '/':
                        strcat(&shell_src_path[0], "/")
                    strcat(&shell_src_path[0], &shell_name_buf[0])
                    if result == 1:
                        shell_puts("drwxr-xr-x    0 ")
                    else:
                        shell_puts("-rw-r--r-- ")
                        fsize2: int32 = ramfs_size(&shell_src_path[0])
                        # Right-align size in 4 chars
                        if fsize2 < 10:
                            shell_puts("   ")
                        elif fsize2 < 100:
                            shell_puts("  ")
                        elif fsize2 < 1000:
                            shell_puts(" ")
                        shell_puts(shell_int_to_str(fsize2))
                        shell_puts(" ")
                    shell_puts(&shell_name_buf[0])
                    shell_newline()
                else:
                    shell_puts(&shell_name_buf[0])
                    if result == 1:
                        shell_putc('/')
                    shell_puts("  ")
                idx = idx + 1
                result = ramfs_readdir(ls_path, idx, &shell_name_buf[0])
            if not ls_long:
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
            shell_newline()

            # Check if it's a device file
            dev_idx: int32 = devfs_find_by_path(&shell_path_buf[0])
            if dev_idx >= 0:
                # Device file - use devfs
                dev_data: Ptr[char] = devfs_read(dev_idx)
                shell_puts(dev_data)
                shell_newline()
            elif ramfs_exists(&shell_path_buf[0]) and not ramfs_isdir(&shell_path_buf[0]):
                # Regular file - use ramfs
                bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
                if bytes_read > 0:
                    shell_read_buf[bytes_read] = 0
                    shell_puts(cast[Ptr[char]](&shell_read_buf[0]))
                shell_newline()
            else:
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

    if shell_starts_with("kill"):
        kill_arg: Ptr[char] = shell_get_arg()
        shell_newline()
        # Parse job number - accept %1, 1, or just "kill" for job 1
        job_num: int32 = 1
        if kill_arg[0] == '%':
            job_num = atoi(&kill_arg[1])
        elif kill_arg[0] >= '0' and kill_arg[0] <= '9':
            job_num = atoi(kill_arg)

        if job_num == 1:
            if job1_state != SHELL_JOB_TERMINATED:
                job1_state = SHELL_JOB_TERMINATED
                shell_puts("[1]   Terminated              main.py")
            else:
                shell_puts("kill: job 1 already terminated")
        else:
            shell_puts("kill: no such job")
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
        head_arg: Ptr[char] = shell_get_arg()
        head_n: int32 = 10

        # Parse -n flag
        if head_arg[0] == '-' and head_arg[1] == 'n':
            head_arg = &head_arg[2]
            while head_arg[0] == ' ':
                head_arg = &head_arg[1]
            head_n = atoi(head_arg)
            if head_n <= 0:
                head_n = 10
            # Skip to filename
            while head_arg[0] != '\0' and head_arg[0] != ' ':
                head_arg = &head_arg[1]
            while head_arg[0] == ' ':
                head_arg = &head_arg[1]

        if head_arg[0] == '\0':
            shell_newline()
            shell_puts("Usage: head [-n N] <file>")
            shell_newline()
        else:
            shell_build_path(head_arg)
            if ramfs_exists(&shell_path_buf[0]) and not ramfs_isdir(&shell_path_buf[0]):
                shell_newline()
                bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
                if bytes_read > 0:
                    shell_read_buf[bytes_read] = 0
                    lines: int32 = 0
                    i: int32 = 0
                    while i < bytes_read and lines < head_n:
                        shell_putc(cast[char](shell_read_buf[i]))
                        if shell_read_buf[i] == 10:
                            lines = lines + 1
                        i = i + 1
                shell_newline()
            else:
                shell_newline()
                shell_puts("No such file: ")
                shell_puts(head_arg)
                shell_newline()
        return True

    if shell_starts_with("tail"):
        tail_arg: Ptr[char] = shell_get_arg()
        tail_n: int32 = 10

        # Parse -n flag
        if tail_arg[0] == '-' and tail_arg[1] == 'n':
            tail_arg = &tail_arg[2]
            while tail_arg[0] == ' ':
                tail_arg = &tail_arg[1]
            tail_n = atoi(tail_arg)
            if tail_n <= 0:
                tail_n = 10
            # Skip to filename
            while tail_arg[0] != '\0' and tail_arg[0] != ' ':
                tail_arg = &tail_arg[1]
            while tail_arg[0] == ' ':
                tail_arg = &tail_arg[1]

        if tail_arg[0] == '\0':
            shell_newline()
            shell_puts("Usage: tail [-n N] <file>")
            shell_newline()
        else:
            shell_build_path(tail_arg)
            if ramfs_exists(&shell_path_buf[0]) and not ramfs_isdir(&shell_path_buf[0]):
                shell_newline()
                bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
                if bytes_read > 0:
                    shell_read_buf[bytes_read] = 0
                    # Count total lines
                    total_lines: int32 = 0
                    i: int32 = 0
                    while i < bytes_read:
                        if shell_read_buf[i] == 10:
                            total_lines = total_lines + 1
                        i = i + 1
                    # If last char isn't newline, count that as a line too
                    if bytes_read > 0 and shell_read_buf[bytes_read - 1] != 10:
                        total_lines = total_lines + 1
                    # Find start position (skip lines until we have tail_n left)
                    skip_lines: int32 = total_lines - tail_n
                    if skip_lines < 0:
                        skip_lines = 0
                    lines_skipped: int32 = 0
                    i = 0
                    while i < bytes_read and lines_skipped < skip_lines:
                        if shell_read_buf[i] == 10:
                            lines_skipped = lines_skipped + 1
                        i = i + 1
                    # Print from position i
                    while i < bytes_read:
                        shell_putc(cast[char](shell_read_buf[i]))
                        i = i + 1
                shell_newline()
            else:
                shell_newline()
                shell_puts("No such file: ")
                shell_puts(tail_arg)
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

def shell_exec_grep(cmd: Ptr[char]) -> bool:
    """Handle grep command. Returns True if handled."""

    if shell_starts_with("grep"):
        grep_arg: Ptr[char] = shell_get_arg()
        grep_invert: bool = False
        grep_count: bool = False

        # Parse flags
        while grep_arg[0] == '-':
            if grep_arg[1] == 'v':
                grep_invert = True
                grep_arg = &grep_arg[2]
            elif grep_arg[1] == 'c':
                grep_count = True
                grep_arg = &grep_arg[2]
            else:
                break
            while grep_arg[0] == ' ':
                grep_arg = &grep_arg[1]

        if grep_arg[0] == '\0':
            shell_newline()
            shell_puts("Usage: grep [-v] [-c] pattern file")
            shell_newline()
        else:
            # Extract pattern and file
            i: int32 = 0
            while grep_arg[i] != '\0' and grep_arg[i] != ' ':
                shell_grep_pat[i] = grep_arg[i]
                i = i + 1
            shell_grep_pat[i] = '\0'

            grep_file: Ptr[char] = &grep_arg[i]
            while grep_file[0] == ' ':
                grep_file = &grep_file[1]

            if grep_file[0] == '\0':
                shell_newline()
                shell_puts("Usage: grep [-v] [-c] pattern file")
                shell_newline()
            else:
                shell_build_path(grep_file)
                if ramfs_exists(&shell_path_buf[0]) and not ramfs_isdir(&shell_path_buf[0]):
                    bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
                    shell_newline()
                    if bytes_read > 0:
                        shell_read_buf[bytes_read] = 0
                        match_count: int32 = 0
                        line_start: int32 = 0
                        pos: int32 = 0
                        while pos <= bytes_read:
                            if pos == bytes_read or shell_read_buf[pos] == 10:
                                # Extract line
                                line_len: int32 = pos - line_start
                                if line_len > 255:
                                    line_len = 255
                                j: int32 = 0
                                while j < line_len:
                                    shell_line_buf[j] = cast[char](shell_read_buf[line_start + j])
                                    j = j + 1
                                shell_line_buf[line_len] = '\0'

                                # Check for match
                                has_match: bool = str_contains(&shell_line_buf[0], &shell_grep_pat[0])
                                if grep_invert:
                                    has_match = not has_match

                                if has_match:
                                    match_count = match_count + 1
                                    if not grep_count:
                                        shell_puts(&shell_line_buf[0])
                                        shell_newline()

                                line_start = pos + 1
                            pos = pos + 1
                        if grep_count:
                            shell_puts(shell_int_to_str(match_count))
                            shell_newline()
                else:
                    shell_newline()
                    shell_puts("grep: ")
                    shell_puts(grep_file)
                    shell_puts(": No such file")
                    shell_newline()
        return True

    return False

def shell_find_in_dir(dir_path: Ptr[char], pattern: Ptr[char], name_only: bool):
    """Search for files matching pattern in dir_path (non-recursive)."""
    idx: int32 = 0
    result: int32 = ramfs_readdir(dir_path, idx, &shell_find_buf[0])
    while result >= 0:
        # Build full path
        strcpy(&shell_find_path[0], dir_path)
        if shell_find_path[strlen(&shell_find_path[0]) - 1] != '/':
            strcat(&shell_find_path[0], "/")
        strcat(&shell_find_path[0], &shell_find_buf[0])

        # Check if name matches pattern
        if pattern[0] == '\0' or str_contains(&shell_find_buf[0], pattern):
            if name_only:
                shell_puts(&shell_find_buf[0])
            else:
                shell_puts(&shell_find_path[0])
            shell_newline()

        idx = idx + 1
        result = ramfs_readdir(dir_path, idx, &shell_find_buf[0])

def shell_exec_find(cmd: Ptr[char]) -> bool:
    """Handle find command. Returns True if handled."""

    if shell_starts_with("find"):
        find_arg: Ptr[char] = shell_get_arg()
        find_name_only: bool = False

        if find_arg[0] == '\0':
            # No args - search current directory
            shell_newline()
            shell_find_in_dir(&shell_cwd[0], "", False)
        else:
            # Check for -name flag
            find_dir: Ptr[char] = find_arg
            find_pattern: Ptr[char] = ""

            # Skip directory arg if present
            if find_arg[0] == '-':
                # -name pattern
                if find_arg[1] == 'n' and find_arg[2] == 'a':
                    find_arg = &find_arg[5]  # Skip "-name"
                    while find_arg[0] == ' ':
                        find_arg = &find_arg[1]
                    # Extract pattern
                    i: int32 = 0
                    while find_arg[i] != '\0' and find_arg[i] != ' ' and i < 63:
                        shell_find_pat[i] = find_arg[i]
                        i = i + 1
                    shell_find_pat[i] = '\0'
                    find_pattern = &shell_find_pat[0]
                    find_dir = &shell_cwd[0]
            else:
                # Directory specified, check for -name after
                i: int32 = 0
                while find_arg[i] != '\0' and find_arg[i] != ' ':
                    i = i + 1
                if find_arg[i] == ' ':
                    find_arg[i] = '\0'
                    find_dir = find_arg
                    find_arg = &find_arg[i + 1]
                    while find_arg[0] == ' ':
                        find_arg = &find_arg[1]
                    if find_arg[0] == '-' and find_arg[1] == 'n' and find_arg[2] == 'a':
                        find_arg = &find_arg[5]
                        while find_arg[0] == ' ':
                            find_arg = &find_arg[1]
                        j: int32 = 0
                        while find_arg[j] != '\0' and find_arg[j] != ' ' and j < 63:
                            shell_find_pat[j] = find_arg[j]
                            j = j + 1
                        shell_find_pat[j] = '\0'
                        find_pattern = &shell_find_pat[0]

            shell_newline()
            shell_build_path(find_dir)
            if ramfs_exists(&shell_path_buf[0]) and ramfs_isdir(&shell_path_buf[0]):
                shell_find_in_dir(&shell_path_buf[0], find_pattern, False)
            else:
                shell_puts("find: ")
                shell_puts(find_dir)
                shell_puts(": No such directory")
                shell_newline()
        return True

    return False

def shell_exec_sed(cmd: Ptr[char]) -> bool:
    """Handle sed command. Supports s/old/new/ substitution."""

    if shell_starts_with("sed"):
        sed_arg: Ptr[char] = shell_get_arg()

        if sed_arg[0] != 's' or sed_arg[1] != '/':
            shell_newline()
            shell_puts("Usage: sed s/old/new/ file")
            shell_newline()
            return True

        # Parse s/old/new/
        sed_arg = &sed_arg[2]  # Skip "s/"

        # Extract old pattern
        i: int32 = 0
        while sed_arg[i] != '/' and sed_arg[i] != '\0' and i < 63:
            shell_sed_old[i] = sed_arg[i]
            i = i + 1
        shell_sed_old[i] = '\0'

        if sed_arg[i] != '/':
            shell_newline()
            shell_puts("Usage: sed s/old/new/ file")
            shell_newline()
            return True

        sed_arg = &sed_arg[i + 1]  # Skip delimiter

        # Extract new pattern
        i = 0
        while sed_arg[i] != '/' and sed_arg[i] != '\0' and i < 63:
            shell_sed_new[i] = sed_arg[i]
            i = i + 1
        shell_sed_new[i] = '\0'

        if sed_arg[i] != '/':
            shell_newline()
            shell_puts("Usage: sed s/old/new/ file")
            shell_newline()
            return True

        sed_arg = &sed_arg[i + 1]  # Skip trailing /
        while sed_arg[0] == ' ':
            sed_arg = &sed_arg[1]

        if sed_arg[0] == '\0':
            shell_newline()
            shell_puts("Usage: sed s/old/new/ file")
            shell_newline()
            return True

        # Read file
        shell_build_path(sed_arg)
        if not ramfs_exists(&shell_path_buf[0]) or ramfs_isdir(&shell_path_buf[0]):
            shell_newline()
            shell_puts("sed: ")
            shell_puts(sed_arg)
            shell_puts(": No such file")
            shell_newline()
            return True

        bytes_read: int32 = ramfs_read(&shell_path_buf[0], &shell_read_buf[0], 511)
        shell_newline()
        if bytes_read > 0:
            shell_read_buf[bytes_read] = 0
            old_len: int32 = strlen(&shell_sed_old[0])
            new_len: int32 = strlen(&shell_sed_new[0])

            # Process each character, looking for old pattern
            in_pos: int32 = 0
            out_pos: int32 = 0
            while in_pos < bytes_read and out_pos < 500:
                # Check for match at current position
                j: int32 = 0
                matched: bool = True
                while j < old_len and matched:
                    if shell_read_buf[in_pos + j] != cast[uint8](shell_sed_old[j]):
                        matched = False
                    j = j + 1

                if matched and old_len > 0:
                    # Replace with new string
                    k: int32 = 0
                    while k < new_len and out_pos < 500:
                        shell_sed_out[out_pos] = shell_sed_new[k]
                        out_pos = out_pos + 1
                        k = k + 1
                    in_pos = in_pos + old_len
                else:
                    shell_sed_out[out_pos] = cast[char](shell_read_buf[in_pos])
                    out_pos = out_pos + 1
                    in_pos = in_pos + 1

            shell_sed_out[out_pos] = '\0'
            shell_puts(&shell_sed_out[0])
        shell_newline()
        return True

    return False

# ============================================================================
# Hardware commands - sensors and motors
# ============================================================================

# Hardware initialized flag
_hw_init_done: bool = False

def _hw_ensure_init():
    """Initialize hardware if not already done."""
    global _hw_init_done
    if not _hw_init_done:
        sensors_seed(12345)
        sensors_enable_noise(True)
        sensors_init_all()
        _hw_init_done = True

def shell_exec_hw(cmd: Ptr[char]) -> bool:
    """Handle hardware commands. Returns True if handled."""

    # sensormon - run sensor monitor demo
    if strcmp(cmd, "sensormon") == 0:
        shell_newline()
        _hw_ensure_init()
        sensormon_main(0, cast[Ptr[Ptr[char]]](0))
        return True

    # motorctl - run motor controller demo
    if strcmp(cmd, "motorctl") == 0:
        shell_newline()
        motorctl_main(0, cast[Ptr[Ptr[char]]](0))
        return True

    # sensors - quick sensor readout
    if strcmp(cmd, "sensors") == 0:
        shell_newline()
        _hw_ensure_init()
        shell_puts("=== Sensor Readings ===")
        shell_newline()

        # Temperature
        t: int32 = temp_read()
        shell_puts("Temp: ")
        shell_puts(shell_int_to_str(t / 100))
        shell_puts(".")
        tf: int32 = abs_int(t % 100)
        if tf < 10:
            shell_puts("0")
        shell_puts(shell_int_to_str(tf))
        shell_puts(" C")
        shell_newline()

        # Accelerometer
        shell_puts("Accel: X=")
        shell_puts(shell_int_to_str(accel_read_x()))
        shell_puts(" Y=")
        shell_puts(shell_int_to_str(accel_read_y()))
        shell_puts(" Z=")
        shell_puts(shell_int_to_str(accel_read_z()))
        shell_puts(" mg")
        shell_newline()

        # Light
        shell_puts("Light: ")
        shell_puts(shell_int_to_str(light_read()))
        shell_newline()

        # Humidity
        h: int32 = humid_read()
        shell_puts("Humid: ")
        shell_puts(shell_int_to_str(h / 10))
        shell_puts(".")
        shell_puts(shell_int_to_str(h % 10))
        shell_puts(" %")
        shell_newline()

        # Pressure
        p: int32 = press_read()
        shell_puts("Press: ")
        shell_puts(shell_int_to_str(p / 100))
        shell_puts(" hPa (alt: ")
        shell_puts(shell_int_to_str(press_to_altitude(p)))
        shell_puts(" m)")
        shell_newline()

        return True

    # servo <id> <angle> - set servo angle
    if shell_starts_with("servo"):
        arg: Ptr[char] = shell_get_arg()
        if strlen(arg) == 0:
            shell_newline()
            shell_puts("Usage: servo <id> <angle>")
            shell_newline()
            shell_puts("  id: 0-7, angle: 0-180")
            shell_newline()
            return True

        shell_newline()
        id: int32 = atoi(arg)

        # Get angle (skip to next space)
        i: int32 = 0
        while arg[i] != '\0' and arg[i] != ' ':
            i = i + 1
        while arg[i] == ' ':
            i = i + 1

        if arg[i] == '\0':
            # Just show current angle
            shell_puts("Servo ")
            shell_puts(shell_int_to_str(id))
            shell_puts(": ")
            shell_puts(shell_int_to_str(servo_get_angle(id)))
            shell_puts(" deg")
        else:
            angle: int32 = atoi(&arg[i])
            servo_init(id)
            servo_set_angle(id, angle)
            shell_puts("Servo ")
            shell_puts(shell_int_to_str(id))
            shell_puts(" -> ")
            shell_puts(shell_int_to_str(angle))
            shell_puts(" deg")
        shell_newline()
        return True

    # stepper <id> <steps> - move stepper
    if shell_starts_with("stepper"):
        arg: Ptr[char] = shell_get_arg()
        if strlen(arg) == 0:
            shell_newline()
            shell_puts("Usage: stepper <id> <steps>")
            shell_newline()
            shell_puts("  id: 0-3, steps: +/- integer")
            shell_newline()
            return True

        shell_newline()
        id: int32 = atoi(arg)

        # Get steps
        i: int32 = 0
        while arg[i] != '\0' and arg[i] != ' ':
            i = i + 1
        while arg[i] == ' ':
            i = i + 1

        if arg[i] == '\0':
            # Just show current position
            shell_puts("Stepper ")
            shell_puts(shell_int_to_str(id))
            shell_puts(": pos=")
            shell_puts(shell_int_to_str(stepper_get_position(id)))
        else:
            steps: int32 = atoi(&arg[i])
            stepper_init(id, 200)
            stepper_steps(id, steps)
            shell_puts("Stepper ")
            shell_puts(shell_int_to_str(id))
            shell_puts(" moved ")
            shell_puts(shell_int_to_str(steps))
            shell_puts(", pos=")
            shell_puts(shell_int_to_str(stepper_get_position(id)))
        shell_newline()
        return True

    # motor <id> <speed> - set DC motor speed
    if shell_starts_with("motor"):
        arg: Ptr[char] = shell_get_arg()
        if strlen(arg) == 0:
            shell_newline()
            shell_puts("Usage: motor <id> <speed>")
            shell_newline()
            shell_puts("  id: 0-3, speed: -100 to 100")
            shell_newline()
            shell_puts("  motor <id> brake - brake motor")
            shell_newline()
            return True

        shell_newline()
        id: int32 = atoi(arg)

        # Get speed or command
        i: int32 = 0
        while arg[i] != '\0' and arg[i] != ' ':
            i = i + 1
        while arg[i] == ' ':
            i = i + 1

        if arg[i] == '\0':
            # Just show current speed
            shell_puts("Motor ")
            shell_puts(shell_int_to_str(id))
            shell_puts(": ")
            shell_puts(shell_int_to_str(dc_get_speed(id)))
            shell_puts("%")
        elif arg[i] == 'b':
            # Brake
            dc_brake(id)
            shell_puts("Motor ")
            shell_puts(shell_int_to_str(id))
            shell_puts(" braked")
        else:
            speed: int32 = atoi(&arg[i])
            dc_init(id)
            dc_set_speed(id, speed)
            shell_puts("Motor ")
            shell_puts(shell_int_to_str(id))
            shell_puts(" -> ")
            shell_puts(shell_int_to_str(speed))
            shell_puts("%")
        shell_newline()
        return True

    # drivers - list or reload device drivers
    if strcmp(cmd, "drivers") == 0 or shell_starts_with("drivers"):
        shell_newline()
        arg: Ptr[char] = shell_get_arg()
        if strlen(arg) == 0 or strcmp(arg, "list") == 0:
            shell_puts("=== Device Drivers ===")
            shell_newline()
            cnt: int32 = devfs_get_count()
            if cnt == 0:
                shell_puts("  (no drivers loaded)")
                shell_newline()
            else:
                i: int32 = 0
                while i < cnt:
                    shell_puts("  ")
                    shell_puts(devfs_get_path(i))
                    dtype: int32 = devfs_get_type(i)
                    shell_puts(" (")
                    if dtype == 1:
                        shell_puts("gpio")
                    elif dtype == 2:
                        shell_puts("temp")
                    elif dtype == 3:
                        shell_puts("accel")
                    elif dtype == 4:
                        shell_puts("light")
                    elif dtype == 5:
                        shell_puts("humid")
                    elif dtype == 6:
                        shell_puts("press")
                    elif dtype == 7:
                        shell_puts("servo")
                    elif dtype == 8:
                        shell_puts("stepper")
                    elif dtype == 9:
                        shell_puts("dc")
                    elif dtype == 10:
                        shell_puts("adc")
                    elif dtype == 11:
                        shell_puts("pwm")
                    else:
                        shell_puts("unknown")
                    shell_puts(")")
                    shell_newline()
                    i = i + 1
                shell_puts("Total: ")
                shell_puts(shell_int_to_str(cnt))
                shell_puts(" driver(s)")
                shell_newline()
        elif strcmp(arg, "reload") == 0:
            shell_puts("Reloading drivers...")
            shell_newline()
            devfs_scan_drivers()
            shell_puts("Done. ")
            shell_puts(shell_int_to_str(devfs_get_count()))
            shell_puts(" driver(s) loaded")
            shell_newline()
        else:
            shell_puts("Usage: drivers [list|reload]")
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

    # Save to history and reset navigation
    history_add(cmd)
    history_reset_pos()

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
    elif shell_exec_grep(cmd):
        pass
    elif shell_exec_find(cmd):
        pass
    elif shell_exec_sed(cmd):
        pass
    elif shell_exec_hw(cmd):
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
    global shell_cmd_pos
    global job1_state
    global shell_history_pos
    global shell_fg_mode

    # Handle escape sequences for arrow keys
    if shell_esc[0] == 1:
        # Got ESC, expecting [
        if c == '[':
            shell_esc[0] = 2
            return
        else:
            shell_esc[0] = 0
            # Fall through to process char normally

    if shell_esc[0] == 2:
        # Got ESC [, expecting A/B/C/D
        shell_esc[0] = 0
        if c == 'A':
            # Up arrow - previous command
            if shell_history_count > 0:
                if shell_history_pos < shell_history_count - 1:
                    shell_history_pos = shell_history_pos + 1
                hist_cmd: Ptr[char] = history_get(shell_history_pos)
                if hist_cmd != Ptr[char](0):
                    shell_set_cmd(hist_cmd)
            return
        elif c == 'B':
            # Down arrow - next command
            if shell_history_pos > 0:
                shell_history_pos = shell_history_pos - 1
                hist_cmd2: Ptr[char] = history_get(shell_history_pos)
                if hist_cmd2 != Ptr[char](0):
                    shell_set_cmd(hist_cmd2)
            elif shell_history_pos == 0:
                shell_history_pos = -1
                shell_clear_line()
            return
        # C=right, D=left - ignore for now
        return

    # Check for ESC start (use numeric comparison to avoid signedness issues)
    code: int32 = cast[int32](c) & 0xFF
    if code == 27:
        shell_esc[0] = 1
        return

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

    # TAB - filename completion
    if c == '\t':
        shell_tab_complete()
        return

    # Ctrl+C - cancel current command line or stop foreground job
    if c == '\x03':
        shell_puts("^C")
        shell_newline()
        if shell_fg_mode == 1:
            # Stop the foreground job
            job1_state = SHELL_JOB_STOPPED
            shell_fg_mode = 0
            shell_puts("[1]+  Stopped                 main.py")
            shell_newline()
        shell_cmd_pos = 0
        history_reset_pos()
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
        history_reset_pos()
        shell_prompt()
        return

    # Regular char - reset history position
    history_reset_pos()
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

        # Call user tick function only if job is running (not stopped or terminated)
        if job1_state == SHELL_JOB_RUNNING or job1_state == SHELL_JOB_FOREGROUND:
            user_tick()

        if uart_available():
            c: char = uart_getc()
            shell_input(c)
