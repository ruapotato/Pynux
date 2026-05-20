# u_busybox_musl build notes (U40; static-PIE fix U42)

U40 ships `tests/u-binary/u_busybox_musl` -- busybox 1.36.1 linked
against musl libc and built **static-PIE (ET_DYN)**. The intent is to
give the U-track a leaner busybox than the glibc-static `u_busybox`
shipped at M16.37+: smaller binary, smaller syscall surface, faster
iteration.

RETIRED (U42): the glibc-static `u_busybox` is no longer used. It was
an ET_EXEC linked at 0x400000; commit `653d962` ("elf loader: refuse
ET_EXEC overlay that collides with kernel image") made it dead on
arrival -- its fixed LOAD range collides with Hamnix's identity-
mapped kernel image, so the loader -ENOEXECs it. Every busybox
regression test (`test_u29_busybox.sh`, `test_u32_busybox_ls.sh`,
`test_u33_busybox_applets.sh`, `test_u36_busybox_sh.sh`,
`test_u37_busybox_pipe3.sh`, `test_u40_musl_busybox.sh`) now drives
THIS musl static-PIE fixture instead. `tests/u-binary/u_busybox` (if
still present on a host from an old extraction) is unused -- delete
it; nothing reads it. There is no build recipe for it to retire: it
was never built here, only extracted from a Debian `busybox-static`
package by hand.

## Why static-PIE (ET_DYN), NOT `-static` (ET_EXEC)

The original U40 build linked with `LDFLAGS=-static` -- producing an
**ET_EXEC at the fixed link address 0x400000**. Commit `653d962`
("elf loader: refuse ET_EXEC overlay that collides with kernel
image") later added a kernel-image collision guard to `fs/elf.ad`:
the loader overlays an ET_EXEC's fixed `[vlow, vhigh)` LOAD range
into the spawned task's PML4, and if that range overlaps Hamnix's
~12 MiB identity-mapped kernel image it is **REFUSED** with
`-ENOEXEC` (pre-`653d962` it silently dead-froze the box once
`schedule()` loaded the colliding CR3). Standard x86_64 `-no-pie`
binaries link at 0x400000 -- squarely inside the kernel image -- so a
`-static` busybox is now dead on arrival.

The fix mirrors the U41 CPython fixture (commit `d9f31ca`): build a
**musl static-PIE** -- an `ET_DYN`, statically linked, no-`PT_INTERP`
binary. ET_DYN binaries load at Hamnix's kernel-chosen identity-
mapped load region with no fixed-address overlay, so there is
nothing to collide. musl (not glibc) static-PIE also dodges the
glibc 2.41 `_dl_relocate_static_pie` TLS bug: the staged binary
carries **0** `R_X86_64_TPOFF64` relocations. Verify the fixture
shape with:

```bash
file tests/u-binary/u_busybox_musl
# -> ELF 64-bit LSB pie executable ... (GNU/Linux), static-pie linked
readelf -h tests/u-binary/u_busybox_musl | grep Type   # -> DYN
readelf -rW tests/u-binary/u_busybox_musl | grep -c TPOFF64   # -> 0
```

## Sizes (May 2026)

| binary                         | size      | libc / link        |
| ------------------------------ | --------- | ------------------ |
| `tests/u-binary/u_busybox`     | 2,024,544 | glibc, `-static`   |
| `tests/u-binary/u_busybox_musl`|  1,005,880| musl, `-static-pie`|

About 2x smaller. (Reduction would be larger if we also stripped
out applets we don't ship in Hamnix's environment -- networking,
init, mount -- but for a fair comparison both binaries enable the
defconfig applet menu.)

## Rebuilding from source

Prerequisites on the host:

```bash
sudo apt-get install -y musl-tools build-essential wget bzip2
```

Then from the repo root:

```bash
make -C tests/u-binary/src/musl_busybox install
```

This:

1. Downloads `busybox-1.36.1.tar.bz2` from busybox.net into
   `tests/u-binary/src/musl_busybox/build/`.
2. Extracts the source tree.
3. Runs `make defconfig` to start from the upstream "everything
   sensible" baseline. `defconfig` leaves both `CONFIG_STATIC` and
   `CONFIG_PIE` OFF -- which is what we want (see step 4).
4. Patches the `.config` via `sed` to: set
   `CONFIG_EXTRA_CFLAGS="-fPIE"` (position-independent codegen for
   every object), drop TLS / PAM / SELinux / EFENCE, drop `tc` /
   `nsenter` / `unshare` (kernel features Hamnix doesn't ship),
   drop NFS / inetd RPC (musl ships no Sun RPC headers). It does
   **NOT** set `CONFIG_STATIC=y`: that would inject `-static` into
   `CFLAGS_busybox`, and `-static` + `-static-pie` are mutually
   exclusive at the gcc driver. It also does NOT set `CONFIG_PIE=y`
   (that builds a *dynamic* PIE needing `ld.so`).
5. Symlinks the host kernel UAPI trees (`linux/`, `asm-generic/`,
   the multiarch `asm/`) into a private include dir at
   `build/busybox-1.36.1/uapi/`. We do NOT add `/usr/include`
   wholesale to the include path -- that would pull in glibc's
   `limits.h` / `stdio.h` / ... ahead of musl's, breaking the build.
   The musl tree intentionally excludes kernel UAPI ("kernel
   detail, not libc"), so applets that `#include <linux/kd.h>`,
   `<linux/vt.h>`, ... need to find the host kernel's copy. The
   UAPI headers are stable across libc choices.
6. Builds with `CC="musl-gcc -isystem .../uapi"` and
   `CFLAGS_busybox=-static-pie`. The `-static-pie` driver flag is
   passed via `CFLAGS_busybox` (not `LDFLAGS` / `CONFIG_EXTRA_LDFLAGS`)
   because busybox does `ld -r` partial-link steps that consume the
   exported `$(LDFLAGS)`, and `ld -r` rejects `-pie`
   ("`-r and -pie may not be used together`"). `CFLAGS_busybox` is
   applied **only** to the final `$(CC)`-driven busybox link
   (`scripts/trylink`), so `-static-pie` lands exactly there.
7. Copies the result to `../../u_busybox_musl`, strips it, and
   stamps `e_ident[EI_OSABI] = ELFOSABI_LINUX` so Hamnix's U1
   ELF-detect path (`elf_is_linux_binary`) recognises it
   unambiguously.

Build time on a modern host CPU: ~30-90 seconds.

## The glibc-static busybox is retired (U42)

The glibc-static busybox came in at M16.37 to stress-test pipes /
SYS_pipe2 / SYS_dup2 with a third-party binary. It was an ET_EXEC
linked at the fixed address 0x400000.

Commit `653d962` ("elf loader: refuse ET_EXEC overlay that collides
with kernel image") added a kernel-image collision guard to
`fs/elf.ad`: an ET_EXEC whose fixed `[vlow, vhigh)` LOAD range
overlaps Hamnix's ~12 MiB identity-mapped kernel image is REFUSED
with `-ENOEXEC`. A `-static` busybox links squarely inside that
range, so it is dead on arrival -- the busybox tests that drove it
SKIP'd (fixture refused) ever after.

U42 re-pointed every busybox regression test
(`test_u29_busybox.sh`, `test_u32_busybox_ls.sh`,
`test_u33_busybox_applets.sh`, `test_u36_busybox_sh.sh`,
`test_u37_busybox_pipe3.sh`) at THIS musl static-PIE fixture --
`test_u40_musl_busybox.sh` already used it. ET_DYN loads at a
kernel-chosen relocated base with no fixed-address overlay, so
nothing collides. Same busybox 1.36.1, same applet menu.

There is nothing to "retire" build-recipe-wise: the glibc
`u_busybox` was never built by a Makefile here -- it was extracted
by hand from a Debian `busybox-static` package. If a stale copy
still sits at `tests/u-binary/u_busybox` on an old host, delete it;
no test or script reads it any more. (`test_u34_syscalls.sh` and
`test_u35_pipelines.sh` still name it in a `UBIN=` guard; with the
fixture absent they SKIP cleanly -- they are outside the U42
re-point scope and a follow-up can re-point them the same way.)

## Skip behaviour

If `musl-gcc` is missing on the build host, the `install` target
prints a clear note and exits 0. The matching test
(`scripts/test_u40_musl_busybox.sh`) skips on missing
`tests/u-binary/u_busybox_musl` the same way U22/U24/U39 do. CI in
environments without `musl-tools` keeps moving.

## Known build notes

- We disable `CONFIG_PAM`, `CONFIG_SELINUX`, `CONFIG_EFENCE`, and a
  few other heavy options up front. If a future busybox bump
  re-enables one of these by default, edit the `DISABLE_APPLETS` or
  the explicit `sed` calls in the Makefile.
- The build runs `yes "" | make oldconfig >/dev/null` after the
  sed patches so dependent Kconfig symbols settle. If you change
  the applet menu and the build complains about an undefined
  symbol, that's where to look.
- Strip is unconditional in `install` -- the upstream `make install`
  strip uses host binutils strip on an x86_64 binary, which is the
  same arch we're targeting, so it's safe.
- The OSABI stamp is the same `printf '\003' | dd of=... seek=7
  count=1 conv=notrunc` trick the other u_* fixtures use. The
  binary on disk will read as `ELF ... (GNU/Linux), ... static-pie
  linked` rather than `(SYSV)`.
- If a future busybox bump's `defconfig` starts shipping
  `CONFIG_STATIC=y` or `CONFIG_PIE=y` ON by default, add an
  explicit `sed` to turn them back OFF -- both break the
  `-static-pie` link (see "Why static-PIE" above).
