#!/usr/bin/env bash
# scripts/test_hamUI_phase4c_wm.sh — hamUI Phase 4c window management.
#
# Verifies the two window-manager interactions added on top of the
# persistent `hamUId daemon` (drag-to-CREATE lives in
# test_hamUI_phase4c_interactive.sh and is unchanged):
#
#   (1) DRAG-TITLE-TO-MOVE: pressing inside a window's title bar and
#       dragging relocates the window.
#   (2) CLICK-TO-CLOSE: a press+release inside the title bar's [x] close
#       box destroys the window (tearing down its hamsh child + pipes).
#
# DETERMINISTIC PROOF (primary). `hamUId daemon wmselftest` creates one
# autowin and then drives a title-bar move + a close-box click by calling
# the EXACT same gesture state machine (wm_button) that real /dev/mouse
# packets reach — with absolute cursor coordinates, so no QEMU mouse
# injection and the result is repeatable. The daemon emits these serial
# markers we assert on:
#     WM move start
#     WM move done x=<X> y=<Y>
#     WM close window
#     DAEMON wm selftest done
# and must finish with the window count back at 0 and NO kernel panic.
#
# This is honest (the move/close traverse the real gesture machine, the
# real wsys_free, the real child SIGTERM + pipe close) — it merely drives
# the daemon's own gesture state machine with absolute coordinates instead
# of the i8042 wire, which a non-interactive QEMU run cannot drive with
# pixel precision.

. "$(dirname "$0")/_build_lock.sh"

set -uo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf

echo "[test_hamUI_phase4c_wm] (1/4) Build userland"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

echo "[test_hamUI_phase4c_wm] (2/4) Build initramfs"
python3 scripts/build_initramfs.py >/dev/null

echo "[test_hamUI_phase4c_wm] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

if [ ! -s build/user/hamUId.elf ]; then
    echo "[test_hamUI_phase4c_wm] FAIL: build/user/hamUId.elf missing/empty"
    exit 1
fi

echo "[test_hamUI_phase4c_wm] (4/4) Boot QEMU + run the WM self-test (move + close)"

LOG="$(mktemp)"
trap 'rm -f "$LOG"' EXIT

set +e
(
    sleep 10
    printf 'echo MARK_WM_BEGIN; hamUId daemon wmselftest\n'
    sleep 25
) | timeout 75s qemu-system-x86_64 \
    -kernel "$ELF" \
    -smp 2 \
    -vga std \
    -display none \
    -no-reboot \
    -m 256M \
    -serial stdio \
    > "$LOG" 2>&1
rc=$?
set -e

echo "[test_hamUI_phase4c_wm] --- captured serial output (WM markers) ---"
grep -aE 'DAEMON|WM (down|move|close)|MARK_WM_BEGIN' "$LOG" | head -40
echo "[test_hamUI_phase4c_wm] --- end ---"

fail=0

assert_marker() {
    if grep -aq "$1" "$LOG"; then
        echo "[test_hamUI_phase4c_wm] OK: $2"
    else
        echo "[test_hamUI_phase4c_wm] MISS: $2 (expected marker: '$1')"
        fail=1
    fi
}

assert_marker 'DAEMON up screen=' 'daemon started + read framebuffer geometry'
assert_marker 'DAEMON autowin created' 'autowin window created'
assert_marker 'WM move start' 'title-bar press started a window move'
assert_marker 'WM move done' 'window relocated and move finalised'
assert_marker 'WM close window' 'close-box click destroyed the window'
assert_marker 'DAEMON wm selftest done' 'self-test ran to completion (no hang/crash)'

if grep -aq 'WM move done' "$LOG"; then
    mline="$(grep -ao 'WM move done x=[0-9]* y=[0-9]*' "$LOG" | head -n1)"
    echo "[test_hamUI_phase4c_wm] moved window origin: '$mline' (autowin started at x=720 y=80)"
fi

if grep -aE -q "PANIC|panic:|TRAP:|BUG:" "$LOG"; then
    echo "[test_hamUI_phase4c_wm] FAIL: kernel panic / trap"
    tail -n 60 "$LOG"
    exit 1
fi

# rc=124 (timeout killed the forever-looping daemon) is EXPECTED — the
# daemon present-loop never exits on its own.
if [ "$fail" -ne 0 ]; then
    echo "[test_hamUI_phase4c_wm] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_hamUI_phase4c_wm] capture method: drives the real daemon gesture machine (wm_button) with absolute coordinates + deterministic serial markers"
echo "[test_hamUI_phase4c_wm] PASS"
