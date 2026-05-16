/*
 * tests/u-binary/src/dynsym/dynsym.S — U11 dynsym + vDSO fixture.
 *
 * Pure x86_64 asm, no libc. Built as an ET_DYN (-shared) Linux ELF
 * whose .data carries a `.quad __vdso_clock_gettime` slot referring
 * to a weak undefined external. Linker output:
 *
 *   .dynsym  — 1 UND entry for __vdso_clock_gettime
 *   .dynstr  — contains the name
 *   .rela.dyn — one R_X86_64_64 entry targeting the .data slot, with
 *               sym_index = the __vdso_clock_gettime dynsym row and
 *               r_addend = 0.
 *
 * On a pre-U11 kernel, _apply_dyn_relocs would see the R_X86_64_64,
 * not have a dynsym walker, log "dyn-reloc sym-resolved type 1
 * skipped", and the slot would stay at the link-time value (0).
 * `testq %rsi, %rsi` would then take the failure branch and the
 * "U11: dynsym ok" marker would never be written.
 *
 * On a U11 kernel, _lookup_dynsym sees the name "__vdso_clock_gettime"
 * in .dynstr and returns the address of linux_abi/vdso.ad's
 * vdso_clock_gettime function. That non-zero address survives
 * `testq`, the marker line goes to serial, and the kernel logs
 * "elf64: applied N relocations" with N >= 1 — proof the symbol-
 * resolving reloc path fired.
 *
 * Success marker: "U11: dynsym ok\n"
 * Failure marker: "U11: dynsym FAIL\n" (on stderr).
 */

    /* Weak undefined: the linker keeps a .dynsym slot for this name
     * (so _lookup_dynsym can find it) but never resolves the
     * reference at link time. */
    .weak __vdso_clock_gettime

    /* `vdso_ptr` is .data with hidden visibility so the linker can
     * keep generating local references to it from .text. Without
     * .hidden, ld would treat any reference to a global .data symbol
     * inside a -shared object as a candidate for symbol interposition
     * and demand we go through the GOT (R_X86_64_PC32 against an
     * exported data symbol is illegal in a shared object). Hiding it
     * keeps the reference RIP-relative and confines the only dynamic
     * reloc to the __vdso_clock_gettime quad slot — exactly what we
     * want to exercise the U11 dynsym path. */
    .hidden vdso_ptr
    .hidden msg
    .hidden msg_fail

    .section .text
    .globl _start
_start:
    /* Load the relocated function pointer. After the U11 reloc pass
     * vdso_ptr holds the kernel-side address of vdso_clock_gettime.
     * Before U11 it holds 0 (the weak-undef fallback). */
    movq    vdso_ptr(%rip), %rsi
    testq   %rsi, %rsi
    jz      fail

    /* write(1, msg, msg_len) */
    movq    $1, %rax                 /* SYS_write                   */
    movq    $1, %rdi                 /* fd = stdout                 */
    leaq    msg(%rip), %rsi
    movq    $msg_len, %rdx
    syscall

    /* exit_group(0) */
    movq    $231, %rax               /* SYS_exit_group              */
    xorq    %rdi, %rdi
    syscall
1:  jmp     1b

fail:
    /* write(2, msg_fail, msg_fail_len) + exit_group(1) */
    movq    $1, %rax
    movq    $2, %rdi
    leaq    msg_fail(%rip), %rsi
    movq    $msg_fail_len, %rdx
    syscall
    movq    $231, %rax
    movq    $1, %rdi
    syscall
2:  jmp     2b

    .section .data
    .align 8
vdso_ptr:
    /* This 8-byte slot is the R_X86_64_64 target. Pre-reloc value: 0
     * (or whatever the linker wrote — for a weak undef, 0). Post-
     * reloc value: address of linux_abi/vdso.ad::vdso_clock_gettime. */
    .quad   __vdso_clock_gettime

    .section .rodata
msg:           .ascii "U11: dynsym ok\n"
msg_len      = . - msg

msg_fail:      .ascii "U11: dynsym FAIL\n"
msg_fail_len = . - msg_fail
