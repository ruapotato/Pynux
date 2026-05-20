---
name: feedback-fix-the-language-layer
description: When agents keep hitting the same Adder/compiler hiccup, fix it in the language layer (the compiler) — don't let workarounds accrue. Make Adder as simple as possible for agents.
metadata:
  node_type: memory
  type: feedback
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

Stated by the user 2026-05-20: "when there's a common hiccup that the
agents keep hitting, you solve it in the language layer. Making the
language as simple as possible for agents to use."

**Why:** Hamnix is written in Adder, whose compiler is hand-written
(`compiler/`). Every Adder codegen bug or missing feature forces every
agent that hits it to write an ugly workaround — and those workarounds
multiply and rot. Fixing the compiler once removes the hiccup for every
agent forever. This is the highest-leverage form of [[feedback-fix-dont-catalogue]].
The track record bears it out: the U9 nested-frame-`Array` bug, the
sized-store `Ptr` bug, `&arr[i][j]`, signed-only compares, and
string-literal globals were all recurring hiccups — each fixed in
`compiler/codegen_x86.py` once, then the scattered workarounds removed.

**How to apply:**
- When triaging compiler/language limitations, ask "do agents keep
  tripping on this?" If yes, prioritise a compiler fix over tolerating
  the workaround.
- A compiler-codegen fix is verifiable: `scripts/run_compiler_tests.sh`
  (the fixture suite) plus the full boot+userland surface catch
  miscompiles. Every compiler fix lands a new `tests/test_compiler_*.ad`
  fixture.
- Bias toward making Adder SIMPLER for agents — fewer reserved-word
  traps, fewer "declare it this exact way or it miscompiles" rules,
  natural code that just works.
- Keep [[feedback-compiler-quirks]] current as the canonical
  workaround→fix→workaround-removed paper trail.

Known still-open compiler issues worth fixing (2026-05-20): unsigned
`>>` emits arithmetic `sarq` (needs `shrq`); unsigned `/`/`%` emit
signed `idivq` (need `divq`); flat global symbol namespace across
merged modules forces helper-rename collisions; no first-class
function-pointer type; no adjacent string-literal concatenation.

Related: [[feedback-fix-dont-catalogue]], [[feedback-compiler-quirks]],
[[project-core-stabilization]].
