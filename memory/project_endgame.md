---
name: project-endgame
description: Hamnix's long-term goal — full Linux ABI (kernel + userspace) + Debian repo + NVIDIA — shippable distribution
metadata:
  node_type: memory
  type: project
  originSessionId: 87369342-5631-4e0b-b8bd-c6f8925641a7
---

## Hamnix end-game (as of 2026-05-15)

Hamnix is being built toward a real, shippable Linux-compatible
distribution that mostly runs Hamnix's own code but consumes
Debian's package repositories for everything else.

**The full stack (in dependency order):**

1. **M-series (M1..M16.x)** — DONE / IN PROGRESS. Bare-metal x86_64
   kernel written in Adder. Block layer, ext4 r/w, FAT r, VFS,
   procfs, tmpfs, /dev nodes, RTC, PS/2 keyboard, hamsh shell,
   ~55 user binaries.

2. **L-series (Linux KERNEL ABI)** — IN PROGRESS (M16.80+ checkpoint).
   Binary compatibility with stock Linux 6.12 .ko modules.
   Loading hello.ko → loading distro modules → loading xhci_hcd,
   nvme, usbhid → boot on real ThinkPad hardware (L40).

3. **U-series (Linux USERSPACE ABI)** — NOT STARTED. Run unmodified
   Linux user binaries (Steam, Firefox, etc). Implies:
   * /lib/ld-linux-x86-64.so.2 dynamic linker (or compat shim)
   * glibc syscall ABI (Linux syscall numbers + signatures)
   * /proc layout matching Linux's enough that glibc's runtime
     setup doesn't panic
   * /sys layout for hardware introspection
   * sysfs for udev / systemd-style device discovery
   * Linux ioctl numbers for terminal, networking, block devices
   * Process model: PID 1, sessions, groups, capabilities
   * Threading primitives: futex syscall, clone CLONE_THREAD
   * Mmap layout matching what dynamic linkers assume

4. **NVIDIA driver support** — END GAME. Implies a working enough
   Linux KERNEL ABI (L-series) that the closed-source
   nvidia.ko + companion modules load + initialize. Plus a
   working enough USERSPACE ABI (U-series) that the userspace
   libraries (libnvidia-glcore.so, libcuda.so, etc) link and run.

5. **Debian repository compatibility** — SHIPPING GATE. Hamnix
   shipped as a real distribution:
   * .deb package install path (dpkg / apt compatibility)
   * Debian's /etc layout, /lib layout, /var/lib/dpkg state
   * Most installable packages just work because Linux ABI is
     done
   * The MAJORITY of the system is Hamnix-authored: bootloader,
     kernel, init, shell, coreutils. Debian provides the
     long-tail userspace: editors, browsers, language runtimes,
     graphical environments.

**Why this matters:**

- Hamnix becomes a real OS, not a hobby kernel. Users can run
  whatever they need without waiting for Hamnix to reimplement it.
- The OS author retains control of the SECURITY-CRITICAL surface
  (boot, kernel, init, shell) while leveraging the world's
  largest free-software repository for everything else.
- NVIDIA support specifically is the "this can be my daily
  driver" test — gamers + ML researchers + scientists all need
  it, and proving it works validates the L-series ABI work.

**How to apply:**

When making architectural choices, prefer ones that don't burn
bridges to Linux compatibility:
- File system layouts: stick to Linux conventions (/etc, /bin,
  /lib, /usr, /var, /tmp, /proc, /sys, /dev).
- Syscall numbers: when adding new syscalls, allocate them
  in a range that doesn't collide with Linux's x86_64 syscall
  numbers (0..400+). Use a high range (e.g. 1000+) for
  Hamnix-specific ones.
- Init system: don't lock in to a non-Linux model. The L-series
  insmod already uses Linux numbers (175/176).
- Kernel data structures: prefer matching Linux's layouts even
  when re-implementing from scratch — saves a translation
  layer later. (The L0 BTF generator already does this.)

The order is L-series → U-series → NVIDIA → Debian shipping. Skip
none.
