---
name: project-m16-state
description: "Snapshot of the bare-metal Hamnix kernel as of M16.66 (ext4 r/w + tmpfs unlink + ~25 user binaries + /proc enriched)"
metadata: 
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

State of the bare-metal Hamnix kernel as of 2026-05-15, last
commit bf3c9c4 (M16.66). Verify against the actual code before
relying on this — milestone summaries decay fast.

**Boot path:** QEMU multiboot1 → arch/x86/boot/header.S → long
mode → start_kernel in init/main.ad. Real-hardware boot (BIOS or
UEFI) is not implemented yet.

**Kernel features in place** (after M16.55..M16.66):
  - Per-task PML4 + CR3 switching, 4 task slots, round-robin
    scheduler driven by the LAPIC timer at 100 Hz.
  - SYSCALL/SYSRET with per-task kernel stacks via TSS.RSP0.
  - Pipes, signals (SIGINT via Ctrl-C), dup/dup2, multi-stage
    pipelines.
  - CWD per task; relative paths normalized for . and ..
  - Block layer (`kernel/block/blk.ad`) with BlockDeviceOps
    vtable. READ and WRITE both wired (M16.60). Backed by ramdisk
    (brd) or virtio-blk-pci (VIRTIO_BLK_T_OUT supported).
  - FAT32 r/o (M16.43..46): BPB parse, FAT chain walk, multi-
    component path lookup, subdir traversal, listdir.
  - EXT4 read-write (M16.51..64):
    * Superblock parse (32/64-byte group descriptors)
    * Inode read/write (256-byte inodes, sector RMW)
    * Index extents — eh_depth > 0 walked (M16.58)
    * 48-bit physical addresses (ee_start_hi / ei_leaf_hi)
    * Multi-block directory walks (M16.59)
    * Block bitmap allocator + free (M16.61)
    * Inode bitmap allocator + free (M16.62)
    * file create — alloc inode + alloc block + write inode +
      splice dirent (M16.63)
    * vfs_open_write routes /ext/* through ext4_open_create_or_
      trunc; file body RMW via ext4_write_open_file (M16.64)
    NOT yet: extent extension past one block, dir-block extension
    when no slack, ext4 unlink, group desc free-count maintenance.

**Filesystem mount layout:**
  /              VFS root (paths only)
  /proc/*        procfs (M16.65 adds meminfo, cpuinfo, mounts on
                 top of version, uptime, tasks)
  /tmp/*         tmpfs (in-memory, writable, up to 8 files; M16.65
                 adds tmpfs_unlink for /rm)
  /mnt/*         FAT32 (ram0 OR virtio-blk vda if FAT)
  /ext/*         EXT4 r/w (virtio-blk vda if non-FAT)

**Userland binaries** (25+, all Adder-authored except marked):
  Original (pre-M16.57):
    /hamsh /init /hello /stdin_demo /pyhello
    /echo /cat /ls /pwd /ps /dup_demo
  M16.57: /head /wc /grep
  M16.65: /rm /touch /mkdir (mkdir is no-op stub — tmpfs is flat)
  M16.66: /seq /uname /true /false /yes /sleep /sort /tee /rev

**Syscalls (0..22):**
  putc, exit, get_jiffies, clone, getpid, open, read, close,
  write, lseek, execve, spawn, waitpid, open_write, pipe, kill,
  dup, dup2, listdir, chdir, getcwd, unlink (M16.65), mkdir
  (M16.65, no-op).

**Compiler state:** unchanged from M16.54 — hand-written x86_64
codegen, no LLVM. Stack-arg params past 6 (M16.50). merge_programs
collision-loud (M16.40). outw/inw intrinsics. NO type aliases. NO
method-call-on-struct-field; use uint64-cast-to-Ptr[uint8] indirect-
call idiom.

**Integration tests** (19, all sequential-pass; parallel-agent
QEMU runs sometimes collide on build/disk.img lock — not a real
regression). Added since M16.54:
  test_blkwrite (M16.60: virtio-blk + brd write round-trip)
  test_ext4 expanded with bitmap, create, shell-write assertions.

**Where the next milestone goes:**
  - ext4 unlink (free inode + free block + clear dirent)
  - ext4 file extension past one block (alloc new extent)
  - directory mkdir for ext4 (alloc dir inode + initial dirent block
    with . and ..)
  - PS/2 keyboard driver for real-hardware boot (UART-only today)
  - UEFI boot stub — still the big install-roadmap rock.

Related: [[project-install-roadmap]] for the ext4 write
decomposition. [[project-m16-boot]] for the multiboot1 path UEFI
will replace.
