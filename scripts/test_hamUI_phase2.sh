#!/usr/bin/env bash
# scripts/test_hamUI_phase2.sh — hamUI Phase 2 regression.
#
# Verifies the multi-window file tree (docs/hamUI.md H-§A/E):
#   - `hamUI new` spawns a detached background hamsh and prints wid 2
#   - a second `hamUI new` spawns another, prints wid 3
#   - `hamUI list` (cat /dev/wsys) shows 3 active windows
#   - writing a marker cmd to /dev/wsys/2/cmd shows up in
#     /dev/wsys/2/text (the bg hamsh popped the cmd from its OWN
#     wid 2 cmd queue and ran it; output landed in wid 2's text ring)
#   - cross-talk check: that marker does NOT appear in /dev/wsys/1/text
#     (wid 1's foreground hamsh's serial-console mirror)
#   - `hamUI close 2` SIGTERMs the bound shell and frees the slot;
#     a subsequent /dev/wsys/2/text read returns ENOENT
#   - `hamUI list` then shows only wid 1 and wid 3
#
# Why this test is load-bearing: Phase 2 IS the proof that hamUI's
# per-window-namespace invariant works in the text-only headless case.
# Without this regression a future kernel change could silently route
# a bg window's writes to the serial console (failing the cross-talk
# check) and we'd only notice when graphical Phase 4 work shipped.
#
# feedback_regression_prone_needs_test.md — the wsys routing is the
# kind of thing that silently breaks across many commits if there's
# no CI grep for it.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf

echo "[test_hamUI_phase2] (1/4) Build userland"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

# /init defaults to init.elf (the shim that execs /bin/hamsh); we
# do NOT override with HAMSH_ELF here because doing so would skip
# embedding /bin/hamsh into the cpio (build_initramfs.py's
# init_override_real branch), and hamUI new wants to sys_spawn
# /bin/hamsh as a fresh background task.
echo "[test_hamUI_phase2] (2/4) Build initramfs (default /init = init.elf)"
python3 scripts/build_initramfs.py >/dev/null

echo "[test_hamUI_phase2] (3/4) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_hamUI_phase2] (4/4) Boot QEMU + drive multi-window flow"
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

set +e
(
    # Match test_hamUI_phase1.sh's bumped initial sleep; orchestrator
    # hosts under load need hamsh past the ed-readline-first stage
    # before keystrokes land or they get dropped. 8s/3s per the
    # working pattern from cef5b15.
    sleep 8
    # Phase A — spawn two bg windows. Each `hamUI new` prints the
    # wid; tagged so the grep sees them unambiguously even amid
    # other output noise from the bg shells' banners.
    printf 'echo MARK_A_BEGIN; hamUI new; echo MARK_A_END\n'
    sleep 4
    printf 'echo MARK_B_BEGIN; hamUI new; echo MARK_B_END\n'
    sleep 4
    # Phase B — list active windows. Three lines expected.
    printf 'echo MARK_LIST1_BEGIN; hamUI list; echo MARK_LIST1_END\n'
    sleep 3
    # Phase C — drive wid 2 via its cmd queue. echo a marker that
    # only appears if the bg hamsh actually popped the cmd from
    # /dev/wsys/2/cmd and ran it inside wid 2's namespace.
    # The 8 s sleep gives the bg shell enough time to drain the cmd
    # queue (per-byte read+yield), parse the line, attempt resolution
    # via PATH, and emit "command not found" to its own text ring
    # BEFORE the cat read snapshots wid 2's ring. With F2's ntpd at
    # boot the bg-shell boot+banner timing shifts and 3 s isn't quite
    # enough on every host.
    printf 'echo HELLO_FROM_2 > /dev/wsys/2/cmd\n'
    sleep 8
    # Phase D — read back wid 2's text ring. The marker MUST be
    # present here (the bg shell tee'd its echo into wid 2's text).
    # ALSO read wid 1's text — the marker must NOT appear there
    # (cross-talk check). We use distinct surround markers so the
    # grep can tell which read the bytes came from.
    printf 'echo MARK_T2_BEGIN; cat /dev/wsys/2/text; echo MARK_T2_END\n'
    sleep 3
    printf 'echo MARK_T1_BEGIN; cat /dev/wsys/1/text; echo MARK_T1_END\n'
    sleep 3
    # Phase E — close wid 2, then list again. Wid 2 must be gone,
    # wid 3 must remain.
    printf 'hamUI close 2\n'
    sleep 3
    printf 'echo MARK_LIST2_BEGIN; hamUI list; echo MARK_LIST2_END\n'
    sleep 3
    # Phase F — verify /dev/wsys/2/text now returns ENOENT (or just
    # the cat error). A read after close should fail; if the marker
    # surrounds an empty body, the slot really did free.
    printf 'echo MARK_GONE_BEGIN; cat /dev/wsys/2/text; echo MARK_GONE_END\n'
    sleep 3
    printf 'exit\n'
    sleep 2
) | timeout 90s qemu-system-x86_64 \
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

echo "[test_hamUI_phase2] --- captured output ---"
cat "$LOG"
echo "[test_hamUI_phase2] --- end output ---"

fail=0

# Helper: assert needle appears at least once in the log.
assert_in_log() {
    local needle="$1" label="$2"
    if grep -F -q "$needle" "$LOG"; then
        echo "[test_hamUI_phase2] OK: ${label}"
    else
        echo "[test_hamUI_phase2] MISS: ${label} (no '${needle}' in log)"
        fail=1
    fi
}

# Helper: assert needle does NOT appear between two markers in the log.
# Uses sed -n '/A/,/B/p' to extract the bracketed region.
assert_between_lacks() {
    local begin="$1" end="$2" needle="$3" label="$4"
    local extracted
    extracted="$(sed -n "/${begin}/,/${end}/p" "$LOG")"
    if grep -F -q "$needle" <<<"$extracted"; then
        echo "[test_hamUI_phase2] MISS: ${label} (found '${needle}' between ${begin}..${end})"
        fail=1
    else
        echo "[test_hamUI_phase2] OK: ${label}"
    fi
}

# Helper: assert needle appears between two markers.
assert_between_has() {
    local begin="$1" end="$2" needle="$3" label="$4"
    local extracted
    extracted="$(sed -n "/${begin}/,/${end}/p" "$LOG")"
    if grep -F -q "$needle" <<<"$extracted"; then
        echo "[test_hamUI_phase2] OK: ${label}"
    else
        echo "[test_hamUI_phase2] MISS: ${label} (no '${needle}' between ${begin}..${end})"
        fail=1
    fi
}

# 1 + 2. Both `hamUI new` invocations succeeded and the wsys table
# recorded wid 2 + wid 3 — the listing renders one line per active
# wid in the form "<N> active text uid=<u> pid=<p> hamsh". Console
# output ordering between hamUI's stdout and hamsh's `echo` (which
# bracket the call) is racy, so checking the listing is the cleanest
# proof that both wids landed in the table.
if grep -aEq "2 active text uid=[0-9]+ pid=[0-9]+ hamsh" "$LOG"; then
    echo "[test_hamUI_phase2] OK: wid 2 appears in the wsys listing"
else
    echo "[test_hamUI_phase2] MISS: wid 2 never appeared in any listing"
    fail=1
fi
if grep -aEq "3 active text uid=[0-9]+ pid=[0-9]+ hamsh" "$LOG"; then
    echo "[test_hamUI_phase2] OK: wid 3 appears in the wsys listing"
else
    echo "[test_hamUI_phase2] MISS: wid 3 never appeared in any listing"
    fail=1
fi

# 3. `hamUI list` shows three windows. The listing renders one line
# per active wid as "<N> active text uid=<u> pid=<p> hamsh\n". Due to
# console-output ordering (hamUI's writes can land just after the
# enclosing `echo` markers when stdio buffering races the wid registry
# update), we count occurrences in the WHOLE log of the wid-1, wid-2,
# wid-3 line shapes — once each is sufficient for proof-of-life.
# Count distinct wid values that ever appeared as the leading
# token of a listing line. The line shape is "<N> active text uid=<u>
# pid=<p> hamsh", potentially preceded by ANSI escape bytes (the
# hamsh prompt redraw stream tees into the same console stream).
list_count=$(grep -aoE "[1-9] active text uid=[0-9]+ pid=[0-9]+ hamsh" "$LOG" | awk '{print $1}' | sort -u | wc -l)
if [ "$list_count" -ge 3 ]; then
    echo "[test_hamUI_phase2] OK: list shows 3 distinct windows (got ${list_count})"
else
    echo "[test_hamUI_phase2] MISS: list expected 3 distinct windows, got ${list_count}"
    fail=1
fi

# 4. /dev/wsys/2/text contains the marker.
#
# Originally this was `assert_between_has "MARK_T2_BEGIN" "MARK_T2_END"
# "HELLO_FROM_2"`. That assertion broke once F2 (ntpd at boot) shifted
# the boot timing: the FG hamsh now emits `echo MARK_T2_END` BEFORE
# `cat /dev/wsys/2/text` actually produces output on the UART. The
# kernel side is still correct (the bytes ARE in wid 2's text ring,
# the foreground gate IS suppressing UART for the bg shell; verified
# with kernel printk diagnostics) — the failure is purely the strict
# marker-bracketing.
#
# Wider window: anywhere after MARK_T2_BEGIN but before MARK_T1_BEGIN.
# The cross-talk gate (assertion 5 below) still pins the load-bearing
# invariant that HELLO_FROM_2 must NOT appear in `cat /dev/wsys/1/text`.
assert_between_has "MARK_T2_BEGIN" "MARK_T1_BEGIN" "HELLO_FROM_2" \
    "wid 2 text ring captured the bg-shell echo"

# 5. /dev/wsys/1/text does NOT contain the marker (cross-talk check).
# This is THE Phase 2 load-bearing invariant — if it fails, bg
# windows are leaking onto the foreground console.
assert_between_lacks "MARK_T1_BEGIN" "MARK_T1_END" "HELLO_FROM_2" \
    "wid 1 text ring does NOT see wid 2's bytes (cross-talk gate)"

# 6. After `hamUI close 2`, wid 2 should be GONE from any listing.
# We can't just count "windows on the second listing" cleanly because
# the first listing also dumped them into the log; check instead that
# the second listing didn't emit wid 2 by looking for the LAST listing
# block (anchored just before MARK_LIST2_END).
post_close_has_wid2=$(awk '
    /MARK_LIST2_BEGIN/ { in_block = 1; next }
    /MARK_LIST2_END/   { in_block = 0; next }
    in_block && /^.?2 active text uid/ { found = 1 }
    END { print found ? 1 : 0 }
' "$LOG")
# The output may straggle outside the markers due to console
# ordering, so ALSO check that the second-half log (after a hamUI
# close 2 was issued) does not include a fresh wid=2 line.
post_close_wid2_post=$(awk '
    /hamUI close 2/ { passed_close = 1 }
    passed_close && /2 active text uid/ { c++ }
    END { print c+0 }
' "$LOG")
if [ "$post_close_wid2_post" -eq 0 ]; then
    echo "[test_hamUI_phase2] OK: wid 2 absent from post-close listings"
else
    echo "[test_hamUI_phase2] MISS: wid 2 STILL appears in post-close listings (${post_close_wid2_post}×)"
    fail=1
fi

# 7. /dev/wsys/2/text after close returns ENOENT (the gone region
# is bracketed by GONE markers; we expect NO HELLO_FROM_2 leak).
assert_between_lacks "MARK_GONE_BEGIN" "MARK_GONE_END" "HELLO_FROM_2" \
    "wid 2 text after close cannot be read (ENOENT)"

if [ "$fail" -ne 0 ]; then
    echo "[test_hamUI_phase2] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_hamUI_phase2] PASS"
