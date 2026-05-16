/* tests/linux-modules/src/crypto/crypto.c
 *
 * The L15 test fixture: alloc a synchronous SHA-256 transform, hash
 * a short literal string, verify the output is non-zero. Built with
 * stock kbuild against Linux 6.12 headers and stashed at
 * tests/linux-modules/crypto.ko for the regression .ko suite.
 *
 * Expected serial output on insmod:
 *     L15: crypto digest ok
 *     L15: crypto.ko module_init
 *
 * Followed by, on rmmod:
 *     L15: crypto.ko module_exit
 *
 * The L15 Hamnix shim doesn't implement real SHA-256 — it folds the
 * input via XOR and replicates the result across the digest. That's
 * enough for this fixture: any non-empty input produces a non-zero
 * digest, and we only assert the "any byte non-zero" condition.
 *
 * Per the L1 shim contract printk is varargs-blind (the shim
 * discards everything past the format string), so this module uses
 * only literal format strings — no %d / %s markers.
 */

#include <linux/module.h>
#include <linux/kernel.h>
#include <crypto/hash.h>

static int __init crypto_init(void)
{
    struct crypto_shash *tfm;
    unsigned int        dsize;
    u8                  out[32];
    unsigned int        i;
    int                 any_nonzero = 0;
    int                 rc;
    static const char   data[] = "hello";

    tfm = crypto_alloc_shash("sha256", 0, 0);
    if (!tfm || IS_ERR(tfm)) {
        printk(KERN_ERR "L15: crypto_alloc_shash failed\n");
        return 0;
    }

    dsize = crypto_shash_digestsize(tfm);
    if (dsize == 0 || dsize > sizeof(out)) {
        printk(KERN_ERR "L15: bad digest size\n");
        crypto_free_shash(tfm);
        return 0;
    }

    for (i = 0; i < sizeof(out); i++)
        out[i] = 0;

    rc = crypto_shash_tfm_digest(tfm, data, sizeof(data) - 1, out);
    if (rc != 0) {
        printk(KERN_ERR "L15: crypto_shash_tfm_digest failed\n");
        crypto_free_shash(tfm);
        return 0;
    }

    for (i = 0; i < dsize; i++) {
        if (out[i] != 0) {
            any_nonzero = 1;
            break;
        }
    }

    crypto_free_shash(tfm);

    if (any_nonzero)
        printk(KERN_INFO "L15: crypto digest ok\n");
    else
        printk(KERN_ERR "L15: digest all zero\n");

    printk(KERN_INFO "L15: crypto.ko module_init\n");
    return 0;
}

static void __exit crypto_exit(void)
{
    printk(KERN_INFO "L15: crypto.ko module_exit\n");
}

module_init(crypto_init);
module_exit(crypto_exit);
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Hamnix L15 test fixture - crypto_shash round trip");
MODULE_AUTHOR("Hamnix project");
