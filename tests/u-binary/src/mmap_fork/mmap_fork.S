/*
 * tests/u-binary/src/mmap_fork/mmap_fork.S — copy-on-write fork over
 * an mmap VMA.
 *
 * Pure x86_64 asm, no libc. Built into a host-side Linux ELF with
 * OSABI=Linux so Hamnix's U2 detector flips is_linux_userspace=1.
 *
 * This fixture targets the mmap-VMA copy-on-write path specifically —
 * the part of fork() that vma_fork_copy COW-shares (the ELF image /
 * brk / stack are covered by the separate test_cow_fork fixture).
 *
 * Each of MF_ITERS iterations:
 *
 *   1. mmap(NULL, 2 pages, RW, ANON|PRIV, -1, 0) — a fresh anonymous
 *      VMA. Two pages so the COW share + per-page resolution runs over
 *      more than one page.
 *   2. Write a per-iteration PARENT sentinel into BOTH pages.
 *   3. fork(). Under COW the parent's mmap pages are now read-only +
 *      COW-marked in both PML4s, both pointing at the same physical
 *      pages.
 *   4. CHILD: overwrite both pages with a distinct CHILD sentinel —
 *      each write faults into the COW handler and copies that page
 *      privately. Read both pages back; the child must see ONLY its
 *      own value. exit_group(0) on success, exit_group(1) on a leak.
 *   5. PARENT: wait4() for the child, then read both mmap pages back —
 *      they must STILL hold the parent sentinel (the child's divergent
 *      writes must never have reached the parent's copy). Then
 *      munmap() the region: a COW-shared page must be returned to the
 *      buddy allocator through the refcount, so this exercises the
 *      cow_drop_page-routed free path. munmap must return 0.
 *
 * The iteration count makes a per-page refcount leak or a double-free
 * cumulative: a leak eventually OOMs mmap (caught: marker missing /
 * "mmap FAIL"); a double-free / use-after-free corrupts the kernel
 * (caught: a trap-diag line or a wrong sentinel readback).
 *
 * Markers (the test harness greps the serial log):
 *   "MF: start"
 *   "MF: iter ok"   once per iteration
 *   "MF: PASS"      all iterations clean
 *   "MF: FAIL ..."  a privacy violation / mmap failure / munmap failure
 */

    .set MF_ITERS,      8
    .set PAGE,          0x1000
    .set REGION_LEN,    0x2000        /* two pages */

    .set SYS_write,     1
    .set SYS_mmap,      9
    .set SYS_munmap,    11
    .set SYS_fork,      57
    .set SYS_wait4,     61
    .set SYS_exit_group, 231

    .section .text
    .globl _start
_start:
    /* ---- "MF: start" --------------------------------------------- */
    movq    $SYS_write, %rax
    movq    $1, %rdi
    leaq    msg_start(%rip), %rsi
    movq    $len_start, %rdx
    syscall

    /* %r15 = iteration counter (callee-saved across syscalls). */
    xorq    %r15, %r15

iter_loop:
    cmpq    $MF_ITERS, %r15
    jge     all_done

    /* ---- 1. mmap a 2-page anonymous private region --------------- */
    movq    $SYS_mmap, %rax
    xorq    %rdi, %rdi                 /* a0 = NULL                   */
    movq    $REGION_LEN, %rsi          /* a1 = length = 2 pages       */
    movq    $3, %rdx                   /* a2 = PROT_READ|PROT_WRITE   */
    movq    $0x22, %r10                /* a3 = MAP_PRIVATE|MAP_ANON   */
    movq    $-1, %r8                   /* a4 = fd = -1                */
    xorq    %r9, %r9                   /* a5 = offset = 0             */
    syscall
    cmpq    $0, %rax
    jle     fail_mmap
    movq    %rax, %r14                 /* %r14 = region base          */

    /* ---- 2. write the PARENT sentinel into both pages ------------ *
     * Parent sentinel = 0x11110000 + iter. Stored as a 64-bit value
     * at the start of each page so the readback can compare a full
     * quad (a partial-page COW bug would still surface). */
    movq    %r15, %rbx
    addq    $0x11110000, %rbx          /* %rbx = parent sentinel      */
    movq    %rbx, 0(%r14)              /* page 0                      */
    movq    %rbx, PAGE(%r14)           /* page 1                      */

    /* ---- 3. fork() ----------------------------------------------- */
    movq    $SYS_fork, %rax
    syscall
    cmpq    $0, %rax
    jl      fail_fork
    testq   %rax, %rax
    jz      child_path                 /* rax == 0 -> child           */

    /* ---- parent: wait4(child, &status, 0, 0) --------------------- */
    movq    %rax, %r13                 /* %r13 = child pid            */
    subq    $16, %rsp                  /* scratch for status         */
    movq    $SYS_wait4, %rax
    movq    %r13, %rdi                 /* a0 = pid                    */
    movq    %rsp, %rsi                 /* a1 = &status                */
    xorq    %rdx, %rdx                 /* a2 = options = 0            */
    xorq    %r10, %r10                 /* a3 = rusage = NULL          */
    syscall
    addq    $16, %rsp
    cmpq    $0, %rax
    jl      fail_wait

    /* The child overwrote ITS private copies with a child sentinel.
     * The parent's two pages must STILL hold the parent sentinel —
     * proof the child's COW writes never reached us. */
    movq    0(%r14), %rax
    cmpq    %rbx, %rax
    jne     fail_parent
    movq    PAGE(%r14), %rax
    cmpq    %rbx, %rax
    jne     fail_parent

    /* ---- 5. munmap the region -----------------------------------
     * The region was COW-shared on fork, so this free runs through
     * cow_drop_page (mm/vma.ad's COW-aware free path). munmap must
     * return 0; a non-zero return leaks the VMA. */
    movq    $SYS_munmap, %rax
    movq    %r14, %rdi                 /* a0 = base                   */
    movq    $REGION_LEN, %rsi          /* a1 = length                 */
    syscall
    testq   %rax, %rax
    jnz     fail_munmap

    /* ---- "MF: iter ok" ------------------------------------------- */
    movq    $SYS_write, %rax
    movq    $1, %rdi
    leaq    msg_iter_ok(%rip), %rsi
    movq    $len_iter_ok, %rdx
    syscall

    incq    %r15
    jmp     iter_loop

child_path:
    /* Child sentinel = 0x99990000 + iter. Overwrite both pages: each
     * store write-faults into the COW handler, which copies just that
     * page into the child's private address space. 0x99990000 has
     * bit 31 set, so it does not fit a sign-extended 32-bit add
     * immediate — build it via movq (which takes a full imm64). */
    movq    $0x99990000, %rcx
    addq    %r15, %rcx                 /* %rcx = child sentinel       */
    movq    %rcx, 0(%r14)
    movq    %rcx, PAGE(%r14)
    /* The child must observe ITS OWN value in both pages — never the
     * parent sentinel. */
    movq    0(%r14), %rax
    cmpq    %rcx, %rax
    jne     child_fail
    movq    PAGE(%r14), %rax
    cmpq    %rcx, %rax
    jne     child_fail
    /* Child is clean: exit_group(0). */
    movq    $SYS_exit_group, %rax
    xorq    %rdi, %rdi
    syscall
1:  jmp     1b

child_fail:
    /* Child saw the parent's value: report + exit_group(1). */
    movq    $SYS_write, %rax
    movq    $2, %rdi
    leaq    msg_fail_child(%rip), %rsi
    movq    $len_fail_child, %rdx
    syscall
    movq    $SYS_exit_group, %rax
    movq    $1, %rdi
    syscall
2:  jmp     2b

all_done:
    /* ---- "MF: PASS" ---------------------------------------------- */
    movq    $SYS_write, %rax
    movq    $1, %rdi
    leaq    msg_pass(%rip), %rsi
    movq    $len_pass, %rdx
    syscall
    movq    $SYS_exit_group, %rax
    xorq    %rdi, %rdi
    syscall
3:  jmp     3b

fail_mmap:
    leaq    msg_fail_mmap(%rip), %rsi
    movq    $len_fail_mmap, %rdx
    jmp     fail_emit
fail_fork:
    leaq    msg_fail_fork(%rip), %rsi
    movq    $len_fail_fork, %rdx
    jmp     fail_emit
fail_wait:
    leaq    msg_fail_wait(%rip), %rsi
    movq    $len_fail_wait, %rdx
    jmp     fail_emit
fail_parent:
    leaq    msg_fail_parent(%rip), %rsi
    movq    $len_fail_parent, %rdx
    jmp     fail_emit
fail_munmap:
    leaq    msg_fail_munmap(%rip), %rsi
    movq    $len_fail_munmap, %rdx
    jmp     fail_emit
fail_emit:
    movq    $SYS_write, %rax
    movq    $2, %rdi                   /* stderr                      */
    syscall
    movq    $SYS_exit_group, %rax
    movq    $1, %rdi
    syscall
4:  jmp     4b

    .section .rodata
    .align 8
msg_start:       .ascii "MF: start\n"
len_start = . - msg_start

msg_iter_ok:     .ascii "MF: iter ok\n"
len_iter_ok = . - msg_iter_ok

msg_pass:        .ascii "MF: PASS\n"
len_pass = . - msg_pass

msg_fail_mmap:   .ascii "MF: FAIL mmap\n"
len_fail_mmap = . - msg_fail_mmap

msg_fail_fork:   .ascii "MF: FAIL fork\n"
len_fail_fork = . - msg_fail_fork

msg_fail_wait:   .ascii "MF: FAIL wait\n"
len_fail_wait = . - msg_fail_wait

msg_fail_parent: .ascii "MF: FAIL parent copy corrupted by child\n"
len_fail_parent = . - msg_fail_parent

msg_fail_munmap: .ascii "MF: FAIL munmap\n"
len_fail_munmap = . - msg_fail_munmap

msg_fail_child:  .ascii "MF: FAIL child saw parent value\n"
len_fail_child = . - msg_fail_child
