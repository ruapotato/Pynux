#!/usr/bin/env bash
# scripts/test_autostubs.sh — regression guard for the autostub safety
# net (scripts/gen_autostubs.py + linux_abi/api_autostubs.ad +
# linux_abi_register_autostubs() in linux_abi/exports.ad).
#
# Boots a kernel with an existing .ko loaded (snd_hda_intel.ko via the
# auto-modules path — it has the most static-call trampolines, so it's
# the densest target for the catalog) and asserts:
#
#   1. scripts/gen_autostubs.py runs from build_initramfs.py (the
#      "[gen_autostubs] scanned ... .ko files" line shows up in the
#      build log).
#   2. The kernel ELF builds (proves linux_abi/api_autostubs.ad is
#      well-formed Adder).
#   3. linux_abi_register_autostubs() runs at boot — the
#      "linux_abi_register_autostubs registered N symbols" printk
#      appears.
#   4. Module loading still works: at least one [modprobe]
#      kmod_linux_load OK line, with skipped=0 on every relocation
#      pass, and no "unresolved external symbol" / "TRAP:" / "BUG:".
#
# N is allowed to be 0 today (the hand-written api_*.ad files already
# cover every trivial pattern across the bundled .ko set). The line's
# PRESENCE is what proves the autostub register ran; the loader's
# `skipped=0` is what proves the resulting symbol table is good.
#
# When a new .ko is added with un-shimmed trivial-pattern UNDs (e.g.
# new __SCK__tp_func_foo / __tracepoint_bar / __x86_indirect_thunk_r{N}),
# this test catches the regression FIRST — if the catalog wins the gap,
# N > 0 and the kmod_linux relocation pass reports skipped=0. If the
# catalog misses, this test still passes (N=0) but
# test_<that_module>_ko.sh catches the unresolved external.
#
# Env overrides:
#   AUTOSTUB_BOOT_TIMEOUT  seconds qemu may run     (default: 45)

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
AUTOSTUB_BOOT_TIMEOUT="${AUTOSTUB_BOOT_TIMEOUT:-45}"

fail=0

echo "[test_autostubs] (1/5) Sanity: gen_autostubs.py exists and is executable"
if [ ! -f scripts/gen_autostubs.py ]; then
    echo "[test_autostubs] FAIL: scripts/gen_autostubs.py missing"
    exit 1
fi

echo "[test_autostubs] (2/5) Build userland + modules"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

echo "[test_autostubs] (3/5) Bake initramfs with ENABLE_AUTO_MODULES=1"
INITRAMFS_LOG=$(mktemp)
ENABLE_AUTO_MODULES=1 python3 scripts/build_initramfs.py \
    > "$INITRAMFS_LOG" 2>&1
trap 'rm -f "$INITRAMFS_LOG" "${LOG:-}"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# Assert (1): gen_autostubs ran as part of the build.
if grep -F -q "[gen_autostubs] scanned" "$INITRAMFS_LOG"; then
    echo "[test_autostubs] OK: gen_autostubs.py ran from build_initramfs.py"
    grep -F "[gen_autostubs]" "$INITRAMFS_LOG" | head -10 | sed 's/^/  /'
else
    echo "[test_autostubs] FAIL: gen_autostubs.py did not run during build"
    echo "[test_autostubs] --- build_initramfs.py output ---"
    cat "$INITRAMFS_LOG"
    fail=1
fi

# Assert: linux_abi/api_autostubs.ad exists (the generator's output).
if [ ! -f linux_abi/api_autostubs.ad ]; then
    echo "[test_autostubs] FAIL: linux_abi/api_autostubs.ad missing"
    fail=1
fi

if [ "$fail" -ne 0 ]; then exit 1; fi

echo "[test_autostubs] (4/5) Rebuild kernel ELF (with api_autostubs.ad)"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null
if [ ! -f "$ELF" ] || [ ! -s "$ELF" ]; then
    echo "[test_autostubs] FAIL: kernel ELF missing after build"
    exit 1
fi
echo "[test_autostubs] OK: kernel ELF built ($(stat -c%s "$ELF") bytes)"

echo "[test_autostubs] (5/5) Boot QEMU with intel-hda + e1000e (auto-modules)"
LOG=$(mktemp)
trap 'rm -f "$INITRAMFS_LOG" "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
timeout "${AUTOSTUB_BOOT_TIMEOUT}s" qemu-system-x86_64 \
    -kernel "$ELF" \
    -netdev user,id=n0 \
    -device e1000e,netdev=n0,mac=52:54:00:12:34:56 \
    -device intel-hda \
    -device hda-output \
    -nographic -no-reboot -m 256M -monitor none -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

cp "$LOG" /tmp/test_autostubs.last.log || true

echo "[test_autostubs] --- captured (autostubs / kmod_linux / boot:35) ---"
grep -aE 'linux_abi_register_autostubs|linux_abi: WARN|\[modprobe\]|kmod_linux:|\[boot:35' \
    "$LOG" | head -60 || true
echo "[test_autostubs] --- end ---"

# Assert (3): linux_abi_register_autostubs printk line.
if grep -aE -q 'linux_abi_register_autostubs registered [0-9]+ symbols' "$LOG"; then
    n_auto=$(grep -aoE 'linux_abi_register_autostubs registered [0-9]+ symbols' "$LOG" \
        | head -1 | awk '{print $3}')
    echo "[test_autostubs] OK: autostub register printk fired (N=${n_auto:-?})"
    if [ -n "${n_auto:-}" ] && [ "$n_auto" -gt 0 ]; then
        echo "[test_autostubs] INFO: autostub catalog caught $n_auto symbols not hand-shimmed"
    else
        echo "[test_autostubs] INFO: autostub catalog had 0 hits (every trivial pattern already hand-shimmed)"
    fi
else
    echo "[test_autostubs] FAIL: 'linux_abi_register_autostubs registered N symbols' line missing"
    fail=1
fi

# Assert: MAX_EXPORTS overflow warn did NOT fire.
if grep -aF -q 'linux_abi: WARN: NR_EXPORTS == MAX_EXPORTS' "$LOG"; then
    echo "[test_autostubs] FAIL: MAX_EXPORTS overflow warn fired — bump MAX_EXPORTS"
    fail=1
fi

# Assert (4a): at least one kmod_linux_load OK report.
n_load_ok=$(grep -caE '\[modprobe\] kmod_linux_load OK' "$LOG" || true)
if [ "${n_load_ok:-0}" -ge 1 ]; then
    echo "[test_autostubs] OK: $n_load_ok kmod_linux_load OK reports"
else
    echo "[test_autostubs] FAIL: no kmod_linux_load OK lines"
    fail=1
fi

# Assert (4b): no skipped relocations.
n_bad_skipped=$( { grep -aE "kmod_linux: relocations applied=" "$LOG" || true; } \
                | { grep -vE 'skipped=0' || true; } | wc -l)
if [ "$n_bad_skipped" -eq 0 ]; then
    n_reloc=$(grep -caE "kmod_linux: relocations applied=[0-9]+ skipped=0" "$LOG" || true)
    echo "[test_autostubs] OK: all $n_reloc relocation passes resolved (skipped=0)"
else
    echo "[test_autostubs] FAIL: $n_bad_skipped relocation passes had skipped>0"
    grep -aE "kmod_linux: relocations applied=" "$LOG" | grep -vE 'skipped=0' | head
    grep -aE "kmod_linux: unresolved external" "$LOG" | head -30
    fail=1
fi

# Assert (4c): no unresolved external / TRAP / BUG / init returned -N.
for needle in 'unresolved external symbol' 'TRAP:' 'BUG:' 'init returned -'; do
    if grep -aE -q "$needle" "$LOG"; then
        echo "[test_autostubs] FAIL: '$needle' present in boot log"
        grep -aE "$needle" "$LOG" | head -10
        fail=1
    fi
done

if [ "$fail" -ne 0 ]; then
    echo "[test_autostubs] FAIL (qemu rc=$rc)"
    echo "[test_autostubs] --- full log tail ---"
    tail -160 "$LOG"
    exit 1
fi

echo "[test_autostubs] PASS"
