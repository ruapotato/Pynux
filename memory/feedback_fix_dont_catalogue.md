---
name: feedback-fix-dont-catalogue
description: When an agent finds a real bug OR pre-existing tech debt, fix/pay it back then and there — don't accumulate "X is broken" reports. Solidifying the base is continuous, not a phase.
metadata:
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

Stated by the user 2026-05-20: "let's make sure the base works and we
can close those gaps. We don't want to have a bunch of agent nodes
saying which things are broken; we want to fix those things as they
are found."

**Why:** over the autonomous push, several agents STOPPED and reported a
gap instead of fixing it (apt-get's missing user-socket path, the
fork() investigation, busybox `ls` diagnosis). That was partly because
task prompts scoped agents narrowly and fenced files. The result was a
growing list of "here's what's broken" hand-offs. The user wants the
opposite: a solid base, gaps closed as discovered.

**How to apply:**
- Default to FIXING, not cataloguing. When dispatching, give the agent
  enough scope and authority to fix the ROOT CAUSE — not just a narrow
  patch around it. If a fix plausibly needs a neighbouring file, grant
  that file in the prompt up front.
- Reserve STOP-and-report for genuine architecture-decision forks
  (two legitimate designs, the user should pick) — NOT for "the fix
  needs a file I wasn't given." If an agent keeps stopping because it
  lacks scope, the dispatch was mis-scoped; re-dispatch wider.
- When an agent's investigation surfaces a NEW real bug mid-task,
  prefer letting it (or an immediate follow-up) fix that too, rather
  than filing it. Bug found → bug fixed, same cycle where feasible.
- Still verify broadly before merging (see [[feedback-agent-test-scope]])
  and still don't ship regressions — "fix it" never means "fix it
  sloppily."
- Fenced files: the standing `syscall_64.S` fence means "ask before
  touching", not "never fix bugs there." When a real bug IS there,
  surface it to the user for a one-time grant rather than leaving it
  broken (the user granted exactly that for the fork() fix).

**Pay back technical debt found — continuously (user, 2026-05-20).**
"As we solidify the base and make Adder a more friendly AI language, we
want to make sure we're paying back any technical debt found." This is
NOT a one-time phase — it's a standing posture. When an agent (or the
orchestrator) trips over pre-existing debt while doing other work — a
crappy workaround, a stale comment, a dead branch, an ergonomic trap in
the compiler — pay it down in that cycle rather than deferring it. Two
qualifiers: (1) don't let debt-payback balloon a task's scope past what
can be verified safely — if a payback is genuinely large (e.g. the
name-resolution redesign), spin it as its own job rather than smuggling
it in; (2) "pay it back" still means verified, no-regression work.
Examples this session: the build-lock auto-wipe (fixed a poisoned-build
trap), the CI initramfs step, dropping dead U9 workarounds, the unsigned
shift/divide codegen fix.

Related: [[feedback-working-agreements]], [[feedback-agent-test-scope]],
[[feedback-fix-the-language-layer]], [[project-core-stabilization]],
[[project-fork-broken]].
