---
name: project-vma-maxorder-limit
description: RESOLVED 2026-05-20 — VMA allocator now backs >4 MiB allocations with multiple buddy chunks (landed b8e0398); 8 MiB glibc pthread stacks work, test_u28_glibc_thread PASSES.
metadata:
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

**STATUS: RESOLVED 2026-05-20.** `b8e0398` (`mm: back >4 MiB VMAs with
multiple buddy chunks`) landed on `main` and is pushed. A VMA larger
than the 4 MiB buddy MAX_ORDER is now backed by N buddy chunks mapped
contiguously into a dedicated `[1 GiB, 4 GiB)` virtual window;
`vma_fork_copy` copies all chunks. `test_u28_glibc_thread` PASSES (8 MiB
glibc pthread stack allocates). Two latent thread-start bugs were fixed
in the same commit: CLONE_VM threads now share the creator's PML4;
glibc clone3 `%rdx`/`%r8` worker-fn/arg propagation. History below.

---

Surfaced 2026-05-20 by the fork() agent while landing per-process page
allocation.

**Fact.** `mm/vma.ad`'s `vma_alloc` / `_order_for_bytes` / `MAX_ORDER`
cap a single VMA allocation at 4 MiB. glibc's pthread default thread
stack is 8 MiB, so `test_u28_glibc_thread` fails with:
`vma: alloc len=8392704 exceeds MAX_ORDER`.

**Why it matters:** this failure is **pre-existing** — it pre-dates the
fork rework and is unrelated to it. When evaluating the fork agent's
merge for regressions, do NOT count `test_u28_glibc_thread` as a fork
regression. The fork agent's `mm/vma.ad` change was purely additive
(+62 lines: `vma_fork_copy` + imports); it did not touch
`vma_alloc`/`_order_for_bytes`/`MAX_ORDER`.

**How to apply:**
- Queued deep-fix (user, 2026-05-20): rework the VMA allocator so a
  single allocation can exceed 4 MiB — needed for glibc pthreads. Do
  this AFTER the fork keystone lands, as its own dedicated effort.
- If a future agent reports `exceeds MAX_ORDER`, it's this known
  limitation, not a new bug — point it at the allocator rework.

Related: [[project-fork-broken]], [[feedback-fix-dont-catalogue]].
