# Hamnix

**A from-scratch x86_64 server OS, written in Adder — a Python-syntax
systems language with a hand-written x86_64 compiler (no LLVM).**
Hamnix is the OS; Adder is the language and compiler used to write it.
Boots on BIOS + UEFI; reaches a real userspace shell.

The novel claim is the **layered architecture**: native Plan 9-shape
syscalls underneath, with a Linux ABI shim sitting on top so unmodified
Linux binaries also run. Both worlds share one kernel.

---

## What's different about Hamnix

Most OS projects pick one of two stances: clone Linux, or implement Plan 9
from scratch. Hamnix picks both, layered:

| Layer | Shape | What lives there |
|--|--|--|
| **5** | Apps | Stock Debian packages (apt-installed) + Hamnix-native binaries |
| **4** | Wire protocols | 9P (kernel↔userspace), [rio](docs/rio.md) (window system, planned) |
| **3** | Userspace services | 9P file servers (hamwd-like) — Hamnix programs |
| **2** | Linux ABI shims | `linux_abi/` — translates Linux syscalls onto Layer 1 |
| **1** | Native syscalls | **Plan 9-shape** — ~25 calls including `rfork`, `bind`, `mount`, `errstr`. See [`docs/native-api.md`](docs/native-api.md) |
| **0** | Kernel internals | Linux-shape — task_struct, scheduler, allocators. Reading kernel/sched/core.c → porting to `kernel/sched/core.ad` is the unit of work. |

The clearest demonstration: the **cdev family**. Native code reads system
state via Plan 9-shape paths like `/dev/cpuinfo`, `/dev/meminfo`,
`/dev/uptime`, `/dev/loadavg`, `/dev/version`, `/dev/hostname` (twelve
files; see M16.131–M16.133). Linux binaries open `/proc/cpuinfo`,
`/proc/meminfo`, etc. and the **Layer-2 translation** (M16.134) silently
rewrites the path before `vfs_open` — Linux ELFs see byte-identical
output to native code.

This pattern generalises: the kernel knows letters (`#s`, `#p`, `#c`,
`#/` — Plan 9 device aliases); userspace `init` reads a recipe and
binds them at conventional paths (`bind '#s' /srv`, `bind '#p' /proc`,
…). Per-process namespaces via `rfork(RFNAMEG)`, real `Pgrp` struct
with refcount, end-to-end 9P loop closes through userspace-posted
srvfds. See M16.135 + 9P V0..V4.1 in [STATUS.md](STATUS.md).

---

## What it boots into today

- **Hybrid BIOS+UEFI ISO** built by `scripts/build_iso.sh` — boots under
  SeaBIOS, OVMF UEFI, and GNOME Boxes.
- **UEFI direct boot**: PE/COFF stub uses SFSP to load the kernel ELF
  off the ESP, runs ExitBootServices, jumps to long mode. Reaches the
  hamsh prompt end-to-end on the UEFI path (M16.126, M16.138).
- **Linux ABI**: ~250 syscall numbers wired; 24 stock Debian `.ko`
  modules load cleanly; musl-static, glibc-static-pie, and CPython
  3.11 (frozen-stdlib build) all run real ELF binaries.
- **Network stack**: virtio-net / e1000e / r8169 / Realtek MAC drivers;
  ARP/IP/UDP/TCP/ICMP/DHCP (with renew+rebind)/DNS/HTTP/TLS 1.3 client
  with HTTPS GET working end-to-end.
- **Block stack**: AHCI + NVMe, MBR + GPT read+write, FAT32 read,
  EXT4 read+write, partition-aware block-device naming (`sd0p1`,
  `nvme0n1p2`).
- **Plan 9 base**: codec + spec, kernel 9P client, per-process Pgrps
  (heap-allocated), `/srv` / `/n` / `/proc/<pid>/ns` namespace
  primitives, userspace recipe-driven init, `sys_srv_post`/`sys_srv_open`
  syscalls, end-to-end userspace-server → kernel-client → read-bytes
  loop verified.
- **Userspace**: hamsh shell with control flow, `$?`, `$VAR`, PATH
  walker; ~60 GNU-style binaries; per-process namespaces verified to
  isolate.

For the full milestone log (140+ entries across M / L / U tracks), see
**[STATUS.md](STATUS.md)**.

---

## MVP cut

Hamnix is a wide project. The minimum-viable shape we're converging on:

> **Bootable ISO that boots on a real ThinkPad, runs Python and a static
> busybox, fetches a Debian package over HTTPS, and serves HTTP.**

Concretely this means closing four named gates:

1. **L40 — boot on real ThinkPad hardware.** Today's UEFI verification
   is QEMU + OVMF firmware + GNOME Boxes. The structural pieces (PE/COFF
   stub, SFSP ELF loader, GDT handoff at M16.138, FAT12 ESP per OVMF's
   El Torito quirk) are in place, but **L40 is Pending** — no T480
   / Dell / HP physical box has run the ISO yet.
2. **TLS-CERT — X.509 + RSA-PSS / ECDSA verify with a baked CA store.**
   **Closed** in V0..V6 + V5.1 (commits `f47449e` → `563e23f`).
   ASN.1 parser, X.509 walker, RSA-PSS-SHA256, ECDSA-P256 (binary-GCD
   modular inverse — ~1s verify in QEMU), PKCS#1 v1.5 SHA-256 dispatch,
   chain builder with 8-anchor CA store, validity window, CertificateVerify
   transcript binding. Apt-over-HTTPS against LE-signed mirrors is now
   MITM-resistant for the common path. Remaining fragilities are
   smaller in scope: multi-record handshake stitching unsupported
   (chains > ~1.4 KB split across two AEAD records will trip);
   CRL/OCSP intentionally out of scope; primitives are not const-time
   yet (V6+ hardening).
3. **USB HID V2 — interrupt-IN poll** so real `sendkey x` keystrokes
   reach hamsh stdin. M16.139 V0+V1 ship the controller + transfer
   engine end-to-end on `qemu-xhci + usb-kbd`; the continuous polling
   loop is the only remaining piece. (In flight.)
4. **inbound SSH** — needs `sshd` running. The crypto primitives are
   in place (ChaCha20-Poly1305, X25519, SHA-256); the SSH protocol
   itself is not. Once present, "useful server OS" is functionally
   demonstrated.

Everything else on the project — GUI / rio, full real cert validation
for outbound TLS, multi-core scheduler polish, additional drivers — is
beyond MVP.

---

## Known blockers

| Gate | Status | Impact |
|--|--|--|
| **TLS cert validation** | **Closed** — apt-over-HTTPS against LE-signed mirrors is MITM-resistant for chains that fit one AEAD record | Full chain validation V0..V6 + V5.1: ASN.1 parser, X.509 walker, RSA-PSS-SHA256 verify, ECDSA-P256 verify, PKCS#1 v1.5 verify (`ba2d9dc`), chain builder + CA store + validity window, CertificateVerify transcript binding per RFC 8446 §4.4.3 (`563e23f`). The two V5-disclosed residuals both landed. Remaining real-world fragilities are smaller: (a) multi-record handshake stitching is unsupported — LE chains > ~1.4 KB across two AEAD records will trip; (b) no CRL/OCSP (intentional per RFC 5280 §6 — out of scope); (c) timing-channel hardening pending in V2/V3 primitives; (d) `_tls_now_unix` falls back to a build epoch when RTC is unavailable, opening a clock-rolled-back attack on expired certs. |
| **L40: real T480 boot** | Pending | "Real hardware" verification is QEMU+OVMF today; no physical box has been booted yet. The cron-priority claim is **structurally** complete, not **physically** verified. |
| **USB HID V2 polling** | Closed structurally; wire-side verification in QEMU `sendkey` pending `socat` install | Continuous interrupt-IN poll wired into the timer tick; synthetic Transfer Events round-trip through `kbd_rx_push`. Real keypress on `qemu sendkey x` would now go through the same path but the harness can't inject without `socat`. |
| **Inbound SSH** | Not yet started | Needed for "useful server OS" but no SSH protocol code exists. Crypto primitives are in place (ChaCha20-Poly1305, X25519, SHA-256, ECDSA-P256, RSA-PSS); the SSH layer itself isn't. |
| **U9 nested-frame Array spill** | Active compiler bug | `Array[N, T]` locals with the same shape in caller + callee miscompile. Workaround: inline the callee. See [`memory/feedback_compiler_quirks.md`](memory/feedback_compiler_quirks.md). |

Four other compiler bugs landed proper fixes during the recent sessions
(M16.135): `Ptr[T]` writes to `&local` sub-8-byte scalars, `&arr[i][j]`
on 2-D Array globals, a confirmed-phantom cast-load report, and the
already-fixed signed-only comparison rediscovery. Language quirks land
in `tests/test_compiler_*.ad` as guarded regressions the moment they're
surfaced — see [`scripts/run_compiler_tests.sh`](scripts/run_compiler_tests.sh)
(7 fixtures, all green).

---

## Quick start

Requirements: `gcc`, `make`, `qemu-system-x86_64`, `flex`, `bison`,
`libelf-dev`, `xorriso`, `mtools`, Python 3.10+. For UEFI testing
also `ovmf`.

### Boot the bare-metal Hamnix kernel under QEMU

```bash
./scripts/run_x86_bare.sh
```

Compiles `init/main.ad` (plus imports), assembles + links into
`build/hamnix-vmlinux.elf`, boots via QEMU `-kernel` multiboot1. Serial
shows the boot banner, memblock smoke, per-CPU id, PIT timer ticks, the
init task, and the hamsh prompt.

### Build + boot the hybrid ISO

```bash
./scripts/build_iso.sh                # produces build/hamnix.iso
./scripts/test_bios_boot.sh           # SeaBIOS boot
./scripts/test_uefi_boot.sh           # OVMF / UEFI boot (apt install ovmf)
```

Both test scripts force-rebuild the ISO every invocation so stale-artifact
silent-PASS is impossible (M16.141 fixed the boot-test trap). Set
`HAMNIX_SKIP_BUILD=1` to reuse a cached `build/hamnix.iso`.

### Run the M1..M15 stock-Linux .ko regression suite

```bash
./scripts/build_x86_kernel.sh         # one-time: ~10-25 min, cached
for d in kernel-modules/*/; do ./scripts/run_x86_module.sh "$d"; done
```

Each module has an `expected.txt` of required serial strings; runner
asserts them and exits 0 on success.

---

## How it works

```
Adder source (.ad — Python syntax with static types)
   │
   ▼
compiler/  (CPython-hosted; adder.py CLI dispatches by --target)
   │
   ├──► codegen_x86.py  ──►  .S
   │     │
   │     ├──► x86_64-bare-metal              (M16+ kernel)
   │     │    as --32 + ld -m elf_i386
   │     │    ──► hamnix-vmlinux.elf
   │     │    ──► QEMU/SeaBIOS/OVMF ──► long mode ──► start_kernel()
   │     │
   │     ├──► x86_64-adder-user              (user binaries)
   │     │    as + ld -static  ──► CPL-3 ELF
   │     │    ──► loaded by /init or hamsh exec
   │     │
   │     └──► x86_64-linux-kernel-module     (M1..M15 stock-Linux .ko)
   │          kbuild + modpost ──► .ko
   │          ──► QEMU + busybox initramfs ──► dev-loop closes
```

The x86_64 backend is hand-written — no LLVM. Kernel-codegen constraints
(SysV AMD64 ABI, 16-byte stack alignment, ENDBR64 for IBT, no red zone,
RIP-relative `.rodata`) are emitted directly. See
[`docs/x86-backend.md`](docs/x86-backend.md) for the design rationale.

---

## Agent-orchestrated development

Hamnix is being built with AI-assisted development running in parallel
worktrees. Each independent piece of work happens in a `git worktree`
clone (under `.claude/worktrees/agent-<id>/`); an orchestrator session
on `main` reviews and applies the commits. Per-worktree build locks
(M16.141 in [STATUS.md](STATUS.md)) keep concurrent worktree builds
genuinely independent — the global lock that used to serialize them
artificially is gone.

Discipline rules enforced in agent prompts:
- Agents commit on their throwaway branch; only the orchestrator pushes
  to `origin`.
- Agents must use `git add <specific paths>` — never `-A` or `.` — so
  one agent can't absorb a sibling's WIP into its commit.
- `README.md`, `TODO.md`, and `STATUS.md` are orchestrator-only.
- Commit-immediately discipline: an agent commits the moment its
  directly-relevant test passes, BEFORE running the broader regression
  sweep. This guarantees real work survives test-infrastructure flakes.

If the workflow itself is interesting to you, the orchestrator's
hands-on observations live in [`memory/`](memory/) — the per-session
project memory that drives orchestrator decisions. The pattern is
honest about what was tried, what was fixed at the source, and what
was a phantom; see [`memory/feedback_compiler_quirks.md`](memory/feedback_compiler_quirks.md)
for the canonical example.

---

## Project structure

```
compiler/        Adder compiler (CPython-hosted)
  adder.py        CLI: --target= x86_64-{bare-metal,adder-user,linux-kernel-module}
  lexer.py        Tokenizer (digit-leading idents per M16.135)
  parser.py       Recursive-descent parser → AST
  codegen_x86.py  x86_64 backend (hand-written)

arch/x86/        Architecture-specific kernel code (mirrors Linux layout)
  boot/           multiboot1 header + EFI PE/COFF stub + GDT/long mode
  kernel/         IDT, IRQ, syscalls, scheduler hooks, time, APIC, SMP
  realmode/       AP bring-up trampoline
  mm/             page tables

drivers/         Native Adder drivers
  ata/            AHCI
  nvme/           NVMe (PRP1+PRP2+PRP-list)
  net/            virtio-net, e1000e, r8169 + ARP/IP/UDP/TCP/ICMP/DHCP/DNS/HTTP/TLS
  block/          partition table parser (MBR+GPT, read+write)
  input/          atkbd (PS/2), auxmouse (PS/2)
  usb/            xHCI + HID boot keyboard
  tty/serial/     16550A UART
  video/console/  VGA text + EFI GOP framebuffer text mode
  pci/            PCI config-space scan

mm/              Memory management (memblock → page_alloc → slab/kmalloc)
kernel/sched/    Task struct, preemptive scheduler, per-task PML4
kernel/printk/   printk family
fs/              VFS, cpio initramfs, pipe, socketpair, ext4, fat
sys/src/9/port/  Plan 9 kernel surface — channels, namespaces, cdevs
lib/9p/          9P2000 codec library
linux_abi/       Layer-2 Linux syscall shims
user/            Hamnix-authored userland (hamsh, init, hamwd, p9srv_demo, …)
init/            start_kernel(), /init shim, boot smoke tests

kernel-modules/  M1..M15 stock-Linux .ko regression baseline
tests/           Integration tests + compiler regression fixtures
scripts/         Build + test harness (build_iso.sh, test_*.sh, …)

docs/            Project documentation (see index below)
memory/          Orchestrator session memory (not in repo)
```

---

## Documentation index

- [`STATUS.md`](STATUS.md) — full M / L / U milestone log (this is the
  changelog).
- [`docs/architecture.md`](docs/architecture.md) — the layered model
  (Layer 0..5), migration plan, per-subsystem layer assignment.
- [`docs/native-api.md`](docs/native-api.md) — Plan 9-shape syscall
  reference + migration table.
- [`docs/9p.md`](docs/9p.md) — 9P2000 wire spec.
- [`docs/rio.md`](docs/rio.md) — file-based window system spec
  (Plan 9 rio shape). Supersedes the older `docs/vtnext-v2.md`.
- [`docs/BOOT.md`](docs/BOOT.md) — building + booting the ISO,
  real-hardware notes.
- [`docs/REAL_HARDWARE.md`](docs/REAL_HARDWARE.md) — how to test on
  physical hardware (USB-stick `dd` recipe, known device caveats).
- [`docs/x86-backend.md`](docs/x86-backend.md) — why the backend is
  hand-written.
- [`docs/L_TRACK_HOWTO.md`](docs/L_TRACK_HOWTO.md) — adding a stock-
  Debian `.ko` to the L-track.
- [`docs/distro-namespaces.md`](docs/distro-namespaces.md) — Phase C.5
  distro-shape namespace design.
- [`LANGUAGE.md`](LANGUAGE.md) — Adder language reference.
- [`TODO.md`](TODO.md) — open work items, organised by layer.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — agent + human workflow.

---

## Working agreements

- Each Adder language extension lands with a `LANGUAGE.md` sentence,
  a test fixture in `tests/`, and a real use site that justified it.
- Small commits that boot. A non-loading `.ko` is worse than fewer
  features.
- When a kernel idiom is awkward, propose a minimal language extension
  before working around it.
- Real bugs get real fixes. Codegen workarounds in driver code accrue
  debt; **every new compiler quirk lands a regression test in
  `tests/test_compiler_*.ad`** so the next driver doesn't trip on it.
  Three quirks landed proper fixes in M16.135; the pattern repeats.
- Naming: **the language and compiler are `Adder`. The OS is `Hamnix`.**
  Source files end in `.ad`; the build tree is `Hamnix/`; the compiler
  CLI is `python3 -m compiler.adder`.
- Kernel codegen constraints honored as code is written: SysV AMD64
  ABI, 16-byte stack alignment, ENDBR64, no red zone, RIP-relative
  `.rodata`. Initial development targets a custom kernel with
  mitigations off; ratchet them on as the codegen matures.

---

## License

GPL-3.0 — see [LICENSE](LICENSE).
