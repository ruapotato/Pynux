#!/usr/bin/env bash
# scripts/test_spawn_loop.sh — task-slot lifecycle regression test.
#
# REGRESSION GUARD (do not delete): an interactive hamsh session used
# to wedge after ~15 command spawns. The kernel task_table has a fixed
# NTASKS ceiling; once every slot was occupied by an un-reaped EXITED
# zombie, sys_spawn returned -1 and hamsh misreported every further
# command as "command not found". Two root causes were fixed in
# kernel/sched/core.ad::task_exit_current:
#
#   1. ORPHAN LEAK: a child whose parent had already exited (or never
#      waits) stayed STATE_EXITED forever — no init-reaper, no
#      self-reap. Now a task with no live waitable parent self-reaps to
#      STATE_FREE on exit.
#   2. PARENT-EXIT CHILD LEAK: when a parent exited it abandoned its
#      children. Now an exiting task reaps its already-zombie children
#      and reparents its still-live children to PID 1.
#
# This test spawns MANY more short-lived children than NTASKS in a
# single uninterrupted hamsh session and asserts the LAST one still
# runs (i.e. the slot pool recycled and never wedged).
#
# It drives the DEFAULT boot path (init -> rc.boot -> hamsh), exactly
# like scripts/test_hpm.sh, and uses scripts/_qemu_drive.sh so it
# adapts to boot-time jitter.

. "$(dirname "$0")/_build_lock.sh"
. "$(dirname "$0")/_qemu_drive.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf

echo "[test_spawn_loop] (1/3) Build userland + initramfs"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null 2>&1 || true
python3 scripts/build_initramfs.py >/dev/null

echo "[test_spawn_loop] (2/3) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal init/main.ad -o "$ELF" >/dev/null

LOG=$(mktemp /tmp/test-spawn-loop.XXXXXX.log)
trap 'rm -f "$LOG"' EXIT

# How many spawns to drive. NTASKS is 16; we drive comfortably past it
# (>20) so a single leaked slot per spawn would exhaust the table long
# before the last command. SPAWNS=24 leaves a wide margin.
SPAWNS=24

# Build the alternating "cmd delay" arg list:
#   /bin/hello       (a tiny external binary -> one sys_spawn each)
#   echo SPAWN_<n>   (an in-shell marker so we can prove iteration <n>
#                     was actually reached and the shell was still
#                     accepting commands at that point)
# A leak would surface as "command not found: /bin/hello" once the
# table filled — the assertions below check that NEVER happens and that
# the FINAL marker printed.
CMDS=()
n=1
while [ "$n" -le "$SPAWNS" ]; do
    CMDS+=( "/bin/hello" 1 )
    CMDS+=( "echo SPAWN_${n}" 1 )
    n=$((n + 1))
done
CMDS+=( "echo SPAWN_LOOP_DONE" 2 )
CMDS+=( "exit" 1 )

echo "[test_spawn_loop] (3/3) Boot QEMU + drive ${SPAWNS} sequential spawns"
set +e
qemu_drive "$LOG" "$ELF" "[hamsh] M16.35 shell ready" 180 \
    -- "${CMDS[@]}"
rc="$QEMU_DRIVE_RC"
set -e

echo "[test_spawn_loop] --- captured output (filtered) ---"
grep -a -E "/hello\]|SPAWN_|command not found|out of tasks|no free task slot" "$LOG" \
    | sed 's/\x1b\[[0-9;]*[a-zA-Z]//g' | tr -d '\000' | head -120
echo "[test_spawn_loop] --- end output ---"

fail=0

# 1. The shell came up.
if ! grep -a -F -q "[hamsh] M16.35 shell ready" "$LOG"; then
    echo "[test_spawn_loop] FAIL: hamsh never reached the interactive loop"
    exit 1
fi

# Command OUTPUT lines only (drop the line-editor input echo, which
# carries a 'hamsh$' prompt prefix). See scripts/_hamsh_log.sh.
outlines() { grep -a -vE 'hamsh\$|\] > ' "$LOG" 2>/dev/null || true; }

# 2. The slot pool must NEVER have wedged: sys_spawn must never have
#    failed for lack of a free slot.
if outlines | grep -a -q "out of tasks"; then
    echo "[test_spawn_loop] FAIL: sys_spawn ran out of task slots (leak)"
    fail=1
else
    echo "[test_spawn_loop] OK: no 'spawn: out of tasks'"
fi

# 3. /bin/hello must never have been reported as not-found (that is how
#    hamsh surfaces a sys_spawn -1).
if outlines | grep -a -q "command not found"; then
    echo "[test_spawn_loop] FAIL: a spawn was reported 'command not found' (slot exhaustion)"
    fail=1
else
    echo "[test_spawn_loop] OK: no 'command not found' for any spawn"
fi

# 4. /bin/hello actually ran many times (its banner is unique). The
#    external /bin/hello is user/hello.S, whose only output line is the
#    "[/hello] hello from a second ELF ..." banner — one per successful
#    sys_spawn. (Counting the banner, not an exit-code line, because
#    hello.S exits with a stale rdi=1 status that is irrelevant here.)
hello_runs=$(outlines | grep -a -c "/hello\] hello")
echo "[test_spawn_loop] /bin/hello ran ${hello_runs} times"
if [ "${hello_runs:-0}" -ge "$SPAWNS" ]; then
    echo "[test_spawn_loop] OK: all ${SPAWNS} spawns completed"
else
    echo "[test_spawn_loop] FAIL: only ${hello_runs}/${SPAWNS} spawns completed"
    fail=1
fi

# 5. The shell was still alive AND accepting commands after the LAST
#    spawn — the late marker proves the table recycled, not just that
#    the first few spawns worked.
if outlines | grep -a -q "SPAWN_${SPAWNS}\b"; then
    echo "[test_spawn_loop] OK: reached SPAWN_${SPAWNS} (well past NTASKS)"
else
    echo "[test_spawn_loop] FAIL: never reached SPAWN_${SPAWNS} marker"
    fail=1
fi
if outlines | grep -a -q "SPAWN_LOOP_DONE"; then
    echo "[test_spawn_loop] OK: shell survived the whole spawn loop"
else
    echo "[test_spawn_loop] FAIL: SPAWN_LOOP_DONE absent — shell wedged"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_spawn_loop] FAIL (qemu rc=$rc)"
    exit 1
fi
echo "[test_spawn_loop] PASS (qemu rc=$rc)"
