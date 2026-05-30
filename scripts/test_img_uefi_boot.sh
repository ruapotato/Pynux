#!/usr/bin/env bash
# scripts/test_img_uefi_boot.sh — ACCEPTANCE GATE for the installed-system
# raw disk image build/hamnix.img.
#
# Boots build/hamnix.img under OVMF (UEFI) as a DISK (not a cdrom) via
# virtio-blk, exactly the way a shipped Hamnix install boots, and proves
# the whole cpio-less ext4-root path end-to-end:
#
#   OVMF firmware
#     -> reads GPT, finds the ESP (partition 1, FAT)
#     -> launches \EFI\BOOT\BOOTX64.EFI (native PE/COFF stub)
#     -> stub loads \hamnix-kernel.elf off the ESP and jumps to the kernel
#     -> kernel probes virtio-blk, scans GPT, finds the ext4 partition by
#        its 0xEF53 superblock magic, reads .hamnix-roots, binds
#        #sysroot at /, ELF-loads /init OFF EXT4
#     -> /init execs /bin/hamsh /etc/rc.boot (both off ext4) -> shell
#
# Asserts, IN ORDER:
#   1. kernel banner          ("Hamnix kernel booting")
#   2. shell-ready marker     ("handing off to interactive shell")
#   3. a typed command resolves OFF EXT4: `ls /bin` + `cat /version`
#      list the native toolset AND there is ZERO "command not found".
#
# SKIPS CLEANLY (exit 0) when /dev/kvm or OVMF firmware is unavailable.
#
# Env overrides:
#   HAMNIX_IMG         image path                (default: build/hamnix.img)
#   OVMF_FD            OVMF firmware path        (default: auto-resolved)
#   SHELL_BOOT_WAIT    seconds to wait for the   (default: 90)
#                      interactive-prompt marker
#   HAMNIX_SKIP_BUILD  1 = reuse existing image  (default: rebuild)

set -uo pipefail

PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

# shellcheck source=_build_lock.sh
source "$PROJ_ROOT/scripts/_build_lock.sh"

HAMNIX_IMG="${HAMNIX_IMG:-build/hamnix.img}"
SHELL_BOOT_WAIT="${SHELL_BOOT_WAIT:-90}"
KERNEL_BANNER="Hamnix kernel booting"
# rc.boot.full's final line before the interactive REPL.
PROMPT_MARKER="handing off to interactive shell"

# --- environment gates (skip cleanly) ---------------------------------
if [ ! -e /dev/kvm ]; then
    echo "[test_img_uefi] SKIP: /dev/kvm absent (KVM required; boot too slow without it)" >&2
    exit 0
fi

# OVMF resolution: prefer the Debian-style single-file /usr/share/ovmf/
# OVMF.fd; fall back to the split /usr/share/OVMF/OVMF_CODE*.fd packaging.
OVMF_FD="${OVMF_FD:-}"
if [ -z "$OVMF_FD" ]; then
    if [ -f /usr/share/ovmf/OVMF.fd ]; then
        OVMF_FD=/usr/share/ovmf/OVMF.fd
    elif [ -f /usr/share/OVMF/OVMF_CODE.fd ]; then
        OVMF_FD=/usr/share/OVMF/OVMF_CODE.fd
    elif [ -f /usr/share/OVMF/OVMF_CODE_4M.fd ]; then
        OVMF_FD=/usr/share/OVMF/OVMF_CODE_4M.fd
    fi
fi
if [ -z "$OVMF_FD" ] || [ ! -f "$OVMF_FD" ]; then
    echo "[test_img_uefi] SKIP: OVMF firmware not found (tried /usr/share/ovmf/OVMF.fd and /usr/share/OVMF/OVMF_CODE*.fd; apt install ovmf)" >&2
    exit 0
fi

# --- build the image --------------------------------------------------
if [ "${HAMNIX_SKIP_BUILD:-0}" != "1" ]; then
    echo "[test_img_uefi] building disk image via build_img.sh"
    rm -f "$HAMNIX_IMG"
    bash "$PROJ_ROOT/scripts/build_img.sh"
fi
if [ ! -f "$HAMNIX_IMG" ]; then
    echo "[test_img_uefi] FAIL: $HAMNIX_IMG missing after build_img.sh." >&2
    exit 1
fi

# Report the image + ext4 partition sizes (brief deliverable).
IMG_BYTES=$(stat -c%s "$HAMNIX_IMG")
echo "[test_img_uefi] image size: ${IMG_BYTES} bytes ($(( IMG_BYTES / 1024 / 1024 )) MiB)"
if [ -f build/hamnix-rootfs.img ]; then
    ROOTFS_BYTES=$(stat -c%s build/hamnix-rootfs.img)
    echo "[test_img_uefi] ext4 partition size: ${ROOTFS_BYTES} bytes ($(( ROOTFS_BYTES / 1024 / 1024 )) MiB)"
fi

# OVMF persists UEFI variables back into the firmware file, so it needs a
# writable copy. The image itself is also written to (UEFI varstore is
# separate; the disk is opened r/w by qemu) — copy it so a re-run starts
# from a pristine image.
OVMF_RW=$(mktemp --tmpdir hamnix-img-uefi.ovmf.XXXXXX.fd)
IMG_RW=$(mktemp --tmpdir hamnix-img-uefi.disk.XXXXXX.img)
LOG=$(mktemp --tmpdir hamnix-img-uefi.XXXXXX.log)
INFIFO=$(mktemp --tmpdir -u hamnix-img-uefi-in.XXXXXX)
cp "$OVMF_FD" "$OVMF_RW"
cp "$HAMNIX_IMG" "$IMG_RW"
mkfifo "$INFIFO"

cleanup() {
    [ -n "${QEMU_PID:-}" ] && kill "$QEMU_PID" 2>/dev/null
    rm -f "$OVMF_RW" "$IMG_RW" "$INFIFO"
}
trap cleanup EXIT

exec 4<>"$INFIFO"
exec 3>"$INFIFO"

# Boot the image as a DISK (not -cdrom) via virtio-blk, per the brief.
qemu-system-x86_64 \
    -enable-kvm -cpu host \
    -bios "$OVMF_RW" \
    -drive file="$IMG_RW",format=raw,if=virtio \
    -m 512M \
    -nographic -no-reboot -monitor none \
    -serial stdio \
    <&4 > "$LOG" 2>&1 &
QEMU_PID=$!

# --- wait for the interactive prompt ----------------------------------
echo "[test_img_uefi] waiting up to ${SHELL_BOOT_WAIT}s for prompt marker..."
booted=0
for _ in $(seq 1 "$SHELL_BOOT_WAIT"); do
    if grep -a -q "$PROMPT_MARKER" "$LOG"; then
        booted=1
        break
    fi
    if ! kill -0 "$QEMU_PID" 2>/dev/null; then
        echo "[test_img_uefi] FAIL: qemu exited before reaching the prompt." >&2
        echo "----- serial log tail -----" >&2
        tail -80 "$LOG" >&2
        exit 1
    fi
    sleep 1
done

if [ "$booted" -ne 1 ]; then
    echo "[test_img_uefi] FAIL: prompt marker '$PROMPT_MARKER' not seen in ${SHELL_BOOT_WAIT}s." >&2
    echo "----- serial log tail -----" >&2
    tail -80 "$LOG" >&2
    exit 1
fi
echo "[test_img_uefi] prompt reached; typing commands at the shell."

# The prompt MARKER printing is not the same as the shell being ready to
# read input: on first prompt hamsh runs a getty-style stale-input flush
# and the service supervisor/heartbeat settle. Typing the very first
# command at that instant races that startup and the keystrokes can be
# eaten (the bytes never reach the REPL). Give it a settle so the first
# command lands — the gap to readiness grows with initramfs size.
sleep 6

type_cmd() {
    printf '%s\n' "$1" >&3
    sleep 4
}

type_cmd "echo HAMNIX_IMG_REPL_OK"     # proves echo + the REPL live
type_cmd "ls /bin"                     # native toolset must list OFF EXT4
type_cmd "cat /version"                # a real tool, run OFF EXT4
type_cmd "echo HAMNIX_IMG_DONE_99"

sleep 3
kill "$QEMU_PID" 2>/dev/null
wait "$QEMU_PID" 2>/dev/null
exec 3>&-
exec 4>&-

# --- assertions -------------------------------------------------------
fail=0

# 1. Kernel banner (proves the EFI stub loaded + jumped into the kernel).
if grep -a -q "$KERNEL_BANNER" "$LOG"; then
    echo "[test_img_uefi] PASS: kernel banner ('$KERNEL_BANNER') present."
else
    echo "[test_img_uefi] FAIL: kernel banner ('$KERNEL_BANNER') NOT present — EFI stub did not reach the kernel." >&2
    fail=1
fi

# 2. Shell-ready marker (already matched above, but assert explicitly).
if grep -a -q "$PROMPT_MARKER" "$LOG"; then
    echo "[test_img_uefi] PASS: shell-ready marker ('$PROMPT_MARKER') present."
else
    echo "[test_img_uefi] FAIL: shell-ready marker ('$PROMPT_MARKER') NOT present." >&2
    fail=1
fi

# 3a. REPL alive.
if grep -a -q -E '^HAMNIX_IMG_REPL_OK' "$LOG"; then
    echo "[test_img_uefi] PASS: echo marker round-tripped (REPL alive)."
else
    echo "[test_img_uefi] FAIL: echo marker not echoed back (REPL dead)." >&2
    fail=1
fi

# 3b. THE KEYSTONE: zero 'command not found'. With the toolset on ext4
#     and the kernel-bound #sysroot at /, every typed command MUST
#     resolve off the partition. Any 'command not found' means the
#     ext4-root path is broken.
if grep -a -q "command not found" "$LOG"; then
    echo "[test_img_uefi] FAIL: 'command not found' present — commands do NOT resolve off ext4:" >&2
    grep -a "command not found" "$LOG" >&2
    fail=1
else
    echo "[test_img_uefi] PASS (KEYSTONE): zero 'command not found' — commands resolve off ext4."
fi

# 3c. `ls /bin` actually listed native tools off ext4. Require several
#     distinct tool names to appear — a real listing, not noise.
hits=0
for tool in whoami xargs uname uptime wget which; do
    if grep -a -q -E "(^|[[:space:]])${tool}([[:space:]]|\$)" "$LOG"; then
        hits=$((hits + 1))
    fi
done
if [ "$hits" -ge 4 ]; then
    echo "[test_img_uefi] PASS: ls /bin listed the native toolset off ext4 ($hits/6 probe tools present)."
else
    echo "[test_img_uefi] FAIL: ls /bin did not list the native toolset ($hits/6 probe tools) — ext4 /bin not resolving." >&2
    fail=1
fi

if [ "$fail" -eq 0 ]; then
    echo "[test_img_uefi] PASS"
    rm -f "$LOG"
    exit 0
else
    echo "[test_img_uefi] FAIL (serial log: $LOG)" >&2
    exit 1
fi
