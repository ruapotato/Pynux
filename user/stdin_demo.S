/*
 * user/stdin_demo.S - user-mode "read a line, echo it" demo.
 *
 * Originally user/echo.S; renamed in M16.37 when user/echo.ad
 * (the real coreutils-shaped echo) shipped. Kept around as the
 * focused stdin-readback fixture that scripts/test_stdin.sh drives.
 *
 * Reads up to 32 bytes from stdin (fd 0 — routes to UART RX via
 * the kernel's vfs_read FD_STDIN branch), then writes them back to
 * stdout (fd 1). One round-trip per run, then exits.
 *
 * Run interactively:
 *   INIT_ELF=build/user/stdin_demo.elf bash scripts/run_x86_bare.sh
 * Or piped:
 *   echo "hello" | INIT_ELF=build/user/stdin_demo.elf bash scripts/run_x86_bare.sh
 */

    .code64
    .section .text, "ax"

    .globl _start
_start:
    /* write(1, prompt, len) */
    movq    $1, %rdi
    leaq    echo_prompt(%rip), %rsi
    movq    $echo_prompt_end - echo_prompt, %rdx
    movq    $8, %rax                /* SYS_WRITE */
    syscall

    /* n = read(0, buf, 32) — blocks until a line (or 32 bytes). */
    movq    $0, %rdi                /* fd 0 = stdin */
    leaq    echo_buf(%rip), %rsi
    movq    $32, %rdx
    movq    $6, %rax                /* SYS_READ */
    syscall
    movq    %rax, %r12              /* save bytes-read count */

    /* echo banner */
    movq    $1, %rdi
    leaq    echo_label(%rip), %rsi
    movq    $echo_label_end - echo_label, %rdx
    movq    $8, %rax
    syscall

    /* write(1, buf, n) */
    movq    $1, %rdi
    leaq    echo_buf(%rip), %rsi
    movq    %r12, %rdx
    movq    $8, %rax
    syscall

    /* exit(0) */
    movq    $1, %rax
    syscall

.Lecho_hang:
    jmp     .Lecho_hang

    .balign 8
echo_prompt:
    .ascii "[/echo] type a line (max 32 chars): "
echo_prompt_end:
echo_label:
    .ascii "[/echo] you said: "
echo_label_end:

    .balign 8
echo_buf:
    .skip 32
