/*
 * tests/u-binary/src/musl_hello/hello.c — U12 fixture.
 *
 * First "real toolchain-built C binary" target for Hamnix's U-track
 * Linux ABI: a musl-libc static-PIE hello-world. Compiled with
 *
 *     musl-gcc -static-pie -O2 -o ../../u_musl_hello hello.c
 *
 * The `-static-pie` matters — it produces an ET_DYN ELF64 with
 * R_X86_64_RELATIVE entries in .rela.dyn, which Hamnix's U10
 * loader already processes. Unlike glibc-static, musl's startup
 * touches only syscalls Hamnix already implements:
 *
 *     arch_prctl(ARCH_SET_FS), set_tid_address, brk,
 *     writev / write, exit_group
 *
 * The body of main() bypasses musl's stdio entirely with a raw
 * write(2) inline syscall — so even if printf's setup glue trips
 * on something musl-internal, the marker string still hits serial
 * if _start → __libc_start_main → main reached us at all.
 *
 * Marker: "U12: musl hello\n" on serial == U12 PASS.
 */

int main(void) {
    /* `volatile` + an explicit "memory" clobber below keeps GCC -O2
     * from optimizing away the stack initialization. With just
     * "r"(msg), the compiler sees the asm only takes a pointer
     * and (correctly) deduces the array contents are never read
     * by C — so it elides the string copy onto the stack and
     * we end up writing 16 bytes of uninitialized stack garbage. */
    volatile char msg[] = "U12: musl hello\n";
    /* musl static-PIE: write(2) is the system call.
     * We hand-roll it here so the only thing standing between us
     * and the kernel is musl's _start/__libc_start_main; main()
     * itself doesn't pull in any libc surface. */
    __asm__ volatile (
        "movq $1, %%rax\n\t"      /* SYS_write */
        "movq $1, %%rdi\n\t"      /* fd=1 */
        "movq %0, %%rsi\n\t"      /* buf */
        "movq $16, %%rdx\n\t"     /* len */
        "syscall\n\t"
        : : "r"(msg) : "rax", "rdi", "rsi", "rdx", "rcx", "r11", "memory"
    );
    return 0;
}
