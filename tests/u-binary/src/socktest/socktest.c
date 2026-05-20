/*
 * tests/u-binary/src/socktest/socktest.c — U-socket fixture.
 *
 * The first user-space binary to complete a real TCP connection on
 * Hamnix. Exercises the userland socket(2) syscall family bridged to
 * the in-kernel TCP/IP stack (drivers/net/tcp.ad) by linux_abi/
 * u_syscalls.ad + fs/vfs.ad:
 *
 *     socket(AF_INET, SOCK_STREAM, 0)
 *     connect(fd, sockaddr_in{ host:port }, 16)
 *     write(fd, "GET / HTTP/1.0\r\n\r\n", ...)
 *     read(fd, buf, ...)            (looped until EOF)
 *     close(fd)
 *
 * Built with musl-gcc -static-pie; OSABI is stamped to ELFOSABI_LINUX
 * so Hamnix routes it through linux_u_syscall_dispatch. Every syscall
 * is a raw inline `syscall` instruction — the test must not depend on
 * whether musl's socket wrappers do anything clever.
 *
 * The server is a host-side Python http.server reached through SLIRP
 * at 10.0.2.2 (the SLIRP host alias). The connect target host/port are
 * compile-time macros so scripts/test_u_socket.sh can pick a free
 * port:
 *
 *     musl-gcc -static-pie -O2 -DSOCKTEST_PORT=NNNN -o socktest socktest.c
 *
 * Markers (one line each, on stdout — the harness greps for these):
 *   "socktest: socket fd=F"
 *   "socktest: connect rc=R"          (R == 0 on success)
 *   "socktest: write rc=R"
 *   "socktest: read total=N"
 *   "socktest: body=<first line of HTTP response>"
 *   "socktest: PASS" / "socktest: FAIL ..."
 */

#include <stdint.h>

#ifndef SOCKTEST_PORT
#define SOCKTEST_PORT 8080
#endif

/* SLIRP host alias — the QEMU user-net stack maps the host loopback
 * to 10.0.2.2 as seen from the guest. */
#define SOCKTEST_IP0 10
#define SOCKTEST_IP1 0
#define SOCKTEST_IP2 2
#define SOCKTEST_IP3 2

#define SYS_read        0
#define SYS_write       1
#define SYS_close       3
#define SYS_socket      41
#define SYS_connect     42
#define SYS_exit_group  231

#define AF_INET     2
#define SOCK_STREAM 1

static long sys3(long nr, long a, long b, long c) {
    long rc;
    __asm__ volatile (
        "syscall"
        : "=a"(rc)
        : "0"(nr), "D"(a), "S"(b), "d"(c)
        : "rcx", "r11", "memory"
    );
    return rc;
}

static long sys_write(int fd, const void *buf, unsigned long n) {
    return sys3(SYS_write, fd, (long)buf, (long)n);
}

static long sys_read(int fd, void *buf, unsigned long n) {
    return sys3(SYS_read, fd, (long)buf, (long)n);
}

static long sys_close(int fd) {
    return sys3(SYS_close, fd, 0, 0);
}

static long sys_socket(int domain, int type, int proto) {
    return sys3(SYS_socket, domain, type, proto);
}

static long sys_connect(int fd, const void *addr, unsigned long len) {
    return sys3(SYS_connect, fd, (long)addr, (long)len);
}

static void sys_exit(int code) {
    sys3(SYS_exit_group, code, 0, 0);
}

/* --- tiny string helpers (no libc) -------------------------------- */

static unsigned long u_strlen(const char *s) {
    unsigned long n = 0;
    while (s[n]) n++;
    return n;
}

static void puts_str(const char *s) {
    sys_write(1, s, u_strlen(s));
}

/* Append a signed decimal to dst at *pos; returns nothing. */
static void put_dec(char *dst, unsigned long *pos, long v) {
    char tmp[24];
    int ti = 0;
    int neg = 0;
    unsigned long uv;
    if (v < 0) { neg = 1; uv = (unsigned long)(-v); }
    else       { uv = (unsigned long)v; }
    if (uv == 0) tmp[ti++] = '0';
    while (uv) { tmp[ti++] = (char)('0' + (uv % 10)); uv /= 10; }
    if (neg) dst[(*pos)++] = '-';
    while (ti) dst[(*pos)++] = tmp[--ti];
}

static void puts_dec_line(const char *prefix, long v) {
    char line[96];
    unsigned long p = 0;
    const char *s = prefix;
    while (*s) line[p++] = *s++;
    put_dec(line, &p, v);
    line[p++] = '\n';
    sys_write(1, line, p);
}

int main(void) {
    /* struct sockaddr_in, 16 bytes:
     *   0: u16 sin_family (host order)
     *   2: u16 sin_port   (big-endian)
     *   4: u32 sin_addr   (big-endian IPv4)
     *   8: u8[8] sin_zero */
    volatile unsigned char sa[16];
    int i;
    for (i = 0; i < 16; i++) sa[i] = 0;
    sa[0] = AF_INET & 0xff;          /* sin_family low  */
    sa[1] = (AF_INET >> 8) & 0xff;   /* sin_family high */
    sa[2] = (SOCKTEST_PORT >> 8) & 0xff;  /* sin_port big-endian hi */
    sa[3] = SOCKTEST_PORT & 0xff;         /* sin_port big-endian lo */
    sa[4] = SOCKTEST_IP0;
    sa[5] = SOCKTEST_IP1;
    sa[6] = SOCKTEST_IP2;
    sa[7] = SOCKTEST_IP3;

    long fd = sys_socket(AF_INET, SOCK_STREAM, 0);
    puts_dec_line("socktest: socket fd=", fd);
    if (fd < 0) {
        puts_str("socktest: FAIL socket\n");
        sys_exit(1);
    }

    long crc = sys_connect((int)fd, (const void *)sa, 16);
    puts_dec_line("socktest: connect rc=", crc);
    if (crc != 0) {
        puts_str("socktest: FAIL connect\n");
        sys_close((int)fd);
        sys_exit(1);
    }

    /* HTTP/1.0 so the server closes the connection after the body —
     * gives us a clean EOF without depending on Content-Length
     * parsing. */
    const char *req =
        "GET / HTTP/1.0\r\n"
        "Host: hamnix-socktest\r\n"
        "Connection: close\r\n"
        "\r\n";
    unsigned long req_len = u_strlen(req);
    long wrc = sys_write((int)fd, req, req_len);
    puts_dec_line("socktest: write rc=", wrc);
    if (wrc != (long)req_len) {
        puts_str("socktest: FAIL write\n");
        sys_close((int)fd);
        sys_exit(1);
    }

    /* Drain the response. read() returns 0 at EOF (peer FIN). */
    char buf[2048];
    unsigned long total = 0;
    int first_line_done = 0;
    char body_line[256];
    unsigned long bl = 0;
    for (;;) {
        long n = sys_read((int)fd, buf, sizeof(buf));
        if (n < 0) {
            puts_str("socktest: FAIL read\n");
            sys_close((int)fd);
            sys_exit(1);
        }
        if (n == 0) break;
        /* Capture the first response line for the marker. */
        long k;
        for (k = 0; k < n && !first_line_done; k++) {
            char c = buf[k];
            if (c == '\r' || c == '\n') { first_line_done = 1; break; }
            if (bl < sizeof(body_line) - 1) body_line[bl++] = c;
        }
        total += (unsigned long)n;
        if (total > 1000000) break;   /* runaway guard */
    }
    body_line[bl] = 0;

    puts_dec_line("socktest: read total=", (long)total);
    {
        char line[320];
        unsigned long p = 0;
        const char *pfx = "socktest: body=";
        while (*pfx) line[p++] = *pfx++;
        unsigned long j;
        for (j = 0; j < bl; j++) line[p++] = body_line[j];
        line[p++] = '\n';
        sys_write(1, line, p);
    }

    sys_close((int)fd);

    if (total > 0 && body_line[0] == 'H' && body_line[1] == 'T'
            && body_line[2] == 'T' && body_line[3] == 'P') {
        puts_str("socktest: PASS\n");
        sys_exit(0);
    }
    puts_str("socktest: FAIL no HTTP response\n");
    sys_exit(1);
    return 0;
}
