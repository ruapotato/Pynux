#!/usr/bin/env bash
# scripts/test_u28_musl_thread_join_many.sh -- U28 stress fixture.
#
# N workers, each doing mmap+write+munmap loops. Validates fd-table
# sharing and per-thread state isolation across the CLONE_VM|
# CLONE_FILES path.
#
# PASS criteria: 4 "U28: jthread N done" markers (N=1..4) plus the
# final "U28: jcounter=4 (expect 4)".

. "$(dirname "$0")/_build_lock.sh"
. "$(dirname "$0")/_qemu_drive.sh"
. "$(dirname "$0")/_ensure_ubin.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

UBIN=tests/u-binary/u_musl_thread_join_many
# Build-on-missing: the fixture is gitignored (host-built). If absent,
# build it from tests/u-binary/src/musl_thread_join_many; only SKIP on
# a real failure (e.g. a genuine missing musl-gcc).
ensure_ubin_or_skip test_u28_musl_thread_join_many u_musl_thread_join_many musl_thread_join_many

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf

echo "[test_u28_musl_thread_join_many] (1/4) Build userland"
bash scripts/build_user.sh
bash scripts/build_modules.sh

echo "[test_u28_musl_thread_join_many] (2/4) Swap /init + embed binary"
HAMNIX_EMBED_UBIN=1 INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py

echo "[test_u28_musl_thread_join_many] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF"

echo "[test_u28_musl_thread_join_many] (4/4) Boot QEMU + run binary"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# Prompt-aware drive: wait for hamsh's ready banner before sending
# input. A fixed `sleep 3` races boot-time variance and drops the
# command onto the 16550 RX FIFO before hamsh's readline is armed —
# the binary then never runs (see _qemu_drive.sh).
set +e
qemu_drive "$LOG" "$ELF" "[hamsh] M16.35 shell ready" 50 \
    -- "u_musl_thread_join_many" 15 \
       "exit" 1
rc="$QEMU_DRIVE_RC"
set -e

echo "[test_u28_musl_thread_join_many] --- captured output ---"
cat "$LOG"
echo "[test_u28_musl_thread_join_many] --- end output ---"

fail=0

check_marker() {
    local label="$1"
    local needle="$2"
    if grep -F -q "$needle" "$LOG"; then
        echo "[test_u28_musl_thread_join_many] OK: $label  ('$needle')"
    else
        echo "[test_u28_musl_thread_join_many] MISS: $label  ('$needle')"
        fail=1
    fi
}

for i in 1 2 3 4; do
    check_marker "jthread $i done" "U28: jthread $i done"
done
check_marker "jcounter=4" "U28: jcounter=4 (expect 4)"

if grep -F -q "unknown syscall" "$LOG"; then
    echo "[test_u28_musl_thread_join_many] DIAG: unknown syscall(s)"
    grep -F "unknown syscall" "$LOG" | sort -u || true
fi
if grep -F -q "TRAP: vector" "$LOG"; then
    echo "[test_u28_musl_thread_join_many] DIAG: CPU exception"
    grep -F "TRAP: vector" "$LOG" | head -5 || true
fi
if grep -F -q "mmap table full" "$LOG"; then
    echo "[test_u28_musl_thread_join_many] DIAG: mmap table full"
fi
if grep -F -q "MISMATCH" "$LOG"; then
    echo "[test_u28_musl_thread_join_many] DIAG: per-thread page mismatch"
    grep -F "MISMATCH" "$LOG" | head -5 || true
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_u28_musl_thread_join_many] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_u28_musl_thread_join_many] PASS -- N-thread mmap loop + fd-table share"
