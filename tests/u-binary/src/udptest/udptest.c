/*
 * tests/u-binary/src/udptest/udptest.c — §10 UDP-socket fixture.
 *
 * The first user-space binary to do real datagram I/O on Hamnix.
 * Exercises the userland SOCK_DGRAM socket family bridged to the
 * in-kernel UDP socket layer (drivers/net/udp.ad) by linux_abi/
 * u_syscalls.ad + fs/vfs.ad:
 *
 *     socket(AF_INET, SOCK_DGRAM, 0)
 *     bind(fd, sockaddr_in{ 0.0.0.0:LOCAL })   (so the reply has a home)
 *     sendto(fd, dns_query, sockaddr_in{ 10.0.2.2:53 })
 *     recvfrom(fd, buf, &src)                   (the DNS response)
 *     close(fd)
 *
 * The peer is QEMU SLIRP's built-in DNS resolver at 10.0.2.2:53 — a
 * real UDP server that always answers, with NO host-side helper and
 * NO guestfwd needed (QEMU's guestfwd is TCP-only, so a UDP echo
 * server is not reachable through SLIRP; the built-in resolver is).
 * The fixture sends a minimal DNS A-record query for "example.com"
 * and asserts a well-formed DNS response comes back: the recvfrom
 * datagram must echo our 16-bit query id and have the QR (response)
 * bit set. That round-trip proves socket / bind / sendto / recvfrom /
 * close on a datagram socket end to end.
 *
 * Built with musl-gcc -static-pie; OSABI is stamped to ELFOSABI_LINUX.
 * Every syscall is a raw inline `syscall` instruction.
 *
 * Markers (one line each, on stdout — the harness greps for these):
 *   "udptest: socket fd=F"
 *   "udptest: bind rc=R"
 *   "udptest: sendto rc=R"
 *   "udptest: recvfrom rc=R"
 *   "udptest: dns id ok"  / "udptest: dns qr ok"
 *   "udptest: PASS" / "udptest: FAIL ..."
 */

#include <stdint.h>

/* QEMU SLIRP's built-in DNS forwarder. SLIRP places the virtual DNS
 * at 10.0.2.3 (10.0.2.2 is the gateway/host alias, which has no DNS
 * — a UDP datagram there draws an ICMP port-unreachable instead). */
#define UDPTEST_IP0 10
#define UDPTEST_IP1 0
#define UDPTEST_IP2 2
#define UDPTEST_IP3 3
#define UDPTEST_DNS_PORT 53

/* The local port the guest binds — the DNS reply lands here. */
#ifndef UDPTEST_LOCAL_PORT
#define UDPTEST_LOCAL_PORT 12345
#endif

/* 16-bit query id we stamp into the DNS header and expect echoed. */
#define UDPTEST_QID 0x4D31

#define SYS_write       1
#define SYS_close       3
#define SYS_socket      41
#define SYS_bind        49
#define SYS_sendto      44
#define SYS_recvfrom    45
#define SYS_exit_group  231

#define AF_INET     2
#define SOCK_DGRAM  2

static long sys6(long nr, long a, long b, long c,
                 long d, long e, long f) {
    long rc;
    register long r10 __asm__("r10") = d;
    register long r8  __asm__("r8")  = e;
    register long r9  __asm__("r9")  = f;
    __asm__ volatile (
        "syscall"
        : "=a"(rc)
        : "0"(nr), "D"(a), "S"(b), "d"(c),
          "r"(r10), "r"(r8), "r"(r9)
        : "rcx", "r11", "memory"
    );
    return rc;
}

static long sys_write(int fd, const void *buf, unsigned long n) {
    return sys6(SYS_write, fd, (long)buf, (long)n, 0, 0, 0);
}
static long sys_close(int fd) {
    return sys6(SYS_close, fd, 0, 0, 0, 0, 0);
}
static long sys_socket(int domain, int type, int proto) {
    return sys6(SYS_socket, domain, type, proto, 0, 0, 0);
}
static long sys_bind(int fd, const void *addr, unsigned long len) {
    return sys6(SYS_bind, fd, (long)addr, (long)len, 0, 0, 0);
}
static long sys_sendto(int fd, const void *buf, unsigned long n,
                       int flags, const void *addr,
                       unsigned long alen) {
    return sys6(SYS_sendto, fd, (long)buf, (long)n,
                flags, (long)addr, (long)alen);
}
static long sys_recvfrom(int fd, void *buf, unsigned long n,
                         int flags, void *addr, void *alen) {
    return sys6(SYS_recvfrom, fd, (long)buf, (long)n,
                flags, (long)addr, (long)alen);
}
static void sys_exit(int code) {
    sys6(SYS_exit_group, code, 0, 0, 0, 0, 0);
}

static unsigned long u_strlen(const char *s) {
    unsigned long n = 0;
    while (s[n]) n++;
    return n;
}
static void puts_str(const char *s) {
    sys_write(1, s, u_strlen(s));
}
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

static void make_sa(unsigned char *sa, int port,
                    int ip0, int ip1, int ip2, int ip3) {
    int i;
    for (i = 0; i < 16; i++) sa[i] = 0;
    sa[0] = AF_INET & 0xff;
    sa[1] = (AF_INET >> 8) & 0xff;
    sa[2] = (port >> 8) & 0xff;
    sa[3] = port & 0xff;
    sa[4] = (unsigned char)ip0;
    sa[5] = (unsigned char)ip1;
    sa[6] = (unsigned char)ip2;
    sa[7] = (unsigned char)ip3;
}

/* Build a minimal DNS A-record query for "example.com" into `q`.
 * Returns the query length. */
static unsigned long build_dns_query(unsigned char *q) {
    unsigned long p = 0;
    /* header (12 bytes) */
    q[p++] = (UDPTEST_QID >> 8) & 0xff;   /* id hi */
    q[p++] = UDPTEST_QID & 0xff;          /* id lo */
    q[p++] = 0x01;  /* flags hi: RD=1 (recursion desired) */
    q[p++] = 0x00;  /* flags lo */
    q[p++] = 0x00; q[p++] = 0x01;  /* QDCOUNT = 1 */
    q[p++] = 0x00; q[p++] = 0x00;  /* ANCOUNT */
    q[p++] = 0x00; q[p++] = 0x00;  /* NSCOUNT */
    q[p++] = 0x00; q[p++] = 0x00;  /* ARCOUNT */
    /* QNAME: 7"example" 3"com" 0 */
    q[p++] = 7;
    q[p++] = 'e'; q[p++] = 'x'; q[p++] = 'a'; q[p++] = 'm';
    q[p++] = 'p'; q[p++] = 'l'; q[p++] = 'e';
    q[p++] = 3;
    q[p++] = 'c'; q[p++] = 'o'; q[p++] = 'm';
    q[p++] = 0;
    /* QTYPE = A (1), QCLASS = IN (1) */
    q[p++] = 0x00; q[p++] = 0x01;
    q[p++] = 0x00; q[p++] = 0x01;
    return p;
}

int main(void) {
    volatile unsigned char dst[16];
    volatile unsigned char loc[16];
    make_sa((unsigned char *)dst, UDPTEST_DNS_PORT,
            UDPTEST_IP0, UDPTEST_IP1, UDPTEST_IP2, UDPTEST_IP3);
    make_sa((unsigned char *)loc, UDPTEST_LOCAL_PORT, 0, 0, 0, 0);

    long fd = sys_socket(AF_INET, SOCK_DGRAM, 0);
    puts_dec_line("udptest: socket fd=", fd);
    if (fd < 0) {
        puts_str("udptest: FAIL socket\n");
        sys_exit(1);
    }

    long brc = sys_bind((int)fd, (const void *)loc, 16);
    puts_dec_line("udptest: bind rc=", brc);
    if (brc != 0) {
        puts_str("udptest: FAIL bind\n");
        sys_close((int)fd);
        sys_exit(1);
    }

    unsigned char query[64];
    unsigned long qlen = build_dns_query(query);
    long src = sys_sendto((int)fd, query, qlen, 0,
                          (const void *)dst, 16);
    puts_dec_line("udptest: sendto rc=", src);
    if (src != (long)qlen) {
        puts_str("udptest: FAIL sendto\n");
        sys_close((int)fd);
        sys_exit(1);
    }

    /* Receive the DNS response. The src_addr out-param is filled with
     * the resolver's (ip, port). */
    unsigned char buf[1024];
    unsigned char from[16];
    unsigned int fromlen = 16;
    long rrc = sys_recvfrom((int)fd, buf, sizeof(buf), 0,
                            from, &fromlen);
    puts_dec_line("udptest: recvfrom rc=", rrc);
    if (rrc < 12) {
        puts_str("udptest: FAIL recvfrom\n");
        sys_close((int)fd);
        sys_exit(1);
    }

    sys_close((int)fd);

    /* Validate: the response must echo our query id and have the
     * QR (query/response) bit set (bit 7 of flags hi byte). */
    int id_ok = (buf[0] == ((UDPTEST_QID >> 8) & 0xff))
             && (buf[1] == (UDPTEST_QID & 0xff));
    int qr_ok = (buf[2] & 0x80) != 0;
    if (id_ok) {
        puts_str("udptest: dns id ok\n");
    } else {
        puts_str("udptest: FAIL dns id mismatch\n");
    }
    if (qr_ok) {
        puts_str("udptest: dns qr ok\n");
    } else {
        puts_str("udptest: FAIL dns qr bit not set\n");
    }

    if (id_ok && qr_ok) {
        puts_str("udptest: PASS\n");
        sys_exit(0);
    }
    puts_str("udptest: FAIL bad DNS response\n");
    sys_exit(1);
    return 0;
}
