---
name: project-kernel-pivot
description: "Pynux's new direction — incremental x86_64 Linux kernel rewrite via loadable kernel modules"
metadata: 
  node_type: memory
  type: project
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

As of 2026-05-14, Pynux changed direction. It was a Python-syntax systems language with its own small OS for ARM Cortex-M microcontrollers. The new goal: use Pynux as the target language for an **incremental, piece-by-piece rewrite of Linux kernel code on x86_64** — "a slow infection into the Linux kernel" replacing subsystems bit by bit. End goal is a fully-Pynux kernel.

**Why:** The MCU OS was a proof the language works bare-metal; the kernel rewrite is the real ambition. Strategy: `.ko` kernel module as the integration boundary (no bootloader/MMU/arch-init — the stock kernel did that), QEMU/KVM + serial console for an automatable code→build→boot→read→iterate loop.

**How to apply:**
- x86_64 ONLY. Defer all other architectures.
- The MCU OS in this repo must not break, but it is NOT the focus — don't extend it.
- Milestones: M1 = hello-world `.ko` in Pynux (insmod/dmesg/rmmod works under QEMU). M2 = 16550A UART serial driver as drop-in replacement. M3+ TBD post-M2.
- Deferred: Pynux self-hosting (buggy, revisit earliest post-M2), optimization (-O0 fine), production safety (research vehicle).
- Required language additions in rough order: x86_64 backend, C FFI (`extern "C"`, exact struct layout), inline asm, linker section attributes (`__init`/`__exit`/`.modinfo`), volatile + LKMM primitives (READ_ONCE/WRITE_ONCE/smp_*/atomic), compile-time metaprogramming for container_of/intrusive lists.
- Kernel ABI questions: consult target kernel source tree (`Documentation/process/`, `include/linux/module.h`), not memory.
