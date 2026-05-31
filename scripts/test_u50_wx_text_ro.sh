#!/usr/bin/env bash
# scripts/test_u50_wx_text_ro.sh -- W^X Stage 1b: CODE pages read-only.
#
# W^X Stage 1a (test_u49_wxorx) marks user DATA pages No-Execute. Stage
# 1b is the COMPLEMENT: user CODE pages (.text / .rodata of the loaded
# ELF image AND its interpreter) are mapped READ-ONLY + executable. The
# loader maps the whole image RW+X (so userspace ld.so / glibc can patch
# its GOT/.data during relocation), then -- in fs/elf.ad::
# elf_apply_last_user_mapping, after the image install and before the
# first user instruction -- flips every NON-WRITABLE PT_LOAD segment
# READ-ONLY (clears PT_FLAG_RW, leaves it executable). A userland WRITE
# into its own .text then raises a #PF protection fault, which
# arch/x86/kernel/trap_diag.ad::do_page_fault converts into SIGSEGV(11)
# delivered to the faulting task (the COW handler ruled the fault out as
# non-COW first, so it is a genuine W^X violation, not a COW copy).
#
# This fixture drives the .text-write path end-to-end:
#
#   write() baseline -> install a SIGSEGV handler -> READ a byte of a
#   function's machine code (succeeds; .text is R+X) -> WRITE a byte
#   back to that .text address -> the store faults (.text is RO) ->
#   kernel delivers SIGSEGV -> the handler prints the trap marker + PASS
#   and _exit(0)s.
#
# PASS criteria: all of these markers land on serial:
#   - "WXTEXT: pre-write ok"           (a normal program runs -- no
#                                        false fault from the RO flip)
#   - "WXTEXT: handler armed"
#   - "WXTEXT: text read ok"           (a READ from .text still works)
#   - "WXTEXT: RO trapped write-to-text"
#   - "wx_text_ro: PASS"
# And the boot log shows the kernel TRAPPED the write into RO .text:
#   - "[pf] W^X write-fault on RO user page"
#
# Build-on-missing: the fixture is gitignored (host-built). If absent,
# build it from tests/u-binary/src/wx_text_ro; only SKIP on a real build
# failure (a genuine missing musl-gcc).
#
# REQUIRES: musl-gcc on $PATH. Build step:
#     make -C tests/u-binary/src/wx_text_ro install
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

UBIN=tests/u-binary/u_wx_text_ro
ensure_ubin_or_skip test_u50_wx_text_ro u_wx_text_ro wx_text_ro

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf

echo "[test_u50_wx_text_ro] (1/4) Build userland (hamsh + helpers)"
bash scripts/build_user.sh
bash scripts/build_modules.sh

echo "[test_u50_wx_text_ro] (2/4) Swap /init = $HAMSH_ELF + embed u_wx_text_ro"
HAMNIX_EMBED_UBIN=1 INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py

echo "[test_u50_wx_text_ro] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF"

echo "[test_u50_wx_text_ro] (4/4) Boot QEMU + run /bin/u_wx_text_ro via hamsh"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# Prompt-aware drive: wait for hamsh's ready banner before sending input.
set +e
qemu_drive "$LOG" "$ELF" "[hamsh] M16.35 shell ready" 45 \
    -- "u_wx_text_ro" 8 \
       "exit" 1
rc="$QEMU_DRIVE_RC"
set -e

echo "[test_u50_wx_text_ro] --- captured output ---"
cat "$LOG"
echo "[test_u50_wx_text_ro] --- end output ---"

fail=0

check_marker() {
    local label="$1"
    local needle="$2"
    if grep -a -F -q "$needle" "$LOG"; then
        echo "[test_u50_wx_text_ro] OK: $label  ('$needle')"
    else
        echo "[test_u50_wx_text_ro] MISS: $label  ('$needle')"
        fail=1
    fi
}

check_marker "kernel trapped write"   "[pf] W^X write-fault on RO user page"
check_marker "pre-write baseline"     "WXTEXT: pre-write ok"
check_marker "handler armed"          "WXTEXT: handler armed"
check_marker "text read ok"           "WXTEXT: text read ok"
check_marker "RO trapped write"       "WXTEXT: RO trapped write-to-text"
check_marker "fixture PASS"           "wx_text_ro: PASS"

# Diagnostics: surface the next-gap signal for triage. A HALTING
# trap-diag block (vec/err/rip) means the W^X write-fault was NOT routed
# to SIGSEGV and instead halted the kernel -- that's the regression to
# watch. The benign install-time "[trap-diag] install:" lines are
# filtered out so they don't masquerade as a fault.
if grep -a -F "trap-diag" "$LOG" | grep -a -v -F "install:" | grep -a -q "vec="; then
    echo "[test_u50_wx_text_ro] DIAG: kernel reported a halting CPU exception"
    grep -a -F "trap-diag" "$LOG" | head -8 || true
fi
if grep -a -F -q "wx_text_ro: FAIL" "$LOG"; then
    echo "[test_u50_wx_text_ro] DIAG: fixture self-reported FAIL"
    grep -a -F "wx_text_ro: FAIL" "$LOG" | head -5 || true
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_u50_wx_text_ro] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_u50_wx_text_ro] PASS -- W^X Stage 1b: .text read-only;" \
     "write-to-text traps to SIGSEGV"
