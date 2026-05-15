/*
 * arch/x86/kernel/boot_info_asm.S - accessors for the multiboot
 * info pointer stashed by the boot stub.
 *
 * header.S's 32-bit entry path saves the multiboot magic (EAX) and
 * info pointer (EBX) into two .long slots in .data:
 *      .globl mb_magic
 *      mb_magic: .long 0
 *      .globl mb_info
 *      mb_info:  .long 0
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
