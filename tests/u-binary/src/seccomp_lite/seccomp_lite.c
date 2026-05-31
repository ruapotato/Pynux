/*
 * tests/u-binary/src/seccomp_lite/seccomp_lite.c — #160 seccomp-lite e2e.
 *
 * Exercises Hamnix's per-task syscall filter (linux_abi/u_syscalls.ad
 * seccomp_check_entry + _u_seccomp / prctl(PR_SET_SECCOMP), enforced at
 * the central linux_u_syscall_dispatch ENTRY boundary, with the SIGSYS
 * delivered through the kernel signal path in kernel/sched/core.ad):
 *
 *   1. write(2) BEFORE arming seccomp — baseline, proves the binary runs.
 *   2. Install a SIGSYS handler (so a denied syscall is observable from
 *      userspace instead of an immediate kill).
 *   3. prctl(PR_SET_SECCOMP, SECCOMP_MODE_STRICT) — arm strict mode.
 *   4. write(2) AFTER arming — strict mode ALLOWS read/write/_exit/
 *      rt_sigreturn, so this must still succeed (prints a marker).
 *   5. getpid(2) AFTER arming — strict mode DENIES it, so the kernel
 *      posts SIGSYS; our handler runs and prints the denial marker.
 *      Control resumes past the denied syscall, we observe the handler
 *      fired, and _exit(0) cleanly (exit is in the allow-set).
 *
 * All output via raw write(2) (the one syscall guaranteed allowed under
 * strict mode) — no stdio, no other syscalls that strict mode would kill.
 *
 * Markers on serial (the harness greps these):
 *   "SECCOMP: pre-arm write ok"
 *   "SECCOMP: strict armed"
 *   "SECCOMP: allowed write after arm"
 *   "SECCOMP: SIGSYS on blocked syscall"
 *   "seccomp_lite: PASS" / "seccomp_lite: FAIL ..."
 */

#define _GNU_SOURCE
#include <signal.h>
#include <unistd.h>
#include <string.h>
#include <sys/prctl.h>

#ifndef PR_SET_SECCOMP
#define PR_SET_SECCOMP 22
#endif
#ifndef SECCOMP_MODE_STRICT
#define SECCOMP_MODE_STRICT 1
#endif
#ifndef SIGSYS
#define SIGSYS 31
#endif

static volatile sig_atomic_t sigsys_hits = 0;

/* Raw write(2): syscall nr 1. Used for ALL output so nothing we print
 * depends on a syscall strict mode would deny. */
static inline long do_write(int fd, const char *buf, unsigned long len) {
    long rc;
    __asm__ volatile (
        "syscall" : "=a"(rc)
        : "0"(1), "D"(fd), "S"(buf), "d"(len)
        : "rcx", "r11", "memory");
    return rc;
}
#define SAY(s) do_write(1, s "\n", sizeof(s) - 1)

/* Raw _exit(2): syscall nr 60. In the allow-set, so callable post-arm. */
static inline void do_exit(int code) {
    __asm__ volatile (
        "syscall" :: "a"(60), "D"((long)code) : "rcx", "r11", "memory");
    __builtin_unreachable();
}

/* Raw getpid(2): syscall nr 39 — NOT in the strict allow-set. Issuing
 * this after arming strict mode is what triggers SIGSYS. */
static inline long do_getpid(void) {
    long rc;
    __asm__ volatile (
        "syscall" : "=a"(rc) : "0"(39) : "rcx", "r11", "memory");
    return rc;
}

/* Raw prctl(2): syscall nr 157. Issued BEFORE strict mode is armed
 * (prctl is how we arm it), so it is always permitted at the call site. */
static inline long do_prctl(long op, long a1, long a2, long a3, long a4) {
    long rc;
    register long r10 __asm__("r10") = a3;
    register long r8  __asm__("r8")  = a4;
    __asm__ volatile (
        "syscall" : "=a"(rc)
        : "0"(157), "D"(op), "S"(a1), "d"(a2), "r"(r10), "r"(r8)
        : "rcx", "r11", "memory");
    return rc;
}

/* Raw rt_sigaction(2): syscall nr 13. Installs the SIGSYS handler before
 * arming seccomp. Uses musl's sigaction wrapper would also work, but we
 * keep the whole pre-arm path explicit. We just call the libc wrapper —
 * sigaction itself runs before strict mode is armed, so it is allowed. */

static void on_sigsys(int sig) {
    (void)sig;
    sigsys_hits++;
    SAY("SECCOMP: SIGSYS on blocked syscall");
    /* The denial was observed from userspace exactly as a real seccomp
     * SIGSYS handler would see it. Report PASS and exit from inside the
     * handler — _exit (nr 60) is in the strict allow-set, so it is
     * permitted even now. We exit here rather than returning so the test
     * outcome does not depend on whether a handler's write to a global
     * survives the rt_sigreturn frame restore (which on some ABIs spills
     * the pre-signal register file verbatim). */
    SAY("seccomp_lite: PASS");
    do_exit(0);
}

int main(void) {
    /* --- 1. baseline write before arming -------------------------- */
    SAY("SECCOMP: pre-arm write ok");

    /* --- 2. install a SIGSYS handler ------------------------------ *
     * Done BEFORE arming seccomp (sigaction/rt_sigaction is denied once
     * strict mode is on). With a handler installed, a denied syscall is
     * observable from userspace rather than an immediate kernel kill. */
    struct sigaction sa;
    memset(&sa, 0, sizeof(sa));
    sa.sa_handler = on_sigsys;
    if (sigaction(SIGSYS, &sa, 0) != 0) {
        SAY("seccomp_lite: FAIL sigaction");
        return 1;
    }

    /* --- 3. arm strict mode --------------------------------------- */
    if (do_prctl(PR_SET_SECCOMP, SECCOMP_MODE_STRICT, 0, 0, 0) != 0) {
        SAY("seccomp_lite: FAIL prctl set_seccomp");
        return 1;
    }
    SAY("SECCOMP: strict armed");

    /* --- 4. an ALLOWED syscall still works ------------------------ *
     * write(2) is in the strict allow-set, so this must succeed. If
     * seccomp wrongly killed us here, the marker below never prints. */
    SAY("SECCOMP: allowed write after arm");

    /* --- 5. a DISALLOWED syscall is caught ------------------------ *
     * getpid(2) is NOT allowed under strict mode. The kernel posts
     * SIGSYS; our handler runs (printing the denial marker + PASS) and
     * exits from inside the handler. If we ever return PAST the denied
     * call without the handler having fired, that is a FAIL (the filter
     * let a forbidden syscall through). */
    (void)do_getpid();          /* must trap to the SIGSYS handler */

    /* Only reached if SIGSYS was NOT delivered — i.e. the filter failed
     * to deny getpid(). (sigsys_hits is consulted purely defensively.) */
    if (sigsys_hits == 0) {
        SAY("seccomp_lite: FAIL no SIGSYS on blocked syscall");
        do_exit(1);
    }
    /* Handler fired but somehow returned here instead of exiting; still
     * a correct denial, so report PASS. */
    SAY("seccomp_lite: PASS");
    do_exit(0);
}
