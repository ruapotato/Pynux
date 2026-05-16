/* tests/linux-modules/src/debugfs/debugfs.c
 *
 * The L14 test fixture (M11.2): exercises the debugfs registration
 * ABI. Builds as a stock Linux 6.12 module via kbuild, lands at
 * tests/linux-modules/debugfs.ko for the regression suite.
 *
 * Expected serial output on insmod:
 *     L14: debugfs entries created
 *     L14: debugfs.ko module_init
 *
 * Followed by, on rmmod:
 *     L14: debugfs.ko module_exit
 *
 * The cycle exercises:
 *   - debugfs_create_dir       (claims a slot, kind=DIR)
 *   - debugfs_create_u32       (claims a slot, kind=U32, mode 0644)
 *   - debugfs_remove           (clears child then parent on exit)
 *
 * Per the L14 shim contract, Hamnix's debugfs ABI is registration-
 * shaped only — no read-path dispatch yet, so /sys/kernel/debug/
 * hamnix_l14/counter is not yet observable from userspace. The
 * test is satisfied by non-NULL dentry returns + clean rmmod.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/debugfs.h>

static struct dentry *l14_dir;
static struct dentry *l14_counter;
static u32 my_u32;

static int __init debugfs_init_mod(void)
{
    l14_dir = debugfs_create_dir("hamnix_l14", NULL);
    l14_counter = debugfs_create_u32("counter", 0644, l14_dir, &my_u32);
    printk(KERN_INFO "L14: debugfs entries created\n");
    printk(KERN_INFO "L14: debugfs.ko module_init\n");
    return 0;
}

static void __exit debugfs_exit_mod(void)
{
    /* Remove child before parent so the slot-clear walks the right
     * order under Hamnix's flat L14 model (no recursive remove yet). */
    debugfs_remove(l14_counter);
    debugfs_remove(l14_dir);
    printk(KERN_INFO "L14: debugfs.ko module_exit\n");
}

module_init(debugfs_init_mod);
module_exit(debugfs_exit_mod);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L14 test fixture - debugfs dir/u32 register");
MODULE_AUTHOR("Hamnix project");
