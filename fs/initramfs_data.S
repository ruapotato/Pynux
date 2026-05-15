/*
 * fs/initramfs_data.S - raw file content for the baked-in initramfs.
 *
 * Pynux's codegen can't initialise global byte arrays with string
 * literals yet, so the file payloads live here as `.ascii` blobs in
 * .rodata and accessor functions return their start address + length.
 * Mirrors what Linux's initramfs cpio archive does at link time (the
 * kernel image embeds the bytes; the boot-time unpack reads them in
 * place), just without the cpio framing.
 *
 * Initial fileset:
 *   /motd      welcome banner read by the M16.21 user demo
 *   /version   short version string
 *
 * Accessors exposed to Pynux:
 *   initramfs_entry_count()         -> uint64 (number of files)
 *   initramfs_entry_name(idx)       -> Ptr[char]  (NUL-terminated)
 *   initramfs_entry_data(idx)       -> Ptr[uint8]
 *   initramfs_entry_size(idx)       -> uint64
 *
 * Implementation: a tiny lookup table of 3-quad entries in .rodata,
 * each (name_ptr, data_ptr, size). The accessors index into it.
 */

    .code64

/* ---------- File contents ---------------------------------------- */
    .section .rodata
    .align 4

motd_name:
    .asciz "/motd"
motd_data:
    .ascii "Welcome to Pynux from a real VFS!\n"
    .ascii "/motd was read via SYS_OPEN + SYS_READ + SYS_CLOSE.\n"
motd_data_end:

version_name:
    .asciz "/version"
version_data:
    .ascii "Pynux bare-metal kernel, M16.21\n"
version_data_end:

/* ---------- Entry table (3 longs per entry: name, data, size) ----
 * Use .long because absolute references in elf32-i386 must fit in
 * 32 bits — all our addresses do (<4 GiB load). The accessors below
 * load each field as a 32-bit value and zero-extend.
 */
    .align 4
initramfs_table:
    /* entry 0: /motd */
    .long motd_name
    .long motd_data
    .long motd_data_end - motd_data
    /* entry 1: /version */
    .long version_name
    .long version_data
    .long version_data_end - version_data

initramfs_entry_count_word:
    .long 2

/* ---------- Accessors ------------------------------------------- *
 * Use leaq RIP-relative to dodge BFD_RELOC_X86_64_32S (absolute
 * symbol references that elf32-i386 can't hold), as elsewhere.
 */
    .section .text, "ax"

    .align 16
    .globl initramfs_entry_count
initramfs_entry_count:
    leaq    initramfs_entry_count_word(%rip), %rax
    movl    (%rax), %eax
    ret

    /* Each table entry is 12 bytes: 3x .long (name, data, size). */
    .align 16
    .globl initramfs_entry_name
initramfs_entry_name:
    /* %rdi = idx ; returns Ptr[char] = entry[idx].name */
    leaq    initramfs_table(%rip), %rax
    imulq   $12, %rdi, %rdx
    addq    %rdx, %rax
    movl    (%rax), %eax              /* name_ptr (zero-extends)    */
    ret

    .align 16
    .globl initramfs_entry_data
initramfs_entry_data:
    leaq    initramfs_table(%rip), %rax
    imulq   $12, %rdi, %rdx
    addq    %rdx, %rax
    movl    4(%rax), %eax             /* data_ptr                   */
    ret

    .align 16
    .globl initramfs_entry_size
initramfs_entry_size:
    leaq    initramfs_table(%rip), %rax
    imulq   $12, %rdi, %rdx
    addq    %rdx, %rax
    movl    8(%rax), %eax             /* size                       */
    ret
