/*
 * tests/u-binary/src/cow_fork/cow_fork.c — #143 fork() COW isolation e2e.
 *
 * Copy-on-write fork() is fully implemented in the kernel (mm/cow.ad +
 * the #PF arm in arch/x86/kernel/trap_diag.ad calling
 * cow_handle_write_fault, plus fork's vm_cow_share_all / per-region copy
 * in fs/elf.ad) but had ZERO automated coverage, so it could silently
 * regress. This fixture proves the load-bearing CORRECTNESS guarantee:
 * fork() gives the child a PRIVATE, ISOLATED address space — the child's
 * writes after fork() do NOT leak into the parent, and the parent's
 * post-fork writes do NOT leak into a second child.
 *
 * It exercises three independent writable region kinds so a COW bug in
 * any one of them shows up:
 *   - a writable GLOBAL array (.data),
 *   - a heap allocation (brk/mmap via malloc),
 *   - an anonymous mmap() region (PROT_READ|PROT_WRITE).
 *
 * Flow:
 *   1. Fill all three buffers with a known PARENT sentinel.
 *   2. fork() child A. In child A: overwrite every buffer with a CHILD
 *      sentinel, read it back to confirm the child sees ITS OWN writes
 *      (these writes fault the COW pages and get private copies), then
 *      _exit(7).
 *   3. Parent waitpid()s child A, confirms it exited 7, then verifies
 *      ALL THREE of the parent's buffers are STILL the parent sentinel —
 *      i.e. the child's writes never leaked back (private addr space).
 *   4. Reverse direction: the parent now overwrites its buffers with a
 *      PARENT2 sentinel and fork()s child B. Child B reads the buffers:
 *      it must see PARENT2 (the values at the time of the second fork),
 *      NOT the CHILD sentinel from the first child — proving each fork
 *      snapshots the live parent state into a private child space and the
 *      first child's space was fully independent. Child B _exit(9)s; the
 *      parent confirms its own buffers are untouched by child B too.
 *
 * Uses raw write(2) for output so stdio buffering can't lose a marker
 * across the fork frame, exactly like sig_rt.c.
 *
 * Markers on serial (the harness greps these):
 *   "COW: child saw its write"
 *   "COW: parent copy intact"
 *   "COW: second child saw parent snapshot"
 *   "COW: parent intact after second child"
 *   "cow_fork: PASS" / "cow_fork: FAIL ..."
 */

#define _GNU_SOURCE
#include <unistd.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/wait.h>

#define N 1024

/* Writable global (.data) — a COW-tracked region after fork. */
static unsigned char g_global[N];

static inline long do_write(int fd, const char *buf, unsigned long len) {
    long rc;
    __asm__ volatile (
        "syscall" : "=a"(rc)
        : "0"(1), "D"(fd), "S"(buf), "d"(len)
        : "rcx", "r11", "memory");
    return rc;
}
#define SAY(s) do_write(1, s "\n", sizeof(s) - 1)

static void fill(unsigned char *b, unsigned char v) {
    for (int i = 0; i < N; i++) b[i] = (unsigned char)(v ^ (i & 0xff));
}

/* Returns 1 iff every byte matches the fill() pattern for sentinel v. */
static int check(const unsigned char *b, unsigned char v) {
    for (int i = 0; i < N; i++)
        if (b[i] != (unsigned char)(v ^ (i & 0xff)))
            return 0;
    return 1;
}

#define PARENT_V  0xA5
#define CHILD_V   0x5A
#define PARENT2_V 0x3C

int main(void) {
    unsigned char *g_heap = malloc(N);
    if (!g_heap) { SAY("cow_fork: FAIL malloc"); return 1; }

    unsigned char *g_mmap = mmap(0, N, PROT_READ | PROT_WRITE,
                                 MAP_PRIVATE | MAP_ANONYMOUS, -1, 0);
    if (g_mmap == MAP_FAILED) { SAY("cow_fork: FAIL mmap"); return 1; }

    /* --- 1. seed all three regions with the parent sentinel --------- */
    fill(g_global, PARENT_V);
    fill(g_heap,   PARENT_V);
    fill(g_mmap,   PARENT_V);

    /* --- 2. fork child A; child overwrites every buffer ------------- */
    pid_t a = fork();
    if (a < 0) { SAY("cow_fork: FAIL fork A"); return 1; }
    if (a == 0) {
        /* CHILD A: writing faults each COW page and gets a private copy. */
        fill(g_global, CHILD_V);
        fill(g_heap,   CHILD_V);
        fill(g_mmap,   CHILD_V);
        /* Read back: the child must see ITS OWN writes. */
        if (!check(g_global, CHILD_V) ||
            !check(g_heap,   CHILD_V) ||
            !check(g_mmap,   CHILD_V)) {
            SAY("cow_fork: FAIL child A did not see its own writes");
            _exit(1);
        }
        SAY("COW: child saw its write");
        _exit(7);
    }

    /* --- 3. parent reaps child A, verifies its copies are intact ---- */
    int st = 0;
    pid_t r = waitpid(a, &st, 0);
    if (r != a || !WIFEXITED(st) || WEXITSTATUS(st) != 7) {
        SAY("cow_fork: FAIL child A bad exit");
        return 1;
    }
    if (!check(g_global, PARENT_V)) {
        SAY("cow_fork: FAIL parent GLOBAL clobbered by child A");
        return 1;
    }
    if (!check(g_heap, PARENT_V)) {
        SAY("cow_fork: FAIL parent HEAP clobbered by child A");
        return 1;
    }
    if (!check(g_mmap, PARENT_V)) {
        SAY("cow_fork: FAIL parent MMAP clobbered by child A");
        return 1;
    }
    SAY("COW: parent copy intact");

    /* --- 4. reverse: parent rewrites, forks child B (snapshot test) - */
    fill(g_global, PARENT2_V);
    fill(g_heap,   PARENT2_V);
    fill(g_mmap,   PARENT2_V);

    pid_t b = fork();
    if (b < 0) { SAY("cow_fork: FAIL fork B"); return 1; }
    if (b == 0) {
        /* CHILD B reads only: must see PARENT2 (the live state at fork),
         * never the first child's CHILD_V, and never a stale PARENT_V. */
        if (!check(g_global, PARENT2_V) ||
            !check(g_heap,   PARENT2_V) ||
            !check(g_mmap,   PARENT2_V)) {
            SAY("cow_fork: FAIL child B wrong snapshot");
            _exit(1);
        }
        SAY("COW: second child saw parent snapshot");
        _exit(9);
    }

    st = 0;
    r = waitpid(b, &st, 0);
    if (r != b || !WIFEXITED(st) || WEXITSTATUS(st) != 9) {
        SAY("cow_fork: FAIL child B bad exit");
        return 1;
    }
    /* child B only read, but re-verify the parent is still PARENT2. */
    if (!check(g_global, PARENT2_V) ||
        !check(g_heap,   PARENT2_V) ||
        !check(g_mmap,   PARENT2_V)) {
        SAY("cow_fork: FAIL parent clobbered by child B");
        return 1;
    }
    SAY("COW: parent intact after second child");

    SAY("cow_fork: PASS");
    return 0;
}
