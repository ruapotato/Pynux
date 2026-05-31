#!/usr/bin/env bash
# scripts/test_u47_cow_fork.sh -- #143 fork() COW isolation e2e fixture.
#
# Copy-on-write fork() is fully implemented in the kernel (mm/cow.ad COW
# refcount + share/copy, the #PF arm in arch/x86/kernel/trap_diag.ad that
# calls cow_handle_write_fault, and fork's vm_cow_share_all / per-region
# copy machinery in fs/elf.ad) but had ZERO automated coverage, so it
# could silently regress. This fixture proves the load-bearing CORRECTNESS
# property: fork() gives the child a PRIVATE, ISOLATED address space.
#
# A real musl binary:
#   - seeds a writable GLOBAL array, a HEAP (malloc) buffer, and an
#     anonymous mmap() region with a parent sentinel,
#   - fork()s child A which overwrites all three and confirms it sees its
#     OWN writes (each write faults a COW page -> private copy),
#   - parent waitpid()s, then confirms its three copies are STILL the
#     parent sentinel (the child's writes did NOT leak back),
#   - parent rewrites with a 2nd sentinel and fork()s child B, which must
#     read the live snapshot (proving each fork is an independent copy),
#   - parent re-confirms its buffers are untouched.
#
# PASS criteria: all isolation markers land on serial:
#   - "COW: child saw its write"
#   - "COW: parent copy intact"
#   - "COW: second child saw parent snapshot"
#   - "COW: parent intact after second child"
#   - "cow_fork: PASS"
#
# Build-on-missing: the fixture is gitignored (host-built). If absent,
# build it from tests/u-binary/src/cow_fork; only SKIP on a real build
# failure (e.g. a genuine missing musl-gcc).
#
# REQUIRES: musl-gcc on $PATH. Build step:
#     make -C tests/u-binary/src/cow_fork install
#
# NOTE: a trailing QEMU rc=124 AFTER the markers have printed is benign
# (the kernel halts without powering off qemu, so the watchdog reaps it);
# the grep marker checks below are authoritative.

. "$(dirname "$0")/_build_lock.sh"
. "$(dirname "$0")/_qemu_drive.sh"
. "$(dirname "$0")/_ensure_ubin.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

UBIN=tests/u-binary/u_cow_fork
ensure_ubin_or_skip test_u47_cow_fork u_cow_fork cow_fork

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf

echo "[test_u47_cow_fork] (1/4) Build userland (hamsh + helpers)"
bash scripts/build_user.sh
bash scripts/build_modules.sh

echo "[test_u47_cow_fork] (2/4) Swap /init = $HAMSH_ELF + embed u_cow_fork"
HAMNIX_EMBED_UBIN=1 INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py

echo "[test_u47_cow_fork] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF"

echo "[test_u47_cow_fork] (4/4) Boot QEMU + run /bin/u_cow_fork via hamsh"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# Prompt-aware drive: wait for hamsh's ready banner before sending input
# (a fixed sleep races boot-time variance -- see _qemu_drive.sh).
set +e
qemu_drive "$LOG" "$ELF" "[hamsh] M16.35 shell ready" 45 \
    -- "u_cow_fork" 8 \
       "exit" 1
rc="$QEMU_DRIVE_RC"
set -e

echo "[test_u47_cow_fork] --- captured output ---"
cat "$LOG"
echo "[test_u47_cow_fork] --- end output ---"

fail=0

check_marker() {
    local label="$1"
    local needle="$2"
    # -a: the serial log carries binary bytes; treat it as text.
    if grep -a -F -q "$needle" "$LOG"; then
        echo "[test_u47_cow_fork] OK: $label  ('$needle')"
    else
        echo "[test_u47_cow_fork] MISS: $label  ('$needle')"
        fail=1
    fi
}

check_marker "child saw its write"      "COW: child saw its write"
check_marker "parent copy intact"       "COW: parent copy intact"
check_marker "second child snapshot"    "COW: second child saw parent snapshot"
check_marker "parent intact after B"    "COW: parent intact after second child"
check_marker "fixture PASS"             "cow_fork: PASS"

# Diagnostics: surface the next-gap signal for triage.
if grep -a -F -q "unknown syscall" "$LOG"; then
    echo "[test_u47_cow_fork] DIAG: kernel logged 'unknown syscall'"
    grep -a -F "unknown syscall" "$LOG" | sort -u || true
fi
if grep -a -F -q "TRAP: vector" "$LOG"; then
    echo "[test_u47_cow_fork] DIAG: kernel reported a CPU exception"
    grep -a -F "TRAP: vector" "$LOG" | head -5 || true
fi
if grep -a -F -q "cow_fork: FAIL" "$LOG"; then
    echo "[test_u47_cow_fork] DIAG: fixture self-reported FAIL"
    grep -a -F "cow_fork: FAIL" "$LOG" | head -5 || true
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_u47_cow_fork] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_u47_cow_fork] PASS -- fork() COW private-address-space isolation works"
