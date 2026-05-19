---
name: project-m2-complete
description: "M2 done — a 16550A serial console driver in pure Pynux, registered with the kernel and replacing 8250 as the active console"
metadata: 
  node_type: memory
  type: project
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

As of 2026-05-14, M2 is complete (see [[project-kernel-pivot]],
[[project-m1-complete]]). A loadable kernel module written in pure Pynux
(zero C glue) populates a `struct console`, registers it via
`register_console()`, and the kernel uses Pynux's `pynux_console_write`
for every subsequent printk. Verified by booting QEMU with
`console=pynux` on the cmdline and observing the `[P]` marker prepended
to every kernel log line, plus `pynux0  -W- (EC p)` in `/proc/consoles`.

**Why this matters:** Pynux now drives real kernel hardware (16550A UART)
via its own emitted assembly, end-to-end. The compiler grew the AST
surface needed for that to be possible without falling back to C glue.

**How to apply / where things live:**
- `kernel-modules/m2-console/` — the driver module. The `Console` Pynux
  class mirrors the kernel's `struct console` byte-for-byte for
  **linux-6.12.x** (size 280, opaque padding = 168 bytes covering
  hlist_node + nbcon block). Adapting to another kernel requires
  re-probing the struct (see the `/tmp/probe` recipe in the conversation
  history: a tiny C module with `offsetof()`/`sizeof()`).
- To make our console actually serve printk, the **kernel cmdline must
  include `console=pynux`** — register_console matches our `name` field
  to a pending cmdline spec to flip `CON_ENABLED`. `add_preferred_console`
  is NOT exported to modules in 6.12.
- `kernel-modules/m2-arith/`, `m2-string/`, `m2-outb/`, `m2-strout/`
  are use sites for each compiler tier as it landed; keep them as
  regression tests.
- Each module dir has `expected.txt` — runner asserts those literal
  strings appear in the QEMU serial output.
- Compiler grew `codegen_x86.py` from ~220 to ~650 LoC. Still small.

**Compiler features now supported on x86_64 (delta from M1):**
- Function parameters (SysV AMD64: rdi/rsi/rdx/rcx/r8/r9), local
  variables, identifier-as-rvalue, simple assignment.
- BinaryExpr: +, -, *, ==, !=, <, <=, >, >=, &, |, ^, <<, >>, and, or.
- UnaryExpr: NEG, BIT_NOT, NOT, DEREF, ADDR.
- IfStmt (with elif/else), WhileStmt, BreakStmt, ContinueStmt, PassStmt.
- IndexExpr load + assignment (size-aware via movzbq/movzwq/movl/movq).
- MemberExpr load + assignment; ClassDef as C-ABI struct (natural-align).
- Top-level VarDecls: `.data` (with int initializer) or `.bss`
  (zero-init).
- `outb` / `inb` as x86 intrinsics emitting bare `out`/`in` instructions
  (the kernel's are `static __always_inline` with no exported symbols).
- Varargs ABI: `xorl %eax, %eax` before every extern call so `_printk`'s
  variadic dispatch sees 0 vector args.

**Still deferred (not needed for M2):**
- For-loops (only `while` so far).
- Compound assignment (`+=`, etc.).
- Parameterized decorators (`@section(...)`).
- Full inline-asm-with-constraints syntax (only outb/inb intrinsics).
- Struct-literal initializers (we use zero-init `.bss` + imperative
  field assignments in init_module).
- Optimization (-O0-quality codegen is fine).
