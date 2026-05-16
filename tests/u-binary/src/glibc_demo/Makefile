# tests/u-binary/src/glibc_demo/Makefile -- U22 fixture build.
#
# REQUIRES: host C compiler (cc/gcc) + glibc's static archive (libc.a)
# + the static-PIE startup (Scrt1.o + libc.a relocs). On Debian/Ubuntu
# this is the `libc6-dev` package. If `cc -static-pie` fails (no static
# glibc, missing toolchain, alternate libc on the host), the install
# target prints a skip note and exits 0 so the rest of the U-track
# regression keeps running -- same shape as U19/U20.
#
# Output: ../../u_glibc_demo -- a static-PIE ELF64 (ET_DYN) whose
# .rela.dyn contains the usual R_X86_64_RELATIVE + R_X86_64_IRELATIVE
# entries. build_initramfs.py picks this up and embeds it at
# /bin/u_glibc_demo.
#
# Why this fixture exists: U22 widens the U-track exercised surface
# beyond "print a string". It puts heap allocation (strdup/free),
# FILE* I/O (fopen/fread/fclose against /etc/motd), printf format
# variety, and time(NULL) through the same binary. The point isn't
# any single new syscall -- it's that the existing surface holds up
# when several glibc subsystems run together in one process.

CC      := cc
HAS_CC  := $(shell command -v $(CC) 2>/dev/null)

CAN_SPIE := $(shell printf 'int main(void){return 0;}\n' > /tmp/.u22_probe.c && \
                  $(CC) -static-pie -O2 -o /tmp/.u22_probe /tmp/.u22_probe.c >/dev/null 2>&1 && \
                  echo yes || echo no)

hello: hello.c
ifeq ($(HAS_CC),)
	@echo "[glibc_demo] SKIP: no host C compiler ($(CC)) found"
else
ifeq ($(CAN_SPIE),no)
	@echo "[glibc_demo] SKIP: $(CC) -static-pie failed (libc.a / Scrt1.o missing?)"
	@echo "[glibc_demo]   apt-get install -y libc6-dev  # (needs sudo)"
else
	$(CC) -static-pie -O2 -o hello hello.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3). The host's gcc
	# emits OSABI=0 (SysV) by default; the explicit Linux byte makes
	# Hamnix's U1 detect path unambiguous (matches the rest of the
	# u_glibc_* / u_musl_* fixtures).
	printf '\003' | dd of=hello bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif
endif

install: hello
ifeq ($(HAS_CC),)
	@echo "[glibc_demo] SKIP install (no host C compiler)"
else
ifeq ($(CAN_SPIE),no)
	@echo "[glibc_demo] SKIP install (no static-pie glibc)"
else
	cp hello ../../u_glibc_demo
endif
endif

clean:
	rm -f hello hello.o
