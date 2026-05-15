# Pynux M10.1: /dev/pynuxzero — clone of /dev/zero.
#
# Each read fills the user buffer with NUL bytes via memset on a
# stack chunk + _copy_to_user. dd if=/dev/pynuxzero bs=1024 count=1
# returns 1024 zeros.

extern def __register_chrdev(major: uint32, baseminor: uint32,
                             count: uint32, name: Ptr[char],
                             fops: Ptr[uint8]) -> int32
extern def __unregister_chrdev(major: uint32, baseminor: uint32,
                               count: uint32, name: Ptr[char])
extern def memset(dst: Ptr[uint8], v: int32, n: uint64) -> Ptr[uint8]
extern def _copy_to_user(to: Ptr[char], from_buf: Ptr[uint8],
                         n: uint64) -> uint64
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


MAJOR_NUM: uint32 = 242
CHUNK:     uint64 = 256

pynux_zero_fops: FileOps


def pynux_zero_read(file: Ptr[uint8], ubuf: Ptr[char], count: uint64,
                    ppos: Ptr[uint8]) -> int64:
    want: uint64 = count
    if want > CHUNK:
        want = CHUNK
    tmp: Array[256, uint8]
    memset(&tmp, 0, want)
    if _copy_to_user(ubuf, &tmp, want) != 0:
        return -14
    return want


def init_module() -> int32:
    pynux_zero_fops.read = pynux_zero_read
    rc: int32 = __register_chrdev(MAJOR_NUM, 0, 1, "pynuxzero",
                                  &pynux_zero_fops)
    _printk("[ZERO] register rc = %d\n", rc)
    return rc


def cleanup_module():
    __unregister_chrdev(MAJOR_NUM, 0, 1, "pynuxzero")
    _printk("[ZERO] unregistered\n", 0)
