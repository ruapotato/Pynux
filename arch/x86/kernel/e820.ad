# arch/x86/kernel/e820.py
#
# Mirrors arch/x86/kernel/e820.c in Linux at the bit that matters most
# for early boot: walking the firmware-reported memory map and turning
# it into something the allocators can trust. Linux gets its map from
# the BIOS e820 call (or EFI memmap) packaged into a boot_params
# struct; we get the same information from the multiboot1 info struct
# that QEMU's `-kernel` loader hands us via EBX at the 32-bit entry
# point. arch/x86/boot/header.S stashed the pointer into the `mb_info`
# global; boot_info_asm.S exposes a read accessor.
#
# Multiboot1 info struct (only the slots we read):
#   offset  0:  flags         (uint32)
#   offset 44:  mmap_length   (uint32)         iff flags & (1 << 6)
#   offset 48:  mmap_addr     (uint32)
#
# Each memory-map entry, packed (NOTE: 64-bit fields are 4-byte
# aligned, not 8 — x86_64 tolerates the unaligned read):
#   offset 0:  size_of_this_entry   (uint32, NOT counting itself)
#   offset 4:  base                 (uint64)
#   offset 12: length               (uint64)
#   offset 20: type                 (uint32)
#
# Type code 1 = "available RAM" (the only one we feed to memblock).
# 2 = reserved, 3 = ACPI reclaimable, 4 = NVS, 5 = bad. The other
# kinds we just log for visibility.
#
# Strategy: walk the entries, print each, find the LARGEST available
# region whose base is >= MIN_BASE (= 2 MiB — keeps our kernel image
# out of the way), and call memblock_set_region() to widen memblock's
# pool to that region. With QEMU's default 256 MiB map this means
# memblock typically grows from the hardcoded 2..240 MiB to the full
# ~256 MiB usable.

from kernel.printk.printk import printk0, printk1, printk2
from mm.memblock import memblock_set_region

extern def get_mb_info() -> uint64
extern def get_mb_magic() -> uint64

MULTIBOOT_BOOTLOADER_MAGIC: uint64 = 0x2BADB002
MULTIBOOT_INFO_MMAP_BIT:    uint64 = 0x40              # flags bit 6

MMAP_TYPE_AVAILABLE:        uint64 = 1
MMAP_TYPE_RESERVED:         uint64 = 2
MMAP_TYPE_ACPI_RECLAIM:     uint64 = 3
MMAP_TYPE_NVS:              uint64 = 4
MMAP_TYPE_BAD:              uint64 = 5

# Floor for "usable" RAM. The kernel image, page tables, and very
# early data sit below 2 MiB; ignoring everything under this address
# keeps the allocator pool clear of them. Once we have a real
# kernel-image reservation system this floor goes away.
E820_MIN_BASE: uint64 = 0x00200000


def _type_name(t: uint64) -> Ptr[char]:
    # Short identifier for log lines. Keep these strings short so the
    # serial dump aligns nicely.
    if t == MMAP_TYPE_AVAILABLE:
        return "RAM "
    if t == MMAP_TYPE_RESERVED:
        return "RSVD"
    if t == MMAP_TYPE_ACPI_RECLAIM:
        return "ACPI"
    if t == MMAP_TYPE_NVS:
        return "NVS "
    if t == MMAP_TYPE_BAD:
        return "BAD "
    return "????"


def e820_init():
    # Validate that we were entered via multiboot. If not (the magic
    # in mb_magic doesn't match), fall back to the hardcoded memblock
    # range memblock_init() installed.
    magic: uint64 = get_mb_magic()
    if magic != MULTIBOOT_BOOTLOADER_MAGIC:
        printk1("e820: mb_magic = %x; not a multiboot kernel?\n", magic)
        return

    info: uint64 = get_mb_info()
    if info == 0:
        printk0("e820: mb_info is null, skipping\n")
        return

    flags: uint64 = cast[uint64](cast[Ptr[uint32]](info)[0])
    if (flags & MULTIBOOT_INFO_MMAP_BIT) == 0:
        printk1("e820: mb_info flags=%x missing mmap bit\n", flags)
        return

    # mmap_length / mmap_addr are uint32 fields at offsets 44 / 48.
    mmap_length: uint64 = cast[uint64](
        cast[Ptr[uint32]](info + 44)[0]
    )
    mmap_addr: uint64 = cast[uint64](
        cast[Ptr[uint32]](info + 48)[0]
    )

    printk2("e820: memory map @ %p, length %d bytes\n",
            mmap_addr, mmap_length)
    printk0("       idx  type   base               length\n")

    # Walk entries. Track the largest "available" region we see at
    # or above E820_MIN_BASE so we can hand it to memblock.
    best_base:    uint64 = 0
    best_length:  uint64 = 0

    pos: uint64 = mmap_addr
    end: uint64 = mmap_addr + mmap_length
    idx: uint64 = 0
    while pos < end:
        entry_size: uint64 = cast[uint64](cast[Ptr[uint32]](pos)[0])
        # entry_size is the BYTE count of fields AFTER itself, so to
        # advance to the next entry we add (entry_size + 4).
        base:       uint64 = cast[Ptr[uint64]](pos + 4)[0]
        length:     uint64 = cast[Ptr[uint64]](pos + 12)[0]
        type_code:  uint64 = cast[uint64](cast[Ptr[uint32]](pos + 20)[0])

        # Compact log row, intentionally not using a real format
        # string for the multi-field layout — printk2's two-arg max
        # would need two lines anyway. Two prints keep it readable.
        printk2("       %d    %s  ", idx, cast[uint64](_type_name(type_code)))
        printk2("%p  %p\n", base, length)

        # Available region: clamp its base up to E820_MIN_BASE if the
        # region straddles our floor (very common — the big "RAM"
        # entry on a PC starts at 1 MiB, but we want to keep the
        # kernel image area at 0x100000..~0x200000 reserved). If the
        # clamped region still has positive length, consider it.
        if type_code == MMAP_TYPE_AVAILABLE:
            adj_base:   uint64 = base
            adj_length: uint64 = length
            if adj_base < E820_MIN_BASE:
                # How many bytes did we trim off the front?
                shift: uint64 = E820_MIN_BASE - adj_base
                if shift >= adj_length:
                    adj_length = 0
                else:
                    adj_base   = E820_MIN_BASE
                    adj_length = adj_length - shift
            if adj_length > best_length:
                best_base   = adj_base
                best_length = adj_length

        pos = pos + entry_size + 4
        idx = idx + 1

    if best_length == 0:
        printk0("e820: no usable region above 2 MiB; keeping fallback\n")
        return

    printk2("e820: feeding memblock: base=%p length=%p\n",
            best_base, best_length)
    memblock_set_region(best_base, best_base + best_length)
