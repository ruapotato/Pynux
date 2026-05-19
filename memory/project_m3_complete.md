---
name: project-m3-complete
description: M3 sub-milestones shipped — Pynux /proc entry and Pynux-driven block device. M3.3/M3.4 deferred.
metadata: 
  node_type: memory
  type: project
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

As of 2026-05-14, M3.1 and M3.2 are complete (see [[project-m2-complete]]).
M3.3 (ramfs) and M3.4 (virtio-blk) are scoped but deferred to a future
session.

**What landed:**
- `kernel-modules/m3-proc/` — `/proc/pynux/state` whose read callback is a
  pure-Pynux `pynux_proc_show` writing via `seq_write`. Userspace `cat`
  hits Pynux code. Uses `single_open` + `seq_read`/`seq_lseek`/`single_release`
  wired into `struct proc_ops`.
- `kernel-modules/m3-disk/` — `/dev/pynuxdisk` 8-MiB block device.
  `submit_bio` is implemented in Pynux. Bytes-moving is currently a no-op
  (calls `bio_endio`) — promotes to a real bvec walk in a follow-up.
  Visible in `/proc/partitions`.

**Why this matters:** every kernel surface Pynux has touched so far
(printk console, procfs entry, block device) has been the canonical
registration pattern: mirror a kernel struct, populate fields
imperatively in init_module, call register/add helper, hook
callbacks. The pattern is reliable enough that future modules should
follow it without re-deriving anything.

**How to apply / gotchas baked in:**
- Many kernel symbols userspace knows as `xxx()` are actually
  `__xxx()` underneath: `blk_alloc_disk`/`add_disk` are macros that
  wrap `__blk_alloc_disk` and `device_add_disk`. Always check
  `include/linux/*.h` before declaring an extern — what you grep for
  may not be a real symbol.
- A `gendisk` with `major == 0` MUST have `minors == 0` too (the
  dynamic-major path uses the extended minor allocator). Setting
  minors=1 with major=0 emits a WARN at `block/genhd.c:439` and
  `device_add_disk` fails silently — partition table won't show the
  disk. Easy missable.
- Setting up a procfs entry with `single_open` is not enough — you
  also need `seq_read`, `seq_lseek`, `single_release` wired through
  `proc_ops` or the read returns zero bytes.
- Writing into kernel-allocated structs from Pynux (e.g. gendisk
  fields) — since we can't declare a Pynux class matching that struct
  cleanly (the kernel allocated it, we just have a Ptr[uint8]) — use
  `memcpy(disk + offset, &local, size)`. Pointer arithmetic on
  `Ptr[uint8]` works in current Pynux because the integer + integer
  semantics happen to compose right.

**No new compiler features were needed for M3.** Everything ran on the
M2-era codegen. This is in stark contrast to M2.0..M2.4 which roughly
tripled the codegen.

**M3.3 fully landed** (real read/write filesystem):
- `kernel-modules/m3-fs/` — a `pynuxfs` filesystem with full I/O:
  `mount -t pynuxfs`, `touch`/`echo > file`/`cat file`,
  `mkdir`/`rmdir`, `rm`, `umount` all work. The Pynux module mirrors
  `fs/ramfs/inode.c` for file_system_type, fs_context_operations,
  super_operations, inode_operations (both directory + file variants),
  file_operations, plus `fill_super`, `ramfs_mknod`, `ramfs_create`,
  `ramfs_mkdir`, and the root-inode setup.
- **Key win**: discovered `ram_aops` is exported by libfs and already
  wires up `simple_read_folio` / `simple_write_begin` / `simple_write_end`
  / `noop_dirty_folio`. Just point `inode->i_mapping->a_ops` at it; no
  custom address_space_operations struct needed. Saves ~50 LoC.
- **`dget` workaround**: `dget` is a static inline that calls
  `lockref_get(&dentry->d_lockref)`. We declare `lockref_get` extern and
  call it with `dentry + 128` (the d_lockref offset). Necessary to keep
  ramfs files pinned in the dcache.
- Small compiler fix landed in passing: `gen_data` now constant-folds
  `-LITERAL` for negative-int globals (e.g. `ENOSPC_NEG: int32 = -28`),
  since `-` is a unary operator and an IntLiteral can't be negative
  directly.

**Still deferred (M3.4 virtio-blk):**
- virtqueue + scatter-gather + IRQ handler + blk-mq tag set. Multi-session.
- Compiler likely still does not need new features. What's needed is
  patience and probing.

See [[project-m1-complete]] [[project-m2-complete]] for prior state.
