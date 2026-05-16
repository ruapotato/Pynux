/* tests/linux-modules/src/kprobe/kprobe.c
 *
 * The L13 test fixture (M7.1 / M14.1 / M14.2): exercises the kprobe
 * registration ABI. Builds as a stock Linux 6.12 module via kbuild,
 * lands at tests/linux-modules/kprobe.ko for the regression suite.
 *
 * Expected serial output on insmod:
 *     L13: kprobe registered
 *     L13: kprobe.ko module_init
 *
 * Followed by, on rmmod:
 *     L13: kprobe.ko module_exit
 *
 * The cycle exercises:
 *   - register_kprobe     (records the probe in our 16-slot table)
 *   - unregister_kprobe   (clears the slot on exit)
 *
 * Per the L13 shim contract, Hamnix does NOT actually patch kernel
 * text — register_kprobe just records (probe_ptr, symbol, pre_handler,
 * post_handler). So the pre_handler defined below never fires under
 * Hamnix; it exists for symmetry with what stock kprobes would invoke
 * when the breakpoint trips. Under a real Linux host, loading this
 * module on a kernel that has do_sys_open exported would log "L13:
 * pre_handler fired" on every open() syscall.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/kprobes.h>

static int l13_pre_handler(struct kprobe *p, struct pt_regs *regs)
{
    /* Hamnix's L13 shim never invokes this — see file header. The
     * body is kept printk-only so it matches the L1..L12 "varargs
     * blind" contract (no %d/%s tokens). */
    printk(KERN_INFO "L13: pre_handler fired\n");
    return 0;
}

static struct kprobe l13_kp = {
    .symbol_name = "do_sys_open",
    .pre_handler = l13_pre_handler,
};

static int __init kprobe_init_mod(void)
{
    int ret = register_kprobe(&l13_kp);
    if (ret < 0) {
        printk(KERN_INFO "L13: register_kprobe failed\n");
        return ret;
    }
    printk(KERN_INFO "L13: kprobe registered\n");
    printk(KERN_INFO "L13: kprobe.ko module_init\n");
    return 0;
}

static void __exit kprobe_exit_mod(void)
{
    unregister_kprobe(&l13_kp);
    printk(KERN_INFO "L13: kprobe.ko module_exit\n");
}

module_init(kprobe_init_mod);
module_exit(kprobe_exit_mod);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L13 test fixture - kprobe register/unregister");
MODULE_AUTHOR("Hamnix project");
