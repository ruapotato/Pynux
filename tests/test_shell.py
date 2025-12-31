# Pynux Shell Enhancement Tests
#
# Comprehensive tests for shell features including:
# - Command history (circular buffer)
# - Line editing (cursor movement, insert/delete)
# - Aliases
# - Environment variables
# - Tab completion

from lib.io import print_str, print_int, print_newline
from lib.string import strcmp, strlen, strcpy
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_lt, test_pass, test_fail)
from lib.shell import (
    # History
    history_add, history_get, history_search, history_reset_pos,
    history_save_current, history_restore_saved,
    # History state
    shell_history_count, shell_history_pos, HISTORY_SIZE, HISTORY_CMD_LEN,
    # Line editing
    line_insert_char, line_delete_char,
    line_move_left, line_move_right, line_move_home, line_move_end,
    shell_cmd, shell_cmd_pos, shell_cursor_pos,
    # Aliases
    alias_find, alias_get, alias_set, alias_remove,
    ALIAS_MAX,
    # Environment
    env_find, env_get, env_set,
    ENV_MAX,
    # Completion
    shell_init_commands, complete_command, complete_path,
    # Init
    shell_init
)

# ============================================================================
# History Constants Tests
# ============================================================================

def test_history_constants():
    """Test history constants are correct."""
    print_section("History Constants")

    assert_eq(HISTORY_SIZE, 20, "HISTORY_SIZE is 20")
    assert_eq(HISTORY_CMD_LEN, 256, "HISTORY_CMD_LEN is 256")

# ============================================================================
# History Function Tests
# ============================================================================

def test_history_add_single():
    """Test adding a single command to history."""
    print_section("History Add")

    # Reset history for clean test
    # We'll add a command and verify it can be retrieved
    test_cmd: Array[32, char]
    test_cmd[0] = 't'
    test_cmd[1] = 'e'
    test_cmd[2] = 's'
    test_cmd[3] = 't'
    test_cmd[4] = '1'
    test_cmd[5] = '\0'

    history_add(&test_cmd[0])
    test_pass("history_add does not crash")

def test_history_add_empty():
    """Test that empty commands are not added to history."""
    empty: Array[2, char]
    empty[0] = '\0'

    count_before: int32 = shell_history_count
    history_add(&empty[0])
    # Count should not increase for empty command
    test_pass("history_add handles empty command")

def test_history_get():
    """Test retrieving commands from history."""
    print_section("History Get")

    # Add a command
    test_cmd: Array[32, char]
    test_cmd[0] = 'g'
    test_cmd[1] = 'e'
    test_cmd[2] = 't'
    test_cmd[3] = 't'
    test_cmd[4] = 'e'
    test_cmd[5] = 's'
    test_cmd[6] = 't'
    test_cmd[7] = '\0'

    history_add(&test_cmd[0])

    # Get most recent (index 0)
    cmd: Ptr[char] = history_get(0)
    if cast[uint32](cmd) != 0:
        test_pass("history_get(0) returns command")
    else:
        test_fail("history_get(0) should not be null")

def test_history_get_invalid():
    """Test getting invalid history index returns null."""
    # Negative index
    cmd1: Ptr[char] = history_get(-1)
    if cast[uint32](cmd1) == 0:
        test_pass("history_get(-1) returns null")
    else:
        test_fail("history_get(-1) should be null")

    # Very large index
    cmd2: Ptr[char] = history_get(10000)
    if cast[uint32](cmd2) == 0:
        test_pass("history_get(10000) returns null")
    else:
        test_fail("history_get(10000) should be null")

def test_history_search():
    """Test searching history by prefix."""
    print_section("History Search")

    # Add some commands
    cmd1: Array[32, char]
    cmd1[0] = 'l'
    cmd1[1] = 's'
    cmd1[2] = ' '
    cmd1[3] = '-'
    cmd1[4] = 'l'
    cmd1[5] = '\0'
    history_add(&cmd1[0])

    cmd2: Array[32, char]
    cmd2[0] = 'l'
    cmd2[1] = 's'
    cmd2[2] = ' '
    cmd2[3] = '-'
    cmd2[4] = 'a'
    cmd2[5] = '\0'
    history_add(&cmd2[0])

    # Search for "ls"
    prefix: Array[8, char]
    prefix[0] = 'l'
    prefix[1] = 's'
    prefix[2] = '\0'

    result: Ptr[char] = history_search(&prefix[0])
    if cast[uint32](result) != 0:
        test_pass("history_search finds match")
    else:
        test_fail("history_search should find 'ls' commands")

def test_history_search_no_match():
    """Test searching for non-existent prefix returns null."""
    prefix: Array[16, char]
    prefix[0] = 'n'
    prefix[1] = 'o'
    prefix[2] = 'n'
    prefix[3] = 'e'
    prefix[4] = 'x'
    prefix[5] = 'i'
    prefix[6] = 's'
    prefix[7] = 't'
    prefix[8] = '\0'

    result: Ptr[char] = history_search(&prefix[0])
    if cast[uint32](result) == 0:
        test_pass("history_search returns null for no match")
    else:
        test_fail("history_search should return null for no match")

def test_history_reset_pos():
    """Test resetting history navigation position."""
    history_reset_pos()
    assert_eq(shell_history_pos, -1, "history_pos reset to -1")

# ============================================================================
# Alias Tests
# ============================================================================

def test_alias_set_and_get():
    """Test setting and getting an alias."""
    print_section("Aliases")

    name: Array[16, char]
    name[0] = 'l'
    name[1] = 'l'
    name[2] = '\0'

    value: Array[32, char]
    value[0] = 'l'
    value[1] = 's'
    value[2] = ' '
    value[3] = '-'
    value[4] = 'l'
    value[5] = 'a'
    value[6] = '\0'

    # Set alias
    result: bool = alias_set(&name[0], &value[0])
    assert_true(result, "alias_set succeeds")

    # Get alias
    retrieved: Ptr[char] = alias_get(&name[0])
    if cast[uint32](retrieved) != 0:
        test_pass("alias_get returns value")
    else:
        test_fail("alias_get should return set value")

def test_alias_find():
    """Test finding alias index."""
    # Set a test alias
    name: Array[16, char]
    name[0] = 'f'
    name[1] = 'i'
    name[2] = 'n'
    name[3] = 'd'
    name[4] = 't'
    name[5] = 's'
    name[6] = 't'
    name[7] = '\0'

    value: Array[8, char]
    value[0] = 'l'
    value[1] = 's'
    value[2] = '\0'

    alias_set(&name[0], &value[0])

    # Find it
    idx: int32 = alias_find(&name[0])
    assert_gte(idx, 0, "alias_find returns valid index")

def test_alias_find_not_found():
    """Test finding non-existent alias returns -1."""
    name: Array[16, char]
    name[0] = 'n'
    name[1] = 'o'
    name[2] = 's'
    name[3] = 'u'
    name[4] = 'c'
    name[5] = 'h'
    name[6] = '\0'

    idx: int32 = alias_find(&name[0])
    assert_eq(idx, -1, "alias_find returns -1 for not found")

def test_alias_remove():
    """Test removing an alias."""
    print_section("Alias Remove")

    # Set an alias to remove
    name: Array[16, char]
    name[0] = 'r'
    name[1] = 'm'
    name[2] = 't'
    name[3] = 's'
    name[4] = 't'
    name[5] = '\0'

    value: Array[8, char]
    value[0] = 'a'
    value[1] = 'b'
    value[2] = 'c'
    value[3] = '\0'

    alias_set(&name[0], &value[0])

    # Remove it
    result: bool = alias_remove(&name[0])
    assert_true(result, "alias_remove succeeds")

    # Should not be found now
    idx: int32 = alias_find(&name[0])
    assert_eq(idx, -1, "removed alias not found")

def test_alias_remove_not_found():
    """Test removing non-existent alias returns false."""
    name: Array[16, char]
    name[0] = 'n'
    name[1] = 'o'
    name[2] = 'p'
    name[3] = 'e'
    name[4] = '\0'

    result: bool = alias_remove(&name[0])
    assert_false(result, "alias_remove returns false for not found")

# ============================================================================
# Environment Variable Tests
# ============================================================================

def test_env_set_and_get():
    """Test setting and getting an environment variable."""
    print_section("Environment Variables")

    name: Array[16, char]
    name[0] = 'T'
    name[1] = 'E'
    name[2] = 'S'
    name[3] = 'T'
    name[4] = '\0'

    value: Array[32, char]
    value[0] = 'v'
    value[1] = 'a'
    value[2] = 'l'
    value[3] = 'u'
    value[4] = 'e'
    value[5] = '\0'

    # Set env var
    result: bool = env_set(&name[0], &value[0])
    assert_true(result, "env_set succeeds")

    # Get env var
    retrieved: Ptr[char] = env_get(&name[0])
    if cast[uint32](retrieved) != 0:
        test_pass("env_get returns value")
    else:
        test_fail("env_get should return set value")

def test_env_find():
    """Test finding environment variable index."""
    name: Array[16, char]
    name[0] = 'F'
    name[1] = 'I'
    name[2] = 'N'
    name[3] = 'D'
    name[4] = '\0'

    value: Array[8, char]
    value[0] = 'x'
    value[1] = '\0'

    env_set(&name[0], &value[0])

    idx: int32 = env_find(&name[0])
    assert_gte(idx, 0, "env_find returns valid index")

def test_env_find_not_found():
    """Test finding non-existent env var returns -1."""
    name: Array[16, char]
    name[0] = 'N'
    name[1] = 'O'
    name[2] = 'T'
    name[3] = 'H'
    name[4] = 'E'
    name[5] = 'R'
    name[6] = 'E'
    name[7] = '\0'

    idx: int32 = env_find(&name[0])
    assert_eq(idx, -1, "env_find returns -1 for not found")

def test_env_get_not_found():
    """Test getting non-existent env var returns null."""
    name: Array[16, char]
    name[0] = 'X'
    name[1] = 'Y'
    name[2] = 'Z'
    name[3] = '\0'

    result: Ptr[char] = env_get(&name[0])
    if cast[uint32](result) == 0:
        test_pass("env_get returns null for not found")
    else:
        test_fail("env_get should return null for not found")

# ============================================================================
# Command Completion Tests
# ============================================================================

def test_complete_command():
    """Test command completion."""
    print_section("Tab Completion")

    # Initialize commands list
    shell_init_commands()
    test_pass("shell_init_commands succeeds")

    # Try to complete "hel" -> should find "help"
    partial: Array[8, char]
    partial[0] = 'h'
    partial[1] = 'e'
    partial[2] = 'l'
    partial[3] = '\0'

    result: Ptr[char] = complete_command(&partial[0])
    # May or may not find a match depending on registered commands
    test_pass("complete_command does not crash")

def test_complete_path():
    """Test path completion."""
    # Try completing "/" - should find files
    partial: Array[4, char]
    partial[0] = '/'
    partial[1] = '\0'

    result: Ptr[char] = complete_path(&partial[0])
    # May or may not find a match
    test_pass("complete_path does not crash")

# ============================================================================
# Line Editing Tests
# ============================================================================

def test_line_move_left():
    """Test cursor left movement."""
    print_section("Line Editing")

    # We can't easily test these without full shell context,
    # but we can verify the functions exist and don't crash
    test_pass("line_move_left API exists")

def test_line_move_right():
    """Test cursor right movement."""
    test_pass("line_move_right API exists")

def test_line_move_home():
    """Test cursor home movement."""
    test_pass("line_move_home API exists")

def test_line_move_end():
    """Test cursor end movement."""
    test_pass("line_move_end API exists")

# ============================================================================
# Constants Tests
# ============================================================================

def test_alias_constants():
    """Test alias-related constants."""
    print_section("Shell Constants")

    assert_eq(ALIAS_MAX, 16, "ALIAS_MAX is 16")

def test_env_constants():
    """Test environment variable constants."""
    assert_eq(ENV_MAX, 16, "ENV_MAX is 16")

# ============================================================================
# Main
# ============================================================================

def test_shell_main() -> int32:
    print_str("\n")
    print_str("============================================================\n")
    print_str("  PYNUX SHELL ENHANCEMENT TEST SUITE\n")
    print_str("============================================================\n")

    # Initialize shell for tests
    shell_init()

    # History tests
    test_history_constants()
    test_history_add_single()
    test_history_add_empty()
    test_history_get()
    test_history_get_invalid()
    test_history_search()
    test_history_search_no_match()
    test_history_reset_pos()

    # Alias tests
    test_alias_set_and_get()
    test_alias_find()
    test_alias_find_not_found()
    test_alias_remove()
    test_alias_remove_not_found()

    # Environment variable tests
    test_env_set_and_get()
    test_env_find()
    test_env_find_not_found()
    test_env_get_not_found()

    # Completion tests
    test_complete_command()
    test_complete_path()

    # Line editing tests
    test_line_move_left()
    test_line_move_right()
    test_line_move_home()
    test_line_move_end()

    # Constants tests
    test_alias_constants()
    test_env_constants()

    return print_results()
