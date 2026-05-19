---
name: project-coverage-state
description: Subsystems Pynux has touched as of 2026-05-15 — 38 modules covering most major kernel API categories
metadata: 
  node_type: memory
  type: project
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

As of 2026-05-15, **38 Pynux kernel modules pass end-to-end** under
QEMU on a custom mitigations-off Linux 6.12.48. Far past the original
brief's three milestones; effectively a complete tour of the
mainstream kernel API.

**Subsystem coverage** (each demonstrated by at least one Pynux module):
- **Driver registration**: virtio (blk+net), char device (×4 — pynux,
  pynurand, pynuxzero, pynuxnull), file_system (full ramfs), console
  (16550A), procfs, sysfs (kobject + attribute), debugfs (u32),
  dummy net_device (eth1).
- **Async / deferred work**: kthread + workqueue + delayed_work, IRQ
  handler (request_threaded_irq), jiffies timer + hrtimer, ktime_get.
- **Memory**: dma_alloc_attrs, kmem_cache (slab), kmalloc.
- **Synchronization**: spin_lock_irqsave, mutex, completion,
  wait_queue, atomic_t via `lock incl` inline asm.
- **Introspection / observability**: kprobe (M7.1), kprobe with
  payload capture (M14.1 — reads syscall filename via
  copy_from_user_nofault), kretprobe (M14.2 — captures return
  values), sysfs, debugfs, current_task via %gs:pcpu_hot,
  smp_processor_id via %gs:pcpu_hot+12.
- **Data structures**: list_head intrusive list reimplemented in pure
  Pynux.
- **Networking**: virtio-net probe + MAC read, netfilter hook on
  NF_INET_PRE_ROUTING + packet inspector (parses sk_buff →
  IPv4 src/dst), kernel UDP socket via sock_create_kern +
  kernel_bind, dummy ethernet net_device with ndo_open/stop/xmit.
- **Crypto**: SHA-256 via crypto_alloc_shash +
  crypto_shash_tfm_digest.
- **CSPRNG**: get_random_bytes + _copy_to_user → /dev/pynurand.
- **VFS**: full ramfs (mount, file create/write/read, mkdir/rmdir/rm).
- **VirtIO**: full path through find_vqs vtable → DMA buffer → SG list
  → kick → get_buf (proven on virtio-blk reading sector 0).
- **Kernel state introspection**: read pid+comm of current task,
  current CPU id, kernel release string ("6.12.48") from init_uts_ns.

**Why this matters / how to apply:**
- The imperative-init pattern (zero-init global struct, populate
  fields field-by-field in init_module, register via the kernel API)
  is the established Pynux idiom. Use it for every new subsystem.
- Most kernel "register_X" helpers are static inlines that call
  underlying `__X` / `__register_X` / `register_X_args` exports.
  Always check `include/linux/*.h` before declaring an extern — what
  you grep for may not be a real symbol.
- Indirect calls via local function pointers WORK in the codegen
  (added during M4.2 for vdev->config->find_vqs).
- `asm_volatile("inst")` is the language addition for inline asm;
  only zero-operand for now. Sufficient for `pause`/`cli`/`sti`/
  `mfence`/`lock incl`/`%gs:sym` reads.
- Variadic-extern calls (e.g. _printk) zero %al before the call
  thanks to the codegen's blanket `xorl %eax, %eax` before every
  `call`.
- Probe struct layouts via /tmp/probe/probe.c (one C kernel module
  printing sizeof + offsetof) before mirroring them in Pynux. Layouts
  are kernel-version-specific.
- A comment line immediately after `class X:` confuses the parser —
  put the comment ABOVE the class instead.

See [[project-m1-complete]] [[project-m2-complete]] [[project-m3-complete]]
for milestone history.
