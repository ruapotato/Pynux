---
name: feedback-working-agreements
description: "How to collaborate on Pynux — language-extension discipline, commit discipline"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

Working agreements for the Hamnix kernel-rewrite work (see [[project-kernel-pivot]]):

- **Propose a language extension before working around an awkward kernel idiom in user code.** The language is meant to grow.
  - **Why:** Hamnix/Adder is being co-designed with the kernel port; awkwardness is signal, not noise.
  - **How to apply:** When a kernel idiom is clumsy in current Adder, first draft a minimal language extension. Every extension lands with three things together: a spec sentence in `LANGUAGE.md`, a test in `tests/`, and a real use site in kernel-module code that justified it.
- **Patch bugs at the layer they belong; never paper over compiler/language bugs in user code or tests.** If a test is flaky, the underlying behaviour is broken — find the real cause and fix the compiler, runtime, or kernel.
  - **Why:** During M16.40 a flaky multi-stage pipeline tempted a "retry the test N times" workaround. The actual cause was a silent symbol collision in `merge_programs` — two modules each defined `_find_free_slot`, the dedup-by-name pass dropped one, and callers in module B linked against module A's body. Retries would have hidden it forever.
  - **How to apply:** When something fails intermittently or "works most of the time", stop adding retries / sleeps / loosened greps. Add instrumentation, find root cause, fix in the compiler / kernel / runtime — and ideally turn the silent failure into a loud one (e.g. `merge_programs` now errors on duplicate top-level names instead of silently dropping the second).
- **Prefer small commits that boot.** A failing-to-load `.ko` is worse than fewer features.
- Correctness first; `-O0`-quality codegen is acceptable.
