#!/usr/bin/env bash
# scripts/test_man.sh - verify the `man` and `help` discovery system.
#
# Two phases:
#
#   Phase A (offline, fast):
#     1. Compile user/man.ad and user/help.ad to ELFs.
#     2. Build the cpio initramfs and assert every /usr/share/man/*.md
#        page is embedded.
#     3. Assert essential pages exist by name (man, hamsh, hpm, help).
#
#   Phase B (QEMU smoke, ~30s):
#     4. Drive hamsh through:
#          man man          (expect NAME + SYNOPSIS)
#          man hamsh        (expect "shell" somewhere)
#          help             (expect index lists man, hamsh, hpm)
#          help svc         (expect svc page printed)
#          man no-such-topic (expect "no entry")
#          exit
#
# Set HAMNIX_TEST_MAN_OFFLINE=1 to skip Phase B (useful in CI environments
# without QEMU). Phase A alone catches the regression-prone parts:
# build manifest drift, missing pages, compile failures.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf
MAN_ELF=build/user/man.elf
HELP_ELF=build/user/help.elf

# --- Phase A: offline checks ----------------------------------------

echo "[test_man] (A1) Compile user/man.ad + user/help.ad"
bash scripts/build_user.sh > /tmp/test_man.build_user.log 2>&1 || {
    echo "[test_man] FAIL: build_user.sh failed. Tail of log:"
    tail -30 /tmp/test_man.build_user.log
    exit 1
}
for elf in "$MAN_ELF" "$HELP_ELF"; do
    if [ ! -s "$elf" ]; then
        echo "[test_man] FAIL: $elf missing or empty after build."
        exit 1
    fi
done
echo "[test_man] OK: man.elf + help.elf produced."

echo "[test_man] (A2) Build initramfs and grep for /usr/share/man/ entries"
python3 scripts/build_initramfs.py > /tmp/test_man.initramfs.log 2>&1
EMBED_LOG=/tmp/test_man.initramfs.log
# Count pages staged at /usr/share/man/.
PAGES_STAGED=$(grep -c "embedded /usr/share/man/" "$EMBED_LOG" || true)
if [ "$PAGES_STAGED" -lt 15 ]; then
    echo "[test_man] FAIL: only $PAGES_STAGED pages staged at /usr/share/man/ (expected >=15)."
    grep "embedded /usr/share/man/" "$EMBED_LOG" || true
    exit 1
fi
echo "[test_man] OK: $PAGES_STAGED man pages staged into the cpio."

echo "[test_man] (A3) Spot-check essential pages exist in etc/man/"
fail=0
for page in man.1.md help.1.md hamsh.1.md hpm.1.md svc.1.md ls.1.md; do
    if [ ! -s "etc/man/$page" ]; then
        echo "[test_man] MISS: etc/man/$page does not exist"
        fail=1
    fi
done
if [ "$fail" -ne 0 ]; then
    echo "[test_man] FAIL: missing essential pages."
    exit 1
fi
echo "[test_man] OK: essential pages present in etc/man/."

echo "[test_man] (A4) gen_install_manifest emits man-page rows"
python3 scripts/gen_install_manifest.py > /tmp/test_man.gen_manifest.log 2>&1
MANIFEST=etc/install/rootfs.manifest
MAN_ROWS=$(grep -c "^usr/share/man/" "$MANIFEST" || true)
if [ "$MAN_ROWS" -lt 15 ]; then
    echo "[test_man] FAIL: only $MAN_ROWS man rows in rootfs.manifest (expected >=15)."
    grep "usr/share/man" "$MANIFEST" || true
    exit 1
fi
echo "[test_man] OK: $MAN_ROWS man-page entries in rootfs.manifest."

# --- Phase B: QEMU smoke (optional) ---------------------------------

if [ "${HAMNIX_TEST_MAN_OFFLINE:-0}" = "1" ]; then
    echo "[test_man] PASS (offline only — HAMNIX_TEST_MAN_OFFLINE=1)."
    exit 0
fi

echo "[test_man] (B1) Swap /init = $HAMSH_ELF"
INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py > /dev/null

echo "[test_man] (B2) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" 2>&1 | tail -3

echo "[test_man] (B3) Boot QEMU and drive man + help"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
(
    sleep 4
    printf 'man man\n'
    sleep 1
    printf 'man hamsh\n'
    sleep 1
    printf 'help\n'
    sleep 1
    printf 'help svc\n'
    sleep 1
    printf 'man no-such-topic\n'
    sleep 1
    printf 'exit\n'
    sleep 1
) | timeout 30s qemu-system-x86_64 \
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

echo "[test_man] --- captured output ---"
cat "$LOG"
echo "[test_man] --- end output ---"

fail=0

# `man man` must produce NAME and SYNOPSIS.
if ! grep -F -q "NAME" "$LOG"; then
    echo "[test_man] MISS: 'NAME' (man-page header) not seen"
    fail=1
fi
if ! grep -F -q "SYNOPSIS" "$LOG"; then
    echo "[test_man] MISS: 'SYNOPSIS' (man-page header) not seen"
    fail=1
fi

# `man hamsh` must mention "shell".
if ! grep -F -iq "shell" "$LOG"; then
    echo "[test_man] MISS: 'shell' (from man hamsh) not seen"
    fail=1
fi

# `help` index must list at least man, hamsh, hpm.
for needle in "hamsh" "hpm" "svc"; do
    if ! grep -F -q "$needle" "$LOG"; then
        echo "[test_man] MISS: '$needle' (help index) not seen"
        fail=1
    fi
done

# `man no-such-topic` must emit the canonical error.
if ! grep -F -q "no entry" "$LOG"; then
    echo "[test_man] MISS: 'no entry' (missing-topic error) not seen"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_man] FAIL (qemu rc=$rc)"
    exit 1
fi
echo "[test_man] PASS"
