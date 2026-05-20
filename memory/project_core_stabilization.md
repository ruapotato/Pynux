---
name: project-core-stabilization
description: Queued phase — after fork per-process AS + VMA MAX_ORDER fixes land, hunt down agent-introduced workarounds and replace them with fundamental fixes in the core.
metadata:
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

Directed by the user 2026-05-20: once the two major fixes land —
(1) fork() per-process address space [[project-fork-broken]] and
(2) the VMA `MAX_ORDER` rework [[project-vma-maxorder-limit]] — run a
**core-stabilization pass**: identify the crappy workarounds agents
have had to adopt and patch them out of the core fundamentally, rather
than letting them accumulate.

**UNBLOCKED 2026-05-20:** both prerequisite fixes have landed on `main`
(`b8e0398`). The core-stabilization phase is now active. First sweeping
job in flight: the **higher-half kernel relocation** — it kills the
ET_EXEC@`0x400000`-collides-with-kernel workaround at its root.

**Why:** the autonomous build accreted band-aids. Each one is a latent
instability and a trap for the next agent. The user wants the base
solid, not papered over.

**How to apply:**
- This is SEQUENCED — do it after fork + VMA land, not before.
- Audit candidates known at writing time (verify each is still present
  before acting — some may already be fixed):
  - Adder compiler bugs that force workarounds (see
    [[feedback-compiler-quirks]]): the U9 nested-frame-`Array` bug
    (forces top-level BSS), no string-literal globals (forces inline
    materialization). Fixing the compiler removes both workarounds
    repo-wide.
  - `test_*.sh` harness fragility: fixed `sleep N` before piping input,
    racing boot time (test_u26_fork hit this; likely others). Replace
    with ready-marker waits.
  - `[atkbd-diag]` boot-log spam (being fixed inside the fork task).
  - ET_EXEC@0x400000 colliding with the identity-mapped kernel image —
    currently dodged via musl static-PIE/ET_DYN; a higher-half kernel
    or proper load-region model is the real fix.
  - Any `xorq`/zeroing/"U27"-style conditional hacks left in the
    syscall path once the fork agent is done.
- Method: grep the tree for comment markers agents leave on
  workarounds (`WORKAROUND`, `HACK`, `XXX`, `FIXME`, `U9`, `quirk`,
  `band-aid`) plus the memory in [[feedback-compiler-quirks]]; triage
  by blast radius; fix the root cause.

Related: [[feedback-fix-dont-catalogue]], [[feedback-compiler-quirks]],
[[project-fork-broken]], [[project-vma-maxorder-limit]].
