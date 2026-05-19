---
name: project-m1-complete
description: M1 hello-world kernel module landed; the x86_64 kernel-module dev loop now works end-to-end
metadata: 
  node_type: memory
  type: project
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

As of 2026-05-14, M1 is complete (see [[project-kernel-pivot]]). The
end-to-end loop works: `scripts/run_x86_module.sh` builds the Pynux module,
packs it into a busybox initramfs, boots a custom mitigations-off kernel
under QEMU, scrapes serial, and asserts the printk output. Exit code 0 on
success, 1 on output mismatch, 2 on environment failure.

**Why this matters:** future kernel-module work (M2 16550A driver and
beyond) reuses this same loop — `scripts/run_x86_module.sh <module-dir>`.

**How to apply / where things live:**
- Custom kernel: `$HOME/pynux-kernel/linux` (6.12.48, mitigations off,
  `bzImage modules` both built — `make modules` is required so Module.symvers
  exists). Pass `KDIR=$HOME/pynux-kernel/linux` to per-module Makefiles.
- Static busybox cache: `$HOME/pynux-kernel/busybox-1.36.1/busybox`.
- The compiler emits `.S`; kbuild owns `.S → .o → .ko`. Don't try to do
  assembly/link in `pynux.py` for the kernel-module target.
- Non-obvious gotchas now baked into the scripts (don't reintroduce them):
  the kernel build needs `make bzImage modules` (not just bzImage), QEMU
  needs `-monitor none` alongside `-serial stdio` on x86, busybox has no
  `scripts/config` helper or `olddefconfig` target, and
  `make_initramfs.sh` must resolve `.ko` paths to absolute up front
  because it `cd`s into the busybox build dir.
- Front end (lexer/parser/AST) was NOT modified — M1 needed zero language
  extensions. `parser.py` parses `def f() -> None:` as a function with NO
  return type annotation (NONE keyword is not a valid return-type token);
  omit the annotation for void returns instead.
