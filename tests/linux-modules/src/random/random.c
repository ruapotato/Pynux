/* tests/linux-modules/src/random/random.c
 *
 * The L16 test fixture: pulls a small buffer of random bytes via
 * get_random_bytes and asserts the result is not all-zero. Built
 * with stock kbuild against Linux 6.12 headers and stashed at
 * tests/linux-modules/random.ko for the regression .ko suite.
 *
 * Expected serial output on insmod:
 *     L16: random bytes ok
 *     L16: random.ko module_init
 *
 * Followed by, on rmmod:
 *     L16: random.ko module_exit
 *
 * Hamnix's L16 shim is an LCG seeded from jiffies — not a CSPRNG, but
 * it deterministically returns non-zero, input-independent output.
 * That's enough for the "any byte non-zero" assertion this fixture
 * makes. _copy_to_user / _copy_from_user are also exported at L16
 * but they're exercised by the M5.1 chrdev round-trip fixture, not
 * here — keeping this module focused on the random half.
 *
 * Per the L1 shim contract printk is varargs-blind (the shim discards
 * everything past the format string), so this module uses only
 * literal format strings — no %d / %s markers.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <linux/random.h>

static int __init random_init(void)
{
    u8           buf[16];
    unsigned int i;
    int          any_nonzero = 0;

    for (i = 0; i < sizeof(buf); i++)
        buf[i] = 0;

    get_random_bytes(buf, sizeof(buf));

    for (i = 0; i < sizeof(buf); i++) {
        if (buf[i] != 0) {
            any_nonzero = 1;
            break;
        }
    }

    if (any_nonzero)
        printk(KERN_INFO "L16: random bytes ok\n");
    else
        printk(KERN_ERR "L16: random bytes all zero\n");

    printk(KERN_INFO "L16: random.ko module_init\n");
    return 0;
}

static void __exit random_exit(void)
{
    printk(KERN_INFO "L16: random.ko module_exit\n");
}

module_init(random_init);
module_exit(random_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L16 test fixture - get_random_bytes round trip");
MODULE_AUTHOR("Hamnix project");
