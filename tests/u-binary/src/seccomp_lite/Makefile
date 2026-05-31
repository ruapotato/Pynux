# tests/u-binary/src/seccomp_lite/Makefile — #160 fixture build.
#
# Builds a musl-gcc static-PIE x86_64 ELF that exercises seccomp-lite:
# write before arm -> install SIGSYS handler -> prctl(PR_SET_SECCOMP,
# SECCOMP_MODE_STRICT) -> allowed write still works -> denied getpid
# delivers SIGSYS to the handler -> _exit clean.
# Staged at tests/u-binary/u_seccomp_lite -> /bin/u_seccomp_lite.
# SKIPs quietly if musl-gcc isn't installed.

MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)

seccomp_lite: seccomp_lite.c
ifeq ($(MUSL_GCC),)
	@echo "[seccomp_lite] SKIP: musl-gcc not installed."
	@echo "[seccomp_lite]   apt-get install -y musl-tools (needs sudo)"
else
	$(MUSL_GCC) -static-pie -O2 -o seccomp_lite seccomp_lite.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3).
	printf '\003' | dd of=seccomp_lite bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: seccomp_lite
ifeq ($(MUSL_GCC),)
	@echo "[seccomp_lite] SKIP install (no musl-gcc, nothing built)"
else
	cp seccomp_lite ../../u_seccomp_lite
endif

clean:
	rm -f seccomp_lite seccomp_lite.o
