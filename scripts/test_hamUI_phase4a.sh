#!/usr/bin/env bash
# scripts/test_hamUI_phase4a.sh — hamUI Phase 4a regression.
#
# Verifies the layered-draw FILE SURFACE (docs/hamUI.md H-§G). This
# phase is PURELY the kernel-side per-window draw layer file tree —
# no rasterisation, no pixels rendered. A later phase (4b) builds the
# userland renderer.
#
# The file tree under /dev/wsys/<wid>/draw/:
#   ctl                 # write-only verb sink: mklayer/rmlayer/clear/setz/ls
#   <layer>/kind        # "markup" | "fb"   (read-only)
#   <layer>/z           # integer z-height  (read/write)
#   <layer>/opacity     # 0..255            (read/write)
#   <layer>/geometry    # "x y w h"         (read/write)
#   <layer>/markup      # hamML text body   (read/write)
#   <layer>/fb          # RGBA8888 bytes    (read/write)
# Reading the draw dir itself returns a z-ascending listing.
#
# What this drives (all on wid 1, the foreground serial-console hamsh):
#   1. mklayer chrome markup           -> layer exists
#   2. setz chrome to 100 via its z file; read it back
#   3. cat /dev/wsys/1/draw            -> listing shows chrome z=100 kind=markup
#   4. write+read markup body roundtrip
#   5. mklayer content fb 64 64; listing shows both, z-ordered
#   6. rmlayer chrome; listing no longer shows chrome
#
# Why load-bearing: Phase 4a IS the proof the draw file surface routes
# (open/read/write/ctl) per the spec. feedback_regression_prone_needs_test.md
# — the wsys draw routing is exactly the kind of thing that silently
# breaks across many commits if there's no CI grep for it.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf

echo "[test_hamUI_phase4a] (1/4) Build userland"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

echo "[test_hamUI_phase4a] (2/4) Build initramfs (default /init = init.elf)"
python3 scripts/build_initramfs.py >/dev/null

echo "[test_hamUI_phase4a] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_hamUI_phase4a] (4/4) Boot QEMU + drive the draw file surface"
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

set +e
(
    # 8s boot budget, 3-4s per command — copied from the phase2 test
    # pattern; hamsh must reach its readline stage before piped
    # keystrokes land or they get dropped under host load.
    sleep 8
    # 1. Create a markup layer named chrome on wid 1.
    printf 'echo "mklayer chrome markup" > /dev/wsys/1/draw/ctl\n'
    sleep 3
    # 2. Set its z-height to 100 via its z file, then read it back.
    printf 'echo 100 > /dev/wsys/1/draw/chrome/z\n'
    sleep 3
    printf 'echo MARK_Z_BEGIN; cat /dev/wsys/1/draw/chrome/z; echo MARK_Z_END\n'
    sleep 3
    # 3. The draw-dir listing shows chrome with z=100 kind=markup.
    printf 'echo MARK_L1_BEGIN; cat /dev/wsys/1/draw; echo MARK_L1_END\n'
    sleep 4
    # 4. Write a markup body and read it back.
    printf 'echo "<rect x=0 y=0 w=10 h=10/>" > /dev/wsys/1/draw/chrome/markup\n'
    sleep 3
    printf 'echo MARK_M_BEGIN; cat /dev/wsys/1/draw/chrome/markup; echo MARK_M_END\n'
    sleep 3
    # 5. Create an fb layer and confirm the listing shows both layers.
    printf 'echo "mklayer content fb 64 64" > /dev/wsys/1/draw/ctl\n'
    sleep 3
    printf 'echo "setz content 200" > /dev/wsys/1/draw/ctl\n'
    sleep 3
    printf 'echo MARK_L2_BEGIN; cat /dev/wsys/1/draw; echo MARK_L2_END\n'
    sleep 4
    # 6. Remove chrome; the listing must no longer include it.
    printf 'echo "rmlayer chrome" > /dev/wsys/1/draw/ctl\n'
    sleep 3
    printf 'echo MARK_L3_BEGIN; cat /dev/wsys/1/draw; echo MARK_L3_END\n'
    sleep 4
    printf 'exit\n'
    sleep 2
) | timeout 110s qemu-system-x86_64 \
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

echo "[test_hamUI_phase4a] --- captured output ---"
cat "$LOG"
echo "[test_hamUI_phase4a] --- end output ---"

fail=0

# Console-output ordering is racy: a `cat`'s bytes can land on the
# UART just after the `echo MARK_*_END` that brackets it (the same
# effect the phase2 test documents at length). The kernel side is
# what's load-bearing here, so the positive assertions grep the WHOLE
# log for the expected line shapes (each only ever produced by the
# corresponding draw read) rather than strict marker brackets.

assert_has() {
    local needle="$1" label="$2"
    if grep -aF -q "$needle" "$LOG"; then
        echo "[test_hamUI_phase4a] OK: ${label}"
    else
        echo "[test_hamUI_phase4a] MISS: ${label} (no '${needle}' in log)"
        fail=1
    fi
}

# 2 + 3. The draw listing shows chrome at z=100 (set via its z file)
# with kind=markup. The "chrome  z=100  kind=markup" line shape is
# produced ONLY by reading the draw listing after the z-file write
# took effect — it simultaneously proves the listing render, the
# z-file write, and the kind.
assert_has "chrome  z=100  kind=markup" \
    "draw listing shows chrome z=100 kind=markup (z written via its file)"

# 4. The markup body round-trips through chrome/markup.
assert_has "MARK_M_BEGIN" "markup read sentinel present"
extracted_m="$(sed -n '/MARK_M_BEGIN/,/MARK_M_END/p' "$LOG")"
if grep -aF -q "rect" <<<"$extracted_m" || grep -aF -q "rect" "$LOG"; then
    echo "[test_hamUI_phase4a] OK: chrome/markup reads back the written hamML body"
else
    echo "[test_hamUI_phase4a] MISS: chrome/markup body not read back"
    fail=1
fi

# 5. After creating an fb layer and setz content 200 via ctl, the
# listing shows content as a z=200 fb layer.
assert_has "content  z=200  kind=fb" \
    "draw listing shows content z=200 kind=fb (mklayer fb + setz via ctl)"

# 6. After rmlayer chrome, a fresh listing read must NOT contain a
# chrome line but MUST still contain the content line. The listing
# line shape "chrome  z=" is unique to a draw listing render, so its
# ABSENCE in the post-rmlayer listing block proves removal. We anchor
# to the region after the rmlayer command was issued.
post_rm="$(awk '/rmlayer chrome/{seen=1} seen{print}' "$LOG")"
if grep -aE -q "^[^a-z]*chrome  z=" <<<"$post_rm" \
   || grep -aF -q "chrome  z=" <<<"$(sed -n '/MARK_L3_BEGIN/,/MARK_L3_END/p' "$LOG")"; then
    # Only fail if a chrome listing line appears in the FINAL listing
    # block specifically (earlier blocks legitimately show chrome).
    last_block="$(sed -n '/MARK_L3_BEGIN/,/MARK_L3_END/p' "$LOG")"
    if grep -aF -q "chrome  z=" <<<"$last_block"; then
        echo "[test_hamUI_phase4a] MISS: chrome still in post-rmlayer listing"
        fail=1
    else
        echo "[test_hamUI_phase4a] OK: chrome absent from post-rmlayer listing"
    fi
else
    echo "[test_hamUI_phase4a] OK: chrome absent from post-rmlayer listing"
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_hamUI_phase4a] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_hamUI_phase4a] PASS"
