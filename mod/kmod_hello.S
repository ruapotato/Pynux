/*
 * mod/kmod_hello.S - sample loadable kernel module.
 *
 * Demonstrates Pynux's M16.32 module loader. The kernel ELF-loads
 * this binary into kernel-mode memory and calls `init_module` at
 * CPL=0 with a Ptr[ModuleApi] in %rdi.
 *
 * struct ModuleApi (defined in arch/x86/kernel/module_api.py):
 *   offset 0  printk_str (void (*)(const char *))
 *   offset 8  kmalloc    (void *(*)(uint64))
 *   offset 16 kfree      (void (*)(void *))
 *
 * Module convention (mirrors Linux's loadable module ABI at minimal
 * scale):
 *   - init_module returns int32 (0 on success, negative on error)
 *   - Position-independent code only (no .got, no .plt)
 */

    .code64
    .section .text, "ax"

    .globl init_module
init_module:
    /* %rdi = Ptr[ModuleApi]. Save it because the API call will
     * clobber %rdi when we put our string-arg there. */
    movq    %rdi, %rbx

    /* api->printk_str("[kmod_hello] init_module called!\n") */
    leaq    kmod_hello_msg(%rip), %rdi
    movq    (%rbx), %rax              /* api[0] = printk_str */
    call    *%rax

    /* kmalloc(64) — let's verify the slab path works from a module. */
    movq    $64, %rdi
    movq    8(%rbx), %rax             /* api[1] = kmalloc */
    call    *%rax
    movq    %rax, %r12                 /* save allocated address */

    /* Print success line; second printk_str call. */
    leaq    kmod_hello_alloced(%rip), %rdi
    movq    (%rbx), %rax
    call    *%rax

    /* kfree(p) */
    movq    %r12, %rdi
    movq    16(%rbx), %rax            /* api[2] = kfree */
    call    *%rax

    /* return 0 */
    xorl    %eax, %eax
    ret

    .balign 8
kmod_hello_msg:
    .asciz "[kmod_hello] init_module called!\n"
kmod_hello_alloced:
    .asciz "[kmod_hello] kmalloc + kfree round-trip OK; returning 0.\n"
