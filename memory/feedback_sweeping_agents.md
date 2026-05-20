---
name: feedback-sweeping-agents
description: Don't shy away from large topics — dispatch a single agent with sweeping whole-worktree authority for big architectural changes rather than fragmenting into timid narrow tasks.
metadata:
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

Stated by the user 2026-05-20: "don't shy away from large topics that
need a single agent to do sweeping changes. Let's push this into top
tier OS/kernel."

**Why:** the fork() keystone was solved exactly this way — one solo
agent with full authority over every file (incl. the fenced
`syscall_64.S`) landed a real per-process address space. Narrow,
fenced, parallel-fragmented dispatches had stalled on it for days. The
user wants Hamnix to reach genuine top-tier OS/kernel quality, and that
needs bold architectural moves, not incremental timidity.

**How to apply:**
- When a topic is genuinely large and cross-cutting (COW fork, a
  higher-half kernel, the core-stabilization sweep, a namespace
  rework), dispatch ONE agent with sweeping authority over the whole
  worktree — including normally-fenced files — rather than splitting it
  into narrow tasks that each lack the scope to finish.
- A big single-agent job and small parallel jobs can't always coexist
  (the sweeping agent wants the whole tree). When a sweeping job is the
  priority, run it solo; otherwise the 2-agent cap still applies.
- This does NOT relax verification or the no-regression-by-default
  bar — sweeping ≠ sloppy. It's about scope and ambition, not care.
- Still respect worktree isolation and orchestrator-merges discipline
  ([[feedback-agent-git-discipline]]).

Related: [[feedback-fix-dont-catalogue]], [[project-core-stabilization]],
[[feedback-agent-git-discipline]], [[project-fork-broken]].
