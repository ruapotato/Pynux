/*
 * tests/u-binary/src/glibc_idprobe/hello.c -- U21 fixture.
 *
 * U21 milestone: exercise the identity / time / sysinfo syscalls
 * that glibc reaches for as soon as a binary does anything beyond
 * "write a literal string and exit".
 *
 *   getuid / getgid     (102 / 104) -- root probe
 *   getppid             (110)       -- parent-pid probe
 *   gettimeofday        (96)        -- struct timeval, not timespec
 *   sysinfo             (99)        -- uptime + ram totals
 *
 * Each printf emits a unique "U21:" marker so test_u21_glibc_idprobe.sh
 * can grep for them independently. A regression that drops any of the
 * four handlers shows up as a missing marker in the captured log.
 *
 * Build: gcc -static-pie -O2 (same as the U19/U20 glibc fixtures).
 */
#include <stdio.h>
#include <sys/types.h>
#include <unistd.h>
#include <sys/time.h>
#include <sys/sysinfo.h>
int main(void) {
    printf("U21: uid=%d gid=%d ppid=%d\n",
           (int)getuid(), (int)getgid(), (int)getppid());
    struct timeval tv;
    gettimeofday(&tv, NULL);
    printf("U21: time tv_sec=%ld\n", (long)tv.tv_sec);
    struct sysinfo si;
    if (sysinfo(&si) == 0)
        printf("U21: uptime=%ld\n", (long)si.uptime);
    return 0;
}
