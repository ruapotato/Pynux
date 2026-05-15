/*
 * arch/x86/lib/string_64.S - memset / memcpy / memmove for x86_64.
 *
 * Mirrors arch/x86/lib/memset_64.S, arch/x86/lib/memcpy_64.S, and
 * arch/x86/lib/memmove_64.S in Linux at their simplest form: the
 * straight `rep movsb`/`rep stosb` path. These are the canonical x86
 * string-op instructions; on modern CPUs with ERMS/FSRM they are at
 * memcpy speed of the fastest hand-written SIMD loops. We deliberately
 * don't ship the alignment-aware fast paths Linux uses for older CPUs
 * (those need cpufeature.h glue we haven't ported yet).
 *
 * All three follow SysV AMD64:
 *   memset(dst, val, n)   ->  dst (returned in %rax)
 *   memcpy(dst, src, n)   ->  dst
 *   memmove(dst, src, n)  ->  dst, handling overlap (backwards copy
 *                              if dst > src)
 *
 * For Hamnix extern decls, use any of:
 *   extern def memset(dst: Ptr[uint8], val: int32, n: uint64) -> Ptr[uint8]
 *   extern def memcpy(dst: Ptr[uint8], src: Ptr[uint8], n: uint64) -> Ptr[uint8]
 *   extern def memmove(dst: Ptr[uint8], src: Ptr[uint8], n: uint64) -> Ptr[uint8]
 */

    .code64
    .section .text, "ax"

/* ---------- memset ----------------------------------------------- *
 *   %rdi = dst, %rsi = val (low 8 bits used), %rdx = n
 *   returns %rax = dst                                              */
    .align 16
    .globl memset
memset:
    movq    %rdi, %r9                  /* save dst for return        */
    movl    %esi, %eax                 /* AL = val (low 8 bits)      */
    movq    %rdx, %rcx                 /* RCX = count                */
    rep stosb                          /* fill RCX bytes at ES:RDI   */
    movq    %r9, %rax
    ret

/* ---------- memcpy ----------------------------------------------- *
 *   %rdi = dst, %rsi = src, %rdx = n
 *   returns %rax = dst
 *   No overlap handling — callers with possibly-overlapping regions
 *   must use memmove.                                               */
    .align 16
    .globl memcpy
memcpy:
    movq    %rdi, %r9
    movq    %rdx, %rcx
    rep movsb
    movq    %r9, %rax
    ret

/* ---------- memmove ---------------------------------------------- *
 *   %rdi = dst, %rsi = src, %rdx = n
 *   returns %rax = dst
 *   Overlapping regions OK: if dst > src we walk backwards from the
 *   end so we never overwrite a byte we still need to read. Matches
 *   the contract of C99 memmove.                                    */
    .align 16
    .globl memmove
memmove:
    movq    %rdi, %r9                  /* save dst                   */
    cmpq    %rsi, %rdi
    jbe     .Lmm_forward               /* dst <= src → forward       */

    /* Backwards copy: point %rdi / %rsi at the LAST byte each, set
     * DF=1, then `rep movsb` walks downward. */
    leaq    -1(%rdi, %rdx), %rdi
    leaq    -1(%rsi, %rdx), %rsi
    movq    %rdx, %rcx
    std
    rep movsb
    cld                                /* leave DF cleared (SysV)    */
    movq    %r9, %rax
    ret

.Lmm_forward:
    movq    %rdx, %rcx
    cld
    rep movsb
    movq    %r9, %rax
    ret
