# tests/u-binary/src/cow_fork/Makefile — #143 fixture build.
#
# Builds a musl-gcc static-PIE x86_64 ELF that proves fork() gives the
# child a private, isolated (COW) address space: a child overwrites a
# global/.heap/.mmap buffer, the parent's copies stay intact; a second
# fork snapshots live parent state.
# Staged at tests/u-binary/u_cow_fork -> /bin/u_cow_fork.
# SKIPs quietly if musl-gcc isn't installed.

MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)

cow_fork: cow_fork.c
ifeq ($(MUSL_GCC),)
	@echo "[cow_fork] SKIP: musl-gcc not installed."
	@echo "[cow_fork]   apt-get install -y musl-tools (needs sudo)"
else
	$(MUSL_GCC) -static-pie -O2 -o cow_fork cow_fork.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3).
	printf '\003' | dd of=cow_fork bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: cow_fork
ifeq ($(MUSL_GCC),)
	@echo "[cow_fork] SKIP install (no musl-gcc, nothing built)"
else
	cp cow_fork ../../u_cow_fork
endif

clean:
	rm -f cow_fork cow_fork.o
