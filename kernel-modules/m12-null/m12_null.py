# Pynux M12.2: /dev/pynuxnull — clone of /dev/null.
#
# read() returns 0 (EOF) immediately. write() returns the request size,
# silently consuming whatever was sent. Pairs with M5.1 /dev/pynux,
# M8.1 /dev/pynurand, M10.1 /dev/pynuxzero to round out the basic
# Pynux character-device trio.

extern def __register_chrdev(major: uint32, baseminor: uint32,
                             count: uint32, name: Ptr[char],
                             fops: Ptr[uint8]) -> int32
extern def __unregister_chrdev(major: uint32, baseminor: uint32,
                               count: uint32, name: Ptr[char])
extern def _printk(fmt: str, val: int32) -> int32


class FileOps:
    owner: Ptr[uint8]
    fop_flags: Array[8, uint8]
    llseek: Ptr[uint8]
    read: Ptr[uint8]
    write: Ptr[uint8]
    read_iter: Ptr[uint8]
    write_iter: Ptr[uint8]
    pad1: Array[40, uint8]
    mmap: Ptr[uint8]
    pad2: Array[24, uint8]
    fsync: Ptr[uint8]
    pad3: Array[16, uint8]
    get_unmapped_area: Ptr[uint8]
    pad4: Array[16, uint8]
    splice_write: Ptr[uint8]
    splice_read: Ptr[uint8]
    pad_end: Array[72, uint8]


MAJOR_NUM: uint32 = 243

pynux_null_fops: FileOps
pynux_null_written: int64


def pynux_null_read(file: Ptr[uint8], ubuf: Ptr[char], count: uint64,
                    ppos: Ptr[uint8]) -> int64:
    return 0     # EOF


def pynux_null_write(file: Ptr[uint8], ubuf: Ptr[char], count: uint64,
                     ppos: Ptr[uint8]) -> int64:
    pynux_null_written = pynux_null_written + count
    return count


def init_module() -> int32:
    pynux_null_fops.read = pynux_null_read
    pynux_null_fops.write = pynux_null_write
    rc: int32 = __register_chrdev(MAJOR_NUM, 0, 1, "pynuxnull",
                                  &pynux_null_fops)
    _printk("[NULL] register rc = %d\n", rc)
    return rc


def cleanup_module():
    __unregister_chrdev(MAJOR_NUM, 0, 1, "pynuxnull")
    # Truncate to int32 for printk %d; demo writes are tiny anyway.
    written32: int32 = pynux_null_written
    _printk("[NULL] bytes consumed = %d\n", written32)
    _printk("[NULL] unregistered\n", 0)
