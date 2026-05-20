# tests/u-binary/src/cpython/Makefile -- U41 fixture build.
#
# Produces ../../u_cpython -- a full static CPython 3.11.x interpreter
# suitable for proving "Hamnix can run apt-installable Python".
#
# U39 shipped MicroPython 1.22 (~900 KB) as the canary proof that
# Hamnix's Linux ABI is wide enough to host a Python interpreter.
# U41 raises the bar to the same binary Debian's `apt install python3`
# delivers: CPython, with its full stdlib + much wider syscall surface
# (mmap-heavy, brk-aggressive, getrandom, prlimit64, clock_nanosleep,
# pselect6, ...).
#
# FROZEN-MODULES BUILD (this revision):
#   We patch Tools/scripts/freeze_modules.py to widen the upstream
#   FROZEN list. Beyond CPython 3.11's stock bootstrap set (importlib,
#   abc, codecs, io, os, posixpath, site, ...), we add:
#     <encodings.*>  -- the entire encodings package (~120 KB). This
#                       is what init_fs_encoding needs at startup;
#                       upstream leaves it OFF because of build-time
#                       noise, but for us it's load-bearing.
#     _weakrefset, types, enum, keyword, reprlib, operator, functools,
#     <collections.*>, copyreg, token, tokenize, linecache, traceback,
#     warnings, contextlib, heapq, weakref, inspect.
#   With these frozen INTO the static binary's data segment, CPython
#   runs with PYTHONHOME=/nonexistent + PYTHONPATH= cleanly. The
#   /usr/lib/python3.11/ initramfs embedding path (HAMNIX_EMBED_PYLIB)
#   is no longer needed — sidesteps the fs/cpio.ad NR_FILES=192 cap.
#
# SIZE: ~29 MB unstripped, ~7.9 MB stripped (was 5.7 MB pre-freeze).
#   The +2.2 MB stripped overhead buys complete self-containment.
#
# REQUIRES (build host):
#   - musl-gcc (Debian: apt-get install musl-tools) + make
#   - wget or curl (to fetch the upstream tarball)
#   - tar + xz-utils
#   - host python3.11 (to run Tools/scripts/freeze_modules.py)
#   - ~500 MB free disk for the source + build tree
#   - 10-20 minutes wall time on a modern x86_64 host
#
# If any of those are missing the install target prints a clear SKIP
# note and exits 0 -- mirrors the U22/U24/U39/U40 fixture pattern so
# CI in minimal environments keeps moving.
#
# Output stamping: e_ident[EI_OSABI] is rewritten to ELFOSABI_LINUX
# (3) so Hamnix's U1 ELF-detect path (elf_is_linux_binary) returns 1
# unambiguously -- musl-gcc emits OSABI=0 (SysV) by default.
#
# Why musl `-static-pie` (NOT glibc `-static`)?
#
# Hamnix's ELF loader (fs/elf.ad) can ONLY run ET_DYN binaries. An
# ET_EXEC binary linked at the fixed 0x400000 collides with Hamnix's
# ~12 MiB identity-mapped kernel image and is REFUSED by the
# kernel-image collision guard added in commit 653d962. So u_cpython
# MUST be ET_DYN (static-PIE) -- the same ELF shape as the working
# U39 MicroPython fixture.
#
# A glibc `-static-pie` build of CPython 3.11 *links* cleanly, but the
# resulting binary carries 2 dynamic R_X86_64_TPOFF64 relocations
# (against glibc's own `errno` / `__libc_dlerror_result` TLS symbols,
# pulled in from libc.a). Debian trixie's glibc 2.41
# `_dl_relocate_static_pie` mishandles those: it calls
# `_dl_allocate_static_tls` during early self-relocation, which fails
# into `_dl_signal_error` BEFORE the error-catch frame exists -- the
# binary SIGSEGVs before main() even on the host. The working U39
# MicroPython fixture has ZERO TPOFF64 relocs, which is why it is
# unaffected.
#
# Building CPython with musl-gcc sidesteps the glibc TLS bug entirely:
# musl 1.2.5's static-pie startup resolves TLS without the buggy
# `_dl_allocate_static_tls` path. The musl build produces a clean
# ET_DYN, static-pie, no-PT_INTERP `python` with 0 TPOFF64 relocs that
# runs both on the host and on Hamnix.
#
# Note: CPython 3.11's configure aborts on a "platform triplet"
# mismatch under musl-gcc (musl-gcc's wrapper reports the host gcc
# multiarch `x86_64-linux-gnu` while CPython's compiler probe yields
# `x86_64-linux-musl`). The configure-patch step below neutralises
# that check the same way Alpine Linux does -- trust the compiler
# probe's triplet.

PY_VERSION  := 3.11.10
PY_TARBALL  := Python-$(PY_VERSION).tar.xz
PY_URL      := https://www.python.org/ftp/python/$(PY_VERSION)/$(PY_TARBALL)
PY_SRCDIR   := build/Python-$(PY_VERSION)
PY_OUT      := $(PY_SRCDIR)/python

WGET     := $(shell command -v wget 2>/dev/null)
CURL     := $(shell command -v curl 2>/dev/null)
MUSLGCC  := $(shell command -v musl-gcc 2>/dev/null)
MAKE_BIN := $(shell command -v make 2>/dev/null)
# host python3.11 is required to run Tools/scripts/freeze_modules.py
PY311    := $(shell command -v python3.11 2>/dev/null)

.PHONY: all install clean stdlib-path freeze-patch configure-patch

all: hello

# DEPRECATED (kept for the HAMNIX_EMBED_PYLIB hook in
# scripts/build_initramfs.py — still callable if some future Python
# distribution scenario needs an on-disk stdlib). The default U41
# build no longer uses this: the stdlib is frozen INTO u_cpython
# so no /usr/lib/python3.11/ tree is needed.
#
# Prints (to stdout) the absolute path to the extracted upstream
# CPython source's `Lib/` directory.
stdlib-path:
	@if [ -d "$(PY_SRCDIR)/Lib" ]; then \
	    cd $(PY_SRCDIR) && pwd | tr -d '\n' && echo "/Lib"; \
	else \
	    echo "[cpython] stdlib-path: $(PY_SRCDIR)/Lib not found" >&2; \
	    echo "[cpython]   run 'make -C tests/u-binary/src/cpython install' first" >&2; \
	    exit 1; \
	fi

# Patch the extracted CPython source's freeze_modules.py to widen
# the FROZEN list (encodings + site.py support modules). Idempotent:
# the patch checks for the sentinel comment before re-applying. Run
# from the $(PY_OUT) rule below before invoking ./configure + make.
freeze-patch: $(PY_SRCDIR)/configure
	@if grep -q "HAMNIX U41: freeze the encodings package" \
	    $(PY_SRCDIR)/Tools/scripts/freeze_modules.py; then \
	    echo "[cpython] freeze-patch already applied"; \
	else \
	    echo "[cpython] applying Hamnix freeze-modules patch"; \
	    python3 -c 'import re, sys; \
p = "$(PY_SRCDIR)/Tools/scripts/freeze_modules.py"; \
s = open(p).read(); \
old = "    (\x27stdlib - startup, without site (python -S)\x27, [\n        \x27abc\x27,\n        \x27codecs\x27,\n        # For now we do not freeze the encodings, due # to the noise all\n        # those extra modules add to the text printed during the build.\n        # (See https://github.com/python/cpython/pull/28398#pullrequestreview-756856469.)\n        #\x27<encodings.*>\x27,\n        \x27io\x27,\n        ]),"; \
new = "    (\x27stdlib - startup, without site (python -S)\x27, [\n        \x27abc\x27,\n        \x27codecs\x27,\n        # HAMNIX U41: freeze the encodings package so CPython\x27s\n        # init_fs_encoding succeeds without an on-disk stdlib tree.\n        \x27<encodings.*>\x27,\n        \x27io\x27,\n        ]),"; \
assert old in s, "freeze_modules.py upstream format drifted; refresh patch"; \
s = s.replace(old, new); \
old2 = "        \x27site\x27,\n        \x27stat\x27,\n        ]),"; \
new2 = "        \x27site\x27,\n        \x27stat\x27,\n        # HAMNIX U41: site.py + eval-loop boot path support.\n        \x27_weakrefset\x27,\n        \x27types\x27,\n        \x27enum\x27,\n        \x27keyword\x27,\n        \x27reprlib\x27,\n        \x27operator\x27,\n        \x27functools\x27,\n        \x27<collections.*>\x27,\n        \x27copyreg\x27,\n        \x27token\x27,\n        \x27tokenize\x27,\n        \x27linecache\x27,\n        \x27traceback\x27,\n        \x27warnings\x27,\n        \x27contextlib\x27,\n        \x27heapq\x27,\n        \x27weakref\x27,\n        \x27inspect\x27,\n        ]),"; \
assert old2 in s, "freeze_modules.py site section drifted; refresh patch"; \
s = s.replace(old2, new2); \
open(p, "w").write(s); \
print("[cpython] patched freeze_modules.py")'; \
	    cd $(PY_SRCDIR) && $(PY311) ./Tools/scripts/freeze_modules.py; \
	fi

# Patch the generated `configure` script so building against musl-gcc
# does not abort on the "platform triplet" check. musl-gcc's wrapper
# reports the host gcc multiarch (x86_64-linux-gnu) while CPython's
# compiler-characteristics probe yields x86_64-linux-musl; upstream
# treats the mismatch as a hard error. Alpine Linux resolves this by
# trusting the compiler-probe triplet -- we do the same. Idempotent:
# checks for the sentinel before re-applying.
configure-patch: $(PY_SRCDIR)/configure
	@if grep -q "HAMNIX U41: building against musl-gcc" \
	    $(PY_SRCDIR)/configure; then \
	    echo "[cpython] configure-patch already applied"; \
	else \
	    echo "[cpython] applying Hamnix configure triplet patch"; \
	    $(PY311) -c 'p = "$(PY_SRCDIR)/configure"; \
s = open(p).read(); \
old = "if test x$$PLATFORM_TRIPLET != x && test x$$MULTIARCH != x; then\n  if test x$$PLATFORM_TRIPLET != x$$MULTIARCH; then\n    as_fn_error $$? \"internal configure error for the platform triplet, please file a bug report\" \"$$LINENO\" 5\n  fi\nelif test x$$PLATFORM_TRIPLET != x && test x$$MULTIARCH = x; then\n  MULTIARCH=$$PLATFORM_TRIPLET\nfi"; \
new = "# HAMNIX U41: building against musl-gcc, whose wrapper reports the\n# host gcc multiarch (x86_64-linux-gnu) while CPython index probe\n# yields x86_64-linux-musl. Trust the compiler-probe triplet.\nif test x$$PLATFORM_TRIPLET != x; then\n  MULTIARCH=$$PLATFORM_TRIPLET\nfi"; \
assert old in s, "configure platform-triplet block drifted; refresh patch"; \
s = s.replace(old, new); \
open(p, "w").write(s); \
print("[cpython] patched configure")'; \
	fi

# `hello` is the fixture-target name (matches u_hello / u_python /
# u_busybox_musl conventions). The underlying artifact is the CPython
# `python` binary; we stamp it + copy it to ../../u_cpython in install.
hello: $(PY_OUT)

build/$(PY_TARBALL):
	@mkdir -p build
ifneq ($(WGET),)
	cd build && $(WGET) -q $(PY_URL) -O $(PY_TARBALL)
else
ifneq ($(CURL),)
	cd build && $(CURL) -fsSL $(PY_URL) -o $(PY_TARBALL)
else
	@echo "[cpython] FAIL: need wget or curl on PATH"
	@exit 1
endif
endif

$(PY_SRCDIR)/configure: build/$(PY_TARBALL)
	cd build && tar xf $(PY_TARBALL)
	@touch $@

$(PY_OUT): $(PY_SRCDIR)/configure configure-patch freeze-patch
ifeq ($(MUSLGCC),)
	@echo "[cpython] SKIP: musl-gcc not on PATH."
	@echo "[cpython]   apt-get install -y musl-tools  (needs sudo)"
	@exit 0
else
ifeq ($(PY311),)
	@echo "[cpython] SKIP: python3.11 not on PATH"
	@echo "[cpython]   (needed to run Tools/scripts/freeze_modules.py)"
	@exit 0
else
	# Configure CPython for a fully-static, position-independent
	# (static-PIE / ET_DYN) build against musl. Key flags:
	#   CC=musl-gcc            -- musl, NOT glibc. glibc 2.41's static-pie
	#                             _dl_relocate_static_pie SIGSEGVs on
	#                             CPython's R_X86_64_TPOFF64 relocs; musl
	#                             does not. See the header comment.
	#   CFLAGS=-fPIE           -- position-independent code for the PIE.
	#   LDFLAGS=-static-pie    -- produce ET_DYN, statically linked, no
	#                             PT_INTERP. This is the ONLY ELF shape
	#                             Hamnix's loader can run for u_cpython
	#                             (an ET_EXEC @0x400000 collides with the
	#                             kernel image and is refused).
	#   --disable-shared       -- no libpython3.x.so; everything in one ELF.
	#   --without-pymalloc-debug -- trim debug bookkeeping (smaller binary).
	#   --without-doc-strings  -- drop the ~1 MB of __doc__ tables in stdlib.
	#   --disable-test-modules -- don't build _testcapi / _testbuffer / ...
	#   --with-system-libmpdec -- use the host libmpdec rather than
	#                             rebuilding the bundled _decimal tree.
	#
	# --enable-optimizations (PGO + LTO) is INTENTIONALLY OMITTED:
	#   it lengthens the build and PGO needs to run the test interpreter.
	cd $(PY_SRCDIR) && CC="musl-gcc" CXX="musl-gcc" \
	    CFLAGS="-fPIE" LDFLAGS="-static-pie" ./configure \
	    --disable-shared \
	    --without-pymalloc-debug \
	    --without-doc-strings \
	    --disable-test-modules \
	    --with-system-libmpdec
	# Build. The first `make` links `python`; `regen-frozen` then
	# bakes the widened FROZEN module set (encodings.* etc.) into
	# Python/frozen_modules/*.h, and the second `make` re-links the
	# interpreter with those headers compiled in.
	$(MAKE_BIN) -C $(PY_SRCDIR) -j$$(nproc)
	$(MAKE_BIN) -C $(PY_SRCDIR) regen-frozen
	$(MAKE_BIN) -C $(PY_SRCDIR) -j$$(nproc)
endif
endif

install: hello
ifeq ($(MUSLGCC),)
	@echo "[cpython] SKIP install (no musl-gcc)"
else
ifeq ($(PY311),)
	@echo "[cpython] SKIP install (no python3.11)"
else
	@if [ ! -f "$(PY_OUT)" ]; then \
	    echo "[cpython] SKIP install (build failed -- see build log)"; \
	    exit 0; \
	fi
	cp $(PY_OUT) ../../u_cpython
	# Strip aggressively. With the widened frozen-modules set the
	# musl static-pie CPython is ~20 MB before strip, ~9.3 MB after.
	# We keep symbols off the staged binary; the build dir retains
	# the unstripped copy for debugging.
	strip --strip-all ../../u_cpython || true
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3). Same trick the
	# other u_* fixtures use so the U1 detect path is unambiguous.
	printf '\003' | dd of=../../u_cpython bs=1 seek=7 count=1 \
	    conv=notrunc 2>/dev/null
	@echo "[cpython] installed ../../u_cpython ($$(stat -c%s ../../u_cpython) bytes)"
endif
endif

clean:
	rm -rf build
