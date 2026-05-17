# tests/u-binary/src/musl_thread/Makefile -- U27 pivot fixture build.
#
# REQUIRES: musl-gcc on the host. musl rolls pthread into libc.a so
# -pthread is implicit; we pass it anyway for clarity. If musl-gcc
# isn't on $PATH the install target prints a clear note and exits 0
# so CI keeps moving (same shape as the other u_musl_* / u_glibc_*
# fixtures).
#
# Output: ../../u_musl_thread -- static-PIE ELF64, OSABI=Linux,
# embedded into the initramfs by build_initramfs.py at
# /bin/u_musl_thread.

MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)

hello: hello.c
ifeq ($(MUSL_GCC),)
	@echo "[musl_thread] SKIP: musl-gcc not installed."
	@echo "[musl_thread]   apt-get install -y musl-tools (needs sudo)"
	@echo "[musl_thread]   then re-run: make -C tests/u-binary/src/musl_thread install"
else
	$(MUSL_GCC) -static-pie -O2 -pthread -o hello hello.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3). musl-gcc emits
	# OSABI=0 (SysV); the explicit Linux byte makes Hamnix's U1
	# detect path unambiguous (matches the other u_musl_* fixtures).
	printf '\003' | dd of=hello bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: hello
ifeq ($(MUSL_GCC),)
	@echo "[musl_thread] SKIP install (no musl-gcc, nothing built)"
else
	cp hello ../../u_musl_thread
endif

clean:
	rm -f hello hello.o
