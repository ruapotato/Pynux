---
name: project-real-hw-boot
description: Hamnix boots to userspace (hamsh) on real hardware — Asus i5-4210U Haswell laptop, BOTH Legacy/BIOS and UEFI confirmed 2026-05-20. Ring-3 triple-fault fixed. Remaining gap: no keyboard input.
metadata:
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

**Milestone: 2026-05-20 — Hamnix reached `[hamsh] M16.35 shell ready` on a
real Asus laptop (Intel Core i5-4210U, Haswell ULT, Legacy/BIOS boot).**

**Why this mattered:** the #1 end-game priority (boot real hardware) was
blocked for ~15 ISO iterations (hamnix_5 .. hamnix_17) by a triple-fault at
the kernel→userspace ring-3 transition. The box rebooted in a loop with no
exception ever routed.

**The debugging arc (for context if it recurs):**
- Real-hw boot exposed a cascade of bugs QEMU/KVM never showed: e820 >4GiB
  identity map, GOP-framebuffer-corrupted-by-VGA-0xB8000-writes, slow
  framebuffer scroll, xhci self-test hanging with no USB keyboard, and
  finally the ring-3 triple-fault.
- The triple-fault resisted ~6 diagnostic-only ISO cycles. Every register
  dump (GDT/TSS/MSRs/page tables/RFLAGS/CR0/CR4/segment regs/CPUID) matched
  the QEMU baseline byte-for-byte. Both IRETQ and SYSRETQ failed identically.
  UD2 and HLT probes planted at user RIP both stayed silent — proving the
  CPU never reached the first user instruction.
- Fix landed in commit `62e5939` (M16.156): three mitigations applied
  together right after `load_cr3` in `start_first_task` —
  (1) `fninit` to clear firmware-dirty FPU state,
  (2) set `CR4.OSXSAVE=1` when CPUID.01h:ECX bit 26 (XSAVE) is set,
  (3) clear RFLAGS.IF in the first-task iret frame + `cli` before sysretq.
- **Most likely the decisive fix: CR4.OSXSAVE.** The kernel had been running
  OSXSAVE=0 on a CPU advertising XSAVE. QEMU TCG reports no XSAVE so it never
  exercised that path — which is exactly why the bug was real-hw-only and
  unreproducible in QEMU/KVM even with `-cpu Haswell`.

**UPDATE 2026-05-20 — UEFI confirmed.** The user tested the latest ISO
build on the Asus: it **boots fine in BOTH Legacy/BIOS and UEFI** modes.
The earlier UEFI hang at the 9P smoke test is resolved. Real-hardware boot
(end-game priority #1) is effectively achieved for this machine.

**Remaining real-hw gap: no keyboard input.** The built-in keyboard
produces nothing on the Asus. Known issue — the `[atkbd-diag]`
instrumentation in `drivers/input/atkbd.ad` was added to chase exactly
this (irq1_count / poll_calls / bytes_from_0x60 counters); on the Asus
`bytes_from_0x60` stays 0. The user has explicitly said this is NOT a
priority to action right now — do not dispatch keyboard work unless
asked. (Note: the fork agent's harness commit `33510d7` gated atkbd-diag
to stay quiet on QEMU while preserving the real-hw diagnostic.)

**How to apply:**
- Which of the 3 mitigations was *individually* decisive is not yet bisected.
  If asked to clean up M16.156, bisect first (test each mitigation alone on
  real hw) before removing any.
- The M16.151..M16.156 diagnostic scaffolding (ring3-diag, eft step markers,
  trap-diag handlers, probe-verify, cpuid dump, gdt/tss/seg dumps) is heavy
  and noisy. It can be trimmed once real-hw boot is confirmed stable across
  a few reboots — but keep the trap-diag #UD/#GP/#PF/#DF handlers,
  they are genuinely useful kernel infrastructure.
- ISO test loop: build with `scripts/build_iso.sh`, copy to `~/iso/hamnix_N.iso`,
  user dd's to USB and boots the Asus. Each cycle is ~20-30 min wall time —
  batch diagnostics, don't burn cycles on one-bit-at-a-time probes.

Related: [[project-m16-boot]], [[feedback-agent-test-scope]].
