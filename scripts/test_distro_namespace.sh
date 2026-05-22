#!/usr/bin/env bash
# scripts/test_distro_namespace.sh - distro-shape namespace regression.
#
# The bespoke `distrorun` launcher is RETIRED (HAMSH_SPEC §0: one
# primitive, many skins — no special container command). Running a
# binary in a distro-shape namespace is now plain namespace verbs:
#
#   * /etc/rc.boot defines the Linux runtime namespace as a captured
#     `ns { }` value named `linuxruntime` — the distro-shape recipe
#     (graft /etc, /usr, /lib, /lib64, /var onto the backing tree
#     /var/lib/distros/default/). It is a TEMPLATE (HAMSH_SPEC §11).
#   * `enter linuxruntime { <cmd> }` forks a child, applies a fresh
#     COW instance of the template, runs the command, blocks for it.
#
# This test boots via the DEFAULT /init shim (so /etc/rc.boot runs and
# `linuxruntime` is defined), then proves the architectural shape of
# distro-shape namespaces end-to-end on Phase C's rfork/bind/mount:
#
#   1. rc.boot defined the `linuxruntime` namespace value.
#   2. `enter linuxruntime { /bin/cat /etc/debian_version }` reads
#      /etc/debian_version from the distro backing
#      (/var/lib/distros/default/etc/debian_version = "12.4") — the
#      ns-template's bind grafted the distro tree into the child's
#      view.
#   3. From OUTSIDE the namespace (hamsh's own view, unaffected by
#      the enter child's rfork), /etc/debian_version still reads
#      Hamnix's native value ("hamnix/0.1") — the namespace mutation
#      is per-task, not global.
#   4. `enter linuxruntime { ... } && echo CHAIN_OK` — the §11
#      namespace verbs chain with && / || like any other command.
#
# Test backing fixture is tests/distros/default/ (etc/debian_version =
# "12.4"). build_initramfs.py walks tests/distros/* and embeds each
# file at /var/lib/distros/<name>/<rel>.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf

echo "[test_distro_namespace] (1/4) Build userland (hamsh + coreutils)"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

echo "[test_distro_namespace] (2/4) Plant default /init shim + " \
     "/var/lib/distros/default/* fixture"
# Default /init = the shim — it execs hamsh with /etc/rc.boot, which
# defines the `linuxruntime` namespace value. No INIT_ELF override.
python3 scripts/build_initramfs.py >/dev/null

echo "[test_distro_namespace] (3/4) Rebuild kernel image"
mkdir -p build
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

echo "[test_distro_namespace] (4/4) Boot QEMU + drive via hamsh"
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

# In-VM script: drive hamsh through (a) native read of
# /etc/debian_version, (b) an `enter linuxruntime { cat ... }` read
# inside the rc-defined namespace, (c) a SECOND native read AFTER the
# enter returns, (d) an `enter ... && echo` chain. `enter` launches
# /bin/cat inside the namespace, which reads /etc/debian_version.
# Inside, the ns-template's bind makes that resolve to
# /var/lib/distros/default/etc/debian_version ("12.4"). Outside,
# hamsh's namespace is unaffected (enter rfork's a child), so the
# native read after enter still sees Hamnix's "hamnix/0.1".
set +e
(
    sleep 4
    # 1) Baseline native read (before any enter).
    printf '/bin/echo BANNER-NATIVE-PRE\n'
    sleep 1
    printf '/bin/cat /etc/debian_version\n'
    sleep 1
    # 2) Namespaced read via `enter linuxruntime`.
    printf '/bin/echo BANNER-RUNTIME\n'
    sleep 1
    printf 'enter linuxruntime {\n/bin/cat /etc/debian_version\n}\n'
    sleep 3
    # 3) Native read AFTER the entered child returned — proves
    # hamsh's namespace is untouched.
    printf '/bin/echo BANNER-NATIVE-POST\n'
    sleep 1
    printf '/bin/cat /etc/debian_version\n'
    sleep 1
    # 4) The §11 namespace verbs chain with && like any command.
    printf 'enter linuxruntime { /bin/true } && /bin/echo CHAIN_OK\n'
    sleep 3
    printf 'exit\n'
    sleep 1
) | timeout 40s qemu-system-x86_64 \
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

echo "[test_distro_namespace] --- captured output ---"
cat "$LOG"
echo "[test_distro_namespace] --- end output ---"

fail=0

# 1. rc.boot defined the Linux runtime namespace value.
if grep -F -q "rc.boot: linux runtime namespace defined" "$LOG"; then
    echo "[test_distro_namespace] OK: rc.boot defined the linuxruntime ns value"
else
    echo "[test_distro_namespace] MISS: rc.boot did not define linuxruntime"
    fail=1
fi

# Helper: assert that VALUE appears in the captured log somewhere
# within the 20 lines following the BANNER marker. `[atkbd-diag]`
# periodic kernel keyboard-poll lines are skipped — they are neither
# program output nor window-consuming.
assert_banner_value() {
    local banner="$1"
    local value="$2"
    local label="$3"
    if awk -v b="$banner" -v v="$value" '
        BEGIN { armed=0; win=0; found=0 }
        index($0, "[atkbd-diag]") > 0 { next }
        index($0, b) > 0 { armed=1; win=0; next }
        armed { win++ ; if (index($0, v) > 0) { found=1; exit }
                if (win > 20) armed=0 }
        END { exit found ? 0 : 1 }
    ' "$LOG"; then
        echo "[test_distro_namespace] OK: $label"
    else
        echo "[test_distro_namespace] MISS: $label" \
             "(banner='$banner' value='$value')"
        fail=1
    fi
}

# 2. Inside the namespace, /etc/debian_version came from the default
#    distro backing ("12.4").
assert_banner_value "BANNER-RUNTIME" "12.4" \
    "enter linuxruntime: /etc/debian_version reads distro backing"

# 3. Outside the namespace (hamsh's own view), /etc/debian_version
#    still reads Hamnix's native value. Both the pre- and post-enter
#    reads — the post one is the real boundary test (proves the
#    enter child's rfork didn't bleed into hamsh's namespace).
assert_banner_value "BANNER-NATIVE-PRE" "hamnix/0.1" \
    "pre-enter native /etc/debian_version reads Hamnix"
assert_banner_value "BANNER-NATIVE-POST" "hamnix/0.1" \
    "post-enter native /etc/debian_version still reads Hamnix"

# 4. The namespace verb chained with && (HAMSH_SPEC §11).
if grep -F -q "CHAIN_OK" "$LOG"; then
    echo "[test_distro_namespace] OK: enter linuxruntime { } && echo chains"
else
    echo "[test_distro_namespace] MISS: enter did not chain with &&"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_distro_namespace] FAIL (qemu rc=$rc)"
    exit 1
fi

echo "[test_distro_namespace] PASS"
