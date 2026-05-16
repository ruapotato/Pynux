/* tests/linux-modules/src/utsname/utsname.c
 *
 * The L18 test fixture: exercises init_uts_ns (data symbol) and
 * smp_processor_id (function symbol). Built with stock kbuild
 * against Linux 6.12 headers; the resulting utsname.ko is checked
 * into tests/linux-modules/ for CI consumption.
 *
 * Expected serial output on insmod:
 *     L18: utsname.release readable
 *     L18: smp_processor_id ok
 *     L18: utsname.ko module_init
 *
 * Followed by, on rmmod:
 *     L18: utsname.ko module_exit
 *
 * Per the L1 shim contract printk is varargs-blind, so this module
 * uses only literal format strings — no %s on the release string.
 * The "readable" check just confirms the first byte isn't NUL, which
 * means the L18 shim populated the buffer.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/utsname.h>
#include <linux/smp.h>

static int __init utsname_init(void)
{
    int cpu;

    /* utsname()->release expands to init_uts_ns.name.release —
     * pulls the address of the L18 shim's static buffer. */
    if (init_utsname()->release[0] != '\0') {
        printk(KERN_INFO "L18: utsname.release readable\n");
    }

    cpu = smp_processor_id();
    if (cpu == 0) {
        printk(KERN_INFO "L18: smp_processor_id ok\n");
    }

    printk(KERN_INFO "L18: utsname.ko module_init\n");
    return 0;
}

static void __exit utsname_exit(void)
{
    printk(KERN_INFO "L18: utsname.ko module_exit\n");
}

module_init(utsname_init);
module_exit(utsname_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L18 test fixture - init_uts_ns + smp_processor_id");
MODULE_AUTHOR("Hamnix project");
