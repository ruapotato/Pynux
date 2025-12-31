# Pynux Calculator Application
#
# GUI calculator with integer math operations.

from lib.vtnext import vtn_rect, vtn_textline, vtn_rect_outline, vtn_present
from lib.string import strlen, itoa

# Calculator State
calc_display: Array[20, char]
calc_display_len: int32 = 0
calc_operand: int32 = 0
calc_result: int32 = 0
calc_op: int32 = 0
calc_new_number: bool = True
calc_has_operand: bool = False
calc_error: bool = False

# Window layout
CALC_X: int32 = 200
CALC_Y: int32 = 100
CALC_W: int32 = 220
CALC_H: int32 = 300
CALC_BTN_W: int32 = 45
CALC_BTN_H: int32 = 35
CALC_BTN_GAP: int32 = 5
CALC_TITLE_H: int32 = 24

def calc_init():
    global calc_display_len, calc_operand, calc_result, calc_op
    global calc_new_number, calc_has_operand, calc_error
    calc_display[0] = '0'
    calc_display[1] = '\0'
    calc_display_len = 1
    calc_operand = 0
    calc_result = 0
    calc_op = 0
    calc_new_number = True
    calc_has_operand = False
    calc_error = False

def calc_clear():
    calc_init()

def calc_display_to_int() -> int32:
    result: int32 = 0
    negative: bool = False
    i: int32 = 0
    if calc_display[0] == '-':
        negative = True
        i = 1
    while i < calc_display_len:
        c: char = calc_display[i]
        if c >= '0' and c <= '9':
            result = result * 10 + (cast[int32](c) - cast[int32]('0'))
        i = i + 1
    if negative:
        result = -result
    return result

def calc_int_to_display(val: int32):
    global calc_display_len
    if val == 0:
        calc_display[0] = '0'
        calc_display[1] = '\0'
        calc_display_len = 1
        return
    temp: Array[20, char]
    itoa(val, &temp[0])
    i: int32 = 0
    while temp[i] != '\0' and i < 15:
        calc_display[i] = temp[i]
        i = i + 1
    calc_display[i] = '\0'
    calc_display_len = i

def calc_digit(d: int32):
    global calc_display_len, calc_new_number, calc_error
    if calc_error:
        calc_clear()
    if calc_new_number:
        calc_display[0] = cast[char](cast[int32]('0') + d)
        calc_display[1] = '\0'
        calc_display_len = 1
        calc_new_number = False
    else:
        if calc_display_len < 12:
            if calc_display_len == 1 and calc_display[0] == '0':
                calc_display[0] = cast[char](cast[int32]('0') + d)
            else:
                calc_display[calc_display_len] = cast[char](cast[int32]('0') + d)
                calc_display_len = calc_display_len + 1
                calc_display[calc_display_len] = '\0'

def calc_operation(op: int32):
    global calc_op, calc_operand, calc_has_operand, calc_new_number
    if calc_error:
        calc_clear()
        return
    if calc_has_operand and not calc_new_number:
        calc_equals()
    calc_operand = calc_display_to_int()
    calc_op = op
    calc_has_operand = True
    calc_new_number = True

def calc_equals():
    global calc_result, calc_new_number, calc_has_operand, calc_op, calc_error
    if not calc_has_operand:
        return
    current: int32 = calc_display_to_int()
    if calc_op == 1:
        calc_result = calc_operand + current
    elif calc_op == 2:
        calc_result = calc_operand - current
    elif calc_op == 3:
        calc_result = calc_operand * current
    elif calc_op == 4:
        if current == 0:
            calc_display[0] = 'E'
            calc_display[1] = 'r'
            calc_display[2] = 'r'
            calc_display[3] = '\0'
            calc_display_len = 3
            calc_error = True
            calc_has_operand = False
            return
        calc_result = calc_operand / current
    else:
        calc_result = current
    calc_int_to_display(calc_result)
    calc_new_number = True
    calc_has_operand = False
    calc_op = 0

def calc_draw_btn(x: int32, y: int32, w: int32, h: int32, lbl: Ptr[char], cr: int32, cg: int32, cb: int32):
    vtn_rect(x, y, w, h, cr, cg, cb, 255)
    vtn_rect_outline(x, y, w, h, 1, 40, 40, 40, 255)
    lbl_len: int32 = strlen(lbl)
    tx: int32 = x + (w - lbl_len * 10) / 2
    ty: int32 = y + (h - 16) / 2
    vtn_textline(lbl, tx, ty, 230, 230, 230)

def calc_draw():
    x: int32 = CALC_X
    y: int32 = CALC_Y
    vtn_rect(x + 3, y + 3, CALC_W, CALC_H, 20, 20, 20, 255)
    vtn_rect(x - 1, y - 1, CALC_W + 2, CALC_H + 2, 60, 60, 60, 255)
    vtn_rect(x, y, CALC_W, CALC_TITLE_H, 78, 128, 188, 255)
    vtn_textline("Calculator", x + 8, y + 4, 230, 230, 230)
    cbx: int32 = x + CALC_W - 20
    cby: int32 = y + 4
    vtn_rect(cbx, cby, 16, 16, 180, 60, 60, 255)
    vtn_textline("X", cbx + 4, cby + 1, 230, 230, 230)
    vtn_rect(x, y + CALC_TITLE_H, CALC_W, CALC_H - CALC_TITLE_H, 48, 48, 48, 255)
    dx: int32 = x + 10
    dy: int32 = y + CALC_TITLE_H + 10
    dw: int32 = CALC_W - 20
    dh: int32 = 40
    vtn_rect(dx, dy, dw, dh, 32, 32, 32, 255)
    vtn_rect_outline(dx, dy, dw, dh, 1, 60, 60, 60, 255)
    display_len: int32 = strlen(&calc_display[0])
    tx: int32 = dx + dw - display_len * 10 - 8
    ty: int32 = dy + 12
    vtn_textline(&calc_display[0], tx, ty, 230, 230, 230)
    bx: int32 = x + 10
    by: int32 = dy + dh + 15
    calc_draw_btn(bx, by, CALC_BTN_W, CALC_BTN_H, "C", 180, 60, 60)
    calc_draw_btn(bx + CALC_BTN_W + CALC_BTN_GAP, by, CALC_BTN_W, CALC_BTN_H, "/", 100, 80, 50)
    calc_draw_btn(bx + 2 * (CALC_BTN_W + CALC_BTN_GAP), by, CALC_BTN_W, CALC_BTN_H, "*", 100, 80, 50)
    calc_draw_btn(bx + 3 * (CALC_BTN_W + CALC_BTN_GAP), by, CALC_BTN_W, CALC_BTN_H, "-", 100, 80, 50)
    by = by + CALC_BTN_H + CALC_BTN_GAP
    calc_draw_btn(bx, by, CALC_BTN_W, CALC_BTN_H, "7", 70, 70, 70)
    calc_draw_btn(bx + CALC_BTN_W + CALC_BTN_GAP, by, CALC_BTN_W, CALC_BTN_H, "8", 70, 70, 70)
    calc_draw_btn(bx + 2 * (CALC_BTN_W + CALC_BTN_GAP), by, CALC_BTN_W, CALC_BTN_H, "9", 70, 70, 70)
    calc_draw_btn(bx + 3 * (CALC_BTN_W + CALC_BTN_GAP), by, CALC_BTN_W, CALC_BTN_H, "+", 100, 80, 50)
    by = by + CALC_BTN_H + CALC_BTN_GAP
    calc_draw_btn(bx, by, CALC_BTN_W, CALC_BTN_H, "4", 70, 70, 70)
    calc_draw_btn(bx + CALC_BTN_W + CALC_BTN_GAP, by, CALC_BTN_W, CALC_BTN_H, "5", 70, 70, 70)
    calc_draw_btn(bx + 2 * (CALC_BTN_W + CALC_BTN_GAP), by, CALC_BTN_W, CALC_BTN_H, "6", 70, 70, 70)
    eq_h: int32 = CALC_BTN_H * 2 + CALC_BTN_GAP
    calc_draw_btn(bx + 3 * (CALC_BTN_W + CALC_BTN_GAP), by, CALC_BTN_W, eq_h, "=", 78, 128, 188)
    by = by + CALC_BTN_H + CALC_BTN_GAP
    calc_draw_btn(bx, by, CALC_BTN_W, CALC_BTN_H, "1", 70, 70, 70)
    calc_draw_btn(bx + CALC_BTN_W + CALC_BTN_GAP, by, CALC_BTN_W, CALC_BTN_H, "2", 70, 70, 70)
    calc_draw_btn(bx + 2 * (CALC_BTN_W + CALC_BTN_GAP), by, CALC_BTN_W, CALC_BTN_H, "3", 70, 70, 70)
    by = by + CALC_BTN_H + CALC_BTN_GAP
    zero_w: int32 = CALC_BTN_W * 2 + CALC_BTN_GAP
    calc_draw_btn(bx, by, zero_w, CALC_BTN_H, "0", 70, 70, 70)
    calc_draw_btn(bx + 2 * (CALC_BTN_W + CALC_BTN_GAP), by, CALC_BTN_W, CALC_BTN_H, ".", 70, 70, 70)

def calc_handle_key(c: char):
    if c >= '0' and c <= '9':
        calc_digit(cast[int32](c) - cast[int32]('0'))
    elif c == '+':
        calc_operation(1)
    elif c == '-':
        calc_operation(2)
    elif c == '*':
        calc_operation(3)
    elif c == '/':
        calc_operation(4)
    elif c == '=' or c == '\r':
        calc_equals()
    elif c == 'c' or c == 'C':
        calc_clear()

def calc_handle_click(mx: int32, my: int32) -> bool:
    x: int32 = CALC_X
    y: int32 = CALC_Y
    if mx < x or mx >= x + CALC_W:
        return False
    if my < y or my >= y + CALC_H:
        return False
    cbx: int32 = x + CALC_W - 20
    cby: int32 = y + 4
    if mx >= cbx and mx < cbx + 16 and my >= cby and my < cby + 16:
        return False
    bx: int32 = x + 10
    by: int32 = y + CALC_TITLE_H + 10 + 40 + 15
    col: int32 = (mx - bx) / (CALC_BTN_W + CALC_BTN_GAP)
    row: int32 = (my - by) / (CALC_BTN_H + CALC_BTN_GAP)
    if col < 0 or col > 3 or row < 0 or row > 4:
        return True
    if row == 0:
        if col == 0:
            calc_clear()
        elif col == 1:
            calc_operation(4)
        elif col == 2:
            calc_operation(3)
        elif col == 3:
            calc_operation(2)
    elif row == 1:
        if col == 0:
            calc_digit(7)
        elif col == 1:
            calc_digit(8)
        elif col == 2:
            calc_digit(9)
        elif col == 3:
            calc_operation(1)
    elif row == 2:
        if col == 0:
            calc_digit(4)
        elif col == 1:
            calc_digit(5)
        elif col == 2:
            calc_digit(6)
        elif col == 3:
            calc_equals()
    elif row == 3:
        if col == 0:
            calc_digit(1)
        elif col == 1:
            calc_digit(2)
        elif col == 2:
            calc_digit(3)
        elif col == 3:
            calc_equals()
    elif row == 4:
        if col <= 1:
            calc_digit(0)
    return True

def calc_main():
    calc_init()
    calc_draw()
    vtn_present()
