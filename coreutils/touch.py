# touch - create empty files

from lib.io import print_str
from kernel.ramfs import ramfs_create, ramfs_exists

def touch(path: Ptr[char]) -> int32:
    if ramfs_exists(path):
        # File exists, just return success (touch updates timestamp)
        return 0

    result: int32 = ramfs_create(path, False)
    if result < 0:
        print_str("touch: cannot touch '")
        print_str(path)
        print_str("'\n")
        return 1

    return 0

def main() -> int32:
    return 0
