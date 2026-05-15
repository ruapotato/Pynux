# fs/vfs.py
#
# Mirrors the very smallest meaningful slice of fs/open.c +
# fs/read_write.c + fs/namei.c in Linux: a flat file lookup against a
# baked-in initramfs (no real namespace, no inodes, no dentry cache)
# plus a tiny global file-descriptor table backing sys_open / sys_read
# / sys_close. The "filesystem" itself is the .ascii blobs that
# fs/initramfs_data.S exposes via four accessor functions.
#
# Scope kept deliberately small for M16.21:
#   - read-only (no sys_write)
#   - flat namespace; names match by byte-for-byte strcmp
#   - 4 fd slots, GLOBAL not per-task (the demo uses one task; the
#     fd table becomes per-task when we wire it into task_struct
#     properly in a later milestone)
#   - no positional sys_lseek; sys_read advances pos internally
#
# Even at this size the path through user-mode is honest: a CPL-3
# task issues SYS_OPEN with a string pointer, kernel resolves the
# name to an initramfs entry, returns a small integer the user holds
# onto for subsequent SYS_READ + SYS_CLOSE.

from kernel.printk.printk import printk0, printk1, printk2

extern def initramfs_entry_count() -> uint64
extern def initramfs_entry_name(idx: uint64) -> Ptr[char]
extern def initramfs_entry_data(idx: uint64) -> Ptr[uint8]
extern def initramfs_entry_size(idx: uint64) -> uint64
extern def memcpy(dst: Ptr[uint8], src: Ptr[uint8], n: uint64) -> Ptr[uint8]

NR_FDS: uint64 = 4

# Per-fd state. Two parallel arrays keep the struct layout simple
# (Pynux doesn't yet have inner array fields with sub-quad widths
# that bind reliably in the codegen we care about).
#
#   fd_file_idx[fd] = initramfs file index, or -1 (= 0xFFFFFFFF) when
#                     the slot is closed
#   fd_pos[fd]      = current read position within the file
FD_CLOSED: uint64 = 0xFFFFFFFFFFFFFFFF
fd_file_idx: Array[4, uint64]
fd_pos:      Array[4, uint64]


def vfs_init():
    i: uint64 = 0
    while i < NR_FDS:
        fd_file_idx[i] = FD_CLOSED
        fd_pos[i]      = 0
        i = i + 1


def _strcmp_cstr(a: Ptr[char], b: Ptr[char]) -> int32:
    # Tiny byte-for-byte strcmp. Returns 0 on equality, non-zero
    # otherwise. Both args must be NUL-terminated. We don't bother
    # mimicking glibc's < 0 / > 0 contract — call sites only need
    # the equality bit.
    i: int32 = 0
    while True:
        ca: int32 = a[i]
        cb: int32 = b[i]
        if ca != cb:
            return 1
        if ca == 0:
            return 0
        i = i + 1


def _lookup_name(name: Ptr[char]) -> int32:
    # Linear scan of the initramfs entries. Returns the entry index,
    # or -1 if `name` isn't a baked-in file. Linux's path_lookup goes
    # through dentry / inode caches; M16.21 is intentionally simpler.
    count: uint64 = initramfs_entry_count()
    i: uint64 = 0
    while i < count:
        candidate: Ptr[char] = initramfs_entry_name(i)
        if _strcmp_cstr(name, candidate) == 0:
            return cast[int32](i)
        i = i + 1
    return -1


def _alloc_fd() -> int32:
    i: uint64 = 0
    while i < NR_FDS:
        if fd_file_idx[i] == FD_CLOSED:
            return cast[int32](i)
        i = i + 1
    return -1


def vfs_open(name: Ptr[char]) -> int32:
    # Returns fd >= 0 on success, -1 on lookup miss, -2 on no free fd.
    file_idx: int32 = _lookup_name(name)
    if file_idx < 0:
        return -1
    fd: int32 = _alloc_fd()
    if fd < 0:
        return -2
    fd_file_idx[cast[uint64](fd)] = cast[uint64](file_idx)
    fd_pos[cast[uint64](fd)]      = 0
    return fd


def vfs_read(fd: int32, buf: Ptr[uint8], count: uint64) -> int64:
    if fd < 0:
        return -1
    if cast[uint64](fd) >= NR_FDS:
        return -1
    fdu: uint64 = cast[uint64](fd)
    file_idx: uint64 = fd_file_idx[fdu]
    if file_idx == FD_CLOSED:
        return -1
    size: uint64 = initramfs_entry_size(file_idx)
    pos:  uint64 = fd_pos[fdu]
    if pos >= size:
        return 0                       # EOF
    remaining: uint64 = size - pos
    take: uint64 = count
    if take > remaining:
        take = remaining
    src: Ptr[uint8] = initramfs_entry_data(file_idx)
    memcpy(buf, cast[Ptr[uint8]](cast[uint64](src) + pos), take)
    fd_pos[fdu] = pos + take
    return cast[int64](take)


def vfs_close(fd: int32) -> int32:
    if fd < 0:
        return -1
    if cast[uint64](fd) >= NR_FDS:
        return -1
    fdu: uint64 = cast[uint64](fd)
    if fd_file_idx[fdu] == FD_CLOSED:
        return -1
    fd_file_idx[fdu] = FD_CLOSED
    fd_pos[fdu]      = 0
    return 0
