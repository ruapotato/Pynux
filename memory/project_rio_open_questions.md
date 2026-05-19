---
name: project-rio-open-questions
description: 4 open design questions from docs/rio.md awaiting user input before V4 GUI implementation begins
metadata: 
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

`docs/rio.md` landed 2026-05-18 at commit `b8edbdf`. Plan 9-style file-based window system spec — per-window namespaces, `/dev/mouse` multiplexed by rio, `/dev/draw` for binary drawing, `/dev/wctl`/`/dev/wsys` for window control. VTNext-v2 retired in the process (`drivers/vt/vtnext.ad` was on shelved worktree `agent-abaa05e2…` — no longer slated to merge).

**Why these are open:** four decisions affect the V4 implementation shape but aren't yet picked. Don't implement V4 until the user answers.

**How to apply:** when the user returns, surface these as an AskUserQuestion (or just inline if they're already engaged). After they answer:
- Q1 affects `init/main.ad` (whether init execs rio or hamsh).
- Q2 affects the `/dev/cons` per-window dispatch model in the rio agent's prompt.
- Q3 affects whether to keep `acme` in the long-term roadmap or drop it.
- Q4 affects the `/dev/draw/<id>/data` byte spec the rio agent will implement.

**The four questions (verbatim):**

1. **Q1**: Should rio be PID-1 (replacing hamsh as init's exec target) or run as a daemon spawned by hamsh?
2. **Q2**: V0 keyboard model — does rio multiplex `/dev/cons` like mouse, or is keyboard always-focused-window?
3. **Q3**: Do we want acme as a future userspace project (the structured-editor 9P server that runs ON rio), or just hamsh and friends?
4. **Q4**: Wire framing for `/dev/draw` data — strict Plan 9 binary protocol, or Hamnix-specific simpler variant?

See also [[project-plan9-pivot]] for the broader Plan 9 reframing context.
