/* tests/linux-modules/src/dma/dma.c
 *
 * L22 test fixture: dma_alloc_coherent + dma_free_coherent round
 * trip on a single 4 KiB buffer. Same kbuild shape as the L1/L4/L21
 * fixtures; output ko is copied to tests/linux-modules/dma.ko for
 * the L22 regression slot.
 *
 * Expected serial output on insmod:
 *     L22: dma ok
 *     L22: dma.ko module_init
 *
 * Followed by, on rmmod:
 *     L22: dma.ko module_exit
 *
 * What this exercises:
 *   - dma_alloc_coherent  (4 KiB, GFP_KERNEL) - shim records the
 *                         (size, addr) pair in its 8-slot table.
 *   - dma_free_coherent   - matching release, slot cleared.
 *
 * What this DOESN'T exercise yet:
 *   - dma_map_single / dma_unmap_single  - the streaming path. Those
 *     are exported by L22's shim but no upstream-shaped driver pulls
 *     them in a way the L1 loader could reach yet (the streaming
 *     dance is per-transaction inside a driver's xmit/rx callbacks).
 *     A virtio-net fixture will exercise that surface in a later L.
 *
 * The shim's NULL-dev tolerance lets us pass NULL for `dev` instead of
 * constructing a struct device; real drivers pass &pdev->dev and the
 * Hamnix-side IOMMU path (currently absent) would use it. Passing NULL
 * here keeps the fixture self-contained.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/dma-mapping.h>

#define HAMNIX_L22_BUF_SIZE (4 * 1024)

static int __init dma_test_init(void)
{
    void *cpu_addr;
    dma_addr_t dma_handle;

    cpu_addr = dma_alloc_coherent(NULL, HAMNIX_L22_BUF_SIZE,
                                  &dma_handle, GFP_KERNEL);
    if (!cpu_addr) {
        printk(KERN_ERR "L22: dma_alloc_coherent failed\n");
        return -ENOMEM;
    }

    dma_free_coherent(NULL, HAMNIX_L22_BUF_SIZE, cpu_addr, dma_handle);

    printk(KERN_INFO "L22: dma ok\n");
    printk(KERN_INFO "L22: dma.ko module_init\n");
    return 0;
}

static void __exit dma_test_exit(void)
{
    printk(KERN_INFO "L22: dma.ko module_exit\n");
}

module_init(dma_test_init);
module_exit(dma_test_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L22 test fixture - dma_alloc_coherent round trip");
MODULE_AUTHOR("Hamnix project");
