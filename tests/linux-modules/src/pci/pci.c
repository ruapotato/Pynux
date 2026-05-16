/* tests/linux-modules/src/pci/pci.c
 *
 * L21 test fixture: PCI driver registration. Mirrors the structure of
 * the L1 hello / L4 chrdev / L5 proc fixtures — stock kbuild against
 * Linux 6.12 headers, ko gets copied up to tests/linux-modules/pci.ko
 * for the L21 regression slot.
 *
 * Expected serial output when Hamnix's L1 loader insmods this:
 *     L21: pci registered
 *     L21: pci unregistered                  (on rmmod)
 *
 * What this exercises:
 *   - pci_register_driver (→ __pci_register_driver)  : slot-table claim
 *   - pci_unregister_driver                          : slot release
 *   - struct pci_driver + struct pci_device_id table : ABI layout
 *
 * What this DOESN'T exercise yet (deferred to a later L milestone):
 *   - drv->probe(pdev) being invoked from the PCI bus walk. Hamnix's
 *     drivers/pci/pci.ad already enumerates devices, but the wiring
 *     from "enumerated device" to "registered driver whose id_table
 *     matches" lands separately. The probe callback below is present
 *     so the struct pci_driver is shaped correctly, not because it
 *     fires.
 *
 * Device under match: vendor 0x1AF4 (Red Hat / virtio), device 0x1001
 * (virtio-blk). QEMU's default machine attaches this when -drive is
 * given, which is the same setup Hamnix uses for the existing PCI
 * scan test. When probe wiring lands, this fixture will fire on the
 * same device the bus walker already prints.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/pci.h>

#define HAMNIX_L21_NAME "hamnix_l21_pci"

#define PCI_VENDOR_ID_REDHAT_QUMRANET 0x1AF4
#define PCI_DEVICE_ID_VIRTIO_BLK      0x1001

static int hamnix_l21_probe(struct pci_dev *pdev,
                            const struct pci_device_id *id)
{
    /* Not invoked at L21 — bus-walk dispatch isn't wired into the
     * driver table yet. The body is shaped like a real probe so the
     * next milestone's wiring lands with a meaningful callback target.
     */
    int ret;

    ret = pci_enable_device(pdev);
    if (ret)
        return ret;
    pci_set_master(pdev);
    ret = pci_request_regions(pdev, HAMNIX_L21_NAME);
    if (ret) {
        pci_disable_device(pdev);
        return ret;
    }
    return 0;
}

static void hamnix_l21_remove(struct pci_dev *pdev)
{
    pci_release_regions(pdev);
    pci_disable_device(pdev);
}

static const struct pci_device_id hamnix_l21_id_table[] = {
    { PCI_DEVICE(PCI_VENDOR_ID_REDHAT_QUMRANET, PCI_DEVICE_ID_VIRTIO_BLK) },
    { 0, },
};
MODULE_DEVICE_TABLE(pci, hamnix_l21_id_table);

static struct pci_driver hamnix_l21_driver = {
    .name     = HAMNIX_L21_NAME,
    .id_table = hamnix_l21_id_table,
    .probe    = hamnix_l21_probe,
    .remove   = hamnix_l21_remove,
};

static int __init pci_test_init(void)
{
    int ret;

    ret = pci_register_driver(&hamnix_l21_driver);
    if (ret) {
        printk(KERN_ERR "L21: pci_register_driver failed\n");
        return ret;
    }
    printk(KERN_INFO "L21: pci registered\n");
    return 0;
}

static void __exit pci_test_exit(void)
{
    pci_unregister_driver(&hamnix_l21_driver);
    printk(KERN_INFO "L21: pci unregistered\n");
}

module_init(pci_test_init);
module_exit(pci_test_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L21 test fixture - pci_register_driver round trip");
MODULE_AUTHOR("Hamnix project");
