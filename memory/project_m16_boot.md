---
name: project-m16-boot
description: "M16 boot history (2026-05-15, Pynux-era). PARTLY SUPERSEDED 2026-05-20: kernel is now elf64-x86-64, higher-half at 0xffffffff80000000 — the elf32 'decisions' below are stale."
metadata: 
  node_type: memory
  type: project
  originSessionId: fe0d7e45-ec05-4c40-bb83-081a2ddfe24d
---

**SUPERSEDED IN PART 2026-05-20.** The kernel was relocated to the
higher half (`0xffffffff80000000`, PML4 entry 511) and the boot format
changed from `elf32-i386` to `elf64-x86-64` — commits `406c313` +
`da065ec` on `main`. This INVALIDATES the elf32 items in "Non-obvious
decisions" below: the build is now elf64 (`as --64`, `ld -m elf_x86_64`),
`.quad sym` / `movabsq` ARE now used, the linker script has a LMA/VMA
split with a low boot region + high-half kernel, and QEMU's multiboot1
`-kernel` can't load it — tests boot via a BIOS-GRUB-ISO PATH shim
(`scripts/_kernel_iso.sh`). The `.pgtables`-outside-`.bss` rule still
holds. The M16.1-7 milestone history below is kept as history only.

---

M16 is the pivot from "Pynux as .ko modules inside stock Linux" (M1..M15)
to "Pynux compiles its own kernel image". As of 2026-05-15 the bare-metal
kernel image at `build/pynux-vmlinux.elf` boots, handles interrupts,
schedules cooperative kernel threads, and uses Linux-style printk.

**Why:** the .ko path could never reach a true Linux replacement —
boot, MM, scheduler, syscall entry, and the module ABI all stay owned by
stock Linux. M16 takes ownership of those layers.

**How to apply:** future M16.x work expands `init/main.py` and the
subsystems to mirror Linux's `init/main.c:start_kernel`. Read the
equivalent Linux file in `~/pynux-kernel/linux/` and port. Track Linux
function names where possible. The 40 existing `.ko` modules in
`kernel-modules/` still build against stock Linux as a regression
baseline; they will be re-targeted only after the relevant subsystems
land.

## Milestones shipped 2026-05-15

- **M16.1**: Boot path — multiboot1 header, 32→64 long-mode transition,
  start_kernel(), 16550A UART banner. Pivot moment.
- **M16.2**: IDT + trap handlers — 32 vector stubs + common_trap +
  Pynux do_trap(). INT3 smoke test confirms dispatch.
- **M16.3**: memblock bump allocator — fixed 2 MiB..240 MiB range,
  aligned alloc, mem_init().
- **M16.4**: per-CPU areas — page-sized area, IA32_GS_BASE loaded,
  smp_processor_id() = `mov %gs:0, %rax`.
- **M16.5**: PIC + PIT timer + jiffies — 8259 remap to vectors 0x20-0x2F,
  PIT @ 100 Hz, first real hardware IRQ handled. common_irq returns
  via iretq (vs common_trap which halts).
- **M16.6**: Cooperative scheduler — __switch_to_asm saves/restores SysV
  callee-saved set + RSP; kthread_create pre-builds the task stack;
  3-slot runqueue (0 = init, 1..2 = workers); two demo threads print
  "ABABAB...".
- **M16.7**: printk0/printk1/printk2 with %d/%x/%s/%p/%c. Replaces the
  piecemeal early_puts+early_print_hex64 idiom across init/main.py.

## Layout (mirrors Linux source tree)

```
Pynux/
  arch/x86/boot/header.S            multiboot1 + 32->64 transition
  arch/x86/kernel/head_64.S         64-bit entry, BSS-zero, call start_kernel
  arch/x86/kernel/vmlinux.lds       linker script (OUTPUT_FORMAT elf32-i386)
  arch/x86/kernel/idt_asm.S         per-vector trap stubs, common_trap,
                                    get_trap_stub, idt_load, trigger_int3
  arch/x86/kernel/idt.py            gate descriptor packing, idt_init()
  arch/x86/kernel/traps.py          do_trap() body + hex printing
  arch/x86/kernel/irq_asm.S         per-IRQ stubs, common_irq (iretq),
                                    get_irq_stub, local_irq_enable/disable,
                                    cpu_relax
  arch/x86/kernel/irq.py            do_irq() vector dispatch
  arch/x86/kernel/i8259.py          8259 PIC init/mask/unmask/EOI
  arch/x86/kernel/time.py           PIT @ 100 Hz, jiffies, timer_interrupt
  arch/x86/kernel/setup_percpu_asm.S wrmsr_gsbase, read_cpu_id_percpu
  arch/x86/kernel/setup_percpu.py   setup_per_cpu_areas, get_cpu_id
  arch/x86/kernel/sched_asm.S       __switch_to_asm (the actual context switch)
  arch/x86/mm/init.py               mem_init() arch-side entry
  kernel/sched/core.py              task_struct, kthread_create, schedule()
  kernel/printk/printk.py           printk0/1/2 + %d/%x/%s/%p/%c
  mm/memblock.py                    memblock_init/_alloc/_used/_avail
  drivers/tty/serial/early_8250.py  polled 16550A UART + hex print helpers
  init/main.py                      start_kernel()
  scripts/run_x86_bare.sh           QEMU runner
```

## Non-obvious decisions (record so we don't re-derive)

- **Build target is `elf32-i386`, not `elf64-x86-64`**: QEMU's
  multiboot1 loader requires ELFCLASS32 ("Cannot load x86-64 image,
  give a 32bit one."). Workaround: assemble all .S with `as --32`,
  but prepend `.code64` to Pynux-emitted .S and put `.code64`
  directives at the top of head_64.S / idt_asm.S / irq_asm.S /
  sched_asm.S / setup_percpu_asm.S. The assembler emits 64-bit
  instruction bytes; only the ELF wrapper is 32-bit. Linker:
  `ld -m elf_i386 -T vmlinux.lds`.
- **No `.quad sym` and no `movabsq $sym, %reg`**: 64-bit symbol
  relocations don't fit in elf32-i386. Use `movl $sym, %reg`
  (zero-extends in long mode) and `.long sym; .long 0` for 8-byte
  table slots that need to look like uint64 at runtime.
- **Page tables MUST be outside `[__bss_start, __bss_end)`**: head_64.S
  zeroes BSS with paging already on, so PT in .bss triple-faults. The
  `.pgtables` NOLOAD section in vmlinux.lds keeps pml4/pdpt/pd safe.
- **CastExpr is a no-op in x86 codegen**: integer types all share the
  same 64-bit register encoding; cast is just a type-system hint. This
  is added codegen support — pynux ARM did it; x86 didn't until M16.2.
- **`while value > 0` is signed**: 0xFFFFFFFFFFFFFFFF compares as -1
  and loops zero times. Use `value != 0` in unsigned loops (decimal /
  hex printing in kernel/printk/printk.py).
- **DIV codegen is unsigned (divq, xor %rdx)**: Pynux currently only
  emits unsigned division on x86. PIT divisor math and printk's
  decimal print both rely on this — signed division will need a
  separate codepath keyed on operand type.
- **Per-CPU + scheduler**: __switch_to_asm preserves SysV callee-saved
  set + RSP only. The %gs base set by setup_per_cpu_areas is per-CPU,
  not per-task, so it survives context switches without explicit save.
  When SMP lands, each AP will have its own GSBASE.
- **Multiboot header at file offset 0x1000**: within the multiboot1
  8 KiB window. `.head.text` first in the linker script.
- **`-kernel` boots through SeaBIOS**: QEMU always launches SeaBIOS as
  firmware; SeaBIOS reads the kernel via fw_cfg and jumps to it. The
  "Booting from ROM.." line precedes our banner — not a fallback path.

## Compiler integration

`compiler/pynux.py` TARGETS:
```
"x86_64-bare-metal": {"codegen": "x86", "kbuild": False, "bare_metal": True}
```
The `bare_metal` flag is threaded into `X86CodeGen.__init__` and gates
`gen_modinfo()` (only meaningful for .ko targets).
`assemble_and_link_x86_bare()` dispatches by target: `arm-cortex-m3`
uses the legacy ARM path, `x86_64-bare-metal` uses
`as --32` + `ld -m elf_i386` on every .S file under `arch/x86/`.
New .S files are picked up automatically — drop one in arch/x86/{boot,kernel}
and rebuild.

Codegen additions during M16:
- CastExpr lowering (no-op, added M16.2)
- BinOp.DIV / IDIV / MOD using divq + xorq %rdx (added M16.5)

## Verified success (M16.1-7)

`bash scripts/run_x86_bare.sh` produces over serial (excerpt):
```
Pynux kernel booting...
Pynux: trap_init done
Pynux: memblock smoke test
  alloc(128,16) = 0x0000000000200000
  ...
Pynux: smp_processor_id() = 0
Pynux: PIT @ 100 Hz armed, enabling IRQs
  jiffies = 1 .. 5
Pynux: two kthreads created, entering scheduler
ABABABABABABABABABABABABABABAB
Pynux: M16.x demo done, halting
```

m15-kfifo .ko regression in QEMU still passes (verified after every
codegen change).

## Next steps

- M16.8: preemption — hook schedule() into the timer ISR so greedy
  tasks lose CPU. Needs careful IRQ-frame management on the task stack.
- M16.9: panic() + WARN_ON() — small but pervasive.
- M16.10: kmalloc / slab on top of memblock (mm/slub.c).
- M16.11: parse multiboot info struct to discover real memory ranges
  (replace hardcoded 2..240 MiB range with e820-equivalent walk).
- M16.12: ACPI tables (madt for SMP, fadt for shutdown).

Related: [[project-x86-backend-decision]], [[project-real-hw-boot]].
