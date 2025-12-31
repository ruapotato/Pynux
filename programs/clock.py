# Pynux Clock Application
#
# Digital clock displaying current uptime.

from lib.vtnext import vtn_rect, vtn_textline, vtn_rect_outline
from lib.string import itoa
from kernel.timer import timer_get_ticks

# Clock State
clock_time_buf: Array[20, char]
clock_last_update: int32 = 0

# Window layout
CLOCK_X: int32 = 280
CLOCK_Y: int32 = 180
CLOCK_W: int32 = 240
CLOCK_H: int32 = 140
CLOCK_TITLE_H: int32 = 24

# Clock colors
CLOCK_TIME_R: int32 = 0
CLOCK_TIME_G: int32 = 255
CLOCK_TIME_B: int32 = 128

def clock_init():
    global clock_last_update
    clock_last_update = 0
    clock_time_buf[0] = '0'
    clock_time_buf[1] = '0'
    clock_time_buf[2] = ':'
    clock_time_buf[3] = '0'
    clock_time_buf[4] = '0'
    clock_time_buf[5] = ':'
    clock_time_buf[6] = '0'
    clock_time_buf[7] = '0'
    clock_time_buf[8] = '\0'

def clock_format_digit(val: int32, buf: Ptr[char], pos: int32):
    tens: int32 = val / 10
    ones: int32 = val % 10
    buf[pos] = cast[char](cast[int32]('0') + tens)
    buf[pos + 1] = cast[char](cast[int32]('0') + ones)

def clock_update() -> bool:
    global clock_last_update
    ticks: int32 = timer_get_ticks()
    if ticks - clock_last_update < 1000:
        return False
    clock_last_update = ticks
    total_secs: int32 = ticks / 1000
    hours: int32 = (total_secs / 3600) % 100
    mins: int32 = (total_secs / 60) % 60
    secs: int32 = total_secs % 60
    clock_format_digit(hours, &clock_time_buf[0], 0)
    clock_time_buf[2] = ':'
    clock_format_digit(mins, &clock_time_buf[0], 3)
    clock_time_buf[5] = ':'
    clock_format_digit(secs, &clock_time_buf[0], 6)
    clock_time_buf[8] = '\0'
    return True

def clock_needs_update() -> bool:
    ticks: int32 = timer_get_ticks()
    return (ticks - clock_last_update) >= 1000

def clock_draw_digit(x: int32, y: int32, digit: char):
    d: int32 = cast[int32](digit) - cast[int32]('0')
    if d < 0 or d > 9:
        if digit == ':':
            vtn_rect(x + 10, y + 12, 6, 6, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)
            vtn_rect(x + 10, y + 32, 6, 6, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)
        return
    w: int32 = 24
    h: int32 = 44
    t: int32 = 5
    segments: Array[10, int32]
    segments[0] = 0x3F
    segments[1] = 0x06
    segments[2] = 0x5B
    segments[3] = 0x4F
    segments[4] = 0x66
    segments[5] = 0x6D
    segments[6] = 0x7D
    segments[7] = 0x07
    segments[8] = 0x7F
    segments[9] = 0x6F
    seg: int32 = segments[d]
    if (seg & 0x01) != 0:
        vtn_rect(x + t, y, w - 2 * t, t, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)
    if (seg & 0x02) != 0:
        vtn_rect(x + w - t, y + t, t, h / 2 - t, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)
    if (seg & 0x04) != 0:
        vtn_rect(x + w - t, y + h / 2, t, h / 2 - t, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)
    if (seg & 0x08) != 0:
        vtn_rect(x + t, y + h - t, w - 2 * t, t, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)
    if (seg & 0x10) != 0:
        vtn_rect(x, y + h / 2, t, h / 2 - t, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)
    if (seg & 0x20) != 0:
        vtn_rect(x, y + t, t, h / 2 - t, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)
    if (seg & 0x40) != 0:
        vtn_rect(x + t, y + h / 2 - t / 2, w - 2 * t, t, CLOCK_TIME_R, CLOCK_TIME_G, CLOCK_TIME_B, 255)

def clock_draw():
    x: int32 = CLOCK_X
    y: int32 = CLOCK_Y
    vtn_rect(x + 3, y + 3, CLOCK_W, CLOCK_H, 20, 20, 20, 255)
    vtn_rect(x - 1, y - 1, CLOCK_W + 2, CLOCK_H + 2, 60, 60, 60, 255)
    vtn_rect(x, y, CLOCK_W, CLOCK_TITLE_H, 78, 128, 188, 255)
    vtn_textline("Clock", x + 8, y + 4, 230, 230, 230)
    cbx: int32 = x + CLOCK_W - 20
    cby: int32 = y + 4
    vtn_rect(cbx, cby, 16, 16, 180, 60, 60, 255)
    vtn_textline("X", cbx + 4, cby + 1, 230, 230, 230)
    vtn_rect(x, y + CLOCK_TITLE_H, CLOCK_W, CLOCK_H - CLOCK_TITLE_H, 32, 32, 32, 255)
    dx: int32 = x + 15
    dy: int32 = y + CLOCK_TITLE_H + 15
    dw: int32 = CLOCK_W - 30
    dh: int32 = 60
    vtn_rect(dx, dy, dw, dh, 16, 16, 16, 255)
    vtn_rect_outline(dx, dy, dw, dh, 1, 40, 40, 40, 255)
    clock_update()
    digit_w: int32 = 26
    colon_w: int32 = 20
    total_w: int32 = 6 * digit_w + 2 * colon_w
    start_x: int32 = dx + (dw - total_w) / 2 + 4
    digit_y: int32 = dy + 8
    cx: int32 = start_x
    i: int32 = 0
    while clock_time_buf[i] != '\0':
        c: char = clock_time_buf[i]
        clock_draw_digit(cx, digit_y, c)
        if c == ':':
            cx = cx + colon_w
        else:
            cx = cx + digit_w
        i = i + 1
    vtn_textline("System Uptime", x + 75, y + CLOCK_TITLE_H + 85, 160, 160, 160)

def clock_handle_click(mx: int32, my: int32) -> bool:
    x: int32 = CLOCK_X
    y: int32 = CLOCK_Y
    if mx < x or mx >= x + CLOCK_W:
        return False
    if my < y or my >= y + CLOCK_H:
        return False
    cbx: int32 = x + CLOCK_W - 20
    cby: int32 = y + 4
    if mx >= cbx and mx < cbx + 16 and my >= cby and my < cby + 16:
        return False
    return True

def clock_main():
    clock_init()
