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
# Text processing command handler (separate function to reduce branch distances)
# ============================================================================

def cmd_grep():
    """grep <pattern> <file> - search for pattern in file"""
    arg: Ptr[char] = cmd_get_arg()
    pat: Array[32, char]
    lb: Array[128, char]
    sz: int32 = 0
    i: int32 = 0
    j: int32 = 0
    k: int32 = 0
    lbi: int32 = 0
    found: bool = False
    mtch: bool = False

    if arg[0] == '\0':
        term_puts("\nUsage: grep <pattern> <file>\n")
        return
    # Parse pattern
    while arg[j] != '\0' and arg[j] != ' ' and i < 31:
        pat[i] = arg[j]
        i = i + 1
        j = j + 1
    pat[i] = '\0'
    while arg[j] == ' ':
        j = j + 1
    if arg[j] == '\0':
        term_puts("\nUsage: grep <pattern> <file>\n")
        return
    build_path(&arg[j])
    if not ramfs_exists(&path_buf[0]):
        term_puts("\ngrep: file not found\n")
        return
    sz = ramfs_read(&path_buf[0], &read_buf[0], 512)
    term_putc('\n')
    i = 0
    while i < sz:
        if read_buf[i] == 10:
            lb[lbi] = '\0'
            found = False
            j = 0
            while lb[j] != '\0' and not found:
                mtch = True
                k = 0
                while pat[k] != '\0' and mtch:
                    if lb[j + k] != pat[k]:
                        mtch = False
                    k = k + 1
                if mtch and pat[0] != '\0':
                    found = True
                j = j + 1
            if found:
                term_puts(&lb[0])
                term_putc('\n')
            lbi = 0
        else:
            if lbi < 127:
                lb[lbi] = cast[char](read_buf[i])
                lbi = lbi + 1
        i = i + 1

def cmd_sort():
    """sort <file> - sort lines alphabetically"""
    arg: Ptr[char] = cmd_get_arg()
    ls: Array[32, int32]
    le: Array[32, int32]
    sz: int32 = 0
    lc: int32 = 0
    i: int32 = 0
    j: int32 = 0
    k1: int32 = 0
    k2: int32 = 0
    swap: bool = False
    ts: int32 = 0
    te: int32 = 0

    if arg[0] == '\0':
        term_puts("\nUsage: sort <file>\n")
        return
    build_path(arg)
    if not ramfs_exists(&path_buf[0]):
        term_puts("\nsort: file not found\n")
        return
    sz = ramfs_read(&path_buf[0], &read_buf[0], 512)
    term_putc('\n')
    ls[0] = 0
    i = 0
    while i < sz:
        if read_buf[i] == 10:
            if lc < 32:
                le[lc] = i
                lc = lc + 1
                if i < sz - 1:
                    ls[lc] = i + 1
        i = i + 1
    if sz > 0 and read_buf[sz - 1] != 10 and lc < 32:
        le[lc] = sz
        lc = lc + 1
    # Bubble sort
    i = 0
    while i < lc - 1:
        j = 0
        while j < lc - i - 1:
            swap = False
            k1 = ls[j]
            k2 = ls[j + 1]
            while k1 < le[j] and k2 < le[j + 1]:
                if read_buf[k1] > read_buf[k2]:
                    swap = True
                    k1 = sz
                elif read_buf[k1] < read_buf[k2]:
                    k1 = sz
                else:
                    k1 = k1 + 1
                    k2 = k2 + 1
            if swap:
                ts = ls[j]
                ls[j] = ls[j + 1]
                ls[j + 1] = ts
                te = le[j]
                le[j] = le[j + 1]
                le[j + 1] = te
            j = j + 1
        i = i + 1
    # Print sorted
    i = 0
    while i < lc:
        j = ls[i]
        while j < le[i]:
            term_putc(cast[char](read_buf[j]))
            j = j + 1
        term_putc('\n')
        i = i + 1

def cmd_uniq():
    """uniq <file> - filter adjacent duplicates"""
    arg: Ptr[char] = cmd_get_arg()
    sz: int32 = 0
    ps: int32 = -1
    pe: int32 = -1
    cs: int32 = 0
    ce: int32 = 0
    i: int32 = 0
    k: int32 = 0
    dup: bool = False

    if arg[0] == '\0':
        term_puts("\nUsage: uniq <file>\n")
        return
    build_path(arg)
    if not ramfs_exists(&path_buf[0]):
        term_puts("\nuniq: file not found\n")
        return
    sz = ramfs_read(&path_buf[0], &read_buf[0], 512)
    term_putc('\n')
    while i <= sz:
        if i == sz or read_buf[i] == 10:
            ce = i
            dup = False
            if ps >= 0 and ce - cs == pe - ps:
                dup = True
                k = 0
                while k < ce - cs:
                    if read_buf[cs + k] != read_buf[ps + k]:
                        dup = False
                    k = k + 1
            if not dup:
                k = cs
                while k < ce:
                    term_putc(cast[char](read_buf[k]))
                    k = k + 1
                term_putc('\n')
            ps = cs
            pe = ce
            cs = i + 1
        i = i + 1

def cmd_tr():
    """tr <from> <to> <file> - translate characters"""
    arg: Ptr[char] = cmd_get_arg()
    fc: char = '\0'
    tc: char = '\0'
    sz: int32 = 0
    i: int32 = 0

    if arg[0] == '\0' or arg[1] != ' ' or arg[2] == '\0' or arg[3] != ' ':
        term_puts("\nUsage: tr <char> <char> <file>\n")
        return
    fc = arg[0]
    tc = arg[2]
    i = 4
    while arg[i] == ' ':
        i = i + 1
    if arg[i] == '\0':
        term_puts("\nUsage: tr <char> <char> <file>\n")
        return
    build_path(&arg[i])
    if not ramfs_exists(&path_buf[0]):
        term_puts("\ntr: file not found\n")
        return
    sz = ramfs_read(&path_buf[0], &read_buf[0], 512)
    term_putc('\n')
    i = 0
    while i < sz:
        if cast[char](read_buf[i]) == fc:
            term_putc(tc)
        else:
            term_putc(cast[char](read_buf[i]))
        i = i + 1

def cmd_tac():
    """tac <file> - reverse line order"""
    arg: Ptr[char] = cmd_get_arg()
    ends: Array[64, int32]
    sz: int32 = 0
    lc: int32 = 0
    i: int32 = 0
    st: int32 = 0
    ed: int32 = 0

    if arg[0] == '\0':
        term_puts("\nUsage: tac <file>\n")
        return
    build_path(arg)
    if not ramfs_exists(&path_buf[0]):
        term_puts("\ntac: file not found\n")
        return
    sz = ramfs_read(&path_buf[0], &read_buf[0], 512)
    term_putc('\n')
    i = 0
    while i < sz:
        if read_buf[i] == 10 and lc < 64:
            ends[lc] = i
            lc = lc + 1
        i = i + 1
    if sz > 0 and read_buf[sz - 1] != 10 and lc < 64:
        ends[lc] = sz
        lc = lc + 1
    i = lc - 1
    while i >= 0:
        st = 0
        if i > 0:
            st = ends[i - 1] + 1
        ed = ends[i]
        while st < ed:
            if read_buf[st] != 10:
                term_putc(cast[char](read_buf[st]))
            st = st + 1
        term_putc('\n')
        i = i - 1

def cmd_fold():
    """fold <file> - wrap at 60 columns"""
    arg: Ptr[char] = cmd_get_arg()
    sz: int32 = 0
    col: int32 = 0
    i: int32 = 0

    if arg[0] == '\0':
        term_puts("\nUsage: fold <file>\n")
        return
    build_path(arg)
    if not ramfs_exists(&path_buf[0]):
        term_puts("\nfold: file not found\n")
        return
    sz = ramfs_read(&path_buf[0], &read_buf[0], 512)
    term_putc('\n')
    while i < sz:
        if read_buf[i] == 10:
            term_putc('\n')
            col = 0
        else:
            if col >= 60:
                term_putc('\n')
                col = 0
            term_putc(cast[char](read_buf[i]))
            col = col + 1
        i = i + 1

def cmd_cut():
    """cut <file> - first 20 chars per line"""
    arg: Ptr[char] = cmd_get_arg()
    sz: int32 = 0
    cnt: int32 = 0
    i: int32 = 0

    if arg[0] == '\0':
        term_puts("\nUsage: cut <file>\n")
        return
    build_path(arg)
    if not ramfs_exists(&path_buf[0]):
        term_puts("\ncut: file not found\n")
        return
    sz = ramfs_read(&path_buf[0], &read_buf[0], 512)
    term_putc('\n')
    while i < sz:
        if read_buf[i] == 10:
            term_putc('\n')
            cnt = 0
        else:
            if cnt < 20:
                term_putc(cast[char](read_buf[i]))
            cnt = cnt + 1
        i = i + 1

def cmd_wc():
    """wc <file> - word/line/char count"""
    arg: Ptr[char] = cmd_get_arg()
    sz: int32 = 0
    lines: int32 = 0
    words: int32 = 0
    in_word: bool = False
    i: int32 = 0
    c: int32 = 0

    if arg[0] == '\0':
        term_puts("\nUsage: wc <file>\n")
        return
    build_path(arg)
    if not ramfs_exists(&path_buf[0]):
        term_puts("\nwc: file not found\n")
        return
    sz = ramfs_read(&path_buf[0], &read_buf[0], 512)
    while i < sz:
        c = cast[int32](read_buf[i])
        if c == 10:
            lines = lines + 1
        if c == 32 or c == 10 or c == 9:
            if in_word:
                words = words + 1
                in_word = False
        else:
            in_word = True
        i = i + 1
    if in_word:
        words = words + 1
    term_putc('\n')
    term_puts(int_to_str(lines))
    term_putc(' ')
    term_puts(int_to_str(words))
    term_putc(' ')
    term_puts(int_to_str(sz))
    term_putc(' ')
    term_puts(arg)
    term_putc('\n')

def exec_text_cmd(cmd: Ptr[char]) -> bool:
    """Handle text processing commands. Returns True if handled."""
    if cmd_starts_with("grep"):
        cmd_grep()
        return True
    if cmd_starts_with("sort"):
        cmd_sort()
        return True
    if cmd_starts_with("uniq"):
        cmd_uniq()
        return True
    if cmd_starts_with("tr"):
        cmd_tr()
        return True
    if cmd_starts_with("tac"):
        cmd_tac()
        return True
    if cmd_starts_with("fold"):
        cmd_fold()
        return True
    if cmd_starts_with("cut"):
        cmd_cut()
        return True
    if cmd_starts_with("wc"):
        cmd_wc()
        return True
    return False

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
    elif cmd_starts_with("seq"):
        # seq <end> or seq <start> <end>
        arg11: Ptr[char] = cmd_get_arg()
        if arg11[0] == '\0':
            term_puts("\nUsage: seq [start] end\n")
        else:
            start: int32 = 1
            end: int32 = 0
            # Check if there's a second number
            i: int32 = 0
            while arg11[i] != '\0' and arg11[i] != ' ':
                i = i + 1
            if arg11[i] == ' ':
                arg11[i] = '\0'
                start = atoi(arg11)
                end = atoi(&arg11[i + 1])
            else:
                end = atoi(arg11)
            term_putc('\n')
            j: int32 = start
            while j <= end:
                term_puts(int_to_str(j))
                term_putc('\n')
                j = j + 1
    elif cmd_starts_with("factor"):
        # factor <number>
        arg12: Ptr[char] = cmd_get_arg()
        if arg12[0] == '\0':
            term_puts("\nUsage: factor <number>\n")
        else:
            n: int32 = atoi(arg12)
            term_putc('\n')
            term_puts(int_to_str(n))
            term_puts(": ")
            if n >= 2:
                # Factor out 2s
                while n % 2 == 0:
                    term_puts("2 ")
                    n = n / 2
                # Factor out odd numbers
                i: int32 = 3
                while i * i <= n:
                    while n % i == 0:
                        term_puts(int_to_str(i))
                        term_putc(' ')
                        n = n / i
                    i = i + 2
                if n > 1:
                    term_puts(int_to_str(n))
            term_putc('\n')
    elif strcmp(cmd, "fortune") == 0:
        term_putc('\n')
        # Simple fortune cookie messages
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
        # Use a simple hash of heap_used as "random"
        idx: int32 = heap_used() % 10
        term_puts(fortunes[idx])
        term_putc('\n')
    elif cmd_starts_with("basename"):
        # basename <path>
        arg13: Ptr[char] = cmd_get_arg()
        if arg13[0] == '\0':
            term_puts("\nUsage: basename <path>\n")
        else:
            # Find last /
            i: int32 = strlen(arg13) - 1
            while i >= 0 and arg13[i] != '/':
                i = i - 1
            term_putc('\n')
            term_puts(&arg13[i + 1])
            term_putc('\n')
    elif cmd_starts_with("dirname"):
        # dirname <path>
        arg14: Ptr[char] = cmd_get_arg()
        if arg14[0] == '\0':
            term_puts("\nUsage: dirname <path>\n")
        else:
            # Find last /
            i: int32 = strlen(arg14) - 1
            while i > 0 and arg14[i] != '/':
                i = i - 1
            term_putc('\n')
            if i == 0:
                if arg14[0] == '/':
                    term_putc('/')
                else:
                    term_putc('.')
            else:
                arg14[i] = '\0'
                term_puts(arg14)
            term_putc('\n')
    elif strcmp(cmd, "arch") == 0:
        term_puts("\narmv7m\n")
    elif strcmp(cmd, "nproc") == 0:
        term_puts("\n1\n")
    elif strcmp(cmd, "tty") == 0:
        term_puts("\n/dev/ttyS0\n")
    elif strcmp(cmd, "logname") == 0:
        term_puts("\nroot\n")
    elif strcmp(cmd, "printenv") == 0:
        term_puts("\nHOME=/home\n")
        term_puts("USER=root\n")
        term_puts("SHELL=/bin/psh\n")
        term_puts("PATH=/bin\n")
        term_puts("TERM=vtnext\n")
        term_puts("PWD=")
        term_puts(&cwd[0])
        term_putc('\n')
    elif cmd_starts_with("banner"):
        # banner <text>
        arg15: Ptr[char] = cmd_get_arg()
        if arg15[0] == '\0':
            term_puts("\nUsage: banner <text>\n")
        else:
            term_putc('\n')
            # Print 5 lines of the text (simple banner)
            line: int32 = 0
            while line < 5:
                i: int32 = 0
                while arg15[i] != '\0':
                    c: char = arg15[i]
                    j: int32 = 0
                    while j < 5:
                        if c >= 'a' and c <= 'z':
                            term_putc(cast[char](cast[int32](c) - 32))
                        elif c == ' ':
                            term_putc(' ')
                        else:
                            term_putc(c)
                        j = j + 1
                    term_putc(' ')
                    i = i + 1
                term_putc('\n')
                line = line + 1
    elif strcmp(cmd, "dmesg") == 0:
        term_puts("\n[    0.000] Pynux kernel booting...\n")
        term_puts("[    0.001] UART initialized\n")
        term_puts("[    0.002] Heap initialized (16KB)\n")
        term_puts("[    0.003] Timer initialized\n")
        term_puts("[    0.004] RAMFS initialized\n")
        term_puts("[    0.005] Kernel ready\n")
    elif strcmp(cmd, "lscpu") == 0:
        term_puts("\nArchitecture:    armv7m\n")
        term_puts("Vendor:          ARM\n")
        term_puts("Model:           Cortex-M3\n")
        term_puts("CPU(s):          1\n")
        term_puts("Max MHz:         25\n")
    elif strcmp(cmd, "sync") == 0:
        term_puts("\n")  # In RAMFS, sync is a no-op
    elif strcmp(cmd, "reset") == 0:
        term_init()
        needs_full_redraw = True
    elif cmd_starts_with("head"):
        # head <file> - show first lines of file
        arg16: Ptr[char] = cmd_get_arg()
        if arg16[0] == '\0':
            term_puts("\nUsage: head <file>\n")
        else:
            build_path(arg16)
            if ramfs_exists(&path_buf[0]) and not ramfs_isdir(&path_buf[0]):
                term_putc('\n')
                bytes_read: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
                if bytes_read > 0:
                    read_buf[bytes_read] = 0
                    # Print first 10 lines
                    lines: int32 = 0
                    i: int32 = 0
                    while i < bytes_read and lines < 10:
                        term_putc(cast[char](read_buf[i]))
                        if read_buf[i] == 10:
                            lines = lines + 1
                        i = i + 1
                term_putc('\n')
            else:
                term_puts("\nNo such file: ")
                term_puts(arg16)
                term_putc('\n')
    elif cmd_starts_with("tail"):
        # tail <file> - show last lines
        arg17: Ptr[char] = cmd_get_arg()
        if arg17[0] == '\0':
            term_puts("\nUsage: tail <file>\n")
        else:
            build_path(arg17)
            if ramfs_exists(&path_buf[0]) and not ramfs_isdir(&path_buf[0]):
                term_putc('\n')
                bytes_read: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
                if bytes_read > 0:
                    read_buf[bytes_read] = 0
                    term_puts(cast[Ptr[char]](&read_buf[0]))
                term_putc('\n')
            else:
                term_puts("\nNo such file: ")
                term_puts(arg17)
                term_putc('\n')
    elif cmd_starts_with("wc"):
        # wc <file> - word count
        arg18: Ptr[char] = cmd_get_arg()
        if arg18[0] == '\0':
            term_puts("\nUsage: wc <file>\n")
        else:
            build_path(arg18)
            if ramfs_exists(&path_buf[0]) and not ramfs_isdir(&path_buf[0]):
                bytes_read: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
                if bytes_read > 0:
                    read_buf[bytes_read] = 0
                    lines: int32 = 0
                    words: int32 = 0
                    chars: int32 = bytes_read
                    in_word: bool = False
                    i: int32 = 0
                    while i < bytes_read:
                        c: char = cast[char](read_buf[i])
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
                    term_puts("\n  ")
                    term_puts(int_to_str(lines))
                    term_puts("  ")
                    term_puts(int_to_str(words))
                    term_puts("  ")
                    term_puts(int_to_str(chars))
                    term_puts(" ")
                    term_puts(arg18)
                    term_putc('\n')
                else:
                    term_puts("\n  0  0  0 ")
                    term_puts(arg18)
                    term_putc('\n')
            else:
                term_puts("\nNo such file: ")
                term_puts(arg18)
                term_putc('\n')
    elif cmd_starts_with("stat"):
        # stat <file>
        arg19: Ptr[char] = cmd_get_arg()
        if arg19[0] == '\0':
            term_puts("\nUsage: stat <file>\n")
        else:
            build_path(arg19)
            if ramfs_exists(&path_buf[0]):
                term_puts("\n  File: ")
                term_puts(&path_buf[0])
                term_putc('\n')
                if ramfs_isdir(&path_buf[0]):
                    term_puts("  Type: directory\n")
                else:
                    term_puts("  Type: regular file\n")
                    bytes_read: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
                    term_puts("  Size: ")
                    term_puts(int_to_str(bytes_read))
                    term_puts(" bytes\n")
            else:
                term_puts("\nNo such file: ")
                term_puts(arg19)
                term_putc('\n')
    elif strcmp(cmd, "users") == 0:
        term_puts("\nroot\n")
    elif strcmp(cmd, "groups") == 0:
        term_puts("\nroot\n")
    elif strcmp(cmd, "kill") == 0:
        term_puts("\nkill: No processes to kill\n")
    elif strcmp(cmd, "ps") == 0:
        term_puts("\n  PID TTY      TIME CMD\n")
        term_puts("    1 ttyS0    0:00 psh\n")
    elif strcmp(cmd, "df") == 0:
        term_puts("\nFilesystem  1K-blocks  Used  Available  Use%  Mounted on\n")
        term_puts("ramfs            16     ")
        used_kb: int32 = heap_used() / 1024
        term_puts(int_to_str(used_kb))
        term_puts("         ")
        free_kb: int32 = heap_remaining() / 1024
        term_puts(int_to_str(free_kb))
        term_puts("     ")
        pct: int32 = (heap_used() * 100) / heap_total()
        term_puts(int_to_str(pct))
        term_puts("%   /\n")
    elif strcmp(cmd, "mount") == 0:
        term_puts("\nramfs on / type ramfs (rw)\n")
    elif strcmp(cmd, "umount") == 0:
        term_puts("\numount: cannot unmount /: device is busy\n")
    elif cmd_starts_with("expr") or cmd_starts_with("calc"):
        # Simple expression evaluator: expr <num> <op> <num>
        arg20: Ptr[char] = cmd_get_arg()
        if arg20[0] == '\0':
            term_puts("\nUsage: expr <num> <op> <num>\n")
        else:
            # Parse: num op num
            num1: int32 = atoi(arg20)
            # Find operator
            i: int32 = 0
            while arg20[i] != '\0' and arg20[i] != ' ':
                i = i + 1
            while arg20[i] == ' ':
                i = i + 1
            op: char = arg20[i]
            # Find second number
            i = i + 1
            while arg20[i] == ' ':
                i = i + 1
            num2: int32 = atoi(&arg20[i])
            result: int32 = 0
            valid: bool = True
            if op == '+':
                result = num1 + num2
            elif op == '-':
                result = num1 - num2
            elif op == '*':
                result = num1 * num2
            elif op == '/':
                if num2 != 0:
                    result = num1 / num2
                else:
                    term_puts("\nDivision by zero\n")
                    valid = False
            elif op == '%':
                if num2 != 0:
                    result = num1 % num2
                else:
                    valid = False
            else:
                term_puts("\nUnknown operator: ")
                term_putc(op)
                term_putc('\n')
                valid = False
            if valid:
                term_putc('\n')
                term_puts(int_to_str(result))
                term_putc('\n')
    elif cmd_starts_with("which") or cmd_starts_with("type"):
        arg21: Ptr[char] = cmd_get_arg()
        if arg21[0] == '\0':
            term_puts("\nUsage: which <command>\n")
        else:
            term_putc('\n')
            term_puts(arg21)
            term_puts(": shell built-in\n")
    elif strcmp(cmd, "history") == 0:
        term_puts("\nNo history available (single-line buffer)\n")
    elif strcmp(cmd, "alias") == 0:
        term_puts("\nNo aliases defined\n")
    elif strcmp(cmd, "unalias") == 0:
        term_puts("\nunalias: no aliases to remove\n")
    elif strcmp(cmd, "export") == 0:
        term_puts("\nexport: no environment to modify\n")
    elif strcmp(cmd, "set") == 0:
        term_puts("\nPOSIXLY_CORRECT=y\n")
        term_puts("PATH=/bin\n")
        term_puts("HOME=/home\n")
        term_puts("PWD=")
        term_puts(&cwd[0])
        term_putc('\n')
    elif strcmp(cmd, "unset") == 0:
        term_puts("\nunset: cannot unset in this shell\n")
    elif strcmp(cmd, "source") == 0 or strcmp(cmd, ".") == 0:
        term_puts("\nUsage: source <file> (not implemented)\n")
    elif cmd_starts_with("test") or cmd_buffer[0] == '[':
        term_puts("\ntest: not implemented\n")
    elif cmd_starts_with("printf"):
        arg22: Ptr[char] = cmd_get_arg()
        term_putc('\n')
        term_puts(arg22)
    elif strcmp(cmd, "read") == 0:
        term_puts("\nread: not implemented\n")
    elif strcmp(cmd, "exec") == 0:
        term_puts("\nexec: not implemented\n")
    elif strcmp(cmd, "wait") == 0:
        term_puts("\nwait: no jobs to wait for\n")
    elif strcmp(cmd, "jobs") == 0:
        term_puts("\njobs: no background jobs\n")
    elif strcmp(cmd, "fg") == 0:
        term_puts("\nfg: no foreground jobs\n")
    elif strcmp(cmd, "bg") == 0:
        term_puts("\nbg: no background jobs\n")
    elif strcmp(cmd, "time") == 0:
        term_puts("\nreal 0m0.000s\nuser 0m0.000s\nsys  0m0.000s\n")
    elif strcmp(cmd, "times") == 0:
        term_puts("\n0m0.000s 0m0.000s\n")
    elif strcmp(cmd, "ulimit") == 0:
        term_puts("\nunlimited\n")
    elif strcmp(cmd, "umask") == 0:
        term_puts("\n0022\n")
    elif strcmp(cmd, "getconf") == 0:
        term_puts("\nUsage: getconf <name>\n")
    elif strcmp(cmd, "locale") == 0:
        term_puts("\nLANG=C\n")
        term_puts("LC_ALL=C\n")
    elif strcmp(cmd, "mesg") == 0:
        term_puts("\nis y\n")
    elif strcmp(cmd, "stty") == 0:
        term_puts("\nspeed 115200 baud\n")
        term_puts("rows 24; columns 80;\n")
    elif strcmp(cmd, "tput") == 0:
        term_putc('\n')
    elif strcmp(cmd, "pathchk") == 0:
        term_puts("\npathchk: no arguments\n")
    elif strcmp(cmd, "link") == 0 or strcmp(cmd, "ln") == 0:
        term_puts("\nlink: not supported on ramfs\n")
    elif strcmp(cmd, "unlink") == 0:
        term_puts("\nunlink: use rm instead\n")
    elif strcmp(cmd, "readlink") == 0:
        term_puts("\nreadlink: no symlinks on ramfs\n")
    elif strcmp(cmd, "realpath") == 0:
        arg23: Ptr[char] = cmd_get_arg()
        if arg23[0] == '\0':
            term_puts("\nUsage: realpath <path>\n")
        else:
            build_path(arg23)
            term_putc('\n')
            term_puts(&path_buf[0])
            term_putc('\n')
    elif cmd_starts_with("mktemp"):
        term_puts("\n/tmp/tmp.XXXXXX\n")
    elif strcmp(cmd, "install") == 0:
        term_puts("\ninstall: no destination specified\n")
    elif strcmp(cmd, "shred") == 0:
        term_puts("\nshred: not implemented (ramfs)\n")
    elif strcmp(cmd, "truncate") == 0:
        term_puts("\ntruncate: not implemented\n")

    # Text processing commands (in separate function to avoid branch offset limits)
    elif exec_text_cmd(cmd):
        pass  # Handled by exec_text_cmd

    # Simple text commands that fit here
    elif cmd_starts_with("cal"):
        term_puts("\n    January 2025\nSu Mo Tu We Th Fr Sa\n          1  2  3  4\n 5  6  7  8  9 10 11\n12 13 14 15 16 17 18\n19 20 21 22 23 24 25\n26 27 28 29 30 31\n")

    elif cmd_starts_with("rev"):
        arg_rv: Ptr[char] = cmd_get_arg()
        if arg_rv[0] == '\0':
            term_puts("\nUsage: rev <file>\n")
        else:
            build_path(arg_rv)
            if not ramfs_exists(&path_buf[0]):
                term_puts("\nrev: file not found\n")
            else:
                szr: int32 = ramfs_read(&path_buf[0], &read_buf[0], 512)
                term_putc('\n')
                lsr: int32 = 0
                ir: int32 = 0
                jr: int32 = 0
                while ir <= szr:
                    if ir == szr or read_buf[ir] == 10:
                        jr = ir - 1
                        while jr >= lsr:
                            term_putc(cast[char](read_buf[jr]))
                            jr = jr - 1
                        term_putc('\n')
                        lsr = ir + 1
                    ir = ir + 1

    elif cmd_starts_with("nl"):
        arg_n: Ptr[char] = cmd_get_arg()
        if arg_n[0] == '\0':
            term_puts("\nUsage: nl <file>\n")
        else:
            build_path(arg_n)
            if not ramfs_exists(&path_buf[0]):
                term_puts("\nnl: file not found\n")
            else:
                szn: int32 = ramfs_read(&path_buf[0], &read_buf[0], 512)
                term_putc('\n')
                lnn: int32 = 1
                term_puts(int_to_str(lnn))
                term_putc('\t')
                inn: int32 = 0
                while inn < szn:
                    if read_buf[inn] == 10:
                        term_putc('\n')
                        lnn = lnn + 1
                        if inn < szn - 1:
                            term_puts(int_to_str(lnn))
                            term_putc('\t')
                    else:
                        term_putc(cast[char](read_buf[inn]))
                    inn = inn + 1

    elif cmd_starts_with("xxd"):
        arg_x: Ptr[char] = cmd_get_arg()
        if arg_x[0] == '\0':
            term_puts("\nUsage: xxd <file>\n")
        else:
            build_path(arg_x)
            if not ramfs_exists(&path_buf[0]):
                term_puts("\nxxd: file not found\n")
            else:
                szx: int32 = ramfs_read(&path_buf[0], &read_buf[0], 128)
                term_putc('\n')
                hxc: Ptr[char] = "0123456789abcdef"
                ix: int32 = 0
                jx: int32 = 0
                bx: int32 = 0
                while ix < szx:
                    term_putc(hxc[(ix >> 4) & 15])
                    term_putc(hxc[ix & 15])
                    term_puts(": ")
                    jx = 0
                    while jx < 8 and ix + jx < szx:
                        bx = cast[int32](read_buf[ix + jx])
                        term_putc(hxc[(bx >> 4) & 15])
                        term_putc(hxc[bx & 15])
                        term_putc(' ')
                        jx = jx + 1
                    term_putc(' ')
                    jx = 0
                    while jx < 8 and ix + jx < szx:
                        bx = cast[int32](read_buf[ix + jx])
                        if bx >= 32 and bx < 127:
                            term_putc(cast[char](bx))
                        else:
                            term_putc('.')
                        jx = jx + 1
                    term_putc('\n')
                    ix = ix + 8

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
