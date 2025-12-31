# RP2040 DMA Hardware Abstraction Layer
#
# Direct Memory Access controller driver for RP2040.
# The RP2040 has 12 independent DMA channels that can perform
# memory-to-memory, memory-to-peripheral, and peripheral-to-memory
# transfers without CPU intervention.
#
# Features:
#   - 12 independent DMA channels
#   - Chained transfers (trigger another channel on completion)
#   - Ring buffer support (address wrapping)
#   - Data request (DREQ) pacing from peripherals
#   - Interrupt on completion
#
# Memory Map:
#   DMA_BASE: 0x50000000

# ============================================================================
# Base Addresses
# ============================================================================

DMA_BASE: uint32 = 0x50000000

# ============================================================================
# DMA Channel Register Offsets
# ============================================================================
# Each channel has a set of registers with stride of 0x40 (64 bytes)

DMA_CH_STRIDE: uint32 = 0x40           # Bytes per channel

# Per-channel registers (offset from DMA_BASE + channel * DMA_CH_STRIDE)
DMA_CH_READ_ADDR: uint32 = 0x00        # Read address pointer
DMA_CH_WRITE_ADDR: uint32 = 0x04       # Write address pointer
DMA_CH_TRANS_COUNT: uint32 = 0x08      # Transfer count
DMA_CH_CTRL_TRIG: uint32 = 0x0C        # Control and trigger register
DMA_CH_AL1_CTRL: uint32 = 0x10         # Alias 1: CTRL, no trigger
DMA_CH_AL1_READ_ADDR: uint32 = 0x14    # Alias 1: Read address
DMA_CH_AL1_WRITE_ADDR: uint32 = 0x18   # Alias 1: Write address
DMA_CH_AL1_TRANS_COUNT_TRIG: uint32 = 0x1C  # Alias 1: Trans count, trigger
DMA_CH_AL2_CTRL: uint32 = 0x20         # Alias 2: CTRL
DMA_CH_AL2_TRANS_COUNT: uint32 = 0x24  # Alias 2: Trans count
DMA_CH_AL2_READ_ADDR: uint32 = 0x28    # Alias 2: Read address
DMA_CH_AL2_WRITE_ADDR_TRIG: uint32 = 0x2C   # Alias 2: Write address, trigger
DMA_CH_AL3_CTRL: uint32 = 0x30         # Alias 3: CTRL
DMA_CH_AL3_WRITE_ADDR: uint32 = 0x34   # Alias 3: Write address
DMA_CH_AL3_TRANS_COUNT: uint32 = 0x38  # Alias 3: Trans count
DMA_CH_AL3_READ_ADDR_TRIG: uint32 = 0x3C    # Alias 3: Read address, trigger

# ============================================================================
# DMA Global Registers (at DMA_BASE + 0x400)
# ============================================================================

DMA_INTR: uint32 = 0x400               # Interrupt status (raw)
DMA_INTE0: uint32 = 0x404              # Interrupt enable for IRQ0
DMA_INTF0: uint32 = 0x408              # Interrupt force for IRQ0
DMA_INTS0: uint32 = 0x40C              # Interrupt status for IRQ0
DMA_INTE1: uint32 = 0x414              # Interrupt enable for IRQ1
DMA_INTF1: uint32 = 0x418              # Interrupt force for IRQ1
DMA_INTS1: uint32 = 0x41C              # Interrupt status for IRQ1
DMA_TIMER0: uint32 = 0x420             # Pacing timer 0
DMA_TIMER1: uint32 = 0x424             # Pacing timer 1
DMA_TIMER2: uint32 = 0x428             # Pacing timer 2
DMA_TIMER3: uint32 = 0x42C             # Pacing timer 3
DMA_MULTI_CHAN_TRIGGER: uint32 = 0x430 # Trigger multiple channels
DMA_SNIFF_CTRL: uint32 = 0x434         # Sniffer control
DMA_SNIFF_DATA: uint32 = 0x438         # Sniffer data
DMA_FIFO_LEVELS: uint32 = 0x440        # Debug FIFO levels
DMA_CHAN_ABORT: uint32 = 0x444         # Abort channel transfers

# ============================================================================
# CTRL_TRIG Register Bits
# ============================================================================

DMA_CTRL_EN: uint32 = 0x00000001       # Channel enable
DMA_CTRL_HIGH_PRIORITY: uint32 = 0x00000002  # High priority
DMA_CTRL_DATA_SIZE_BYTE: uint32 = 0x00000000   # 1 byte transfers
DMA_CTRL_DATA_SIZE_HALFWORD: uint32 = 0x00000004  # 2 byte transfers
DMA_CTRL_DATA_SIZE_WORD: uint32 = 0x00000008     # 4 byte transfers
DMA_CTRL_INCR_READ: uint32 = 0x00000010   # Increment read address
DMA_CTRL_INCR_WRITE: uint32 = 0x00000020  # Increment write address
DMA_CTRL_RING_SIZE_SHIFT: uint32 = 6      # Ring size (0-15, 2^n bytes)
DMA_CTRL_RING_SEL: uint32 = 0x00000400    # Ring applies to write (1) or read (0)
DMA_CTRL_CHAIN_TO_SHIFT: uint32 = 11      # Chain to channel (4 bits)
DMA_CTRL_TREQ_SEL_SHIFT: uint32 = 15      # DREQ select (6 bits)
DMA_CTRL_IRQ_QUIET: uint32 = 0x00200000   # Don't generate interrupt
DMA_CTRL_BSWAP: uint32 = 0x00400000       # Byte swap
DMA_CTRL_SNIFF_EN: uint32 = 0x00800000    # Enable sniffer
DMA_CTRL_BUSY: uint32 = 0x01000000        # Channel is busy
DMA_CTRL_WRITE_ERROR: uint32 = 0x20000000 # Write error
DMA_CTRL_READ_ERROR: uint32 = 0x40000000  # Read error
DMA_CTRL_AHB_ERROR: uint32 = 0x80000000   # AHB error

# ============================================================================
# DREQ (Data Request) Constants
# ============================================================================
# These specify which peripheral paces the DMA transfer

DREQ_PIO0_TX0: uint32 = 0
DREQ_PIO0_TX1: uint32 = 1
DREQ_PIO0_TX2: uint32 = 2
DREQ_PIO0_TX3: uint32 = 3
DREQ_PIO0_RX0: uint32 = 4
DREQ_PIO0_RX1: uint32 = 5
DREQ_PIO0_RX2: uint32 = 6
DREQ_PIO0_RX3: uint32 = 7
DREQ_PIO1_TX0: uint32 = 8
DREQ_PIO1_TX1: uint32 = 9
DREQ_PIO1_TX2: uint32 = 10
DREQ_PIO1_TX3: uint32 = 11
DREQ_PIO1_RX0: uint32 = 12
DREQ_PIO1_RX1: uint32 = 13
DREQ_PIO1_RX2: uint32 = 14
DREQ_PIO1_RX3: uint32 = 15
DREQ_SPI0_TX: uint32 = 16
DREQ_SPI0_RX: uint32 = 17
DREQ_SPI1_TX: uint32 = 18
DREQ_SPI1_RX: uint32 = 19
DREQ_UART0_TX: uint32 = 20
DREQ_UART0_RX: uint32 = 21
DREQ_UART1_TX: uint32 = 22
DREQ_UART1_RX: uint32 = 23
DREQ_PWM_WRAP0: uint32 = 24
DREQ_PWM_WRAP1: uint32 = 25
DREQ_PWM_WRAP2: uint32 = 26
DREQ_PWM_WRAP3: uint32 = 27
DREQ_PWM_WRAP4: uint32 = 28
DREQ_PWM_WRAP5: uint32 = 29
DREQ_PWM_WRAP6: uint32 = 30
DREQ_PWM_WRAP7: uint32 = 31
DREQ_I2C0_TX: uint32 = 32
DREQ_I2C0_RX: uint32 = 33
DREQ_I2C1_TX: uint32 = 34
DREQ_I2C1_RX: uint32 = 35
DREQ_ADC: uint32 = 36
DREQ_XIP_STREAM: uint32 = 37
DREQ_XIP_SSITX: uint32 = 38
DREQ_XIP_SSIRX: uint32 = 39
DREQ_TIMER0: uint32 = 0x3B              # Pacing timer 0
DREQ_TIMER1: uint32 = 0x3C              # Pacing timer 1
DREQ_TIMER2: uint32 = 0x3D              # Pacing timer 2
DREQ_TIMER3: uint32 = 0x3E              # Pacing timer 3
DREQ_UNPACED: uint32 = 0x3F             # Unpaced (as fast as possible)

# ============================================================================
# DMA Configuration Constants
# ============================================================================

DMA_NUM_CHANNELS: uint32 = 12

# Data sizes
DMA_SIZE_8: uint32 = 0                  # 8-bit transfers
DMA_SIZE_16: uint32 = 1                 # 16-bit transfers
DMA_SIZE_32: uint32 = 2                 # 32-bit transfers

# ============================================================================
# Channel Allocation Tracking
# ============================================================================

# Bitmask of claimed channels (bit N = channel N claimed)
_dma_channels_claimed: uint32 = 0

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    """Read from memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    """Write to memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def _dma_channel_base(ch: uint32) -> uint32:
    """Get base address for DMA channel registers."""
    return DMA_BASE + (ch * DMA_CH_STRIDE)

# ============================================================================
# Channel Allocation Functions
# ============================================================================

def dma_channel_claim(ch: uint32) -> bool:
    """Claim a specific DMA channel for exclusive use.

    Args:
        ch: Channel number (0-11)

    Returns:
        True if claimed successfully, False if already claimed or invalid
    """
    global _dma_channels_claimed

    if ch >= DMA_NUM_CHANNELS:
        return False

    mask: uint32 = 1 << ch
    if (_dma_channels_claimed & mask) != 0:
        return False

    _dma_channels_claimed = _dma_channels_claimed | mask
    return True

def dma_channel_unclaim(ch: uint32):
    """Release a previously claimed DMA channel.

    Args:
        ch: Channel number (0-11)
    """
    global _dma_channels_claimed

    if ch >= DMA_NUM_CHANNELS:
        return

    mask: uint32 = 1 << ch
    _dma_channels_claimed = _dma_channels_claimed & ~mask

def dma_claim_unused_channel() -> int32:
    """Find and claim an unused DMA channel.

    Returns:
        Channel number (0-11) if found, -1 if none available
    """
    global _dma_channels_claimed

    ch: uint32 = 0
    while ch < DMA_NUM_CHANNELS:
        mask: uint32 = 1 << ch
        if (_dma_channels_claimed & mask) == 0:
            _dma_channels_claimed = _dma_channels_claimed | mask
            return cast[int32](ch)
        ch = ch + 1

    return -1

def dma_channel_is_claimed(ch: uint32) -> bool:
    """Check if a DMA channel is claimed.

    Args:
        ch: Channel number (0-11)

    Returns:
        True if claimed, False otherwise
    """
    if ch >= DMA_NUM_CHANNELS:
        return False

    return (_dma_channels_claimed & (1 << ch)) != 0

# ============================================================================
# Channel Configuration Functions
# ============================================================================

def dma_channel_configure(ch: uint32, ctrl: uint32, write_addr: uint32,
                          read_addr: uint32, count: uint32):
    """Configure a DMA channel for transfer.

    This sets up all transfer parameters but does not start the transfer.
    Write to CTRL_TRIG with EN bit to start.

    Args:
        ch: Channel number (0-11)
        ctrl: Control register value (without EN bit, use dma_channel_start)
        write_addr: Destination address
        read_addr: Source address
        count: Number of transfers (not bytes, depends on data size)
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)

    # Write addresses and count first (order matters for aliases)
    mmio_write(base + DMA_CH_READ_ADDR, read_addr)
    mmio_write(base + DMA_CH_WRITE_ADDR, write_addr)
    mmio_write(base + DMA_CH_TRANS_COUNT, count)

    # Write control without triggering
    mmio_write(base + DMA_CH_AL1_CTRL, ctrl & ~DMA_CTRL_EN)

def dma_channel_set_read_addr(ch: uint32, addr: uint32, trigger: bool):
    """Set the read address for a DMA channel.

    Args:
        ch: Channel number (0-11)
        addr: Source address
        trigger: If True, also starts the transfer
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)

    if trigger:
        mmio_write(base + DMA_CH_AL3_READ_ADDR_TRIG, addr)
    else:
        mmio_write(base + DMA_CH_READ_ADDR, addr)

def dma_channel_set_write_addr(ch: uint32, addr: uint32, trigger: bool):
    """Set the write address for a DMA channel.

    Args:
        ch: Channel number (0-11)
        addr: Destination address
        trigger: If True, also starts the transfer
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)

    if trigger:
        mmio_write(base + DMA_CH_AL2_WRITE_ADDR_TRIG, addr)
    else:
        mmio_write(base + DMA_CH_WRITE_ADDR, addr)

def dma_channel_set_trans_count(ch: uint32, count: uint32, trigger: bool):
    """Set the transfer count for a DMA channel.

    Args:
        ch: Channel number (0-11)
        count: Number of transfers
        trigger: If True, also starts the transfer
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)

    if trigger:
        mmio_write(base + DMA_CH_AL1_TRANS_COUNT_TRIG, count)
    else:
        mmio_write(base + DMA_CH_TRANS_COUNT, count)

def dma_channel_get_trans_count(ch: uint32) -> uint32:
    """Get remaining transfer count.

    Args:
        ch: Channel number (0-11)

    Returns:
        Remaining transfers
    """
    if ch >= DMA_NUM_CHANNELS:
        return 0

    base: uint32 = _dma_channel_base(ch)
    return mmio_read(base + DMA_CH_TRANS_COUNT)

# ============================================================================
# Control Register Builder
# ============================================================================

def dma_channel_build_ctrl(data_size: uint32, incr_read: bool, incr_write: bool,
                            dreq: uint32, chain_to: uint32, ring_size: uint32,
                            ring_sel_write: bool, high_priority: bool) -> uint32:
    """Build a control register value for DMA channel configuration.

    Args:
        data_size: DMA_SIZE_8, DMA_SIZE_16, or DMA_SIZE_32
        incr_read: Increment read address after each transfer
        incr_write: Increment write address after each transfer
        dreq: DREQ source (DREQ_* constant) for pacing
        chain_to: Channel to trigger on completion (same channel = no chain)
        ring_size: Ring buffer size as power of 2 (0 = disabled, 1-15 = 2^n bytes)
        ring_sel_write: True = ring applies to write addr, False = read addr
        high_priority: Give channel high scheduling priority

    Returns:
        Control register value (without EN bit)
    """
    ctrl: uint32 = 0

    # Data size
    ctrl = ctrl | ((data_size & 0x03) << 2)

    # Address increment
    if incr_read:
        ctrl = ctrl | DMA_CTRL_INCR_READ
    if incr_write:
        ctrl = ctrl | DMA_CTRL_INCR_WRITE

    # Ring buffer
    if ring_size > 0:
        ctrl = ctrl | ((ring_size & 0x0F) << DMA_CTRL_RING_SIZE_SHIFT)
        if ring_sel_write:
            ctrl = ctrl | DMA_CTRL_RING_SEL

    # Chain to
    ctrl = ctrl | ((chain_to & 0x0F) << DMA_CTRL_CHAIN_TO_SHIFT)

    # DREQ
    ctrl = ctrl | ((dreq & 0x3F) << DMA_CTRL_TREQ_SEL_SHIFT)

    # Priority
    if high_priority:
        ctrl = ctrl | DMA_CTRL_HIGH_PRIORITY

    return ctrl

# ============================================================================
# Channel Start/Stop Functions
# ============================================================================

def dma_channel_start(ch: uint32):
    """Start a DMA channel transfer.

    The channel must be configured before calling this.

    Args:
        ch: Channel number (0-11)
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)

    # Read current control and set EN bit
    ctrl: uint32 = mmio_read(base + DMA_CH_CTRL_TRIG)
    mmio_write(base + DMA_CH_CTRL_TRIG, ctrl | DMA_CTRL_EN)

def dma_channel_abort(ch: uint32):
    """Abort a DMA channel transfer.

    Args:
        ch: Channel number (0-11)
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    # Write to the abort register
    mmio_write(DMA_BASE + DMA_CHAN_ABORT, 1 << ch)

    # Wait for abort to complete
    while (mmio_read(DMA_BASE + DMA_CHAN_ABORT) & (1 << ch)) != 0:
        pass

def dma_channel_wait(ch: uint32):
    """Wait for a DMA channel transfer to complete.

    Args:
        ch: Channel number (0-11)
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)

    # Poll the BUSY bit
    while (mmio_read(base + DMA_CH_CTRL_TRIG) & DMA_CTRL_BUSY) != 0:
        pass

def dma_channel_is_busy(ch: uint32) -> bool:
    """Check if a DMA channel is currently transferring.

    Args:
        ch: Channel number (0-11)

    Returns:
        True if busy, False if idle
    """
    if ch >= DMA_NUM_CHANNELS:
        return False

    base: uint32 = _dma_channel_base(ch)
    return (mmio_read(base + DMA_CH_CTRL_TRIG) & DMA_CTRL_BUSY) != 0

# ============================================================================
# Interrupt Control
# ============================================================================

def dma_channel_set_irq_enabled(ch: uint32, irq: uint32, enabled: bool):
    """Enable or disable interrupt for a DMA channel.

    Args:
        ch: Channel number (0-11)
        irq: IRQ number (0 or 1 for DMA_IRQ_0 or DMA_IRQ_1)
        enabled: True to enable, False to disable
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    mask: uint32 = 1 << ch

    if irq == 0:
        inte_addr: uint32 = DMA_BASE + DMA_INTE0
    else:
        inte_addr: uint32 = DMA_BASE + DMA_INTE1

    val: uint32 = mmio_read(inte_addr)
    if enabled:
        mmio_write(inte_addr, val | mask)
    else:
        mmio_write(inte_addr, val & ~mask)

def dma_channel_acknowledge_irq(ch: uint32, irq: uint32):
    """Acknowledge (clear) interrupt for a DMA channel.

    Args:
        ch: Channel number (0-11)
        irq: IRQ number (0 or 1)
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    mask: uint32 = 1 << ch

    if irq == 0:
        ints_addr: uint32 = DMA_BASE + DMA_INTS0
    else:
        ints_addr: uint32 = DMA_BASE + DMA_INTS1

    # Write 1 to clear
    mmio_write(ints_addr, mask)

def dma_irq_get_channel_status(irq: uint32) -> uint32:
    """Get interrupt status for all channels.

    Args:
        irq: IRQ number (0 or 1)

    Returns:
        Bitmask of channels with pending interrupts
    """
    if irq == 0:
        return mmio_read(DMA_BASE + DMA_INTS0)
    else:
        return mmio_read(DMA_BASE + DMA_INTS1)

# ============================================================================
# Multi-Channel Operations
# ============================================================================

def dma_start_channels(mask: uint32):
    """Start multiple DMA channels simultaneously.

    Args:
        mask: Bitmask of channels to start (bit N = channel N)
    """
    mmio_write(DMA_BASE + DMA_MULTI_CHAN_TRIGGER, mask & 0xFFF)

# ============================================================================
# Ring Buffer Support
# ============================================================================

def dma_channel_configure_ring(ch: uint32, write_ring: bool, ring_size_bits: uint32):
    """Configure ring buffer (address wrapping) for a channel.

    The ring wraps the read or write address at a power-of-2 boundary.
    This is useful for circular buffers.

    Args:
        ch: Channel number (0-11)
        write_ring: True for write address ring, False for read address ring
        ring_size_bits: Ring size as power of 2 (0 = disabled, 1-15 = 2^n bytes)
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)
    ctrl: uint32 = mmio_read(base + DMA_CH_AL1_CTRL)

    # Clear ring bits
    ctrl = ctrl & ~(0x0F << DMA_CTRL_RING_SIZE_SHIFT)
    ctrl = ctrl & ~DMA_CTRL_RING_SEL

    # Set ring size
    ctrl = ctrl | ((ring_size_bits & 0x0F) << DMA_CTRL_RING_SIZE_SHIFT)

    # Set ring select
    if write_ring:
        ctrl = ctrl | DMA_CTRL_RING_SEL

    mmio_write(base + DMA_CH_AL1_CTRL, ctrl)

# ============================================================================
# Chain Transfer Support
# ============================================================================

def dma_channel_set_chain_to(ch: uint32, chain_ch: uint32):
    """Set the channel to trigger when this channel completes.

    Args:
        ch: Channel number (0-11)
        chain_ch: Channel to trigger (0-11, use same as ch to disable chaining)
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)
    ctrl: uint32 = mmio_read(base + DMA_CH_AL1_CTRL)

    # Clear and set chain_to bits
    ctrl = ctrl & ~(0x0F << DMA_CTRL_CHAIN_TO_SHIFT)
    ctrl = ctrl | ((chain_ch & 0x0F) << DMA_CTRL_CHAIN_TO_SHIFT)

    mmio_write(base + DMA_CH_AL1_CTRL, ctrl)

# ============================================================================
# Error Handling
# ============================================================================

def dma_channel_get_error(ch: uint32) -> uint32:
    """Get error flags for a DMA channel.

    Args:
        ch: Channel number (0-11)

    Returns:
        Error flags (DMA_CTRL_WRITE_ERROR | DMA_CTRL_READ_ERROR | DMA_CTRL_AHB_ERROR)
    """
    if ch >= DMA_NUM_CHANNELS:
        return 0

    base: uint32 = _dma_channel_base(ch)
    ctrl: uint32 = mmio_read(base + DMA_CH_CTRL_TRIG)

    return ctrl & (DMA_CTRL_WRITE_ERROR | DMA_CTRL_READ_ERROR | DMA_CTRL_AHB_ERROR)

def dma_channel_clear_error(ch: uint32):
    """Clear error flags for a DMA channel.

    Args:
        ch: Channel number (0-11)
    """
    if ch >= DMA_NUM_CHANNELS:
        return

    base: uint32 = _dma_channel_base(ch)

    # Write 1 to clear error bits
    mmio_write(base + DMA_CH_CTRL_TRIG,
               DMA_CTRL_WRITE_ERROR | DMA_CTRL_READ_ERROR | DMA_CTRL_AHB_ERROR)

# ============================================================================
# Sniffer Support (CRC calculation during transfer)
# ============================================================================

def dma_sniffer_enable(ch: uint32, mode: uint32):
    """Enable DMA sniffer on a channel.

    The sniffer can calculate CRC or checksum of transferred data.

    Args:
        ch: Channel to sniff (0-11)
        mode: Sniffer mode (0=CRC32, 1=CRC32 bit-reversed, etc.)
    """
    # Enable sniff on the channel
    if ch < DMA_NUM_CHANNELS:
        base: uint32 = _dma_channel_base(ch)
        ctrl: uint32 = mmio_read(base + DMA_CH_AL1_CTRL)
        mmio_write(base + DMA_CH_AL1_CTRL, ctrl | DMA_CTRL_SNIFF_EN)

    # Configure sniffer
    sniff_ctrl: uint32 = (ch & 0x0F) | ((mode & 0x0F) << 5) | 0x01  # Enable
    mmio_write(DMA_BASE + DMA_SNIFF_CTRL, sniff_ctrl)

def dma_sniffer_disable():
    """Disable DMA sniffer."""
    mmio_write(DMA_BASE + DMA_SNIFF_CTRL, 0)

def dma_sniffer_get_data() -> uint32:
    """Get sniffer result (CRC/checksum).

    Returns:
        Sniffer accumulator value
    """
    return mmio_read(DMA_BASE + DMA_SNIFF_DATA)

def dma_sniffer_set_data(data: uint32):
    """Set sniffer initial value.

    Args:
        data: Initial value for CRC/checksum calculation
    """
    mmio_write(DMA_BASE + DMA_SNIFF_DATA, data)

# ============================================================================
# Convenience Functions
# ============================================================================

def dma_memcpy(ch: uint32, dst: uint32, src: uint32, size: uint32):
    """Perform memory-to-memory copy using DMA.

    Args:
        ch: Channel number (0-11)
        dst: Destination address
        src: Source address
        size: Number of bytes to copy
    """
    if ch >= DMA_NUM_CHANNELS or size == 0:
        return

    # Use word transfers if aligned, otherwise byte transfers
    if ((dst & 3) == 0) and ((src & 3) == 0) and ((size & 3) == 0):
        data_size: uint32 = DMA_SIZE_32
        count: uint32 = size >> 2
    elif ((dst & 1) == 0) and ((src & 1) == 0) and ((size & 1) == 0):
        data_size: uint32 = DMA_SIZE_16
        count: uint32 = size >> 1
    else:
        data_size: uint32 = DMA_SIZE_8
        count: uint32 = size

    ctrl: uint32 = dma_channel_build_ctrl(
        data_size, True, True, DREQ_UNPACED, ch, 0, False, False)

    dma_channel_configure(ch, ctrl, dst, src, count)
    dma_channel_start(ch)

def dma_memset(ch: uint32, dst: uint32, value: uint32, size: uint32):
    """Fill memory with a value using DMA.

    Note: The value must be stored in a static location that persists
    during the transfer.

    Args:
        ch: Channel number (0-11)
        dst: Destination address
        value: Address of value to fill (not the value itself)
        size: Number of bytes to fill
    """
    if ch >= DMA_NUM_CHANNELS or size == 0:
        return

    # Use word transfers if aligned
    if ((dst & 3) == 0) and ((size & 3) == 0):
        data_size: uint32 = DMA_SIZE_32
        count: uint32 = size >> 2
    else:
        data_size: uint32 = DMA_SIZE_8
        count: uint32 = size

    # Don't increment read address (read same value repeatedly)
    ctrl: uint32 = dma_channel_build_ctrl(
        data_size, False, True, DREQ_UNPACED, ch, 0, False, False)

    dma_channel_configure(ch, ctrl, dst, value, count)
    dma_channel_start(ch)
