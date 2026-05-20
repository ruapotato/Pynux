# u_cpython build notes

U41 ships `tests/u-binary/u_cpython` -- a static-PIE (ET_DYN) CPython
3.11.x interpreter, built against **musl**, that runs on Hamnix's
U-track Linux ABI. This file explains how the binary is built so the
next agent can rebuild or upgrade to a newer 3.x.

## TL;DR — the build that works

```
make -C tests/u-binary/src/cpython install
```

produces an `ET_DYN`, statically-linked, **no-PT_INTERP** CPython.
The exact commands the Makefile runs:

```
# fetch + extract Python-3.11.10.tar.xz from python.org

# patch the generated configure: trust the compiler-probe triplet
# (Alpine-style) so musl-gcc does not abort the platform-triplet check

# patch Tools/scripts/freeze_modules.py: widen the FROZEN list with
# <encodings.*>, <collections.*>, enum, functools, ... (see below)

cd build/Python-3.11.10
CC="musl-gcc" CXX="musl-gcc" CFLAGS="-fPIE" LDFLAGS="-static-pie" \
    ./configure --disable-shared --without-pymalloc-debug \
    --without-doc-strings --disable-test-modules --with-system-libmpdec
make -j$(nproc)
make regen-frozen          # bakes the widened FROZEN headers
make -j$(nproc)            # re-link with the frozen headers compiled in
strip --strip-all python
# stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3) -> ../../u_cpython
```

Result: `ELF 64-bit LSB pie executable, static-pie linked`,
`Type: DYN`, **0** `R_X86_64_TPOFF64` relocations, ~9.3 MB stripped.

## Why musl static-PIE (NOT glibc `-static`)?

Hamnix's ELF loader (`fs/elf.ad`) overlays an ET_EXEC binary's
fixed-address LOAD range into the spawned task's PML4. CPython linked
glibc-`-static` is an **ET_EXEC at 0x400000** — that range collides
with Hamnix's ~12 MiB identity-mapped kernel image, and commit
`653d962` added a kernel-image collision guard that **refuses** such a
binary (`-ENOEXEC`). Only **ET_DYN** (static-PIE) binaries run: they
load at Hamnix's identity-mapped load region with no fixed overlay.
The working U39 MicroPython fixture is exactly this shape.

A glibc **`-static-pie`** build of CPython 3.11 *links* cleanly (the
old HOWTO's fear of `R_X86_64_32` from `_freeze_module.o` was wrong —
`_freeze_module` is a build tool, never linked into `python`). But
the resulting binary carries **2 dynamic `R_X86_64_TPOFF64`**
relocations, against glibc's own `errno` / `__libc_dlerror_result`
TLS symbols pulled in from `libc.a`. Debian trixie's glibc 2.41
`_dl_relocate_static_pie` mishandles those: during early self-
relocation it calls `_dl_allocate_static_tls`, which fails into
`_dl_signal_error` *before the error-catch frame exists* — the binary
SIGSEGVs before `main()`, **even on the host**:

```
#0  _dl_signal_error ()
#1  _dl_allocate_static_tls ()
#2  _dl_relocate_static_pie ()
#3  __libc_start_main_impl ()
```

The U39 MicroPython fixture has **0** `R_X86_64_TPOFF64` relocs, which
is why it is unaffected. Building CPython with **musl-gcc** sidesteps
the glibc TLS bug entirely: musl 1.2.5's static-pie startup resolves
TLS without the buggy `_dl_allocate_static_tls` path. The musl build
produces a clean ET_DYN static-PIE `python` with 0 TPOFF64 relocs
that runs both on the host and on Hamnix.

### The configure triplet patch

CPython 3.11's `configure` aborts under musl-gcc with `internal
configure error for the platform triplet`: musl-gcc's wrapper reports
the host gcc multiarch (`x86_64-linux-gnu`) while CPython's compiler-
characteristics probe yields `x86_64-linux-musl`, and upstream treats
the mismatch as fatal. The Makefile's `configure-patch` target
neutralises the check the same way Alpine Linux does — it trusts the
compiler-probe triplet (`MULTIARCH=$PLATFORM_TRIPLET`). Idempotent.

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
- Lands at ~9.3 MB stripped (vs ~20 MB unstripped, vs ~900 KB
  MicroPython). The overhead vs MicroPython buys complete self-
  containment: drop the binary into any namespace and
  `-c "print(...)"` just runs.
- Exercises a much wider syscall surface than MicroPython:
  `getrandom`, `clock_nanosleep`, `prlimit64`, `fstatat`,
  `readlinkat`, `mprotect`, plus the same brk/mmap/futex set as
  MicroPython. This is the surface `apt-installable Python apps`
  routinely walk.

## What's actually in `u_cpython`?

The staged binary is CPython 3.11.10's `python` interpreter, built
against **musl** and linked **`-static-pie`** (ET_DYN, no
PT_INTERP). See "Why musl static-PIE" above for the full rationale.
The `tests/u-binary/src/cpython/Makefile` orchestrates the whole
build via `make install`:

1. `configure-patch` — neutralise CPython's platform-triplet check
   so musl-gcc does not abort `./configure`. Idempotent.
2. `freeze-patch` — widen `Tools/scripts/freeze_modules.py`'s FROZEN
   list with `<encodings.*>` + the site.py / eval-loop support
   modules, then re-run `freeze_modules.py`. Idempotent.
3. `./configure` with `CC=musl-gcc CFLAGS=-fPIE LDFLAGS=-static-pie`
   and `--disable-shared --without-pymalloc-debug
   --without-doc-strings --disable-test-modules --with-system-libmpdec`.
4. `make -j$(nproc)` — first link.
5. `make regen-frozen` — bake the widened FROZEN headers.
6. `make -j$(nproc)` — re-link with the frozen headers compiled in.
7. `strip --strip-all` + OSABI-stamp + copy to `../../u_cpython`.

The interpreter implements full Python 3.11 semantics. The `-c
"print('hello from CPython on Hamnix')"` invocation in the U41 test
exercises:

- ELF static-PIE load + page-in at Hamnix's identity-mapped load
  region (U5, U10, U14, U19).
- musl-static crt startup.
- `set_tid_address`, `arch_prctl(ARCH_SET_FS)`, the static-init
  prelude.
- `brk(NULL)` / `brk(end)` for the Python heap (per-task brk via
  M16.104).
- `mmap(anon, RW)` for stdlib import + bytecode + object arenas.
- `getrandom(buf, 16, 0)` for `hash randomization` + `os.urandom`
  seeding.
- `write(1, ...)` -- the actual success marker.
- `exit_group(0)` -- normal interpreter teardown.

## How to rebuild

```
make -C tests/u-binary/src/cpython clean
make -C tests/u-binary/src/cpython install
```

This will:
1. Download `Python-3.11.10.tar.xz` from python.org (~20 MB).
2. Extract into `build/Python-3.11.10/`.
3. Apply `configure-patch` + `freeze-patch`.
4. Run `./configure` with the musl static-PIE flags above.
5. `make -j$(nproc)` → `make regen-frozen` → `make -j$(nproc)` --
   10-20 min on a modern x86_64 host; the link is serial so
   multi-core only helps the compile phase.
6. Strip + OSABI-stamp + copy to `tests/u-binary/u_cpython`.

Total disk: ~500 MB in `build/` (source + objects); after a
successful `install` you can `make clean` to reclaim it.

Total wall time: ~10-20 min on a recent (8+ core) x86_64 host.

## Host requirements

- `musl-gcc`. Debian: `apt-get install musl-tools` (provides
  `/usr/bin/musl-gcc` + the musl static archives). The build does
  NOT use the host glibc — see "Why musl static-PIE" above.
- `make`.
- `python3.11` on PATH — needed to run
  `Tools/scripts/freeze_modules.py` (CPython 3.11's freeze tooling
  is version-locked; a 3.12+ host python will not drive it).
- `wget` OR `curl` (to fetch the tarball).
- `tar`, `xz-utils`.
- `libmpdec-dev` (for `--with-system-libmpdec`); optional — without
  it `_decimal` is simply not built, which `print('x')` does not
  need.

The Makefile auto-detects `musl-gcc` + `python3.11`. If either is
missing it prints a clear `SKIP` line and exits 0 -- mirrors the
U22/U24/U39/U40 pattern so CI in minimal environments keeps moving.

## Troubleshooting

### `configure: error: internal configure error for the platform triplet`

musl-gcc's wrapper reports the host gcc multiarch
(`x86_64-linux-gnu`) while CPython's compiler probe yields
`x86_64-linux-musl`. The Makefile's `configure-patch` target fixes
this; if you ran `./configure` by hand, apply the patch first
(`make -C tests/u-binary/src/cpython configure-patch`) or set
`MULTIARCH=$PLATFORM_TRIPLET` in the configure script.

### SIGSEGV before `main()` in `_dl_relocate_static_pie`

You built against **glibc**, not musl. A glibc `-static-pie`
CPython carries 2 `R_X86_64_TPOFF64` relocs that Debian trixie's
glibc 2.41 mishandles during static-pie self-relocation. Rebuild
with `CC=musl-gcc` (this Makefile's default). Verify with
`readelf -rW python | grep -c TPOFF64` — it must print `0`.

### `Could not find platform independent libraries`

Two harmless stderr lines printed by CPython when it has no on-disk
stdlib tree. The `print('x')` boot path is satisfied entirely by the
frozen modules, so these lines do not stop the interpreter — the
U41 test PASSes regardless.

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
- `set_robust_list` (273) -- libc-static prologue, no-op safe.
- `rseq` (334) -- restartable sequences, no-op safe.
- `prlimit64` (302) -- already handled at U18.

The U41 test does NOT fix any missing syscalls; that's deferred
to a follow-up agent batching the cd-validation agent's syscall.ad
work. See TODO.md.

## How to upgrade to CPython 3.12 / 3.13

Bump `PY_VERSION` in the Makefile. The `CC=musl-gcc` +
`--disable-shared` + `LDFLAGS=-static-pie` story is stable across
the 3.x line. Two things to re-check on a bump:

- The `configure-patch` and `freeze-patch` targets pin exact source
  text from CPython 3.11.10's `configure` / `freeze_modules.py`. If
  3.12+ drifts that text the patch's `assert` fires with a clear
  "drifted; refresh patch" message — update the `old`/`new` strings.
- 3.12 introduced `_PyRuntime`-driven init that touches more of the
  syscall surface during startup; expect a couple new `-ENOSYS`
  hits when you bump.

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

The musl static-PIE frozen build is ~20 MB unstripped, ~9.3 MB
stripped. The frozen-module bytecode (`<encodings.*>` +
`<collections.*>` dominate) accounts for most of the size over a
bare interpreter. The initramfs `fs/initramfs_blob.S` is gitignored
and only embeds `u_cpython` when `HAMNIX_EMBED_UBIN=1` is set, so
the committed-default initramfs is unaffected.

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
