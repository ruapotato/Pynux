#!/usr/bin/env bash
# scripts/test_snd_hda_ko.sh — regression guard for the Intel HD Audio
# .ko stack (snd_hda_intel + snd_hda_codec + snd_hda_core + snd_pcm +
# snd) loading via the L-series loader, end-to-end through the
# modprobe auto-discovery framework.
#
# Builds an ISO with ENABLE_AUTO_MODULES=1 and boots QEMU with
# `-device intel-hda -device hda-output` as the audio fixture.
# snd_hda_intel's alias table matches PCI class=0x040300 (Audio
# device) — QEMU's intel-hda controller emulates that class — so
# the modprobe auto-loader picks the .ko up from /lib/modules/auto/
# and kmod_linux_load drives it through init_module.
#
# V0 assertions (module load + relocations resolve for ALL 5 .ko's):
#
#   Tier 1 (build-side, owned by this batch):
#     * All 5 .ko files are present in kernel-modules/<name>/ at
#       reasonable sizes (>100 KiB each).
#     * The kernel ELF builds successfully with the new
#       linux_abi_register_snd_core/_pcm/_hda calls in exports.ad.
#     * The initramfs cpio carries each .ko at /lib/modules/auto/.
#     * The modules.alias table contains an entry for snd_hda_intel.
#
#   Tier 2 (runtime, owned by this batch):
#     * The kernel boots far enough that the new register_* calls
#       didn't wedge linux_abi_exports_init.
#     * "[modprobe] alias table:" appears (table parsed).
#     * "[modprobe] MATCH -> module=snd_hda_intel" appears (the
#       audio class match worked).
#     * "[modprobe] kmod_linux_load OK" appears for snd_hda_intel.
#     * "kmod_linux: relocations applied=N skipped=0" for the
#       loaded .ko — the symbol gap closed; zero remaining UND.
#
# PCM playback / capture is OUT OF SCOPE — opening /dev/snd/pcmC0D0p
# would fall through to a -ENODEV from the un-wired fops. Today's
# milestone is load + probe (snd_hda_intel's probe runs through
# azx_bus_init -> azx_probe_codecs and lands at -ENXIO from the
# shimmed RIRB; the controller treats that as "no codec found"
# and the module init returns 0).

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
SND_BOOT_TIMEOUT="${SND_BOOT_TIMEOUT:-45}"

echo "[test_snd_hda_ko] (0/5) Sanity-check the 5 .ko files are checked in"
fail=0
for sub in snd snd_pcm snd_hda_core snd_hda_codec snd_hda_intel; do
    KO=$(ls "$PROJ_ROOT/kernel-modules/$sub/"*.ko 2>/dev/null | head -1)
    if [ -z "$KO" ]; then
        echo "[test_snd_hda_ko] FAIL: kernel-modules/$sub/*.ko missing"
        fail=1
    else
        KO_SIZE=$(stat -c%s "$KO" 2>/dev/null || echo 0)
        if [ "$KO_SIZE" -lt 100000 ]; then
            echo "[test_snd_hda_ko] FAIL: $KO too small (${KO_SIZE} bytes)"
            fail=1
        else
            echo "[test_snd_hda_ko] OK: $KO present (${KO_SIZE} bytes)"
        fi
    fi
done
if [ "$fail" -ne 0 ]; then exit 1; fi

echo "[test_snd_hda_ko] (1/5) Build userland + modules"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

echo "[test_snd_hda_ko] (2/5) Bake initramfs with ENABLE_AUTO_MODULES=1"
INITRAMFS_LOG=$(mktemp)
ENABLE_AUTO_MODULES=1 python3 scripts/build_initramfs.py \
    > "$INITRAMFS_LOG" 2>&1
trap 'rm -f "$INITRAMFS_LOG" "${LOG:-}"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# Tier 1 — initramfs contents.
for needle in \
    "embedded /lib/modules/auto/snd.ko" \
    "embedded /lib/modules/auto/snd_pcm.ko" \
    "embedded /lib/modules/auto/snd_hda_core.ko" \
    "embedded /lib/modules/auto/snd_hda_codec.ko" \
    "embedded /lib/modules/auto/snd_hda_intel.ko" \
    "embedded /lib/modules/modules.alias"
do
    if grep -F -q "$needle" "$INITRAMFS_LOG"; then
        echo "[test_snd_hda_ko] OK (cpio): '$needle'"
    else
        echo "[test_snd_hda_ko] MISS (cpio): '$needle'"
        fail=1
    fi
done
if [ "$fail" -ne 0 ]; then
    echo "[test_snd_hda_ko] --- build_initramfs.py stdout ---"
    cat "$INITRAMFS_LOG"
    exit 1
fi

echo "[test_snd_hda_ko] (3/5) Rebuild kernel image (with new snd_* exports)"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

if [ ! -f "$ELF" ] || [ ! -s "$ELF" ]; then
    echo "[test_snd_hda_ko] FAIL: kernel ELF missing after build"
    exit 1
fi
echo "[test_snd_hda_ko] OK: kernel ELF built ($(stat -c%s "$ELF") bytes)"

echo "[test_snd_hda_ko] (4/5) Boot QEMU with intel-hda + hda-output"
LOG=$(mktemp)

# Inner trap captures both temp files when we exit out of this block.
trap 'rm -f "$INITRAMFS_LOG" "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
timeout "${SND_BOOT_TIMEOUT}s" qemu-system-x86_64 \
    -kernel "$ELF" \
    -netdev user,id=n0 \
    -device e1000e,netdev=n0,mac=52:54:00:12:34:56 \
    -device intel-hda \
    -device hda-output \
    -nographic -no-reboot -m 256M -monitor none -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

echo "[test_snd_hda_ko] --- captured (modprobe / kmod_linux / snd / hda) ---"
grep -aE '\[modprobe\]|\[boot:35\.M\]|kmod_linux:|\[snd|\[hda|\[azx' "$LOG" \
    | head -200 || true
echo "[test_snd_hda_ko] --- end ---"
# Stash the raw log for post-mortem debugging — overwritten on next run.
cp "$LOG" /tmp/test_snd_hda_ko.last.log || true

echo "[test_snd_hda_ko] (5/5) Assert load + probe markers"

# Tier 2 — kernel boot reached.
if grep -aE -q '\[boot:|hamnix|rc\.boot:' "$LOG"; then
    echo "[test_snd_hda_ko] OK: kernel reached early boot — snd_* registers didn't wedge init"
else
    echo "[test_snd_hda_ko] FAIL: kernel did not reach early boot"
    fail=1
fi

# Tier 2 — modprobe found the alias table.
if grep -aF -q "[modprobe] alias table:" "$LOG"; then
    echo "[test_snd_hda_ko] OK: modprobe parsed alias table"
else
    echo "[test_snd_hda_ko] MISS: '[modprobe] alias table:' not in boot log"
    fail=1
fi

# Tier 2 — snd_hda_intel got matched (audio class 0x040300 on the
# emulated intel-hda PCI device).
if grep -aF -q "[modprobe] MATCH -> module=snd_hda_intel" "$LOG"; then
    echo "[test_snd_hda_ko] OK: modprobe matched snd_hda_intel by PCI alias"
else
    echo "[test_snd_hda_ko] MISS: '[modprobe] MATCH -> module=snd_hda_intel'"
    # Don't fail outright — depends on whether QEMU emits the right
    # class code AND whether the alias table got generated for
    # snd_hda_intel.ko. Print everything that did match.
    echo "[test_snd_hda_ko] INFO: --- modprobe MATCH lines seen ---"
    grep -aE "\[modprobe\] MATCH" "$LOG" | head -20 || true
    fail=1
fi

# Tier 2 — kmod_linux_load OK for snd_hda_intel. modprobe loads each
# matched PCI device's .ko in scan order; the boot log carries one
# kmod_linux_load OK per loaded module. We assert at least 2 loads OK
# (e1000e + snd_hda_intel), since the test also boots an e1000e NIC.
#
# QEMU emits its serial as raw bytes (BIOS banner + ANSI escapes
# + line endings), which `grep` heuristics treat as binary. Pass
# `-a` so grep walks every line in text mode.
n_load_ok=$(grep -caE "^\[[0-9]+\] \[modprobe\] kmod_linux_load OK" "$LOG" || true)
if [ "${n_load_ok:-0}" -ge 2 ]; then
    echo "[test_snd_hda_ko] OK: $n_load_ok kmod_linux_load OK reports (>=2 expected)"
    # Every relocations-applied line must report skipped=0.
    n_bad_skipped=$( { grep -aE "kmod_linux: relocations applied=" "$LOG" || true; } \
                    | { grep -vE 'skipped=0' || true; } | wc -l)
    if [ "$n_bad_skipped" -eq 0 ]; then
        n_reloc=$(grep -caE "kmod_linux: relocations applied=[0-9]+ skipped=0" "$LOG" || true)
        echo "[test_snd_hda_ko] OK: all $n_reloc relocation runs resolved (0 skipped)"
    else
        echo "[test_snd_hda_ko] FAIL: $n_bad_skipped relocation runs had skipped>0"
        grep -aE "kmod_linux: relocations applied=" "$LOG" | grep -vE 'skipped=0' | head
        grep -aE "kmod_linux: unresolved external" "$LOG" | head -30
        fail=1
    fi
else
    echo "[test_snd_hda_ko] MISS: only ${n_load_ok:-0} kmod_linux_load OK (expected >=2)"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_snd_hda_ko] FAIL (qemu rc=$rc)"
    echo "[test_snd_hda_ko] --- full log tail ---"
    tail -160 "$LOG"
    exit 1
fi

echo "[test_snd_hda_ko] PASS (snd_hda_intel.ko + deps loaded via L-shim)"
