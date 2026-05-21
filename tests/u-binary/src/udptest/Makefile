# tests/u-binary/src/udptest/Makefile — §10 UDP-socket fixture build.
#
# Builds udptest.c — the first user binary to do real datagram I/O on
# Hamnix (socket/bind/sendto/recvfrom/close bridged to the in-kernel
# UDP socket layer). Output: ../../u_udptest, embedded into the
# initramfs by build_initramfs.py at /bin/u_udptest.
#
# The fixture queries QEMU SLIRP's built-in DNS resolver at
# 10.0.2.2:53 — a real UDP server that always answers, with no host
# helper and no guestfwd needed (QEMU guestfwd is TCP-only).
#
# REQUIRES: musl-gcc on the host. Skips quietly (exit 0) if it isn't
# installed so CI without the toolchain still builds a kernel.

MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)

udptest: udptest.c
ifeq ($(MUSL_GCC),)
	@echo "[udptest] SKIP: musl-gcc not installed."
	@echo "[udptest]   apt-get install -y musl-tools (needs sudo)"
	@echo "[udptest]   then re-run: make -C tests/u-binary/src/udptest install"
else
	$(MUSL_GCC) -static-pie -O2 -o udptest udptest.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3) — see musl_hello.
	printf '\003' | dd of=udptest bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: udptest
ifeq ($(MUSL_GCC),)
	@echo "[udptest] SKIP install (no musl-gcc, nothing built)"
else
	cp udptest ../../u_udptest
endif

clean:
	rm -f udptest udptest.o
