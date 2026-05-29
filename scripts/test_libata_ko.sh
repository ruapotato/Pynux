#!/usr/bin/env bash
# scripts/test_libata_ko.sh — regression guard for the libata.ko harvest
# through the L-series loader. libata is Linux's GENERIC ATA/SATA layer:
# the ATA command set, the SCSI-to-ATA translator, port/link state
# machines and error recovery. It sits ABOVE the SCSI mid-layer
# (scsi_mod.ko) — each ATA port is registered as a SCSI host — and below
# libahci.ko / ahci.ko. Harvesting it proves Hamnix's module loader +
# linux_abi ABI can absorb a whole real Linux subsystem (ATA + SCSI),
# not just a single leaf driver.
#
# WHY A KERNEL-SIDE BOOT EXERCISE (not userspace `insmod`):
#   libata.ko's modinfo in this Debian 6.1.0-32 build carries NO
#   `depends:` line, so the modules.dep walker can't auto-pull libata's
#   real dependency (scsi_mod). The load order is load-bearing: scsi_mod
#   MUST register its 152-entry __ksymtab in the loader's cross-module
#   registry BEFORE libata's relocation pass, or libata's ~23 scsi_* /
#   sdev_* UND symbols hit the unresolved-external panic path. Driving
#   three ordered insmods over a piped hamsh stdin is timing-fragile
#   (the shell line-editor drops fast-typed lines). Instead the kernel's
#   boot:35.LAT path (init/main.ad, gated on /etc/libata-ko) does the
#   explicit ordered load: scsi_common -> scsi_mod -> libata. This test
#   plants that marker (ENABLE_LIBATA_KO=1) and asserts the serial log.
#
# Assertions (the harvest bar — "links + init runs", NOT block I/O):
#   1. `kmod_linux: name=scsi_mod`  — SCSI mid-layer located + parsed.
#   2. `kmod_linux: name=libata`    — harvest target located + parsed.
#   3. Every relocation pass reports `skipped=0` (no UND silently left).
#   4. scsi_mod init_module returned 0, libata init_module returned 0.
#   5. `[boot:35.LAT] libata.ko harvest OK`.
#   6. >=1 `[ksymtab_hit] libata -> scsi*` — the cross-module resolution
#      of libata's scsi_* UND against scsi_mod's real EXPORT_SYMBOL impls
#      (the whole point: libata links against the SCSI midlayer, not a
#      pile of linux_abi stubs).
#   7. No CPU traps / kernel BUGs / panics.
#
# SKIPs cleanly (exit 0) if qemu / grub-mkrescue prerequisites are
# absent so the suite stays green on a tooling-less host.

. "$(dirname "$0")/_build_lock.sh"

set -uo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
INIT_ELF=build/user/init.elf

# --- module presence (hard fail if the .ko files are missing) -------
for pair in \
    "kernel-modules/libata/libata.ko:200000" \
    "kernel-modules/scsi_mod/scsi_mod.ko:200000" \
    "kernel-modules/scsi_common/scsi_common.ko:2000"; do
    ko="${pair%%:*}"; min="${pair##*:}"
    sz=$(stat -c%s "$PROJ_ROOT/$ko" 2>/dev/null || echo 0)
    if [ "$sz" -lt "$min" ]; then
        echo "[test_libata_ko] FAIL: $ko missing or too small (${sz} bytes)"
        exit 1
    fi
    echo "[test_libata_ko] OK: $ko present (${sz} bytes)"
done

# --- gap diagnostic (informational, non-fatal) ----------------------
# libata's UND symbols not covered by either a linux_abi shim OR
# scsi_mod's EXPORT_SYMBOL surface. A non-empty list here means the
# harvest is genuinely incomplete (the boot exercise would then report
# unresolved-external). We expect 0 — the scsi_* UND resolve
# cross-module against scsi_mod.
UND_SYMS=$(nm -u "$PROJ_ROOT/kernel-modules/libata/libata.ko" 2>/dev/null \
           | awk '{print $2}' | sort -u)
SCSI_EXPORTS=$(nm "$PROJ_ROOT/kernel-modules/scsi_mod/scsi_mod.ko" 2>/dev/null \
               | awk '$2 ~ /^[TtDdRrWw]$/ {print $3}' | sort -u)
MISSING=""
for sym in $UND_SYMS; do
    grep -rq "_add_export(\"${sym}\"" linux_abi/ 2>/dev/null && continue
    echo "$SCSI_EXPORTS" | grep -qxF "$sym" && continue
    MISSING+=" $sym"
done
TOTAL_UND=$(echo "$UND_SYMS" | wc -w)
TOTAL_MISSING=$(echo "$MISSING" | wc -w)
echo "[test_libata_ko] libata UND total=$TOTAL_UND uncovered(shim+scsi)=$TOTAL_MISSING"
if [ -n "$MISSING" ]; then
    for s in $MISSING; do echo "  - $s"; done
fi

# --- prerequisite gate (clean SKIP) ---------------------------------
if ! command -v qemu-system-x86_64 >/dev/null 2>&1; then
    echo "[test_libata_ko] SKIP: qemu-system-x86_64 not available"
    exit 0
fi
if ! command -v grub-mkrescue >/dev/null 2>&1; then
    echo "[test_libata_ko] SKIP: grub-mkrescue not available (kernel is ELF64; needs the ISO shim)"
    exit 0
fi

echo "[test_libata_ko] (1/3) Build userland + modules + initramfs (libata marker)"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null
ENABLE_LIBATA_KO=1 INIT_ELF="$INIT_ELF" \
    python3 scripts/build_initramfs.py >/dev/null

echo "[test_libata_ko] (2/3) Rebuild kernel image"
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

if [ ! -s "$ELF" ]; then
    echo "[test_libata_ko] FAIL: kernel ELF missing"
    INIT_ELF="$INIT_ELF" python3 scripts/build_initramfs.py >/dev/null 2>&1 || true
    exit 1
fi
echo "[test_libata_ko] OK: kernel ELF built ($(stat -c%s "$ELF") bytes)"

echo "[test_libata_ko] (3/3) Boot QEMU; kernel-side boot:35.LAT drives the load"
LOG=$(mktemp)
# Restore the default initramfs on exit so a later test isn't surprised
# by the libata marker leaking into its image.
trap 'rm -f "$LOG"; INIT_ELF="'"$INIT_ELF"'" python3 scripts/build_initramfs.py >/dev/null 2>&1 || true' EXIT

# init.elf never exits, so qemu runs until the timeout. The boot:35.LAT
# exercise fires at ~boot:35 (well before the timeout); 45s is ample
# even on TCG. No stdin needed — the load is kernel-driven.
set +e
timeout 60s qemu-system-x86_64 \
    -kernel "$ELF" \
    -smp 2 -nographic -no-reboot -m 512M \
    -monitor none -serial stdio \
    < /dev/null > "$LOG" 2>&1
rc=$?
set -e
# rc=124 (timeout) is EXPECTED — init.elf is a long-running PID 1.
echo "[test_libata_ko] qemu exited rc=$rc (124=timeout, expected for long-running init)"
cp "$LOG" /tmp/test_libata_ko.last.log 2>/dev/null || true

echo "[test_libata_ko] --- captured (boot:35.LAT / kmod / ksymtab) ---"
grep -aE 'boot:35.LAT|kmod_linux: (name=(scsi_common|scsi_mod|libata)|relocations applied|init returned|no init|unresolved external|unknown reloc)' "$LOG" | head -40 || true
echo "[test_libata_ko] --- end ---"

fail=0

# 1. No traps / panics anywhere in the boot.
if grep -aE -q "PANIC|panic:|TRAP: vector|^TRAP:|#GP fault|#UD|Page Fault|invalid opcode|^BUG:" "$LOG"; then
    echo "[test_libata_ko] FAIL: TRAP / BUG / PANIC reported"
    grep -aE "PANIC|panic:|TRAP|#GP fault|#UD|Page Fault|invalid opcode|BUG:" "$LOG" | head -10
    fail=1
else
    echo "[test_libata_ko] OK: no traps/panics in boot log"
fi

# 2. No unresolved external symbol / unknown reloc anywhere.
if grep -aF -q "unresolved external symbol" "$LOG"; then
    echo "[test_libata_ko] FAIL: unresolved external symbol reported"
    grep -aF "unresolved external symbol" "$LOG" | head -20
    fail=1
else
    echo "[test_libata_ko] OK: no unresolved external symbols"
fi
if grep -aF -q "unknown reloc type" "$LOG"; then
    echo "[test_libata_ko] FAIL: unknown reloc type reported"
    grep -aF "unknown reloc type" "$LOG" | head
    fail=1
fi

# 3. scsi_mod.ko was located + parsed.
if grep -aE -q "kmod_linux: name=scsi_mod( |\$)" "$LOG"; then
    echo "[test_libata_ko] OK: kmod_linux: name=scsi_mod"
else
    echo "[test_libata_ko] FAIL: scsi_mod.ko not loaded (no name=scsi_mod marker)"
    fail=1
fi

# 4. libata.ko was located + parsed.
if grep -aE -q "kmod_linux: name=libata( |\$)" "$LOG"; then
    echo "[test_libata_ko] OK: kmod_linux: name=libata"
else
    echo "[test_libata_ko] FAIL: libata.ko not loaded (no name=libata marker)"
    fail=1
fi

# 5. Every relocation pass that fired resolved fully (skipped=0).
n_bad_skipped=$( { grep -aE "kmod_linux: relocations applied=" "$LOG" || true; } \
                | { grep -vE 'skipped=0' || true; } | wc -l)
if [ "$n_bad_skipped" -ne 0 ]; then
    echo "[test_libata_ko] FAIL: $n_bad_skipped relocation pass(es) had skipped>0"
    grep -aE "kmod_linux: relocations applied=" "$LOG" | grep -vE 'skipped=0' | head
    fail=1
else
    echo "[test_libata_ko] OK: every relocation pass resolved (skipped=0)"
fi

# 6. The harvest-OK marker fired (libata.ko load returned a valid slot).
if grep -aF -q "[boot:35.LAT] libata.ko harvest OK" "$LOG"; then
    echo "[test_libata_ko] OK: boot:35.LAT libata.ko harvest OK"
else
    echo "[test_libata_ko] FAIL: no '[boot:35.LAT] libata.ko harvest OK' marker"
    fail=1
fi

# 7. scsi_mod + libata init_module both returned 0. Slots are assigned
#    in load order; scsi_common is library-only (no init), so scsi_mod
#    takes a slot then libata the next. We just require >=2 distinct
#    'init returned 0' lines between name=scsi_mod and the harvest marker.
INIT_OK=$(awk '/kmod_linux: name=scsi_mod/,/libata\.ko harvest OK/' "$LOG" \
          | grep -acE "kmod_linux: init returned 0" || true)
INIT_OK=${INIT_OK:-0}
if [ "$INIT_OK" -ge 2 ]; then
    echo "[test_libata_ko] OK: scsi_mod + libata init_module returned 0 (count=$INIT_OK)"
else
    echo "[test_libata_ko] FAIL: expected >=2 'init returned 0' between scsi_mod and harvest OK (got $INIT_OK)"
    fail=1
fi

# 8. Cross-module resolution: libata's scsi_* UND linked against
#    scsi_mod's real EXPORT_SYMBOL impls, not linux_abi stubs.
KSYM_HITS=$(grep -acE "\[ksymtab_hit\] libata -> scsi" "$LOG" || true)
KSYM_HITS=${KSYM_HITS:-0}
if [ "$KSYM_HITS" -ge 1 ]; then
    echo "[test_libata_ko] OK: libata->scsi cross-module ksymtab hits=$KSYM_HITS"
else
    echo "[test_libata_ko] FAIL: no [ksymtab_hit] libata -> scsi* — scsi midlayer not cross-linked"
    fail=1
fi

if [ "$fail" -ne 0 ]; then
    echo "[test_libata_ko] FAIL"
    echo "[test_libata_ko] --- full log tail ---"
    tail -120 "$LOG"
    exit 1
fi

echo "[test_libata_ko] PASS (libata.ko + scsi_mod loaded; relocations clean; init returned 0; scsi cross-linked)"
