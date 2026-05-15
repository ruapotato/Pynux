#!/usr/bin/env bash
# scripts/build_modules.sh - assemble + link Pynux kernel modules.
#
# Each mod/*.S becomes build/mod/<name>.elf; scripts/build_initramfs.py
# embeds them as /<name> entries (with the kmod_ prefix preserved) so
# the kernel's module_load() can fetch them by path at boot.

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

mkdir -p build/mod

build_one() {
    local name="$1"
    as --32 -o "build/mod/${name}.o" "mod/${name}.S"
    ld -m elf_i386 -nostdlib -static \
       -T mod/module.lds \
       -o "build/mod/${name}.elf" \
       "build/mod/${name}.o"
    echo "[build_modules] wrote build/mod/${name}.elf"
}

build_one kmod_hello
