# Pynux RAM Filesystem Tests
#
# Tests for file creation, reading, writing, and directory operations.

from lib.io import print_str, print_int, print_newline
from lib.string import strcmp, strlen
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_gt, test_pass, test_fail)
from kernel.ramfs import (ramfs_init, ramfs_create, ramfs_delete, ramfs_exists,
                           ramfs_read, ramfs_write, ramfs_append, ramfs_size,
                           ramfs_isdir, ramfs_lookup, ramfs_readdir)

# ============================================================================
# File Creation Tests
# ============================================================================

def test_create_file():
    """Test basic file creation."""
    print_section("File Creation")

    # Create a simple file
    result: int32 = ramfs_create("/test_file.txt", False)
    assert_gte(result, 0, "create file returns success")

    # File should exist
    exists: bool = ramfs_exists("/test_file.txt")
    assert_true(exists, "created file exists")

    # Should not be a directory
    is_dir: bool = ramfs_isdir("/test_file.txt")
    assert_false(is_dir, "file is not directory")

    # Clean up
    ramfs_delete("/test_file.txt")

def test_create_directory():
    """Test directory creation."""
    result: int32 = ramfs_create("/test_dir", True)
    assert_gte(result, 0, "create directory returns success")

    exists: bool = ramfs_exists("/test_dir")
    assert_true(exists, "created directory exists")

    is_dir: bool = ramfs_isdir("/test_dir")
    assert_true(is_dir, "directory is marked as directory")

    ramfs_delete("/test_dir")

def test_create_nested():
    """Test creating nested files."""
    # Create parent directory
    ramfs_create("/parent", True)

    # Create file in directory
    result: int32 = ramfs_create("/parent/child.txt", False)
    assert_gte(result, 0, "create nested file")

    exists: bool = ramfs_exists("/parent/child.txt")
    assert_true(exists, "nested file exists")

    # Clean up
    ramfs_delete("/parent/child.txt")
    ramfs_delete("/parent")

def test_create_duplicate():
    """Test creating duplicate files."""
    ramfs_create("/dup_test", False)

    # Try to create again - should fail or return existing
    result: int32 = ramfs_create("/dup_test", False)
    # Behavior depends on implementation - just verify no crash
    test_pass("duplicate create doesn't crash")

    ramfs_delete("/dup_test")

# ============================================================================
# File Read/Write Tests
# ============================================================================

def test_write_read():
    """Test basic file write and read."""
    print_section("File I/O")

    ramfs_create("/rw_test.txt", False)

    # Write data
    result: int32 = ramfs_write("/rw_test.txt", "Hello World")
    assert_gte(result, 0, "write returns success")

    # Check size
    size: int32 = ramfs_size("/rw_test.txt")
    assert_eq(size, 11, "file size is 11 bytes")

    # Read data
    buf: Array[32, uint8]
    read_len: int32 = ramfs_read("/rw_test.txt", &buf[0], 32)
    assert_eq(read_len, 11, "read returns 11 bytes")

    # Verify content (first few chars)
    matched: bool = (buf[0] == 'H' and buf[1] == 'e' and
                   buf[2] == 'l' and buf[3] == 'l' and
                   buf[4] == 'o')
    assert_true(matched, "content matches 'Hello'")

    ramfs_delete("/rw_test.txt")

def test_overwrite():
    """Test overwriting file content."""
    ramfs_create("/overwrite.txt", False)
    ramfs_write("/overwrite.txt", "First")

    # Overwrite with new content
    ramfs_write("/overwrite.txt", "Second")

    buf: Array[32, uint8]
    read_len: int32 = ramfs_read("/overwrite.txt", &buf[0], 32)

    # Should be "Second" not "First"
    is_second: bool = (buf[0] == 'S' and buf[1] == 'e')
    assert_true(is_second, "content was overwritten")

    ramfs_delete("/overwrite.txt")

def test_append():
    """Test appending to file."""
    ramfs_create("/append.txt", False)
    ramfs_write("/append.txt", "Hello")

    # Append more
    result: int32 = ramfs_append("/append.txt", " World")
    assert_gte(result, 0, "append returns success")

    # Size should be combined
    size: int32 = ramfs_size("/append.txt")
    assert_eq(size, 11, "size after append is 11")

    # Read and verify
    buf: Array[32, uint8]
    ramfs_read("/append.txt", &buf[0], 32)

    # Should be "Hello World"
    matched: bool = (buf[0] == 'H' and buf[5] == ' ' and buf[6] == 'W')
    assert_true(matched, "appended content correct")

    ramfs_delete("/append.txt")

def test_read_nonexistent():
    """Test reading non-existent file."""
    buf: Array[16, uint8]
    read_len: int32 = ramfs_read("/does_not_exist.txt", &buf[0], 16)
    assert_eq(read_len, -1, "read nonexistent returns -1")

def test_partial_read():
    """Test reading part of a file."""
    ramfs_create("/partial.txt", False)
    ramfs_write("/partial.txt", "ABCDEFGHIJ")  # 10 bytes

    buf: Array[5, uint8]
    read_len: int32 = ramfs_read("/partial.txt", &buf[0], 5)
    assert_eq(read_len, 5, "partial read returns 5")

    # Should be first 5 chars
    matched: bool = (buf[0] == 'A' and buf[4] == 'E')
    assert_true(matched, "partial read correct chars")

    ramfs_delete("/partial.txt")

# ============================================================================
# File Deletion Tests
# ============================================================================

def test_delete():
    """Test file deletion."""
    print_section("File Deletion")

    ramfs_create("/to_delete.txt", False)
    ramfs_write("/to_delete.txt", "delete me")

    exists_before: bool = ramfs_exists("/to_delete.txt")
    assert_true(exists_before, "file exists before delete")

    result: int32 = ramfs_delete("/to_delete.txt")
    assert_eq(result, 0, "delete returns success")

    exists_after: bool = ramfs_exists("/to_delete.txt")
    assert_false(exists_after, "file gone after delete")

def test_delete_nonexistent():
    """Test deleting non-existent file."""
    result: int32 = ramfs_delete("/never_existed.txt")
    assert_eq(result, -1, "delete nonexistent returns -1")

# ============================================================================
# Directory Operations Tests
# ============================================================================

def test_directory_listing():
    """Test listing directory contents."""
    print_section("Directory Operations")

    # Create directory with files
    ramfs_create("/listdir", True)
    ramfs_create("/listdir/file1.txt", False)
    ramfs_create("/listdir/file2.txt", False)
    ramfs_create("/listdir/subdir", True)

    # Read directory entries
    name_buf: Array[64, char]
    count: int32 = 0

    # Try to read entries
    idx: int32 = 0
    while idx < 10:
        result: int32 = ramfs_readdir("/listdir", idx, &name_buf[0])
        if result < 0:
            break
        count = count + 1
        idx = idx + 1

    assert_gte(count, 3, "found at least 3 entries")

    # Clean up
    ramfs_delete("/listdir/file1.txt")
    ramfs_delete("/listdir/file2.txt")
    ramfs_delete("/listdir/subdir")
    ramfs_delete("/listdir")

def test_empty_directory():
    """Test empty directory operations."""
    ramfs_create("/emptydir", True)

    is_dir: bool = ramfs_isdir("/emptydir")
    assert_true(is_dir, "empty dir is directory")

    # Should be able to delete empty directory
    result: int32 = ramfs_delete("/emptydir")
    assert_eq(result, 0, "delete empty dir succeeds")

# ============================================================================
# Path Lookup Tests
# ============================================================================

def test_lookup():
    """Test file lookup."""
    print_section("Path Lookup")

    ramfs_create("/lookup_test.txt", False)

    # Lookup should return valid index
    idx: int32 = ramfs_lookup("/lookup_test.txt")
    assert_gte(idx, 0, "lookup returns valid index")

    # Lookup nonexistent should fail
    idx = ramfs_lookup("/not_here.txt")
    assert_eq(idx, -1, "lookup nonexistent returns -1")

    ramfs_delete("/lookup_test.txt")

def test_root_exists():
    """Test that root directory exists."""
    exists: bool = ramfs_exists("/")
    assert_true(exists, "root directory exists")

    is_dir: bool = ramfs_isdir("/")
    assert_true(is_dir, "root is directory")

# ============================================================================
# Intuitive API Tests
# ============================================================================

def test_intuitive_ramfs_api():
    """Test that filesystem API is intuitive."""
    print_section("Intuitive Filesystem API")

    # Creating a file should be straightforward
    result: int32 = ramfs_create("/intuitive.txt", False)
    if result >= 0:
        test_pass("ramfs_create returns >= 0 on success")
    else:
        test_fail("ramfs_create should succeed")
        return

    # exists() should return true for existing file
    if ramfs_exists("/intuitive.txt"):
        test_pass("ramfs_exists returns true for existing")
    else:
        test_fail("ramfs_exists should return true")

    # exists() should return false for non-existing
    if not ramfs_exists("/not_here.txt"):
        test_pass("ramfs_exists returns false for missing")
    else:
        test_fail("ramfs_exists should return false")

    # write should return bytes written or success indicator
    written: int32 = ramfs_write("/intuitive.txt", "test data")
    if written >= 0:
        test_pass("ramfs_write indicates success")
    else:
        test_fail("ramfs_write should succeed")

    # size should return actual file size
    size: int32 = ramfs_size("/intuitive.txt")
    if size == 9:  # "test data" is 9 bytes
        test_pass("ramfs_size returns correct size")
    else:
        test_fail("ramfs_size should return 9")

    # delete should return 0 on success
    del_result: int32 = ramfs_delete("/intuitive.txt")
    if del_result == 0:
        test_pass("ramfs_delete returns 0 on success")
    else:
        test_fail("ramfs_delete should return 0")

    # After delete, should not exist
    if not ramfs_exists("/intuitive.txt"):
        test_pass("file gone after delete")
    else:
        test_fail("file should be gone")

# ============================================================================
# Edge Cases
# ============================================================================

def test_edge_cases():
    """Test edge cases."""
    print_section("Edge Cases")

    # Empty filename
    result: int32 = ramfs_create("", False)
    assert_eq(result, -1, "empty path fails")

    # Just slash
    exists: bool = ramfs_exists("/")
    assert_true(exists, "root exists")

    # Very long content
    ramfs_create("/longfile.txt", False)
    long_data: Array[256, char]
    i: int32 = 0
    while i < 255:
        long_data[i] = 'L'
        i = i + 1
    long_data[255] = '\0'

    result = ramfs_write("/longfile.txt", &long_data[0])
    if result >= 0:
        test_pass("write long content succeeds")
    else:
        test_fail("should handle long content")

    ramfs_delete("/longfile.txt")

# ============================================================================
# Main
# ============================================================================

def test_ramfs_main() -> int32:
    print_str("\n=== Pynux RAM Filesystem Tests ===\n")

    # Initialize filesystem
    ramfs_init()

    test_create_file()
    test_create_directory()
    test_create_nested()
    test_create_duplicate()

    test_write_read()
    test_overwrite()
    test_append()
    test_read_nonexistent()
    test_partial_read()

    test_delete()
    test_delete_nonexistent()

    test_directory_listing()
    test_empty_directory()

    test_lookup()
    test_root_exists()

    test_intuitive_ramfs_api()

    test_edge_cases()

    return print_results()
