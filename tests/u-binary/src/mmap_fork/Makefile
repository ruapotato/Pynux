mmap_fork: mmap_fork.S
	as -o mmap_fork.o mmap_fork.S
	# Emit a SysV (Linux) ELF: -nostdlib avoids glibc, -static means no
	# dynamic linker. Mirrors tests/u-binary/src/mmap/Makefile.
	ld -nostdlib -static -o mmap_fork mmap_fork.o
	# Set e_ident[EI_OSABI] = ELFOSABI_LINUX (3) so Hamnix's U2
	# detector (elf_is_linux_binary) returns 1. Byte at offset 7.
	# Octal escape \003 (POSIX) — dash's printf has no \x hex escapes.
	printf '\003' | dd of=mmap_fork bs=1 seek=7 count=1 conv=notrunc 2>/dev/null

install: mmap_fork
	cp mmap_fork ../../u_mmap_fork

clean:
	rm -f mmap_fork mmap_fork.o
