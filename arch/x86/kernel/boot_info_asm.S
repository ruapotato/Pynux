/*
 * arch/x86/kernel/boot_info_asm.S - accessors for the multiboot
 * info pointer stashed by the boot stub, plus EFI GOP framebuffer
 * info stashed by the UEFI stub.
 *
 * header.S's 32-bit entry path saves the multiboot magic (EAX) and
 * info pointer (EBX) into two .long slots in .data:
 *      .globl mb_magic
 *      mb_magic: .long 0
 *      .globl mb_info
 *      mb_info:  .long 0
 *
 * On the UEFI path (arch/x86/boot/efi_stub.S), the stub queries the
 * EFI_GRAPHICS_OUTPUT_PROTOCOL via BootServices->LocateProtocol BEFORE
 * ExitBootServices() and stores the framebuffer geometry into the
 * efi_fb_info struct defined below. The stub finds this struct via
 * the handoff table's +64 slot in header.S's multiboot header. After
 * ExitBootServices(), boot-services calls (including LocateProtocol)
 * are no longer legal, so this is the only place we can capture GOP.
 *
 * Why a struct instead of separate flag globals: the EFI stub writes
 * five values at once; one base address + offset writes is fewer asm
 * relocations than five separate symbol references.
 *
 * Hamnix currently has no "extern variable" syntax, so we read those
 * symbols out via tiny accessor functions instead. Both slots store
 * 32-bit values that we zero-extend into a uint64 for the Hamnix
 * caller. The multiboot info struct lives below 4 GiB (multiboot1
 * spec) so the upper bits are genuinely zero.
 */

    .code64
    .section .text, "ax"

    /* Use leaq+movl rather than `movl sym, %eax` to dodge the
     * BFD_RELOC_X86_64_32S that bare absolute addressing generates
     * (elf32-i386 can't represent that). leaq RIP-relative produces
     * R_386_PC32 which fits cleanly. */
    .align 16
    .globl get_mb_magic
get_mb_magic:
    leaq    mb_magic(%rip), %rax
    movl    (%rax), %eax              /* movl zero-extends to %rax  */
    ret

    .align 16
    .globl get_mb_info
get_mb_info:
    leaq    mb_info(%rip), %rax
    movl    (%rax), %eax
    ret

    /* ---- EFI GOP framebuffer accessors --------------------------------
     *
     * efi_fb_info layout (.data, populated by arch/x86/boot/efi_stub.S
     * right before ExitBootServices; zero on the multiboot1 BIOS path):
     *
     *   off  0: uint32 present       (1 = populated, 0 = no GOP captured)
     *   off  4: uint32 width         (HorizontalResolution)
     *   off  8: uint32 height        (VerticalResolution)
     *   off 12: uint32 pitch_bytes   (PixelsPerScanLine × bytes_per_pixel,
     *                                 i.e. the actual byte stride between
     *                                 successive scanlines — UEFI 2.10
     *                                 §12.9.2 says PixelsPerScanLine is
     *                                 *pixels*, so we must multiply by
     *                                 bytes_per_pixel in the stub before
     *                                 storing here)
     *   off 16: uint32 pixel_format  (0 = RGB, 1 = BGR, 2 = BitMask,
     *                                 3 = BltOnly — per
     *                                 EFI_GRAPHICS_PIXEL_FORMAT)
     *   off 20: uint32 bpp           (always 32 today — GOP-reported
     *                                 RGB/BGR formats are 8-bit per
     *                                 channel plus 8-bit reserved)
     *   off 24: uint64 base          (FrameBufferBase — may be above
     *                                 4 GiB on some real hardware; full
     *                                 64-bit slot)
     *   off 32: uint64 size          (FrameBufferSize — total bytes)
     *
     * Total: 40 bytes. The efi_stub.S writes the whole struct in one
     * pass via offset stores from a base register pointing here.
     */
    .align 16
    .globl get_efi_fb_present
get_efi_fb_present:
    leaq    efi_fb_info(%rip), %rax
    movl    0(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_width
get_efi_fb_width:
    leaq    efi_fb_info(%rip), %rax
    movl    4(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_height
get_efi_fb_height:
    leaq    efi_fb_info(%rip), %rax
    movl    8(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_pitch_bytes
get_efi_fb_pitch_bytes:
    leaq    efi_fb_info(%rip), %rax
    movl    12(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_pixel_format
get_efi_fb_pixel_format:
    leaq    efi_fb_info(%rip), %rax
    movl    16(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_bpp
get_efi_fb_bpp:
    leaq    efi_fb_info(%rip), %rax
    movl    20(%rax), %eax
    ret

    /* base + size are 64-bit. Use a paired-load pattern: caller gets
     * the full 64-bit value in %rax. */
    .align 16
    .globl get_efi_fb_base
get_efi_fb_base:
    leaq    efi_fb_info(%rip), %rcx
    movq    24(%rcx), %rax
    ret

    .align 16
    .globl get_efi_fb_size
get_efi_fb_size:
    leaq    efi_fb_info(%rip), %rcx
    movq    32(%rcx), %rax
    ret

    /* ---- EFI GOP framebuffer storage ----------------------------------
     *
     * .data (NOT .bss) so the EFI stub doesn't have to clear it before
     * writing — the .data init pattern leaves it zero at boot and the
     * stub writes the populated fields atomically before ExitBootServices.
     * BIOS multiboot1 boot never touches this region; `present` stays 0
     * and the Adder accessor short-circuits.
     *
     * Address must be reachable via a R_386_32 / 32-bit absolute
     * relocation from the multiboot handoff table planted by header.S
     * (kernel is elf32-i386; VMAs all < 4 GiB).
     */
    .section .data
    .align 8
    .globl efi_fb_info
efi_fb_info:
    .long 0     /* off  0 present       */
    .long 0     /* off  4 width         */
    .long 0     /* off  8 height        */
    .long 0     /* off 12 pitch_bytes   */
    .long 0     /* off 16 pixel_format  */
    .long 0     /* off 20 bpp           */
    .quad 0     /* off 24 base (uint64) */
    .quad 0     /* off 32 size (uint64) */
