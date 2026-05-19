# Hamnix orchestrator memory

This is the per-session memory that drives the AI-orchestrated development
workflow described in the top-level [README.md](../README.md#agent-orchestrated-development).
Each file is a single fact the orchestrator wants to carry forward across
conversations — a user preference, a project decision, a debugging
artifact, a debunked claim. It exists so the orchestrator does not redo
the same root-cause investigation twice, or repeat a mistake that was
already corrected once.

If you are a new reader trying to understand the project's direction
without reading 140 commits, start with the `project_*` files. If you are
debugging a compiler issue, start with [`feedback_compiler_quirks.md`](feedback_compiler_quirks.md).

## How this directory is structured

The orchestrator uses a small ontology — four types of memory, each with a
specific purpose:

| Type | When to read it | Recent example |
|--|--|--|
| **`feedback_*`** | When the user has corrected an approach or confirmed a non-obvious one. Carries discipline rules ("agents must use `git add <specific paths>`", "Plan 9 vocabulary is per-process namespaces not sandboxes"). | [`feedback_agent_git_discipline.md`](feedback_agent_git_discipline.md), [`feedback_compiler_quirks.md`](feedback_compiler_quirks.md) |
| **`project_*`** | When establishing what's going on in the project right now. Stale fastest. Always re-verify against current git state before acting on a recommendation. | [`project_plan9_pivot.md`](project_plan9_pivot.md), [`project_endgame_cadence.md`](project_endgame_cadence.md) |
| **`reference_*`** | Pointers to external systems (Linear, Slack, Grafana). None yet for Hamnix. | — |
| **`user_*`** | Things about the user — role, preferences, knowledge gaps. None currently surfaced; the user has not asked for one. | — |

## Index

[`MEMORY.md`](MEMORY.md) is the index — the orchestrator's automatic
shortcut to "what memories exist." It's always loaded into the session
context. Individual files are loaded on demand based on relevance.

## Why publish this?

Two reasons:

1. **Honesty.** Hamnix is being built with significant AI assistance.
   This directory is the actual mechanism — not a vibe, an artifact. Showing
   it makes the workflow legible to anyone evaluating the project.
2. **Reusability.** The patterns here ("compiler quirks as a tracked file
   with crossed-out entries for fixed bugs", "agent git discipline rules
   in a single canonical place") generalise to other AI-orchestrated
   projects. If someone wants to bootstrap a similar workflow, this is
   the prior art.

These files were captured during a multi-day autonomous run; the dates and
commit SHAs in each file place them precisely in the project's timeline.
They are not curated for publication — they are what the orchestrator
actually wrote to itself. The crossed-out FIXED entries in
[`feedback_compiler_quirks.md`](feedback_compiler_quirks.md) are the
clearest demonstration: every "real bug → workaround → real codegen fix
→ workaround removed" cycle leaves a paper trail here before the README's
status table catches up.

## What this is not

- **Not a changelog.** That's [STATUS.md](../STATUS.md).
- **Not a design doc.** Those live in [docs/](../docs/).
- **Not authoritative.** Memory entries can be wrong, stale, or fabricated
  by an over-eager agent. Cross-check against `git log` and the actual
  source tree before relying on a claim.
- **Not exhaustive.** The orchestrator writes memories when something
  seems worth carrying forward, not on every interaction. There are
  gaps.

If you find an obviously stale or wrong claim in these files, opening
an issue is the right move — it improves the orchestrator's accuracy
on future sessions.
