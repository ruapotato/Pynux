/*
 * tests/u-binary/src/sockopt/sockopt.c — §10 getsockopt/setsockopt
 * round-trip fixture.
 *
 * Exercises the userland setsockopt(2)/getsockopt(2) syscalls bridged
 * to the per-socket-record option store (linux_abi/u_socket_state.ad)
 * by linux_abi/u_syscalls.ad. No network traffic — purely a
 * set-then-get round-trip on the common options server daemons set:
 *
 *     socket(AF_INET, SOCK_STREAM, 0)
 *     setsockopt(SO_REUSEADDR, 1)  -> getsockopt must read back 1
 *     setsockopt(SO_RCVBUF, V)     -> getsockopt must read back V
 *     setsockopt(TCP_NODELAY, 1)   -> getsockopt must read back 1
 *     getsockopt(SO_ERROR)         -> must read 0 (no pending error)
 *     close(fd)
 *
 * Built with musl-gcc -static-pie; OSABI stamped to ELFOSABI_LINUX.
 *
 * Markers (on stdout — the harness greps for these):
 *   "sockopt: reuseaddr ok"
 *   "sockopt: rcvbuf ok"
 *   "sockopt: nodelay ok"
 *   "sockopt: so_error ok"
 *   "sockopt: badopt rejected ok"
 *   "sockopt: PASS" / "sockopt: FAIL ..."
 */

#include <stdint.h>

#define SYS_close       3
#define SYS_socket      41
#define SYS_setsockopt  54
#define SYS_getsockopt  55
#define SYS_write       1
#define SYS_exit_group  231

#define AF_INET      2
#define SOCK_STREAM  1
#define SOCK_DGRAM   2

#define SOL_SOCKET   1
#define IPPROTO_TCP  6

#define SO_REUSEADDR 2
#define SO_ERROR     4
#define SO_BROADCAST 6
#define SO_SNDBUF    7
#define SO_RCVBUF    8
#define SO_KEEPALIVE 9
#define SO_REUSEPORT 15
#define TCP_NODELAY  1

static long sys5(long nr, long a, long b, long c, long d, long e) {
    long rc;
    register long r10 __asm__("r10") = d;
    register long r8  __asm__("r8")  = e;
    __asm__ volatile (
        "syscall"
        : "=a"(rc)
        : "0"(nr), "D"(a), "S"(b), "d"(c), "r"(r10), "r"(r8)
        : "rcx", "r11", "memory"
    );
    return rc;
}

static long sys_write(int fd, const void *buf, unsigned long n) {
    return sys5(SYS_write, fd, (long)buf, (long)n, 0, 0);
}
static long sys_close(int fd) {
    return sys5(SYS_close, fd, 0, 0, 0, 0);
}
static long sys_socket(int domain, int type, int proto) {
    return sys5(SYS_socket, domain, type, proto, 0, 0);
}
static long sys_setsockopt(int fd, int level, int optname,
                           const void *val, unsigned long len) {
    return sys5(SYS_setsockopt, fd, level, optname,
                (long)val, (long)len);
}
static long sys_getsockopt(int fd, int level, int optname,
                           void *val, void *len) {
    return sys5(SYS_getsockopt, fd, level, optname,
                (long)val, (long)len);
}
static void sys_exit(int code) {
    sys5(SYS_exit_group, code, 0, 0, 0, 0);
}

static unsigned long u_strlen(const char *s) {
    unsigned long n = 0;
    while (s[n]) n++;
    return n;
}
static void puts_str(const char *s) {
    sys_write(1, s, u_strlen(s));
}
static void puts_dec_line(const char *prefix, long v) {
    char line[96];
    unsigned long p = 0;
    const char *s = prefix;
    while (*s) line[p++] = *s++;
    char tmp[24];
    int ti = 0;
    int neg = 0;
    unsigned long uv;
    if (v < 0) { neg = 1; uv = (unsigned long)(-v); }
    else       { uv = (unsigned long)v; }
    if (uv == 0) tmp[ti++] = '0';
    while (uv) { tmp[ti++] = (char)('0' + (uv % 10)); uv /= 10; }
    if (neg) line[p++] = '-';
    while (ti) line[p++] = tmp[--ti];
    line[p++] = '\n';
    sys_write(1, line, p);
}

/* setsockopt an int, then getsockopt it back; return 1 if the value
 * round-trips, 0 otherwise. */
static int rt_int(int fd, int level, int optname, int set_val) {
    int sv = set_val;
    long src = sys_setsockopt(fd, level, optname, &sv, sizeof(sv));
    if (src != 0) {
        puts_dec_line("sockopt:   setsockopt rc=", src);
        return 0;
    }
    int gv = -1;
    unsigned int gl = sizeof(gv);
    long grc = sys_getsockopt(fd, level, optname, &gv, &gl);
    if (grc != 0) {
        puts_dec_line("sockopt:   getsockopt rc=", grc);
        return 0;
    }
    if (gv != set_val) {
        puts_dec_line("sockopt:   round-trip mismatch got=", gv);
        return 0;
    }
    return 1;
}

int main(void) {
    int fails = 0;

    long fd = sys_socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        puts_str("sockopt: FAIL socket\n");
        sys_exit(1);
    }

    /* SO_REUSEADDR — boolean flag a server daemon always sets. */
    if (rt_int((int)fd, SOL_SOCKET, SO_REUSEADDR, 1)) {
        puts_str("sockopt: reuseaddr ok\n");
    } else {
        puts_str("sockopt: FAIL reuseaddr\n");
        fails++;
    }

    /* SO_RCVBUF — a non-boolean integer; must round-trip verbatim. */
    if (rt_int((int)fd, SOL_SOCKET, SO_RCVBUF, 131072)) {
        puts_str("sockopt: rcvbuf ok\n");
    } else {
        puts_str("sockopt: FAIL rcvbuf\n");
        fails++;
    }

    /* TCP_NODELAY at level IPPROTO_TCP. */
    if (rt_int((int)fd, IPPROTO_TCP, TCP_NODELAY, 1)) {
        puts_str("sockopt: nodelay ok\n");
    } else {
        puts_str("sockopt: FAIL nodelay\n");
        fails++;
    }

    /* SO_ERROR — read-only, must report 0 (no pending error) on a
     * fresh socket. */
    {
        int ev = -1;
        unsigned int el = sizeof(ev);
        long grc = sys_getsockopt((int)fd, SOL_SOCKET, SO_ERROR,
                                  &ev, &el);
        if (grc == 0 && ev == 0) {
            puts_str("sockopt: so_error ok\n");
        } else {
            puts_dec_line("sockopt: FAIL so_error ev=", ev);
            fails++;
        }
    }

    /* An unmodelled option must be REJECTED with -ENOPROTOOPT (-92),
     * not silently accepted — a daemon depending on a real option
     * needs to learn it is unsupported. optname 9999 is bogus. */
    {
        int bv = 1;
        long src = sys_setsockopt((int)fd, SOL_SOCKET, 9999,
                                  &bv, sizeof(bv));
        if (src == -92) {
            puts_str("sockopt: badopt rejected ok\n");
        } else {
            puts_dec_line("sockopt: FAIL badopt rc=", src);
            fails++;
        }
    }

    sys_close((int)fd);

    /* Also confirm SO_BROADCAST round-trips on a UDP socket. */
    {
        long ufd = sys_socket(AF_INET, SOCK_DGRAM, 0);
        if (ufd < 0) {
            puts_str("sockopt: FAIL udp socket\n");
            fails++;
        } else {
            if (rt_int((int)ufd, SOL_SOCKET, SO_BROADCAST, 1)) {
                puts_str("sockopt: broadcast ok\n");
            } else {
                puts_str("sockopt: FAIL broadcast\n");
                fails++;
            }
            sys_close((int)ufd);
        }
    }

    if (fails == 0) {
        puts_str("sockopt: PASS\n");
        sys_exit(0);
    }
    puts_str("sockopt: FAIL\n");
    sys_exit(1);
    return 0;
}
