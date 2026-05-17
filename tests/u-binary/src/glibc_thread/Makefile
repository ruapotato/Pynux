# tests/u-binary/src/glibc_thread/Makefile -- U27 fixture build.
#
# REQUIRES: host C compiler (cc/gcc) + glibc's static archive (libc.a)
# + the static-PIE startup (Scrt1.o + libc.a relocs) + libpthread.a.
# On Debian/Ubuntu this is `libc6-dev`. If `cc -static-pie -lpthread`
# fails (no static glibc, no static libpthread, alternate libc on the
# host), the install target prints a skip note and exits 0 -- same
# shape as U22/U25/U26 fixtures.
#
# Output: ../../u_glibc_thread -- a static-PIE ELF64 (ET_DYN) that
# pthread_create()s two workers, joins them, and validates a shared
# counter. build_initramfs.py picks this up and embeds it at
# /bin/u_glibc_thread.

CC      := cc
HAS_CC  := $(shell command -v $(CC) 2>/dev/null)

CAN_SPIE := $(shell printf '#include <pthread.h>\nint main(void){pthread_t t; return 0;}\n' > /tmp/.u27_probe.c && \
                  $(CC) -static-pie -O2 -o /tmp/.u27_probe /tmp/.u27_probe.c -lpthread >/dev/null 2>&1 && \
                  echo yes || echo no)

hello: hello.c
ifeq ($(HAS_CC),)
	@echo "[glibc_thread] SKIP: no host C compiler ($(CC)) found"
else
ifeq ($(CAN_SPIE),no)
	@echo "[glibc_thread] SKIP: $(CC) -static-pie -lpthread failed (libc.a / libpthread.a missing?)"
	@echo "[glibc_thread]   apt-get install -y libc6-dev  # (needs sudo)"
else
	$(CC) -static-pie -O2 -o hello hello.c -lpthread
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3). The host's gcc
	# emits OSABI=0 (SysV) by default; the explicit Linux byte makes
	# Hamnix's U1 detect path unambiguous (matches the rest of the
	# u_glibc_* / u_musl_* fixtures).
	printf '\003' | dd of=hello bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif
endif

install: hello
ifeq ($(HAS_CC),)
	@echo "[glibc_thread] SKIP install (no host C compiler)"
else
ifeq ($(CAN_SPIE),no)
	@echo "[glibc_thread] SKIP install (no static-pie glibc / libpthread)"
else
	cp hello ../../u_glibc_thread
endif
endif

clean:
	rm -f hello hello.o
