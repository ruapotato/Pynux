---
name: project-compiler-state
description: State of the Pynux compiler at the start of the kernel-rewrite work
metadata: 
  node_type: memory
  type: project
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

Snapshot as of 2026-05-14 (verify against code before relying on it):

- Compiler is CPython-hosted, lives in `compiler/`: `lexer.py`, `parser.py`, `ast_nodes.py`, `optimizer.py`, `codegen_arm.py` (~3700 lines, hand-written Thumb-2 encoder emitting GNU `as` assembly), `pynux.py` (CLI driver).
- CLI (`pynux.py`) has `compile` / `run` / `asm` subcommands. `compile` does transitive import resolution, merges all modules into one `Program`, calls `generate()`, assembles+links with `arm-none-eabi` toolchain against `runtime/` and `mps2-an385.ld`. There is NO target-selection plumbing yet — adding `--target=x86_64-linux-kernel-module` is new work.
- The team has prior hand-rolled-codegen experience (the existing Thumb-2 backend). The kernel briefing strongly recommends routing the x86_64 path through LLVM (llvmlite or textual IR) instead.

**Why this matters:** M1 (hello-world .ko) needs a new x86_64 codegen path + target plumbing in the CLI. The LLVM-vs-hand-written-encoder decision gates the whole backend effort.
