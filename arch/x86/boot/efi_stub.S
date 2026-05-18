/*
 * arch/x86/boot/efi_stub.S - Hamnix native UEFI PE/COFF entry stub.
 *
 * This file is assembled and linked into a standalone PE32+ EFI application
 * (`build/hamnix-bootx64.efi`) that UEFI firmware loads directly from the
 * EFI System Partition at \EFI\BOOT\BOOTX64.EFI. No GRUB-EFI middleman.
 *
 * Mirrors the role of arch/x86/boot/header.S for the multiboot1 path:
 * it is the first piece of Hamnix code firmware executes. Where header.S
 * has to crawl out of 32-bit protected mode into long mode, the EFI entry
 * arrives already in 64-bit long mode with identity-mapped low memory and
 * boot services still active.
 *
 * What this stub does today (EFI handoff completion):
 *   1. Receive EFI_HANDLE in %rcx, EFI_SYSTEM_TABLE* in %rdx (Microsoft
 *      x64 calling convention, per UEFI Specification 2.x §2.3.4).
 *   2. Stash both into well-known globals (efi_image_handle /
 *      efi_system_table) so any later kernel code can pull them back.
 *   3. Write "[hamnix] EFI entry reached\r\n" to the 16550A UART at
 *      COM1 / port 0x3F8. UEFI does not claim port I/O so we can talk
 *      to the legacy UART directly; this is also how the QEMU
 *      `-serial stdio` test capture sees it.
 *   4. Call BootServices->GetMemoryMap() into a 16 KiB static buffer
 *      in .data to obtain the current MapKey.
 *   5. Call BootServices->ExitBootServices(ImageHandle, MapKey). UEFI
 *      requires this before the OS may program its own paging /
 *      interrupt state. The call may return EFI_INVALID_PARAMETER if
 *      the MapKey is stale (firmware allocated something between our
 *      GetMemoryMap and ExitBootServices); on that error we retry the
 *      GetMemoryMap + ExitBootServices pair up to a bounded count.
 *   6. Write "[hamnix] post-EFI handoff complete\r\n" to COM1. By this
 *      point firmware boot services are gone: no more boot-services
 *      timers, no more behind-the-back memory manager. This is the
 *      marker the test script asserts AFTER "EFI entry reached" — it
 *      ONLY fires when the ExitBootServices handshake succeeded.
 *   7. Halt forever (cli; hlt; jmp $-).
 *
 * Why halt after ExitBootServices instead of jumping to start_kernel:
 *   The kernel ELF is currently a SEPARATE binary from this stub
 *   (build/hamnix-vmlinux.elf vs. build/hamnix-bootx64.efi); UEFI
 *   loaded only the stub, so the kernel's .text isn't in memory.
 *   Completing the boot would require either (a) using UEFI's Simple
 *   File System Protocol BEFORE ExitBootServices to read the ELF off
 *   the ESP, parse it, and copy PT_LOADs to their LMA; or (b) merging
 *   the two binaries into one hybrid file (PE header + multiboot1
 *   header at the same offset 0). Both are larger commits. This
 *   commit's win is that the EFI side of the handshake now actually
 *   completes — proven by the second marker firing after firmware has
 *   relinquished control. head_64.S grew a `_x86_start_after_loader`
 *   symbol pre-positioning the merge point for that follow-up.
 *
 * Build:
 *   The Hamnix compiler still emits ELF for the multiboot1 kernel image.
 *   This file is assembled with `as --64` (true 64-bit elf64-x86-64) and
 *   linked with `ld -m i386pep --subsystem 10` to produce a true PE32+
 *   EFI_APPLICATION. See scripts/build_iso.sh for the exact invocation.
 *   Two separate output binaries — see docs/BOOT.md for why.
 */

    .code64

    /* Size of the static memory-map buffer in .bss. Referenced from
     * both .text (resetting efi_mmap_size on each retry) and .bss
     * (the .skip count); define once at the top to keep them in sync. */
    .equ EFI_MMAP_BUF_SIZE, 16384

    /* Bounded retries on ExitBootServices. Standard EFI handoff
     * pattern: ExitBootServices can fail with EFI_INVALID_PARAMETER
     * if firmware allocated memory between our GetMemoryMap and
     * ExitBootServices, invalidating the MapKey. The fix is to
     * re-run GetMemoryMap and try again. 4 attempts is sufficient
     * for every UEFI firmware in practice; more usually indicates
     * firmware doing something pathological (a polling event
     * spawning allocations on every tick). */
    .equ EFI_EXIT_RETRY_MAX, 4

    .section .text, "ax"

    .globl  efi_main
efi_main:
    /* Microsoft x64 calling convention:
     *   %rcx = EFI_HANDLE       ImageHandle
     *   %rdx = EFI_SYSTEM_TABLE *SystemTable
     * UEFI doesn't expect a frame; we stash both before doing anything
     * else so a later kernel handoff can pull them back. */
    cli
    movq    %rcx, efi_image_handle(%rip)
    movq    %rdx, efi_system_table(%rip)

    /* Anchor a stack of our own. UEFI provides a stack but the size is
     * implementation-defined (typically 128 KiB on edk2 OVMF); switching
     * to our own keeps later kernel handoff straightforward and gives
     * us a known 16 KiB region. The PE linker puts efi_stub_stack_top
     * in .bss, 16-aligned.
     *
     * Microsoft x64 ABI requires the stack pointer to be 16-byte aligned
     * at every CALL site such that on entry to the callee, [rsp+8] is
     * 16-aligned. efi_stub_stack_top is 16-aligned in .bss; we subtract
     * a multiple of 16 before each CALL to keep alignment correct. */
    leaq    efi_stub_stack_top(%rip), %rsp

    /* Print "[hamnix] EFI entry reached\r\n" over COM1. */
    leaq    efi_marker_msg(%rip), %rsi
    call    efi_serial_puts

    /* ---- EFI handoff: GetMemoryMap + ExitBootServices --------------
     *
     * EFI_BOOT_SERVICES function pointer offsets (from UEFI 2.x spec
     * §4.4 EFI_BOOT_SERVICES table layout — these offsets are stable
     * across past, present, and future spec revisions):
     *
     *   off  56  GetMemoryMap
     *   off 232  ExitBootServices
     *
     * GetMemoryMap signature (Microsoft x64 ABI):
     *   EFI_STATUS GetMemoryMap(
     *     IN OUT UINTN  *MemoryMapSize,           // RCX
     *     OUT EFI_MEMORY_DESCRIPTOR *MemoryMap,    // RDX
     *     OUT UINTN  *MapKey,                     // R8
     *     OUT UINTN  *DescriptorSize,             // R9
     *     OUT UINT32 *DescriptorVersion);         // [RSP+32]
     *
     * ExitBootServices signature:
     *   EFI_STATUS ExitBootServices(
     *     IN EFI_HANDLE ImageHandle,   // RCX
     *     IN UINTN MapKey);            // RDX
     *
     * EFI_SYSTEM_TABLE layout (only the slot we need):
     *   off 96  EFI_BOOT_SERVICES *BootServices
     *
     * Microsoft x64 calling convention requires:
     *   - 32 bytes of "shadow space" on the stack for the 4 register
     *     args (the callee may spill them there).
     *   - 16-byte stack alignment at the CALL site, so after CALL
     *     pushes the return address (8 bytes), [RSP+8] is 16-aligned
     *     on entry.
     *   - Stack args beyond the 4th go at [RSP+32], [RSP+40], etc.
     */

    /* Cache BootServices pointer once. */
    movq    efi_system_table(%rip), %rax
    movq    96(%rax), %rax
    movq    %rax, efi_boot_services(%rip)

    /* Retry counter lives in %rbx (callee-saved under MS x64). */
    movl    $0, %ebx

.Lefi_exit_retry:
    /* --- 1. Reset the map-size scratch to the buffer capacity. -----
     *
     * GetMemoryMap reads the IN value of *MemoryMapSize as "how much
     * room you've got" and writes back "how much I actually used"
     * (or "how much I needed" if EFI_BUFFER_TOO_SMALL). On retry we
     * must reset it to our buffer's capacity each pass. */
    movq    $EFI_MMAP_BUF_SIZE, efi_mmap_size(%rip)

    /* --- 2. Call BootServices->GetMemoryMap() ----------------------
     *
     *   rcx = &efi_mmap_size
     *   rdx = efi_mmap_buf
     *   r8  = &efi_mmap_key
     *   r9  = &efi_mmap_descsize
     *   [rsp+32] = &efi_mmap_descver
     *
     * Stack layout below the new %rsp (48 bytes = multiple of 16,
     * so 16-byte alignment is preserved across the call):
     *
     *   [rsp+0x00]  shadow rcx slot
     *   [rsp+0x08]  shadow rdx slot
     *   [rsp+0x10]  shadow r8  slot
     *   [rsp+0x18]  shadow r9  slot
     *   [rsp+0x20]  5th arg: &efi_mmap_descver
     *   [rsp+0x28]  pad
     */
    leaq    efi_mmap_size(%rip),     %rcx
    leaq    efi_mmap_buf(%rip),      %rdx
    leaq    efi_mmap_key(%rip),      %r8
    leaq    efi_mmap_descsize(%rip), %r9
    subq    $0x30, %rsp
    leaq    efi_mmap_descver(%rip), %r10
    movq    %r10, 0x20(%rsp)
    movq    efi_boot_services(%rip), %rax
    movq    56(%rax), %rax              /* ->GetMemoryMap */
    call    *%rax
    addq    $0x30, %rsp
    /* Ignore EFI_BUFFER_TOO_SMALL here: the buffer is 16 KiB which is
     * plenty for any plausible firmware (OVMF on 256 MiB RAM produces
     * ~30 descriptors at 48 bytes each = ~1.4 KiB). If GetMemoryMap
     * fails outright we fall through into ExitBootServices with
     * whatever MapKey is in efi_mmap_key, which will fail too — the
     * retry loop catches that. */

    /* --- 3. Call BootServices->ExitBootServices(ImageHandle, MapKey).
     *
     *   rcx = efi_image_handle
     *   rdx = efi_mmap_key
     *
     * 32 bytes of shadow space + 16-aligned stack. */
    movq    efi_image_handle(%rip), %rcx
    movq    efi_mmap_key(%rip),     %rdx
    movq    efi_boot_services(%rip), %rax
    movq    232(%rax), %rax             /* ->ExitBootServices */
    subq    $0x20, %rsp
    call    *%rax
    addq    $0x20, %rsp

    /* Success = EFI_SUCCESS = 0. On any other return, retry up to
     * EFI_EXIT_RETRY_MAX times — the canonical EFI handoff pattern. */
    testq   %rax, %rax
    jz      .Lefi_exit_ok

    incl    %ebx
    cmpl    $EFI_EXIT_RETRY_MAX, %ebx
    jb      .Lefi_exit_retry

    /* Out of retries. Print a fail marker and halt. Useful for
     * post-mortem on real hardware: the box is dead either way, but
     * the serial cable tells us we never got past firmware. */
    leaq    efi_exit_fail_msg(%rip), %rsi
    call    efi_serial_puts
    jmp     .Lefi_halt

.Lefi_exit_ok:
    /* From here on, firmware boot services are GONE. We own the CPU,
     * the memory map (such as we've parsed it), and the platform.
     *
     * Print the post-handoff marker. This is the line the test script
     * asserts AFTER "EFI entry reached" — its appearance proves
     * ExitBootServices returned EFI_SUCCESS, meaning firmware accepted
     * our MapKey and is now out of the boot path. */
    leaq    efi_post_handoff_msg(%rip), %rsi
    call    efi_serial_puts

    /* Next steps the follow-up commit takes from here (not in this
     * commit):
     *   - Load our own GDT via `lgdt` (firmware's GDT is no longer
     *     guaranteed valid post-ExitBootServices on every firmware;
     *     we currently rely on it only for halt).
     *   - Set CR3 to a PML4 we built ourselves.
     *   - jmp _x86_start_after_loader (defined in head_64.S).
     *
     * Today we halt. The next bring-up step is gated on linking the
     * EFI stub and the kernel ELF into one image so the stub can
     * reach kernel symbols. */
.Lefi_halt:
    cli
    hlt
    jmp     .Lefi_halt

    .globl  efi_main_end
efi_main_end:


/* efi_serial_puts:
 *   %rsi = pointer to NUL-terminated ASCII string
 *   Trashes: %rax, %rcx, %rdx, %rsi (caller-saved under MS x64)
 *
 * Writes each byte to port 0x3F8 after polling LSR bit 5 (THR empty).
 * Tight loop — no timeout. If the UART is dead this hangs, but the
 * outer code halts the CPU anyway and a hung CPU after a dead UART
 * is the same observable state on real hardware (silent box). */
efi_serial_puts:
    movw    $0x3F8, %dx
.Lputs_next:
    movb    (%rsi), %al
    testb   %al, %al
    jz      .Lputs_done
    /* Wait for THR empty (LSR bit 5). */
    movw    $0x3FD, %dx
.Lputs_wait:
    inb     %dx, %al
    testb   $0x20, %al
    jz      .Lputs_wait
    /* Restore the byte to send — inb clobbered %al. */
    movb    (%rsi), %al
    movw    $0x3F8, %dx
    outb    %al, %dx
    incq    %rsi
    jmp     .Lputs_next
.Lputs_done:
    ret


/* ---------- Read-only data --------------------------------------- */
    .section .rdata, "a"
    .align 8
efi_marker_msg:
    .asciz  "[hamnix] EFI entry reached\r\n"
efi_post_handoff_msg:
    .asciz  "[hamnix] post-EFI handoff complete\r\n"
efi_exit_fail_msg:
    .asciz  "[hamnix] EFI ExitBootServices retries exhausted; halt\r\n"


/* ---------- Writable data --------------------------------------- *
 * Stashed firmware handoff state. The follow-up kernel-handoff
 * commit can pull these back without threading them through
 * %rcx/%rdx by hand. */
    .section .data, "aw"
    .align 8
    .globl efi_image_handle
efi_image_handle:
    .quad 0
    .globl efi_system_table
efi_system_table:
    .quad 0
    /* Cached EFI_BOOT_SERVICES*, derived from system_table before
     * the first GetMemoryMap and reused for ExitBootServices. */
    .globl efi_boot_services
efi_boot_services:
    .quad 0
    /* GetMemoryMap scratch slots. EFI writes the actual map size,
     * map key, descriptor size, and descriptor version into these
     * uint64 slots. MapKey, MemoryMapSize, and DescriptorSize are
     * UINTN — 64-bit on x86_64. DescriptorVersion is UINT32 but
     * reading the slot as uint64 is harmless: ExitBootServices
     * never reads it. */
    .align 8
    .globl efi_mmap_size
efi_mmap_size:
    .quad 0
    .globl efi_mmap_key
efi_mmap_key:
    .quad 0
    .globl efi_mmap_descsize
efi_mmap_descsize:
    .quad 0
    .globl efi_mmap_descver
efi_mmap_descver:
    .quad 0


/* ---------- BSS: our own stack + memory-map buffer --------------- *
 * Stack: 16 KiB matches arch/x86/boot/header.S's boot_stack —
 * symmetry helps future kernel-handoff debugging when both paths
 * land in start_kernel with a comparable stack profile.
 *
 * Memory-map buffer: 16 KiB. EFI_MEMORY_DESCRIPTOR is 40 bytes
 * per the UEFI spec (most firmwares pad to 48 in the descriptor-
 * size field for forward compat); 16 KiB holds ~341 entries, far
 * more than any plausible firmware reports. OVMF on 256 MiB
 * returns ~30; real workstations with 64 GiB return ~150 entries.
 * The buffer must be reachable when boot services are still active
 * (i.e. in our own image's .bss); PE/COFF .bss is loaded NOBITS,
 * so firmware zero-fills it at image map time — no explicit clear
 * pass needed.
 */
    .section .bss, "aw", @nobits
    .align 16
efi_stub_stack_bottom:
    .skip 16384
    .globl efi_stub_stack_top
efi_stub_stack_top:

    .align 16
    .globl efi_mmap_buf
efi_mmap_buf:
    .skip EFI_MMAP_BUF_SIZE
