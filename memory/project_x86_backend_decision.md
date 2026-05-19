---
name: project-x86-backend-decision
description: "Decision — x86_64 kernel-module backend is a hand-written encoder, not LLVM"
metadata: 
  node_type: memory
  type: project
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

Decided 2026-05-14: the x86_64 kernel-module backend will be a **hand-written x86_64 encoder** (new `compiler/codegen_x86.py` emitting GNU `as` assembly), NOT routed through LLVM — despite the kernel briefing's recommendation to use LLVM.

**Why:** Chosen deliberately over LLVM (textual IR and llvmlite were both offered). Keeps zero external dependency and stays consistent with the existing hand-written Thumb-2 backend (`codegen_arm.py`).

**How to apply:**
- Build `codegen_x86.py` in the same style as `codegen_arm.py` (emit assembly text for the system assembler/linker).
- Accept the cost the briefing flagged: ABI (SysV AMD64), ELF relocatable output, and kernel mitigations (-mno-red-zone, retpoline, IBT/ENDBR64, kCFI, 16-byte stack alignment) must all be handled by hand. Initial dev target is a custom kernel with mitigations OFF; ratchet on later.
- This choice is documented in-repo at `docs/x86-backend.md` (kept in sync with the codegen as mitigations are ratcheted on).
- See [[project-compiler-state]] and [[project-kernel-pivot]].
