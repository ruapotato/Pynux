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
#   - gcc + make + libc6-dev with static-libc (libc.a) available
#   - wget or curl (to fetch the upstream tarball)
#   - tar + xz-utils
#   - ~500 MB free disk for the source + build tree
#   - 15-30 minutes wall time on a modern x86_64 host
#
# If any of those are missing the install target prints a clear SKIP
# note and exits 0 -- mirrors the U22/U24/U39/U40 fixture pattern so
# CI in minimal environments keeps moving.
#
# Output stamping: e_ident[EI_OSABI] is rewritten to ELFOSABI_LINUX
# (3) so Hamnix's U1 ELF-detect path (elf_is_linux_binary) returns 1
# unambiguously -- host gcc emits OSABI=0 (SysV) by default.
#
# Why "-static" not "-static-pie"?
#
# Debian trixie's libpython3.x.a IS built with -fPIC -- but the
# upstream CPython source's own Modules/_decimal/libmpdec, Modules/zlib,
# Modules/expat trees compile with the project's CFLAGS, which we set
# to `-fPIC` here. Even so, a few linker objects (e.g.
# Programs/_freeze_module.o) end up with R_X86_64_32 relocations that
# `-static-pie` rejects. Plain `-static` accepts them. Hamnix's ELF
# loader handles both static and static-pie ELFs (U19); we go with the
# more robust path.
#
# If a future agent needs static-pie (e.g. for ASLR inside Hamnix),
# rebuild with `LDFLAGS="-static-pie -fPIE"` and CFLAGS="-fPIC -fPIE".
# Expect link-time failures unless ALL transitive .o's are PIC.

PY_VERSION  := 3.11.10
PY_TARBALL  := Python-$(PY_VERSION).tar.xz
PY_URL      := https://www.python.org/ftp/python/$(PY_VERSION)/$(PY_TARBALL)
PY_SRCDIR   := build/Python-$(PY_VERSION)
PY_OUT      := $(PY_SRCDIR)/python

WGET     := $(shell command -v wget 2>/dev/null)
CURL     := $(shell command -v curl 2>/dev/null)
GCC      := $(shell command -v gcc 2>/dev/null)
MAKE_BIN := $(shell command -v make 2>/dev/null)
HAS_LIBC_A := $(shell test -f /usr/lib/x86_64-linux-gnu/libc.a && echo yes || echo no)

.PHONY: all install clean stdlib-path freeze-patch

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
	    cd $(PY_SRCDIR) && python3.11 ./Tools/scripts/freeze_modules.py; \
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

$(PY_OUT): $(PY_SRCDIR)/configure freeze-patch
ifeq ($(GCC),)
	@echo "[cpython] SKIP: gcc not on PATH"
	@exit 0
else
ifeq ($(HAS_LIBC_A),no)
	@echo "[cpython] SKIP: /usr/lib/x86_64-linux-gnu/libc.a not present."
	@echo "[cpython]   apt-get install -y libc6-dev  (needs sudo)"
	@exit 0
else
	# Configure CPython for a fully-static build. Key flags:
	#   --disable-shared       -- no libpython3.x.so; everything in one ELF.
	#   --without-pymalloc-debug -- trim debug bookkeeping (smaller binary).
	#   --without-doc-strings  -- drop the ~1 MB of __doc__ tables in stdlib.
	#   --disable-test-modules -- don't build _testcapi / _testbuffer / ...
	#                             (they're for CPython's own test suite).
	#   CFLAGS=-fPIC          -- belt + braces; some PIC-needing libs need it.
	#   LDFLAGS=-static       -- the actual static link flag.
	#
	# --enable-optimizations (PGO + LTO) is INTENTIONALLY OMITTED:
	#   it lengthens the build from ~5 min to ~25 min on a modern host,
	#   and PGO needs to run the test interpreter which doesn't add up
	#   for our use case (boot-once-and-exit on Hamnix's serial). If a
	#   future agent wants a faster runtime + ~5% size cut, append
	#   `--enable-optimizations` here. Document the trade-off in the
	#   commit + HOWTO.
	cd $(PY_SRCDIR) && CFLAGS="-fPIC" ./configure \
	    --disable-shared \
	    --without-pymalloc-debug \
	    --without-doc-strings \
	    --disable-test-modules \
	    LDFLAGS="-static"
	# Build. Parallel make helps the compile phase; the link is
	# serial. ~5-10 min on a modern (8+ core) x86_64 host without
	# PGO; ~25 min if --enable-optimizations is added above.
	$(MAKE_BIN) -C $(PY_SRCDIR) -j$$(nproc)
endif
endif

install: hello
ifeq ($(GCC),)
	@echo "[cpython] SKIP install (no gcc)"
else
ifeq ($(HAS_LIBC_A),no)
	@echo "[cpython] SKIP install (no libc.a)"
else
	@if [ ! -f "$(PY_OUT)" ]; then \
	    echo "[cpython] SKIP install (build failed -- see build log)"; \
	    exit 0; \
	fi
	cp $(PY_OUT) ../../u_cpython
	# Strip aggressively. With the widened frozen-modules set,
	# CPython is ~29 MB before strip, ~7.9 MB after. We keep
	# symbols off the staged binary; the build dir retains the
	# unstripped copy for debugging.
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
