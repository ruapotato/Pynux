# Project Memory Index

- [Project direction: Linux kernel rewrite](project_kernel_pivot.md) — Pynux pivoted from MCU OS to incremental x86_64 Linux kernel rewrite via .ko modules
- [Working agreements](feedback_working_agreements.md) — how language extensions land, commit discipline, propose-extension-first rule
- [Adder compiler quirks](feedback_compiler_quirks.md) — known compiler bugs + stable workarounds (Array-in-nested-frames, no string concat)
- [Compiler architecture state](project_compiler_state.md) — CPython-hosted, hand-written Thumb-2 backend; x86_64 backend is new work
- [x86_64 backend decision](project_x86_backend_decision.md) — hand-written encoder (codegen_x86.py), NOT LLVM; decided 2026-05-14
- [M1 complete](project_m1_complete.md) — hello-world .ko works end-to-end; where the kernel/busybox caches live; gotchas baked into scripts
- [M2 complete](project_m2_complete.md) — pure-Pynux 16550A console driver registered with the kernel; compiler features delta from M1
- [M3 partial](project_m3_complete.md) — M3.1 /proc/pynux/state + M3.2 /dev/pynuxdisk shipped; M3.3 ramfs / M3.4 virtio-blk deferred
- [Subsystem coverage state](project_coverage_state.md) — current breadth: 23 Pynux kernel modules across M1..M8
- [M16.1 boot path](project_m16_boot.md) — Pynux now compiles its own bootable kernel image; QEMU multiboot1 → long mode → start_kernel() banner; key gotchas (elf32-i386 wrapper, .pgtables outside .bss)
- [M16.69 state](project_m16_state.md) — current bare-metal kernel snapshot: ext4 r/w + 40 user binaries + /etc + /dev/null + RTC + hamsh $? — ~21 integration tests
- [Install roadmap](project_install_roadmap.md) — FAT32 read + EXT4 read/write + block-write DONE; UEFI outstanding for real-hardware boot
- [Endgame: Linux ABI + Debian distro](project_endgame.md) — L-series (kernel ABI) → U-series (userspace ABI) → NVIDIA → ship as a real distro consuming Debian repos
- [Plan 9 namespace framing](feedback_plan9_namespace_framing.md) — no global root; namespaces are per-process bindings to file servers, not sandboxed views
- [Endgame cadence](project_endgame_cadence.md) — multi-day (~7d) autonomous run: hourly cron + 2..8 parallel agents, no near-term stop, until "everything debugged"
- [Plan 9 pivot](project_plan9_pivot.md) — 2026-05-18: all non-9P work paused until V0..V4 land; shelved worktree branches mineable later
- [Rio open questions](project_rio_open_questions.md) — 4 design Qs from docs/rio.md pending user input before V4 GUI implementation
- [Agent git discipline](feedback_agent_git_discipline.md) — every dispatched agent uses isolation:worktree; orchestrator is sole writer to main; agents must never edit README.md/TODO.md/CLAUDE.md
