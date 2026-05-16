/*
 * tests/u-binary/src/glibc_demo/hello.c -- U22 fixture.
 *
 * U22 milestone: stress the U-track ABI with a more demanding glibc
 * static-PIE binary. Previous U-track binaries proved very narrow
 * slices of the Linux ABI (U12 hello, U15 printf, U16 argv, U17 envp,
 * U19 hello-via-glibc, U20 IFUNC memcpy). U22 widens the surface in
 * one go:
 *
 *   1) Heap path: strdup + free exercises glibc's malloc arena
 *      (brk for the first chunk, mmap for chunks > 128 KiB), plus
 *      the free path that returns the block to the arena.
 *
 *   2) FILE* path: fopen("/etc/motd","r") + fread + fclose exercises
 *      the whole openat -> fstat -> read -> close chain through
 *      glibc's FILE* abstraction (line-buffering setup runs even
 *      if we never actually call gets/putc).
 *
 *   3) Format variety: multiple printf() calls with %d, %u, %x,
 *      %ld, %lu, %zu, %.5s (precision-truncated string), %6d
 *      (right-justified width), %#04x (alt-form hex with padding).
 *      All formatting is in-process — no syscalls beyond writev to
 *      flush stdout — but the variety hits enough of glibc's
 *      vfprintf machinery to catch format-spec lowering regressions.
 *
 *   4) Time path: time(NULL) calls __clock_gettime(CLOCK_REALTIME)
 *      (modern glibc routes time() through clock_gettime). Just
 *      formats the integer seconds — no strftime, so no locale
 *      machinery in this revision.
 *
 * Marker on serial:  "U22: heap ok"               -- strdup PASS
 *                    "U22: motd read N bytes"     -- fopen/fread PASS
 *                    "U22: ints="                 -- format-variety PASS
 *                    "U22: time_t="               -- time PASS
 *
 * Build: gcc -static-pie -O2 (same shape as U19/U20). Stamp
 * EI_OSABI=Linux so the U1 detect path is unambiguous.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

int main(void) {
    /* 1) Heap: strdup + free */
    char *s = strdup("U22: heap ok");
    if (s) { puts(s); free(s); } else { puts("U22: heap FAIL"); return 1; }

    /* 2) File I/O via FILE* */
    FILE *f = fopen("/etc/motd", "r");
    if (f) {
        char buf[64] = {0};
        size_t n = fread(buf, 1, 63, f);
        printf("U22: motd read %zu bytes\n", n);
        fclose(f);
    } else {
        puts("U22: motd open FAIL"); /* not fatal */
    }

    /* 3) Format variety */
    printf("U22: ints=%d %u %x  longs=%ld %lu\n", -1, 1u, 0xdeadu, (long)42, (unsigned long)42);
    printf("U22: str=%.5s pad=%6d hex=%#04x\n", "abcdef", 7, 0xab);

    /* 4) Time formatting (light) -- calls __clock_gettime under modern glibc */
    time_t t = time(NULL);
    printf("U22: time_t=%ld\n", (long)t);

    return 0;
}
