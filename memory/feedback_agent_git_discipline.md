---
name: feedback-agent-git-discipline
description: Parallel agents committing to the same branch corrupt history; use worktree isolation and never let agents commit directly
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

When dispatching parallel agents to Hamnix (or any shared-branch repo), agents committing directly to `main` will race and corrupt history. Observed failure modes on 2026-05-18 during an 8-agent run:

- **`git add -A` absorbs siblings' WIP**: hamsh-papercut agent's commit absorbed mkpart/TLS/mkfs uncommitted files. Sibling agents who later tried to commit their own scope produced empty or duplicate commits.
- **Reset-to-fix collides**: mkfs agent did `git reset --hard HEAD~1` to drop a sibling's commit it considered "in the way." The reset orphaned a clean commit that was already on origin (push had succeeded). Local diverged from origin.
- **Repeated re-attempts**: same hamsh commit got authored as e1f271a, 927d34f, 78a5b9a, 49756d1 across cherry-pick/reset cycles. Each agent thought it was "recovering" prior state.
- **Stash thrash**: one agent (vma-validator) stashed parallel WIPs to build a clean tree; siblings rewrote the same files immediately after; the stashes piled up and confused subsequent agents.

**Why:** the file-ownership matrix in prompts isn't enforced — agents see the whole tree, and any agent doing wide `git add` plus `git commit` plus `git push` can step on sibling work. The orchestrator can't validate post-hoc.

**How to apply:**
- **EVERY dispatched agent must use `isolation: "worktree"`**. User direction 2026-05-18: "If they're worktree isolated, we can have up to eight." No exceptions — even single-file changes go through a worktree.
- Agents in worktrees do NOT push and do NOT touch the main checkout. They commit on their throwaway branch and report a verdict + commit SHA + file list + suggested commit message. The orchestrator (you, in the main checkout) cherry-picks or re-applies and pushes.
- Concurrency ceiling: 8 worktree agents. Zero agents allowed to commit to `main` directly. Orchestrator is the single writer to `main`.
- Worktrees live under `.claude/worktrees/agent-<id>/`. After consuming the patch, clean up with `git worktree remove .claude/worktrees/agent-<id>/ --force` (the harness usually auto-cleans on no-change, but if changes exist they linger).
- When an agent reports "I had to stash siblings' WIP" or "I had to reset HEAD~1," that's a violation; verify history with `git reflog` and recover. Should not happen in a worktree.
- Agents staging files MUST use `git add <specific paths>`, never `git add -A` or `git add .`. Bake this into every prompt.
- After 2-3 agents land in one cycle, the orchestrator must validate `main` still equals `origin/main` (no reflog surprises) before pushing.

**Commit BEFORE running long regressions.** Observed failure mode (2026-05-18): agent finishes its code work, then runs 6-8 regression tests serially, hits a build-lock or QEMU-timeout flake on test 5, gets stuck in a "wait for lock to free / retry" loop, and never reaches `git commit`. The real work is stranded uncommitted in the worktree. Orchestrator has to stop the agent and mine the WT manually — wasting ~30 min of agent cycles plus orchestrator attention. The pattern that prevents it:
  1. Do the code work.
  2. Run ONE directly-relevant test (the one the brief explicitly asked for).
  3. **Commit immediately on PASS** — even if regressions are still TBD.
  4. Run the full regression sweep.
  5. If a regression fails, AMEND or follow-up-commit.

This guarantees the work is preserved before the test-infrastructure ladder can fail. Build-lock contention specifically was fixed at commit `93df52c` (lock is now per-worktree, not global) — but the "commit early" discipline still matters for QEMU-timeout / OVMF / serial-glitch flakes.

See [[project-endgame-cadence]] for the broader multi-day cadence this constrains.
