/* tests/linux-modules/src/irq/irq.c
 *
 * The L11 test fixture: exercises the IRQ-registration surface. Built
 * the same way as the L1/L5/L6 fixtures (stock kbuild against Linux
 * 6.12 headers); the resulting irq.ko is checked into
 * tests/linux-modules/ for CI consumption.
 *
 * Expected serial output on insmod:
 *     L11: irq registered
 *     L11: irq.ko module_init
 *
 * Followed by, on rmmod:
 *     L11: irq.ko module_exit
 *
 * The round-trip exercises:
 *   - request_irq(0x42, ...) with a top-half-only handler
 *   - free_irq(0x42, ...)
 *
 * Hamnix's L11 shims don't wire the IDT yet — request_irq just records
 * the (irq, handler, dev) tuple into a static slot table so a later
 * milestone can route arch/x86/kernel/idt.ad dispatches through it.
 * The handler in this fixture is therefore never actually invoked; it
 * exists so the request_irq call has a non-NULL function pointer to
 * stash (a NULL handler with no thread_fn is -EINVAL in real Linux).
 *
 * Per the L1 shim contract printk is varargs-blind (the shim discards
 * everything past the format string), so this module uses only literal
 * format strings — no %d / %s markers.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/interrupt.h>

#define L11_IRQ_NR 0x42

static irqreturn_t l11_handler(int irq, void *dev_id)
{
    /* Never actually fired at L11 — see file comment. Returning
     * IRQ_HANDLED is the conventional "yes, this device" answer for
     * a non-shared handler. */
    return IRQ_HANDLED;
}

static int __init irq_init(void)
{
    int rc = request_irq(L11_IRQ_NR, l11_handler, 0, "hamnix_l11", NULL);
    if (rc) {
        printk(KERN_INFO "L11: request_irq failed\n");
        return rc;
    }
    printk(KERN_INFO "L11: irq registered\n");
    printk(KERN_INFO "L11: irq.ko module_init\n");
    return 0;
}

static void __exit irq_exit(void)
{
    free_irq(L11_IRQ_NR, NULL);
    printk(KERN_INFO "L11: irq.ko module_exit\n");
}

module_init(irq_init);
module_exit(irq_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L11 test fixture - request_irq / free_irq round trip");
MODULE_AUTHOR("Hamnix project");
