#!/usr/bin/env bash
# scripts/test_named_stack.sh — Phase 9 acceptance for the named
# file-server stack (docs/rootfs_partition.md "Future direction —
# Stack semantics" + "Inspection: /proc/fs").
#
# The full bind-freeze + hot-plug story needs:
#   * Two partitions both sentinel-declaring `home` (we'd need to
#     build a custom multi-partition disk image for this).
#   * A way to push/pop entries from the test rig (the block layer
#     does not yet emit unplug events).
#
# Until the multi-partition fixture lands, this test exercises the
# pieces we CAN reach from a normal boot:
#
#   1. The boot rootfs is sentinel-declared as `distro` — verify
#      /proc/fs/by-name/distro returns a non-empty stack with the
#      partuuid + sentinel + dir fields populated.
#   2. `bind '#distro' /n/distros` (from rc.boot) snapshots the
#      named-stack top at bind time — the binding shows up in
#      /proc/self/ns and stays put (bind-freeze).
#   3. /proc/fs/by-name/<unknown> returns an empty-stack line, not
#      ENOENT — the readout is always idempotent.
#
# The two-partitions-pushing-the-same-name scenario gates on a
# kernel-side debug hook (sysfile that calls name_push with caller-
# supplied args) which is not in scope for the FS-discovery pass.
# This test asserts the visible part of the contract.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf
ROOTFS_IMG=build/hamnix-rootfs.img

bash scripts/build_user.sh >/dev/null
INIT_ELF="$HAMSH_ELF" python3 scripts/build_initramfs.py >/dev/null
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal init/main.ad -o "$ELF" >/dev/null
# Need the rootfs image for the named-stack to have something to
# discover (its `.hamnix-roots` sentinel declares `distro`).
python3 scripts/build_rootfs_img.py >/dev/null

LOG=$(mktemp /tmp/test-named-stack.XXXXXX.log)
trap 'rm -f "$LOG"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null' EXIT

set +e
(
    sleep 3
    printf "echo NS_DISTRO_BEGIN\n"
    sleep 1
    printf "cat /proc/fs/by-name/distro\n"
    sleep 1
    printf "echo NS_DISTRO_END\n"
    sleep 1
    # /proc/fs/by-name/<unknown-word> must return a graceful empty
    # readout, not ENOENT.
    printf "echo NS_UNKNOWN_BEGIN\n"
    sleep 1
    printf "cat /proc/fs/by-name/nopartition\n"
    sleep 1
    printf "echo NS_UNKNOWN_END\n"
    sleep 1
    # bind-freeze: rc.boot already did `bind '#distro' /n/distros`.
    # Verify the binding is in /proc/self/ns.
    printf "echo NS_FREEZE_BEGIN\n"
    sleep 1
    printf "cat /proc/self/ns\n"
    sleep 1
    printf "echo NS_FREEZE_END\n"
    sleep 1
    printf "echo NS_DONE\n"
    sleep 1
    printf "exit\n"
    sleep 1
) | timeout 60s qemu-system-x86_64 \
    -kernel "$ELF" -smp 2 -nographic -no-reboot -m 256M \
    -monitor none -serial stdio \
    -drive file="$ROOTFS_IMG",if=virtio,format=raw \
    > "$LOG" 2>&1
set -e

echo "[test_named_stack] --- captured ---"
cat "$LOG"
echo "[test_named_stack] --- end ---"

fail=0

# /proc/fs/by-name/distro must include the partuuid + sentinel + dir
# fields. The sentinel value should be `distro` (from build_rootfs_img.py).
distro_block=$(awk '/NS_DISTRO_BEGIN/,/NS_DISTRO_END/' "$LOG")
if echo "$distro_block" | grep -E -q 'partuuid='; then
    echo "[test_named_stack] OK: /proc/fs/by-name/distro renders partuuid"
else
    echo "[test_named_stack] MISS: distro stack missing partuuid"
    fail=1
fi
if echo "$distro_block" | grep -F -q "sentinel=\`distro\`"; then
    echo "[test_named_stack] OK: sentinel field carries the declared word"
else
    echo "[test_named_stack] MISS: sentinel word not rendered"
    fail=1
fi

# /proc/fs/by-name/<unknown> renders a graceful "(no stack ...)" line.
unknown_block=$(awk '/NS_UNKNOWN_BEGIN/,/NS_UNKNOWN_END/' "$LOG")
if echo "$unknown_block" | grep -F -q "no stack"; then
    echo "[test_named_stack] OK: unknown name produces graceful readout"
else
    echo "[test_named_stack] MISS: unknown name didn't render gracefully"
    fail=1
fi

# bind-freeze: the rc.boot `bind '#distro' /n/distros` must be present
# in /proc/self/ns (this verifies the bind actually went through and
# the path is now reachable; the LIFO-stack-mutation aspect of the
# freeze contract gates on the multi-partition fixture mentioned in
# the header).
freeze_block=$(awk '/NS_FREEZE_BEGIN/,/NS_FREEZE_END/' "$LOG")
if echo "$freeze_block" | grep -F -q "/n/distros"; then
    echo "[test_named_stack] OK: bind '#distro' /n/distros visible in ns"
else
    echo "[test_named_stack] MISS: distro bind not in /proc/self/ns"
    fail=1
fi

if [ $fail -ne 0 ]; then
    echo "[test_named_stack] FAIL"
    exit 1
fi
echo "[test_named_stack] PASS"
