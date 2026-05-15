/*
 * mod/module.lds - linker script for Hamnix kernel modules.
 *
 * Same elf32-i386 wrapper as the kernel image and user binaries.
 * Modules are position-independent (RIP-relative throughout); link
 * base = 0 so the kernel loader can place them at any address.
 *
 * Modules export `init_module` — the kernel calls it at CPL=0 with
 * a Ptr[ModuleApi] in %rdi. Future `cleanup_module` will be looked
 * up by name (or via a symbol table) when rmmod-equivalent lands.
 */

OUTPUT_FORMAT("elf32-i386")
OUTPUT_ARCH(i386)
ENTRY(init_module)

PHDRS {
    text PT_LOAD;
}

SECTIONS
{
    . = 0;

    .text : ALIGN(16) {
        *(.text)
        *(.text.*)
        *(.rodata)
        *(.rodata.*)
    } : text

    /DISCARD/ : {
        *(.note.*)
        *(.comment)
        *(.eh_frame)
        *(.eh_frame_hdr)
    }
}
