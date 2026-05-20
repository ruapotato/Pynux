---
name: feedback-agent-test-scope
description: Don't make dispatched agents run the full QEMU regression suite — they only run the test that targets their change. The orchestrator runs broad verification at cherry-pick time.
metadata:
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

When dispatching agents, the acceptance gate must NOT include the full
QEMU regression suite (run_compiler_tests.sh, test_uefi_boot.sh,
test_bios_boot.sh, and every test_net_https*.sh).

**Why:** 2026-05-19 the user pointed out that 15-minute agent waits had
become the norm — most of the time was QEMU-boot acceptance gates the
agent ran serially. The V7 TLS agent burned 100+ minutes monitoring its
own full suite before its conversation budget ran out (work was
functional but never got committed by the agent). Across N agents × 7
days of cron, this is the largest waste in the orchestration.

**How to apply:**
- Each agent's acceptance gate should be:
  - The narrow test that targets THIS change (e.g. test_net_https_lechain.sh for a TLS fix).
  - The lexer fixtures (`python3 compiler/lexer_test.py`, `scripts/test_lex_*.sh`) — these are sub-second pure-Python.
  - That's it. Skip the full `run_compiler_tests.sh`, skip both boot tests, skip unrelated networking tests.
- The orchestrator runs broad verification ONCE at cherry-pick time on main: `run_compiler_tests.sh` + the two boot tests + the test families touching the same subsystem. If anything breaks there, revert + re-task — but only the orchestrator pays that cost, and only once per merge.
- Prompts should explicitly say "DO NOT run the full regression suite; run only <X>." Defaults bite.
- For compiler changes, an exception: do run `run_compiler_tests.sh` because a codegen bug regresses unrelated kernel/userland code silently.
- For purely-userland changes that don't touch the kernel build (e.g. new user/foo.ad binary), skip the boot tests entirely — they don't exercise the change.

Related: [[feedback-agent-git-discipline]] for the worktree/commit rules these agents already follow.
