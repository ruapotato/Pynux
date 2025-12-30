# Pynux Desktop Environment
#
# Graphical desktop with windowed terminal over VTNext protocol.
# Optimized for serial communication with dirty region tracking.

from lib.io import uart_putc, uart_getc, uart_available, print_str, print_int
from lib.vtnext import vtn_init, vtn_clear, vtn_rect, vtn_textline
from lib.vtnext import vtn_clear_rect, vtn_present, vtn_flush
from lib.vtnext import vtn_line, vtn_text
from lib.string import strcmp, strlen, strcpy, memset, strcat, atoi
from kernel.ramfs import ramfs_readdir, ramfs_create, ramfs_delete
from kernel.ramfs import ramfs_read, ramfs_write, ramfs_exists, ramfs_isdir
from lib.memory import heap_remaining, heap_total, heap_used
from kernel.timer import timer_delay_ms

# ============================================================================
# Screen and color constants
# ============================================================================

SCREEN_W: int32 = 800
SCREEN_H: int32 = 600

# Colors (RGB)
BG_R: int32 = 30
BG_G: int32 = 40
BG_B: int32 = 60

TITLE_R: int32 = 50
TITLE_G: int32 = 60
TITLE_B: int32 = 80

TERM_BG_R: int32 = 20
TERM_BG_G: int32 = 25
TERM_BG_B: int32 = 35

TEXT_R: int32 = 220
TEXT_G: int32 = 220
TEXT_B: int32 = 220

ACCENT_R: int32 = 100
ACCENT_G: int32 = 150
ACCENT_B: int32 = 255

# ============================================================================
# Terminal widget state
# ============================================================================

# Terminal dimensions
TERM_X: int32 = 50
TERM_Y: int32 = 60
TERM_W: int32 = 700
TERM_H: int32 = 480
TERM_COLS: int32 = 80
TERM_ROWS: int32 = 24
TERM_SCROLL_MAX: int32 = 100
CHAR_W: int32 = 8
CHAR_H: int32 = 16

# Terminal buffer (100 lines of 80 chars each)
term_buffer: Array[8000, char]  # 100 * 80
term_line_dirty: Array[100, bool]
term_scroll_pos: int32 = 0
term_cursor_x: int32 = 0
term_cursor_y: int32 = 0
term_line_count: int32 = 0

# Command input buffer
cmd_buffer: Array[256, char]
cmd_pos: int32 = 0

# Current working directory
cwd: Array[128, char]

# Temp path buffer for building full paths
path_buf: Array[256, char]

# Read buffer for cat
read_buf: Array[512, uint8]

# Number buffer for printing integers
num_buf: Array[16, char]

# ============================================================================
# Dirty region tracking
# ============================================================================

needs_full_redraw: bool = True
term_needs_redraw: bool = False
status_needs_redraw: bool = False

# ============================================================================
# Helper functions
# ============================================================================

def cmd_get_arg() -> Ptr[char]:
    """Get the argument part of the command (after first space)."""
    i: int32 = 0
    # Skip command name
    while cmd_buffer[i] != '\0' and cmd_buffer[i] != ' ':
        i = i + 1
    # Skip spaces
    while cmd_buffer[i] == ' ':
        i = i + 1
    return &cmd_buffer[i]

def cmd_starts_with(prefix: Ptr[char]) -> bool:
    """Check if command starts with prefix."""
    i: int32 = 0
    while prefix[i] != '\0':
        if cmd_buffer[i] != prefix[i]:
            return False
        i = i + 1
    # Must be followed by space or end of string
    return cmd_buffer[i] == ' ' or cmd_buffer[i] == '\0'

def build_path(name: Ptr[char]):
    """Build full path from cwd and name into path_buf."""
    if name[0] == '/':
        # Absolute path
        strcpy(&path_buf[0], name)
    else:
        # Relative path
        strcpy(&path_buf[0], &cwd[0])
        # Add / if cwd doesn't end with /
        cwd_len: int32 = strlen(&cwd[0])
        if cwd_len > 0 and cwd[cwd_len - 1] != '/':
            strcat(&path_buf[0], "/")
        strcat(&path_buf[0], name)

def int_to_str(n: int32) -> Ptr[char]:
    """Convert integer to string in num_buf."""
    if n == 0:
        num_buf[0] = '0'
        num_buf[1] = '\0'
        return &num_buf[0]

    neg: bool = False
    if n < 0:
        neg = True
        n = -n

    # Build digits in reverse
    i: int32 = 0
    while n > 0:
        num_buf[i] = cast[char](48 + (n % 10))
        n = n / 10
        i = i + 1

    if neg:
        num_buf[i] = '-'
        i = i + 1

    num_buf[i] = '\0'

    # Reverse the string
    j: int32 = 0
    k: int32 = i - 1
    while j < k:
        tmp: char = num_buf[j]
        num_buf[j] = num_buf[k]
        num_buf[k] = tmp
        j = j + 1
        k = k - 1

    return &num_buf[0]

def term_line_ptr(line: int32) -> Ptr[char]:
    """Get pointer to a terminal line buffer."""
    offset: int32 = line * TERM_COLS
    return &term_buffer[offset]

def term_clear_line(line: int32):
    """Clear a terminal line."""
    ptr: Ptr[char] = term_line_ptr(line)
    i: int32 = 0
    while i < TERM_COLS:
        ptr[i] = ' '
        i = i + 1
    term_line_dirty[line] = True

def term_init():
    """Initialize terminal state."""
    global term_scroll_pos, term_cursor_x, term_cursor_y, term_line_count, cmd_pos

    # Clear all lines
    i: int32 = 0
    while i < TERM_SCROLL_MAX:
        term_clear_line(i)
        i = i + 1

    term_scroll_pos = 0
    term_cursor_x = 0
    term_cursor_y = 0
    term_line_count = 0
    cmd_pos = 0

    # Initialize cwd
    cwd[0] = '/'
    cwd[1] = '\0'

def term_scroll():
    """Scroll terminal up by one line."""
    global term_scroll_pos, term_cursor_y

    if term_scroll_pos < TERM_SCROLL_MAX - TERM_ROWS:
        term_scroll_pos = term_scroll_pos + 1
    else:
        # Wrap around - shift buffer
        i: int32 = 0
        while i < TERM_SCROLL_MAX - 1:
            src: Ptr[char] = term_line_ptr(i + 1)
            dst: Ptr[char] = term_line_ptr(i)
            j: int32 = 0
            while j < TERM_COLS:
                dst[j] = src[j]
                j = j + 1
            i = i + 1
        term_clear_line(TERM_SCROLL_MAX - 1)

    # Mark all visible lines dirty
    i = 0
    while i < TERM_ROWS:
        term_line_dirty[term_scroll_pos + i] = True
        i = i + 1

def term_newline():
    """Move to next line, scroll if needed."""
    global term_cursor_x, term_cursor_y

    term_cursor_x = 0
    term_cursor_y = term_cursor_y + 1

    if term_cursor_y >= TERM_ROWS:
        term_cursor_y = TERM_ROWS - 1
        term_scroll()

def term_putc(c: char):
    """Output a character to terminal."""
    global term_cursor_x, term_cursor_y, term_needs_redraw

    if c == '\n':
        term_newline()
        return

    if c == '\r':
        term_cursor_x = 0
        return

    if c == '\b':
        if term_cursor_x > 0:
            term_cursor_x = term_cursor_x - 1
        return

    # Regular character
    line: int32 = term_scroll_pos + term_cursor_y
    ptr: Ptr[char] = term_line_ptr(line)
    ptr[term_cursor_x] = c
    term_line_dirty[line] = True
    term_needs_redraw = True

    term_cursor_x = term_cursor_x + 1
    if term_cursor_x >= TERM_COLS:
        term_newline()

def term_puts(s: Ptr[char]):
    """Output a string to terminal."""
    i: int32 = 0
    while s[i] != '\0':
        term_putc(s[i])
        i = i + 1

def term_print_prompt():
    """Print shell prompt."""
    term_puts("pynux:")
    term_puts(&cwd[0])
    term_puts("> ")

# ============================================================================
# Drawing functions
# ============================================================================

def draw_titlebar():
    """Draw the desktop title bar."""
    vtn_rect(0, 0, SCREEN_W, 30, TITLE_R, TITLE_G, TITLE_B, 255)
    vtn_textline("Pynux Desktop", 10, 8, TEXT_R, TEXT_G, TEXT_B)

status_buf: Array[80, char]

def draw_statusbar():
    """Draw the status bar at bottom."""
    vtn_rect(0, SCREEN_H - 25, SCREEN_W, 25, TITLE_R, TITLE_G, TITLE_B, 255)

    # Build status string with memory info
    strcpy(&status_buf[0], "Ready | Heap: ")
    strcat(&status_buf[0], int_to_str(heap_used()))
    strcat(&status_buf[0], "/")
    strcat(&status_buf[0], int_to_str(heap_total()))
    strcat(&status_buf[0], " bytes")

    vtn_textline(&status_buf[0], 10, SCREEN_H - 18, TEXT_R, TEXT_G, TEXT_B)

def draw_terminal_frame():
    """Draw terminal window frame."""
    # Window background
    vtn_rect(TERM_X - 2, TERM_Y - 22, TERM_W + 4, TERM_H + 24, TITLE_R, TITLE_G, TITLE_B, 255)

    # Terminal title bar
    vtn_textline("Terminal", TERM_X + 5, TERM_Y - 18, TEXT_R, TEXT_G, TEXT_B)

    # Terminal content area
    vtn_rect(TERM_X, TERM_Y, TERM_W, TERM_H, TERM_BG_R, TERM_BG_G, TERM_BG_B, 255)

def draw_terminal_content():
    """Draw terminal text content (only dirty lines)."""
    global term_needs_redraw

    line_buf: Array[81, char]

    i: int32 = 0
    while i < TERM_ROWS:
        line: int32 = term_scroll_pos + i

        if term_line_dirty[line]:
            # Clear line area first
            y: int32 = TERM_Y + i * CHAR_H
            vtn_clear_rect(TERM_X, y, TERM_W, CHAR_H, TERM_BG_R, TERM_BG_G, TERM_BG_B)

            # Copy line to null-terminated buffer
            ptr: Ptr[char] = term_line_ptr(line)
            j: int32 = 0
            while j < TERM_COLS:
                line_buf[j] = ptr[j]
                j = j + 1
            line_buf[TERM_COLS] = '\0'

            # Draw the text
            vtn_textline(&line_buf[0], TERM_X + 4, y + 2, TEXT_R, TEXT_G, TEXT_B)

            term_line_dirty[line] = False

        i = i + 1

    term_needs_redraw = False

def draw_cursor():
    """Draw cursor as a small rectangle."""
    x: int32 = TERM_X + 4 + term_cursor_x * CHAR_W
    y: int32 = TERM_Y + term_cursor_y * CHAR_H + CHAR_H - 2
    vtn_rect(x, y, CHAR_W, 2, TEXT_R, TEXT_G, TEXT_B, 255)

def de_draw():
    """Draw the entire desktop."""
    global needs_full_redraw

    if needs_full_redraw:
        # Full redraw
        vtn_clear(BG_R, BG_G, BG_B, 255)
        draw_titlebar()
        draw_statusbar()
        draw_terminal_frame()

        # Mark all visible terminal lines dirty
        i: int32 = 0
        while i < TERM_ROWS:
            term_line_dirty[term_scroll_pos + i] = True
            i = i + 1

        needs_full_redraw = False

    # Always draw terminal content (respects dirty tracking)
    draw_terminal_content()
    draw_cursor()

# ============================================================================
# Command execution
# ============================================================================

def exec_cmd():
    """Execute command in cmd_buffer."""
    global cmd_pos

    # Null terminate
    cmd_buffer[cmd_pos] = '\0'

    # Skip empty commands
    if cmd_pos == 0:
        term_print_prompt()
        return

    # Parse command (simple first-word extraction)
    cmd: Ptr[char] = &cmd_buffer[0]

    # Built-in commands
    if strcmp(cmd, "help") == 0:
        term_puts("\nPynux Desktop Commands:\n")
        term_puts("  help       - Show this help\n")
        term_puts("  clear      - Clear terminal\n")
        term_puts("  pwd        - Print working directory\n")
        term_puts("  ls         - List directory\n")
        term_puts("  cd <dir>   - Change directory\n")
        term_puts("  cat <file> - Show file contents\n")
        term_puts("  mkdir <n>  - Create directory\n")
        term_puts("  touch <n>  - Create empty file\n")
        term_puts("  rm <name>  - Remove file/dir\n")
        term_puts("  echo <txt> - Print text\n")
        term_puts("  uname [-a] - System name\n")
        term_puts("  free       - Memory usage\n")
        term_puts("  whoami     - Current user\n")
        term_puts("  hostname   - System hostname\n")
        term_puts("  date       - Current date\n")
        term_puts("  uptime     - System uptime\n")
        term_puts("  write f t  - Write text to file\n")
        term_puts("  cp s d     - Copy file\n")
        term_puts("  id         - User identity\n")
        term_puts("  env        - Environment vars\n")
        term_puts("  sleep <n>  - Sleep N seconds\n")
        term_puts("  reboot     - Reboot system\n")
        term_puts("  halt       - Halt system\n")
        term_puts("  version    - Show version\n")
    elif strcmp(cmd, "clear") == 0:
        term_init()
        needs_full_redraw = True
    elif strcmp(cmd, "pwd") == 0:
        term_putc('\n')
        term_puts(&cwd[0])
        term_putc('\n')
    elif strcmp(cmd, "ls") == 0:
        term_putc('\n')
        name_buf: Array[64, char]
        idx: int32 = 0
        result: int32 = ramfs_readdir(&cwd[0], idx, &name_buf[0])
        while result >= 0:
            term_puts(&name_buf[0])
            if result == 1:
                term_putc('/')
            term_puts("  ")
            idx = idx + 1
            result = ramfs_readdir(&cwd[0], idx, &name_buf[0])
        term_putc('\n')
    elif cmd_starts_with("cd"):
        arg: Ptr[char] = cmd_get_arg()
        if arg[0] == '\0':
            # cd with no arg goes to /
            cwd[0] = '/'
            cwd[1] = '\0'
        elif strcmp(arg, "..") == 0:
            # Go up one level
            cwd_len: int32 = strlen(&cwd[0])
            if cwd_len > 1:
                i: int32 = cwd_len - 1
                if cwd[i] == '/':
                    i = i - 1
                while i > 0 and cwd[i] != '/':
                    i = i - 1
                if i == 0:
                    cwd[0] = '/'
                    cwd[1] = '\0'
                else:
                    cwd[i] = '\0'
        else:
            build_path(arg)
            if ramfs_exists(&path_buf[0]) and ramfs_isdir(&path_buf[0]):
                strcpy(&cwd[0], &path_buf[0])
            else:
                term_puts("\nNo such directory: ")
                term_puts(arg)
                term_putc('\n')
    elif cmd_starts_with("cat"):
        arg2: Ptr[char] = cmd_get_arg()
        if arg2[0] == '\0':
            term_puts("\nUsage: cat <file>\n")
        else:
            build_path(arg2)
            if ramfs_exists(&path_buf[0]) and not ramfs_isdir(&path_buf[0]):
                term_putc('\n')
                bytes_read: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
                if bytes_read > 0:
                    read_buf[bytes_read] = 0
                    term_puts(cast[Ptr[char]](&read_buf[0]))
                term_putc('\n')
            else:
                term_puts("\nNo such file: ")
                term_puts(arg2)
                term_putc('\n')
    elif cmd_starts_with("mkdir"):
        arg3: Ptr[char] = cmd_get_arg()
        if arg3[0] == '\0':
            term_puts("\nUsage: mkdir <name>\n")
        else:
            build_path(arg3)
            if ramfs_create(&path_buf[0], True) >= 0:
                term_puts("\nCreated: ")
                term_puts(&path_buf[0])
                term_putc('\n')
            else:
                term_puts("\nFailed to create directory\n")
    elif cmd_starts_with("touch"):
        arg4: Ptr[char] = cmd_get_arg()
        if arg4[0] == '\0':
            term_puts("\nUsage: touch <name>\n")
        else:
            build_path(arg4)
            if ramfs_create(&path_buf[0], False) >= 0:
                term_puts("\nCreated: ")
                term_puts(&path_buf[0])
                term_putc('\n')
            else:
                term_puts("\nFailed to create file\n")
    elif cmd_starts_with("rm"):
        arg5: Ptr[char] = cmd_get_arg()
        if arg5[0] == '\0':
            term_puts("\nUsage: rm <name>\n")
        else:
            build_path(arg5)
            if ramfs_delete(&path_buf[0]) >= 0:
                term_puts("\nRemoved: ")
                term_puts(&path_buf[0])
                term_putc('\n')
            else:
                term_puts("\nFailed to remove\n")
    elif cmd_starts_with("echo"):
        arg6: Ptr[char] = cmd_get_arg()
        term_putc('\n')
        term_puts(arg6)
        term_putc('\n')
    elif strcmp(cmd, "version") == 0:
        term_puts("\nPynux Desktop v0.1\n")
        term_puts("ARM Cortex-M3 / VTNext Graphics\n")
    elif strcmp(cmd, "uname") == 0 or cmd_starts_with("uname"):
        term_putc('\n')
        arg7: Ptr[char] = cmd_get_arg()
        if arg7[0] == '\0' or strcmp(arg7, "-s") == 0:
            term_puts("Pynux\n")
        elif strcmp(arg7, "-a") == 0:
            term_puts("Pynux 0.1.0 armv7m Cortex-M3\n")
        elif strcmp(arg7, "-r") == 0:
            term_puts("0.1.0\n")
        elif strcmp(arg7, "-m") == 0:
            term_puts("armv7m\n")
        else:
            term_puts("Pynux\n")
    elif strcmp(cmd, "free") == 0:
        term_puts("\n       total     used     free\n")
        term_puts("Heap:  ")
        term_puts(int_to_str(heap_total()))
        term_puts("    ")
        term_puts(int_to_str(heap_used()))
        term_puts("    ")
        term_puts(int_to_str(heap_remaining()))
        term_putc('\n')
    elif strcmp(cmd, "whoami") == 0:
        term_puts("\nroot\n")
    elif strcmp(cmd, "hostname") == 0:
        term_puts("\npynux\n")
    elif strcmp(cmd, "date") == 0:
        term_puts("\nJan 1 00:00:00 UTC 2025\n")
    elif strcmp(cmd, "uptime") == 0:
        term_puts("\nup 0 days, 0:00\n")
    elif cmd_starts_with("write"):
        # write <file> <content>
        arg8: Ptr[char] = cmd_get_arg()
        if arg8[0] == '\0':
            term_puts("\nUsage: write <file> <content>\n")
        else:
            # Find the content (after the filename)
            i: int32 = 0
            while arg8[i] != '\0' and arg8[i] != ' ':
                i = i + 1
            if arg8[i] == ' ':
                arg8[i] = '\0'
                content: Ptr[char] = &arg8[i + 1]
                build_path(arg8)
                # Create file if it doesn't exist
                if not ramfs_exists(&path_buf[0]):
                    ramfs_create(&path_buf[0], False)
                # Write content
                content_len: int32 = strlen(content)
                if ramfs_write(&path_buf[0], content) >= 0:
                    term_puts("\nWrote ")
                    term_puts(int_to_str(content_len))
                    term_puts(" bytes to ")
                    term_puts(&path_buf[0])
                    term_putc('\n')
                else:
                    term_puts("\nFailed to write\n")
            else:
                term_puts("\nUsage: write <file> <content>\n")
    elif strcmp(cmd, "id") == 0:
        term_puts("\nuid=0(root) gid=0(root)\n")
    elif strcmp(cmd, "env") == 0:
        term_puts("\nHOME=/home\n")
        term_puts("USER=root\n")
        term_puts("SHELL=/bin/psh\n")
        term_puts("PWD=")
        term_puts(&cwd[0])
        term_putc('\n')
    elif cmd_starts_with("cp"):
        # cp <src> <dst>
        arg9: Ptr[char] = cmd_get_arg()
        if arg9[0] == '\0':
            term_puts("\nUsage: cp <src> <dst>\n")
        else:
            # Find src and dst
            i: int32 = 0
            while arg9[i] != '\0' and arg9[i] != ' ':
                i = i + 1
            if arg9[i] == ' ':
                arg9[i] = '\0'
                dst: Ptr[char] = &arg9[i + 1]
                # Skip spaces
                while dst[0] == ' ':
                    dst = &dst[1]
                if dst[0] != '\0':
                    # Read source
                    build_path(arg9)
                    src_path: Array[256, char]
                    strcpy(&src_path[0], &path_buf[0])
                    if ramfs_exists(&src_path[0]) and not ramfs_isdir(&src_path[0]):
                        bytes_read: int32 = ramfs_read(&src_path[0], &read_buf[0], 511)
                        if bytes_read >= 0:
                            read_buf[bytes_read] = 0
                            # Write to dest
                            build_path(dst)
                            if not ramfs_exists(&path_buf[0]):
                                ramfs_create(&path_buf[0], False)
                            if ramfs_write(&path_buf[0], cast[Ptr[char]](&read_buf[0])) >= 0:
                                term_puts("\nCopied ")
                                term_puts(&src_path[0])
                                term_puts(" -> ")
                                term_puts(&path_buf[0])
                                term_putc('\n')
                            else:
                                term_puts("\nFailed to write dest\n")
                        else:
                            term_puts("\nFailed to read source\n")
                    else:
                        term_puts("\nSource not found: ")
                        term_puts(arg9)
                        term_putc('\n')
                else:
                    term_puts("\nUsage: cp <src> <dst>\n")
            else:
                term_puts("\nUsage: cp <src> <dst>\n")
    elif strcmp(cmd, "true") == 0:
        pass  # Do nothing, return success
    elif strcmp(cmd, "false") == 0:
        term_puts("\n")  # Just print newline, simulates failure
    elif strcmp(cmd, "yes") == 0:
        # Just print y once (don't loop forever!)
        term_puts("\ny\n")
    elif cmd_starts_with("sleep"):
        # sleep <seconds>
        arg10: Ptr[char] = cmd_get_arg()
        if arg10[0] == '\0':
            term_puts("\nUsage: sleep <seconds>\n")
        else:
            secs: int32 = atoi(arg10)
            if secs > 0 and secs <= 60:
                term_puts("\nSleeping for ")
                term_puts(int_to_str(secs))
                term_puts(" seconds...\n")
                # Redraw before sleeping
                de_draw()
                vtn_present()
                timer_delay_ms(secs * 1000)
                term_puts("Done.\n")
            else:
                term_puts("\nInvalid sleep time (1-60)\n")
    elif strcmp(cmd, "reboot") == 0:
        term_puts("\nRebooting...\n")
        de_draw()
        vtn_present()
        timer_delay_ms(1000)
        # Trigger system reset via NVIC
        NVIC_AIRCR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED0C)
        NVIC_AIRCR[0] = 0x05FA0004
        while True:
            pass
    elif strcmp(cmd, "halt") == 0 or strcmp(cmd, "poweroff") == 0:
        term_puts("\nSystem halted.\n")
        de_draw()
        vtn_present()
        while True:
            pass
    elif strcmp(cmd, "exit") == 0:
        term_puts("\nExiting to text mode...\n")
        # Not implemented - would need to return to kernel
    else:
        term_puts("\nUnknown command: ")
        term_puts(cmd)
        term_putc('\n')

    term_newline()
    term_print_prompt()
    cmd_pos = 0

def handle_input(c: char):
    """Handle keyboard input."""
    global cmd_pos, term_needs_redraw

    if c == '\r' or c == '\n':
        term_putc('\n')
        exec_cmd()
        term_needs_redraw = True
        return

    if c == '\b' or c == '\x7f':
        if cmd_pos > 0:
            cmd_pos = cmd_pos - 1
            term_putc('\b')
            term_putc(' ')
            term_putc('\b')
            term_needs_redraw = True
        return

    # Ctrl+C - cancel line
    if c == '\x03':
        term_puts("^C\n")
        cmd_pos = 0
        term_print_prompt()
        term_needs_redraw = True
        return

    # Regular character
    if cmd_pos < 255:
        cmd_buffer[cmd_pos] = c
        cmd_pos = cmd_pos + 1
        term_putc(c)
        term_needs_redraw = True

# ============================================================================
# Main DE loop
# ============================================================================

def de_init():
    """Initialize the desktop environment."""
    term_init()
    vtn_init(SCREEN_W, SCREEN_H)

def de_main():
    """Main desktop environment loop."""
    global needs_full_redraw, term_needs_redraw

    de_init()

    # Initial welcome message
    term_puts("Pynux Desktop Environment\n")
    term_puts("Type 'help' for commands.\n\n")
    term_print_prompt()

    # Force initial draw
    needs_full_redraw = True
    de_draw()
    vtn_present()

    # Main loop
    while True:
        # Check for input
        if uart_available():
            c: char = uart_getc()
            handle_input(c)

        # Redraw if needed
        if needs_full_redraw or term_needs_redraw:
            de_draw()
            vtn_present()
