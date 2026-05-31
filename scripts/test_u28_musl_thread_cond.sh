#!/usr/bin/env bash
# scripts/test_u28_musl_thread_cond.sh -- U28 stress fixture.
#
# pthread_cond_t exerciser: producer signals N times via
# pthread_cond_signal; consumer counts via pthread_cond_wait. Hits
# FUTEX_REQUEUE / FUTEX_CMP_REQUEUE (ops 3/4), which U27's _u_futex
# folds to FUTEX_WAKE — this test validates that fold for a simple
# producer/consumer.
#
# PASS criteria: both done markers and the count line:
#   - "U28: cond producer done"
#   - "U28: cond consumer done"
#   - "U28: cond_count=5 (expect 5)"

. "$(dirname "$0")/_build_lock.sh"
. "$(dirname "$0")/_qemu_drive.sh"
. "$(dirname "$0")/_ensure_ubin.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

UBIN=tests/u-binary/u_musl_thread_cond
# Build-on-missing: the fixture is gitignored (host-built). If absent,
# build it from tests/u-binary/src/musl_thread_cond; only SKIP on a
# real failure (e.g. a genuine missing musl-gcc).
ensure_ubin_or_skip test_u28_musl_thread_cond u_musl_thread_cond musl_thread_cond

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf

echo "[test_u28_musl_thread_cond] (1/4) Build userland"
bash scripts/build_user.sh
bash scripts/build_modules.sh

echo "[test_u28_musl_thread_cond] (2/4) Swap /init + embed binary"
HAMNIX_EMBED_UBIN=1 INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py

echo "[test_u28_musl_thread_cond] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF"

echo "[test_u28_musl_thread_cond] (4/4) Boot QEMU + run binary"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# Prompt-aware drive: wait for hamsh's ready banner before sending
# input. A fixed `sleep 3` races boot-time variance and drops the
# command onto the 16550 RX FIFO before hamsh's readline is armed —
# the binary then never runs (see _qemu_drive.sh).
set +e
qemu_drive "$LOG" "$ELF" "[hamsh] M16.35 shell ready" 45 \
    -- "u_musl_thread_cond" 12 \
       "exit" 1
rc="$QEMU_DRIVE_RC"
set -e

echo "[test_u28_musl_thread_cond] --- captured output ---"
cat "$LOG"
echo "[test_u28_musl_thread_cond] --- end output ---"

fail=0

check_marker() {
    local label="$1"
    local needle="$2"
    if grep -F -q "$needle" "$LOG"; then
        echo "[test_u28_musl_thread_cond] OK: $label  ('$needle')"
    else
        echo "[test_u28_musl_thread_cond] MISS: $label  ('$needle')"
        fail=1
    fi
}

check_marker "producer done"     "U28: cond producer done"
check_marker "consumer done"     "U28: cond consumer done"
check_marker "cond_count=5"      "U28: cond_count=5 (expect 5)"

if grep -F -q "unknown syscall" "$LOG"; then
    echo "[test_u28_musl_thread_cond] DIAG: unknown syscall(s)"
    grep -F "unknown syscall" "$LOG" | sort -u || true
fi
if grep -F -q "TRAP: vector" "$LOG"; then
    echo "[test_u28_musl_thread_cond] DIAG: CPU exception"
    grep -F "TRAP: vector" "$LOG" | head -5 || true
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_u28_musl_thread_cond] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_u28_musl_thread_cond] PASS -- pthread_cond_wait + signal works"
