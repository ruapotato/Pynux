# Pynux UI Widgets Library
#
# Reusable UI components for the Desktop Environment.
# Uses VTNext protocol for graphics rendering.
#
# Widgets:
#   - Button: Clickable button with states (normal, hover, pressed)
#   - TextInput: Single-line text input with cursor
#   - Scrollbar: Vertical scrollbar
#   - Checkbox: Toggle checkbox
#   - Menu: Dropdown menu

from lib.vtnext import vtn_rect, vtn_rect_outline, vtn_textline
from lib.string import strlen, strcpy, memset

# ============================================================================
# Widget state constants
# ============================================================================

# Button states
BTN_STATE_NORMAL: int32 = 0
BTN_STATE_HOVER: int32 = 1
BTN_STATE_PRESSED: int32 = 2

# Button struct layout (24 bytes):
#   x: int32         offset 0
#   y: int32         offset 4
#   w: int32         offset 8
#   h: int32         offset 12
#   state: int32     offset 16
#   callback_id: int32  offset 20
BTN_STRUCT_SIZE: int32 = 24

# TextInput struct layout (28 bytes):
#   x: int32         offset 0
#   y: int32         offset 4
#   w: int32         offset 8
#   cursor: int32    offset 12
#   buf_size: int32  offset 16
#   focused: int32   offset 20
#   scroll: int32    offset 24
TEXTINPUT_STRUCT_SIZE: int32 = 28

# Scrollbar struct layout (24 bytes):
#   x: int32         offset 0
#   y: int32         offset 4
#   h: int32         offset 8
#   pos: int32       offset 12
#   max_pos: int32   offset 16
#   dragging: int32  offset 20
SCROLLBAR_STRUCT_SIZE: int32 = 24

# Checkbox struct layout (16 bytes):
#   x: int32         offset 0
#   y: int32         offset 4
#   checked: int32   offset 8
#   hover: int32     offset 12
CHECKBOX_STRUCT_SIZE: int32 = 16

# Menu struct layout (24 bytes):
#   x: int32         offset 0
#   y: int32         offset 4
#   count: int32     offset 8
#   selection: int32 offset 12
#   visible: int32   offset 16
#   hover: int32     offset 20
MENU_STRUCT_SIZE: int32 = 24

# ============================================================================
# Widget colors
# ============================================================================

# Button colors - normal state
BTN_NORMAL_R: int32 = 70
BTN_NORMAL_G: int32 = 70
BTN_NORMAL_B: int32 = 70

# Button colors - hover state
BTN_HOVER_R: int32 = 90
BTN_HOVER_G: int32 = 90
BTN_HOVER_B: int32 = 90

# Button colors - pressed state
BTN_PRESSED_R: int32 = 50
BTN_PRESSED_G: int32 = 50
BTN_PRESSED_B: int32 = 50

# Button border
BTN_BORDER_R: int32 = 100
BTN_BORDER_G: int32 = 100
BTN_BORDER_B: int32 = 100

# Text input colors
INPUT_BG_R: int32 = 40
INPUT_BG_G: int32 = 40
INPUT_BG_B: int32 = 40

INPUT_BORDER_R: int32 = 80
INPUT_BORDER_G: int32 = 80
INPUT_BORDER_B: int32 = 80

INPUT_FOCUS_R: int32 = 78
INPUT_FOCUS_G: int32 = 128
INPUT_FOCUS_B: int32 = 188

# Scrollbar colors
SCROLL_BG_R: int32 = 50
SCROLL_BG_G: int32 = 50
SCROLL_BG_B: int32 = 50

SCROLL_THUMB_R: int32 = 100
SCROLL_THUMB_G: int32 = 100
SCROLL_THUMB_B: int32 = 100

SCROLL_THUMB_HOVER_R: int32 = 130
SCROLL_THUMB_HOVER_G: int32 = 130
SCROLL_THUMB_HOVER_B: int32 = 130

# Checkbox colors
CHECK_BG_R: int32 = 50
CHECK_BG_G: int32 = 50
CHECK_BG_B: int32 = 50

CHECK_MARK_R: int32 = 100
CHECK_MARK_G: int32 = 200
CHECK_MARK_B: int32 = 100

# Menu colors
MENU_BG_R: int32 = 55
MENU_BG_G: int32 = 55
MENU_BG_B: int32 = 55

MENU_HOVER_R: int32 = 78
MENU_HOVER_G: int32 = 128
MENU_HOVER_B: int32 = 188

# Text color
WIDGET_TEXT_R: int32 = 230
WIDGET_TEXT_G: int32 = 230
WIDGET_TEXT_B: int32 = 230

# Character dimensions (matching de.py)
WIDGET_CHAR_W: int32 = 10
WIDGET_CHAR_H: int32 = 16

# Scrollbar dimensions
SCROLLBAR_W: int32 = 14
MIN_THUMB_H: int32 = 20

# Menu item height
MENU_ITEM_H: int32 = 24

# Checkbox size
CHECKBOX_SIZE: int32 = 16

# ============================================================================
# Button Widget
# ============================================================================

def widget_button_init(btn: Ptr[int32], x: int32, y: int32, w: int32, h: int32, callback_id: int32):
    """Initialize a button widget."""
    btn[0] = x
    btn[1] = y
    btn[2] = w
    btn[3] = h
    btn[4] = BTN_STATE_NORMAL
    btn[5] = callback_id

def widget_button_draw(btn: Ptr[int32], label: Ptr[char]):
    """Draw a button widget."""
    x: int32 = btn[0]
    y: int32 = btn[1]
    w: int32 = btn[2]
    h: int32 = btn[3]
    state: int32 = btn[4]

    # Background color based on state
    bg_r: int32 = BTN_NORMAL_R
    bg_g: int32 = BTN_NORMAL_G
    bg_b: int32 = BTN_NORMAL_B

    if state == BTN_STATE_HOVER:
        bg_r = BTN_HOVER_R
        bg_g = BTN_HOVER_G
        bg_b = BTN_HOVER_B
    elif state == BTN_STATE_PRESSED:
        bg_r = BTN_PRESSED_R
        bg_g = BTN_PRESSED_G
        bg_b = BTN_PRESSED_B

    # Draw background
    vtn_rect(x, y, w, h, bg_r, bg_g, bg_b, 255)

    # Draw border
    vtn_rect_outline(x, y, w, h, 1, BTN_BORDER_R, BTN_BORDER_G, BTN_BORDER_B, 255)

    # Center the label
    label_len: int32 = strlen(label)
    text_x: int32 = x + (w - label_len * WIDGET_CHAR_W) / 2
    text_y: int32 = y + (h - WIDGET_CHAR_H) / 2

    vtn_textline(cast[Ptr[uint8]](label), text_x, text_y, WIDGET_TEXT_R, WIDGET_TEXT_G, WIDGET_TEXT_B)

def widget_button_handle_mouse(btn: Ptr[int32], mx: int32, my: int32, pressed: bool) -> int32:
    """Handle mouse input for button. Returns callback_id if clicked, -1 otherwise."""
    x: int32 = btn[0]
    y: int32 = btn[1]
    w: int32 = btn[2]
    h: int32 = btn[3]
    old_state: int32 = btn[4]

    # Check if mouse is over button
    inside: bool = mx >= x and mx < x + w and my >= y and my < y + h

    if inside:
        if pressed:
            btn[4] = BTN_STATE_PRESSED
        else:
            # Released while inside = click
            if old_state == BTN_STATE_PRESSED:
                btn[4] = BTN_STATE_HOVER
                return btn[5]  # callback_id
            btn[4] = BTN_STATE_HOVER
    else:
        btn[4] = BTN_STATE_NORMAL

    return -1

def widget_button_set_state(btn: Ptr[int32], state: int32):
    """Set button state directly."""
    btn[4] = state

# ============================================================================
# Text Input Widget
# ============================================================================

def widget_textinput_init(ti: Ptr[int32], x: int32, y: int32, w: int32, buf_size: int32):
    """Initialize a text input widget."""
    ti[0] = x
    ti[1] = y
    ti[2] = w
    ti[3] = 0       # cursor
    ti[4] = buf_size
    ti[5] = 0       # focused (false)
    ti[6] = 0       # scroll

def widget_textinput_draw(ti: Ptr[int32], buf: Ptr[char]):
    """Draw a text input widget."""
    x: int32 = ti[0]
    y: int32 = ti[1]
    w: int32 = ti[2]
    cursor: int32 = ti[3]
    focused: int32 = ti[5]
    scroll: int32 = ti[6]

    h: int32 = WIDGET_CHAR_H + 8

    # Background
    vtn_rect(x, y, w, h, INPUT_BG_R, INPUT_BG_G, INPUT_BG_B, 255)

    # Border - highlight if focused
    if focused != 0:
        vtn_rect_outline(x, y, w, h, 1, INPUT_FOCUS_R, INPUT_FOCUS_G, INPUT_FOCUS_B, 255)
    else:
        vtn_rect_outline(x, y, w, h, 1, INPUT_BORDER_R, INPUT_BORDER_G, INPUT_BORDER_B, 255)

    # Calculate visible text area
    text_x: int32 = x + 4
    text_y: int32 = y + 4
    visible_chars: int32 = (w - 8) / WIDGET_CHAR_W

    # Draw text (scrolled if needed)
    text_len: int32 = strlen(buf)
    display_start: int32 = scroll
    if display_start > text_len:
        display_start = text_len

    # Draw visible portion
    i: int32 = 0
    while i < visible_chars and display_start + i < text_len:
        c: char = buf[display_start + i]
        # Draw single character using a temp buffer
        char_buf: Array[2, char]
        char_buf[0] = c
        char_buf[1] = '\0'
        vtn_textline(cast[Ptr[uint8]](&char_buf[0]), text_x + i * WIDGET_CHAR_W, text_y, WIDGET_TEXT_R, WIDGET_TEXT_G, WIDGET_TEXT_B)
        i = i + 1

    # Draw cursor if focused
    if focused != 0:
        cursor_visible_pos: int32 = cursor - scroll
        if cursor_visible_pos >= 0 and cursor_visible_pos <= visible_chars:
            cursor_x: int32 = text_x + cursor_visible_pos * WIDGET_CHAR_W
            cursor_y: int32 = y + 4 + WIDGET_CHAR_H - 2
            vtn_rect(cursor_x, cursor_y, WIDGET_CHAR_W, 2, 0, 255, 0, 255)

def widget_textinput_handle_key(ti: Ptr[int32], buf: Ptr[char], c: char) -> bool:
    """Handle keyboard input for text input. Returns true if handled."""
    focused: int32 = ti[5]
    if focused == 0:
        return False

    cursor: int32 = ti[3]
    buf_size: int32 = ti[4]
    text_len: int32 = strlen(buf)
    cv: int32 = cast[int32](c)

    # Backspace
    if cv == 8 or cv == 127:
        if cursor > 0:
            # Shift characters left
            i: int32 = cursor - 1
            while i < text_len:
                buf[i] = buf[i + 1]
                i = i + 1
            cursor = cursor - 1
            ti[3] = cursor
            widget_textinput_update_scroll(ti)
        return True

    # Delete key (special handling if supported)
    if cv == 4:  # Ctrl+D often used as delete
        if cursor < text_len:
            i = cursor
            while i < text_len:
                buf[i] = buf[i + 1]
                i = i + 1
        return True

    # Printable characters
    if cv >= 32 and cv < 127:
        if text_len < buf_size - 1:
            # Shift characters right
            i = text_len + 1
            while i > cursor:
                buf[i] = buf[i - 1]
                i = i - 1
            buf[cursor] = c
            cursor = cursor + 1
            ti[3] = cursor
            widget_textinput_update_scroll(ti)
        return True

    return False

def widget_textinput_handle_mouse(ti: Ptr[int32], buf: Ptr[char], mx: int32, my: int32, pressed: bool) -> bool:
    """Handle mouse input for text input. Returns true if now focused."""
    x: int32 = ti[0]
    y: int32 = ti[1]
    w: int32 = ti[2]
    h: int32 = WIDGET_CHAR_H + 8
    scroll: int32 = ti[6]

    # Check if click is inside
    inside: bool = mx >= x and mx < x + w and my >= y and my < y + h

    if pressed and inside:
        ti[5] = 1  # Set focused
        # Calculate cursor position from click
        text_x: int32 = x + 4
        rel_x: int32 = mx - text_x
        char_pos: int32 = rel_x / WIDGET_CHAR_W
        if char_pos < 0:
            char_pos = 0
        new_cursor: int32 = scroll + char_pos
        text_len: int32 = strlen(buf)
        if new_cursor > text_len:
            new_cursor = text_len
        ti[3] = new_cursor
        return True
    elif pressed:
        ti[5] = 0  # Unfocus

    return ti[5] != 0

def widget_textinput_update_scroll(ti: Ptr[int32]):
    """Update scroll position to keep cursor visible."""
    cursor: int32 = ti[3]
    scroll: int32 = ti[6]
    w: int32 = ti[2]
    visible_chars: int32 = (w - 8) / WIDGET_CHAR_W

    # Scroll left if cursor before scroll
    if cursor < scroll:
        ti[6] = cursor
    # Scroll right if cursor past visible area
    elif cursor >= scroll + visible_chars:
        ti[6] = cursor - visible_chars + 1

def widget_textinput_set_cursor(ti: Ptr[int32], pos: int32):
    """Set cursor position."""
    ti[3] = pos
    widget_textinput_update_scroll(ti)

def widget_textinput_move_cursor(ti: Ptr[int32], buf: Ptr[char], delta: int32):
    """Move cursor by delta positions."""
    cursor: int32 = ti[3]
    text_len: int32 = strlen(buf)
    new_pos: int32 = cursor + delta
    if new_pos < 0:
        new_pos = 0
    if new_pos > text_len:
        new_pos = text_len
    ti[3] = new_pos
    widget_textinput_update_scroll(ti)

def widget_textinput_set_focus(ti: Ptr[int32], focused: bool):
    """Set focus state."""
    if focused:
        ti[5] = 1
    else:
        ti[5] = 0

def widget_textinput_is_focused(ti: Ptr[int32]) -> bool:
    """Check if input is focused."""
    return ti[5] != 0

# ============================================================================
# Scrollbar Widget
# ============================================================================

def widget_scrollbar_init(sb: Ptr[int32], x: int32, y: int32, h: int32, max_pos: int32):
    """Initialize a vertical scrollbar widget."""
    sb[0] = x
    sb[1] = y
    sb[2] = h
    sb[3] = 0           # pos
    sb[4] = max_pos
    sb[5] = 0           # dragging

def widget_scrollbar_draw(sb: Ptr[int32]):
    """Draw a vertical scrollbar widget."""
    x: int32 = sb[0]
    y: int32 = sb[1]
    h: int32 = sb[2]
    pos: int32 = sb[3]
    max_pos: int32 = sb[4]
    dragging: int32 = sb[5]

    # Background track
    vtn_rect(x, y, SCROLLBAR_W, h, SCROLL_BG_R, SCROLL_BG_G, SCROLL_BG_B, 255)

    # Calculate thumb size and position
    if max_pos <= 0:
        max_pos = 1

    # Thumb height proportional to visible/total ratio (min 20px)
    thumb_h: int32 = h * h / (h + max_pos * WIDGET_CHAR_H)
    if thumb_h < MIN_THUMB_H:
        thumb_h = MIN_THUMB_H
    if thumb_h > h:
        thumb_h = h

    # Thumb position
    track_space: int32 = h - thumb_h
    thumb_y: int32 = y
    if max_pos > 0 and track_space > 0:
        thumb_y = y + pos * track_space / max_pos

    # Draw thumb
    thumb_r: int32 = SCROLL_THUMB_R
    thumb_g: int32 = SCROLL_THUMB_G
    thumb_b: int32 = SCROLL_THUMB_B
    if dragging != 0:
        thumb_r = SCROLL_THUMB_HOVER_R
        thumb_g = SCROLL_THUMB_HOVER_G
        thumb_b = SCROLL_THUMB_HOVER_B

    vtn_rect(x + 2, thumb_y + 2, SCROLLBAR_W - 4, thumb_h - 4, thumb_r, thumb_g, thumb_b, 255)

def widget_scrollbar_handle_mouse(sb: Ptr[int32], mx: int32, my: int32, pressed: bool) -> bool:
    """Handle mouse input for scrollbar. Returns true if position changed."""
    x: int32 = sb[0]
    y: int32 = sb[1]
    h: int32 = sb[2]
    pos: int32 = sb[3]
    max_pos: int32 = sb[4]

    # Check if mouse is over scrollbar track
    inside: bool = mx >= x and mx < x + SCROLLBAR_W and my >= y and my < y + h

    if pressed and inside:
        sb[5] = 1  # Start dragging
    elif not pressed:
        sb[5] = 0  # Stop dragging

    if sb[5] != 0 and inside:
        # Calculate new position from mouse y
        track_space: int32 = h
        if track_space > 0 and max_pos > 0:
            rel_y: int32 = my - y
            new_pos: int32 = rel_y * max_pos / track_space
            if new_pos < 0:
                new_pos = 0
            if new_pos > max_pos:
                new_pos = max_pos
            if new_pos != pos:
                sb[3] = new_pos
                return True

    return False

def widget_scrollbar_set_pos(sb: Ptr[int32], pos: int32):
    """Set scrollbar position."""
    max_pos: int32 = sb[4]
    if pos < 0:
        pos = 0
    if pos > max_pos:
        pos = max_pos
    sb[3] = pos

def widget_scrollbar_get_pos(sb: Ptr[int32]) -> int32:
    """Get scrollbar position."""
    return sb[3]

def widget_scrollbar_set_max(sb: Ptr[int32], max_pos: int32):
    """Set maximum scrollbar position."""
    sb[4] = max_pos
    # Clamp current position
    if sb[3] > max_pos:
        sb[3] = max_pos

def widget_scrollbar_scroll(sb: Ptr[int32], delta: int32) -> bool:
    """Scroll by delta. Returns true if position changed."""
    pos: int32 = sb[3]
    max_pos: int32 = sb[4]
    new_pos: int32 = pos + delta
    if new_pos < 0:
        new_pos = 0
    if new_pos > max_pos:
        new_pos = max_pos
    if new_pos != pos:
        sb[3] = new_pos
        return True
    return False

# ============================================================================
# Checkbox Widget
# ============================================================================

def widget_checkbox_init(cb: Ptr[int32], x: int32, y: int32, checked: bool):
    """Initialize a checkbox widget."""
    cb[0] = x
    cb[1] = y
    if checked:
        cb[2] = 1
    else:
        cb[2] = 0
    cb[3] = 0  # hover

def widget_checkbox_draw(cb: Ptr[int32], label: Ptr[char]):
    """Draw a checkbox widget with label."""
    x: int32 = cb[0]
    y: int32 = cb[1]
    checked: int32 = cb[2]
    hover: int32 = cb[3]

    # Background
    bg_r: int32 = CHECK_BG_R
    bg_g: int32 = CHECK_BG_G
    bg_b: int32 = CHECK_BG_B
    if hover != 0:
        bg_r = bg_r + 20
        bg_g = bg_g + 20
        bg_b = bg_b + 20

    vtn_rect(x, y, CHECKBOX_SIZE, CHECKBOX_SIZE, bg_r, bg_g, bg_b, 255)
    vtn_rect_outline(x, y, CHECKBOX_SIZE, CHECKBOX_SIZE, 1, BTN_BORDER_R, BTN_BORDER_G, BTN_BORDER_B, 255)

    # Check mark if checked
    if checked != 0:
        # Draw a simple check mark (filled inner square)
        vtn_rect(x + 3, y + 3, CHECKBOX_SIZE - 6, CHECKBOX_SIZE - 6, CHECK_MARK_R, CHECK_MARK_G, CHECK_MARK_B, 255)

    # Label
    vtn_textline(cast[Ptr[uint8]](label), x + CHECKBOX_SIZE + 6, y, WIDGET_TEXT_R, WIDGET_TEXT_G, WIDGET_TEXT_B)

def widget_checkbox_handle_mouse(cb: Ptr[int32], label: Ptr[char], mx: int32, my: int32, pressed: bool) -> bool:
    """Handle mouse input for checkbox. Returns true if toggled."""
    x: int32 = cb[0]
    y: int32 = cb[1]

    # Clickable area includes label
    label_len: int32 = strlen(label)
    total_w: int32 = CHECKBOX_SIZE + 6 + label_len * WIDGET_CHAR_W

    inside: bool = mx >= x and mx < x + total_w and my >= y and my < y + CHECKBOX_SIZE

    if inside:
        cb[3] = 1  # hover
        if pressed:
            # Toggle
            if cb[2] != 0:
                cb[2] = 0
            else:
                cb[2] = 1
            return True
    else:
        cb[3] = 0

    return False

def widget_checkbox_is_checked(cb: Ptr[int32]) -> bool:
    """Check if checkbox is checked."""
    return cb[2] != 0

def widget_checkbox_set_checked(cb: Ptr[int32], checked: bool):
    """Set checkbox checked state."""
    if checked:
        cb[2] = 1
    else:
        cb[2] = 0

def widget_checkbox_toggle(cb: Ptr[int32]):
    """Toggle checkbox state."""
    if cb[2] != 0:
        cb[2] = 0
    else:
        cb[2] = 1

# ============================================================================
# Menu Widget
# ============================================================================

# Menu items are stored in a separate buffer as null-terminated strings
# Each item is 32 bytes max

MENU_ITEM_MAX_LEN: int32 = 32
MENU_WIDTH: int32 = 160

def widget_menu_init(menu: Ptr[int32], x: int32, y: int32, count: int32):
    """Initialize a dropdown menu widget."""
    menu[0] = x
    menu[1] = y
    menu[2] = count
    menu[3] = 0  # selection
    menu[4] = 0  # visible (false)
    menu[5] = -1 # hover (-1 = none)

def widget_menu_draw(menu: Ptr[int32], items: Ptr[char]):
    """Draw a dropdown menu widget. Items is array of 32-byte strings."""
    visible: int32 = menu[4]
    if visible == 0:
        return

    x: int32 = menu[0]
    y: int32 = menu[1]
    count: int32 = menu[2]
    selection: int32 = menu[3]
    hover: int32 = menu[5]

    # Menu dimensions
    w: int32 = MENU_WIDTH
    h: int32 = count * MENU_ITEM_H + 4

    # Background with border
    vtn_rect(x, y, w, h, MENU_BG_R, MENU_BG_G, MENU_BG_B, 255)
    vtn_rect_outline(x, y, w, h, 1, BTN_BORDER_R, BTN_BORDER_G, BTN_BORDER_B, 255)

    # Draw items
    i: int32 = 0
    while i < count:
        item_y: int32 = y + 2 + i * MENU_ITEM_H

        # Highlight selection or hover
        if i == selection or i == hover:
            vtn_rect(x + 2, item_y, w - 4, MENU_ITEM_H, MENU_HOVER_R, MENU_HOVER_G, MENU_HOVER_B, 255)

        # Get item text
        item_ptr: Ptr[char] = &items[i * MENU_ITEM_MAX_LEN]
        vtn_textline(cast[Ptr[uint8]](item_ptr), x + 8, item_y + 4, WIDGET_TEXT_R, WIDGET_TEXT_G, WIDGET_TEXT_B)

        i = i + 1

def widget_menu_handle_mouse(menu: Ptr[int32], mx: int32, my: int32, pressed: bool) -> int32:
    """Handle mouse input for menu. Returns selected item index or -1."""
    visible: int32 = menu[4]
    if visible == 0:
        return -1

    x: int32 = menu[0]
    y: int32 = menu[1]
    count: int32 = menu[2]

    w: int32 = MENU_WIDTH
    h: int32 = count * MENU_ITEM_H + 4

    # Check if inside menu
    inside: bool = mx >= x and mx < x + w and my >= y and my < y + h

    if inside:
        # Calculate which item
        rel_y: int32 = my - y - 2
        item_idx: int32 = rel_y / MENU_ITEM_H
        if item_idx < 0:
            item_idx = 0
        if item_idx >= count:
            item_idx = count - 1

        menu[5] = item_idx  # hover

        if pressed:
            menu[3] = item_idx  # selection
            menu[4] = 0  # hide menu
            return item_idx
    else:
        menu[5] = -1  # clear hover
        if pressed:
            menu[4] = 0  # close menu on click outside

    return -1

def widget_menu_handle_key(menu: Ptr[int32], c: char) -> int32:
    """Handle keyboard input for menu. Returns selected item index or -1."""
    visible: int32 = menu[4]
    if visible == 0:
        return -1

    count: int32 = menu[2]
    selection: int32 = menu[3]
    cv: int32 = cast[int32](c)

    # Escape - close menu
    if cv == 27:
        menu[4] = 0
        return -1

    # Up arrow or k
    if c == 'k' or cv == 16:  # Ctrl+P is often up
        selection = selection - 1
        if selection < 0:
            selection = count - 1
        menu[3] = selection
        menu[5] = selection  # sync hover
        return -1

    # Down arrow or j
    if c == 'j' or cv == 14:  # Ctrl+N is often down
        selection = selection + 1
        if selection >= count:
            selection = 0
        menu[3] = selection
        menu[5] = selection  # sync hover
        return -1

    # Enter - select
    if c == '\r' or c == '\n':
        menu[4] = 0  # hide
        return selection

    return -1

def widget_menu_show(menu: Ptr[int32]):
    """Show the menu."""
    menu[4] = 1
    menu[3] = 0  # reset selection
    menu[5] = 0  # reset hover

def widget_menu_hide(menu: Ptr[int32]):
    """Hide the menu."""
    menu[4] = 0

def widget_menu_is_visible(menu: Ptr[int32]) -> bool:
    """Check if menu is visible."""
    return menu[4] != 0

def widget_menu_set_selection(menu: Ptr[int32], sel: int32):
    """Set menu selection."""
    count: int32 = menu[2]
    if sel >= 0 and sel < count:
        menu[3] = sel
        menu[5] = sel

def widget_menu_get_selection(menu: Ptr[int32]) -> int32:
    """Get current menu selection."""
    return menu[3]

# ============================================================================
# Convenience functions
# ============================================================================

def widget_button(x: int32, y: int32, w: int32, h: int32, label: Ptr[char], callback_id: int32) -> Ptr[int32]:
    """Create and return a button state struct (caller must provide storage)."""
    # This is a convenience documentation - caller should use widget_button_init
    return Ptr[int32](0)

def widget_textinput(x: int32, y: int32, w: int32, buf: Ptr[char], buf_size: int32) -> Ptr[int32]:
    """Create and return a text input state struct (caller must provide storage)."""
    # This is a convenience documentation - caller should use widget_textinput_init
    return Ptr[int32](0)

def widget_scrollbar(x: int32, y: int32, h: int32, pos: int32, max_pos: int32) -> Ptr[int32]:
    """Create and return a scrollbar state struct (caller must provide storage)."""
    # This is a convenience documentation - caller should use widget_scrollbar_init
    return Ptr[int32](0)

def widget_checkbox(x: int32, y: int32, label: Ptr[char], checked: bool) -> Ptr[int32]:
    """Create and return a checkbox state struct (caller must provide storage)."""
    # This is a convenience documentation - caller should use widget_checkbox_init
    return Ptr[int32](0)

def widget_menu(x: int32, y: int32, items: Ptr[char], count: int32) -> Ptr[int32]:
    """Create and return a menu state struct (caller must provide storage)."""
    # This is a convenience documentation - caller should use widget_menu_init
    return Ptr[int32](0)
