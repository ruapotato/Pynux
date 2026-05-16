/* tests/linux-modules/src/atomic/atomic.c
 *
 * The L17 test fixture: exercises atomic_t + delayed_work + kfifo in a
 * single module, since each surface is small and they're all queued
 * under the same milestone. Built with stock kbuild against Linux 6.12
 * headers; the resulting atomic.ko is checked into tests/linux-modules/
 * for CI consumption.
 *
 * Expected serial output on insmod:
 *     L17: atomic round-trip ok
 *     L17: delayed_work queued
 *     L17: kfifo round-trip ok
 *     L17: atomic.ko module_init
 *
 * Followed by, on rmmod:
 *     L17: atomic.ko module_exit
 *
 * Per the L1 shim contract printk is varargs-blind (the shim discards
 * everything past the format string), so this module uses only literal
 * format strings — no %d / %s markers on observed values.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/atomic.h>
#include <linux/workqueue.h>
#include <linux/kfifo.h>
#include <linux/slab.h>

static atomic_t        l17_counter;
static struct kfifo    l17_fifo;
static struct workqueue_struct *l17_wq;
static struct delayed_work      l17_dwork;

static void l17_dwork_fn(struct work_struct *w)
{
    (void)w;
}

static int __init atomic_init(void)
{
    int  val;
    char in_buf[4]  = { 'a', 'b', 'c', 'd' };
    char out_buf[4] = { 0 };

    /* atomic_t round trip. */
    atomic_set(&l17_counter, 0);
    atomic_inc(&l17_counter);
    atomic_inc(&l17_counter);
    val = atomic_add_return(3, &l17_counter);
    atomic_dec(&l17_counter);
    val = atomic_read(&l17_counter);
    if (val == 4) {
        printk(KERN_INFO "L17: atomic round-trip ok\n");
    }

    /* delayed_work — queue then cancel before fire. */
    l17_wq = alloc_workqueue("l17_wq", 0, 1);
    if (l17_wq) {
        INIT_DELAYED_WORK(&l17_dwork, l17_dwork_fn);
        if (queue_delayed_work(l17_wq, &l17_dwork, 5)) {
            printk(KERN_INFO "L17: delayed_work queued\n");
        }
        cancel_delayed_work_sync(&l17_dwork);
    }

    /* kfifo — alloc, in, out, free. */
    if (kfifo_alloc(&l17_fifo, 16, GFP_KERNEL) == 0) {
        kfifo_in(&l17_fifo, in_buf, sizeof(in_buf));
        kfifo_out(&l17_fifo, out_buf, sizeof(out_buf));
        if (out_buf[0] == 'a' && out_buf[3] == 'd') {
            printk(KERN_INFO "L17: kfifo round-trip ok\n");
        }
        kfifo_free(&l17_fifo);
    }

    printk(KERN_INFO "L17: atomic.ko module_init\n");
    return 0;
}

static void __exit atomic_exit(void)
{
    if (l17_wq) {
        destroy_workqueue(l17_wq);
    }
    printk(KERN_INFO "L17: atomic.ko module_exit\n");
}

module_init(atomic_init);
module_exit(atomic_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L17 test fixture - atomic + delayed_work + kfifo");
MODULE_AUTHOR("Hamnix project");
