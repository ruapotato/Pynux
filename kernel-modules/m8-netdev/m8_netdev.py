# Pynux M8.3: a dummy ethernet net_device.
#
# alloc_etherdev_mqs() allocates a struct net_device with priv data,
# we wire up Pynux ndo_open / ndo_stop / ndo_start_xmit / ndo_validate_addr
# into a net_device_ops vtable, set dev->netdev_ops, and register_netdev.
# The device shows up in `ip link show` with a kernel-assigned name
# (eth1 in our QEMU layout since eth0 is virtio-net).
#
# The xmit handler just kfree_skb's whatever is given to it — a true
# blackhole device. Bringing the interface up + assigning an IP from
# /init causes the kernel to send through us; we count the calls.

extern def alloc_etherdev_mqs(sizeof_priv: int32, txqs: uint32,
                              rxqs: uint32) -> Ptr[uint8]
extern def free_netdev(dev: Ptr[uint8])
extern def register_netdev(dev: Ptr[uint8]) -> int32
extern def unregister_netdev(dev: Ptr[uint8])
extern def eth_validate_addr(dev: Ptr[uint8]) -> int32
# kfree_skb is inline; use consume_skb (the same path the kernel uses
# when an skb has been successfully processed, not dropped on error).
extern def consume_skb(skb: Ptr[uint8])
extern def memcpy(dst: Ptr[uint8], src: Ptr[uint8], n: uint64) -> Ptr[uint8]
extern def _printk(fmt: str, val: int32) -> int32


# struct net_device_ops (680 bytes). Pad-then-field layout for just the
# four entries we set.
class NetDeviceOps:
    pad_pre_open:       Array[16, uint8]    # 0..16
    ndo_open:           Ptr[uint8]          # 16
    ndo_stop:           Ptr[uint8]          # 24
    ndo_start_xmit:     Ptr[uint8]          # 32
    pad_after_xmit:     Array[40, uint8]    # 40..80
    ndo_validate_addr:  Ptr[uint8]          # 80
    pad_end:            Array[592, uint8]   # 88..680


NETDEV_OPS_OFF:      int32  = 8       # offsetof(net_device, netdev_ops)
NETDEV_DEV_ADDR_OFF: int32  = 976     # offsetof(net_device, dev_addr) — Ptr to mac bytes
NETDEV_TX_OK:        uint32 = 0


pynux_netops:     NetDeviceOps
pynux_netdev:     Ptr[uint8]
pynux_xmit_count: int32
# A locally-administered MAC (02:AB:CD:EF:01:23). Locally-administered
# bit (bit 1 of byte 0) is set, multicast bit (bit 0) clear.
pynux_mac: Array[6, uint8]


def pynux_open(dev: Ptr[uint8]) -> int32:
    _printk("[NET] ndo_open called\n", 0)
    return 0


def pynux_stop(dev: Ptr[uint8]) -> int32:
    _printk("[NET] ndo_stop called\n", 0)
    return 0


def pynux_xmit(skb: Ptr[uint8], dev: Ptr[uint8]) -> uint32:
    pynux_xmit_count = pynux_xmit_count + 1
    consume_skb(skb)
    return NETDEV_TX_OK


def init_module() -> int32:
    pynux_netops.ndo_open = pynux_open
    pynux_netops.ndo_stop = pynux_stop
    pynux_netops.ndo_start_xmit = pynux_xmit
    pynux_netops.ndo_validate_addr = eth_validate_addr

    pynux_netdev = alloc_etherdev_mqs(0, 1, 1)
    if pynux_netdev == 0:
        _printk("[NET] alloc_etherdev_mqs FAILED\n", 0)
        return -12

    ops_ptr: Ptr[uint8] = &pynux_netops
    memcpy(pynux_netdev + NETDEV_OPS_OFF, &ops_ptr, 8)

    # Set a non-zero MAC so eth_validate_addr passes and ifconfig can
    # bring the interface up.
    pynux_mac[0] = 2          # locally-administered
    pynux_mac[1] = 0xab
    pynux_mac[2] = 0xcd
    pynux_mac[3] = 0xef
    pynux_mac[4] = 0x01
    pynux_mac[5] = 0x23
    dev_addr_ptr: Ptr[uint8] = 0
    memcpy(&dev_addr_ptr, pynux_netdev + NETDEV_DEV_ADDR_OFF, 8)
    memcpy(dev_addr_ptr, &pynux_mac, 6)

    rc: int32 = register_netdev(pynux_netdev)
    _printk("[NET] register_netdev rc = %d\n", rc)
    if rc != 0:
        free_netdev(pynux_netdev)
        pynux_netdev = 0
        return rc
    return 0


def cleanup_module():
    if pynux_netdev != 0:
        unregister_netdev(pynux_netdev)
        free_netdev(pynux_netdev)
    _printk("[NET] xmit_count = %d\n", pynux_xmit_count)
    _printk("[NET] unregistered\n", 0)
