# tests/u-binary/src/socktest/Makefile — U-socket fixture build.
#
# Builds socktest.c — the first user binary to complete a real TCP
# connection on Hamnix (socket/connect/write/read/close bridged to the
# in-kernel TCP stack). Output: ../../u_socktest, embedded into the
# initramfs by build_initramfs.py at /bin/u_socktest.
#
# REQUIRES: musl-gcc on the host. Skips quietly (exit 0) if it isn't
# installed so CI without the toolchain still builds a kernel.
#
# SOCKTEST_PORT picks the host port the guest connects to (via the
# SLIRP host alias 10.0.2.2). scripts/test_u_socket.sh overrides it
# with a free port at build time:
#
#     make SOCKTEST_PORT=NNNN install

MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)
SOCKTEST_PORT ?= 8080

socktest: socktest.c
ifeq ($(MUSL_GCC),)
	@echo "[socktest] SKIP: musl-gcc not installed."
	@echo "[socktest]   apt-get install -y musl-tools (needs sudo)"
	@echo "[socktest]   then re-run: make -C tests/u-binary/src/socktest install"
else
	$(MUSL_GCC) -static-pie -O2 -DSOCKTEST_PORT=$(SOCKTEST_PORT) \
		-o socktest socktest.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3) — see musl_hello.
	printf '\003' | dd of=socktest bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: socktest
ifeq ($(MUSL_GCC),)
	@echo "[socktest] SKIP install (no musl-gcc, nothing built)"
else
	cp socktest ../../u_socktest
endif

clean:
	rm -f socktest socktest.o
