/*
 * arch/x86/kernel/boot_info_asm.S - accessors for the multiboot
 * info pointer stashed by the boot stub, plus EFI GOP framebuffer
 * info stashed by the UEFI stub.
 *
 * header.S's 32-bit entry path saves the multiboot magic (EAX) and
 * info pointer (EBX) into two .long slots in the LOW boot region
 * (.boot.data):
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
 * Hamnix currently has no "extern variable" syntax, so we read those
 * symbols out via tiny accessor functions instead.
 *
 * HIGHER-HALF NOTE: mb_magic / mb_info / boot_via_efi / efi_fb_info
 * all live in the LOW boot region (.boot.data, VMA ~0x10xxxx) so the
 * 32-bit boot stub and the EFI handoff table can reference them with
 * 32-bit addresses. THIS file's code is linked in the higher half
 * (0xffffffff80...). A RIP-relative `leaq sym(%rip)` from high code to
 * a low boot symbol would overflow the ±2 GiB PC-relative
 * displacement, so every accessor below materialises the absolute
 * address with `movabsq $sym` (an R_X86_64_64 relocation — valid now
 * that the kernel links as a true elf64-x86-64 object). The multiboot
 * info struct and the EFI framebuffer base may be anywhere in 64-bit
 * RAM, hence the 64-bit-clean loads.
 */

    .code64
    .section .text, "ax"

    .align 16
    .globl get_mb_magic
get_mb_magic:
    movabsq $mb_magic, %rax
    movl    (%rax), %eax              /* movl zero-extends to %rax  */
    ret

    .align 16
    .globl get_mb_info
get_mb_info:
    movabsq $mb_info, %rax
    movl    (%rax), %eax
    ret

    /* ---- boot_via_efi accessors ---------------------------------------
     *
     * boot_via_efi is a LOW-boot-region int32 flag (.boot.data),
     * default 0. The EFI stub patches it to 1 via the +56 handoff
     * slot before jumping to the kernel; arch/x86/kernel/e820.ad reads
     * it through get_boot_via_efi() and can also set it via
     * set_boot_via_efi_asm() (kept for the documented future API). */
    .align 16
    .globl get_boot_via_efi
get_boot_via_efi:
    movabsq $boot_via_efi, %rax
    movl    (%rax), %eax
    ret

    .align 16
    .globl set_boot_via_efi_asm
set_boot_via_efi_asm:
    movabsq $boot_via_efi, %rax
    movl    $1, (%rax)
    ret

    /* ---- EFI GOP framebuffer accessors --------------------------------
     *
     * efi_fb_info layout (.boot.data, populated by arch/x86/boot/
     * efi_stub.S right before ExitBootServices; zero on multiboot1):
     *
     *   off  0: uint32 present       (1 = populated, 0 = no GOP)
     *   off  4: uint32 width         (HorizontalResolution)
     *   off  8: uint32 height        (VerticalResolution)
     *   off 12: uint32 pitch_bytes   (PixelsPerScanLine × bytes_per_px)
     *   off 16: uint32 pixel_format  (0 RGB, 1 BGR, 2 BitMask, 3 Blt)
     *   off 20: uint32 bpp           (always 32 today)
     *   off 24: uint64 base          (FrameBufferBase — may be > 4 GiB)
     *   off 32: uint64 size          (FrameBufferSize)
     *
     * Total: 40 bytes. The efi_stub.S writes the whole struct in one
     * pass via offset stores from a base register pointing here.
     */
    .align 16
    .globl get_efi_fb_present
get_efi_fb_present:
    movabsq $efi_fb_info, %rax
    movl    0(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_width
get_efi_fb_width:
    movabsq $efi_fb_info, %rax
    movl    4(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_height
get_efi_fb_height:
    movabsq $efi_fb_info, %rax
    movl    8(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_pitch_bytes
get_efi_fb_pitch_bytes:
    movabsq $efi_fb_info, %rax
    movl    12(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_pixel_format
get_efi_fb_pixel_format:
    movabsq $efi_fb_info, %rax
    movl    16(%rax), %eax
    ret

    .align 16
    .globl get_efi_fb_bpp
get_efi_fb_bpp:
    movabsq $efi_fb_info, %rax
    movl    20(%rax), %eax
    ret

    /* base + size are 64-bit. Caller gets the full 64-bit value. */
    .align 16
    .globl get_efi_fb_base
get_efi_fb_base:
    movabsq $efi_fb_info, %rcx
    movq    24(%rcx), %rax
    ret

    .align 16
    .globl get_efi_fb_size
get_efi_fb_size:
    movabsq $efi_fb_info, %rcx
    movq    32(%rcx), %rax
    ret

    /* ---- EFI GOP framebuffer storage ----------------------------------
     *
     * Lives in .boot.data (the LOW boot region) so the EFI handoff
     * table's 32-bit +64 slot can carry its address and the EFI stub
     * can write it by that low physical address before jumping to the
     * kernel. .boot.data is loaded zero-initialised; BIOS multiboot1
     * boot never touches this region (`present` stays 0 and the Adder
     * accessor short-circuits).
     */
    .section .boot.data, "aw"
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
