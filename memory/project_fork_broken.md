---
name: project-fork-broken
description: RESOLVED 2026-05-20 — fork() now gives the child a real private per-process address space (eager-copy; landed on main b8e0398). COW remains a future optimization. History below.
metadata:
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

**STATUS: RESOLVED 2026-05-20.** fork() now works — `e021700`
(`feat(mm): real per-process address space`) landed on `main` and is
pushed (current tip `b8e0398`). The child gets a fully private address
space: stack + ELF image + brk heap + TLS/TCB + mmap VMAs are
eager-copied into fresh physical pages remapped at the same vaddr in
the child's PML4. `test_u26_fork` / `test_rfork` PASS. The `%rdi`
ABI fix (`633dad2`) shipped alongside and was verified NOT to regress
native-Adder code. COW is the remaining optimization (eager-copy is
~33 MiB/fork) — see [[project-core-stabilization]] / a future COW task.
The rest of this file is the diagnostic history, kept for context.

---

Diagnosed 2026-05-20 while chasing the `busybox sh -c "echo a | grep a"`
kernel #GP (one-shot trap, halts the box).

**Root cause — `fork()` does not give the child a private address
space.** U38 (commit `bdd5e87`) implements the `do_clone` fork path by
copying the parent's top stack *page* onto a fresh page at a *different*
virtual address and running the child there. Every absolute pointer in
that page — saved `%rbp` chain, return addresses, `setjmp`/pthread
internals — still points at the PARENT's addresses, so the child
tramples the parent. A real `fork()` child also *returns from* `fork()`,
unwinding up through frames shared with the parent. The single 4 KiB
copy is also far too small.

Additional hazards a forked child corrupts in the parent: the `%r12`
syscall-entry spill slot (`syscall_64.S` parks it at `[user_rsp-8]`),
and the musl TCB (`struct pthread` at `fs_base`, shared because the
child shares `fs_base`). The Linux user stack is also undersized —
`do_execve`/`SYS_SPAWN` give only 16 KiB; busybox ash driving a
pipeline needs ~18 KiB.

**Progress 2026-05-20.** A solo fork agent shipped ONE correct piece:
the `%rdi`-preservation fix to `syscall_64.S` — commit `633dad2` on
**local `main`, NOT yet pushed**. It restores `%rdi` on syscall exit
(old code zeroed it, an ABI violation that broke musl `open(O_CLOEXEC)`
→ `busybox ls` enumerated nothing). This is the held `64173ec` fix,
now folded in. The fenced-file fence on `syscall_64.S` was lifted by
the user for the fork work.

The same agent built the full per-process address-space rework but
**reverted it** — forked parent AND child crashed inside glibc
(`_IO_puts` reading a garbage `stdout->_lock`). Its conclusion: a
correct static-PIE-glibc `fork()` needs the child to have a private
copy of **ALL writable memory** — stack + ELF `.data`/`.bss` + brk
heap + TLS/TCB — not just the stack (`fs_base` is shared, so the
child's post-fork bookkeeping corrupts the *shared* TCB; both procs
race the shared `_IO_2_1_stdout_`).

**The proper fix — V1 eager-copy (per-process address space):**
- Fixed user-stack virtual window; child gets a private physical stack
  at the SAME vaddr as the parent.
- `fs/elf.ad::_load_elf64` records the ELF writable range; ET_DYN
  writable data relocated to a virtual window clear of the kernel image.
- On `fork`: eager-copy stack + `.data`/`.bss` + brk heap + TLS/TCB
  into private physical pages, each remapped at the SAME vaddr in the
  child's PML4. Heap+`.data` likely need a high virtual window too.
- COW is a later optimization; bump Linux user stack to ≥256 KiB.

**Redeployed 2026-05-20** as solo agent `ac638ee4526cf9ccf` with full
worktree authority, tasked to: answer 3 triangulation questions first
(parent-vs-child crash; `stdout->_lock` parent-vs-child post-fork;
8 KiB-vs-256 KiB private copy), then implement V1 eager-copy, then fix
the broken `test_u26_fork` harness.

**Test harness gotcha discovered 2026-05-20:** `test_u26_fork` fails
NOT from a fork regression but because (a) `drivers/input/atkbd.ad`'s
`atkbd_diag_tick()` floods every QEMU boot with `[atkbd-diag]` lines,
slowing boot, and (b) the harness uses a fixed `sleep 3` before piping
input — boot now overruns it so `u_glibc_system` is sent before hamsh
is ready and lost. Both fixes folded into the fork agent's mandate.

**How to apply:**
- `busybox sh -c "echo X | grep X"` (ash-internal pipeline) may stay a
  marked XFAIL in `test_u37`; the hamsh-orchestrated 3-process pipeline
  is what `test_u37` actually asserts.
- Don't ship a bare "bump the Linux user stack" change in isolation —
  it perturbs allocator layout and surfaces this bug elsewhere.

Related: [[project-real-hw-boot]], [[feedback-fix-dont-catalogue]],
[[project-endgame]].
