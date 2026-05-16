# tests/u-binary/src/musl_hello/Makefile — U12 fixture build.
#
# REQUIRES: musl-gcc on the host (apt-get install musl-tools, or
# a hand-built musl toolchain). If musl-gcc isn't on $PATH the
# `install` target prints a clear note and exits 0 so the rest of
# the U-track test harness (and CI) keeps moving.
#
# Output: ../../u_musl_hello — a static-PIE ELF64, OSABI=Linux,
# embedded into the initramfs by build_initramfs.py at /bin/u_musl_hello.
#
# Why static-PIE: musl's _start in crt1.o + __libc_start_main does
# arch_prctl(ARCH_SET_FS), set_tid_address(), brk() before invoking
# main(). All five syscalls are already implemented in Hamnix
# (linux_abi/u_syscalls.ad), so this is the smallest "real C
# toolchain" binary we can plausibly land on the U-track.

MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)

hello: hello.c
ifeq ($(MUSL_GCC),)
	@echo "[musl_hello] SKIP: musl-gcc not installed."
	@echo "[musl_hello]   apt-get install -y musl-tools (needs sudo)"
	@echo "[musl_hello]   then re-run: make -C tests/u-binary/src/musl_hello install"
else
	# -static-pie produces ET_DYN with R_X86_64_RELATIVE entries that
	# Hamnix's U10 loader rewrites. -O2 keeps the binary small. We
	# avoid -nostdlib here: the whole point of U12 is that musl's
	# real crt1.o + libc.a get linked in.
	$(MUSL_GCC) -static-pie -O2 -o hello hello.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3). musl-gcc emits
	# OSABI=0 (SysV) by default; Hamnix's elf_is_linux_binary also
	# accepts the SysV fallback, but the explicit Linux byte makes
	# the detect path unambiguous (mirrors the U10 pie fixture).
	printf '\003' | dd of=hello bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: hello
ifeq ($(MUSL_GCC),)
	@echo "[musl_hello] SKIP install (no musl-gcc, nothing built)"
else
	cp hello ../../u_musl_hello
endif

clean:
	rm -f hello hello.o
