#!/usr/bin/env bash
# scripts/test_hamsh_heartbeat.sh — assert hamsh (PID 1) gets CPU time.
#
# Boots build/hamnix.iso headless under QEMU, captures the serial console
# for ~30 s, and looks for the "[hamsh-alive] tick=1" line that hamsh's
# interactive idle loop emits every ~3 s (HB_PERIOD_JIFFIES = 300 ticks
# @ HZ=100).
#
# This is a load-bearing scheduler-liveness test (per feedback_-
# regression_prone_needs_test.md). The heartbeat line silently regressed
# across 100+ commits because no CI grep checked it. If hamsh-as-PID-1
# never runs (because a kernel busy-poll wedged the CPU with IF=0, or a
# greedy userland task starved the scheduler), this test catches it.
#
# Exit codes:
#   0  — heartbeat tick=1 observed.
#   1  — boot succeeded but no heartbeat tick in the window OR build/boot
#         failed.
#
# Env overrides:
#   HAMNIX_ISO        iso path           (default: build/hamnix.iso)
#   HEARTBEAT_TIMEOUT seconds to capture (default: 30)
#   HAMNIX_SKIP_BUILD if 1, reuse existing build/hamnix.iso

set -euo pipefail

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

# shellcheck source=_build_lock.sh
source "$PROJ_ROOT/scripts/_build_lock.sh"

HAMNIX_ISO="${HAMNIX_ISO:-build/hamnix.iso}"
HEARTBEAT_TIMEOUT="${HEARTBEAT_TIMEOUT:-30}"
HEARTBEAT_RE='\[hamsh-alive\] tick=1'

if [ "${HAMNIX_SKIP_BUILD:-0}" != "1" ]; then
    echo "[test_hamsh_heartbeat] rebuilding ISO (clean) via scripts/build_iso.sh"
    rm -rf build
    bash "$PROJ_ROOT/scripts/build_iso.sh"
fi
if [ ! -f "$HAMNIX_ISO" ]; then
    echo "[test_hamsh_heartbeat] FAIL: $HAMNIX_ISO missing after build_iso.sh." >&2
    exit 1
fi

LOG=$(mktemp --tmpdir hamnix-heartbeat.XXXXXX.log)
trap 'rm -f "$LOG"' EXIT

echo "[test_hamsh_heartbeat] booting QEMU headless (timeout ${HEARTBEAT_TIMEOUT}s)"
set +e
timeout "${HEARTBEAT_TIMEOUT}s" qemu-system-x86_64 \
    -cdrom "$HAMNIX_ISO" \
    -m 256M \
    -display none \
    -no-reboot \
    -monitor none \
    -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

# rc=124 means timeout fired — expected. rc=0 means qemu exited cleanly.
# Anything else is a qemu-side problem.
if [ "$rc" -ne 0 ] && [ "$rc" -ne 124 ]; then
    echo "[test_hamsh_heartbeat] FAIL: qemu exited rc=$rc" >&2
    echo "[test_hamsh_heartbeat] --- tail of log ---"
    tail -50 "$LOG" || true
    exit 1
fi

if grep -a -q -E "$HEARTBEAT_RE" "$LOG"; then
    line=$(grep -a -E "$HEARTBEAT_RE" "$LOG" | head -1)
    echo "[test_hamsh_heartbeat] PASS: heartbeat observed -> $line"
    exit 0
fi

echo "[test_hamsh_heartbeat] FAIL: no '[hamsh-alive] tick=1' line in ${HEARTBEAT_TIMEOUT}s of serial output." >&2
echo "[test_hamsh_heartbeat] This means hamsh (PID 1) never reached its interactive idle loop," >&2
echo "[test_hamsh_heartbeat] OR a kernel busy-poll wedged the CPU (e.g. tcp_accept's while-jiffies" >&2
echo "[test_hamsh_heartbeat] loop running under SYSCALL IF=0)." >&2
echo "[test_hamsh_heartbeat] --- tail of log ---"
tail -80 "$LOG" || true
exit 1
