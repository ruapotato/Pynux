---
name: feedback-build-hygiene
description: Verify agent work on a clean build — stale/truncated build artifacts cause false test failures. _build_lock.sh now auto-wipes compiled outputs; don't kill -9 builds.
metadata:
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

Self-feedback the user endorsed 2026-05-20 ("Good self-feedback to apply").

**What happened:** mid-session I `kill -9`'d several in-flight builds
(`compiler.adder` compiles, QEMU). That left truncated `.elf` files in
`build/`. The per-test build is incremental enough that it did NOT
regenerate the truncated artifacts — so subsequent test runs on the
orchestrator's main worktree produced FALSE failures (`test_u26_fork`
"hamsh: not found", an all-timeout verification batch). I burned real
cycles — including a whole agent's bisect — chasing a self-inflicted
poisoned `build/` before realising the cause.

**Why it matters:** a poisoned `build/` makes verification lie. A
"FAIL" that's actually stale artifacts wastes investigation and can
mask (or fake) a regression.

**How to apply:**
- `scripts/_build_lock.sh` now AUTO-WIPES compiled build outputs
  (`build/user`, `build/mod`, `build/iso`, `build/*.elf`, `build/*.iso`,
  `fs/initramfs_blob.S`) once per test, right after acquiring the build
  lock — so every test starts from clean compiled state. Disk images
  (`build/*.img`) are spared (tests that persist them still work).
- Don't `kill -9` builds. If you must stop one, prefer letting it finish
  or SIGTERM; a hard kill mid-compile is the poison vector.
- When an agent reports PASS but your verification FAILs on an
  unexpected, infrastructure-shaped symptom ("not found", all-timeout,
  zero serial output), suspect build state before suspecting the code —
  a clean rebuild is the first check.

Related: [[feedback-agent-test-scope]], [[feedback-sweeping-agents]].
