/*
 * tests/u-binary/src/wx_text_ro/wx_text_ro.c — W^X Stage 1b: CODE
 * pages are read-only.
 *
 * Stage 1a (u_wxorx) proved user DATA pages are No-Execute (a jmp/call
 * into the stack/heap faults). Stage 1b proves the COMPLEMENT: user
 * CODE pages (.text / .rodata of the loaded image) are READ-ONLY +
 * executable, so a WRITE into .text raises a #PF protection fault that
 * the kernel (arch/x86/kernel/trap_diag.ad::do_page_fault) converts
 * into SIGSEGV(11). This closes the self-modifying-code / code-injection
 * W^X hole: code that runs can never be patched at runtime.
 *
 * Sequence:
 *   1. write(2) baseline — proves the binary runs (a normal program
 *      runs to this point with no false faults from the RO flip).
 *   2. Install a SIGSEGV handler so the protection trap is observable.
 *   3. Read the first byte of target_fn()'s machine code (a READ from
 *      .text must SUCCEED — the page is readable+executable).
 *   4. Write a byte BACK to that same .text address. .text is RO, so
 *      the store faults -> #PF(protection) -> kernel SIGSEGV -> handler
 *      runs, prints the trap marker + PASS, and _exit(0).
 *
 * If .text were writable the store would simply succeed and we'd fall
 * through to the FAIL marker.
 *
 * All output via raw write(2) — no stdio.
 *
 * Markers on serial (the harness greps these):
 *   "WXTEXT: pre-write ok"
 *   "WXTEXT: handler armed"
 *   "WXTEXT: text read ok"
 *   "WXTEXT: RO trapped write-to-text"
 *   "wx_text_ro: PASS" / "wx_text_ro: FAIL ..."
 */

#define _GNU_SOURCE
#include <signal.h>
#include <unistd.h>
#include <string.h>

#ifndef SIGSEGV
#define SIGSEGV 11
#endif

/* Raw write(2): syscall nr 1. */
static inline long do_write(int fd, const char *buf, unsigned long len) {
    long rc;
    __asm__ volatile (
        "syscall" : "=a"(rc)
        : "0"(1), "D"(fd), "S"(buf), "d"(len)
        : "rcx", "r11", "memory");
    return rc;
}
#define SAY(s) do_write(1, s "\n", sizeof(s) - 1)

/* Raw _exit(2): syscall nr 60. */
static inline void do_exit(int code) {
    __asm__ volatile (
        "syscall" :: "a"(60), "D"((long)code) : "rcx", "r11", "memory");
    __builtin_unreachable();
}

static volatile sig_atomic_t segv_hits = 0;

static void on_sigsegv(int sig) {
    (void)sig;
    segv_hits++;
    SAY("WXTEXT: RO trapped write-to-text");
    /* The W^X protection violation was observed from userspace exactly
     * as a real handler would see it. Report PASS and exit from inside
     * the handler — the outcome does not depend on resuming the
     * (faulting) store. */
    SAY("wx_text_ro: PASS");
    do_exit(0);
}

/* A small leaf function whose first machine-code byte we target. The
 * `volatile` asm and the noinline attribute keep the optimizer from
 * eliding it; its address lands in .text (read-only after Stage 1b). */
__attribute__((noinline)) static int target_fn(int x) {
    __asm__ volatile ("" ::: "memory");
    return x + 1;
}

int main(void) {
    SAY("WXTEXT: pre-write ok");

    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_sigsegv;
    if (sigaction(SIGSEGV, &sa, 0) != 0) {
        SAY("wx_text_ro: FAIL sigaction");
        return 1;
    }
    SAY("WXTEXT: handler armed");

    /* Launder the function pointer to a byte pointer aimed at the first
     * byte of target_fn's machine code, sitting in .text. */
    volatile unsigned char *code = (volatile unsigned char *)(void *)
        (unsigned long)&target_fn;

    /* READ from .text must succeed — the page is R+X. Use the value so
     * the read isn't optimized away. */
    unsigned char orig = code[0];
    if (orig == 0) {
        /* Extremely unlikely (a function never starts with a 0x00
         * opcode byte in practice), but don't FAIL on it — just note. */
        SAY("WXTEXT: text read ok");
    } else {
        SAY("WXTEXT: text read ok");
    }

    /* WRITE the same byte back to .text. The store value equals the
     * byte already there, so even if (wrongly) writable, memory is
     * unchanged — but with Stage 1b the store FAULTS before it lands. */
    code[0] = orig;

    /* Only reached if .text was NOT read-only (the store succeeded).
     * That means code pages are still writable -> FAIL. */
    if (segv_hits == 0) {
        SAY("wx_text_ro: FAIL no SIGSEGV on write-to-text (text not RO)");
        do_exit(1);
    }
    SAY("wx_text_ro: PASS");
    do_exit(0);
}
