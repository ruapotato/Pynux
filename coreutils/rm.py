# rm - remove files

from lib.io import print_str
from kernel.ramfs import ramfs_delete, ramfs_exists, ramfs_isdir

def rm(path: Ptr[char], recursive: bool) -> int32:
    if not ramfs_exists(path):
        print_str("rm: cannot remove '")
        print_str(path)
        print_str("': No such file or directory\n")
        return 1

    if ramfs_isdir(path) and not recursive:
        print_str("rm: cannot remove '")
        print_str(path)
        print_str("': Is a directory\n")
        return 1

    result: int32 = ramfs_delete(path)
    if result < 0:
        print_str("rm: cannot remove '")
        print_str(path)
        print_str("'\n")
        return 1

    return 0

def rmdir(path: Ptr[char]) -> int32:
    if not ramfs_exists(path):
        print_str("rmdir: cannot remove '")
        print_str(path)
        print_str("': No such file or directory\n")
        return 1

    if not ramfs_isdir(path):
        print_str("rmdir: failed to remove '")
        print_str(path)
        print_str("': Not a directory\n")
        return 1

    result: int32 = ramfs_delete(path)
    if result < 0:
        print_str("rmdir: failed to remove '")
        print_str(path)
        print_str("': Directory not empty\n")
        return 1

    return 0

def main() -> int32:
    return 0
