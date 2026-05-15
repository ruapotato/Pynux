/*
 * user/hello.S - second user-mode ELF, exec'd by /init via SYS_EXECVE.
 *
 * Proves the exec path works end-to-end: /init starts up, prints its
 * banners, calls SYS_EXECVE("/hello"), kernel ELF-loads this binary,
 * sysretq's into _start below with a fresh user stack. The task_struct
 * and fd table survive the transition (stdout still routes to serial).
 */

    .code64
    .section .text, "ax"

    .globl _start
_start:
    /* write(1, banner, banner_len) */
    movq    $1, %rdi
    leaq    hello_banner(%rip), %rsi
    movq    $hello_banner_end - hello_banner, %rdx
    movq    $8, %rax                /* SYS_WRITE */
    syscall

    /* exit(0) */
    movq    $1, %rax                /* SYS_EXIT */
    syscall

.Lhello_hang:
    jmp     .Lhello_hang

    .balign 8
hello_banner:
    .ascii "[/hello] hello from a second ELF loaded by SYS_EXECVE!\n"
hello_banner_end:
