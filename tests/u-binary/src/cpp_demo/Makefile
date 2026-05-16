# tests/u-binary/src/cpp_demo/Makefile -- U24 fixture build.
#
# REQUIRES: host g++ + libstdc++ static archive + glibc static-PIE
# startup. On Debian/Ubuntu the package set is `g++ + libc6-dev +
# libstdc++-*-dev` (the static libstdc++.a ships alongside the dynamic
# one). If `g++ -static-pie` fails (alternate toolchain, missing static
# libs), the install target prints a skip note and exits 0 so the rest
# of the U-track regression keeps running -- same shape as
# U19/U20/U22.
#
# Output: ../../u_cpp_demo -- a static-PIE ELF64 (ET_DYN) whose
# .rela.dyn carries R_X86_64_RELATIVE + R_X86_64_IRELATIVE entries
# and whose .eh_frame walks the C++ unwinder. build_initramfs.py
# picks this up and embeds it at /bin/u_cpp_demo (12 bytes -- short
# enough to stay clear of the long-argv0 stack overflow U23 is
# fixing in the kernel's user-init path).
#
# Why this fixture exists: U24 is the first non-C user binary on
# Hamnix. C++ static-init constructors run before main (iostream's
# __ioinit, std::__ioinit), exception handling drags in libgcc's
# _Unwind_*, and iostreams hit TLS-backed locale state through %fs:.
# Any of those can blow up against a half-implemented Linux ABI in a
# way the U22 C fixture wouldn't catch.

CXX     := g++
HAS_CXX := $(shell command -v $(CXX) 2>/dev/null)

CAN_SPIE := $(shell printf '#include <iostream>\nint main(){std::cout<<"x\\n";return 0;}\n' > /tmp/.u24_probe.cc && \
                  $(CXX) -static-pie -O2 -o /tmp/.u24_probe /tmp/.u24_probe.cc >/dev/null 2>&1 && \
                  echo yes || echo no)

hello: hello.cc
ifeq ($(HAS_CXX),)
	@echo "[cpp_demo] SKIP: no host C++ compiler ($(CXX)) found"
else
ifeq ($(CAN_SPIE),no)
	@echo "[cpp_demo] SKIP: $(CXX) -static-pie failed (libstdc++.a / Scrt1.o missing?)"
	@echo "[cpp_demo]   apt-get install -y g++ libc6-dev  # (needs sudo)"
else
	$(CXX) -static-pie -O2 -o hello hello.cc
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3). The host's g++
	# emits OSABI=0 (SysV) by default; the explicit Linux byte makes
	# Hamnix's U1 detect path unambiguous (matches the rest of the
	# u_glibc_* / u_musl_* fixtures).
	printf '\003' | dd of=hello bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif
endif

install: hello
ifeq ($(HAS_CXX),)
	@echo "[cpp_demo] SKIP install (no host C++ compiler)"
else
ifeq ($(CAN_SPIE),no)
	@echo "[cpp_demo] SKIP install (no static-pie libstdc++)"
else
	cp hello ../../u_cpp_demo
endif
endif

clean:
	rm -f hello hello.o
