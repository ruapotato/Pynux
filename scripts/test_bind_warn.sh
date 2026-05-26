#!/usr/bin/env bash
# scripts/test_bind_warn.sh — Phase 9 acceptance for the source-first
# bind flip + inversion warning (docs/rootfs_partition.md "Future
# direction — hamsh `bind` syntax — source first").
#
# Verifies:
#   1. The new source-first `bind SRC DST` order works — `bind '#s' /srv`
#      grafts the srv device onto /srv (visible in /proc/self/ns).
#   2. The inversion-warning fires for `bind /srv '#s'` (arg2 starts
#      with '#' and arg1 does not), printed to fd 2.
#   3. The warning does NOT refuse the call — the bind still goes
#      through with the args as typed.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf

bash scripts/build_user.sh >/dev/null
# Keep the normal init shim path — hamsh sources /etc/rc.boot, and
# we type our `bind` commands at the prompt after rc.boot finishes.
python3 scripts/build_initramfs.py >/dev/null
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal init/main.ad -o "$ELF" >/dev/null

LOG=$(mktemp /tmp/test-bind-warn.XXXXXX.log)
trap 'rm -f "$LOG"' EXIT

set +e
(
    sleep 3
    # Source-first form — no warning expected.
    printf "echo BW_FORWARD_BEGIN\n"
    sleep 1
    printf "bind '#s' /srv_alt\n"
    sleep 1
    printf "echo BW_FORWARD_END\n"
    sleep 1
    # Inverted form — warning expected on stderr.
    printf "echo BW_INVERTED_BEGIN\n"
    sleep 1
    printf "bind /srv_inv '#s'\n"
    sleep 1
    printf "echo BW_INVERTED_END\n"
    sleep 1
    # Both binds should appear in the ns dump.
    printf "cat /proc/self/ns\n"
    sleep 2
    printf "echo BW_DONE\n"
    sleep 1
    printf "exit\n"
    sleep 1
) | timeout 60s qemu-system-x86_64 \
    -kernel "$ELF" -smp 2 -nographic -no-reboot -m 256M \
    -monitor none -serial stdio > "$LOG" 2>&1
set -e

echo "[test_bind_warn] --- captured ---"
cat "$LOG"
echo "[test_bind_warn] --- end ---"

fail=0

# Inversion warning must appear when arg2 starts with '#' and arg1
# does not. Look for the well-known marker text from hamsh.ad's
# _hamsh_bind_warn helper.
if grep -F -q "[hamsh-bind] WARN: argument order looks inverted" "$LOG"; then
    echo "[test_bind_warn] OK: inversion warning fired for 'bind /srv_inv \"#s\"'"
else
    echo "[test_bind_warn] MISS: no inversion warning observed"
    fail=1
fi

# The forward (source-first) form must NOT trigger the warning. We
# need to verify the warning only fires for the inverted call by
# checking it appears AFTER the BW_INVERTED_BEGIN marker, not before.
if awk '/BW_FORWARD_BEGIN/,/BW_FORWARD_END/' "$LOG" \
        | grep -F -q "hamsh-bind"; then
    echo "[test_bind_warn] FAIL: warning fired on the source-first call"
    fail=1
else
    echo "[test_bind_warn] OK: source-first form did NOT trigger the warning"
fi

# The bind STILL went through despite the warning. Both /srv_alt and
# /srv_inv should appear in /proc/self/ns.
if grep -F -q "/srv_alt" "$LOG"; then
    echo "[test_bind_warn] OK: source-first bind reached /proc/self/ns"
else
    echo "[test_bind_warn] MISS: source-first bind not visible"
    fail=1
fi
if grep -F -q "/srv_inv" "$LOG"; then
    echo "[test_bind_warn] OK: warning did not refuse the call (inverted bind landed)"
else
    echo "[test_bind_warn] MISS: inverted bind missing — was it refused?"
    fail=1
fi

if [ $fail -ne 0 ]; then
    echo "[test_bind_warn] FAIL"
    exit 1
fi
echo "[test_bind_warn] PASS"
