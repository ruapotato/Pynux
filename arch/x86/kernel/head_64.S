/*
 * arch/x86/kernel/head_64.S - Hamnix 64-bit kernel entry.
 *
 * Mirrors Linux's arch/x86/kernel/head_64.S: it is the first 64-bit code
 * that runs as "the kernel proper" after the bootloader / decompressor
 * hands off. For Hamnix the handoff comes from arch/x86/boot/header.S's
 * long_mode_start, which jumps here once long mode is live, segments are
 * reloaded, and the boot stack is anchored.
 *
 * Responsibilities (minimal for M16.1):
 *   1. Zero the kernel BSS (the Hamnix compiler places globals there).
 *   2. Call the Hamnix-emitted start_kernel().
 *   3. If start_kernel ever returns, halt the CPU.
 */

    .section .text, "ax"
    .code64

    .globl  start_kernel_asm_entry
start_kernel_asm_entry:
    /* Zero kernel BSS: [__bss_start, __bss_end). Both symbols are defined
     * by arch/x86/kernel/vmlinux.lds. Using `rep stosq` so we move 8 bytes
     * at a time; the linker script aligns __bss_start/__bss_end to 8. */
    leaq    __bss_start(%rip), %rdi
    leaq    __bss_end(%rip),   %rcx
    subq    %rdi, %rcx
    shrq    $3, %rcx
    xorl    %eax, %eax
    cld
    rep stosq

    /* Hand off to the Hamnix kernel. SysV AMD64: no args, no return value. */
    call    start_kernel

    /* If start_kernel returns (it shouldn't yet), halt forever. */
halt_loop:
    cli
    hlt
    jmp     halt_loop

/* ---------- kernel_image_end() ----------------------------------- *
 * Returns the physical address one past the last byte the kernel
 * image occupies (= __bss_end). The kernel is identity-mapped, so
 * VMA == LMA == physical. mm/memblock callers bump their pool's base
 * past this so freshly-allocated pages can't overlap kernel
 * .text / .rodata / .data / .pgtables / .bss.
 *
 * Same trick as arch/x86/kernel/smp_asm.S's accessors: the linker
 * symbol is an absolute value, so we stash it as a 32-bit word in
 * .rodata and load via leaq + movl. That sidesteps the ELF32 R_X86_64
 * relocation gap our elf32-i386 OUTPUT_FORMAT can't represent.
 */
    .section .rodata
    .align 4
__bss_end_word:
    .long __bss_end

    .section .text, "ax"
    .align 16
    .globl kernel_image_end
kernel_image_end:
    leaq    __bss_end_word(%rip), %rax
    movl    (%rax), %eax
    ret
