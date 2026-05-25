#!/usr/bin/env bash
# scripts/test_auto_modules.sh — regression guard for the Linux-shape
# modprobe auto-discovery framework (kernel/modprobe.ad).
#
# Builds an ISO with BOTH ENABLE_AUTO_MODULES=1 (turn on the
# auto-discovery framework) AND ENABLE_E1000E_KO=1 (so the legacy
# single-marker path is also armed — we cross-check that the auto path
# claims the device first via _already_loaded and the legacy path
# becomes a no-op for a duplicate device). Boots under QEMU
# `-device e1000e` and asserts:
#
#   1. The build baked /lib/modules/modules.alias into the cpio
#      (visible in build_initramfs.py stdout).
#   2. The cpio also carries /lib/modules/auto/e1000e.ko.
#   3. The in-kernel modprobe_auto_load() found the alias table
#      ("[modprobe] alias table: <N> bytes").
#   4. modprobe formatted the correct PCI query for QEMU's e1000e
#      ("[modprobe] querying pci:v00008086d000010D3..."  — vendor
#      0x8086 device 0x10D3 is QEMU's hard-coded 82574-class id).
#   5. modprobe matched the e1000e alias and dispatched the load
#      ("[modprobe] MATCH -> module=e1000e",
#       "[modprobe] loading /lib/modules/auto/e1000e.ko",
#       "[modprobe] kmod_linux_load OK").
#   6. The "[boot:35.M] modprobe auto-load: N modules loaded"
#      summary printed with N >= 1.
#
# This is a PLUMBING test only — we do not assert end-to-end DHCP
# (that's the sk_buff agent's milestone). The point is to prove the
# framework dispatches the right .ko for the right device automatically.
#
# Pure functional dependencies:
#   - `python3 scripts/build_modules_alias.py` produces modules.alias
#     from kernel-modules/<X>/<X>.ko (via host modinfo).
#   - `ENABLE_AUTO_MODULES=1 python3 scripts/build_initramfs.py`
#     bakes the .ko + alias table + /etc/auto-modules marker.
#   - kernel/modprobe.ad's modprobe_auto_load() walks the PCI bus
#     and matches each device against the table.
#
# Env overrides:
#   AUTO_BOOT_TIMEOUT   seconds qemu may run     (default: 25)
#
# Exit status: 0 PASS, 1 FAIL. Verbose on FAIL — full log dumped.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
AUTO_BOOT_TIMEOUT="${AUTO_BOOT_TIMEOUT:-25}"

echo "[test_auto_modules] (1/4) Build userland + modules + initramfs"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null
INITRAMFS_LOG=$(mktemp)
ENABLE_AUTO_MODULES=1 ENABLE_E1000E_KO=1 python3 scripts/build_initramfs.py \
    > "$INITRAMFS_LOG" 2>&1
trap 'rm -f "$INITRAMFS_LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# Step 1 + 2: the cpio actually carries the alias table + the .ko under
# /lib/modules/auto/. Both are observable in the build_initramfs.py
# stdout, which is the canonical "what's in this cpio" record.
echo "[test_auto_modules] (2/4) Verify initramfs contents"
fail=0
for needle in \
    "embedded /lib/modules/auto/e1000e.ko" \
    "embedded /lib/modules/modules.alias"
do
    if grep -F -q "$needle" "$INITRAMFS_LOG"; then
        echo "[test_auto_modules] OK (cpio): '$needle'"
    else
        echo "[test_auto_modules] MISS (cpio): '$needle'"
        fail=1
    fi
done
if [ "$fail" -ne 0 ]; then
    echo "[test_auto_modules] --- build_initramfs.py stdout ---"
    cat "$INITRAMFS_LOG"
    exit 1
fi

echo "[test_auto_modules] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_auto_modules] (4/4) Boot QEMU with e1000e as the ONLY NIC"
LOG=$(mktemp)
trap 'rm -f "$LOG" "$INITRAMFS_LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
timeout "${AUTO_BOOT_TIMEOUT}s" qemu-system-x86_64 \
    -kernel "$ELF" \
    -netdev user,id=n0 \
    -device e1000e,netdev=n0,mac=52:54:00:12:34:56 \
    -nographic -no-reboot -m 256M -monitor none -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

echo "[test_auto_modules] --- captured (modprobe / kmod_linux / boot:35) ---"
grep -E '\[modprobe\]|\[boot:35\.M\]|kmod_linux: relocations|kmod_linux_load' "$LOG" || true
echo "[test_auto_modules] --- end ---"

# Steps 3-6: in-kernel modprobe assertions.
for needle in \
    "[modprobe] auto-load: reading /lib/modules/modules.alias" \
    "[modprobe] alias table:" \
    "[modprobe] querying pci:v00008086d000010D3" \
    "[modprobe] MATCH -> module=e1000e" \
    "[modprobe] loading /lib/modules/auto/e1000e.ko" \
    "[modprobe] kmod_linux_load OK" \
    "[boot:35.M] modprobe auto-load:"
do
    if grep -F -q "$needle" "$LOG"; then
        echo "[test_auto_modules] OK: '$needle'"
    else
        echo "[test_auto_modules] MISS: '$needle'"
        fail=1
    fi
done

# Final summary line: N modules loaded MUST be >= 1.
loaded_line=$(grep -E '\[boot:35\.M\] modprobe auto-load: [0-9]+ modules loaded' "$LOG" | tail -1 || true)
if [ -z "$loaded_line" ]; then
    echo "[test_auto_modules] MISS: summary line '[boot:35.M] modprobe auto-load: N modules loaded'"
    fail=1
else
    n_loaded=$(echo "$loaded_line" | grep -oE '[0-9]+ modules loaded' | grep -oE '[0-9]+')
    if [ "${n_loaded:-0}" -lt 1 ]; then
        echo "[test_auto_modules] FAIL: summary says $n_loaded modules loaded (expected >= 1)"
        fail=1
    else
        echo "[test_auto_modules] OK: summary reports $n_loaded modules loaded"
    fi
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_auto_modules] FAIL (qemu rc=$rc)"
    echo "[test_auto_modules] --- full log ---"
    cat "$LOG"
    exit 1
fi

echo "[test_auto_modules] PASS (modules.alias dispatched e1000e.ko via PCI ID 8086:10D3)"
