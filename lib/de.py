# Pynux Desktop Environment
#
# Graphical desktop with windowed applications over VTNext protocol.
# Features: Menu, multiple terminals, text editor, file manager

from lib.io import uart_putc, uart_getc, uart_available, print_str, print_int
from lib.vtnext import vtn_init, vtn_clear, vtn_rect, vtn_textline
from lib.vtnext import vtn_clear_rect, vtn_present, vtn_flush
from lib.vtnext import vtn_line, vtn_text, vtn_rect_outline
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

MENU_BG_R: int32 = 45
MENU_BG_G: int32 = 50
MENU_BG_B: int32 = 70

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

SELECT_R: int32 = 70
SELECT_G: int32 = 100
SELECT_B: int32 = 150

# Window constants
WIN_TITLE_H: int32 = 20
MENU_H: int32 = 24
STATUS_H: int32 = 20
CHAR_W: int32 = 10  # Match pygame monospace 16pt font width
CHAR_H: int32 = 16

# ============================================================================
# Window management
# ============================================================================

# Window types
WIN_NONE: int32 = 0
WIN_TERMINAL: int32 = 1
WIN_EDITOR: int32 = 2
WIN_FILES: int32 = 3

# Maximum windows
MAX_WINDOWS: int32 = 4

# Window state arrays
win_type: Array[4, int32]
win_x: Array[4, int32]
win_y: Array[4, int32]
win_w: Array[4, int32]
win_h: Array[4, int32]
win_visible: Array[4, bool]
win_dirty: Array[4, bool]

# Active window index
active_win: int32 = -1
win_count: int32 = 0

# Menu state
menu_open: bool = False
menu_selection: int32 = 0
MENU_ITEMS: int32 = 4

# Global dirty flags
needs_full_redraw: bool = True
menu_dirty: bool = False
status_dirty: bool = False

# ============================================================================
# Terminal state (per-window terminal data)
# ============================================================================

# Terminal dimensions (in chars)
TERM_COLS: int32 = 70  # Reduced to fit with 10px char width
TERM_ROWS: int32 = 20
TERM_SCROLL: int32 = 100

# Terminal buffers - one per possible terminal window
# Each terminal gets 100 lines * 70 chars = 7000 bytes
term_buf0: Array[7000, char]
term_buf1: Array[7000, char]

# Line dirty flags
term_dirty0: Array[100, bool]
term_dirty1: Array[100, bool]

# Terminal state per window
term_scroll: Array[4, int32]
term_cursor_x: Array[4, int32]
term_cursor_y: Array[4, int32]

# Command input buffer (shared)
cmd_buffer: Array[256, char]
cmd_pos: int32 = 0

# Current working directory per terminal
term_cwd0: Array[128, char]
term_cwd1: Array[128, char]

# ============================================================================
# Editor state
# ============================================================================

edit_buffer: Array[4096, char]
edit_size: int32 = 0
edit_cursor: int32 = 0
edit_scroll: int32 = 0
edit_filename: Array[128, char]
edit_dirty: bool = False
edit_modified: bool = False

# ============================================================================
# File manager state
# ============================================================================

fm_cwd: Array[128, char]
fm_selection: int32 = 0
fm_count: int32 = 0
fm_names: Array[512, char]  # 16 entries * 32 chars
fm_types: Array[16, int32]  # 0=file, 1=dir
fm_dirty: bool = False

# ============================================================================
# Shared buffers
# ============================================================================

path_buf: Array[256, char]
read_buf: Array[512, uint8]
num_buf: Array[16, char]
status_buf: Array[80, char]
line_buf: Array[128, char]

# ============================================================================
# Helper functions
# ============================================================================

def int_to_str(n: int32) -> Ptr[char]:
    if n == 0:
        num_buf[0] = '0'
        num_buf[1] = '\0'
        return &num_buf[0]
    neg: bool = False
    if n < 0:
        neg = True
        n = -n
    i: int32 = 0
    while n > 0:
        num_buf[i] = cast[char](48 + (n % 10))
        n = n / 10
        i = i + 1
    if neg:
        num_buf[i] = '-'
        i = i + 1
    num_buf[i] = '\0'
    j: int32 = 0
    k: int32 = i - 1
    while j < k:
        tmp: char = num_buf[j]
        num_buf[j] = num_buf[k]
        num_buf[k] = tmp
        j = j + 1
        k = k - 1
    return &num_buf[0]

def build_path(base: Ptr[char], name: Ptr[char]):
    if name[0] == '/':
        strcpy(&path_buf[0], name)
    else:
        strcpy(&path_buf[0], base)
        blen: int32 = strlen(base)
        if blen > 0 and base[blen - 1] != '/':
            strcat(&path_buf[0], "/")
        strcat(&path_buf[0], name)

# ============================================================================
# Window management functions
# ============================================================================

def win_create(wtype: int32, x: int32, y: int32, w: int32, h: int32) -> int32:
    global win_count, active_win
    if win_count >= MAX_WINDOWS:
        return -1
    idx: int32 = win_count
    win_type[idx] = wtype
    win_x[idx] = x
    win_y[idx] = y
    win_w[idx] = w
    win_h[idx] = h
    win_visible[idx] = True
    win_dirty[idx] = True
    win_count = win_count + 1
    active_win = idx
    return idx

def win_close(idx: int32):
    global win_count, active_win, needs_full_redraw
    if idx < 0 or idx >= win_count:
        return
    # Shift windows down
    i: int32 = idx
    while i < win_count - 1:
        win_type[i] = win_type[i + 1]
        win_x[i] = win_x[i + 1]
        win_y[i] = win_y[i + 1]
        win_w[i] = win_w[i + 1]
        win_h[i] = win_h[i + 1]
        win_visible[i] = win_visible[i + 1]
        win_dirty[i] = win_dirty[i + 1]
        i = i + 1
    win_count = win_count - 1
    if active_win >= win_count:
        active_win = win_count - 1
    needs_full_redraw = True

def win_focus(idx: int32):
    global active_win, needs_full_redraw
    if idx >= 0 and idx < win_count:
        active_win = idx
        needs_full_redraw = True

# ============================================================================
# Terminal functions
# ============================================================================

def term_get_buf(idx: int32) -> Ptr[char]:
    if idx == 0:
        return &term_buf0[0]
    return &term_buf1[0]

def term_get_dirty(idx: int32) -> Ptr[bool]:
    if idx == 0:
        return &term_dirty0[0]
    return &term_dirty1[0]

def term_get_cwd(idx: int32) -> Ptr[char]:
    if idx == 0:
        return &term_cwd0[0]
    return &term_cwd1[0]

def term_line_ptr(idx: int32, line: int32) -> Ptr[char]:
    buf: Ptr[char] = term_get_buf(idx)
    return &buf[line * TERM_COLS]

def term_clear_line(idx: int32, line: int32):
    ptr: Ptr[char] = term_line_ptr(idx, line)
    i: int32 = 0
    while i < TERM_COLS:
        ptr[i] = ' '
        i = i + 1
    dirty: Ptr[bool] = term_get_dirty(idx)
    dirty[line] = True

def term_init_win(idx: int32):
    i: int32 = 0
    while i < TERM_SCROLL:
        term_clear_line(idx, i)
        i = i + 1
    term_scroll[idx] = 0
    term_cursor_x[idx] = 0
    term_cursor_y[idx] = 0
    cwd: Ptr[char] = term_get_cwd(idx)
    cwd[0] = '/'
    cwd[1] = '\0'

def term_scroll_up(idx: int32):
    scr: int32 = term_scroll[idx]
    if scr < TERM_SCROLL - TERM_ROWS:
        term_scroll[idx] = scr + 1
    else:
        # Shift buffer up
        buf: Ptr[char] = term_get_buf(idx)
        i: int32 = 0
        while i < (TERM_SCROLL - 1) * TERM_COLS:
            buf[i] = buf[i + TERM_COLS]
            i = i + 1
        term_clear_line(idx, TERM_SCROLL - 1)
    # Mark visible lines dirty
    dirty: Ptr[bool] = term_get_dirty(idx)
    scr = term_scroll[idx]
    i = 0
    while i < TERM_ROWS:
        dirty[scr + i] = True
        i = i + 1

def term_newline(idx: int32):
    term_cursor_x[idx] = 0
    cy: int32 = term_cursor_y[idx] + 1
    if cy >= TERM_ROWS:
        cy = TERM_ROWS - 1
        term_scroll_up(idx)
    term_cursor_y[idx] = cy

def term_putc_idx(idx: int32, c: char):
    if c == '\n':
        term_newline(idx)
        return
    if c == '\r':
        term_cursor_x[idx] = 0
        return
    if c == '\b':
        if term_cursor_x[idx] > 0:
            term_cursor_x[idx] = term_cursor_x[idx] - 1
        return
    line: int32 = term_scroll[idx] + term_cursor_y[idx]
    ptr: Ptr[char] = term_line_ptr(idx, line)
    cx: int32 = term_cursor_x[idx]
    ptr[cx] = c
    dirty: Ptr[bool] = term_get_dirty(idx)
    dirty[line] = True
    cx = cx + 1
    if cx >= TERM_COLS:
        term_newline(idx)
    else:
        term_cursor_x[idx] = cx
    win_dirty[idx] = True

def term_puts_idx(idx: int32, s: Ptr[char]):
    i: int32 = 0
    while s[i] != '\0':
        term_putc_idx(idx, s[i])
        i = i + 1

def term_print_prompt(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    term_puts_idx(idx, "pynux:")
    term_puts_idx(idx, cwd)
    term_puts_idx(idx, "> ")

# ============================================================================
# Terminal command helpers
# ============================================================================

def cmd_get_arg() -> Ptr[char]:
    i: int32 = 0
    while cmd_buffer[i] != '\0' and cmd_buffer[i] != ' ':
        i = i + 1
    while cmd_buffer[i] == ' ':
        i = i + 1
    return &cmd_buffer[i]

def cmd_starts_with(prefix: Ptr[char]) -> bool:
    i: int32 = 0
    while prefix[i] != '\0':
        if cmd_buffer[i] != prefix[i]:
            return False
        i = i + 1
    return cmd_buffer[i] == ' ' or cmd_buffer[i] == '\0'

# ============================================================================
# Terminal commands (split into small functions to avoid branch limits)
# ============================================================================

def cmd_help(idx: int32):
    term_puts_idx(idx, "\nCommands: help clear ls cd cat mkdir touch rm\n")
    term_puts_idx(idx, "echo pwd cp write uname free whoami hostname\n")
    term_puts_idx(idx, "date uptime id env ps df stat head tail wc\n")

def cmd_ls(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    term_putc_idx(idx, '\n')
    name: Array[64, char]
    i: int32 = 0
    result: int32 = ramfs_readdir(cwd, i, &name[0])
    while result >= 0:
        term_puts_idx(idx, &name[0])
        if result == 1:
            term_putc_idx(idx, '/')
        term_puts_idx(idx, "  ")
        i = i + 1
        result = ramfs_readdir(cwd, i, &name[0])
    term_putc_idx(idx, '\n')

def cmd_cd(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg()
    if arg[0] == '\0':
        cwd[0] = '/'
        cwd[1] = '\0'
        return
    if strcmp(arg, "..") == 0:
        clen: int32 = strlen(cwd)
        if clen > 1:
            i: int32 = clen - 1
            if cwd[i] == '/':
                i = i - 1
            while i > 0 and cwd[i] != '/':
                i = i - 1
            if i == 0:
                cwd[0] = '/'
                cwd[1] = '\0'
            else:
                cwd[i] = '\0'
        return
    build_path(cwd, arg)
    term_puts_idx(idx, "\nChecking: ")
    term_puts_idx(idx, &path_buf[0])
    if ramfs_exists(&path_buf[0]):
        term_puts_idx(idx, " [exists]")
        if ramfs_isdir(&path_buf[0]):
            term_puts_idx(idx, " [isdir]")
            strcpy(cwd, &path_buf[0])
        else:
            term_puts_idx(idx, " [not dir]")
    else:
        term_puts_idx(idx, " [not found]")

def cmd_cat(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg()
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: cat <file>\n")
        return
    build_path(cwd, arg)
    if not ramfs_exists(&path_buf[0]) or ramfs_isdir(&path_buf[0]):
        term_puts_idx(idx, "\nFile not found\n")
        return
    term_putc_idx(idx, '\n')
    sz: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
    if sz > 0:
        read_buf[sz] = 0
        term_puts_idx(idx, cast[Ptr[char]](&read_buf[0]))
    term_putc_idx(idx, '\n')

def cmd_mkdir(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg()
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: mkdir <name>\n")
        return
    build_path(cwd, arg)
    if ramfs_create(&path_buf[0], True) >= 0:
        term_puts_idx(idx, "\nCreated\n")
    else:
        term_puts_idx(idx, "\nFailed\n")

def cmd_touch(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg()
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: touch <name>\n")
        return
    build_path(cwd, arg)
    if ramfs_create(&path_buf[0], False) >= 0:
        term_puts_idx(idx, "\nCreated\n")
    else:
        term_puts_idx(idx, "\nFailed\n")

def cmd_rm(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg()
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: rm <name>\n")
        return
    build_path(cwd, arg)
    if ramfs_delete(&path_buf[0]) >= 0:
        term_puts_idx(idx, "\nRemoved\n")
    else:
        term_puts_idx(idx, "\nFailed\n")

def cmd_echo(idx: int32):
    arg: Ptr[char] = cmd_get_arg()
    term_putc_idx(idx, '\n')
    term_puts_idx(idx, arg)
    term_putc_idx(idx, '\n')

def cmd_pwd(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    term_putc_idx(idx, '\n')
    term_puts_idx(idx, cwd)
    term_putc_idx(idx, '\n')

def cmd_write(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg()
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: write <file> <text>\n")
        return
    i: int32 = 0
    while arg[i] != '\0' and arg[i] != ' ':
        i = i + 1
    if arg[i] != ' ':
        term_puts_idx(idx, "\nUsage: write <file> <text>\n")
        return
    arg[i] = '\0'
    content: Ptr[char] = &arg[i + 1]
    build_path(cwd, arg)
    if not ramfs_exists(&path_buf[0]):
        ramfs_create(&path_buf[0], False)
    if ramfs_write(&path_buf[0], content) >= 0:
        term_puts_idx(idx, "\nWritten\n")
    else:
        term_puts_idx(idx, "\nFailed\n")

def cmd_uname(idx: int32):
    arg: Ptr[char] = cmd_get_arg()
    term_putc_idx(idx, '\n')
    if arg[0] == '\0' or strcmp(arg, "-s") == 0:
        term_puts_idx(idx, "Pynux\n")
    elif strcmp(arg, "-a") == 0:
        term_puts_idx(idx, "Pynux 0.1.0 armv7m Cortex-M3\n")
    else:
        term_puts_idx(idx, "Pynux\n")

def cmd_free(idx: int32):
    term_puts_idx(idx, "\n       total     used     free\n")
    term_puts_idx(idx, "Heap:  ")
    term_puts_idx(idx, int_to_str(heap_total()))
    term_puts_idx(idx, "    ")
    term_puts_idx(idx, int_to_str(heap_used()))
    term_puts_idx(idx, "    ")
    term_puts_idx(idx, int_to_str(heap_remaining()))
    term_putc_idx(idx, '\n')

def cmd_stat(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg()
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: stat <file>\n")
        return
    build_path(cwd, arg)
    if not ramfs_exists(&path_buf[0]):
        term_puts_idx(idx, "\nNot found\n")
        return
    term_puts_idx(idx, "\n  File: ")
    term_puts_idx(idx, &path_buf[0])
    term_putc_idx(idx, '\n')
    if ramfs_isdir(&path_buf[0]):
        term_puts_idx(idx, "  Type: directory\n")
    else:
        term_puts_idx(idx, "  Type: file\n")
        sz: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
        term_puts_idx(idx, "  Size: ")
        term_puts_idx(idx, int_to_str(sz))
        term_puts_idx(idx, "\n")

# ============================================================================
# Terminal command execution
# ============================================================================

def term_exec_cmd(idx: int32):
    global cmd_pos
    cmd_buffer[cmd_pos] = '\0'
    if cmd_pos == 0:
        term_print_prompt(idx)
        return
    # Dispatch commands
    if strcmp(&cmd_buffer[0], "help") == 0:
        cmd_help(idx)
    elif strcmp(&cmd_buffer[0], "clear") == 0:
        term_init_win(idx)
        win_dirty[idx] = True
    elif strcmp(&cmd_buffer[0], "ls") == 0:
        cmd_ls(idx)
    elif cmd_starts_with("cd"):
        cmd_cd(idx)
    elif cmd_starts_with("cat"):
        cmd_cat(idx)
    elif cmd_starts_with("mkdir"):
        cmd_mkdir(idx)
    elif cmd_starts_with("touch"):
        cmd_touch(idx)
    elif cmd_starts_with("rm"):
        cmd_rm(idx)
    elif cmd_starts_with("echo"):
        cmd_echo(idx)
    elif strcmp(&cmd_buffer[0], "pwd") == 0:
        cmd_pwd(idx)
    elif cmd_starts_with("write"):
        cmd_write(idx)
    elif cmd_starts_with("uname"):
        cmd_uname(idx)
    elif strcmp(&cmd_buffer[0], "free") == 0:
        cmd_free(idx)
    elif strcmp(&cmd_buffer[0], "whoami") == 0:
        term_puts_idx(idx, "\nroot\n")
    elif strcmp(&cmd_buffer[0], "hostname") == 0:
        term_puts_idx(idx, "\npynux\n")
    elif strcmp(&cmd_buffer[0], "date") == 0:
        term_puts_idx(idx, "\nJan 1 00:00:00 UTC 2025\n")
    elif strcmp(&cmd_buffer[0], "uptime") == 0:
        term_puts_idx(idx, "\nup 0 days, 0:00\n")
    elif strcmp(&cmd_buffer[0], "id") == 0:
        term_puts_idx(idx, "\nuid=0(root) gid=0(root)\n")
    elif strcmp(&cmd_buffer[0], "env") == 0:
        term_puts_idx(idx, "\nHOME=/home\nUSER=root\nSHELL=/bin/psh\n")
    elif strcmp(&cmd_buffer[0], "ps") == 0:
        term_puts_idx(idx, "\n  PID CMD\n    1 psh\n")
    elif strcmp(&cmd_buffer[0], "df") == 0:
        term_puts_idx(idx, "\nFilesystem  Used  Free\nramfs       ")
        term_puts_idx(idx, int_to_str(heap_used() / 1024))
        term_puts_idx(idx, "K   ")
        term_puts_idx(idx, int_to_str(heap_remaining() / 1024))
        term_puts_idx(idx, "K\n")
    elif cmd_starts_with("stat"):
        cmd_stat(idx)
    else:
        term_puts_idx(idx, "\nUnknown: ")
        term_puts_idx(idx, &cmd_buffer[0])
        term_putc_idx(idx, '\n')
    term_newline(idx)
    term_print_prompt(idx)
    cmd_pos = 0

# ============================================================================
# Editor functions
# ============================================================================

def edit_init():
    global edit_size, edit_cursor, edit_scroll, edit_modified
    edit_size = 0
    edit_cursor = 0
    edit_scroll = 0
    edit_modified = False
    edit_filename[0] = '\0'
    i: int32 = 0
    while i < 4096:
        edit_buffer[i] = '\0'
        i = i + 1

def edit_load(path: Ptr[char]):
    global edit_size, edit_cursor, edit_scroll, edit_modified
    edit_init()
    if ramfs_exists(path) and not ramfs_isdir(path):
        sz: int32 = ramfs_read(path, cast[Ptr[uint8]](&edit_buffer[0]), 4095)
        if sz > 0:
            edit_size = sz
        strcpy(&edit_filename[0], path)
    edit_modified = False

def edit_save():
    global edit_modified
    if edit_filename[0] == '\0':
        return
    edit_buffer[edit_size] = '\0'
    if not ramfs_exists(&edit_filename[0]):
        ramfs_create(&edit_filename[0], False)
    ramfs_write(&edit_filename[0], &edit_buffer[0])
    edit_modified = False

def edit_insert(c: char):
    global edit_size, edit_cursor, edit_modified, edit_dirty
    if edit_size >= 4095:
        return
    # Shift right
    i: int32 = edit_size
    while i > edit_cursor:
        edit_buffer[i] = edit_buffer[i - 1]
        i = i - 1
    edit_buffer[edit_cursor] = c
    edit_cursor = edit_cursor + 1
    edit_size = edit_size + 1
    edit_modified = True
    edit_dirty = True

def edit_delete():
    global edit_size, edit_cursor, edit_modified, edit_dirty
    if edit_cursor >= edit_size:
        return
    i: int32 = edit_cursor
    while i < edit_size - 1:
        edit_buffer[i] = edit_buffer[i + 1]
        i = i + 1
    edit_size = edit_size - 1
    edit_modified = True
    edit_dirty = True

def edit_backspace():
    global edit_cursor, edit_dirty
    if edit_cursor <= 0:
        return
    edit_cursor = edit_cursor - 1
    edit_delete()
    edit_dirty = True

# ============================================================================
# File manager functions
# ============================================================================

def fm_init():
    global fm_selection, fm_count
    fm_cwd[0] = '/'
    fm_cwd[1] = '\0'
    fm_selection = 0
    fm_count = 0

def fm_refresh():
    global fm_count, fm_dirty
    fm_count = 0
    i: int32 = 0
    name: Array[64, char]
    result: int32 = ramfs_readdir(&fm_cwd[0], i, &name[0])
    while result >= 0 and fm_count < 16:
        # Store name
        j: int32 = 0
        base: int32 = fm_count * 32
        while j < 31 and name[j] != '\0':
            fm_names[base + j] = name[j]
            j = j + 1
        fm_names[base + j] = '\0'
        fm_types[fm_count] = result
        fm_count = fm_count + 1
        i = i + 1
        result = ramfs_readdir(&fm_cwd[0], i, &name[0])
    fm_dirty = True

def fm_get_name(idx: int32) -> Ptr[char]:
    return &fm_names[idx * 32]

def fm_enter():
    global fm_selection, fm_dirty
    if fm_count == 0:
        return
    name: Ptr[char] = fm_get_name(fm_selection)
    if fm_types[fm_selection] == 1:
        # Directory
        build_path(&fm_cwd[0], name)
        strcpy(&fm_cwd[0], &path_buf[0])
        fm_selection = 0
        fm_refresh()
    else:
        # File - open in editor
        build_path(&fm_cwd[0], name)
        edit_load(&path_buf[0])
        # Find editor window and focus it
        i: int32 = 0
        while i < win_count:
            if win_type[i] == WIN_EDITOR:
                win_focus(i)
                break
            i = i + 1
    fm_dirty = True

def fm_up():
    global fm_selection, fm_dirty
    # Go up one directory
    clen: int32 = strlen(&fm_cwd[0])
    if clen > 1:
        i: int32 = clen - 1
        while i > 0 and fm_cwd[i] != '/':
            i = i - 1
        if i == 0:
            fm_cwd[0] = '/'
            fm_cwd[1] = '\0'
        else:
            fm_cwd[i] = '\0'
        fm_selection = 0
        fm_refresh()
    fm_dirty = True

# ============================================================================
# Drawing functions
# ============================================================================

def draw_menu():
    # Menu bar background
    vtn_rect(0, 0, SCREEN_W, MENU_H, MENU_BG_R, MENU_BG_G, MENU_BG_B, 255)
    # Menu items
    vtn_textline("Menu", 8, 4, TEXT_R, TEXT_G, TEXT_B)
    # Draw dropdown if open
    if menu_open:
        vtn_rect(0, MENU_H, 120, MENU_ITEMS * 20 + 4, TITLE_R, TITLE_G, TITLE_B, 255)
        # Highlight selection
        vtn_rect(2, MENU_H + 2 + menu_selection * 20, 116, 18, SELECT_R, SELECT_G, SELECT_B, 255)
        vtn_textline("Terminal", 8, MENU_H + 4, TEXT_R, TEXT_G, TEXT_B)
        vtn_textline("Editor", 8, MENU_H + 24, TEXT_R, TEXT_G, TEXT_B)
        vtn_textline("Files", 8, MENU_H + 44, TEXT_R, TEXT_G, TEXT_B)
        vtn_textline("Close Win", 8, MENU_H + 64, TEXT_R, TEXT_G, TEXT_B)

def draw_status():
    y: int32 = SCREEN_H - STATUS_H
    vtn_rect(0, y, SCREEN_W, STATUS_H, MENU_BG_R, MENU_BG_G, MENU_BG_B, 255)
    strcpy(&status_buf[0], "Heap: ")
    strcat(&status_buf[0], int_to_str(heap_used()))
    strcat(&status_buf[0], "/")
    strcat(&status_buf[0], int_to_str(heap_total()))
    strcat(&status_buf[0], " | Win: ")
    strcat(&status_buf[0], int_to_str(win_count))
    strcat(&status_buf[0], " | F1:Menu F2:Switch")
    vtn_textline(&status_buf[0], 8, y + 3, TEXT_R, TEXT_G, TEXT_B)

def draw_window_frame(idx: int32):
    x: int32 = win_x[idx]
    y: int32 = win_y[idx]
    w: int32 = win_w[idx]
    h: int32 = win_h[idx]
    is_active: bool = idx == active_win
    # Title bar
    if is_active:
        vtn_rect(x, y, w, WIN_TITLE_H, ACCENT_R, ACCENT_G, ACCENT_B, 255)
    else:
        vtn_rect(x, y, w, WIN_TITLE_H, TITLE_R, TITLE_G, TITLE_B, 255)
    # Title text
    if win_type[idx] == WIN_TERMINAL:
        strcpy(&line_buf[0], "Terminal ")
        strcat(&line_buf[0], int_to_str(idx + 1))
    elif win_type[idx] == WIN_EDITOR:
        strcpy(&line_buf[0], "Editor")
        if edit_modified:
            strcat(&line_buf[0], " *")
    elif win_type[idx] == WIN_FILES:
        strcpy(&line_buf[0], "Files: ")
        strcat(&line_buf[0], &fm_cwd[0])
    else:
        strcpy(&line_buf[0], "Window")
    vtn_textline(&line_buf[0], x + 4, y + 3, TEXT_R, TEXT_G, TEXT_B)
    # Content area background
    vtn_rect(x, y + WIN_TITLE_H, w, h - WIN_TITLE_H, TERM_BG_R, TERM_BG_G, TERM_BG_B, 255)

def draw_terminal_content(idx: int32):
    x: int32 = win_x[idx] + 4
    y: int32 = win_y[idx] + WIN_TITLE_H + 2
    scr: int32 = term_scroll[idx]
    dirty: Ptr[bool] = term_get_dirty(idx)
    row: int32 = 0
    while row < TERM_ROWS:
        line: int32 = scr + row
        if dirty[line]:
            ptr: Ptr[char] = term_line_ptr(idx, line)
            # Clear line
            vtn_clear_rect(x, y + row * CHAR_H, win_w[idx] - 8, CHAR_H, TERM_BG_R, TERM_BG_G, TERM_BG_B)
            # Copy to buffer and null-terminate
            j: int32 = 0
            while j < TERM_COLS:
                line_buf[j] = ptr[j]
                j = j + 1
            line_buf[TERM_COLS] = '\0'
            vtn_textline(&line_buf[0], x, y + row * CHAR_H, TEXT_R, TEXT_G, TEXT_B)
            dirty[line] = False
        row = row + 1
    # Draw cursor if active
    if idx == active_win:
        cx: int32 = x + term_cursor_x[idx] * CHAR_W
        cy: int32 = y + term_cursor_y[idx] * CHAR_H + CHAR_H - 2
        vtn_rect(cx, cy, CHAR_W, 2, TEXT_R, TEXT_G, TEXT_B, 255)

def draw_editor_content(idx: int32):
    x: int32 = win_x[idx] + 4
    y: int32 = win_y[idx] + WIN_TITLE_H + 2
    rows: int32 = (win_h[idx] - WIN_TITLE_H - 4) / CHAR_H
    cols: int32 = (win_w[idx] - 8) / CHAR_W
    # Count lines and find scroll
    row: int32 = 0
    pos: int32 = 0
    cur_row: int32 = 0
    cur_col: int32 = 0
    # Find cursor position
    i: int32 = 0
    lc: int32 = 0
    cc: int32 = 0
    while i < edit_cursor and i < edit_size:
        if edit_buffer[i] == '\n':
            lc = lc + 1
            cc = 0
        else:
            cc = cc + 1
        i = i + 1
    cur_row = lc
    cur_col = cc
    # Adjust scroll
    if cur_row < edit_scroll:
        edit_scroll = cur_row
    if cur_row >= edit_scroll + rows:
        edit_scroll = cur_row - rows + 1
    # Draw lines
    row = 0
    pos = 0
    # Skip to scroll position
    sl: int32 = 0
    while sl < edit_scroll and pos < edit_size:
        if edit_buffer[pos] == '\n':
            sl = sl + 1
        pos = pos + 1
    # Draw visible lines
    while row < rows and pos <= edit_size:
        col: int32 = 0
        while col < cols and pos < edit_size:
            if edit_buffer[pos] == '\n':
                pos = pos + 1
                break
            line_buf[col] = edit_buffer[pos]
            col = col + 1
            pos = pos + 1
        line_buf[col] = '\0'
        vtn_clear_rect(x, y + row * CHAR_H, win_w[idx] - 8, CHAR_H, TERM_BG_R, TERM_BG_G, TERM_BG_B)
        vtn_textline(&line_buf[0], x, y + row * CHAR_H, TEXT_R, TEXT_G, TEXT_B)
        row = row + 1
    # Clear remaining rows
    while row < rows:
        vtn_clear_rect(x, y + row * CHAR_H, win_w[idx] - 8, CHAR_H, TERM_BG_R, TERM_BG_G, TERM_BG_B)
        row = row + 1
    # Draw cursor
    if idx == active_win:
        vr: int32 = cur_row - edit_scroll
        if vr >= 0 and vr < rows:
            cx: int32 = x + cur_col * CHAR_W
            cy: int32 = y + vr * CHAR_H + CHAR_H - 2
            vtn_rect(cx, cy, CHAR_W, 2, ACCENT_R, ACCENT_G, ACCENT_B, 255)

def draw_files_content(idx: int32):
    x: int32 = win_x[idx] + 4
    y: int32 = win_y[idx] + WIN_TITLE_H + 2
    rows: int32 = (win_h[idx] - WIN_TITLE_H - 4) / CHAR_H
    # Draw ".." first
    if fm_selection == 0:
        vtn_rect(x - 2, y, win_w[idx] - 4, CHAR_H, SELECT_R, SELECT_G, SELECT_B, 255)
    vtn_textline("..", x, y, TEXT_R, TEXT_G, TEXT_B)
    # Draw entries
    row: int32 = 1
    i: int32 = 0
    while i < fm_count and row < rows:
        yy: int32 = y + row * CHAR_H
        if i + 1 == fm_selection:
            vtn_rect(x - 2, yy, win_w[idx] - 4, CHAR_H, SELECT_R, SELECT_G, SELECT_B, 255)
        name: Ptr[char] = fm_get_name(i)
        strcpy(&line_buf[0], name)
        if fm_types[i] == 1:
            strcat(&line_buf[0], "/")
        vtn_textline(&line_buf[0], x, yy, TEXT_R, TEXT_G, TEXT_B)
        row = row + 1
        i = i + 1

def draw_window(idx: int32):
    draw_window_frame(idx)
    if win_type[idx] == WIN_TERMINAL:
        draw_terminal_content(idx)
    elif win_type[idx] == WIN_EDITOR:
        draw_editor_content(idx)
    elif win_type[idx] == WIN_FILES:
        draw_files_content(idx)
    win_dirty[idx] = False

def mark_term_dirty(idx: int32):
    """Mark all visible terminal lines as dirty."""
    if win_type[idx] != WIN_TERMINAL:
        return
    dirty: Ptr[bool] = term_get_dirty(idx)
    scr: int32 = term_scroll[idx]
    i: int32 = 0
    while i < TERM_ROWS:
        dirty[scr + i] = True
        i = i + 1

def de_draw():
    global needs_full_redraw, menu_dirty, status_dirty
    if needs_full_redraw:
        vtn_clear(BG_R, BG_G, BG_B, 255)
        draw_menu()
        draw_status()
        # Mark all terminal windows dirty before drawing
        i: int32 = 0
        while i < win_count:
            if win_visible[i] and win_type[i] == WIN_TERMINAL:
                mark_term_dirty(i)
            i = i + 1
        # Now draw all windows
        i = 0
        while i < win_count:
            if win_visible[i]:
                draw_window(i)
            i = i + 1
        needs_full_redraw = False
        menu_dirty = False
        status_dirty = False
        return
    # Partial updates
    if menu_dirty:
        draw_menu()
        menu_dirty = False
    if status_dirty:
        draw_status()
        status_dirty = False
    # Update dirty windows
    i: int32 = 0
    while i < win_count:
        if win_dirty[i] and win_visible[i]:
            # For terminals, ensure all visible lines are marked dirty
            if win_type[i] == WIN_TERMINAL:
                mark_term_dirty(i)
            draw_window(i)
        i = i + 1

# ============================================================================
# Input handling
# ============================================================================

def handle_menu_input(c: char) -> bool:
    global menu_open, menu_selection, menu_dirty, needs_full_redraw
    if c == '\x1b':  # ESC - close menu
        menu_open = False
        needs_full_redraw = True
        return True
    if c == 'j' or c == '\x02':  # Down
        menu_selection = (menu_selection + 1) % MENU_ITEMS
        menu_dirty = True
        return True
    if c == 'k' or c == '\x10':  # Up
        menu_selection = (menu_selection - 1 + MENU_ITEMS) % MENU_ITEMS
        menu_dirty = True
        return True
    if c == '\r':  # Enter - select
        menu_open = False
        if menu_selection == 0:
            # New terminal
            if win_count < 2:  # Limit terminals
                idx: int32 = win_create(WIN_TERMINAL, 10 + win_count * 30, 40 + win_count * 20, 380, 360)
                if idx >= 0:
                    term_init_win(idx)
                    term_puts_idx(idx, "Pynux Terminal\n\n")
                    term_print_prompt(idx)
        elif menu_selection == 1:
            # Editor
            found: bool = False
            i: int32 = 0
            while i < win_count:
                if win_type[i] == WIN_EDITOR:
                    win_focus(i)
                    found = True
                    break
                i = i + 1
            if not found:
                idx: int32 = win_create(WIN_EDITOR, 400, 40, 380, 360)
                if idx >= 0:
                    edit_init()
        elif menu_selection == 2:
            # Files
            found = False
            i = 0
            while i < win_count:
                if win_type[i] == WIN_FILES:
                    win_focus(i)
                    found = True
                    break
                i = i + 1
            if not found:
                idx: int32 = win_create(WIN_FILES, 10, 200, 200, 300)
                if idx >= 0:
                    fm_init()
                    fm_refresh()
        elif menu_selection == 3:
            # Close active window
            if active_win >= 0:
                win_close(active_win)
        needs_full_redraw = True
        return True
    return False

def handle_terminal_input(idx: int32, c: char):
    global cmd_pos
    if c == '\r':
        term_putc_idx(idx, '\n')
        term_exec_cmd(idx)
        win_dirty[idx] = True
        return
    if c == '\b' or c == '\x7f':
        if cmd_pos > 0:
            cmd_pos = cmd_pos - 1
            term_putc_idx(idx, '\b')
            term_putc_idx(idx, ' ')
            term_putc_idx(idx, '\b')
        win_dirty[idx] = True
        return
    if c == '\x03':  # Ctrl+C
        term_puts_idx(idx, "^C\n")
        cmd_pos = 0
        term_print_prompt(idx)
        win_dirty[idx] = True
        return
    if cmd_pos < 255:
        cmd_buffer[cmd_pos] = c
        cmd_pos = cmd_pos + 1
        term_putc_idx(idx, c)
        win_dirty[idx] = True

def handle_editor_input(idx: int32, c: char):
    global edit_cursor, edit_dirty
    if c == '\x13':  # Ctrl+S - save
        edit_save()
        win_dirty[idx] = True
        return
    if c == '\b' or c == '\x7f':
        edit_backspace()
        win_dirty[idx] = True
        return
    if c >= ' ' or c == '\n' or c == '\t':
        edit_insert(c)
        win_dirty[idx] = True
        return

def handle_files_input(idx: int32, c: char):
    global fm_selection, fm_dirty
    if c == 'j' or c == '\x02':  # Down
        if fm_selection < fm_count:
            fm_selection = fm_selection + 1
        fm_dirty = True
        win_dirty[idx] = True
        return
    if c == 'k' or c == '\x10':  # Up
        if fm_selection > 0:
            fm_selection = fm_selection - 1
        fm_dirty = True
        win_dirty[idx] = True
        return
    if c == '\r':  # Enter
        if fm_selection == 0:
            fm_up()
        else:
            fm_selection = fm_selection - 1
            fm_enter()
            fm_selection = fm_selection + 1
        win_dirty[idx] = True
        return
    if c == 'u':  # Go up
        fm_up()
        win_dirty[idx] = True

def handle_input(c: char):
    global menu_open, menu_dirty, active_win, needs_full_redraw, status_dirty
    # F1 (ESC O P) or Ctrl+M for menu - simplified to just 'm'
    if c == '\x1b':
        # Start of escape sequence - for now just toggle menu
        menu_open = not menu_open
        menu_dirty = True
        needs_full_redraw = True
        return
    if menu_open:
        if handle_menu_input(c):
            return
    # F2 or Tab to switch windows
    if c == '\t':
        if win_count > 0:
            active_win = (active_win + 1) % win_count
            needs_full_redraw = True
            status_dirty = True
        return
    # Route to active window
    if active_win < 0 or active_win >= win_count:
        return
    wt: int32 = win_type[active_win]
    if wt == WIN_TERMINAL:
        handle_terminal_input(active_win, c)
    elif wt == WIN_EDITOR:
        handle_editor_input(active_win, c)
    elif wt == WIN_FILES:
        handle_files_input(active_win, c)

# ============================================================================
# Main DE loop
# ============================================================================

def de_init():
    global win_count, active_win, needs_full_redraw
    win_count = 0
    active_win = -1
    vtn_init(SCREEN_W, SCREEN_H)
    # Create initial terminal
    idx: int32 = win_create(WIN_TERMINAL, 10, 40, 780, 380)
    if idx >= 0:
        term_init_win(idx)
        term_puts_idx(idx, "Pynux Desktop Environment\n")
        term_puts_idx(idx, "ESC=Menu TAB=Switch Ctrl+S=Save(editor)\n\n")
        term_print_prompt(idx)
    # Create file manager
    fm_idx: int32 = win_create(WIN_FILES, 10, 430, 250, 140)
    if fm_idx >= 0:
        fm_init()
        fm_refresh()
    # Create editor
    ed_idx: int32 = win_create(WIN_EDITOR, 270, 430, 520, 140)
    if ed_idx >= 0:
        edit_init()
    active_win = 0
    needs_full_redraw = True

def de_main():
    global needs_full_redraw, status_dirty
    de_init()
    de_draw()
    vtn_present()
    while True:
        if uart_available():
            c: char = uart_getc()
            handle_input(c)
            status_dirty = True
        if needs_full_redraw or status_dirty or win_dirty[0] or win_dirty[1] or win_dirty[2] or win_dirty[3]:
            de_draw()
            vtn_present()
