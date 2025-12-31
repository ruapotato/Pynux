# STM32F4 DMA Hardware Abstraction Layer
#
# Direct Memory Access controller driver for STM32F405/F407.
# The STM32F4 has two DMA controllers:
#   - DMA1: 8 streams, connected to APB1 peripherals
#   - DMA2: 8 streams, connected to APB2 peripherals and memory-to-memory
#
# Each stream can be configured for one of 8 channels (peripheral requests).
# Only DMA2 supports memory-to-memory transfers.
#
# Features:
#   - 8 streams per DMA controller
#   - 8 channel selections per stream
#   - Circular mode, double buffer mode
#   - FIFO with configurable threshold
#   - Burst transfers
#   - Four priority levels
#
# Memory Map:
#   DMA1: 0x40026000
#   DMA2: 0x40026400
#   RCC:  0x40023800

# ============================================================================
# Base Addresses
# ============================================================================

DMA1_BASE: uint32 = 0x40026000
DMA2_BASE: uint32 = 0x40026400
RCC_BASE: uint32 = 0x40023800

# ============================================================================
# DMA Register Offsets
# ============================================================================

# Low and high interrupt status registers
DMA_LISR: uint32 = 0x00                # Low interrupt status (streams 0-3)
DMA_HISR: uint32 = 0x04                # High interrupt status (streams 4-7)
DMA_LIFCR: uint32 = 0x08               # Low interrupt flag clear (streams 0-3)
DMA_HIFCR: uint32 = 0x0C               # High interrupt flag clear (streams 4-7)

# Stream registers stride
DMA_STREAM_STRIDE: uint32 = 0x18       # 24 bytes per stream

# Stream register offsets (from stream base)
DMA_SxCR: uint32 = 0x00                # Stream configuration register
DMA_SxNDTR: uint32 = 0x04              # Number of data items to transfer
DMA_SxPAR: uint32 = 0x08               # Peripheral address register
DMA_SxM0AR: uint32 = 0x0C              # Memory 0 address register
DMA_SxM1AR: uint32 = 0x10              # Memory 1 address register (double buffer)
DMA_SxFCR: uint32 = 0x14               # FIFO control register

# First stream starts at offset 0x10
DMA_STREAM_BASE_OFFSET: uint32 = 0x10

# ============================================================================
# SxCR (Stream Configuration Register) Bits
# ============================================================================

DMA_SxCR_EN: uint32 = 0x00000001       # Stream enable
DMA_SxCR_DMEIE: uint32 = 0x00000002    # Direct mode error interrupt enable
DMA_SxCR_TEIE: uint32 = 0x00000004     # Transfer error interrupt enable
DMA_SxCR_HTIE: uint32 = 0x00000008     # Half transfer interrupt enable
DMA_SxCR_TCIE: uint32 = 0x00000010     # Transfer complete interrupt enable
DMA_SxCR_PFCTRL: uint32 = 0x00000020   # Peripheral flow controller

# Direction
DMA_SxCR_DIR_P2M: uint32 = 0x00000000  # Peripheral to memory
DMA_SxCR_DIR_M2P: uint32 = 0x00000040  # Memory to peripheral
DMA_SxCR_DIR_M2M: uint32 = 0x00000080  # Memory to memory (DMA2 only)
DMA_SxCR_DIR_MASK: uint32 = 0x000000C0

DMA_SxCR_CIRC: uint32 = 0x00000100     # Circular mode
DMA_SxCR_PINC: uint32 = 0x00000200     # Peripheral increment mode
DMA_SxCR_MINC: uint32 = 0x00000400     # Memory increment mode

# Peripheral data size
DMA_SxCR_PSIZE_8: uint32 = 0x00000000  # 8-bit
DMA_SxCR_PSIZE_16: uint32 = 0x00000800 # 16-bit
DMA_SxCR_PSIZE_32: uint32 = 0x00001000 # 32-bit
DMA_SxCR_PSIZE_MASK: uint32 = 0x00001800

# Memory data size
DMA_SxCR_MSIZE_8: uint32 = 0x00000000  # 8-bit
DMA_SxCR_MSIZE_16: uint32 = 0x00002000 # 16-bit
DMA_SxCR_MSIZE_32: uint32 = 0x00004000 # 32-bit
DMA_SxCR_MSIZE_MASK: uint32 = 0x00006000

# Peripheral increment offset size
DMA_SxCR_PINCOS: uint32 = 0x00008000   # Peripheral increment offset size

# Priority level
DMA_SxCR_PL_LOW: uint32 = 0x00000000
DMA_SxCR_PL_MEDIUM: uint32 = 0x00010000
DMA_SxCR_PL_HIGH: uint32 = 0x00020000
DMA_SxCR_PL_VERY_HIGH: uint32 = 0x00030000
DMA_SxCR_PL_MASK: uint32 = 0x00030000

DMA_SxCR_DBM: uint32 = 0x00040000      # Double buffer mode
DMA_SxCR_CT: uint32 = 0x00080000       # Current target (memory 0 or 1)

# Peripheral burst
DMA_SxCR_PBURST_SINGLE: uint32 = 0x00000000
DMA_SxCR_PBURST_INCR4: uint32 = 0x00200000
DMA_SxCR_PBURST_INCR8: uint32 = 0x00400000
DMA_SxCR_PBURST_INCR16: uint32 = 0x00600000
DMA_SxCR_PBURST_MASK: uint32 = 0x00600000

# Memory burst
DMA_SxCR_MBURST_SINGLE: uint32 = 0x00000000
DMA_SxCR_MBURST_INCR4: uint32 = 0x00800000
DMA_SxCR_MBURST_INCR8: uint32 = 0x01000000
DMA_SxCR_MBURST_INCR16: uint32 = 0x01800000
DMA_SxCR_MBURST_MASK: uint32 = 0x01800000

# Channel selection (bits 25-27)
DMA_SxCR_CHSEL_SHIFT: uint32 = 25
DMA_SxCR_CHSEL_MASK: uint32 = 0x0E000000

# ============================================================================
# SxFCR (FIFO Control Register) Bits
# ============================================================================

DMA_SxFCR_FTH_1_4: uint32 = 0x00       # FIFO threshold 1/4 full
DMA_SxFCR_FTH_1_2: uint32 = 0x01       # FIFO threshold 1/2 full
DMA_SxFCR_FTH_3_4: uint32 = 0x02       # FIFO threshold 3/4 full
DMA_SxFCR_FTH_FULL: uint32 = 0x03      # FIFO threshold full
DMA_SxFCR_FTH_MASK: uint32 = 0x03

DMA_SxFCR_DMDIS: uint32 = 0x04         # Direct mode disable (enable FIFO)
DMA_SxFCR_FS_MASK: uint32 = 0x38       # FIFO status (read-only)
DMA_SxFCR_FEIE: uint32 = 0x80          # FIFO error interrupt enable

# ============================================================================
# Interrupt Flag Positions in LISR/HISR
# ============================================================================
# Flags repeat every stream with different bit positions

DMA_FLAG_FEIF: uint32 = 0x01           # FIFO error
DMA_FLAG_DMEIF: uint32 = 0x04          # Direct mode error
DMA_FLAG_TEIF: uint32 = 0x08           # Transfer error
DMA_FLAG_HTIF: uint32 = 0x10           # Half transfer
DMA_FLAG_TCIF: uint32 = 0x20           # Transfer complete

# Bit positions for each stream in LISR (streams 0-3) or HISR (streams 4-7)
# Stream 0/4: bits 0-5
# Stream 1/5: bits 6-11
# Stream 2/6: bits 16-21
# Stream 3/7: bits 22-27

# ============================================================================
# RCC Register for DMA Clock Enable
# ============================================================================

RCC_AHB1ENR: uint32 = 0x30
RCC_DMA1EN: uint32 = 0x00200000        # DMA1 clock enable (bit 21)
RCC_DMA2EN: uint32 = 0x00400000        # DMA2 clock enable (bit 22)

# ============================================================================
# DMA Controller Constants
# ============================================================================

DMA1: uint32 = 1
DMA2: uint32 = 2

DMA_NUM_STREAMS: uint32 = 8
DMA_NUM_CHANNELS: uint32 = 8

# Priority levels
DMA_PRIORITY_LOW: uint32 = 0
DMA_PRIORITY_MEDIUM: uint32 = 1
DMA_PRIORITY_HIGH: uint32 = 2
DMA_PRIORITY_VERY_HIGH: uint32 = 3

# Direction
DMA_DIR_PERIPH_TO_MEM: uint32 = 0
DMA_DIR_MEM_TO_PERIPH: uint32 = 1
DMA_DIR_MEM_TO_MEM: uint32 = 2

# Data sizes
DMA_SIZE_8: uint32 = 0
DMA_SIZE_16: uint32 = 1
DMA_SIZE_32: uint32 = 2

# Burst sizes
DMA_BURST_SINGLE: uint32 = 0
DMA_BURST_INCR4: uint32 = 1
DMA_BURST_INCR8: uint32 = 2
DMA_BURST_INCR16: uint32 = 3

# FIFO thresholds
DMA_FIFO_1_4: uint32 = 0
DMA_FIFO_1_2: uint32 = 1
DMA_FIFO_3_4: uint32 = 2
DMA_FIFO_FULL: uint32 = 3

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

def _dma_base(dma: uint32) -> uint32:
    """Get base address for DMA controller."""
    if dma == DMA1:
        return DMA1_BASE
    return DMA2_BASE

def _dma_stream_base(dma: uint32, stream: uint32) -> uint32:
    """Get base address for DMA stream registers."""
    return _dma_base(dma) + DMA_STREAM_BASE_OFFSET + (stream * DMA_STREAM_STRIDE)

def _dma_flag_shift(stream: uint32) -> uint32:
    """Get bit shift for interrupt flags in LISR/HISR."""
    # Streams 0,4: shift 0; 1,5: shift 6; 2,6: shift 16; 3,7: shift 22
    stream_in_reg: uint32 = stream & 0x03
    if stream_in_reg == 0:
        return 0
    elif stream_in_reg == 1:
        return 6
    elif stream_in_reg == 2:
        return 16
    return 22

# ============================================================================
# Clock Enable
# ============================================================================

def dma_enable_clock(dma: uint32):
    """Enable clock for DMA controller.

    Must be called before using DMA.

    Args:
        dma: DMA1 or DMA2
    """
    rcc_ahb1enr: uint32 = RCC_BASE + RCC_AHB1ENR
    val: uint32 = mmio_read(rcc_ahb1enr)

    if dma == DMA1:
        mmio_write(rcc_ahb1enr, val | RCC_DMA1EN)
    else:
        mmio_write(rcc_ahb1enr, val | RCC_DMA2EN)

    # Small delay for clock stabilization
    dummy: uint32 = mmio_read(rcc_ahb1enr)

# ============================================================================
# DMA Initialization
# ============================================================================

def dma_init(dma: uint32, stream: uint32, channel: uint32, direction: uint32,
             priority: uint32):
    """Initialize a DMA stream.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        channel: Channel number (0-7) - determines peripheral
        direction: DMA_DIR_PERIPH_TO_MEM, DMA_DIR_MEM_TO_PERIPH, or DMA_DIR_MEM_TO_MEM
        priority: DMA_PRIORITY_LOW/MEDIUM/HIGH/VERY_HIGH
    """
    if stream >= DMA_NUM_STREAMS:
        return

    # Enable clock
    dma_enable_clock(dma)

    base: uint32 = _dma_stream_base(dma, stream)

    # Disable stream first
    mmio_write(base + DMA_SxCR, 0)

    # Wait for EN to clear
    while (mmio_read(base + DMA_SxCR) & DMA_SxCR_EN) != 0:
        pass

    # Clear all interrupt flags
    dma_clear_flags(dma, stream)

    # Build configuration
    cr: uint32 = 0

    # Channel selection
    cr = cr | ((channel & 0x07) << DMA_SxCR_CHSEL_SHIFT)

    # Direction
    if direction == DMA_DIR_MEM_TO_PERIPH:
        cr = cr | DMA_SxCR_DIR_M2P
    elif direction == DMA_DIR_MEM_TO_MEM:
        cr = cr | DMA_SxCR_DIR_M2M

    # Priority
    cr = cr | ((priority & 0x03) << 16)

    mmio_write(base + DMA_SxCR, cr)

    # Default FIFO configuration (direct mode)
    mmio_write(base + DMA_SxFCR, 0)

def dma_configure(dma: uint32, stream: uint32, periph_addr: uint32,
                  mem_addr: uint32, count: uint32):
    """Configure DMA stream addresses and transfer count.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        periph_addr: Peripheral address
        mem_addr: Memory address
        count: Number of data items to transfer
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)

    mmio_write(base + DMA_SxPAR, periph_addr)
    mmio_write(base + DMA_SxM0AR, mem_addr)
    mmio_write(base + DMA_SxNDTR, count & 0xFFFF)

def dma_set_data_size(dma: uint32, stream: uint32, periph_size: uint32,
                      mem_size: uint32):
    """Set peripheral and memory data sizes.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        periph_size: DMA_SIZE_8, DMA_SIZE_16, or DMA_SIZE_32
        mem_size: DMA_SIZE_8, DMA_SIZE_16, or DMA_SIZE_32
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)
    cr: uint32 = mmio_read(base + DMA_SxCR)

    # Clear size bits
    cr = cr & ~(DMA_SxCR_PSIZE_MASK | DMA_SxCR_MSIZE_MASK)

    # Set peripheral size
    cr = cr | ((periph_size & 0x03) << 11)

    # Set memory size
    cr = cr | ((mem_size & 0x03) << 13)

    mmio_write(base + DMA_SxCR, cr)

def dma_set_increment(dma: uint32, stream: uint32, periph_inc: bool,
                      mem_inc: bool):
    """Enable/disable address increment for peripheral and memory.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        periph_inc: Increment peripheral address
        mem_inc: Increment memory address
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)
    cr: uint32 = mmio_read(base + DMA_SxCR)

    cr = cr & ~(DMA_SxCR_PINC | DMA_SxCR_MINC)

    if periph_inc:
        cr = cr | DMA_SxCR_PINC
    if mem_inc:
        cr = cr | DMA_SxCR_MINC

    mmio_write(base + DMA_SxCR, cr)

def dma_set_circular(dma: uint32, stream: uint32, enable: bool):
    """Enable/disable circular mode.

    In circular mode, the DMA reloads addresses and count after completion.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        enable: True to enable circular mode
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)
    cr: uint32 = mmio_read(base + DMA_SxCR)

    if enable:
        cr = cr | DMA_SxCR_CIRC
    else:
        cr = cr & ~DMA_SxCR_CIRC

    mmio_write(base + DMA_SxCR, cr)

# ============================================================================
# Double Buffer Mode
# ============================================================================

def dma_set_double_buffer(dma: uint32, stream: uint32, enable: bool,
                          mem1_addr: uint32):
    """Enable double buffer mode.

    In double buffer mode, the DMA alternates between M0AR and M1AR
    on each transfer completion. Requires circular mode.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        enable: True to enable double buffer mode
        mem1_addr: Second memory buffer address
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)

    # Set M1AR
    mmio_write(base + DMA_SxM1AR, mem1_addr)

    cr: uint32 = mmio_read(base + DMA_SxCR)

    if enable:
        cr = cr | DMA_SxCR_DBM | DMA_SxCR_CIRC  # DBM requires circular mode
    else:
        cr = cr & ~DMA_SxCR_DBM

    mmio_write(base + DMA_SxCR, cr)

def dma_get_current_target(dma: uint32, stream: uint32) -> uint32:
    """Get current memory target in double buffer mode.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)

    Returns:
        0 for M0AR, 1 for M1AR
    """
    if stream >= DMA_NUM_STREAMS:
        return 0

    base: uint32 = _dma_stream_base(dma, stream)
    cr: uint32 = mmio_read(base + DMA_SxCR)

    if (cr & DMA_SxCR_CT) != 0:
        return 1
    return 0

def dma_set_memory_address(dma: uint32, stream: uint32, target: uint32,
                           addr: uint32):
    """Set memory address for a target buffer.

    Can be used while DMA is running in double buffer mode to update
    the inactive buffer.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        target: 0 for M0AR, 1 for M1AR
        addr: New memory address
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)

    if target == 0:
        mmio_write(base + DMA_SxM0AR, addr)
    else:
        mmio_write(base + DMA_SxM1AR, addr)

# ============================================================================
# FIFO Configuration
# ============================================================================

def dma_set_fifo(dma: uint32, stream: uint32, enable: bool, threshold: uint32):
    """Configure FIFO mode.

    FIFO mode allows burst transfers and decouples peripheral/memory sizes.
    Direct mode (FIFO disabled) is simpler but limited.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        enable: True to enable FIFO, False for direct mode
        threshold: DMA_FIFO_1_4, DMA_FIFO_1_2, DMA_FIFO_3_4, or DMA_FIFO_FULL
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)

    if enable:
        fcr: uint32 = DMA_SxFCR_DMDIS | (threshold & DMA_SxFCR_FTH_MASK)
    else:
        fcr: uint32 = 0  # Direct mode

    mmio_write(base + DMA_SxFCR, fcr)

def dma_get_fifo_status(dma: uint32, stream: uint32) -> uint32:
    """Get FIFO fill level.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)

    Returns:
        FIFO status (0-4): 0=empty to 1/4, 1=1/4 to 1/2, etc.
    """
    if stream >= DMA_NUM_STREAMS:
        return 0

    base: uint32 = _dma_stream_base(dma, stream)
    fcr: uint32 = mmio_read(base + DMA_SxFCR)

    return (fcr & DMA_SxFCR_FS_MASK) >> 3

# ============================================================================
# Burst Configuration
# ============================================================================

def dma_set_burst(dma: uint32, stream: uint32, periph_burst: uint32,
                  mem_burst: uint32):
    """Configure burst transfer sizes.

    Burst transfers are more efficient but require FIFO mode.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        periph_burst: DMA_BURST_SINGLE/INCR4/INCR8/INCR16
        mem_burst: DMA_BURST_SINGLE/INCR4/INCR8/INCR16
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)
    cr: uint32 = mmio_read(base + DMA_SxCR)

    # Clear burst bits
    cr = cr & ~(DMA_SxCR_PBURST_MASK | DMA_SxCR_MBURST_MASK)

    # Set peripheral burst
    cr = cr | ((periph_burst & 0x03) << 21)

    # Set memory burst
    cr = cr | ((mem_burst & 0x03) << 23)

    mmio_write(base + DMA_SxCR, cr)

# ============================================================================
# Stream Control
# ============================================================================

def dma_start(dma: uint32, stream: uint32):
    """Start a DMA stream transfer.

    The stream must be configured before calling this.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)
    cr: uint32 = mmio_read(base + DMA_SxCR)
    mmio_write(base + DMA_SxCR, cr | DMA_SxCR_EN)

def dma_stop(dma: uint32, stream: uint32):
    """Stop a DMA stream transfer.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)
    cr: uint32 = mmio_read(base + DMA_SxCR)
    mmio_write(base + DMA_SxCR, cr & ~DMA_SxCR_EN)

    # Wait for EN to clear (transfer complete)
    while (mmio_read(base + DMA_SxCR) & DMA_SxCR_EN) != 0:
        pass

def dma_wait(dma: uint32, stream: uint32):
    """Wait for a DMA stream transfer to complete.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
    """
    if stream >= DMA_NUM_STREAMS:
        return

    # Wait for transfer complete flag
    while not dma_get_flag(dma, stream, DMA_FLAG_TCIF):
        pass

def dma_is_enabled(dma: uint32, stream: uint32) -> bool:
    """Check if a DMA stream is enabled (running).

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)

    Returns:
        True if stream is enabled
    """
    if stream >= DMA_NUM_STREAMS:
        return False

    base: uint32 = _dma_stream_base(dma, stream)
    return (mmio_read(base + DMA_SxCR) & DMA_SxCR_EN) != 0

def dma_get_remaining(dma: uint32, stream: uint32) -> uint32:
    """Get remaining transfer count.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)

    Returns:
        Number of data items remaining
    """
    if stream >= DMA_NUM_STREAMS:
        return 0

    base: uint32 = _dma_stream_base(dma, stream)
    return mmio_read(base + DMA_SxNDTR) & 0xFFFF

# ============================================================================
# Interrupt Flag Handling
# ============================================================================

def dma_get_flag(dma: uint32, stream: uint32, flag: uint32) -> bool:
    """Get a specific interrupt flag for a stream.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        flag: DMA_FLAG_FEIF/DMEIF/TEIF/HTIF/TCIF

    Returns:
        True if flag is set
    """
    if stream >= DMA_NUM_STREAMS:
        return False

    base: uint32 = _dma_base(dma)
    shift: uint32 = _dma_flag_shift(stream)

    # Use LISR for streams 0-3, HISR for 4-7
    if stream < 4:
        isr: uint32 = mmio_read(base + DMA_LISR)
    else:
        isr: uint32 = mmio_read(base + DMA_HISR)

    return ((isr >> shift) & flag) != 0

def dma_clear_flag(dma: uint32, stream: uint32, flag: uint32):
    """Clear a specific interrupt flag for a stream.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        flag: DMA_FLAG_FEIF/DMEIF/TEIF/HTIF/TCIF
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_base(dma)
    shift: uint32 = _dma_flag_shift(stream)
    clear_val: uint32 = flag << shift

    # Use LIFCR for streams 0-3, HIFCR for 4-7
    if stream < 4:
        mmio_write(base + DMA_LIFCR, clear_val)
    else:
        mmio_write(base + DMA_HIFCR, clear_val)

def dma_clear_flags(dma: uint32, stream: uint32):
    """Clear all interrupt flags for a stream.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
    """
    all_flags: uint32 = DMA_FLAG_FEIF | DMA_FLAG_DMEIF | DMA_FLAG_TEIF | \
                        DMA_FLAG_HTIF | DMA_FLAG_TCIF
    dma_clear_flag(dma, stream, all_flags)

# ============================================================================
# Interrupt Enable
# ============================================================================

def dma_set_irq_enabled(dma: uint32, stream: uint32, tc: bool, ht: bool,
                        te: bool, dme: bool, fe: bool):
    """Enable/disable interrupts for a stream.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        tc: Transfer complete interrupt enable
        ht: Half transfer interrupt enable
        te: Transfer error interrupt enable
        dme: Direct mode error interrupt enable
        fe: FIFO error interrupt enable
    """
    if stream >= DMA_NUM_STREAMS:
        return

    base: uint32 = _dma_stream_base(dma, stream)

    # Configure SxCR interrupt bits
    cr: uint32 = mmio_read(base + DMA_SxCR)
    cr = cr & ~(DMA_SxCR_TCIE | DMA_SxCR_HTIE | DMA_SxCR_TEIE | DMA_SxCR_DMEIE)

    if tc:
        cr = cr | DMA_SxCR_TCIE
    if ht:
        cr = cr | DMA_SxCR_HTIE
    if te:
        cr = cr | DMA_SxCR_TEIE
    if dme:
        cr = cr | DMA_SxCR_DMEIE

    mmio_write(base + DMA_SxCR, cr)

    # Configure SxFCR FIFO error interrupt
    fcr: uint32 = mmio_read(base + DMA_SxFCR)
    if fe:
        fcr = fcr | DMA_SxFCR_FEIE
    else:
        fcr = fcr & ~DMA_SxFCR_FEIE

    mmio_write(base + DMA_SxFCR, fcr)

# ============================================================================
# Convenience Functions
# ============================================================================

def dma_periph_to_mem(dma: uint32, stream: uint32, channel: uint32,
                      periph_addr: uint32, mem_addr: uint32, count: uint32,
                      periph_size: uint32, mem_size: uint32, circular: bool):
    """Configure and start peripheral-to-memory DMA transfer.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        channel: Channel number (0-7)
        periph_addr: Peripheral data register address
        mem_addr: Memory buffer address
        count: Number of data items to transfer
        periph_size: DMA_SIZE_8, DMA_SIZE_16, or DMA_SIZE_32
        mem_size: DMA_SIZE_8, DMA_SIZE_16, or DMA_SIZE_32
        circular: Enable circular mode
    """
    dma_init(dma, stream, channel, DMA_DIR_PERIPH_TO_MEM, DMA_PRIORITY_HIGH)
    dma_configure(dma, stream, periph_addr, mem_addr, count)
    dma_set_data_size(dma, stream, periph_size, mem_size)
    dma_set_increment(dma, stream, False, True)  # Memory increment only
    dma_set_circular(dma, stream, circular)
    dma_start(dma, stream)

def dma_mem_to_periph(dma: uint32, stream: uint32, channel: uint32,
                      periph_addr: uint32, mem_addr: uint32, count: uint32,
                      periph_size: uint32, mem_size: uint32, circular: bool):
    """Configure and start memory-to-peripheral DMA transfer.

    Args:
        dma: DMA1 or DMA2
        stream: Stream number (0-7)
        channel: Channel number (0-7)
        periph_addr: Peripheral data register address
        mem_addr: Memory buffer address
        count: Number of data items to transfer
        periph_size: DMA_SIZE_8, DMA_SIZE_16, or DMA_SIZE_32
        mem_size: DMA_SIZE_8, DMA_SIZE_16, or DMA_SIZE_32
        circular: Enable circular mode
    """
    dma_init(dma, stream, channel, DMA_DIR_MEM_TO_PERIPH, DMA_PRIORITY_HIGH)
    dma_configure(dma, stream, periph_addr, mem_addr, count)
    dma_set_data_size(dma, stream, periph_size, mem_size)
    dma_set_increment(dma, stream, False, True)  # Memory increment only
    dma_set_circular(dma, stream, circular)
    dma_start(dma, stream)

def dma_mem_to_mem(stream: uint32, dst_addr: uint32, src_addr: uint32,
                   count: uint32, data_size: uint32):
    """Configure and start memory-to-memory DMA transfer.

    Note: Memory-to-memory is only available on DMA2.

    Args:
        stream: Stream number (0-7)
        dst_addr: Destination memory address
        src_addr: Source memory address
        count: Number of data items to transfer
        data_size: DMA_SIZE_8, DMA_SIZE_16, or DMA_SIZE_32
    """
    # Memory-to-memory only on DMA2
    dma_init(DMA2, stream, 0, DMA_DIR_MEM_TO_MEM, DMA_PRIORITY_HIGH)
    dma_configure(DMA2, stream, src_addr, dst_addr, count)
    dma_set_data_size(DMA2, stream, data_size, data_size)
    dma_set_increment(DMA2, stream, True, True)  # Both increment
    dma_start(DMA2, stream)

# ============================================================================
# DMA Channel to Stream Mapping (common peripherals)
# ============================================================================
# This documents which DMA/stream/channel combinations are valid for
# common peripherals on STM32F4.
#
# DMA1:
#   Stream 0: Ch2=SPI3_RX, Ch3=I2C1_RX, Ch7=I2C1_RX
#   Stream 1: Ch1=TIM2_UP/CH3, Ch3=I2C3_RX, Ch6=TIM5_CH4
#   Stream 2: Ch0=SPI3_RX, Ch3=I2C3_RX, Ch5=TIM3_CH4
#   Stream 3: Ch0=SPI2_RX, Ch3=I2C2_RX, Ch7=I2C2_RX
#   Stream 4: Ch0=SPI2_TX, Ch2=SPI3_TX, Ch4=USART3_TX
#   Stream 5: Ch0=SPI3_TX, Ch3=I2C1_TX, Ch4=USART2_RX
#   Stream 6: Ch1=TIM2_CH1, Ch4=USART2_TX, Ch5=TIM5_UP
#   Stream 7: Ch0=SPI3_TX, Ch3=I2C1_TX, Ch4=UART5_TX
#
# DMA2:
#   Stream 0: Ch0=ADC1, Ch3=SPI1_RX, Ch6=TIM1_TRIG
#   Stream 1: Ch3=TIM8_UP, Ch6=TIM1_CH1
#   Stream 2: Ch0=ADC2, Ch3=SPI1_RX, Ch4=USART1_RX
#   Stream 3: Ch0=ADC2, Ch3=SPI1_TX, Ch4=SDIO
#   Stream 4: Ch0=ADC1, Ch5=SPI4_TX, Ch6=TIM1_CH4
#   Stream 5: Ch1=SPI6_TX, Ch3=SPI1_TX, Ch4=USART1_RX
#   Stream 6: Ch0=TIM1_CH1, Ch4=SDIO, Ch5=USART6_TX
#   Stream 7: Ch4=USART1_TX, Ch5=USART6_TX
