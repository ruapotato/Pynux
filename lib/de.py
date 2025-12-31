# Pynux Desktop Environment
#
# GNOME 2/MATE-style graphical desktop over VTNext protocol.
# Features: Top menu bar, bottom taskbar panel, draggable windows

from lib.io import uart_putc, uart_getc, uart_available, print_str, print_int
from lib.io import console_set_mode, console_flush, console_has_output
from lib.vtnext import vtn_init, vtn_clear, vtn_rect, vtn_textline
from lib.vtnext import vtn_clear_rect, vtn_present, vtn_flush
from lib.vtnext import vtn_line, vtn_text, vtn_rect_outline
from lib.string import strcmp, strlen, strcpy, memset, strcat, atoi
from kernel.ramfs import ramfs_readdir, ramfs_create, ramfs_delete
from kernel.ramfs import ramfs_read, ramfs_write, ramfs_exists, ramfs_isdir
from lib.memory import heap_remaining, heap_total, heap_used
from kernel.timer import timer_delay_ms, timer_tick
from programs.hello import hello_main
from programs.main import user_main, user_tick
from programs.calc import calc_main
from programs.clock import clock_main
from programs.hexview import hexview_main
from programs.imgview import imgview_main

# ============================================================================
# Screen and color constants - GNOME 2/MATE style
# ============================================================================

SCREEN_W: int32 = 800
SCREEN_H: int32 = 600

# Panel heights
TOP_PANEL_H: int32 = 28
BOT_PANEL_H: int32 = 32

# Window title bar
WIN_TITLE_H: int32 = 24

# Character dimensions
CHAR_W: int32 = 10
CHAR_H: int32 = 16

# Icon view constants (file browser)
ICON_W: int32 = 48
ICON_H: int32 = 48
CELL_W: int32 = 72
CELL_H: int32 = 68

# Colors - MATE/GNOME 2 inspired
# Panels - dark gray
PANEL_R: int32 = 48
PANEL_G: int32 = 48
PANEL_B: int32 = 48

# Desktop background - nice blue gradient feel
BG_R: int32 = 58
BG_G: int32 = 110
BG_B: int32 = 165

# Window title bar - active
TITLE_ACTIVE_R: int32 = 78
TITLE_ACTIVE_G: int32 = 128
TITLE_ACTIVE_B: int32 = 188

# Window title bar - inactive
TITLE_INACTIVE_R: int32 = 80
TITLE_INACTIVE_G: int32 = 80
TITLE_INACTIVE_B: int32 = 80

# Window content background
WIN_BG_R: int32 = 32
WIN_BG_G: int32 = 32
WIN_BG_B: int32 = 32

# Terminal background - darker
TERM_BG_R: int32 = 24
TERM_BG_G: int32 = 24
TERM_BG_B: int32 = 24

# Text colors
TEXT_R: int32 = 230
TEXT_G: int32 = 230
TEXT_B: int32 = 230

TEXT_DIM_R: int32 = 160
TEXT_DIM_G: int32 = 160
TEXT_DIM_B: int32 = 160

# Selection/highlight
SELECT_R: int32 = 78
SELECT_G: int32 = 128
SELECT_B: int32 = 188

# Taskbar button colors
BTN_R: int32 = 60
BTN_G: int32 = 60
BTN_B: int32 = 60

BTN_ACTIVE_R: int32 = 85
BTN_ACTIVE_G: int32 = 85
BTN_ACTIVE_B: int32 = 85

# ============================================================================
# Window management
# ============================================================================

WIN_NONE: int32 = 0
WIN_TERMINAL: int32 = 1
WIN_EDITOR: int32 = 2
WIN_FILES: int32 = 3

MAX_WINDOWS: int32 = 4

# Window state arrays
win_type: Array[4, int32]
win_x: Array[4, int32]
win_y: Array[4, int32]
win_w: Array[4, int32]
win_h: Array[4, int32]
win_visible: Array[4, bool]
win_dirty: Array[4, bool]
win_title: Array[128, char]  # 4 windows * 32 chars each

active_win: int32 = -1
win_count: int32 = 0

# Menu state
menu_open: bool = False
menu_selection: int32 = 0
MENU_ITEMS: int32 = 5

# Mouse state
mouse_x: int32 = 0
mouse_y: int32 = 0
mouse_down: bool = False
dragging_win: int32 = -1
drag_offset_x: int32 = 0
drag_offset_y: int32 = 0

# Escape sequence parsing
esc_state: int32 = 0
esc_buf: Array[8, int32]
esc_pos: int32 = 0

# Dirty flags
needs_full_redraw: bool = True
panel_dirty: bool = False

# ============================================================================
# Background jobs tracking
# ============================================================================

MAX_JOBS: int32 = 8
job_names: Array[256, char]  # 8 jobs * 32 chars each
job_status: Array[8, int32]  # 0=free, 1=running, 2=done
job_count: int32 = 0
main_job_id: int32 = -1  # Job ID for main.py

JOB_FREE: int32 = 0
JOB_RUNNING: int32 = 1
JOB_DONE: int32 = 2

def job_add(name: Ptr[char]) -> int32:
    """Add a job to tracking. Returns job ID or -1 if full."""
    global job_count
    i: int32 = 0
    while i < MAX_JOBS:
        if job_status[i] == JOB_FREE:
            # Copy name
            base: int32 = i * 32
            j: int32 = 0
            while j < 31 and name[j] != '\0':
                job_names[base + j] = name[j]
                j = j + 1
            job_names[base + j] = '\0'
            job_status[i] = JOB_RUNNING
            job_count = job_count + 1
            return i
        i = i + 1
    return -1

def job_done(jid: int32):
    """Mark a job as done."""
    if jid >= 0 and jid < MAX_JOBS:
        job_status[jid] = JOB_DONE

def job_get_name(jid: int32) -> Ptr[char]:
    return &job_names[jid * 32]

def job_clear_done():
    """Clear all done jobs."""
    global job_count
    i: int32 = 0
    while i < MAX_JOBS:
        if job_status[i] == JOB_DONE:
            job_status[i] = JOB_FREE
            job_count = job_count - 1
        i = i + 1

# ============================================================================
# Terminal state - PER TERMINAL buffers
# ============================================================================

TERM_COLS: int32 = 78
TERM_ROWS: int32 = 24
TERM_SCROLL: int32 = 100

# Terminal text buffers (100 lines * 78 chars = 7800 bytes each)
term_buf0: Array[7800, char]
term_buf1: Array[7800, char]

# Line dirty flags
term_dirty0: Array[100, bool]
term_dirty1: Array[100, bool]

# Terminal scroll/cursor state
term_scroll: Array[4, int32]
term_cursor_x: Array[4, int32]
term_cursor_y: Array[4, int32]

# PER-TERMINAL command buffers (this fixes the bug!)
cmd_buf0: Array[256, char]
cmd_buf1: Array[256, char]
cmd_pos0: int32 = 0
cmd_pos1: int32 = 0

# Per-terminal working directory
term_cwd0: Array[128, char]
term_cwd1: Array[128, char]

# ============================================================================
# Editor state
# ============================================================================

EDIT_BUF_SIZE: int32 = 8192  # 8KB editor buffer
edit_buffer: Array[8192, char]
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
fm_names: Array[1024, char]  # 32 files * 32 chars each
fm_types: Array[32, int32]   # 32 file type entries
fm_dirty: bool = False

# ============================================================================
# Shared buffers
# ============================================================================

path_buf: Array[256, char]
read_buf: Array[512, uint8]
num_buf: Array[16, char]
line_buf: Array[128, char]

# ============================================================================
# User output buffer - for capturing user_main output
# ============================================================================

user_out_buf: Array[512, char]
user_out_pos: int32 = 0
user_out_active: bool = False

def user_print(s: Ptr[char]):
    """User programs call this to print. Captured if in DE mode."""
    global user_out_pos
    if user_out_active:
        # Buffer the output
        i: int32 = 0
        while s[i] != '\0' and user_out_pos < 510:
            user_out_buf[user_out_pos] = s[i]
            user_out_pos = user_out_pos + 1
            i = i + 1
        user_out_buf[user_out_pos] = '\0'
    else:
        # Direct UART output
        print_str(s)

def user_print_flush_to_term(tidx: int32):
    """Flush captured user output to terminal."""
    global user_out_pos
    if user_out_pos > 0:
        i: int32 = 0
        while i < user_out_pos:
            term_putc_idx(tidx, user_out_buf[i])
            i = i + 1
        user_out_pos = 0

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

def get_win_title(idx: int32) -> Ptr[char]:
    return &win_title[idx * 32]

def set_win_title(idx: int32, title: Ptr[char]):
    ptr: Ptr[char] = get_win_title(idx)
    i: int32 = 0
    while i < 31 and title[i] != '\0':
        ptr[i] = title[i]
        i = i + 1
    ptr[i] = '\0'

# ============================================================================
# Window management
# ============================================================================

def win_create(wtype: int32, x: int32, y: int32, w: int32, h: int32) -> int32:
    global win_count, active_win, needs_full_redraw
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
    needs_full_redraw = True
    return idx

def win_close(idx: int32):
    global win_count, active_win, needs_full_redraw
    if idx < 0 or idx >= win_count:
        return
    i: int32 = idx
    while i < win_count - 1:
        win_type[i] = win_type[i + 1]
        win_x[i] = win_x[i + 1]
        win_y[i] = win_y[i + 1]
        win_w[i] = win_w[i + 1]
        win_h[i] = win_h[i + 1]
        win_visible[i] = win_visible[i + 1]
        win_dirty[i] = win_dirty[i + 1]
        # Copy title
        src: Ptr[char] = get_win_title(i + 1)
        set_win_title(i, src)
        i = i + 1
    win_count = win_count - 1
    if active_win >= win_count:
        active_win = win_count - 1
    needs_full_redraw = True

def win_focus(idx: int32):
    global active_win, needs_full_redraw, panel_dirty
    if idx >= 0 and idx < win_count and idx != active_win:
        active_win = idx
        needs_full_redraw = True
        panel_dirty = True

def win_bring_to_top(idx: int32):
    """Move window to top of z-order (end of array) and focus it."""
    global active_win, needs_full_redraw, panel_dirty, win_count
    if idx < 0 or idx >= win_count:
        return
    if idx == win_count - 1:
        # Already on top, just focus
        active_win = idx
        needs_full_redraw = True
        panel_dirty = True
        return
    # Save window data
    save_type: int32 = win_type[idx]
    save_x: int32 = win_x[idx]
    save_y: int32 = win_y[idx]
    save_w: int32 = win_w[idx]
    save_h: int32 = win_h[idx]
    save_visible: bool = win_visible[idx]
    save_dirty: bool = win_dirty[idx]
    # Save title
    save_title: Array[32, char]
    src: Ptr[char] = get_win_title(idx)
    i: int32 = 0
    while i < 31 and src[i] != '\0':
        save_title[i] = src[i]
        i = i + 1
    save_title[i] = '\0'
    # Shift all windows after idx down by one
    i = idx
    while i < win_count - 1:
        win_type[i] = win_type[i + 1]
        win_x[i] = win_x[i + 1]
        win_y[i] = win_y[i + 1]
        win_w[i] = win_w[i + 1]
        win_h[i] = win_h[i + 1]
        win_visible[i] = win_visible[i + 1]
        win_dirty[i] = win_dirty[i + 1]
        # Copy title
        tsrc: Ptr[char] = get_win_title(i + 1)
        set_win_title(i, tsrc)
        i = i + 1
    # Place saved window at end (top of z-order)
    top: int32 = win_count - 1
    win_type[top] = save_type
    win_x[top] = save_x
    win_y[top] = save_y
    win_w[top] = save_w
    win_h[top] = save_h
    win_visible[top] = save_visible
    win_dirty[top] = True
    set_win_title(top, &save_title[0])
    # Focus the now-top window
    active_win = top
    needs_full_redraw = True
    panel_dirty = True

# ============================================================================
# Terminal functions - with per-terminal command buffers
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

def term_get_cmd_buf(idx: int32) -> Ptr[char]:
    if idx == 0:
        return &cmd_buf0[0]
    return &cmd_buf1[0]

def term_get_cmd_pos(idx: int32) -> int32:
    if idx == 0:
        return cmd_pos0
    return cmd_pos1

def term_set_cmd_pos(idx: int32, pos: int32):
    global cmd_pos0, cmd_pos1
    if idx == 0:
        cmd_pos0 = pos
    else:
        cmd_pos1 = pos

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
    term_set_cmd_pos(idx, 0)
    cwd: Ptr[char] = term_get_cwd(idx)
    cwd[0] = '/'
    cwd[1] = '\0'

def term_scroll_up(idx: int32):
    scr: int32 = term_scroll[idx]
    if scr < TERM_SCROLL - TERM_ROWS:
        term_scroll[idx] = scr + 1
    else:
        buf: Ptr[char] = term_get_buf(idx)
        i: int32 = 0
        while i < (TERM_SCROLL - 1) * TERM_COLS:
            buf[i] = buf[i + TERM_COLS]
            i = i + 1
        term_clear_line(idx, TERM_SCROLL - 1)
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
    term_puts_idx(idx, "$ ")

# ============================================================================
# Terminal commands
# ============================================================================

def cmd_get_arg(idx: int32) -> Ptr[char]:
    cmd: Ptr[char] = term_get_cmd_buf(idx)
    i: int32 = 0
    while cmd[i] != '\0' and cmd[i] != ' ':
        i = i + 1
    while cmd[i] == ' ':
        i = i + 1
    return &cmd[i]

def cmd_starts_with(idx: int32, prefix: Ptr[char]) -> bool:
    cmd: Ptr[char] = term_get_cmd_buf(idx)
    i: int32 = 0
    while prefix[i] != '\0':
        if cmd[i] != prefix[i]:
            return False
        i = i + 1
    return cmd[i] == ' ' or cmd[i] == '\0'

def cmd_help(idx: int32):
    term_puts_idx(idx, "\nCommands: help clear ls cd cat mkdir touch rm mv cp\n")
    term_puts_idx(idx, "echo pwd write uname free whoami hostname date uptime\n")
    term_puts_idx(idx, "id env ps df stat head tail wc sleep hello jobs\n")
    term_puts_idx(idx, "true false arch tty groups printenv\n")
    term_puts_idx(idx, "Apps: calc clock hexview imgview\n")

def cmd_ls(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg(idx)
    # Use argument path if provided, otherwise cwd
    list_path: Ptr[char] = cwd
    if arg[0] != '\0':
        if arg[0] == '/':
            # Absolute path
            list_path = arg
        else:
            # Relative path
            build_path(cwd, arg)
            list_path = &path_buf[0]
    term_putc_idx(idx, '\n')
    if not ramfs_exists(list_path):
        term_puts_idx(idx, "No such directory\n")
        return
    if not ramfs_isdir(list_path):
        # It's a file, just show its name
        term_puts_idx(idx, arg)
        term_putc_idx(idx, '\n')
        return
    name: Array[64, char]
    i: int32 = 0
    result: int32 = ramfs_readdir(list_path, i, &name[0])
    while result >= 0:
        term_puts_idx(idx, &name[0])
        if result == 1:
            term_putc_idx(idx, '/')
        term_puts_idx(idx, "  ")
        i = i + 1
        result = ramfs_readdir(list_path, i, &name[0])
    term_putc_idx(idx, '\n')

def cmd_cd(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg(idx)
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
    if ramfs_exists(&path_buf[0]) and ramfs_isdir(&path_buf[0]):
        strcpy(cwd, &path_buf[0])
    else:
        term_puts_idx(idx, "\nNo such directory\n")

def cmd_cat(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg(idx)
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
    arg: Ptr[char] = cmd_get_arg(idx)
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
    arg: Ptr[char] = cmd_get_arg(idx)
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
    arg: Ptr[char] = cmd_get_arg(idx)
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: rm <name>\n")
        return
    build_path(cwd, arg)
    if ramfs_delete(&path_buf[0]) >= 0:
        term_puts_idx(idx, "\nRemoved\n")
    else:
        term_puts_idx(idx, "\nFailed\n")

def cmd_echo(idx: int32):
    arg: Ptr[char] = cmd_get_arg(idx)
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
    arg: Ptr[char] = cmd_get_arg(idx)
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
    arg: Ptr[char] = cmd_get_arg(idx)
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
    arg: Ptr[char] = cmd_get_arg(idx)
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

# Additional Unix commands
def cmd_head(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg(idx)
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: head <file>\n")
        return
    build_path(cwd, arg)
    if not ramfs_exists(&path_buf[0]) or ramfs_isdir(&path_buf[0]):
        term_puts_idx(idx, "\nFile not found\n")
        return
    term_putc_idx(idx, '\n')
    sz: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
    if sz > 0:
        # Show first 10 lines
        lines: int32 = 0
        i: int32 = 0
        while i < sz and lines < 10:
            term_putc_idx(idx, cast[char](read_buf[i]))
            if read_buf[i] == 10:  # newline
                lines = lines + 1
            i = i + 1
    term_putc_idx(idx, '\n')

def cmd_tail(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg(idx)
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: tail <file>\n")
        return
    build_path(cwd, arg)
    if not ramfs_exists(&path_buf[0]) or ramfs_isdir(&path_buf[0]):
        term_puts_idx(idx, "\nFile not found\n")
        return
    term_putc_idx(idx, '\n')
    sz: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
    if sz > 0:
        # Count total lines
        total_lines: int32 = 0
        i: int32 = 0
        while i < sz:
            if read_buf[i] == 10:
                total_lines = total_lines + 1
            i = i + 1
        # Find start of last 10 lines
        start_line: int32 = total_lines - 10
        if start_line < 0:
            start_line = 0
        current_line: int32 = 0
        i = 0
        while i < sz and current_line < start_line:
            if read_buf[i] == 10:
                current_line = current_line + 1
            i = i + 1
        # Print from here
        while i < sz:
            term_putc_idx(idx, cast[char](read_buf[i]))
            i = i + 1
    term_putc_idx(idx, '\n')

def cmd_wc(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg(idx)
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: wc <file>\n")
        return
    build_path(cwd, arg)
    if not ramfs_exists(&path_buf[0]) or ramfs_isdir(&path_buf[0]):
        term_puts_idx(idx, "\nFile not found\n")
        return
    sz: int32 = ramfs_read(&path_buf[0], &read_buf[0], 511)
    lines: int32 = 0
    words: int32 = 0
    in_word: bool = False
    i: int32 = 0
    while i < sz:
        c: int32 = cast[int32](read_buf[i])
        if c == 10:
            lines = lines + 1
        if c == 32 or c == 10 or c == 9:  # space, newline, tab
            if in_word:
                words = words + 1
                in_word = False
        else:
            in_word = True
        i = i + 1
    if in_word:
        words = words + 1
    term_puts_idx(idx, "\n  ")
    term_puts_idx(idx, int_to_str(lines))
    term_puts_idx(idx, "  ")
    term_puts_idx(idx, int_to_str(words))
    term_puts_idx(idx, "  ")
    term_puts_idx(idx, int_to_str(sz))
    term_puts_idx(idx, " ")
    term_puts_idx(idx, arg)
    term_putc_idx(idx, '\n')

def cmd_mv(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg(idx)
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: mv <src> <dest>\n")
        return
    # Parse two arguments
    i: int32 = 0
    while arg[i] != '\0' and arg[i] != ' ':
        i = i + 1
    if arg[i] != ' ':
        term_puts_idx(idx, "\nUsage: mv <src> <dest>\n")
        return
    arg[i] = '\0'
    dest: Ptr[char] = &arg[i + 1]
    # Build source path
    build_path(cwd, arg)
    src_path: Array[256, char]
    strcpy(&src_path[0], &path_buf[0])
    if not ramfs_exists(&src_path[0]):
        term_puts_idx(idx, "\nSource not found\n")
        return
    # Build dest path
    build_path(cwd, dest)
    # Read source content
    sz: int32 = ramfs_read(&src_path[0], &read_buf[0], 511)
    if sz < 0:
        sz = 0
    read_buf[sz] = 0
    # Create destination
    if not ramfs_exists(&path_buf[0]):
        ramfs_create(&path_buf[0], False)
    ramfs_write(&path_buf[0], cast[Ptr[char]](&read_buf[0]))
    # Delete source
    ramfs_delete(&src_path[0])
    term_puts_idx(idx, "\nMoved\n")

def cmd_cp(idx: int32):
    cwd: Ptr[char] = term_get_cwd(idx)
    arg: Ptr[char] = cmd_get_arg(idx)
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: cp <src> <dest>\n")
        return
    # Parse two arguments
    i: int32 = 0
    while arg[i] != '\0' and arg[i] != ' ':
        i = i + 1
    if arg[i] != ' ':
        term_puts_idx(idx, "\nUsage: cp <src> <dest>\n")
        return
    arg[i] = '\0'
    dest: Ptr[char] = &arg[i + 1]
    # Build source path
    build_path(cwd, arg)
    src_path: Array[256, char]
    strcpy(&src_path[0], &path_buf[0])
    if not ramfs_exists(&src_path[0]):
        term_puts_idx(idx, "\nSource not found\n")
        return
    # Build dest path
    build_path(cwd, dest)
    # Read source content
    sz: int32 = ramfs_read(&src_path[0], &read_buf[0], 511)
    if sz < 0:
        sz = 0
    read_buf[sz] = 0
    # Create destination
    if not ramfs_exists(&path_buf[0]):
        ramfs_create(&path_buf[0], False)
    ramfs_write(&path_buf[0], cast[Ptr[char]](&read_buf[0]))
    term_puts_idx(idx, "\nCopied\n")

def cmd_sleep(idx: int32):
    arg: Ptr[char] = cmd_get_arg(idx)
    if arg[0] == '\0':
        term_puts_idx(idx, "\nUsage: sleep <seconds>\n")
        return
    secs: int32 = atoi(arg)
    if secs > 0 and secs < 60:
        timer_delay_ms(secs * 1000)
    term_putc_idx(idx, '\n')

def cmd_true(idx: int32):
    pass  # Does nothing, returns success

def cmd_false(idx: int32):
    term_puts_idx(idx, "\n")  # Just output newline

def cmd_jobs(idx: int32):
    """List background jobs."""
    term_puts_idx(idx, "\n")
    found: bool = False
    i: int32 = 0
    while i < MAX_JOBS:
        if job_status[i] != JOB_FREE:
            found = True
            term_puts_idx(idx, "[")
            term_puts_idx(idx, int_to_str(i + 1))
            term_puts_idx(idx, "] ")
            if job_status[i] == JOB_RUNNING:
                term_puts_idx(idx, "Running  ")
            else:
                term_puts_idx(idx, "Done     ")
            term_puts_idx(idx, job_get_name(i))
            term_putc_idx(idx, '\n')
        i = i + 1
    if not found:
        term_puts_idx(idx, "No jobs\n")
    # Clear done jobs after display
    job_clear_done()

# ============================================================================
# Terminal command execution
# ============================================================================

def term_exec_cmd(idx: int32):
    cmd: Ptr[char] = term_get_cmd_buf(idx)
    pos: int32 = term_get_cmd_pos(idx)
    cmd[pos] = '\0'
    if pos == 0:
        term_print_prompt(idx)
        return
    # Dispatch - jobs first to avoid branch distance issues
    if strcmp(cmd, "jobs") == 0:
        cmd_jobs(idx)
    elif strcmp(cmd, "help") == 0:
        cmd_help(idx)
    elif strcmp(cmd, "clear") == 0:
        term_init_win(idx)
        win_dirty[idx] = True
    elif cmd_starts_with(idx, "ls"):
        cmd_ls(idx)
    elif cmd_starts_with(idx, "cd"):
        cmd_cd(idx)
    elif cmd_starts_with(idx, "cat"):
        cmd_cat(idx)
    elif cmd_starts_with(idx, "mkdir"):
        cmd_mkdir(idx)
    elif cmd_starts_with(idx, "touch"):
        cmd_touch(idx)
    elif cmd_starts_with(idx, "rm"):
        cmd_rm(idx)
    elif cmd_starts_with(idx, "echo"):
        cmd_echo(idx)
    elif strcmp(cmd, "pwd") == 0:
        cmd_pwd(idx)
    elif cmd_starts_with(idx, "write"):
        cmd_write(idx)
    elif cmd_starts_with(idx, "uname"):
        cmd_uname(idx)
    elif strcmp(cmd, "free") == 0:
        cmd_free(idx)
    elif strcmp(cmd, "whoami") == 0:
        term_puts_idx(idx, "\nroot\n")
    elif strcmp(cmd, "hostname") == 0:
        term_puts_idx(idx, "\npynux\n")
    elif strcmp(cmd, "date") == 0:
        term_puts_idx(idx, "\nJan 1 00:00:00 UTC 2025\n")
    elif strcmp(cmd, "uptime") == 0:
        term_puts_idx(idx, "\nup 0 days, 0:00\n")
    elif strcmp(cmd, "id") == 0:
        term_puts_idx(idx, "\nuid=0(root) gid=0(root)\n")
    elif strcmp(cmd, "env") == 0:
        term_puts_idx(idx, "\nHOME=/home\nUSER=root\nSHELL=/bin/psh\n")
    elif strcmp(cmd, "ps") == 0:
        term_puts_idx(idx, "\n  PID CMD\n    1 psh\n")
    elif strcmp(cmd, "df") == 0:
        term_puts_idx(idx, "\nFilesystem  Used  Free\nramfs       ")
        term_puts_idx(idx, int_to_str(heap_used() / 1024))
        term_puts_idx(idx, "K   ")
        term_puts_idx(idx, int_to_str(heap_remaining() / 1024))
        term_puts_idx(idx, "K\n")
    elif cmd_starts_with(idx, "stat"):
        cmd_stat(idx)
    elif strcmp(cmd, "hello") == 0:
        term_putc_idx(idx, '\n')
        hello_main()
    elif strcmp(cmd, "calc") == 0:
        term_putc_idx(idx, '\n')
        calc_main()
    elif strcmp(cmd, "clock") == 0:
        term_putc_idx(idx, '\n')
        clock_main()
    elif cmd_starts_with(idx, "hexview"):
        hv_arg: Ptr[char] = cmd_get_arg(idx)
        if hv_arg[0] == '\0':
            term_puts_idx(idx, "\nUsage: hexview <file>\n")
        else:
            term_putc_idx(idx, '\n')
            build_path(term_get_cwd(idx), hv_arg)
            hexview_main(&path_buf[0])
    elif cmd_starts_with(idx, "imgview"):
        iv_arg: Ptr[char] = cmd_get_arg(idx)
        if iv_arg[0] == '\0':
            term_puts_idx(idx, "\nUsage: imgview <file.bmp>\n")
        else:
            term_putc_idx(idx, '\n')
            build_path(term_get_cwd(idx), iv_arg)
            imgview_main(&path_buf[0])
    elif cmd_starts_with(idx, "head"):
        cmd_head(idx)
    elif cmd_starts_with(idx, "tail"):
        cmd_tail(idx)
    elif cmd_starts_with(idx, "wc"):
        cmd_wc(idx)
    elif cmd_starts_with(idx, "mv"):
        cmd_mv(idx)
    elif cmd_starts_with(idx, "cp"):
        cmd_cp(idx)
    elif cmd_starts_with(idx, "sleep"):
        cmd_sleep(idx)
    elif strcmp(cmd, "true") == 0:
        cmd_true(idx)
    elif strcmp(cmd, "false") == 0:
        cmd_false(idx)
    elif strcmp(cmd, "arch") == 0:
        term_puts_idx(idx, "\narmv7m\n")
    elif strcmp(cmd, "tty") == 0:
        term_puts_idx(idx, "\n/dev/tty\n")
    elif strcmp(cmd, "yes") == 0:
        term_puts_idx(idx, "\ny\n")
    elif strcmp(cmd, "groups") == 0:
        term_puts_idx(idx, "\nroot wheel\n")
    elif strcmp(cmd, "printenv") == 0:
        term_puts_idx(idx, "\nHOME=/home\nUSER=root\nSHELL=/bin/psh\nPATH=/bin\n")
    else:
        term_puts_idx(idx, "\nCommand not found: ")
        term_puts_idx(idx, cmd)
        term_putc_idx(idx, '\n')
    term_newline(idx)
    term_print_prompt(idx)
    term_set_cmd_pos(idx, 0)

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
    while i < EDIT_BUF_SIZE:
        edit_buffer[i] = '\0'
        i = i + 1

def edit_load(path: Ptr[char]):
    global edit_size, edit_cursor, edit_scroll, edit_modified
    edit_init()
    if ramfs_exists(path) and not ramfs_isdir(path):
        sz: int32 = ramfs_read(path, cast[Ptr[uint8]](&edit_buffer[0]), EDIT_BUF_SIZE - 1)
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
    if edit_size >= EDIT_BUF_SIZE - 1:
        return
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
    while result >= 0 and fm_count < 32:
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
    # Bounds check: max 32 entries
    if idx < 0 or idx >= 32:
        return Ptr[char](0)
    return &fm_names[idx * 32]

def fm_enter():
    global fm_selection, fm_dirty
    if fm_count == 0:
        return
    name: Ptr[char] = fm_get_name(fm_selection)
    if fm_types[fm_selection] == 1:
        build_path(&fm_cwd[0], name)
        strcpy(&fm_cwd[0], &path_buf[0])
        fm_selection = 0
        fm_refresh()
    else:
        build_path(&fm_cwd[0], name)
        edit_load(&path_buf[0])
        i: int32 = 0
        while i < win_count:
            if win_type[i] == WIN_EDITOR:
                win_focus(i)
                break
            i = i + 1
    fm_dirty = True

def fm_up():
    global fm_selection, fm_dirty
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

def handle_files_click(widx: int32, mx: int32, my: int32):
    global fm_selection, fm_dirty, needs_full_redraw
    # Calculate content area (icon grid)
    cx: int32 = win_x[widx] + 8
    cy: int32 = win_y[widx] + WIN_TITLE_H + 8
    content_w: int32 = win_w[widx] - 16
    cols: int32 = content_w / CELL_W
    if cols < 1:
        cols = 1
    # Check if in content area
    if my < cy or mx < cx:
        return
    # Calculate grid position
    rel_x: int32 = mx - cx
    rel_y: int32 = my - cy
    clicked_col: int32 = rel_x / CELL_W
    clicked_row: int32 = rel_y / CELL_H
    # Grid position 0 = "..", position 1+ = files
    grid_idx: int32 = clicked_row * cols + clicked_col
    if grid_idx == 0:
        # Clicked ".."
        fm_selection = 0
        fm_up()
    elif grid_idx <= fm_count:
        fm_selection = grid_idx
        # Enter the item (double-click effect)
        fm_enter()
    fm_dirty = True
    win_dirty[widx] = True
    needs_full_redraw = True

# ============================================================================
# Drawing - GNOME 2/MATE Style
# ============================================================================

def draw_top_panel():
    # Top panel background
    vtn_rect(0, 0, SCREEN_W, TOP_PANEL_H, PANEL_R, PANEL_G, PANEL_B, 255)
    # "Applications" menu button (130px wide to fit text)
    vtn_rect(2, 2, 130, TOP_PANEL_H - 4, BTN_R, BTN_G, BTN_B, 255)
    vtn_textline("Applications", 8, 6, TEXT_R, TEXT_G, TEXT_B)
    # Status on right
    strcpy(&line_buf[0], "Heap: ")
    strcat(&line_buf[0], int_to_str(heap_used() / 1024))
    strcat(&line_buf[0], "K/")
    strcat(&line_buf[0], int_to_str(heap_total() / 1024))
    strcat(&line_buf[0], "K")
    vtn_textline(&line_buf[0], SCREEN_W - 140, 6, TEXT_DIM_R, TEXT_DIM_G, TEXT_DIM_B)

def draw_bottom_panel():
    # Bottom panel background
    y: int32 = SCREEN_H - BOT_PANEL_H
    vtn_rect(0, y, SCREEN_W, BOT_PANEL_H, PANEL_R, PANEL_G, PANEL_B, 255)
    # Draw taskbar buttons for open windows
    bx: int32 = 4
    i: int32 = 0
    while i < win_count:
        bw: int32 = 140
        # Button background - highlight active window
        if i == active_win:
            vtn_rect(bx, y + 4, bw, BOT_PANEL_H - 8, BTN_ACTIVE_R, BTN_ACTIVE_G, BTN_ACTIVE_B, 255)
            vtn_rect_outline(bx, y + 4, bw, BOT_PANEL_H - 8, 1, SELECT_R, SELECT_G, SELECT_B, 255)
        else:
            vtn_rect(bx, y + 4, bw, BOT_PANEL_H - 8, BTN_R, BTN_G, BTN_B, 255)
        # Window icon/type indicator and title
        title: Ptr[char] = get_win_title(i)
        vtn_textline(title, bx + 6, y + 8, TEXT_R, TEXT_G, TEXT_B)
        bx = bx + bw + 4
        i = i + 1

def draw_menu_dropdown():
    if menu_open:
        # Draw below "Applications" button
        mx: int32 = 2
        my: int32 = TOP_PANEL_H
        mw: int32 = 160
        mh: int32 = MENU_ITEMS * 24 + 8
        vtn_rect(mx, my, mw, mh, PANEL_R + 10, PANEL_G + 10, PANEL_B + 10, 255)
        vtn_rect_outline(mx, my, mw, mh, 1, 80, 80, 80, 255)
        # Menu items
        iy: int32 = my + 4
        # Highlight selection
        vtn_rect(mx + 2, iy + menu_selection * 24, mw - 4, 22, SELECT_R, SELECT_G, SELECT_B, 255)
        vtn_textline("Terminal", mx + 8, iy + 4, TEXT_R, TEXT_G, TEXT_B)
        vtn_textline("Text Editor", mx + 8, iy + 28, TEXT_R, TEXT_G, TEXT_B)
        vtn_textline("File Manager", mx + 8, iy + 52, TEXT_R, TEXT_G, TEXT_B)
        vtn_textline("Close Window", mx + 8, iy + 76, TEXT_R, TEXT_G, TEXT_B)
        vtn_textline("About Pynux", mx + 8, iy + 100, TEXT_R, TEXT_G, TEXT_B)

def draw_window_frame(idx: int32):
    x: int32 = win_x[idx]
    y: int32 = win_y[idx]
    w: int32 = win_w[idx]
    h: int32 = win_h[idx]
    is_active: bool = idx == active_win
    # Window shadow
    vtn_rect(x + 3, y + 3, w, h, 20, 20, 20, 255)
    # Window border
    vtn_rect(x - 1, y - 1, w + 2, h + 2, 60, 60, 60, 255)
    # Title bar
    if is_active:
        vtn_rect(x, y, w, WIN_TITLE_H, TITLE_ACTIVE_R, TITLE_ACTIVE_G, TITLE_ACTIVE_B, 255)
    else:
        vtn_rect(x, y, w, WIN_TITLE_H, TITLE_INACTIVE_R, TITLE_INACTIVE_G, TITLE_INACTIVE_B, 255)
    # Title text
    title: Ptr[char] = get_win_title(idx)
    vtn_textline(title, x + 8, y + 4, TEXT_R, TEXT_G, TEXT_B)
    # Close button
    cbx: int32 = x + w - 20
    cby: int32 = y + 4
    vtn_rect(cbx, cby, 16, 16, 180, 60, 60, 255)
    vtn_textline("X", cbx + 4, cby + 1, TEXT_R, TEXT_G, TEXT_B)
    # Content area
    vtn_rect(x, y + WIN_TITLE_H, w, h - WIN_TITLE_H, WIN_BG_R, WIN_BG_G, WIN_BG_B, 255)

def draw_terminal_content(idx: int32):
    x: int32 = win_x[idx] + 4
    y: int32 = win_y[idx] + WIN_TITLE_H + 2
    w: int32 = win_w[idx] - 8
    # Background
    vtn_rect(x - 2, y - 2, w + 4, win_h[idx] - WIN_TITLE_H - 2, TERM_BG_R, TERM_BG_G, TERM_BG_B, 255)
    scr: int32 = term_scroll[idx]
    dirty: Ptr[bool] = term_get_dirty(idx)
    row: int32 = 0
    # Calculate visible rows based on window height
    vis_rows: int32 = (win_h[idx] - WIN_TITLE_H - 8) / CHAR_H
    if vis_rows > TERM_ROWS:
        vis_rows = TERM_ROWS
    while row < vis_rows:
        line: int32 = scr + row
        ptr: Ptr[char] = term_line_ptr(idx, line)
        j: int32 = 0
        while j < TERM_COLS:
            line_buf[j] = ptr[j]
            j = j + 1
        line_buf[TERM_COLS] = '\0'
        vtn_textline(&line_buf[0], x, y + row * CHAR_H, TEXT_R, TEXT_G, TEXT_B)
        dirty[line] = False
        row = row + 1
    # Cursor
    if idx == active_win:
        cx: int32 = x + term_cursor_x[idx] * CHAR_W
        cy: int32 = y + term_cursor_y[idx] * CHAR_H + CHAR_H - 2
        vtn_rect(cx, cy, CHAR_W, 2, 0, 255, 0, 255)

def draw_editor_content(idx: int32):
    x: int32 = win_x[idx] + 4
    y: int32 = win_y[idx] + WIN_TITLE_H + 2
    # Reserve 20px for status bar at bottom
    rows: int32 = (win_h[idx] - WIN_TITLE_H - 28) / CHAR_H
    cols: int32 = (win_w[idx] - 8) / CHAR_W
    # Find cursor row/col
    cur_row: int32 = 0
    cur_col: int32 = 0
    i: int32 = 0
    while i < edit_cursor and i < edit_size:
        if edit_buffer[i] == '\n':
            cur_row = cur_row + 1
            cur_col = 0
        else:
            cur_col = cur_col + 1
        i = i + 1
    # Adjust scroll
    if cur_row < edit_scroll:
        edit_scroll = cur_row
    if cur_row >= edit_scroll + rows:
        edit_scroll = cur_row - rows + 1
    # Skip to scroll
    pos: int32 = 0
    sl: int32 = 0
    while sl < edit_scroll and pos < edit_size:
        if edit_buffer[pos] == '\n':
            sl = sl + 1
        pos = pos + 1
    # Draw lines
    row: int32 = 0
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
        vtn_textline(&line_buf[0], x, y + row * CHAR_H, TEXT_R, TEXT_G, TEXT_B)
        row = row + 1
    # Editor status bar
    sby: int32 = win_y[idx] + win_h[idx] - 18
    vtn_rect(win_x[idx], sby, win_w[idx], 18, 50, 50, 50, 255)
    # Show filename or "(new file)"
    if edit_filename[0] != '\0':
        strcpy(&line_buf[0], &edit_filename[0])
    else:
        strcpy(&line_buf[0], "(new file)")
    if edit_modified:
        strcat(&line_buf[0], " *")
    strcat(&line_buf[0], "  |  Ctrl+S: Save")
    vtn_textline(&line_buf[0], win_x[idx] + 4, sby + 2, TEXT_DIM_R, TEXT_DIM_G, TEXT_DIM_B)
    # Cursor
    if idx == active_win:
        vr: int32 = cur_row - edit_scroll
        if vr >= 0 and vr < rows:
            cx: int32 = x + cur_col * CHAR_W
            cy: int32 = y + vr * CHAR_H + CHAR_H - 2
            vtn_rect(cx, cy, CHAR_W, 2, 0, 255, 0, 255)

def draw_folder_icon_large(ix: int32, iy: int32, selected: bool):
    # Draw selection highlight if selected
    if selected:
        vtn_rect(ix - 4, iy - 2, ICON_W + 8, ICON_H + 4, SELECT_R, SELECT_G, SELECT_B, 255)
    # Folder icon - large version
    # Tab at top
    vtn_rect(ix, iy, 18, 8, 240, 200, 80, 255)
    # Main body
    vtn_rect(ix, iy + 6, ICON_W, 38, 220, 180, 50, 255)
    # Shadow/depth
    vtn_rect(ix + 2, iy + 10, ICON_W - 4, 30, 200, 160, 40, 255)

def draw_file_icon_large(ix: int32, iy: int32, selected: bool):
    # Draw selection highlight if selected
    if selected:
        vtn_rect(ix - 4, iy - 2, ICON_W + 8, ICON_H + 4, SELECT_R, SELECT_G, SELECT_B, 255)
    # File icon - large version
    # Page body
    vtn_rect(ix + 4, iy, 40, ICON_H, 240, 240, 240, 255)
    # Corner fold
    vtn_rect(ix + 34, iy, 10, 10, 200, 200, 200, 255)
    # Lines on page (representing text)
    vtn_rect(ix + 10, iy + 14, 28, 2, 180, 180, 180, 255)
    vtn_rect(ix + 10, iy + 20, 24, 2, 180, 180, 180, 255)
    vtn_rect(ix + 10, iy + 26, 26, 2, 180, 180, 180, 255)
    vtn_rect(ix + 10, iy + 32, 20, 2, 180, 180, 180, 255)

def draw_files_content(idx: int32):
    cx: int32 = win_x[idx] + 8
    cy: int32 = win_y[idx] + WIN_TITLE_H + 8
    content_w: int32 = win_w[idx] - 16
    cols: int32 = content_w / CELL_W
    if cols < 1:
        cols = 1
    # ".." entry (parent folder)
    is_sel: bool = fm_selection == 0
    draw_folder_icon_large(cx + 12, cy, is_sel)
    vtn_textline("..", cx + 24, cy + ICON_H + 2, TEXT_R, TEXT_G, TEXT_B)
    # Entries in grid
    i: int32 = 0
    while i < fm_count:
        grid_pos: int32 = i + 1
        col: int32 = grid_pos % cols
        row: int32 = grid_pos / cols
        ix: int32 = cx + col * CELL_W + 12
        iy: int32 = cy + row * CELL_H
        # Check if still in visible area
        if iy + CELL_H > win_y[idx] + win_h[idx] - 8:
            break
        is_sel = (i + 1) == fm_selection
        # Draw icon based on type
        if fm_types[i] == 1:
            draw_folder_icon_large(ix, iy, is_sel)
        else:
            draw_file_icon_large(ix, iy, is_sel)
        # Draw name (truncate to fit)
        name: Ptr[char] = fm_get_name(i)
        vtn_textline(name, ix - 6, iy + ICON_H + 2, TEXT_R, TEXT_G, TEXT_B)
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

def de_draw():
    global needs_full_redraw, panel_dirty
    if needs_full_redraw:
        vtn_clear(BG_R, BG_G, BG_B, 255)
        draw_top_panel()
        draw_bottom_panel()
        # Draw all windows
        i: int32 = 0
        while i < win_count:
            if win_visible[i]:
                draw_window(i)
            i = i + 1
        # Dropdown on top
        draw_menu_dropdown()
        needs_full_redraw = False
        panel_dirty = False
        return
    # Partial updates
    if panel_dirty:
        draw_top_panel()
        draw_bottom_panel()
        panel_dirty = False
    # Dirty windows
    i: int32 = 0
    while i < win_count:
        if win_dirty[i] and win_visible[i]:
            draw_window(i)
        i = i + 1
    # Dropdown always on top
    if menu_open:
        draw_menu_dropdown()

# ============================================================================
# Mouse and input handling
# ============================================================================

def toggle_menu():
    global menu_open, needs_full_redraw
    menu_open = not menu_open
    needs_full_redraw = True

def point_in_rect(px: int32, py: int32, rx: int32, ry: int32, rw: int32, rh: int32) -> bool:
    return px >= rx and px < rx + rw and py >= ry and py < ry + rh

def find_window_at(mx: int32, my: int32) -> int32:
    i: int32 = win_count - 1
    while i >= 0:
        if win_visible[i]:
            if point_in_rect(mx, my, win_x[i], win_y[i], win_w[i], win_h[i]):
                return i
        i = i - 1
    return -1

def is_on_titlebar(idx: int32, mx: int32, my: int32) -> bool:
    return point_in_rect(mx, my, win_x[idx], win_y[idx], win_w[idx], WIN_TITLE_H)

def is_on_close_button(idx: int32, mx: int32, my: int32) -> bool:
    cbx: int32 = win_x[idx] + win_w[idx] - 20
    cby: int32 = win_y[idx] + 4
    return point_in_rect(mx, my, cbx, cby, 16, 16)

def handle_mouse_down(mx: int32, my: int32):
    global mouse_down, dragging_win, drag_offset_x, drag_offset_y
    global menu_open, menu_selection, needs_full_redraw, active_win
    mouse_down = True
    # Check Applications button (130px wide)
    if point_in_rect(mx, my, 2, 2, 130, TOP_PANEL_H - 4):
        toggle_menu()
        return
    # Check menu dropdown
    if menu_open:
        dmx: int32 = 2
        dmy: int32 = TOP_PANEL_H
        dmw: int32 = 160
        dmh: int32 = MENU_ITEMS * 24 + 8
        if point_in_rect(mx, my, dmx, dmy, dmw, dmh):
            sel: int32 = (my - dmy - 4) / 24
            if sel >= 0 and sel < MENU_ITEMS:
                menu_selection = sel
                execute_menu_action()
            return
        else:
            menu_open = False
            needs_full_redraw = True
    # Check taskbar
    ty: int32 = SCREEN_H - BOT_PANEL_H
    if point_in_rect(mx, my, 0, ty, SCREEN_W, BOT_PANEL_H):
        # Find which button
        bx: int32 = 4
        i: int32 = 0
        while i < win_count:
            if point_in_rect(mx, my, bx, ty + 4, 140, BOT_PANEL_H - 8):
                win_bring_to_top(i)
                return
            bx = bx + 144
            i = i + 1
        return
    # Check windows
    widx: int32 = find_window_at(mx, my)
    if widx >= 0:
        if widx != active_win:
            win_bring_to_top(widx)
        # Close button?
        if is_on_close_button(widx, mx, my):
            win_close(widx)
            return
        # Title bar drag
        if is_on_titlebar(widx, mx, my):
            dragging_win = widx
            drag_offset_x = mx - win_x[widx]
            drag_offset_y = my - win_y[widx]
            return
        # File browser content click
        if win_type[widx] == WIN_FILES:
            handle_files_click(widx, mx, my)

def handle_mouse_up(mx: int32, my: int32):
    global mouse_down, dragging_win
    mouse_down = False
    dragging_win = -1

def handle_mouse_drag(mx: int32, my: int32):
    global needs_full_redraw
    if dragging_win >= 0:
        new_x: int32 = mx - drag_offset_x
        new_y: int32 = my - drag_offset_y
        if new_x < 0:
            new_x = 0
        if new_y < TOP_PANEL_H:
            new_y = TOP_PANEL_H
        if new_x + win_w[dragging_win] > SCREEN_W:
            new_x = SCREEN_W - win_w[dragging_win]
        if new_y + win_h[dragging_win] > SCREEN_H - BOT_PANEL_H:
            new_y = SCREEN_H - BOT_PANEL_H - win_h[dragging_win]
        win_x[dragging_win] = new_x
        win_y[dragging_win] = new_y
        needs_full_redraw = True

def execute_menu_action():
    global menu_open, needs_full_redraw
    menu_open = False
    if menu_selection == 0:
        # New terminal
        if win_count < MAX_WINDOWS:
            term_idx: int32 = 0
            if win_count > 0 and win_type[0] == WIN_TERMINAL:
                term_idx = 1
            idx: int32 = win_create(WIN_TERMINAL, 50 + win_count * 30, TOP_PANEL_H + 20 + win_count * 20, 700, 420)
            if idx >= 0:
                set_win_title(idx, "Terminal")
                term_init_win(term_idx)
                term_puts_idx(term_idx, "Pynux Terminal\n")
                term_puts_idx(term_idx, "Type 'help' for commands\n\n")
                term_print_prompt(term_idx)
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
            idx: int32 = win_create(WIN_EDITOR, 100, TOP_PANEL_H + 50, 600, 400)
            if idx >= 0:
                set_win_title(idx, "Text Editor")
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
            idx: int32 = win_create(WIN_FILES, 50, TOP_PANEL_H + 30, 300, 400)
            if idx >= 0:
                set_win_title(idx, "Files")
                fm_init()
                fm_refresh()
    elif menu_selection == 3:
        # Close window
        if active_win >= 0:
            win_close(active_win)
    elif menu_selection == 4:
        # About
        # Show in terminal if one exists
        i = 0
        while i < win_count:
            if win_type[i] == WIN_TERMINAL:
                term_puts_idx(i, "\n=== Pynux 0.1.0 ===\n")
                term_puts_idx(i, "Python-syntax OS for ARM\n")
                term_puts_idx(i, "GNOME 2/MATE style DE\n\n")
                win_dirty[i] = True
                break
            i = i + 1
    needs_full_redraw = True

def parse_mouse_escape(c: char) -> int32:
    global esc_state, esc_pos, mouse_x, mouse_y
    cv: int32 = cast[int32](c)
    if esc_state == 0:
        if cv == 27:
            esc_state = 1
            return 1
        return 0
    if esc_state == 1:
        if c == '[':
            esc_state = 2
            esc_pos = 0
            return 1
        if cv == 27:
            esc_state = 0
            toggle_menu()
            return 1
        esc_state = 0
        return 2
    if esc_state == 2:
        if c == 'M':
            esc_state = 3
            return 1
        esc_state = 0
        return 0
    if esc_state == 3:
        esc_buf[0] = cv - 32
        esc_state = 4
        return 1
    if esc_state == 4:
        esc_buf[1] = (cv - 33) * CHAR_W  # X uses character width (10)
        esc_state = 5
        return 1
    if esc_state == 5:
        esc_buf[2] = (cv - 33) * CHAR_H  # Y uses character height (16)
        esc_state = 0
        mx: int32 = esc_buf[1]
        my: int32 = esc_buf[2]
        mtype: int32 = esc_buf[0]
        mouse_x = mx
        mouse_y = my
        if mtype == 0:
            handle_mouse_down(mx, my)
        elif mtype == 1:
            handle_mouse_up(mx, my)
        elif mtype == 2:
            handle_mouse_drag(mx, my)
        return 1
    esc_state = 0
    return 0

def handle_menu_input(c: char) -> bool:
    global menu_open, menu_selection, needs_full_redraw
    cv: int32 = cast[int32](c)
    if cv == 27:
        menu_open = False
        needs_full_redraw = True
        return True
    if c == 'j' or cv == 2:
        menu_selection = (menu_selection + 1) % MENU_ITEMS
        needs_full_redraw = True
        return True
    if c == 'k' or cv == 16:
        menu_selection = (menu_selection - 1 + MENU_ITEMS) % MENU_ITEMS
        needs_full_redraw = True
        return True
    if c == '\r':
        execute_menu_action()
        return True
    return False

def handle_terminal_input(idx: int32, c: char):
    cv: int32 = cast[int32](c)
    cmd: Ptr[char] = term_get_cmd_buf(idx)
    pos: int32 = term_get_cmd_pos(idx)
    if c == '\r' or c == '\n':
        term_putc_idx(idx, '\n')
        term_exec_cmd(idx)
        win_dirty[idx] = True
        return
    if cv == 8 or cv == 127:
        if pos > 0:
            term_set_cmd_pos(idx, pos - 1)
            cx: int32 = term_cursor_x[idx]
            if cx > 0:
                term_cursor_x[idx] = cx - 1
                line: int32 = term_scroll[idx] + term_cursor_y[idx]
                ptr: Ptr[char] = term_line_ptr(idx, line)
                ptr[term_cursor_x[idx]] = ' '
                dirty: Ptr[bool] = term_get_dirty(idx)
                dirty[line] = True
        win_dirty[idx] = True
        return
    if cv == 3:  # Ctrl+C
        term_puts_idx(idx, "^C\n")
        term_set_cmd_pos(idx, 0)
        term_print_prompt(idx)
        win_dirty[idx] = True
        return
    if pos < 255:
        cmd[pos] = c
        term_set_cmd_pos(idx, pos + 1)
        term_putc_idx(idx, c)
        win_dirty[idx] = True

def handle_editor_input(idx: int32, c: char):
    global edit_cursor, edit_dirty
    cv: int32 = cast[int32](c)
    if cv == 19:  # Ctrl+S
        edit_save()
        win_dirty[idx] = True
        return
    if cv == 8 or cv == 127:
        edit_backspace()
        win_dirty[idx] = True
        return
    # Enter key: \r (13) -> insert \n
    if c == '\r':
        edit_insert('\n')
        win_dirty[idx] = True
        return
    if cv >= 32 or c == '\n' or c == '\t':
        edit_insert(c)
        win_dirty[idx] = True

def handle_files_input(idx: int32, c: char):
    global fm_selection, fm_dirty
    cv: int32 = cast[int32](c)
    if c == 'j' or cv == 2:
        if fm_selection < fm_count:
            fm_selection = fm_selection + 1
        fm_dirty = True
        win_dirty[idx] = True
        return
    if c == 'k' or cv == 16:
        if fm_selection > 0:
            fm_selection = fm_selection - 1
        fm_dirty = True
        win_dirty[idx] = True
        return
    if c == '\r':
        if fm_selection == 0:
            fm_up()
        else:
            fm_selection = fm_selection - 1
            fm_enter()
            fm_selection = fm_selection + 1
        win_dirty[idx] = True

def handle_input(c: char):
    global menu_open, active_win, needs_full_redraw, panel_dirty, esc_state
    result: int32 = parse_mouse_escape(c)
    if result == 1:
        return
    if result == 2:
        toggle_menu()
        result = parse_mouse_escape(c)
        if result == 1:
            return
    if menu_open:
        if handle_menu_input(c):
            return
    if c == '\t':
        if win_count > 0:
            active_win = (active_win + 1) % win_count
            needs_full_redraw = True
            panel_dirty = True
        return
    if active_win < 0 or active_win >= win_count:
        return
    wt: int32 = win_type[active_win]
    if wt == WIN_TERMINAL:
        # Map active_win to terminal index (0 or 1)
        tidx: int32 = 0
        if active_win > 0:
            # Count terminals before this window
            i: int32 = 0
            while i < active_win:
                if win_type[i] == WIN_TERMINAL:
                    tidx = tidx + 1
                i = i + 1
        handle_terminal_input(tidx, c)
    elif wt == WIN_EDITOR:
        handle_editor_input(active_win, c)
    elif wt == WIN_FILES:
        handle_files_input(active_win, c)

# ============================================================================
# Main
# ============================================================================

def de_init():
    global win_count, active_win, needs_full_redraw, user_out_active
    win_count = 0
    active_win = -1
    vtn_init(SCREEN_W, SCREEN_H)
    # Create initial terminal - big and centered
    idx: int32 = win_create(WIN_TERMINAL, 40, TOP_PANEL_H + 10, 720, 480)
    if idx >= 0:
        set_win_title(idx, "Terminal")
        term_init_win(0)
        term_puts_idx(0, "Welcome to Pynux!\n")
        term_puts_idx(0, "GNOME 2/MATE-style Desktop Environment\n\n")
        # Run user main.py startup (user_tick runs in main loop)
        # Register main.py as a background job
        global main_job_id
        main_job_id = job_add("main.py")
        term_puts_idx(0, "[")
        term_puts_idx(0, int_to_str(main_job_id + 1))
        term_puts_idx(0, "] main.py &\n")
        # Set console to buffered mode for DE
        console_set_mode(1)
        user_main()
        # Flush any output from user_main to terminal
        if console_has_output():
            term_puts_idx(0, console_flush())
        term_puts_idx(0, "\nClick 'Applications' or press ESC ESC for menu\n")
        term_puts_idx(0, "Type 'help' for available commands\n\n")
        term_print_prompt(0)
    active_win = 0
    needs_full_redraw = True

def de_main():
    global needs_full_redraw, panel_dirty
    de_init()
    de_draw()
    vtn_present()
    while True:
        # Update timer (must be called regularly for timer_get_ticks to work)
        timer_tick()

        # Call user tick function (cooperative multitasking)
        user_tick()

        # Flush any output from user_tick to terminal 0
        if console_has_output():
            term_puts_idx(0, console_flush())
            # Use full redraw to maintain proper z-order
            needs_full_redraw = True

        if uart_available():
            c: char = uart_getc()
            handle_input(c)
            panel_dirty = True
        if needs_full_redraw or panel_dirty or win_dirty[0] or win_dirty[1] or win_dirty[2] or win_dirty[3]:
            de_draw()
            vtn_present()
