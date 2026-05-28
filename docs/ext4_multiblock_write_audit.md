# ext4 multi-block write audit (M16.64 → present)

Scratch finding while extending vfs_open_write past the single-block cap. Once
the implementation lands and tests pass this file is deleted.

## Single-block writers on the interactive path

The only kernel-side writer that today caps a regular-file `vfs_open_write` at
`ext4_block_size` bytes is **`ext4_write_open_file`** (fs/ext4.ad, ~line 1824).
Its body is "RMW the first data block at offset 0," and it explicitly clamps:

    if pos >= ext4_block_size:
        return 0                                # past single-block cap
    if pos + take > ext4_block_size:
        take = ext4_block_size - pos

The wiring into the VFS is `vfs_write` (fs/vfs.ad ~3731), which calls
`ext4_write_open_file` exactly once per syscall and uses the short-write return
value to advance `task[0].fd_pos[fdu]`. There's no outer block loop in
`vfs_write` — the cap propagates directly to userland.

`ext4_open_create_or_trunc` (fs/ext4.ad ~1784) is the open side. It allocates
one inode + one data block via `ext4_create_file`, which writes an inline-leaf
extent with a single 1-block extent (ee_block=0, ee_len=1). That's the on-disk
starting state for any write-mode open.

## Multi-block writers that already exist

`ext4_blob_save` (fs/ext4.ad ~2734) is the working pattern. It:

  1. Hand-builds an empty depth-0 extent leaf (`eh_entries=0, eh_max=4`).
  2. Loops `lb = 0..nblocks`, for each block:
     * `ext4_alloc_block()` to get a fresh physical block.
     * Fills `ext4_blob_buf` (4 KiB) with a slice of src + zero pad.
     * `_ext4_write_block(nb, ext4_blob_buf)`.
     * `_ext4_extent_append_block(inode, lb, nb)` — coalesces into the last
       extent when `nb` is contiguous, otherwise consumes a fresh extent slot
       (4 slots total before the depth-0 limit is hit).
  3. Stamps `i_size_lo`, `i_blocks_lo`, mtime; writes the inode.
  4. `blk_flush(ext4_blockdev_slot)` for durability.

`ext4_blob_save_at_path` (fs/ext4.ad ~3577) is the same pattern for nested
paths. Both use the existing extent helpers `_ext4_extent_append_block`,
`_ext4_leaf_entries`, `_ext4_inode_block_count`, and `_ext4_extent_trim_to`.
None of these need new code.

## Read path: already block-aware

`ext4_read_file` (fs/ext4.ad ~463) loops blocks via `_ext4_logical_to_physical`,
so as soon as the inode has N extents pointing at N data blocks the read side
will deliver `i_size_lo` bytes correctly. No read-side change is needed.

The fd-level read in `vfs_read` (fs/vfs.ad ~3367) just calls `ext4_read_file`
and advances `fd_pos`, so it inherits multi-block reads for free.

## Userland-side cap

`user/cp.ad:38` has `CAP: uint64 = 8192` — the buffer/file-size limit baked
into the userland cp. After the kernel becomes multi-block, this becomes a
buffer-size choice; the comment at the top of the file should drop the
"silently truncated past 8 KiB" warning, and `copy_file` should loop until
source EOF rather than capping at one buffer fill.

## Strategy chosen

Streaming-extent: extend `ext4_write_open_file` so a write past
`block_count * ext4_block_size` allocates a new physical block, calls
`_ext4_extent_append_block` to grow the inline leaf, and continues the RMW
into the new block. This stays write-through (every write durably hits disk)
and keeps append-as-you-go semantics, matching the existing single-block
behaviour.

Alternative considered: buffer all writes in RAM and flush on close as one
`ext4_blob_save`-style operation. Rejected — it would break append-as-you-go
(a crash before close loses bytes that the writer thought were committed),
and it would require a big per-slot scratch buffer just to handle one growing
file. Streaming-extent reuses every helper that already exists.

## Failure mode at depth-0 leaf-full

With `eh_max=4` and `ee_len` clamped at 32768, a streaming writer can cover
up to 4 * 32768 * 4 KiB = **512 MiB** if every new block happens to be
contiguous with the previous run (`_ext4_extent_append_block` merges those
into ee_len growth without consuming a slot). In the realistic fragmented
case the limit is 4 slots → 4 non-contiguous runs; on our 128 MiB
single-group disk every alloc tends to be near-contiguous so we should
comfortably get tens of MiB per file before hitting the 4-slot ceiling.

When the leaf is full, `_ext4_extent_append_block` returns -1 and
`ext4_write_open_file` returns a short write (the bytes that did fit). That's
the documented escalation point — extent-index-node support is a separate,
larger task.

## Other paths checked for the same assumption

  * **tmpfs writer** (fs/tmpfs.ad / vfs_write FD_TMPFS_MARK): handles
    multi-block files already via `tmpfs_write`. Not affected.
  * **FAT writer** (`fat_write_slot` via FD_FAT_MARK): handles cluster-chain
    growth. Not affected.
  * **`/var/lib/hpm`, log writers**: these all go through tmpfs or the
    distrofs RAM-table snapshot path (`ext4_blob_save`), neither of which is
    capped. No regressions expected.
  * **`ext4_unlink`** (fs/ext4.ad ~1880): already comments "single-block
    files (matches...)". Once a multi-block write lands, unlink needs to
    free EVERY extent's blocks, not just block 0. This is also fixed here.

## Sub-tasks

  1. Extend `ext4_write_open_file` to allocate a new block + append an extent
     when the write spills past the last allocated block.
  2. Stop `ext4_open_create_or_trunc` from pre-allocating a wasted block — a
     fresh-empty file should have `eh_entries=0` and grow naturally on first
     write. (Or: keep the pre-alloc and let writes consume it first; the
     write path already handles "logical block 0 already mapped.")
  3. Teach `ext4_unlink` to walk every extent and free every block, not just
     block 0.
  4. Drop user/cp.ad's 8 KiB cap; copy in a loop until source EOF.
  5. Extend test_cp_r.sh (or add test_ext4_bigfile.sh) to exercise > 8 KiB.
