#!/usr/bin/env bash
# scripts/test_time.sh — §146 high-resolution time regression test.
#
# Drives tests/test_time.ad, which:
#   T1. CLOCK_MONOTONIC advances between two reads.
#   T2. CLOCK_REALTIME is non-zero (or QEMU RTC-absent diagnostic).
#   T3. nanosleep(50 ms): elapsed >= 40 ms and < 2000 ms.
#   T4. timerfd one-shot (50 ms): read() returns expiry count >= 1.
#   T5. timerfd periodic (50 ms interval): accumulated count >= 2.
#
# PASS = serial log contains all of:
#   [time] T1 PASS
#   [time] T2 PASS
#   [time] T3 PASS
#   [time] T4 PASS
#   [time] T5 PASS
#   [time] PASS
# and no "[time] FAIL" line.

. "$(dirname "$0")/_build_lock.sh"
. "$(dirname "$0")/_qemu_drive.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf
TEST_ELF=build/user/test_time.elf

echo "[test_time] (1/5) Build userland (hamsh + helpers)"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

echo "[test_time] (2/5) Build tests/test_time.ad -> $TEST_ELF"
python3 -m compiler.adder compile \
    --target=x86_64-adder-user \
    tests/test_time.ad \
    -o "$TEST_ELF" >/dev/null

echo "[test_time] (3/5) Plant /init = hamsh + /bin/test_time in cpio"
INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py >/dev/null

echo "[test_time] (4/5) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_time] (5/5) Boot QEMU + drive the test via hamsh"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
# Allow 120 s: T3 sleeps 50 ms, T4 polls ~50 ms, T5 polls ~100 ms;
# total test time is < 1 s in practice but give headroom for slow QEMU.
qemu_drive "$LOG" "$ELF" "[hamsh] M16.35 shell ready" 120 \
    -- "/bin/test_time" 60 \
       "exit" 1
rc="$QEMU_DRIVE_RC"
set -e

echo "[test_time] --- captured output ---"
cat "$LOG"
echo "[test_time] --- end output ---"

fail=0

# Check per-test PASS banners.
for t in 1 2 3 4 5; do
    if grep -F -q "[time] T${t} PASS" "$LOG"; then
        echo "[test_time] OK: T${t} passed"
    else
        echo "[test_time] MISS: T${t} PASS banner absent"
        fail=1
    fi
done

# A FAIL line is a hard failure.
if grep -F -q "[time] FAIL" "$LOG"; then
    echo "[test_time] FAIL: fixture reported a failure"
    grep -F "[time] FAIL" "$LOG" || true
    fail=1
fi

# Final PASS banner.
if grep -F -q "[time] PASS" "$LOG"; then
    echo "[test_time] OK: fixture reached final PASS"
else
    echo "[test_time] MISS: final PASS banner absent"
    fail=1
fi

# Kernel exception diagnostics.
if grep -F -q "[trap-diag] vec=" "$LOG"; then
    echo "[test_time] DIAG: kernel reported a CPU exception"
    grep -F "[trap-diag] vec=" "$LOG" | head -6 || true
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_time] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_time] PASS -- clock_gettime/nanosleep/timerfd working"
