/* tests/linux-modules/src/socket/socket.c
 *
 * L28 test fixture: a minimum-meaningful in-kernel socket create / release.
 * Mirrors the structure of the L1 hello/, L4 chrdev/, L27 fs/ fixtures —
 * built via stock kbuild against Linux 6.12, then copied up to
 * tests/linux-modules/socket.ko for the L28 regression slot.
 *
 * Expected serial output when Hamnix's L1 loader insmods this:
 *     L28: socket ok
 *
 * What this exercises:
 *   - sock_create_kern(&init_net, AF_INET, SOCK_STREAM, 0, &sk)
 *     - allocates a slot in api_socket.ad's 16-entry table
 *     - writes the opaque cookie into sk
 *   - sock_release(sk)
 *     - releases the slot
 *
 * What this DOESN'T exercise yet (deferred to a later L milestone when
 * Hamnix has a real network stack):
 *   - kernel_bind / kernel_sendto / kernel_recvfrom — the shims exist
 *     for stray symbol references; this fixture doesn't touch them
 *     because there's no peer to talk to.
 *   - struct socket field access — the cookie is opaque; we never
 *     dereference it.
 *   - SOCK_DGRAM / AF_UNIX variants — covered in their own fixture
 *     when the stack grows multi-family routing.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/net.h>
#include <net/sock.h>

static struct socket *hamnix_l28_sk;

static int __init socket_init(void)
{
    int err = sock_create_kern(&init_net, AF_INET, SOCK_STREAM, 0,
                               &hamnix_l28_sk);
    if (err) {
        printk(KERN_ERR "L28: sock_create_kern failed: %d\n", err);
        return err;
    }
    printk(KERN_INFO "L28: socket ok\n");
    return 0;
}

static void __exit socket_exit(void)
{
    if (hamnix_l28_sk) {
        sock_release(hamnix_l28_sk);
        hamnix_l28_sk = NULL;
    }
    printk(KERN_INFO "L28: socket released\n");
}

module_init(socket_init);
module_exit(socket_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L28 test fixture — kernel socket create/release");
MODULE_AUTHOR("Hamnix project");
