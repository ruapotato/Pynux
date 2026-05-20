---
name: feedback-agent-worktree-paths
description: Dispatched isolation:worktree agents must edit files via their OWN worktree, never absolute /home/david/Hamnix paths — one agent leaked changes into the main worktree.
metadata:
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

When dispatching agents with `isolation: worktree`, the agent gets its
own git worktree under `.claude/worktrees/agent-<id>/`. It must edit
files THERE, not in the shared main checkout at `/home/david/Hamnix`.

**Why:** 2026-05-20 a tmpfs agent took the prompt line "Repo root:
/home/david/Hamnix" literally and edited `/home/david/Hamnix/fs/tmpfs.ad`
directly — its changes landed in the orchestrator's main worktree
(uncommitted) while its own worktree branch stayed empty. That breaks the
clean cherry-pick flow and risks the orchestrator building/testing main
with a still-running agent's half-written changes.

**How to apply:**
- In agent task prompts, do NOT write "Repo root: /home/david/Hamnix".
  Instead say: "You are in your own isolated git worktree — work with
  files relative to your current working directory; never use absolute
  /home/david/Hamnix/... paths, those belong to the orchestrator."
- If an agent still leaks into main: don't panic. Its changes are just
  uncommitted in main. Once the agent finishes, evaluate + commit them
  from main directly (treat main as that agent's deliverable); its empty
  worktree branch is ignored. If a DIFFERENT agent's branch needs
  cherry-picking while main is dirty, `git stash` the leaked changes
  first (stash is safe — not on the forbidden git list), cherry-pick,
  then `git stash pop`.
- Cron tick with the leak present: do NOT commit the leaked changes
  while that agent is still running — it is still writing them; a commit
  would capture a partial state.

Related: [[feedback-agent-git-discipline]], [[feedback-agent-test-scope]].
