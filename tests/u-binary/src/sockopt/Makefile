# tests/u-binary/src/sockopt/Makefile — §10 sockopt fixture build.
#
# Builds sockopt.c — a userland getsockopt/setsockopt round-trip test.
# Output: ../../u_sockopt, embedded into the initramfs by
# build_initramfs.py at /bin/u_sockopt.
#
# REQUIRES: musl-gcc on the host. Skips quietly (exit 0) if it isn't
# installed so CI without the toolchain still builds a kernel.

MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)

sockopt: sockopt.c
ifeq ($(MUSL_GCC),)
	@echo "[sockopt] SKIP: musl-gcc not installed."
	@echo "[sockopt]   apt-get install -y musl-tools (needs sudo)"
	@echo "[sockopt]   then re-run: make -C tests/u-binary/src/sockopt install"
else
	$(MUSL_GCC) -static-pie -O2 -o sockopt sockopt.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3) — see musl_hello.
	printf '\003' | dd of=sockopt bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: sockopt
ifeq ($(MUSL_GCC),)
	@echo "[sockopt] SKIP install (no musl-gcc, nothing built)"
else
	cp sockopt ../../u_sockopt
endif

clean:
	rm -f sockopt sockopt.o
