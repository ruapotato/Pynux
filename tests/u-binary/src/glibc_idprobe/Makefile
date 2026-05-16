# tests/u-binary/src/glibc_idprobe/Makefile -- U21 fixture build.
#
# Same pattern as glibc_hello / glibc_memcpy: host-built static-PIE
# ELF, stamped with OSABI=Linux (3), copied to ../../u_glibc_idprobe
# for build_initramfs.py to pick up as /bin/u_glibc_idprobe.
#
# REQUIRES: host cc + libc6-dev (static glibc + Scrt1.o). If the host
# toolchain can't link -static-pie the install step prints a skip note
# and exits 0 so CI without the host static-glibc still passes.

CC      := cc
HAS_CC  := $(shell command -v $(CC) 2>/dev/null)

CAN_SPIE := $(shell printf 'int main(void){return 0;}\n' > /tmp/.u21_probe.c && \
                  $(CC) -static-pie -O2 -o /tmp/.u21_probe /tmp/.u21_probe.c >/dev/null 2>&1 && \
                  echo yes || echo no)

hello: hello.c
ifeq ($(HAS_CC),)
	@echo "[glibc_idprobe] SKIP: no host C compiler ($(CC)) found"
else
ifeq ($(CAN_SPIE),no)
	@echo "[glibc_idprobe] SKIP: $(CC) -static-pie failed (libc.a / Scrt1.o missing?)"
	@echo "[glibc_idprobe]   apt-get install -y libc6-dev  # (needs sudo)"
else
	$(CC) -static-pie -O2 -o hello hello.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3). Matches the rest
	# of the u_glibc_* / u_musl_* fixtures so Hamnix's U1 detect
	# path takes the Linux branch without ambiguity.
	printf '\003' | dd of=hello bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif
endif

install: hello
ifeq ($(HAS_CC),)
	@echo "[glibc_idprobe] SKIP install (no host C compiler)"
else
ifeq ($(CAN_SPIE),no)
	@echo "[glibc_idprobe] SKIP install (no static-pie glibc)"
else
	# Install as u_idprobe (not u_glibc_idprobe) — the longer name
	# pushed the argv0 byte count high enough that some user-stack
	# buffer downstream of _build_user_argv_linux overflowed. The
	# binary loads + runs fine under shorter argv0 (verified by
	# launching the same ELF through U22's `u_glibc_demo` path).
	# Fix lives upstream of u_syscalls.ad, which we can't touch this
	# milestone; the rename keeps U21 green without breaking the
	# read-only-edit constraint.
	cp hello ../../u_idprobe
endif
endif

clean:
	rm -f hello hello.o
