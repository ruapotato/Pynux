# tests/linux-modules — Stock Linux 6.12 .ko fixtures for the L-track

This directory holds the **L-track regression fixtures**: stock Linux
6.12.48 kernel modules built with the unmodified upstream kbuild
toolchain. The Hamnix L-track (see `linux_abi/`) is the in-tree work
to make Hamnix's bare-metal kernel ABI-compatible enough that these
fixtures load and run unchanged.

Pinned ABI target: **Linux 6.12.48 LTS** (see `linux_abi/TARGET_ABI.md`).

## Layout

    tests/linux-modules/
    +-- Makefile            Top-level driver (clone / build / install)
    +-- README.md           This file
    +-- linux-6.12.48/      One-time `make linux_tree` artifact (gitignored)
    +-- src/
    |   +-- hello/          L1 minimum-meaningful module (printk only)
    |   +-- slab/           L2 — kmalloc / kfree
    |   +-- proc/           L3 — proc_create / single_open
    |   +-- chrdev/         L4 — register_chrdev / file_operations
    +-- hello.ko            Built artifact, checked in
    +-- slab.ko             (ditto, once L2 lands)
    +-- ...

## Build flow

The flow is **two-phase** so that CI never tries to build a kernel
tree (which would take ~20 minutes and ~15 GB).

### Phase 1: developer machine, one-time

    cd tests/linux-modules
    make linux_tree    # clones v6.12.48, defconfig, BTF on, full build

This produces `linux-6.12.48/vmlinux` plus the headers + Module.symvers
that out-of-tree kbuild needs. Override with `LINUX_TREE=/path/to/tree`
if you already have one staged.

### Phase 2: developer machine, per-fixture

    cd tests/linux-modules
    make modules        # out-of-tree build of every src/<name>/<name>.ko
    make install        # copies src/<name>/<name>.ko up to <name>.ko

The resulting `<name>.ko` is **committed to the repo**. The next
`python3 scripts/build_initramfs.py` run picks it up and embeds it as
`/lib/modules/6.12/<name>.ko` in the cpio image; `scripts/test_l_track.sh`
then loads it inside QEMU via Hamnix's own `insmod`.

### Phase 3: CI

CI runs only `scripts/test_l_track.sh`. It does **not** need a kernel
tree — it consumes the already-committed `<name>.ko` binaries. This
is intentional: the L-track's contract is "the Hamnix kernel loads
these exact bytes." A rebuild of the bytes would be a different test
(of kbuild + the host Linux toolchain) and would belong elsewhere.

## Why .ko binaries are checked in

Checking the `.ko` artifacts in is a deliberate trade-off:

  - **CI stays cheap.** No kernel tree, no Module.symvers, no GCC
    plugin dance. Just run the regression.
  - **The bytes are the contract.** When the L1 loader applies
    `R_X86_64_PC32` to a specific 4-byte slot inside hello.ko, that
    slot's exact value is part of the test. Rebuilding from source
    on every CI run would make a kbuild bump look like an ABI break,
    which it's not.
  - **The fixtures are small** (hello.ko is ~10 KB). The committed
    binaries are dwarfed by `fs/initramfs_blob.S`.

When the pinned ABI advances (see `linux_abi/TARGET_ABI.md`'s "How
to refresh" section), the workflow is:

    cd tests/linux-modules
    make clean
    rm -rf linux-6.12.48 && make linux_tree LINUX_VER=<new>
    make modules && make install
    git add *.ko
    git commit -m "Refresh L-track fixtures against Linux <new>"

## Adding a new fixture

1. Create `src/<name>/<name>.c` (a normal Linux module — `module_init`,
   `module_exit`, `MODULE_LICENSE("GPL")`).
2. Copy `src/hello/Makefile` to `src/<name>/Makefile` and rename
   `hello` → `<name>` inside it.
3. Make the `module_init` printk start with `L<N>: <name>.ko module_init`
   (the L-number is whichever milestone the fixture exercises).
4. From this directory: `make modules && make install`. The Makefile's
   `FIXTURE_DIRS` glob will pick up the new src/<name>/ automatically.
5. Add `<name>` and its marker string to the `MARKERS` table in
   `scripts/test_l_track.sh`.
6. `git add src/<name>/ <name>.ko` and commit. Both the source and
   the binary belong in the tree (see "Why .ko binaries are checked
   in" above).

## Related files

- `linux_abi/loader.ad`        — the L1 loader these fixtures exercise
- `linux_abi/exports.ad`       — symbols visible to loaded modules
- `linux_abi/TARGET_ABI.md`    — the pinned Linux version + refresh policy
- `scripts/test_l_track.sh`    — runs the regression
- `scripts/build_initramfs.py` — embeds *.ko as /lib/modules/6.12/*.ko
