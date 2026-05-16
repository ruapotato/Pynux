/* tests/linux-modules/src/netdev/netdev.c
 *
 * L25 test fixture: a minimum-meaningful net_device registration.
 * Mirrors the structure of the L1 hello/, L4 chrdev/, L8 workq/
 * fixtures - built via stock kbuild against Linux 6.12, then copied
 * up to tests/linux-modules/netdev.ko for the regression run.
 *
 * Expected serial output when Hamnix's L1 loader insmods this:
 *     L25: netdev registered
 *     L25: netdev unregistered            (on rmmod)
 *
 * What this exercises:
 *   - alloc_etherdev_mqs(0, 1, 1)          - 2 KiB blob handed back
 *   - register_netdev(dev)                 - slot promoted to live
 *   - unregister_netdev(dev) / free_netdev - teardown symmetry
 *
 * What this DOESN'T exercise yet (deferred to later L milestones):
 *   - netdev_ops vtable (open/stop/start_xmit) - L25 doesn't dispatch
 *   - netif_start_queue / netif_carrier_on  - covered when a real
 *     RX/TX path lands; for now the shims are wired but no module
 *     test reads them back through ethtool / sysfs
 *   - dev_alloc_skb / kfree_skb / eth_type_trans - exercised once
 *     the RX simulator can hand a synthetic skb to the chain
 *
 * Per the L1 shim contract printk is varargs-blind, so this module
 * uses only literal format strings.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/netdevice.h>
#include <linux/etherdevice.h>

static struct net_device *l25_dev;

static int __init netdev_init_mod(void)
{
    l25_dev = alloc_etherdev_mqs(0, 1, 1);
    if (!l25_dev) {
        printk(KERN_ERR "L25: alloc_etherdev_mqs failed\n");
        return -ENOMEM;
    }

    if (register_netdev(l25_dev)) {
        printk(KERN_ERR "L25: register_netdev failed\n");
        free_netdev(l25_dev);
        l25_dev = NULL;
        return -EINVAL;
    }

    printk(KERN_INFO "L25: netdev registered\n");
    return 0;
}

static void __exit netdev_exit_mod(void)
{
    if (l25_dev) {
        unregister_netdev(l25_dev);
        free_netdev(l25_dev);
        l25_dev = NULL;
    }
    printk(KERN_INFO "L25: netdev unregistered\n");
}

module_init(netdev_init_mod);
module_exit(netdev_exit_mod);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L25 test fixture - alloc_etherdev_mqs + register_netdev round trip");
MODULE_AUTHOR("Hamnix project");
