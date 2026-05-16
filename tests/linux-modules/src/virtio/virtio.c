/* tests/linux-modules/src/virtio/virtio.c
 *
 * L23 test fixture: register a virtio_driver for VIRTIO_ID_BLOCK
 * and print a banner. Mirrors the structure of the L4 chrdev/ and
 * L7 sync/ fixtures — built via stock kbuild against Linux 6.12,
 * then copied up to tests/linux-modules/virtio.ko for the L23
 * regression slot.
 *
 * Expected serial output when Hamnix's L1 loader insmods this:
 *     L23: virtio registered
 *     L23: virtio unregistered                 (on rmmod)
 *
 * What this exercises:
 *   - register_virtio_driver(&drv)        -> L23 driver-table insertion
 *   - unregister_virtio_driver(&drv)      -> cleanup symmetry
 *   - struct virtio_driver definition     -> opaque-blob handling in
 *                                            api_virtio.ad
 *
 * What this DOESN'T exercise yet (deferred to later L milestones):
 *   - register_virtio_device / unregister_virtio_device — the L1
 *     loader doesn't enumerate virtio devices at insmod time, so
 *     drv->probe is never called.
 *   - virtqueue_add_sgs / virtqueue_kick / virtqueue_get_buf — those
 *     symbols are exported by api_virtio.ad but only get called from
 *     a driver's probe path, which we don't reach yet.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/virtio.h>
#include <linux/virtio_ids.h>

static const struct virtio_device_id l23_id_table[] = {
    { VIRTIO_ID_BLOCK, VIRTIO_DEV_ANY_ID },
    { 0 },
};

static int l23_probe(struct virtio_device *vdev)
{
    /* Never reached at L23 — no virtio_device is registered against
     * the bus, so the matcher never fires. Kept here for symmetry
     * with a real driver. */
    return 0;
}

static void l23_remove(struct virtio_device *vdev)
{
    /* Symmetric: never reached at L23. */
}

static struct virtio_driver l23_drv = {
    .driver.name = "hamnix_l23",
    .id_table    = l23_id_table,
    .probe       = l23_probe,
    .remove      = l23_remove,
};

static int __init virtio_init(void)
{
    int ret = register_virtio_driver(&l23_drv);
    if (ret < 0) {
        printk(KERN_ERR "L23: register_virtio_driver failed\n");
        return ret;
    }
    printk(KERN_INFO "L23: virtio registered\n");
    return 0;
}

static void __exit virtio_exit(void)
{
    unregister_virtio_driver(&l23_drv);
    printk(KERN_INFO "L23: virtio unregistered\n");
}

module_init(virtio_init);
module_exit(virtio_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L23 test fixture - register_virtio_driver round-trip");
MODULE_AUTHOR("Hamnix project");
