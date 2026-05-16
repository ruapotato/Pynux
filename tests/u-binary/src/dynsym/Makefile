dynsym: dynsym.S
	as -o dynsym.o dynsym.S
	# -shared (NOT -pie) is what makes the linker emit an actual
	# R_X86_64_64 entry against the weak undefined __vdso_clock_gettime
	# symbol, with a .dynsym row for it. With plain -pie + --no-
	# dynamic-linker, ld resolves weak undefs to 0 statically and
	# the .rela.dyn ends up empty — no test signal.
	#
	# ET_DYN (which -shared produces) is what Hamnix's ELF64 loader
	# already accepts for static-PIE binaries. The static-PIE u_pie
	# fixture is also ET_DYN; the only practical difference here is
	# the dynsym entry.
	#
	# -e _start sets the ELF entry point; -shared defaults to "no
	# entry point", which the loader then rejects. The hello / pie
	# fixtures get _start as the entry implicitly via -pie or via
	# the default ET_EXEC layout; -shared needs it explicit.
	ld -shared -nostdlib -e _start -o dynsym dynsym.o
	# Set e_ident[EI_OSABI] = ELFOSABI_LINUX (3) at byte 7 so
	# elf_is_linux_binary returns 1 and the loaded image flips the
	# task's is_linux_userspace flag. Use octal \003 (POSIX) — dash's
	# printf doesn't grok hex escapes.
	printf '\003' | dd of=dynsym bs=1 seek=7 count=1 conv=notrunc 2>/dev/null

install: dynsym
	cp dynsym ../../u_dynsym

clean:
	rm -f dynsym dynsym.o
