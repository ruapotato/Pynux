#!/usr/bin/env bash
# scripts/test_net_e1000e.sh — end-to-end test for the M16.103
# bare-metal e1000e PCI driver.
#
# Boots the kernel with a QEMU e1000e device attached to SLIRP.
# `pci_scan()` (in drivers/pci/pci.ad) calls `e1000e_init()` once
# the bus walk completes; the driver matches Intel vendor 0x8086
# plus device 0x10D3 (82574L, QEMU's `-device e1000e` model),
# enables the PCI MEM + bus-master pair, maps BAR0, sets SLU+ASDE
# on CTRL, reads the MAC from RAL[0]/RAH[0], builds a 256-slot RX
# descriptor ring + 256 × 2 KiB receive buffers, and arms RCTL.EN.
#
# Scope is PROBE + IDENTIFY + RECEIVE only — no TX, no integration
# with the ARP/IP/UDP/ICMP/DNS/DHCP stack. virtio-net (M16.88)
# stays the bring-up NIC for those tests.
#
# The test asserts:
#   1. "[e1000e] controller found bdf=" — PCI vendor/device match
#      + class-triple cross-check both succeeded.
#   2. "[e1000e] mac=52:54:00:12:34:56" — RAL0/RAH0 read worked
#      against the MAC QEMU loaded from the `mac=` argument.
#   3. "[e1000e] link up" — STATUS.LU bit set after SLU+ASDE; QEMU
#      flips this within a few register reads of CTRL being
#      programmed, so it should always be observable here.
#   4. "[e1000e] RX ring ready (256 descriptors)" — the descriptor
#      ring + per-descriptor 2 KiB buffer pre-population path
#      completed without a kmalloc failure.
#   5. "[e1000e] init done" — top-level driver entry returned 0.
#
# RX packet observation is NOT asserted — SLIRP under
# `-device e1000e` does not spontaneously emit broadcasts the way
# it does for virtio-net's ARP path (we haven't built a TX
# path under this driver to provoke a reply), so demanding an RX
# packet would be a flake gate. The follow-up M16.103.1 milestone
# adds a single-descriptor TX helper + an ARP probe to round-trip
# an inbound frame; this commit's test bar is "driver alive".

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-vmlinux.elf

echo "[test_net_e1000e] (1/3) Build userland + modules + initramfs"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null
python3 scripts/build_initramfs.py >/dev/null

echo "[test_net_e1000e] (2/3) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_net_e1000e] (3/3) Boot QEMU with e1000e attached"
LOG=$(mktemp)
# Restore the default /init at the end so subsequent tests / runs
# don't see whatever initramfs state we leave behind.
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
timeout 15s qemu-system-x86_64 \
    -kernel "$ELF" \
    -netdev user,id=n0 \
    -device e1000e,netdev=n0,mac=52:54:00:12:34:56 \
    -nographic -no-reboot -m 256M -monitor none -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

echo "[test_net_e1000e] --- captured (e1000e lines) ---"
grep -E '\[e1000e\]' "$LOG" || true
echo "[test_net_e1000e] --- end ---"

fail=0
for needle in \
    "[e1000e] controller found bdf=" \
    "[e1000e] mac=52:54:00:12:34:56" \
    "[e1000e] link up" \
    "[e1000e] RX ring ready (256 descriptors)" \
    "[e1000e] init done"
do
    if grep -F -q "$needle" "$LOG"; then
        echo "[test_net_e1000e] OK: '$needle'"
    else
        echo "[test_net_e1000e] MISS: '$needle'"
        fail=1
    fi
done

# Optional: if we did happen to see an RX packet (e.g. an STP BPDU
# from a real switch, or future SLIRP behaviour), log that it
# fired — but DO NOT gate the test on it.
if grep -F -q "[e1000e] RX packet: len=" "$LOG"; then
    echo "[test_net_e1000e] INFO: at least one RX frame observed"
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_net_e1000e] FAIL (qemu rc=$rc)"
    echo "[test_net_e1000e] --- full log ---"
    cat "$LOG"
    exit 1
fi

echo "[test_net_e1000e] PASS"
