/* tests/linux-modules/src/fs/fs.c
 *
 * L27 test fixture: a minimum-meaningful filesystem-registration round-trip.
 * Mirrors the structure of the L1 hello/, L4 chrdev/, L5 proc/ fixtures —
 * built via stock kbuild against Linux 6.12, then copied up to
 * tests/linux-modules/fs.ko for the L27 regression slot.
 *
 * Expected serial output when Hamnix's L1 loader insmods this:
 *     L27: fs registered
 *
 * Followed by, on rmmod:
 *     L27: fs unregistered
 *
 * What this exercises:
 *   - register_filesystem(&hamnix_l27_fs_type)
 *     - reads fs_type->name from offset 0
 *     - allocates a 16-slot table entry
 *   - unregister_filesystem(&hamnix_l27_fs_type)
 *     - releases the slot
 *
 * What this DOESN'T exercise yet (deferred to a later L milestone when
 * Hamnix's VFS plumbs a real mount(2) into a registered fs):
 *   - mount_nodev / kill_litter_super — fs_type->mount is provided so
 *     the module is well-formed, but it's never invoked at L27 because
 *     no mount(2) is dispatched.
 *   - iget_locked / unlock_new_inode / iput — the shims exist for stray
 *     symbol references; the fixture doesn't touch them.
 *   - fill_super callbacks — same story; the function is here so the
 *     module compiles as a complete filesystem driver, but it never
 *     runs at L27.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/fs.h>

static int hamnix_l27_fill_super(struct super_block *sb, void *data,
                                 int silent)
{
    /* Never invoked at L27 (no mount(2) plumbing yet). Returning 0
     * would be the "I built a sb" success path; we keep the body
     * trivial so the symbol resolves cleanly during module load.
     */
    return 0;
}

static struct dentry *hamnix_l27_mount(struct file_system_type *fs_type,
                                       int flags, const char *dev_name,
                                       void *data)
{
    return mount_nodev(fs_type, flags, data, hamnix_l27_fill_super);
}

static struct file_system_type hamnix_l27_fs_type = {
    .owner   = THIS_MODULE,
    .name    = "hamnix_l27",
    .mount   = hamnix_l27_mount,
    .kill_sb = kill_litter_super,
    .fs_flags = 0,
};

static int __init fs_init(void)
{
    int err = register_filesystem(&hamnix_l27_fs_type);
    if (err) {
        printk(KERN_ERR "L27: register_filesystem failed: %d\n", err);
        return err;
    }
    printk(KERN_INFO "L27: fs registered\n");
    return 0;
}

static void __exit fs_exit(void)
{
    unregister_filesystem(&hamnix_l27_fs_type);
    printk(KERN_INFO "L27: fs unregistered\n");
}

module_init(fs_init);
module_exit(fs_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L27 test fixture — filesystem registration round-trip");
MODULE_AUTHOR("Hamnix project");
