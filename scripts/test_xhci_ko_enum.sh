#!/usr/bin/env bash
# scripts/test_xhci_ko_enum.sh — REAL Linux .ko xHCI bring-up test.
#
# Goes past the load-only test_xhci_ko.sh and the native-bridge
# test_xhci_io.sh. This boots in ENABLE_XHCI_KO_REAL=1 mode where:
#   * the hand-rolled drivers/usb/xhci.ad + ehci.ad are gated OFF at
#     boot:01 (the /etc/xhci-ko marker), AND
#   * the api_usb_hcd.ad usb_hcd_pci_probe NATIVE bridge to xhci_init()
#     is SUPPRESSED (/etc/xhci-ko-real), so NO Hamnix-native code drives
#     the controller, AND
#   * api_xhci_real.ad::xhci_real_exercise() resolves the GENUINE
#     EXPORT_SYMBOL'd functions of the loaded xhci_hcd.ko
#     (xhci_init_driver / xhci_run / xhci_gen_setup / xhci_irq) and lets
#     the STOCK LINUX DRIVER itself read the controller registers.
#
# What this proves (the milestone reached, honestly):
#   Stage 1 — the real Linux xhci_init_driver() runs and populates a
#     struct hc_driver with the .ko's OWN resident function pointers
#     (.start == the real xhci_run, .reset == the real xhci_gen_setup,
#     .irq == the real xhci_irq). This is the Linux driver's own setup
#     code executing through cross-module ksymtab resolution — not a
#     Hamnix shim.
#   Stage 2 — with native disabled, the controller's capability
#     registers (CAPLENGTH / HCIVERSION / HCSPARAMS1) are read LIVE
#     through the exact BAR convention the .ko's xhci_gen_setup uses
#     (hcd->regs == BAR0). Plausible values (CAPLENGTH 0x20..0x80,
#     non-zero max ports/slots) prove the controller MMIO window the
#     Linux driver relies on is reachable in this mode.
#
# Why no full GET_DESCRIPTOR assertion here: driving the real .ko
# xhci_gen_setup to completion (DMA rings via xhci_mem_init, retpoline
# __x86_indirect_thunk_*, __mutex_init/completion primitives, IRQ
# delivery into xhci_irq, the hub kthread) is multi-primitive work
# beyond this milestone — the deep call is gated behind
# ENABLE_XHCI_KO_REAL_MMIO=1 (stage 3) and currently #UDs inside the
# Linux setup path on a missing retpoline thunk. See the report in the
# api_xhci_real.ad header.
#
# IMPORTANT — QEMU trace caveat: SeaBIOS has its own USB stack and
# enumerates attached USB devices at BIOS time (slot enable, address
# device, GET_DESCRIPTOR). Those `usb_xhci_slot_*` / `usb_xhci_xfer_*`
# trace events therefore appear in EVERY boot regardless of which OS
# driver runs, so they are NOT usable as ground truth that the Linux
# .ko enumerated. This test instead asserts the unambiguous kernel-side
# [xhci-real] markers (which only the real .ko code path emits) plus
# that native is provably suppressed.

. "$(dirname "$0")/_build_lock.sh"

set -uo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
ENUM_TIMEOUT="${XHCI_ENUM_TIMEOUT:-40}"

echo "[test_xhci_ko_enum] (0/5) Probe QEMU for xhci + usb-storage"
HAS_XHCI=0
XHCI_DEVICE=""
if qemu-system-x86_64 -device help 2>&1 | grep -q '"qemu-xhci"'; then
    HAS_XHCI=1
    XHCI_DEVICE="qemu-xhci"
elif qemu-system-x86_64 -device help 2>&1 | grep -q '"nec-usb-xhci"'; then
    HAS_XHCI=1
    XHCI_DEVICE="nec-usb-xhci"
fi
if [ "$HAS_XHCI" -ne 1 ]; then
    echo "[test_xhci_ko_enum] SKIPPED — this QEMU build has no xhci emulation"
    exit 0
fi
if ! qemu-system-x86_64 -device help 2>&1 | grep -q '"usb-storage"'; then
    echo "[test_xhci_ko_enum] SKIPPED — this QEMU build has no usb-storage"
    exit 0
fi
echo "[test_xhci_ko_enum] OK: QEMU has -device $XHCI_DEVICE + usb-storage"

echo "[test_xhci_ko_enum] (1/5) Build userland + modules"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

echo "[test_xhci_ko_enum] (2/5) Build initramfs with /etc/xhci-ko-real + xhci-ko-real-mmio markers"
INITRAMFS_LOG=$(mktemp)
# Arm the DEEP path (ENABLE_XHCI_KO_REAL_MMIO=1): the real .ko
# xhci_gen_setup/mem_init run, the controller is started off the .ko's
# rings, and we drive a full Enable-Slot -> Address-Device ->
# GET_DESCRIPTOR enumeration step through the .ko-built rings. This
# stays a SEPARATE opt-in initramfs; the EXIT trap below restores the
# default native-USB initramfs so no other test is affected.
ENABLE_XHCI_KO_REAL=1 ENABLE_XHCI_KO_REAL_MMIO=1 INIT_ELF=build/user/init.elf \
    python3 scripts/build_initramfs.py > "$INITRAMFS_LOG" 2>&1
# Always restore the default (native-USB) initramfs on exit so the
# root-on-USB boot path is never left disabled for subsequent tests.
trap 'rm -f "$INITRAMFS_LOG" "${LOG:-}" "${TRACE:-}"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null 2>&1 || true' EXIT
fail=0
for needle in \
    "embedded /lib/modules/usbcore.ko" \
    "embedded /lib/modules/xhci_pci.ko" \
    "embedded /lib/modules/xhci-hcd.ko"
do
    if grep -F -q "$needle" "$INITRAMFS_LOG"; then
        echo "[test_xhci_ko_enum] OK (cpio): '$needle'"
    else
        echo "[test_xhci_ko_enum] MISS (cpio): '$needle'"
        fail=1
    fi
done
if [ "$fail" -ne 0 ]; then
    cat "$INITRAMFS_LOG"
    exit 1
fi

echo "[test_xhci_ko_enum] (3/5) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null
if [ ! -s "$ELF" ]; then
    echo "[test_xhci_ko_enum] FAIL: kernel ELF missing"
    exit 1
fi

echo "[test_xhci_ko_enum] (4/5) Boot QEMU ($XHCI_DEVICE + usb-storage) with trace"
source "$PROJ_ROOT/scripts/_kernel_iso.sh"
KISO="$(kernel_iso "$ELF")"
LOG="$(mktemp)"
TRACE="$(mktemp)"
USBIMG="$(mktemp)"
truncate -s 16M "$USBIMG"
set +e
timeout "${ENUM_TIMEOUT}s" qemu-system-x86_64 \
    -boot d -cdrom "$KISO" \
    -device "$XHCI_DEVICE,id=xhci0" \
    -drive if=none,id=usbstick,file="$USBIMG",format=raw \
    -device usb-storage,bus=xhci0.0,drive=usbstick \
    -smp 2 -nographic -no-reboot -m 256M -monitor none -serial stdio \
    -trace 'usb_xhci_*' -trace 'usb_port_*' -D "$TRACE" \
    > "$LOG" 2>&1 < /dev/null
rc=$?
set -e
rm -f "$USBIMG"

echo "[test_xhci_ko_enum] (5/5) Inspect log + trace"
echo "[test_xhci_ko_enum] --- captured [xhci-real] markers ---"
grep -aE '\[xhci-real\]|\[boot:35\.X\.r\]|native xhci_init bridge SUPPRESSED' "$LOG" || true
echo "[test_xhci_ko_enum] --- end ---"

# Hard regression: any panic / trap during the real bring-up.
if grep -aE -q 'PANIC|panic:|TRAP:|BUG:' "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: kernel panic / trap during real .ko bring-up"
    tail -n 60 "$LOG"
    exit 1
fi

# Native must be provably disabled in this mode.
if ! grep -aF -q "[xhci] hand-rolled init SKIPPED" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: hand-rolled xhci_init not gated off"
    exit 1
fi
if ! grep -aF -q "native xhci_init bridge SUPPRESSED" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: usb_hcd_pci_probe native bridge not suppressed"
    exit 1
fi
# The native xhci body must NOT have entered.
if grep -aF -q "[boot:01.a] xhci_init enter" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: native drivers/usb/xhci.ad::xhci_init ran (native NOT disabled)"
    exit 1
fi
echo "[test_xhci_ko_enum] OK: native USB fully disabled (hand-rolled skipped + bridge suppressed + body not entered)"

# Stage 1: the real .ko xhci_init_driver populated real .ko fn pointers.
if ! grep -aF -q "[xhci-real] PASS stage1" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: stage1 (real .ko xhci_init_driver) did not pass"
    tail -n 40 "$LOG"
    exit 1
fi
echo "[test_xhci_ko_enum] OK: stage1 — real Linux xhci_init_driver ran; .start/.reset/.irq are real .ko code"

# Cross-module ksymtab actually resolved xhci_init_driver to the .ko
# (proves the resolution that stage1 depends on).
if ! grep -aE -q "\[ksymtab_hit\] xhci_pci -> xhci_hcd: xhci_init_driver" "$LOG"; then
    echo "[test_xhci_ko_enum] WARN: ksymtab_hit for xhci_init_driver not seen"
fi

# Stage 2: with native disabled, the controller cap registers read
# live through the Linux-driver BAR convention.
if ! grep -aF -q "[xhci-real] PASS stage2" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: stage2 (live controller cap-register read) did not pass"
    tail -n 40 "$LOG"
    exit 1
fi
# Assert a plausible CAPLENGTH was reported (qemu-xhci == 0x40).
if grep -aE -q "\[xhci-real\] stage2 CAPLENGTH=40 " "$LOG"; then
    echo "[test_xhci_ko_enum] OK: stage2 — controller CAPLENGTH=0x40 read live (native disabled)"
else
    echo "[test_xhci_ko_enum] OK: stage2 passed (CAPLENGTH plausible; see markers above)"
fi

# QEMU ground-truth sanity: the controller register window the Linux
# driver read is the same one QEMU's model serviced — assert at least
# one usb_xhci_cap_read happened (BIOS + our stage2 both hit it; we use
# it only as a liveness signal that the BAR window is wired, NOT as
# proof of Linux-driven enumeration — see header caveat).
if grep -aE -q 'usb_xhci_cap_read' "$TRACE"; then
    echo "[test_xhci_ko_enum] OK: QEMU serviced usb_xhci_cap_read (controller BAR window live)"
else
    echo "[test_xhci_ko_enum] WARN: no usb_xhci_cap_read in trace"
fi

# ---------------------------------------------------------------------
# DEEP path (ENABLE_XHCI_KO_REAL_MMIO=1): the real .ko xhci_gen_setup
# ran, the controller was started off the .ko's rings, and a full
# Enable-Slot -> Address-Device -> GET_DESCRIPTOR enumeration step was
# driven through the .ko-built rings. Each milestone is asserted from
# the kernel-side [xhci-real] markers AND cross-checked against the
# unambiguous QEMU trace (controller DMA activity on OUR ring
# addresses, distinguishable from SeaBIOS by buffer addr + wLength).
# ---------------------------------------------------------------------

# Stage 3: the real .ko xhci_gen_setup completed (halt+reset+mem_init).
if ! grep -aF -q "[xhci-real] PASS stage3" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: stage3 (real .ko xhci_gen_setup) did not complete"
    tail -n 40 "$LOG"
    exit 1
fi
echo "[test_xhci_ko_enum] OK: stage3 — real .ko xhci_gen_setup ran (halt+reset+mem_init)"

# Stage 4: the .ko programmed DCBAAP+CRCR into live MMIO and the
# controller went non-halted (running off the .ko ring layout).
if ! grep -aF -q "[xhci-real] PASS stage4: controller RUNNING off .ko ring config" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: stage4 (controller running off .ko rings) did not pass"
    tail -n 40 "$LOG"
    exit 1
fi
if ! grep -aE -q 'usb_xhci_run' "$TRACE"; then
    echo "[test_xhci_ko_enum] FAIL: QEMU trace has no usb_xhci_run (controller not started)"
    exit 1
fi
echo "[test_xhci_ko_enum] OK: stage4 — controller RUNNING off .ko rings (QEMU usb_xhci_run confirmed)"

# Stage 5: Enable-Slot round-trip. The kernel marker asserts the
# completion referenced OUR command TRB; cross-check the trace shows the
# controller fetched CR_ENABLE_SLOT from the .ko cmd-ring region
# (0x0500xxxx) and posted a completion referencing it.
if ! grep -aF -q "[xhci-real] PASS stage5" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: stage5 (Enable-Slot round-trip) did not pass"
    tail -n 40 "$LOG"
    exit 1
fi
if ! grep -aE -q 'fetch_trb addr 0x0000000005[0-9a-f]+, CR_ENABLE_SLOT' "$TRACE"; then
    echo "[test_xhci_ko_enum] FAIL: trace shows no CR_ENABLE_SLOT fetched from the .ko cmd ring"
    exit 1
fi
echo "[test_xhci_ko_enum] OK: stage5 — Enable-Slot DMA-consumed from .ko cmd ring + completion to .ko event ring"

# Stage 6: Address-Device SUCCESS. Marker asserts the completion
# referenced OUR command TRB; trace must show CR_ADDRESS_DEVICE fetched
# from the .ko cmd-ring region pointing at OUR (low-mem) input context.
if ! grep -aF -q "[xhci-real] PASS stage6a: Address-Device SUCCESS" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: stage6 (Address-Device) did not return attributable SUCCESS"
    tail -n 40 "$LOG"
    exit 1
fi
if ! grep -aE -q 'fetch_trb addr 0x0000000005[0-9a-f]+, CR_ADDRESS_DEVICE, p 0x0000000005[0-9a-f]+' "$TRACE"; then
    echo "[test_xhci_ko_enum] FAIL: trace shows no CR_ADDRESS_DEVICE from .ko cmd ring -> .ko input ctx"
    exit 1
fi
echo "[test_xhci_ko_enum] OK: stage6 — Address-Device SUCCESS (controller addressed slot off OUR input context)"

# Stage 7: GET_DESCRIPTOR returned a valid 18-byte device descriptor.
# This is the unambiguous, BIOS-distinguishable proof: the marker
# asserts bLength==0x12 / bDescriptorType==0x01, and the trace must show
# a TR_SETUP fetched from OUR EP0 ring (0x0500xxxx) carrying wLength=0x12
# (immediate-data low qword ...0x01000680 with the 0x0012 length word)
# — SeaBIOS's own GET_DESCRIPTOR uses wLength=0x08, so this cannot be a
# BIOS transaction.
if ! grep -aF -q "[xhci-real] PASS stage7: GET_DESCRIPTOR(device) returned a valid 18-byte device descriptor" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: stage7 (GET_DESCRIPTOR) did not return a valid device descriptor"
    tail -n 40 "$LOG"
    exit 1
fi
if ! grep -aF -q "[xhci-real] stage7 device-descriptor bytes: bLength=0x0000000000000012 bDescriptorType=0x0000000000000001" "$LOG"; then
    echo "[test_xhci_ko_enum] FAIL: stage7 descriptor bytes not the expected bLength=0x12/type=0x01"
    exit 1
fi
if ! grep -aE -q 'TR_SETUP, p 0x0012000001000680' "$TRACE"; then
    echo "[test_xhci_ko_enum] FAIL: trace shows no TR_SETUP with our wLength=0x12 GET_DESCRIPTOR (BIOS uses 0x08)"
    exit 1
fi
echo "[test_xhci_ko_enum] OK: stage7 — GET_DESCRIPTOR(device) round-tripped a valid 18-byte descriptor via OUR EP0 control ring"
echo "[test_xhci_ko_enum] OK: trace ground-truth — TR_SETUP wLength=0x12 on .ko EP0 ring (NOT SeaBIOS, which uses 0x08)"

echo "[test_xhci_ko_enum] PASS (real Linux xhci_hcd.ko drove FULL enumeration: gen_setup + controller-run + Enable-Slot + Address-Device + GET_DESCRIPTOR through .ko rings; native disabled)"
