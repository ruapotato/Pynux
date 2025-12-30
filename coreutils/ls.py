# ls - list directory contents

from lib.io import print_str, print_int, print_newline
from kernel.ramfs import ramfs_lookup, ramfs_readdir, ramfs_size, ramfs_isdir, FTYPE_DIR

def ls(path: Ptr[char], long_format: bool):
    # Check if path exists
    fd: int32 = ramfs_lookup(path)
    if fd < 0:
        print_str("ls: cannot access '")
        print_str(path)
        print_str("': No such file or directory\n")
        return

    # Check if it's a directory
    if not ramfs_isdir(path):
        # It's a file, just print its name
        print_str(path)
        print_newline()
        return

    # List directory contents
    name_buf: Array[32, char]
    index: int32 = 0

    while True:
        result: int32 = ramfs_readdir(path, index, &name_buf[0])
        if result < 0:
            break  # No more entries

        if long_format:
            if result == 1:
                print_str("d ")
            else:
                print_str("- ")
            # Print size (directories show 0)
            # Would need full path to get size...
            print_str("  ")

        print_str(&name_buf[0])
        if result == 1:
            print_str("/")  # Mark directories
        print_newline()

        index = index + 1

    if index == 0:
        # Empty directory
        pass

def main() -> int32:
    ls("/", False)
    return 0
