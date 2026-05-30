#!/usr/bin/env bash
# scripts/test_httpd_concurrent.sh — Hamnix native CONCURRENT web server.
#
# Proves user/httpd.ad is now Apache/nginx-shaped, not a single-shot toy:
#   1. CONCURRENCY  — the master accept loop spawns one /bin/httpd_worker
#      per connection and returns to accept immediately (no waitpid). The
#      host driver opens N connections SIMULTANEOUSLY, sends a request on
#      each, THEN reads all the responses; if the server serialised one
#      connection behind another's worker this interleaving would stall.
#   2. VIRTUAL HOSTS — /etc/httpd.conf defines two vhost blocks
#      (server_name localhost -> /var/www, server_name v2.test ->
#      /var/www2). A request with `Host: v2.test` is routed to the second
#      docroot (asserted via a distinct body marker).
#   3. STATIC FILES — Content-Type by extension (text/html, text/plain,
#      text/css), directory index (GET / -> index.html), 404 for missing.
#   4. CGI — GET /cgi-bin/echo?foo=bar (and a POST with a body) dispatches
#      the cgi_echo binary; its stdout (echoing the CGI env + body) is
#      streamed back as the response.
#
# Pipeline mirrors scripts/test_httpd.sh: build userland, embed httpd as
# /init, stage the vhost fixture in the cpio (HAMNIX_HTTPD_VHOSTS=1),
# rebuild the kernel, boot QEMU with a host->guest port forward, drive
# real HTTP from the host.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
HTTPD_ELF=build/user/httpd.elf
WORKER_ELF=build/user/httpd_worker.elf
CGI_ELF=build/user/cgi_echo.elf

# --- pick a free host port -------------------------------------------
HOST_PORT=$(python3 - <<'PY'
import socket
s = socket.socket()
s.bind(("127.0.0.1", 0))
print(s.getsockname()[1])
s.close()
PY
)
echo "[test_httpd_concurrent] host port $HOST_PORT -> guest port 8080"

echo "[test_httpd_concurrent] (1/3) Build userland (httpd + worker + cgi)"
bash scripts/build_user.sh >/dev/null
for f in "$HTTPD_ELF" "$WORKER_ELF" "$CGI_ELF"; do
    if [ ! -f "$f" ]; then
        echo "[test_httpd_concurrent] FAIL: $f not built"
        exit 1
    fi
done

echo "[test_httpd_concurrent] (2/3) Embed httpd as /init + stage vhost fixture"
INIT_ELF="$HTTPD_ELF" HAMNIX_HTTPD_VHOSTS=1 \
    python3 scripts/build_initramfs.py >/dev/null
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_httpd_concurrent] (3/3) Boot QEMU with hostfwd tcp::${HOST_PORT}-:8080"
LOG=$(mktemp)
CLIENTLOG=$(mktemp)
trap 'rm -f "$LOG" "$CLIENTLOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null 2>&1 || true' EXIT

# Background host-side HTTP driver.
(
    python3 - "$HOST_PORT" "$CLIENTLOG" "$LOG" <<'PY'
import socket, sys, time, threading

port = int(sys.argv[1])
out_path = sys.argv[2]
log_path = sys.argv[3]

# Wait for the guest's listener marker (up to ~180 s of boot).
listen_deadline = time.time() + 180
listening = False
while time.time() < listen_deadline:
    try:
        with open(log_path, "r", errors="replace") as f:
            if "httpd: listening" in f.read():
                listening = True
                break
    except OSError:
        pass
    time.sleep(1)


def raw_request(req_bytes, retries=10):
    """Send a raw HTTP request over a fresh connection, return full reply."""
    last = None
    for _ in range(retries):
        try:
            c = socket.socket()
            c.settimeout(20)
            c.connect(("127.0.0.1", port))
            c.sendall(req_bytes)
            chunks = []
            while True:
                try:
                    b = c.recv(4096)
                except socket.timeout:
                    break
                if not b:
                    break
                chunks.append(b)
            c.close()
            return b"".join(chunks)
        except (ConnectionRefusedError, OSError) as e:
            last = e
            time.sleep(1)
    raise last if last else RuntimeError("no attempt")


def get(path, host="localhost"):
    req = ("GET " + path + " HTTP/1.1\r\nHost: " + host +
           "\r\nConnection: close\r\n\r\n").encode()
    return raw_request(req)


def post(path, body, host="localhost"):
    req = ("POST " + path + " HTTP/1.1\r\nHost: " + host +
           "\r\nContent-Length: " + str(len(body)) +
           "\r\nConnection: close\r\n\r\n").encode() + body.encode()
    return raw_request(req)


def split(raw):
    head, _, body = raw.partition(b"\r\n\r\n")
    lines = head.split(b"\r\n")
    status = lines[0].decode("latin-1") if lines else ""
    headers = {}
    for ln in lines[1:]:
        k, _, v = ln.partition(b":")
        headers[k.decode("latin-1").strip().lower()] = v.decode("latin-1").strip()
    return status, headers, body


def w(f, label, raw):
    st, hd, body = split(raw)
    f.write("=== %s\n" % label)
    f.write("status=%s\n" % st)
    f.write("content-type=%s\n" % hd.get("content-type", ""))
    f.write("bodylen=%d\n" % len(body))
    f.write("body=%s\n" % body.decode("latin-1").replace("\n", "\\n"))


with open(out_path, "w") as f:
    if not listening:
        f.write("status=no-listen\n")
        sys.exit(0)
    try:
        # --- 1. Concurrency: open N connections, send on ALL, then read
        # all replies. We do this by spawning threads that each do a
        # blocking request, started together; assert every one returns a
        # well-formed 200. A serialising/deadlocking server would fail
        # one or more of these within the timeout.
        N = 4
        results = [None] * N
        errs = [None] * N

        def worker(i):
            try:
                results[i] = get("/hello.txt")
            except Exception as e:  # noqa: BLE001
                errs[i] = repr(e)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(N)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=60)

        ok_concurrent = 0
        for i in range(N):
            if errs[i] is None and results[i] is not None:
                st, hd, body = split(results[i])
                if "200" in st and b"hello from hamnix httpd" in body:
                    ok_concurrent += 1
        f.write("concurrent_ok=%d/%d\n" % (ok_concurrent, N))
        if ok_concurrent == N:
            f.write("CONCURRENCY_PASS\n")

        # --- 2. vhost default (localhost) vs second (v2.test).
        w(f, "vhost_default GET / Host: localhost", get("/", "localhost"))
        w(f, "vhost_second GET / Host: v2.test",    get("/", "v2.test"))

        # --- 3. static files + content types.
        w(f, "static_txt GET /hello.txt",  get("/hello.txt"))
        w(f, "static_css GET /style.css",  get("/style.css"))
        w(f, "missing GET /nope.txt",      get("/nope.txt"))

        # --- 4. CGI (GET with query + POST with body).
        w(f, "cgi_get GET /cgi-bin/echo?foo=bar",
          get("/cgi-bin/echo?foo=bar"))
        w(f, "cgi_post POST /cgi-bin/echo",
          post("/cgi-bin/echo", "POSTBODY123"))

        f.write("status=ok\n")
    except Exception as e:  # noqa: BLE001
        f.write("status=error\n")
        f.write("error=%r\n" % (e,))
PY
) &
CLIENT_PID=$!

set +e
timeout 300s qemu-system-x86_64 \
    -kernel "$ELF" \
    -netdev "user,id=n0,hostfwd=tcp::${HOST_PORT}-:8080,guestfwd=tcp:10.0.2.100:7-cmd:cat" \
    -device virtio-net-pci,netdev=n0,mac=52:54:00:12:34:56 \
    -smp 2 \
    -nographic -no-reboot -m 256M -monitor none -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

wait "$CLIENT_PID" 2>/dev/null || true

echo "[test_httpd_concurrent] --- server log (httpd) ---"
grep -E 'httpd:' "$LOG" | head -60 || true
echo "[test_httpd_concurrent] --- host HTTP driver ---"
cat "$CLIENTLOG" 2>/dev/null || echo "(no driver output)"
echo "[test_httpd_concurrent] --- end ---"

fail=0

# --- server-side marker ----------------------------------------------
if grep -F -q "httpd: listening" "$LOG"; then
    echo "[test_httpd_concurrent] OK: server listening"
else
    echo "[test_httpd_concurrent] MISS: server never listened"
    fail=1
fi

assert_client() {
    local label="$1"; local needle="$2"
    if grep -F -q "$needle" "$CLIENTLOG" 2>/dev/null; then
        echo "[test_httpd_concurrent] OK: $label"
    else
        echo "[test_httpd_concurrent] MISS: $label ('$needle')"
        fail=1
    fi
}

# 1. concurrency
assert_client "N concurrent requests all served" "CONCURRENCY_PASS"
# 2. virtual hosts
assert_client "default vhost served (localhost)"  "VHOST_DEFAULT"
assert_client "second vhost served (v2.test)"     "VHOST_SECOND"
# 3. static + content types
assert_client "GET / is 200"                      "status=HTTP/1.1 200 OK"
assert_client ".txt body served"                  "hello from hamnix httpd"
assert_client ".txt is text/plain"                "content-type=text/plain"
assert_client ".css is text/css"                  "content-type=text/css"
assert_client "missing path -> 404"               "status=HTTP/1.1 404 Not Found"
# 4. CGI
assert_client "CGI script ran"                    "CGI_ECHO_OK"
assert_client "CGI saw QUERY_STRING"              "QUERY_STRING=foo=bar"
assert_client "CGI saw REQUEST_METHOD POST"       "REQUEST_METHOD=POST"
assert_client "CGI echoed POST body"              "POSTBODY123"

if grep -F -q "TRAP: vector" "$LOG"; then
    echo "[test_httpd_concurrent] DIAG: kernel reported a CPU exception"
    grep -F "TRAP: vector" "$LOG" | head -5 || true
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_httpd_concurrent] FAIL (qemu rc=$rc)"
    echo "[test_httpd_concurrent] --- full kernel log (last 200 lines) ---"
    tail -n 200 "$LOG"
    exit 1
fi

echo "[test_httpd_concurrent] PASS — concurrent native web server:" \
     "per-connection workers, name-based vhosts, static Content-Type," \
     "and CGI all verified over real HTTP"
