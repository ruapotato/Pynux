#!/usr/bin/env bash
# scripts/test_u11_dynsym.sh — U11 milestone: ELF64 .dynsym walker + vDSO.
#
# Boots Hamnix with /bin/u_dynsym embedded in the initramfs and drives
# hamsh to exec it. u_dynsym is a host-built, ET_DYN (-shared), OSABI=
# Linux x86_64 ELF whose .data carries an R_X86_64_64 reloc against an
# undefined-weak __vdso_clock_gettime symbol. Pre-U11 the kernel saw
# the symbol-resolving reloc, had no .dynsym walker, and logged
# "dyn-reloc sym-resolved type 1 skipped" — the .data slot stayed at
# the linker-emitted zero and the binary took the failure branch.
#
# Post-U11:
#   1. fs/elf.ad::_process_dynamic captures DT_SYMTAB / DT_STRTAB.
#   2. fs/elf.ad::_apply_dyn_relocs invokes _lookup_dynsym for type 1,
#      which strcmps the name against a hard-coded table of vDSO entry
#      points (linux_abi/vdso.ad).
#   3. The .data slot gets the runtime address of vdso_clock_gettime;
#      the binary's `testq %rsi, %rsi` falls through, and "U11:
#      dynsym ok" lands on serial.
#
# Skip-on-missing: if tests/u-binary/u_dynsym hasn't been built on the
# host (`make -C tests/u-binary/src/dynsym install`), exit 0 with a
# notice so CI in environments without `as`/`ld` still passes.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

UBIN=tests/u-binary/u_dynsym
if [ ! -f "$UBIN" ]; then
    echo "[test_u11_dynsym] SKIP: $UBIN not staged"
    echo "    Build with: make -C tests/u-binary/src/dynsym install"
    exit 0
fi

ELF=build/hamnix-vmlinux.elf
HAMSH_ELF=build/user/hamsh.elf

echo "[test_u11_dynsym] (1/4) Build userland (hamsh + helpers)"
bash scripts/build_user.sh
bash scripts/build_modules.sh

echo "[test_u11_dynsym] (2/4) Swap /init = $HAMSH_ELF + embed u_dynsym"
INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py

echo "[test_u11_dynsym] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF"

echo "[test_u11_dynsym] (4/4) Boot QEMU + run /bin/u_dynsym via hamsh"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
(
    sleep 3
    printf 'u_dynsym\n'
    sleep 2
    printf 'exit\n'
    sleep 1
) | timeout 20s qemu-system-x86_64 \
    -kernel "$ELF" \
    -smp 2 \
    -nographic \
    -no-reboot \
    -m 256M \
    -monitor none \
    -serial stdio \
    > "$LOG" 2>&1
rc=$?
set -e

echo "[test_u11_dynsym] --- captured output ---"
cat "$LOG"
echo "[test_u11_dynsym] --- end output ---"

fail=0

check_marker() {
    local label="$1"
    local needle="$2"
    if grep -F -q "$needle" "$LOG"; then
        echo "[test_u11_dynsym] OK: $label  ('$needle')"
    else
        echo "[test_u11_dynsym] MISS: $label  ('$needle')"
        fail=1
    fi
}

# Primary success criterion: the binary saw a non-zero vdso pointer
# after the loader's dynsym walk and wrote its marker line. Failure
# branch ("U11: dynsym FAIL") would be visible too if the slot wasn't
# patched, but the test treats both states equivalently — only "ok"
# means success.
check_marker "dynsym resolution succeeded" "U11: dynsym ok"
# Secondary: the loader announced applying relocations. The dynsym
# binary has exactly 1 R_X86_64_64 entry, so we expect
# "elf64: applied 1 relocations" in the loader summary. If a future
# test grows more relocs the count rises; the marker check is the
# substring, so >=1 is fine.
check_marker "loader logged reloc applied" "elf64: applied 1 relocations"
# U1/U2 path: OSABI=Linux byte got noticed (same printk as u_pie).
check_marker "U1/U2 ELF detect" "Linux-ABI binary detected"

# Sanity: hamsh kept running after the child exited.
if grep -F -q "[hamsh] bye." "$LOG"; then
    echo "[test_u11_dynsym] OK: hamsh reaped u_dynsym and exited cleanly"
else
    echo "[test_u11_dynsym] MISS: hamsh did not reach bye line"
    fail=1
fi

# Negative diagnostic: pre-U11 the loader logged this message for every
# unresolved sym-bound reloc. If we see it post-U11 on the __vdso_*
# names, the dynsym walker isn't matching the name table — useful
# differential signal.
if grep -F -q "dyn-reloc sym-resolved type 1 skipped" "$LOG"; then
    echo "[test_u11_dynsym] DIAG: legacy skip-message present —" \
         "_lookup_dynsym did not match the name; check vdso name table"
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_u11_dynsym] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_u11_dynsym] PASS — dynamic symbol resolution + vDSO shim wired"
