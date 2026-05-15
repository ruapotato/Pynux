#!/usr/bin/env bash
# Build the minimal busybox initramfs for the Hamnix M1 QEMU dev loop.
#
# The initramfs auto-loads the kernel module, dumps dmesg, unloads it, and
# powers off — so QEMU output is fully scriptable. The /init script prints
# a "[PASS] m1-hello" line that the existing tests/qemu_runner.py output
# scraper already recognizes, plus a "[PYNUX-M1-DONE]" sentinel.
#
# Usage: make_initramfs.sh <module.ko> [<module.ko> ...]
#
# Output: build/initramfs.cpio.gz
#
# Env overrides:
#   BUSYBOX_VERSION   busybox release to build static  (default: 1.36.1)
#   PYNUX_KERNEL_DIR  cache dir for the busybox build  (default: ~/hamnix-kernel)
set -euo pipefail

if [ "$#" -lt 1 ]; then
    echo "usage: make_initramfs.sh <module.ko> [<module.ko> ...]" >&2
    exit 2
fi

BUSYBOX_VERSION="${BUSYBOX_VERSION:-1.36.1}"
PYNUX_KERNEL_DIR="${PYNUX_KERNEL_DIR:-$HOME/hamnix-kernel}"
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="$PROJ_ROOT/build"
BB_SRC="$PYNUX_KERNEL_DIR/busybox-${BUSYBOX_VERSION}"
BB_BIN="$BB_SRC/busybox"

# Resolve module paths to absolute up front — we cd into the busybox build
# dir below and the relative paths from the caller would otherwise break.
KO_ABS=()
for ko in "$@"; do
    KO_ABS+=("$(readlink -f "$ko")")
done

mkdir -p "$PYNUX_KERNEL_DIR" "$BUILD_DIR"

# --- static busybox (cached) ------------------------------------------------
if [ ! -x "$BB_BIN" ]; then
    echo "[initramfs] building static busybox $BUSYBOX_VERSION"
    cd "$PYNUX_KERNEL_DIR"
    if [ ! -d "$BB_SRC" ]; then
        curl -fLO "https://busybox.net/downloads/busybox-${BUSYBOX_VERSION}.tar.bz2"
        tar -xf "busybox-${BUSYBOX_VERSION}.tar.bz2"
        rm -f "busybox-${BUSYBOX_VERSION}.tar.bz2"
    fi
    cd "$BB_SRC"
    make defconfig >/dev/null
    # Static link: the initramfs has no shared libraries.
    # Busybox has no scripts/config helper or olddefconfig target — edit
    # .config directly and let `make` consume it.
    sed -i 's/^# CONFIG_STATIC is not set/CONFIG_STATIC=y/' .config
    sed -i 's/^CONFIG_TC=y/# CONFIG_TC is not set/' .config  # avoid libtirpc dep
    yes "" | make oldconfig >/dev/null 2>&1 || true
    make -j"$(nproc)" >/dev/null
else
    echo "[initramfs] reusing cached busybox at $BB_BIN"
fi

# --- assemble the rootfs tree ----------------------------------------------
ROOT="$(mktemp -d)"
trap 'rm -rf "$ROOT"' EXIT

mkdir -p "$ROOT"/{bin,sbin,proc,sys,dev}
cp "$BB_BIN" "$ROOT/bin/busybox"
ln -s busybox "$ROOT/bin/sh"

for ko in "${KO_ABS[@]}"; do
    cp "$ko" "$ROOT/$(basename "$ko")"
done

cat > "$ROOT/init" <<'INIT'
#!/bin/sh
/bin/busybox --install -s /bin
mount -t proc proc /proc
mount -t sysfs sysfs /sys

echo "[PYNUX] loading kernel module(s)"
# If a Hamnix virtio-blk module is about to load, unbind the kernel's
# built-in virtio_blk first so our driver can claim the device.
if ls /m4_virtio_blk.ko >/dev/null 2>&1; then
    for d in /sys/bus/virtio/drivers/virtio_blk/virtio*; do
        [ -e "$d" ] || continue
        name=$(basename "$d")
        echo "[PYNUX] unbinding $name from kernel virtio_blk"
        echo "$name" > /sys/bus/virtio/drivers/virtio_blk/unbind
    done
fi
if ls /m4_virtio_net.ko >/dev/null 2>&1; then
    for d in /sys/bus/virtio/drivers/virtio_net/virtio*; do
        [ -e "$d" ] || continue
        name=$(basename "$d")
        echo "[PYNUX] unbinding $name from kernel virtio_net"
        echo "$name" > /sys/bus/virtio/drivers/virtio_net/unbind
    done
fi
for ko in /*.ko; do
    echo "[PYNUX] insmod $ko"
    insmod "$ko"
done

echo "[PYNUX] --- dmesg tail ---"
dmesg | tail -n 20
echo "[PYNUX] --- end dmesg ---"

echo "[PYNUX] --- /proc/consoles ---"
cat /proc/consoles
echo "[PYNUX] --- end consoles ---"

if [ -e /proc/hamnix/state ]; then
    echo "[PYNUX] --- /proc/hamnix/state ---"
    cat /proc/hamnix/state
    echo "[PYNUX] --- end /proc/hamnix/state ---"
fi

echo "[PYNUX] --- /proc/partitions ---"
cat /proc/partitions
echo "[PYNUX] --- end /proc/partitions ---"

if ls /m11_debugfs.ko >/dev/null 2>&1; then
    mount -t debugfs none /sys/kernel/debug 2>&1 | head -1
    if [ -e /sys/kernel/debug/hamnix/counter ]; then
        initial=$(cat /sys/kernel/debug/hamnix/counter)
        echo "[PYNUX] dfs initial = $initial"
        echo 123 > /sys/kernel/debug/hamnix/counter
        echo "[PYNUX] dfs after write = $(cat /sys/kernel/debug/hamnix/counter)"
    fi
fi

if ls /m5_netfilter.ko >/dev/null 2>&1 || ls /m12_nfdump.ko >/dev/null 2>&1; then
    echo "[PYNUX] --- exercise netfilter hook ---"
    ifconfig eth0 10.0.2.15 up 2>&1 | head -2
    ping -c 2 -W 1 10.0.2.2 2>&1 | grep -E "transmitted|received" | head -1
    echo "[PYNUX] --- end netfilter ---"
fi

if ls /m8_netdev.ko >/dev/null 2>&1; then
    echo "[PYNUX] --- m8 netdev ---"
    # Hamnix device gets the next free ethN slot after eth0=virtio-net.
    ifconfig eth1 192.168.99.1 netmask 255.255.255.0 up 2>&1 | head -2
    ifconfig eth1 2>&1 | head -3
    echo "[PYNUX] --- end netdev ---"
fi

if [ -d /sys/hamnix ]; then
    echo "[PYNUX] --- /sys/hamnix/info ---"
    cat /sys/hamnix/info
    echo "[PYNUX] --- end /sys/hamnix/info ---"
fi

if grep -qE '^[ 0-9]*241 pynurand$' /proc/devices 2>/dev/null; then
    echo "[PYNUX] --- exercise /dev/pynurand ---"
    mknod /dev/pynurand c 241 0
    bytes=$(dd if=/dev/pynurand bs=8 count=1 2>/dev/null | wc -c)
    if [ "$bytes" = "8" ]; then
        echo "[PYNUX] random ok"
    else
        echo "[PYNUX] random FAILED (got $bytes bytes)"
    fi
    rm -f /dev/pynurand
fi

if grep -qE '^[ 0-9]*243 hamnixnull$' /proc/devices 2>/dev/null; then
    echo "[PYNUX] --- exercise /dev/hamnixnull ---"
    mknod /dev/hamnixnull c 243 0
    # busybox echo without -n adds \n, so "hello\n" = 6 bytes
    printf '%s' "hello" > /dev/hamnixnull
    eof_bytes=$(dd if=/dev/hamnixnull bs=64 count=1 2>/dev/null | wc -c)
    if [ "$eof_bytes" = "0" ]; then
        echo "[PYNUX] null ok"
    else
        echo "[PYNUX] null FAILED ($eof_bytes bytes from read)"
    fi
    rm -f /dev/hamnixnull
fi

if grep -qE '^[ 0-9]*242 hamnixzero$' /proc/devices 2>/dev/null; then
    echo "[PYNUX] --- exercise /dev/hamnixzero ---"
    mknod /dev/hamnixzero c 242 0
    nonzero=$(dd if=/dev/hamnixzero bs=1024 count=1 2>/dev/null | tr -d '\0' | wc -c)
    if [ "$nonzero" = "0" ]; then
        echo "[PYNUX] zero ok"
    else
        echo "[PYNUX] zero FAILED ($nonzero non-zero bytes)"
    fi
    rm -f /dev/hamnixzero
fi

if grep -qE '^[ 0-9]*240 hamnix$' /proc/devices 2>/dev/null; then
    echo "[PYNUX] --- exercise /dev/hamnix ---"
    mknod /dev/hamnix c 240 0
    echo "[PYNUX] cat /dev/hamnix:"
    cat /dev/hamnix
    echo "[PYNUX] echo > /dev/hamnix:"
    echo "testdata" > /dev/hamnix && echo "[PYNUX] write ok"
    rm -f /dev/hamnix
    echo "[PYNUX] --- end /dev/hamnix ---"
fi

if grep -q hamnixfs /proc/filesystems 2>/dev/null; then
    echo "[PYNUX] --- exercise hamnixfs ---"
    mkdir -p /mnt/hamnixfs
    if mount -t hamnixfs none /mnt/hamnixfs; then
        echo "[PYNUX] mount ok"

        # File create + write + read.
        if echo "hello from hamnixfs" > /mnt/hamnixfs/greeting; then
            echo "[PYNUX] write ok"
        else
            echo "[PYNUX] write FAILED"
        fi
        if [ -f /mnt/hamnixfs/greeting ]; then
            echo "[PYNUX] file exists"
        fi
        read_back=$(cat /mnt/hamnixfs/greeting 2>/dev/null)
        if [ "$read_back" = "hello from hamnixfs" ]; then
            echo "[PYNUX] read ok: $read_back"
        else
            echo "[PYNUX] read FAILED: got '$read_back'"
        fi

        # Directory create + remove.
        if mkdir /mnt/hamnixfs/subdir; then
            echo "[PYNUX] mkdir ok"
        else
            echo "[PYNUX] mkdir FAILED"
        fi
        echo "[PYNUX] ls /mnt/hamnixfs:"
        ls -la /mnt/hamnixfs

        # Cleanup.
        rm /mnt/hamnixfs/greeting && echo "[PYNUX] rm ok"
        rmdir /mnt/hamnixfs/subdir && echo "[PYNUX] rmdir ok"

        umount /mnt/hamnixfs && echo "[PYNUX] umount ok"
    else
        echo "[PYNUX] mount FAILED"
    fi
    echo "[PYNUX] --- end exercise hamnixfs ---"
fi

for ko in /*.ko; do
    name=$(basename "$ko" .ko)
    echo "[PYNUX] rmmod $name"
    rmmod "$name"
done

echo "[PYNUX-DONE]"
poweroff -f
INIT
chmod +x "$ROOT/init"

# --- pack -------------------------------------------------------------------
OUT="$BUILD_DIR/initramfs.cpio.gz"
( cd "$ROOT" && find . -print0 | cpio --null -o -H newc 2>/dev/null ) \
    | gzip -9 > "$OUT"

echo "[initramfs] wrote $OUT"
