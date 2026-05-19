---
name: project-endgame-cadence
description: "Hamnix orchestrator runs hourly cron + up to 8 concurrent agents for ~7 days continuous, no near-term stop point"
metadata: 
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

Hamnix is in a multi-day autonomous-orchestration run. User set the cadence on 2026-05-18:

  > "Keep the hour cadence and spin up to eight concurrent agents. Until that list is completely done. That everything is debugged as much as possible."
  > "There's no projected end here until all of the to-dos have been completed. This will probably take you seven days."

**Why:** the user wants Hamnix driven to "everything debugged as much as possible" — boot, install, run real Linux binaries, Plan-9-shape syscalls, distro namespaces — and the work surface is wider than any single conversation. Cron + parallel agents is the only way to keep pressure on it across that span.

**How to apply:**
- Hourly cron check-in is the heartbeat; do NOT pause it or schedule a final-wake.
- Keep the parallel-agent floor at 2 and ceiling at 8. Refill as agents complete.
- Each dispatch must include an explicit forbidden-files list to prevent thrash — see [[feedback-working-agreements]] and the file-ownership matrix pattern.
- Orchestrator owns README.md and TODO.md merges; agents must never edit either.
- This is a multi-day run. Don't write "wrap-up" prose or "we're done" summaries — there is no near-term done. Each cron tick: push completed work, dispatch follow-ups, report state, move on.
- See [[project-endgame]] for the L-series → U-series → distro destination this is driving toward.
