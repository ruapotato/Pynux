# scripts/_ensure_ubin.sh — build U-track fixture binaries on demand.
#
# WHY THIS EXISTS
#
# The U-track regression scripts (scripts/test_u*.sh and friends) each
# need a prebuilt fixture binary at tests/u-binary/u_<name>. Those
# fixtures are gitignored — they're host-built, per-host artifacts —
# so EVERY fresh `git worktree` (every dispatched agent works in one)
# starts without them.
#
# The old idiom in each script was a hand-rolled "skip-on-missing"
# block: if tests/u-binary/u_<name> is absent, print a SKIP notice and
# `exit 0`. That made every agent silently UNDER-VERIFY the U-track and
# misreport the cause as "the host lacks the musl/glibc toolchain."
# That diagnosis is FALSE: the host has the full toolchain (gcc, g++,
# cc, musl-gcc, x86_64-linux-musl-gcc, glibc static libc.a/crt1.o, and
# musl/musl-dev/musl-tools). Every fixture with a src/ recipe builds
# cleanly from source.
#
# THE FIX — build-on-missing instead of skip-on-missing:
#
#   1. If tests/u-binary/u_<name> already exists → use it as-is.
#   2. If it's absent → run `make -C tests/u-binary/src/<srcdir> install`
#      to build it.
#   3. If the build SUCCEEDS → return 0; the caller proceeds normally.
#   4. If the build genuinely FAILS (a real toolchain gap, or an
#      offline host that can't fetch an upstream tarball) → return
#      non-zero; the caller then SKIPs, printing the REAL build error
#      — not a generic "fixture not staged."
#
# USAGE
#
#   . "$(dirname "$0")/_ensure_ubin.sh"
#   ...
#   if ! ensure_ubin <fixture> <srcdir> [extra make args...]; then
#       echo "[<test>] SKIP: could not build $UBIN — see build log above"
#       exit 0
#   fi
#
#   <fixture>  — the basename under tests/u-binary/, e.g. u_glibc_hello.
#   <srcdir>   — the directory under tests/u-binary/src/ whose Makefile
#                `install` target produces that fixture, e.g. glibc_hello.
#                (The src dir is NOT a pure function of the fixture name:
#                 u_busybox_musl ← musl_busybox, u_python ← python, etc.
#                 — so the caller passes both explicitly.)
#   [extra...] — optional extra arguments appended to the `make` line
#                (e.g. SOCKTEST_PORT=12345 for the socket fixture).
#
# A convenience `ensure_ubin_or_skip <test-label> <fixture> <srcdir> ...`
# wraps the build + the SKIP-and-exit-0 so the caller is a one-liner.
#
# This file only DEFINES functions — it must be safe to source from any
# point in a test script (it does not touch `set -e`, the build lock,
# or the working directory).

# ensure_ubin <fixture> <srcdir> [extra make args...]
#
# Returns 0 if tests/u-binary/<fixture> is present after the call
# (already there, or freshly built). Returns 1 if it's still missing
# after a build attempt — the build output has already been streamed
# so the caller / log captures the real failure reason.
ensure_ubin() {
    local fixture="$1"
    local srcdir="$2"
    shift 2 2>/dev/null || true

    local ubin="tests/u-binary/${fixture}"
    local src="tests/u-binary/src/${srcdir}"

    if [ -f "$ubin" ]; then
        return 0
    fi

    echo "[ensure_ubin] $ubin absent — building via" \
         "make -C $src install $*"

    if [ ! -d "$src" ]; then
        echo "[ensure_ubin] ERROR: no source recipe at $src —" \
             "this fixture has no build recipe (e.g. a retired or" \
             "hand-extracted binary). Cannot auto-build."
        return 1
    fi

    # Stream the build output so a genuine failure (missing tool,
    # offline tarball fetch, compile error) is visible in the test log.
    if ! make -C "$src" install "$@"; then
        echo "[ensure_ubin] ERROR: 'make -C $src install' FAILED —" \
             "see the build output above for the real reason."
        return 1
    fi

    if [ ! -f "$ubin" ]; then
        # `make install` can exit 0 yet skip (e.g. the musl_busybox /
        # cpython Makefiles print a SKIP note and `exit 0` when a
        # required tool or download is unavailable).
        echo "[ensure_ubin] ERROR: 'make -C $src install' completed" \
             "but $ubin still missing — the Makefile skipped the" \
             "build (real reason printed above)."
        return 1
    fi

    echo "[ensure_ubin] built $ubin ($(stat -c%s "$ubin" 2>/dev/null || echo '?') bytes)"
    return 0
}

# ensure_ubin_or_skip <test-label> <fixture> <srcdir> [extra make args...]
#
# Convenience wrapper: builds the fixture; if it can't be produced,
# prints a SKIP line tagged with <test-label> and exits 0 (the U-track
# convention for "the host genuinely can't build this fixture").
ensure_ubin_or_skip() {
    local label="$1"
    local fixture="$2"
    local srcdir="$3"
    shift 3 2>/dev/null || true

    if ! ensure_ubin "$fixture" "$srcdir" "$@"; then
        echo "[$label] SKIP: tests/u-binary/$fixture could not be" \
             "built (see the real build error above)."
        exit 0
    fi
}
