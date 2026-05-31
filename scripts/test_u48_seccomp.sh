#!/usr/bin/env bash
# scripts/test_u48_seccomp.sh -- #160 seccomp-lite per-task syscall filter.
#
# seccomp-lite is a real, working syscall-filtering capability for
# Linux-ABI userspace, enforced at the central Linux-ABI dispatch
# boundary (linux_abi/u_syscalls.ad seccomp_check_entry, called at
# syscall ENTRY from linux_u_syscall_dispatch). Two install paths feed
# one per-task state in kernel/sched/core.ad's TaskStruct: the dedicated
# seccomp(2) syscall (nr 317) and prctl(PR_SET_SECCOMP, mode, ...).
#
# This fixture drives strict mode end-to-end via prctl:
#
#   write() pre-arm -> install SIGSYS handler -> prctl(PR_SET_SECCOMP,
#   SECCOMP_MODE_STRICT) -> an ALLOWED write() still works -> a DENIED
#   getpid() posts SIGSYS, the handler runs (printing the denial marker),
#   control resumes, _exit(0) clean.
#
# PASS criteria: all of these markers land on serial:
#   - "SECCOMP: pre-arm write ok"
#   - "SECCOMP: strict armed"
#   - "SECCOMP: allowed write after arm"
#   - "SECCOMP: SIGSYS on blocked syscall"
#   - "seccomp_lite: PASS"
#
# Build-on-missing: the fixture is gitignored (host-built). If absent,
# build it from tests/u-binary/src/seccomp_lite; only SKIP on a real
# build failure (a genuine missing musl-gcc).
#
# REQUIRES: musl-gcc on $PATH. Build step:
#     make -C tests/u-binary/src/seccomp_lite install
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

UBIN=tests/u-binary/u_seccomp_lite
ensure_ubin_or_skip test_u48_seccomp u_seccomp_lite seccomp_lite

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf

echo "[test_u48_seccomp] (1/4) Build userland (hamsh + helpers)"
bash scripts/build_user.sh
bash scripts/build_modules.sh

echo "[test_u48_seccomp] (2/4) Swap /init = $HAMSH_ELF + embed u_seccomp_lite"
HAMNIX_EMBED_UBIN=1 INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py

echo "[test_u48_seccomp] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF"

echo "[test_u48_seccomp] (4/4) Boot QEMU + run /bin/u_seccomp_lite via hamsh"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# Prompt-aware drive: wait for hamsh's ready banner before sending input
# (a fixed sleep races boot-time variance -- see _qemu_drive.sh).
set +e
qemu_drive "$LOG" "$ELF" "[hamsh] M16.35 shell ready" 45 \
    -- "u_seccomp_lite" 8 \
       "exit" 1
rc="$QEMU_DRIVE_RC"
set -e

echo "[test_u48_seccomp] --- captured output ---"
cat "$LOG"
echo "[test_u48_seccomp] --- end output ---"

fail=0

check_marker() {
    local label="$1"
    local needle="$2"
    # -a: the serial log carries binary bytes; treat it as text.
    if grep -a -F -q "$needle" "$LOG"; then
        echo "[test_u48_seccomp] OK: $label  ('$needle')"
    else
        echo "[test_u48_seccomp] MISS: $label  ('$needle')"
        fail=1
    fi
}

check_marker "pre-arm write"        "SECCOMP: pre-arm write ok"
check_marker "strict armed"         "SECCOMP: strict armed"
check_marker "allowed after arm"    "SECCOMP: allowed write after arm"
check_marker "SIGSYS on denied"     "SECCOMP: SIGSYS on blocked syscall"
check_marker "fixture PASS"         "seccomp_lite: PASS"

# Diagnostics: surface the next-gap signal for triage.
if grep -a -F -q "seccomp:" "$LOG"; then
    echo "[test_u48_seccomp] DIAG: kernel seccomp denial trace:"
    grep -a -F "seccomp:" "$LOG" | head -5 || true
fi
if grep -a -F -q "TRAP: vector" "$LOG"; then
    echo "[test_u48_seccomp] DIAG: kernel reported a CPU exception"
    grep -a -F "TRAP: vector" "$LOG" | head -5 || true
fi
if grep -a -F -q "seccomp_lite: FAIL" "$LOG"; then
    echo "[test_u48_seccomp] DIAG: fixture self-reported FAIL"
    grep -a -F "seccomp_lite: FAIL" "$LOG" | head -5 || true
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_u48_seccomp] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_u48_seccomp] PASS -- seccomp-lite strict mode: allow read/write," \
     "deny others with SIGSYS"
