# tests/u-binary/src/wx_text_ro/Makefile — W^X Stage 1b fixture build.
#
# Builds a musl-gcc static-PIE x86_64 ELF that exercises read-only
# .text: write baseline -> install SIGSEGV handler -> read a .text byte
# (ok) -> write a .text byte -> protection fault -> kernel SIGSEGV ->
# handler prints the trap marker + PASS and exits.
# Staged at tests/u-binary/u_wx_text_ro -> /bin/u_wx_text_ro.
# SKIPs quietly if musl-gcc isn't installed.

MUSL_GCC := $(shell command -v musl-gcc 2>/dev/null)

wx_text_ro: wx_text_ro.c
ifeq ($(MUSL_GCC),)
	@echo "[wx_text_ro] SKIP: musl-gcc not installed."
	@echo "[wx_text_ro]   apt-get install -y musl-tools (needs sudo)"
else
	$(MUSL_GCC) -static-pie -O2 -o wx_text_ro wx_text_ro.c
	# Stamp e_ident[EI_OSABI] = ELFOSABI_LINUX (3).
	printf '\003' | dd of=wx_text_ro bs=1 seek=7 count=1 conv=notrunc 2>/dev/null
endif

install: wx_text_ro
ifeq ($(MUSL_GCC),)
	@echo "[wx_text_ro] SKIP install (no musl-gcc, nothing built)"
else
	cp wx_text_ro ../../u_wx_text_ro
endif

clean:
	rm -f wx_text_ro wx_text_ro.o
