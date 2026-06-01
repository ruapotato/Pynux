#!/usr/bin/env bash
# scripts/test_selfhost_fixpoint.sh — the self-host CAPSTONE (#154):
# the stage1 == stage2 BYTE-IDENTICAL fixpoint.
#
# Definitions:
#   stage0 = the Python seed compiler (compiler/, codegen_x86.py).
#   stage1 = a RUNNABLE self-hosted COMPILER ELF, produced by compiling the
#            fused-with-driver compiler source (lexer + parser + codegen +
#            elf_emit + a driver `main`) with the EXISTING on-device
#            self-hosted compiler (codegen.ad), via scripts/hamnix-ac.
#   stage2 = the ELF produced by running stage1 ON-DEVICE (natively, CPL-3)
#            to compile the SAME fused-with-driver source.
#   FIXPOINT = stage1 and stage2 are BYTE-IDENTICAL.
#
# Why this is the fixpoint that matters: stage1 and stage2 are BOTH produced
# by the SAME backend pair (codegen.ad + elf_emit.ad) compiling the SAME
# source — one hop apart. stage1 was emitted by the on-device compiler
# running as bytes the PYTHON build laid down; stage2 was emitted by stage1
# itself running natively. If the two agree byte-for-byte, the self-hosted
# compiler reproduces ITSELF exactly: it is a faithful fixpoint, and the
# Adder-in-Adder codegen is deterministic and self-consistent across the
# Python-emitted -> self-emitted boundary.
#
# Pipeline:
#   (1) Fuse lexer+parser+codegen+elf_emit + driver-main into one runnable
#       compiler source (scripts/concat_compiler_source.py --with-driver).
#   (2) stage1: scripts/hamnix-ac compiles that source ON-DEVICE (the
#       existing self-hosted compiler) -> stage1.elf (a runnable compiler).
#   (3) stage2: stage stage1.elf as /bin/stage1 and the SAME fused source as
#       /src/input.ad, boot Hamnix, run /bin/stage1 natively at CPL-3,
#       capture the ELF it hex-dumps -> stage2.elf.
#   (4) Assert `cmp -s stage1.elf stage2.elf` — exact byte identity.
#
# PASS only on exact match. On divergence the test reports the first
# differing offset (cmp -l) so the encoding gap can be mapped back to a
# codegen.ad construct.

. "$(dirname "$0")/_build_lock.sh"

set -euo pipefail
PROJ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJ_ROOT"

ELF=build/hamnix-kernel.elf
HAMSH_ELF=build/user/hamsh.elf
FUSED=build/selfhost/fixpoint_compiler.ad
STAGE1=build/selfhost/stage1.elf
STAGE2=build/selfhost/stage2.elf
# stage1 staged as a /bin binary (build/user/*.elf -> /bin/<name>).
STAGE1_BIN=build/user/stage1.elf

mkdir -p build/selfhost

# --- (1/4) Fuse the runnable-compiler source -------------------------
echo "[fixpoint] (1/4) Fuse lexer+parser+codegen+elf_emit + driver main"
python3 scripts/concat_compiler_source.py --with-driver -o "$FUSED"
SRCLEN=$(wc -c < "$FUSED")
echo "[fixpoint] fused-with-driver source: ${SRCLEN} bytes"

# --- (2/4) stage1: on-device self-hosted compiler compiles it --------
# scripts/hamnix-ac boots Hamnix, has the on-device self-hosted compiler
# (codegen.ad) compile the fused source, and reconstructs the emitted ELF.
# The producer of stage1 is therefore the Adder-in-Adder backend, NOT the
# Python seed — so stage1 and stage2 share the SAME ELF emitter (elf_emit.ad)
# and the byte-identity comparison is meaningful.
echo "[fixpoint] (2/4) stage1: compile fused source ON-DEVICE -> $STAGE1"
rm -f "$STAGE1"
if ! bash scripts/hamnix-ac "$FUSED" -o "$STAGE1"; then
    echo "[fixpoint] FAIL: stage1 on-device compile did not succeed"
    exit 1
fi
if [ ! -s "$STAGE1" ]; then
    echo "[fixpoint] FAIL: $STAGE1 not produced"
    exit 1
fi
S1LEN=$(wc -c < "$STAGE1")
echo "[fixpoint] stage1.elf: ${S1LEN} bytes (a runnable self-hosted compiler)"

# --- (3/4) stage2: run stage1 natively over the SAME source ----------
# Stage stage1.elf at /bin/stage1 and the fused source at /src/input.ad,
# rebuild the kernel, boot, and run /bin/stage1. Its driver `main`
# open()+read()s /src/input.ad, runs lex->parse->codegen->elf_emit, and
# hex-dumps the emitted ELF between [hamnix_ac_emit] HEXBEGIN/HEXEND — the
# same sentinels hamnix-ac uses.
echo "[fixpoint] (3/4) stage2: run stage1 natively over the SAME source"
cp "$STAGE1" "$STAGE1_BIN"

echo "[fixpoint]   build userland + modules"
bash scripts/build_user.sh >/dev/null
bash scripts/build_modules.sh >/dev/null

FUSED_ABS="$(cd "$(dirname "$FUSED")" && pwd)/$(basename "$FUSED")"
echo "[fixpoint]   stage /bin/stage1 + /src/input.ad, build kernel"
INIT_ELF="$HAMSH_ELF" HAMNIX_AC_SRC="$FUSED_ABS" \
    python3 scripts/build_initramfs.py >/dev/null
python3 -m compiler.adder compile \
    --target=x86_64-bare-metal \
    init/main.ad \
    -o "$ELF" >/dev/null

# Restore the default initramfs + remove the staged stage1 binary on exit.
trap 'rm -f "'"$STAGE1_BIN"'"; INIT_ELF=build/user/init.elf python3 scripts/build_initramfs.py >/dev/null 2>&1 || true' EXIT

run_qemu() {
    local log="$1" cmd="$2" donere="$3"
    local fifo
    fifo=$(mktemp -u)
    mkfifo "$fifo"
    (
        exec 3>"$fifo"
        for _ in $(seq 1 600); do
            grep -q "shell ready" "$log" 2>/dev/null && break
            sleep 0.1
        done
        sleep 1
        printf '%s\n' "$cmd" >&3
        for _ in $(seq 1 1200); do
            grep -Eq "$donere" "$log" 2>/dev/null && break
            sleep 0.1
        done
        sleep 1
        printf 'exit\n' >&3
        sleep 1
        exec 3>&-
    ) &
    local driver_pid=$!
    timeout 240s qemu-system-x86_64 \
        -kernel "$ELF" \
        -smp 2 \
        -nographic \
        -no-reboot \
        -m 512M \
        -monitor none \
        -serial stdio \
        < "$fifo" \
        > "$log" 2>&1
    local rc=$?
    kill "$driver_pid" 2>/dev/null
    wait "$driver_pid" 2>/dev/null || true
    rm -f "$fifo"
    return $rc
}

LOG=$(mktemp)
set +e
run_qemu "$LOG" "/bin/stage1" '\[hamnix_ac_emit\] (PASS|FAIL)'
qrc=$?
set -e

echo "[fixpoint] --- stage2 on-device emit lines ---"
grep -E '\[hamnix_ac_emit\]' "$LOG" | grep -v HEXBEGIN | grep -v HEXEND | head -20 || true
echo "[fixpoint] --- end ---"

if grep -F -q "[hamnix_ac_emit] FAIL" "$LOG"; then
    echo "[fixpoint] FAIL: stage2 on-device compile failed:"
    grep -F "[hamnix_ac_emit] FAIL" "$LOG" || true
    tail -n 40 "$LOG"
    rm -f "$LOG"
    exit 1
fi
if ! grep -F -q "[hamnix_ac_emit] PASS" "$LOG"; then
    echo "[fixpoint] FAIL: stage2 did not reach PASS (qemu rc=${qrc})"
    tail -n 60 "$LOG"
    rm -f "$LOG"
    exit 1
fi

awk '/\[hamnix_ac_emit\] HEXBEGIN/{f=1;next} /\[hamnix_ac_emit\] HEXEND/{f=0} f' "$LOG" \
    | tr -d '\r\n ' > /tmp/fixpoint_stage2.hex
HEXLEN=$(wc -c < /tmp/fixpoint_stage2.hex)
if [ "$HEXLEN" -lt 200 ] || [ $((HEXLEN % 2)) -ne 0 ]; then
    echo "[fixpoint] FAIL: implausible stage2 hex capture length ${HEXLEN}"
    rm -f "$LOG" /tmp/fixpoint_stage2.hex
    exit 1
fi
python3 -c "import binascii,sys; open(sys.argv[1],'wb').write(binascii.unhexlify(open('/tmp/fixpoint_stage2.hex','rb').read().strip()))" "$STAGE2"
rm -f /tmp/fixpoint_stage2.hex "$LOG"
if [ ! -s "$STAGE2" ]; then
    echo "[fixpoint] FAIL: reconstructed stage2.elf is empty"
    exit 1
fi
S2LEN=$(wc -c < "$STAGE2")
echo "[fixpoint] stage2.elf: ${S2LEN} bytes"

# --- (4/4) Assert byte-identity --------------------------------------
echo "[fixpoint] (4/4) Compare stage1.elf vs stage2.elf (must be IDENTICAL)"
if cmp -s "$STAGE1" "$STAGE2"; then
    echo "[fixpoint] PASS — stage1 and stage2 are BYTE-IDENTICAL (${S1LEN} bytes)"
    echo "[fixpoint] The self-hosted compiler reproduces ITSELF exactly: FIXPOINT reached."
    exit 0
fi

# Divergence: report the first differing offset for the encoding gap.
echo "[fixpoint] FAIL: stage1 and stage2 DIFFER"
echo "[fixpoint] sizes: stage1=${S1LEN} stage2=${S2LEN}"
NDIFF=$(cmp -l "$STAGE1" "$STAGE2" 2>/dev/null | wc -l || true)
echo "[fixpoint] differing bytes: ${NDIFF}"
echo "[fixpoint] first 20 differences (offset[1-based] stage1-octal stage2-octal):"
cmp -l "$STAGE1" "$STAGE2" 2>/dev/null | head -20 || true
FIRST=$(cmp "$STAGE1" "$STAGE2" 2>&1 || true)
echo "[fixpoint] cmp: ${FIRST}"
exit 1
