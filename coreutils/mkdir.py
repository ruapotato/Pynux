# mkdir - create directories

from lib.io import print_str
from kernel.ramfs import ramfs_create, ramfs_exists

def mkdir(path: Ptr[char]) -> int32:
    if ramfs_exists(path):
        print_str("mkdir: cannot create directory '")
        print_str(path)
        print_str("': File exists\n")
        return 1

    result: int32 = ramfs_create(path, True)
    if result < 0:
        print_str("mkdir: cannot create directory '")
        print_str(path)
        print_str("'\n")
        return 1

    return 0

def main() -> int32:
    return 0
