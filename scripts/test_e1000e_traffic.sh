#!/usr/bin/env bash
# scripts/test_e1000e_traffic.sh — NIC subsystem proof-of-concept
# exercise for the stock Linux e1000e.ko, driven via the L-series
# loader. Builds on top of scripts/test_e1000e_tx.sh (which only
# proved DHCP — ~4 packets — round-trips) by exercising the regular
# packet flow that the rest of the network stack (and every other
# Linux NIC .ko: r8169 / igb / atlantic / alx / sky2 / tg3) rides:
#
#   PHASE A — ICMP ping x5 to the SLIRP gateway (10.0.2.2). Asserts
#             >= 3 of 5 echo replies land. Exercises ARP-cached
#             unicast TX and IRQ-driven RX via MSI vector 0x47.
#
#   PHASE B — DNS A-record lookup for example.com via SLIRP's
#             built-in nameserver (10.0.2.3 from DHCP option 6).
#             Strict PASS requires a resolved answer (live wire);
#             "[traffic_test] PHASE_B_SKIP" (no host internet) is
#             also accepted as proof the TX side issued the query.
#
#   PHASE C — 320-packet UDP burst to 10.0.2.2:9 (closed port).
#             Forces wraparound on the 256-entry TX descriptor ring
#             (and best-effort wraparound on the RX side via SLIRP's
#             ICMP port-unreachable replies). Asserts >= 300 of 320
#             datagrams accepted by udp_send without NETDEV_TX_BUSY.
#             That proves e1000_clean_tx_irq + dev_kfree_skb_any
#             actually recycle descriptors as the ring fills, not
#             just on the first batch.
#
# Setup mirrors test_e1000e_tx.sh: the kernel is built fresh, the
# initramfs is rebuilt with ENABLE_E1000E_TRAFFIC_TEST=1 to plant
# /etc/e1000e-traffic-test (init/main.ad gates the smoke on that
# marker), and QEMU is launched with -device e1000e as the ONLY
# NIC and SLIRP as the user network backend.
#
# Hard failures: any panic, TRAP, BUG marker, or unresolved external
# symbol immediately fails the test before the phase markers are
# graded. Each PHASE_*_PASS / PHASE_*_FAIL line is the gold-standard
# pass/fail channel.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf

echo "[test_e1000e_traffic] (1/3) Build userland + modules + initramfs (with marker)"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null
ENABLE_E1000E_TRAFFIC_TEST=1 python3 scripts/build_initramfs.py >/dev/null

echo "[test_e1000e_traffic] (2/3) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_e1000e_traffic] (3/3) Boot QEMU with e1000e as the ONLY NIC"
LOG=$(mktemp)
# Restore the default (no-marker) initramfs on exit so a follow-up
# test_e1000e_tx.sh sees the same boot shape.
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

# 60s wall-clock — DHCP (~1 s) + Phase A (~1 s) + Phase B (~2 s
# deadline) + Phase C (~2-5 s for 320 sends with inter-batch spins)
# + boot setup. Headroom for slow CI.
set +e
timeout 60s qemu-system-x86_64 \
    -kernel "$ELF" \
    -netdev user,id=n0 \
    -device e1000e,netdev=n0,mac=52:54:00:12:34:56 \
    -nographic -no-reboot -m 256M -monitor none -serial stdio \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e

echo "[test_e1000e_traffic] --- captured (boot:35.b/c, traffic_test, dhcp, icmp, dns) ---"
grep -E '\[boot:35\.[bc]\]|\[traffic_test\]|\[dhcp\]|\[icmp\]|\[dns\]' "$LOG" | head -120 || true
echo "[test_e1000e_traffic] --- end ---"

# Hard-fail on any panic / TRAP / BUG / unresolved extern *before*
# grading the phases. The e1000e.ko loader has historically emitted
# "[kmod_linux] UND unresolved" for missing shim symbols; that's an
# automatic kill.
HARD_FAIL=0
for marker in \
    "PANIC" \
    "kernel panic" \
    "TRAP " \
    "BUG: " \
    "BUG()" \
    "UND unresolved" \
    "skipped=[1-9]"
do
    if grep -E -q "$marker" "$LOG"; then
        echo "[test_e1000e_traffic] HARD FAIL: matched '$marker'"
        HARD_FAIL=1
    fi
done

# Preconditions inherited from test_e1000e_tx.sh — if these miss the
# .ko didn't even get DHCP, so the traffic test can't have run.
PRECOND_FAIL=0
for needle in \
    "[e1000e.ko] loading" \
    "[e1000e.ko] kmod_linux_load OK" \
    "[pci_register_driver] probe OK; triggering dev_open" \
    "[pci_msi] vector=0x47 enabled" \
    "[linux_tx_bridge] armed for netdev=" \
    "[dhcp] got ip=10.0.2.15" \
    "[boot:35.c] e1000e.ko traffic exercise (PHASE A/B/C)" \
    "[traffic_test] BEGIN: e1000e.ko traffic exercise"
do
    if grep -F -q "$needle" "$LOG"; then
        echo "[test_e1000e_traffic] OK precond: '$needle'"
    else
        echo "[test_e1000e_traffic] MISS precond: '$needle'"
        PRECOND_FAIL=1
    fi
done

if [ "$HARD_FAIL" -ne 0 ] || [ "$PRECOND_FAIL" -ne 0 ]; then
    echo "[test_e1000e_traffic] FAIL (qemu rc=$rc; hard=$HARD_FAIL precond=$PRECOND_FAIL)"
    echo "[test_e1000e_traffic] --- full log ---"
    cat "$LOG"
    exit 1
fi

# Phase grading. Each phase emits exactly one of:
#   "[traffic_test] PHASE_X_PASS"
#   "[traffic_test] PHASE_X_FAIL:"
#   (Phase B only) "[traffic_test] PHASE_B_SKIP:"  — TX worked, no
#                                                    host internet for
#                                                    a live answer.
PHASE_FAIL=0

# Phase A — ICMP ping. Hard pass/fail.
if grep -F -q "[traffic_test] PHASE_A_PASS" "$LOG"; then
    echo "[test_e1000e_traffic] PHASE A (ICMP ping x5): PASS"
elif grep -F -q "[traffic_test] PHASE_A_FAIL" "$LOG"; then
    echo "[test_e1000e_traffic] PHASE A (ICMP ping x5): FAIL"
    grep -F "[traffic_test] PHASE_A_FAIL" "$LOG" || true
    PHASE_FAIL=1
else
    echo "[test_e1000e_traffic] PHASE A (ICMP ping x5): NO MARKER (did the phase run?)"
    PHASE_FAIL=1
fi

# Phase B — DNS UDP. PASS or SKIP both count; only FAIL or absence
# is a failure. A SKIP still proves the TX path issued the query.
if grep -F -q "[traffic_test] PHASE_B_PASS" "$LOG"; then
    echo "[test_e1000e_traffic] PHASE B (DNS UDP lookup): PASS (resolved live)"
elif grep -F -q "[traffic_test] PHASE_B_SKIP" "$LOG"; then
    echo "[test_e1000e_traffic] PHASE B (DNS UDP lookup): SKIP (no host internet; TX-side proven)"
elif grep -F -q "[traffic_test] PHASE_B_FAIL" "$LOG"; then
    echo "[test_e1000e_traffic] PHASE B (DNS UDP lookup): FAIL"
    grep -F "[traffic_test] PHASE_B_FAIL" "$LOG" || true
    PHASE_FAIL=1
else
    echo "[test_e1000e_traffic] PHASE B (DNS UDP lookup): NO MARKER"
    PHASE_FAIL=1
fi

# Phase C — Ring wraparound. Hard pass/fail.
if grep -F -q "[traffic_test] PHASE_C_PASS" "$LOG"; then
    echo "[test_e1000e_traffic] PHASE C (320-pkt ring wraparound): PASS"
elif grep -F -q "[traffic_test] PHASE_C_FAIL" "$LOG"; then
    echo "[test_e1000e_traffic] PHASE C (320-pkt ring wraparound): FAIL"
    grep -F "[traffic_test] PHASE_C_FAIL" "$LOG" || true
    PHASE_FAIL=1
else
    echo "[test_e1000e_traffic] PHASE C (320-pkt ring wraparound): NO MARKER"
    PHASE_FAIL=1
fi

# End-of-run sentinel — orchestrator-level success marker. PHASE_B's
# SKIP is allowed; only a real FAIL would prevent ALL_PHASES_PASS.
# When that's missing but no FAILs fired, it means the smoke aborted
# mid-run (e.g. a phase panicked), which is a hard failure too.
if [ "$PHASE_FAIL" -eq 0 ]; then
    if ! grep -F -q "[traffic_test] END: ALL_PHASES_PASS" "$LOG"; then
        echo "[test_e1000e_traffic] FAIL (no ALL_PHASES_PASS sentinel — mid-run abort?)"
        echo "[test_e1000e_traffic] --- full log ---"
        cat "$LOG"
        exit 1
    fi
fi

if [ "$PHASE_FAIL" -ne 0 ]; then
    echo "[test_e1000e_traffic] FAIL (qemu rc=$rc; one or more phases did not pass)"
    echo "[test_e1000e_traffic] --- full log ---"
    cat "$LOG"
    exit 1
fi

echo "[test_e1000e_traffic] PASS (ICMP ping + DNS UDP + ring wraparound all green)"
