# cat - concatenate and print files

from lib.io import print_str, print_newline, uart_putc, uart_getc
from kernel.ramfs import ramfs_read, ramfs_exists, ramfs_size, ramfs_isdir

def cat_stdin():
    # Read and echo until Ctrl+D (0x04)
    while True:
        c: char = uart_getc()
        if c == '\x04':  # EOF (Ctrl+D)
            break
        uart_putc(c)
        if c == '\r':
            uart_putc('\n')

def cat_file(path: Ptr[char]) -> int32:
    if not ramfs_exists(path):
        print_str("cat: ")
        print_str(path)
        print_str(": No such file or directory\n")
        return 1

    if ramfs_isdir(path):
        print_str("cat: ")
        print_str(path)
        print_str(": Is a directory\n")
        return 1

    size: int32 = ramfs_size(path)
    if size <= 0:
        return 0  # Empty file

    # Allocate buffer and read
    buf: Array[4096, uint8]
    bytes_read: int32 = ramfs_read(path, &buf[0], size)

    if bytes_read > 0:
        i: int32 = 0
        while i < bytes_read:
            uart_putc(cast[char](buf[i]))
            i = i + 1

    return 0

def cat(argc: int32, argv: Ptr[Ptr[char]]) -> int32:
    if argc == 0:
        cat_stdin()
        return 0

    result: int32 = 0
    i: int32 = 0
    while i < argc:
        r: int32 = cat_file(argv[i])
        if r != 0:
            result = r
        i = i + 1

    return result

def main() -> int32:
    print_str("cat: reading from UART (Ctrl+D to end)\n")
    cat_stdin()
    return 0
