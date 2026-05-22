#!/usr/bin/env bash
# tests/distros/debian-minbase/BUILD.sh — host-side, one-time:
# populate ./rootfs/ with a real Debian minbase rootfs suitable for
# Hamnix's distro-shape namespace mechanism (docs/distro-namespaces.md).
#
# After running this, the tree at
#   tests/distros/debian-minbase/rootfs/
# contains real Debian binaries (/bin/true, /bin/cat, /bin/bash, ...)
# and shared objects (/lib/x86_64-linux-gnu/libc.so.6,
# /lib64/ld-linux-x86-64.so.2). scripts/build_initramfs.py, when invoked
# with HAMNIX_EMBED_DEBIAN=1, embeds that tree at
#   /var/lib/distros/debian-minbase/<rel>
# in the cpio archive so that an `ns { bind /etc ... }` value can
# splice it into a privatised Layer-1 namespace — `enter <that-ns>
# { ... }` then exec's real Linux binaries inside.
#
# Requirements (Debian/Ubuntu host):
#   sudo apt install debootstrap
#   ~150 MB free disk + working network
#
# This is NOT run as part of the kernel build. It's a one-time host-
# side population step. The actual rootfs/ tree is gitignored (see
# top-level .gitignore); only this script + MANIFEST.txt + HOWTO.md
# live in git.
#
# Usage:
#   bash tests/distros/debian-minbase/BUILD.sh
#
# Idempotent: refuses to clobber an existing rootfs/. Delete the
# directory by hand if you want to re-run.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOTFS="${HERE}/rootfs"

if [ -e "${ROOTFS}" ]; then
    echo "BUILD.sh: ${ROOTFS} already exists; remove it first to re-run."
    echo "  sudo rm -rf '${ROOTFS}'"
    exit 1
fi

# debootstrap lives in /usr/sbin on Debian; non-root shells often have
# /usr/sbin missing from PATH, so widen the search before bailing out.
PATH="/usr/sbin:/sbin:${PATH}"
if ! command -v debootstrap >/dev/null 2>&1; then
    echo "BUILD.sh: debootstrap not installed."
    echo "  sudo apt install debootstrap"
    exit 1
fi

# --variant=minbase: skip recommended packages, ship only the Essential
# + Required priority set + whatever --include adds. ~80-150 MB on disk.
# stable: the current Debian stable release tag (resolves through the
# mirror). bash + coreutils are explicit because the distro-shape
# namespace test wants /bin/bash + /bin/true + /bin/cat verifiable
# inside the namespace; coreutils ships true/false/cat/echo/ls etc.
echo "BUILD.sh: running debootstrap (this takes 2-5 minutes)..."
sudo debootstrap --variant=minbase --include=bash,coreutils \
    stable "${ROOTFS}" http://deb.debian.org/debian

# Make the tree readable by the unprivileged user that built it so
# build_initramfs.py can rglob through without sudo.
sudo chown -R "$(id -u):$(id -g)" "${ROOTFS}"

SIZE="$(du -sh "${ROOTFS}" | cut -f1)"
echo "BUILD.sh: rootfs ready at ${ROOTFS} (${SIZE})"
echo "BUILD.sh: key binaries:"
for f in /bin/true /bin/false /bin/cat /bin/bash \
         /lib/x86_64-linux-gnu/libc.so.6 \
         /lib64/ld-linux-x86-64.so.2 \
         /etc/debian_version /etc/os-release; do
    if [ -e "${ROOTFS}${f}" ]; then
        echo "  OK  ${f}"
    else
        echo "  MISS ${f}"
    fi
done
echo
echo "Next: HAMNIX_EMBED_DEBIAN=1 INIT_ELF=build/user/hamsh.elf \\"
echo "        python3 scripts/build_initramfs.py"
echo "      bash scripts/test_distro_debian.sh"
