#!/usr/bin/env bash
# scripts/test_e1000e_tx.sh — regression guard for the e1000e TX path,
# now driven by Linux's stock e1000e.ko via the L-series loader (the
# strategic pivot from the hand-rolled drivers/net/e1000e.ad).
#
# Boots the kernel with `-device e1000e` as the ONLY NIC, with the
# ENABLE_E1000E_KO=1 marker set so init/main.ad's boot:35.a path runs
# kmod_linux_load /lib/modules/e1000e.ko and pci_scan's hand-rolled
# e1000e_init is skipped (would conflict on MMIO BARs).
#
# Assertions (V0 — module load succeeds):
#   1. "[e1000e.ko] loading"           — the .ko bytes were found in
#      the cpio archive (planted by build_initramfs.py when the
#      ENABLE_E1000E_KO env var is set).
#   2. "[e1000e.ko] kmod_linux_load OK" — the L-series loader walked
#      the ET_REL ELF, applied all relocations, and ran the module's
#      init_module without unresolved-external panic.
#
# DHCP / TX / RX assertions are NOT yet enforced in V0 — the stock
# driver's probe path does PCI enable + alloc rings + NAPI setup;
# real TX/RX requires an IOAPIC IRQ wiring (not yet plumbed) and
# the driver's eth_tx hook integration with our upper stack
# (deferred to a follow-up commit). The loaded-but-quiet state
# is the first milestone; building real I/O on top is the next.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf

echo "[test_e1000e_tx] (1/3) Build userland + modules + initramfs"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null
ENABLE_E1000E_KO=1 python3 scripts/build_initramfs.py >/dev/null

echo "[test_e1000e_tx] (2/3) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_e1000e_tx] (3/3) Boot QEMU with e1000e as the ONLY NIC"
LOG=$(mktemp)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
timeout 25s qemu-system-x86_64 \
    -kernel "$ELF" \
    -netdev user,id=n0 \
    -device e1000e,netdev=n0,mac=52:54:00:12:34:56 \
    -nographic -no-reboot -m 256M -monitor none -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

echo "[test_e1000e_tx] --- captured (kmod / e1000e / eth / pci_register_driver) ---"
grep -E 'kmod_linux|\[e1000e\.ko\]|\[e1000e\]|\[eth\]|\[netdev|\[boot:35|\[pci_register_driver\]' "$LOG" || true
echo "[test_e1000e_tx] --- end ---"

fail=0
# Assertions: the .ko was found in cpio, the L-series loader walked
# the ET_REL header successfully, applied every relocation without
# leaving any unresolved-external skipped, called init_module and
# init_module returned 0. M16-pivot.b: __pci_register_driver now
# walks the live bus, matches against drv->id_table, and INVOKES
# drv->probe(pdev, id) — observable as "[pci_register_driver]
# MATCH 8086:10d3 at 0:3" + "calling probe(...)" + "probe returned
# rc=...". The QEMU e1000e device responds to vendor 0x8086 device
# 0x10d3 (82574-class) at bus 0 device 3 function 0, which is what
# the assertion below pins. DHCP / real TX-RX through the Linux
# driver is the next milestone — probe returns -EIO at the
# ioremap step (pci_resource_start needs the struct pci_dev
# resource[] array populated, which is itself non-trivial: the
# field lives past struct device dev which has CONFIG-dependent
# size).
for needle in \
    "[e1000e.ko] loading" \
    "kmod_linux: relocations applied=" \
    "kmod_linux: init_module @" \
    "[e1000e.ko] kmod_linux_load OK" \
    "[pci_register_driver] MATCH 8086:10d3" \
    "[pci_register_driver] calling probe(" \
    "[pci_register_driver] probe returned rc="
do
    if grep -F -q "$needle" "$LOG"; then
        echo "[test_e1000e_tx] OK: '$needle'"
    else
        echo "[test_e1000e_tx] MISS: '$needle'"
        fail=1
    fi
done

# Also assert no skipped relocations — every UND must have resolved.
if grep -E -q "kmod_linux: relocations applied=[0-9]+ skipped=0" "$LOG"; then
    echo "[test_e1000e_tx] OK: 'all relocations resolved (0 skipped)'"
else
    echo "[test_e1000e_tx] MISS: 'all relocations resolved (0 skipped)'"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_e1000e_tx] FAIL (qemu rc=$rc)"
    echo "[test_e1000e_tx] --- full log ---"
    cat "$LOG"
    exit 1
fi

echo "[test_e1000e_tx] PASS (.ko loaded; init_module returned 0; probe invoked)"
