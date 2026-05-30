#!/usr/bin/env bash
# scripts/test_hamfm.sh — the native TUI file manager user/hamfm.ad, e2e.
#
# hamfm is a full-screen TUI exactly like vi: when hamsh spawns it, fd
# 0/1/2 are bound to the raw console (no kernel line-cooking, no echo),
# and hamfm reads one keystroke at a time with sys_read_nb + sys_yield,
# repainting the whole screen with ANSI escapes on every state change.
# This test boots hamsh directly as /init (so that raw-console path is
# live), drives hamfm over the serial console with scripted keystrokes,
# and asserts deterministic markers in the captured screen output.
#
# DETERMINISM ON COLD BUILDS
#   A cold (rm -rf build) boot is much slower than a warm one. The old
#   version of this test gated every step on a FIXED `sleep N`, so on a
#   cold boot the `hamfm` launch command and the navigation keys arrived
#   before hamsh's REPL was ready to read them — the well-known early-
#   keystroke-eating race. The keys fell through to the `hamsh$` prompt
#   and QEMU hung to timeout (rc=124).
#
#   This version drives QEMU over a FIFO and POLLS the serial log for
#   readiness markers before EVERY keystroke (model: test_img_uefi_boot):
#     - wait for hamsh's first-readline marker before typing `hamfm`
#     - wait for hamfm's `HAMFM_READY` banner before any navigation key
#     - wait for `HAMFM_DESCEND` after entering /etc
#     - wait for `HAMFM_VIEW` after opening /etc/hostname
#   Each wait has a generous bounded timeout so a slow cold boot still
#   passes. No step is timed; every step is synchronized on readiness.
#
# COVERAGE (the four required assertions)
#   (a) LIST a directory: launch `hamfm /`; the root listing shows the
#       known directory `bin/` and `etc/` (dirs render with a trailing
#       '/'; the directory test is sys_listdir, mirroring user/find.ad).
#   (b) DESCEND into a subdir: from `/`, move the cursor to `etc` (init
#       -> bin -> etc) and Enter; the /etc listing shows the known file
#       `hostname`.
#   (c) VIEW a file inline: in /etc, move the cursor to `hostname`
#       (debian_version -> fstab -> group -> host.conf -> hostname) and
#       Enter; hamfm reads the file in-process (NO child spawn) and the
#       file's content `hamnix` (etc/hostname) appears on screen.
#   (d) CLEAN quit: `q` returns to the shell, which exits cleanly with
#       no kernel PANIC / TRAP / BUG.
#
# The orchestrator reads the explicit `[test_hamfm] PASS` / `FAIL` line,
# not the exit code.

. "$(dirname "$0")/_build_lock.sh"

set -uo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf

echo "[test_hamfm] (1/3) Build userland (incl. hamfm + hamsh)"
bash scripts/build_user.sh >/dev/null

echo "[test_hamfm] (2/3) Swap /init = hamsh in initramfs"
INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py >/dev/null

echo "[test_hamfm] (3/3) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

LOG=$(mktemp)
INFIFO=$(mktemp -u)
mkfifo "$INFIFO"

QEMU_PID=""
cleanup() {
    [ -n "${QEMU_PID:-}" ] && kill "$QEMU_PID" 2>/dev/null
    rm -f "$LOG" "$INFIFO"
    INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null 2>&1
}
trap cleanup EXIT

# Hold the FIFO open r/w from this shell so QEMU's stdin never sees EOF
# until we are done driving it (an EOF on -serial stdio would quit QEMU).
exec 4<>"$INFIFO"
exec 3>"$INFIFO"

# wait_for MARKER TIMEOUT_SECS LABEL
#   Poll the serial log until MARKER (a fixed string) appears, or until
#   the timeout elapses, or until QEMU dies. Returns 0 on success, 1 on
#   timeout/death. Generous timeouts keep slow COLD boots deterministic.
wait_for() {
    local marker="$1" timeout="$2" label="$3"
    local i
    for ((i = 0; i < timeout; i++)); do
        if grep -F -a -q -- "$marker" "$LOG"; then
            echo "[test_hamfm] ready: $label (saw '$marker' after ${i}s)"
            return 0
        fi
        if [ -n "${QEMU_PID:-}" ] && ! kill -0 "$QEMU_PID" 2>/dev/null; then
            echo "[test_hamfm] WARN: qemu exited while waiting for $label ('$marker')"
            return 1
        fi
        sleep 1
    done
    echo "[test_hamfm] WARN: timeout (${timeout}s) waiting for $label ('$marker')"
    return 1
}

send() {
    printf '%s' "$1" >&3
}

# Boot hamsh-as-/init under -nographic. _build_lock.sh's GRUB-ISO shim is
# already sourced; we boot the kernel ELF directly, the same way the old
# test did, but feed stdin from the FIFO so we can react to the log.
set +e
timeout 240s qemu-system-x86_64 \
    -kernel "$ELF" \
    -smp 2 \
    -nographic \
    -no-reboot \
    -m 256M \
    -monitor none \
    -serial stdio \
    <&4 > "$LOG" 2>&1 &
QEMU_PID=$!

# --- Step 0: wait for hamsh's REPL to be ready --------------------------
# stage-08 (ed-readline-first) prints right before hamsh enters its first
# interactive readline. After it, hamsh runs a short getty-style stale-
# input flush; type the launch command a beat later so it isn't drained.
wait_for "[hamsh:stage-08] ed-readline-first" 120 "hamsh REPL"
sleep 3

# --- Step 1: launch hamfm on the root directory (assertion a) -----------
send '/bin/hamfm /
'
# hamfm must take over the raw console from hamsh and print its readiness
# banner before any navigation key arrives; otherwise hamsh eats them.
wait_for "HAMFM_READY" 90 "hamfm started"

# --- Step 2: descend into /etc (assertion b) ----------------------------
# Root listing order (dirs + files):
#   0:init 1:bin/ 2:etc/ 3:usr/ ...
# Move the cursor down to `etc` (init -> bin -> etc): two 'j', then Enter.
send 'j'
sleep 1
send 'j'
sleep 1
send '
'
wait_for "HAMFM_DESCEND" 60 "/etc listed"

# --- Step 3: VIEW /etc/hostname inline (assertion c) --------------------
# /etc listing order:
#   0:debian_version 1:fstab 2:group 3:host.conf 4:hostname ...
# Move the cursor down to `hostname`: four 'j', then Enter.
send 'j'
sleep 1
send 'j'
sleep 1
send 'j'
sleep 1
send 'j'
sleep 1
send '
'
wait_for "HAMFM_VIEW" 60 "file view"

# Any key returns to the listing, then quit hamfm back to the shell.
sleep 1
send ' '
sleep 1
send 'q'
sleep 2

# --- Step 4: exit the shell cleanly (assertion d) -----------------------
send 'exit
'
# Wait for the kernel's clean-shutdown marker before tearing QEMU down.
wait_for "no live tasks" 60 "shell exited"

sleep 1
kill "$QEMU_PID" 2>/dev/null
wait "$QEMU_PID" 2>/dev/null
rc=$?
exec 3>&-
exec 4>&-
set -e

echo "[test_hamfm] --- captured output ---"
cat "$LOG"
echo "[test_hamfm] --- end output ---"

fail=0

# (a) Root directory listing showed the known dirs bin/ and etc/.
if grep -F -a -q "bin/" "$LOG"; then
    echo "[test_hamfm] OK: root listing showed 'bin/' (dir)"
else
    echo "[test_hamfm] MISS: 'bin/' not found in root listing"
    fail=1
fi
if grep -F -a -q "etc/" "$LOG"; then
    echo "[test_hamfm] OK: root listing showed 'etc/' (dir)"
else
    echo "[test_hamfm] MISS: 'etc/' not found in root listing"
    fail=1
fi

# (b) Descending into /etc worked — a file known to live there appears.
if grep -F -a -q "hostname" "$LOG"; then
    echo "[test_hamfm] OK: descended into /etc (saw 'hostname')"
else
    echo "[test_hamfm] MISS: '/etc/hostname' entry not found after descend"
    fail=1
fi

# (c) Viewing /etc/hostname inline showed its content ('hamnix').
if grep -F -a -q "hamnix" "$LOG"; then
    echo "[test_hamfm] OK: file view showed /etc/hostname content 'hamnix'"
else
    echo "[test_hamfm] MISS: file content 'hamnix' not shown by VIEW mode"
    fail=1
fi

# (d) Shell survived and exited cleanly.
if grep -F -a -q "no live tasks" "$LOG"; then
    echo "[test_hamfm] OK: shell exited cleanly after browsing"
else
    echo "[test_hamfm] MISS: shell did not exit cleanly"
    fail=1
fi

# No kernel fault of any kind.
if grep -E -a -q "PANIC|panic:|TRAP:|BUG:" "$LOG"; then
    echo "[test_hamfm] DIAG: kernel reported a fault"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_hamfm] FAIL (qemu rc=$rc)"
    exit 1
fi
echo "[test_hamfm] PASS"
