#!/usr/bin/env bash
# scripts/test_mac80211_ko.sh — regression guard for the mac80211.ko
# load path through the L-series loader.
#
# mac80211.ko is the soft-MAC 802.11 stack that sits between cfg80211
# (admin) below and per-chip wifi drivers (ath*, iwl*) above. Like
# cfg80211, it has no PCI alias of its own. init/main.ad's
# framework-modules block (gated by /etc/framework-modules) loads
# BOTH cfg80211.ko and mac80211.ko (cfg80211 first because the
# api_cfg80211 / api_mac80211 shim split mirrors the kernel-side
# layering — mac80211 depends on cfg80211).
#
# V0 assertions (module load + relocations resolve):
#   1. /lib/modules/mac80211.ko is in the cpio archive.
#   2. The framework-modules block reaches the mac80211 load step.
#   3. "[mac80211.ko] kmod_linux_load OK" appears in dmesg.
#   4. No `kmod_linux: relocations applied=X skipped=N>0` line —
#      the api_mac80211.ad shim closure (155 new exports) plus the
#      cfg80211 batch (50 new exports) must be complete; anything
#      else is a missing-shim hard fail.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
BOOT_TIMEOUT="${MAC80211_BOOT_TIMEOUT:-25}"

echo "[test_mac80211_ko] (1/4) Build userland + modules + initramfs"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null
INITRAMFS_LOG=$(mktemp)
ENABLE_FRAMEWORK_MODULES=1 python3 scripts/build_initramfs.py \
    > "$INITRAMFS_LOG" 2>&1
trap 'rm -f "$INITRAMFS_LOG" "${LOG:-/dev/null}"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

echo "[test_mac80211_ko] (2/4) Verify initramfs contents"
fail=0
for needle in \
    "embedded /lib/modules/cfg80211.ko" \
    "embedded /lib/modules/mac80211.ko"
do
    if grep -F -q "$needle" "$INITRAMFS_LOG"; then
        echo "[test_mac80211_ko] OK (cpio): '$needle'"
    else
        echo "[test_mac80211_ko] MISS (cpio): '$needle'"
        fail=1
    fi
done
if [ "$fail" -ne 0 ]; then
    echo "[test_mac80211_ko] --- build_initramfs.py stdout ---"
    cat "$INITRAMFS_LOG"
    exit 1
fi

# Tier-1: .ko file presence
KO_PATH="$PROJ_ROOT/kernel-modules/mac80211/mac80211.ko"
KO_SIZE=$(stat -c%s "$KO_PATH" 2>/dev/null || echo 0)
if [ "$KO_SIZE" -gt 100000 ]; then
    echo "[test_mac80211_ko] OK: mac80211.ko present (${KO_SIZE} bytes)"
else
    echo "[test_mac80211_ko] FAIL: mac80211.ko missing or too small (${KO_SIZE} bytes)"
    exit 1
fi

echo "[test_mac80211_ko] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

if [ -f "$ELF" ] && [ -s "$ELF" ]; then
    echo "[test_mac80211_ko] OK: kernel ELF built ($(stat -c%s "$ELF") bytes)"
else
    echo "[test_mac80211_ko] FAIL: kernel ELF missing"
    exit 1
fi

echo "[test_mac80211_ko] (4/4) Boot QEMU and watch for mac80211.ko load"
LOG=$(mktemp)

set +e
timeout "${BOOT_TIMEOUT}s" qemu-system-x86_64 \
    -kernel "$ELF" \
    -nographic -no-reboot -m 256M -monitor none -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

echo "[test_mac80211_ko] --- captured (boot:35 / mac80211 / cfg80211 / kmod_linux) ---"
grep -aE '\[boot:35|\[cfg80211\.ko\]|\[mac80211\.ko\]|kmod_linux: vermagic|kmod_linux: relocations|kmod_linux: init_module|kmod_linux: init returned' "$LOG" || true
echo "[test_mac80211_ko] --- end ---"

# Boot sanity
if grep -aE -q '\[boot:35\]|linux_abi_exports_init|hamnix' "$LOG"; then
    echo "[test_mac80211_ko] OK: kernel reached linux_abi_exports_init"
else
    echo "[test_mac80211_ko] FAIL: kernel did not reach linux_abi_exports_init"
    fail=1
fi

if grep -aF -q "[boot:35.F] framework modules" "$LOG"; then
    echo "[test_mac80211_ko] OK: framework-modules marker honored"
else
    echo "[test_mac80211_ko] MISS: framework-modules block did not engage"
    fail=1
fi

# mac80211 depends on cfg80211 being loaded successfully first.
if grep -aF -q "[cfg80211.ko] kmod_linux_load OK" "$LOG"; then
    echo "[test_mac80211_ko] OK: cfg80211.ko loaded (mac80211 prerequisite)"
else
    echo "[test_mac80211_ko] FAIL: cfg80211.ko did not load — mac80211 will fail"
    fail=1
fi

if grep -aF -q "[mac80211.ko] loading" "$LOG"; then
    echo "[test_mac80211_ko] OK: mac80211.ko found in cpio + loading"
else
    echo "[test_mac80211_ko] FAIL: mac80211.ko not loaded"
    fail=1
fi

if grep -aF -q "[mac80211.ko] kmod_linux_load OK" "$LOG"; then
    echo "[test_mac80211_ko] OK: kmod_linux_load returned success"
else
    echo "[test_mac80211_ko] FAIL: kmod_linux_load did not return OK"
    fail=1
fi

# Tier-3 strict: zero skipped relocations
if grep -aE -q "kmod_linux: relocations applied=[0-9]+ skipped=[1-9]" "$LOG"; then
    echo "[test_mac80211_ko] FAIL: at least one module had skipped relocations"
    grep -aE "kmod_linux: relocations applied=" "$LOG"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_mac80211_ko] FAIL (qemu rc=$rc)"
    echo "[test_mac80211_ko] --- full log tail ---"
    tail -150 "$LOG"
    exit 1
fi

echo "[test_mac80211_ko] PASS (cfg80211.ko + mac80211.ko load via framework-modules path)"
