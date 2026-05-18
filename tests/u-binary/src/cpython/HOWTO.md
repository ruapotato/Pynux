# u_cpython build notes

U41 ships `tests/u-binary/u_cpython` -- a fully-static CPython 3.11.x
interpreter that runs on Hamnix's U-track Linux ABI. This file
explains how the binary is built so the next agent can rebuild,
upgrade to a newer 3.x, or swap in a musl-linked variant.

## Why CPython (and not just MicroPython)?

U39 shipped MicroPython 1.22.0 (~900 KB) as the proof-of-concept
that Hamnix's Linux ABI is wide enough to host a real Python
interpreter. MicroPython, however, is NOT what `apt install python3`
delivers -- it implements a strict subset of Python 3, ships almost
none of the stdlib, and exercises a narrower syscall surface.

U41 raises the bar to **CPython** -- the same upstream interpreter
Debian packages and the same binary that runs every pip-installed
package, every Django site, every `python3 manage.py runserver` you
ever cared about. The fully-static build:

- Statically links libc, libm, libpthread, libdl, libutil into one
  ELF -- no dynamic linker required, no shared objects to ship.
- **Freezes the bootstrap stdlib into the binary's data segment**
  via CPython's `Tools/scripts/freeze_modules.py`. After this commit
  the binary contains `encodings.*`, `collections.*`, `enum`,
  `keyword`, `re`, `functools`, etc. as `unsigned char[]` arrays
  produced by the upstream `_freeze_module` tool. CPython's
  importlib finds them via the `<frozen>` loader — no filesystem
  lookup needed.
- Lands at ~7.9 MB stripped (vs ~29 MB unstripped, vs ~5.7 MB for
  the pre-freeze build, vs ~900 KB MicroPython). The +2.2 MB
  stripped overhead buys complete self-containment: drop the
  binary into any namespace and `-c "print(...)"` just runs.
- Exercises a much wider syscall surface than MicroPython:
  `getrandom`, `clock_nanosleep`, `prlimit64`, `fstatat`,
  `readlinkat`, `mprotect`, plus the same brk/mmap/futex set as
  MicroPython. This is the surface `apt-installable Python apps`
  routinely walk.

## What's actually in `u_cpython`?

The committed binary is CPython 3.11.10's `python` interpreter,
linked `-static` (NOT `-static-pie` -- see below). Built from
upstream python.org tarball with:

```
# 1. Patch Tools/scripts/freeze_modules.py to widen the FROZEN list:
#    add <encodings.*> + the site.py / eval-loop support modules.
#    The Makefile's `freeze-patch` target does this idempotently.
make -C tests/u-binary/src/cpython freeze-patch

# 2. Regenerate Makefile.pre.in + Python/frozen.c from the patched
#    spec, then re-run configure so Makefile picks up the new
#    FROZEN_FILES_OUT list.
python3.11 Tools/scripts/freeze_modules.py

# 3. Configure + build as before.
CFLAGS="-fPIC" ./configure \
    --disable-shared \
    --without-pymalloc-debug \
    --without-doc-strings \
    --disable-test-modules \
    LDFLAGS="-static"
make -j$(nproc)
strip --strip-all python
```

The `tests/u-binary/src/cpython/Makefile` orchestrates all three
steps via `make install`. `freeze-patch` is idempotent — re-running
it on an already-patched tree is a no-op.

The interpreter implements full Python 3.11 semantics. The `-c
"print('hello from CPython on Hamnix')"` invocation in the U41 test
exercises:

- ELF static load + page-in (U5, U10, U14).
- glibc-static crt1 startup (U18, U19).
- `set_tid_address`, `arch_prctl(ARCH_SET_FS)`, `set_robust_list`,
  `rseq`, `prlimit64` -- the standard glibc-static init prelude.
- `brk(NULL)` / `brk(end)` for the Python heap (now per-task brk
  thanks to M16.104 -- the MicroPython-era workaround of
  `-X heapsize=64k` is unnecessary here).
- `mmap(anon, RW)` for stdlib import + bytecode + object arenas.
- `getrandom(buf, 16, 0)` for `hash randomization` + `os.urandom`
  seeding.
- `openat(AT_FDCWD, "/proc/self/exe", O_RDONLY)` and
  `readlinkat(AT_FDCWD, "/proc/self/exe", ...)` for sys.executable.
- `clock_gettime(CLOCK_MONOTONIC, ...)` for the interpreter's
  startup timer.
- `write(1, "hello from CPython on Hamnix\n", 29)` -- the actual
  success marker.
- `exit_group(0)` -- normal interpreter teardown.

CPython does NOT use io_uring on the boot path. epoll-based async
runs through `_asyncio` which is lazy-loaded; the boot path of
`-c "print(...)"` doesn't touch it. So the `-ENOSYS` triage for
U41 should be MUCH shorter than the MicroPython HOWTO predicted.

## Why `-static`, not `-static-pie`?

Debian trixie's stock libpython3.13.a is built without -fPIC, which
breaks `gcc -static-pie -lpython3.13`. We sidestep that by building
CPython entirely from upstream source, with our own CFLAGS=-fPIC --
but a few internal CPython objects (e.g. `_freeze_module`,
`Modules/_freeze_module.o`, and Modules/_decimal/libmpdec/*) still
end up with R_X86_64_32 relocations that `-static-pie` rejects.
Plain `-static` accepts them.

Hamnix's ELF loader handles BOTH plain `-static` (ET_EXEC) and
static-pie (ET_DYN, INTERP=NULL). U19 lit the static-pie path; the
ET_EXEC path lit at U5 long before that. So `-static` is the
operationally simpler choice here.

If a future agent needs static-pie (for ASLR inside Hamnix, or to
match the U39 MicroPython binary's flags), rebuild with:

```
CFLAGS="-fPIC -fPIE" LDFLAGS="-static-pie -fPIE" ./configure ...
```

Expect link failures on the internal `Modules/_freeze_module.o` /
libmpdec objects; either rebuild those objects with `-fPIC` manually,
or apply the upstream patch
[gh-101282](https://github.com/python/cpython/issues/101282) which
adds `-fPIC` to those translation units.

## How to rebuild

```
make -C tests/u-binary/src/cpython clean
make -C tests/u-binary/src/cpython install
```

This will:
1. Download `Python-3.11.10.tar.xz` from python.org (~20 MB).
2. Extract into `build/Python-3.11.10/`.
3. Run `./configure` with the static-flavour flags above.
4. `make -j$(nproc)` -- the slow step. 15-30 min on a modern x86_64
   host; the link is serial so multi-core only helps the compile
   phase.
5. Strip + OSABI-stamp + copy to `tests/u-binary/u_cpython`.

Total disk: ~500 MB in `build/` (source + objects); after a
successful `install` you can `make clean` to reclaim it.

Total wall time: ~15-30 min on a recent (8+ core) x86_64 host.

## Host requirements

- `gcc` (any 9+).
- `make`.
- `libc6-dev` providing `/usr/lib/x86_64-linux-gnu/libc.a` (the
  static-glibc archive). Debian: `apt-get install libc6-dev`.
- `wget` OR `curl` (to fetch the tarball).
- `tar`, `xz-utils`.

The Makefile auto-detects these. If any is missing, it prints a
clear `SKIP` line and exits 0 -- mirrors the U22/U24/U39/U40
pattern so CI in minimal environments keeps moving.

## Troubleshooting

### `-fPIC` error during link

If you see something like

```
relocation R_X86_64_32 against symbol `XYZ' can not be used when
making a PIE object
```

you tried to build with `-static-pie` against an object that wasn't
compiled `-fPIC`. Drop back to plain `-static` (the default in this
Makefile) or audit which `.o` is causing it.

### `ld: cannot find -lcrypt` / `-ldl`

Older Debian releases ship libdl + libcrypt as separate static
archives. Trixie merges them into libc. If you see the error,
either: install `libcrypt-dev` and `libdl-dev`, or pass
`--without-decimal-contextvar` to drop the dependency.

### Build is too slow / fails: ship Makefile only

If the host can't build CPython in a reasonable time, the
Makefile + HOWTO are still valuable -- a future agent on a
properly-configured host can `make install` to produce the
staged binary without touching anything else. The U41 test
script SKIPs cleanly if `tests/u-binary/u_cpython` is missing,
the same way U22/U24/U39/U40 do.

## Syscall surface CPython actually hit

Run the U41 test:

```
bash scripts/test_u41_cpython.sh
```

Grep the captured log for `linux_u: ENOSYS nr=N` lines. Each
distinct N is a syscall CPython invoked that Hamnix's U-track
hasn't bound to a real body yet. Cross-reference against
the Linux syscall table (`arch/x86/entry/syscalls/syscall_64.tbl`
in upstream Linux source). Most of CPython's `-ENOSYS` hits on
the `-c "print(...)"` boot path are tolerable:

- `epoll_create1` (291), `epoll_ctl` (233), `epoll_wait` (232) --
  CPython falls back to `select(2)`.
- `set_robust_list` (273) -- glibc-static prologue, no-op safe.
- `rseq` (334) -- restartable sequences, no-op safe.
- `prlimit64` (302) -- already handled at U18.

The U41 test does NOT fix any missing syscalls; that's deferred
to a follow-up agent batching the cd-validation agent's syscall.ad
work. See TODO.md.

## How to upgrade to CPython 3.12 / 3.13

Bump `PY_VERSION` in the Makefile. CPython's `--disable-shared`
+ `LDFLAGS=-static` story is stable across the 3.x line. Note:
3.12 introduced `_PyRuntime`-driven init that touches more of the
syscall surface during startup; expect a couple new `-ENOSYS` hits
when you bump.

## Frozen-modules build (this commit)

CPython's interpreter init unconditionally imports the `encodings`
package + `encodings.utf_8` (plus `codecs`, `io`, `abc`,
`_collections_abc`, `_weakrefset`, `types`, `os`, `posixpath`,
`genericpath`, `enum`, `stat`, `_sitebuiltins`, `site`) before it
hits the eval loop. Without them, CPython aborts during
`init_fs_encoding`:

```
Fatal Python error: init_fs_encoding: failed to get the Python codec
of the filesystem encoding
ModuleNotFoundError: No module named 'encodings'
```

The previous approach (commit `86b6b09`) embedded the upstream
`Lib/` tree into the initramfs at `/usr/lib/python3.11/` via
`HAMNIX_EMBED_PYLIB`. That worked in principle but blew through
`fs/cpio.ad`'s `NR_FILES=192` cap (the full Lib/ tree is ~1828 .py
files), and the resulting `fs/initramfs_blob.S` weighed ~190 MiB —
well over GitHub's 100 MiB push limit on the assembly file.

**This commit replaces the embedding path with CPython's own
frozen-modules machinery.** We patch
`Tools/scripts/freeze_modules.py` to widen the FROZEN spec list:

```python
('stdlib - startup, without site (python -S)', [
    'abc',
    'codecs',
    '<encodings.*>',   # was commented out upstream
    'io',
]),
('stdlib - startup, with site', [
    ...                # upstream set
    '_weakrefset',     # new from here down
    'types',
    'enum',
    'keyword',
    'reprlib',
    'operator',
    'functools',
    '<collections.*>',
    'copyreg',
    'token',
    'tokenize',
    'linecache',
    'traceback',
    'warnings',
    'contextlib',
    'heapq',
    'weakref',
    'inspect',
]),
```

`make regen-frozen` walks each entry, calls `_freeze_module` to
marshal the `.py` source to `.pyc`, and emits a `Python/frozen_modules/
<name>.h` containing the bytecode as `unsigned char[]`. Those headers
are then linked into `python` as static data via `Python/frozen.c`.

At import time, CPython's `_frozen_importlib` looks each module up
in the in-binary frozen table BEFORE walking `sys.path`. Result:
`encodings.utf_8` etc. resolve from the binary itself, with no
filesystem lookup. The `/usr/lib/python3.11/` tree is no longer
needed.

### Verification

```
PYTHONHOME=/nonexistent PYTHONPATH= ./python -c "print('test')"
# -> test
```

If that prints `test`, the frozen build is self-contained. If it
fails with `ModuleNotFoundError`, the FROZEN list is missing a
transitively-imported module — either widen the list (re-run
`make regen-frozen && make`) or accept a narrower test.

### Size cost

| build              | unstripped | stripped |
|--------------------|-----------:|---------:|
| pre-freeze (5.7MB) | ~25 MB     | ~5.7 MB  |
| frozen (this)      | ~29 MB     | ~7.9 MB  |

The +2.2 MB stripped overhead is the bytecode of the additional
frozen modules. The initramfs `fs/initramfs_blob.S` is back to its
small baseline size (~18 MiB).

### Follow-ups (deferred)

- **Strip more.** `_weakrefset`, `keyword`, `token`, etc. are
  small but `<collections.*>` + `<encodings.*>` together account
  for most of the +2.2 MB. If size matters more than module
  coverage, the encodings package can be trimmed to just
  `ascii`, `latin_1`, `utf_8`, `aliases`, `__init__` — that's
  ~80% of the encodings cost.
- **--enable-optimizations.** PGO + LTO would shave another ~5%
  and speed up the interpreter, but lengthens the build from
  ~5 min to ~25 min. Not enabled by default; add the flag in
  the Makefile if a future agent wants it.

## Files

- `Makefile` -- this build.
- `HOWTO.md` -- this file.
- `build/` -- gitignored; holds the source tarball + build tree.
- `../../u_cpython` -- gitignored; the staged binary (host-built).
