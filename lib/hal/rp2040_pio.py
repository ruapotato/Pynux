# RP2040 PIO (Programmable I/O) Hardware Abstraction Layer
#
# Low-level PIO driver for Raspberry Pi Pico (RP2040).
# RP2040 has 2 PIO blocks, each with 4 state machines and 32 instruction slots.
#
# Memory Map:
#   PIO0_BASE: 0x50200000 - PIO block 0
#   PIO1_BASE: 0x50300000 - PIO block 1
#
# Each PIO block provides:
#   - 4 state machines (SM0-SM3)
#   - 32 instruction memory slots
#   - Independent clock dividers per SM
#   - Flexible GPIO mapping
#   - TX/RX FIFOs (4 entries each per SM)

# ============================================================================
# Base Addresses
# ============================================================================

PIO0_BASE: uint32 = 0x50200000
PIO1_BASE: uint32 = 0x50300000

IO_BANK0_BASE: uint32 = 0x40014000
RESETS_BASE: uint32 = 0x4000C000

# GPIO function select values for PIO
GPIO_FUNC_PIO0: uint32 = 6
GPIO_FUNC_PIO1: uint32 = 7

# ============================================================================
# PIO Register Offsets
# ============================================================================

PIO_CTRL: uint32 = 0x000            # PIO control register
PIO_FSTAT: uint32 = 0x004           # FIFO status register
PIO_FDEBUG: uint32 = 0x008          # FIFO debug register
PIO_FLEVEL: uint32 = 0x00C          # FIFO levels register
PIO_TXF0: uint32 = 0x010            # TX FIFO for SM0
PIO_TXF1: uint32 = 0x014            # TX FIFO for SM1
PIO_TXF2: uint32 = 0x018            # TX FIFO for SM2
PIO_TXF3: uint32 = 0x01C            # TX FIFO for SM3
PIO_RXF0: uint32 = 0x020            # RX FIFO for SM0
PIO_RXF1: uint32 = 0x024            # RX FIFO for SM1
PIO_RXF2: uint32 = 0x028            # RX FIFO for SM2
PIO_RXF3: uint32 = 0x02C            # RX FIFO for SM3
PIO_IRQ: uint32 = 0x030             # IRQ register
PIO_IRQ_FORCE: uint32 = 0x034       # IRQ force register
PIO_INPUT_SYNC_BYPASS: uint32 = 0x038  # Input synchronizer bypass
PIO_DBG_PADOUT: uint32 = 0x03C      # Debug pad output
PIO_DBG_PADOE: uint32 = 0x040       # Debug pad output enable
PIO_DBG_CFGINFO: uint32 = 0x044     # Debug configuration info

# Instruction memory (32 slots x 4 bytes)
PIO_INSTR_MEM0: uint32 = 0x048
PIO_INSTR_MEM1: uint32 = 0x04C
PIO_INSTR_MEM2: uint32 = 0x050
PIO_INSTR_MEM3: uint32 = 0x054
PIO_INSTR_MEM4: uint32 = 0x058
PIO_INSTR_MEM5: uint32 = 0x05C
PIO_INSTR_MEM6: uint32 = 0x060
PIO_INSTR_MEM7: uint32 = 0x064
PIO_INSTR_MEM8: uint32 = 0x068
PIO_INSTR_MEM9: uint32 = 0x06C
PIO_INSTR_MEM10: uint32 = 0x070
PIO_INSTR_MEM11: uint32 = 0x074
PIO_INSTR_MEM12: uint32 = 0x078
PIO_INSTR_MEM13: uint32 = 0x07C
PIO_INSTR_MEM14: uint32 = 0x080
PIO_INSTR_MEM15: uint32 = 0x084
PIO_INSTR_MEM16: uint32 = 0x088
PIO_INSTR_MEM17: uint32 = 0x08C
PIO_INSTR_MEM18: uint32 = 0x090
PIO_INSTR_MEM19: uint32 = 0x094
PIO_INSTR_MEM20: uint32 = 0x098
PIO_INSTR_MEM21: uint32 = 0x09C
PIO_INSTR_MEM22: uint32 = 0x0A0
PIO_INSTR_MEM23: uint32 = 0x0A4
PIO_INSTR_MEM24: uint32 = 0x0A8
PIO_INSTR_MEM25: uint32 = 0x0AC
PIO_INSTR_MEM26: uint32 = 0x0B0
PIO_INSTR_MEM27: uint32 = 0x0B4
PIO_INSTR_MEM28: uint32 = 0x0B8
PIO_INSTR_MEM29: uint32 = 0x0BC
PIO_INSTR_MEM30: uint32 = 0x0C0
PIO_INSTR_MEM31: uint32 = 0x0C4
PIO_INSTR_MEM_BASE: uint32 = 0x048  # Base offset for instruction memory

# ============================================================================
# State Machine Register Offsets (relative to PIO base + SM offset)
# ============================================================================
# SM0 starts at 0x0C8, each SM has 0x18 bytes of registers

PIO_SM0_CLKDIV: uint32 = 0x0C8      # Clock divider
PIO_SM0_EXECCTRL: uint32 = 0x0CC    # Execution control
PIO_SM0_SHIFTCTRL: uint32 = 0x0D0   # Shift control
PIO_SM0_ADDR: uint32 = 0x0D4        # Current instruction address
PIO_SM0_INSTR: uint32 = 0x0D8       # Current/forced instruction
PIO_SM0_PINCTRL: uint32 = 0x0DC     # Pin control

PIO_SM1_CLKDIV: uint32 = 0x0E0
PIO_SM1_EXECCTRL: uint32 = 0x0E4
PIO_SM1_SHIFTCTRL: uint32 = 0x0E8
PIO_SM1_ADDR: uint32 = 0x0EC
PIO_SM1_INSTR: uint32 = 0x0F0
PIO_SM1_PINCTRL: uint32 = 0x0F4

PIO_SM2_CLKDIV: uint32 = 0x0F8
PIO_SM2_EXECCTRL: uint32 = 0x0FC
PIO_SM2_SHIFTCTRL: uint32 = 0x100
PIO_SM2_ADDR: uint32 = 0x104
PIO_SM2_INSTR: uint32 = 0x108
PIO_SM2_PINCTRL: uint32 = 0x10C

PIO_SM3_CLKDIV: uint32 = 0x110
PIO_SM3_EXECCTRL: uint32 = 0x114
PIO_SM3_SHIFTCTRL: uint32 = 0x118
PIO_SM3_ADDR: uint32 = 0x11C
PIO_SM3_INSTR: uint32 = 0x120
PIO_SM3_PINCTRL: uint32 = 0x124

# SM register stride
PIO_SM_STRIDE: uint32 = 0x18

# ============================================================================
# Interrupt Register Offsets
# ============================================================================

PIO_INTR: uint32 = 0x128            # Raw interrupts
PIO_IRQ0_INTE: uint32 = 0x12C       # IRQ0 interrupt enable
PIO_IRQ0_INTF: uint32 = 0x130       # IRQ0 interrupt force
PIO_IRQ0_INTS: uint32 = 0x134       # IRQ0 interrupt status
PIO_IRQ1_INTE: uint32 = 0x138       # IRQ1 interrupt enable
PIO_IRQ1_INTF: uint32 = 0x13C       # IRQ1 interrupt force
PIO_IRQ1_INTS: uint32 = 0x140       # IRQ1 interrupt status

# ============================================================================
# CTRL Register Bits
# ============================================================================

PIO_CTRL_SM_ENABLE_SHIFT: uint32 = 0
PIO_CTRL_SM_RESTART_SHIFT: uint32 = 4
PIO_CTRL_CLKDIV_RESTART_SHIFT: uint32 = 8

# ============================================================================
# FSTAT Register Bits
# ============================================================================

PIO_FSTAT_RXFULL_SHIFT: uint32 = 0
PIO_FSTAT_RXEMPTY_SHIFT: uint32 = 8
PIO_FSTAT_TXFULL_SHIFT: uint32 = 16
PIO_FSTAT_TXEMPTY_SHIFT: uint32 = 24

# ============================================================================
# EXECCTRL Register Bits
# ============================================================================

PIO_EXECCTRL_STATUS_N_SHIFT: uint32 = 0
PIO_EXECCTRL_STATUS_SEL: uint32 = 0x10
PIO_EXECCTRL_WRAP_BOTTOM_SHIFT: uint32 = 7
PIO_EXECCTRL_WRAP_TOP_SHIFT: uint32 = 12
PIO_EXECCTRL_OUT_STICKY: uint32 = 0x20000
PIO_EXECCTRL_INLINE_OUT_EN: uint32 = 0x40000
PIO_EXECCTRL_OUT_EN_SEL_SHIFT: uint32 = 19
PIO_EXECCTRL_JMP_PIN_SHIFT: uint32 = 24
PIO_EXECCTRL_SIDE_PINDIR: uint32 = 0x20000000
PIO_EXECCTRL_SIDE_EN: uint32 = 0x40000000
PIO_EXECCTRL_EXEC_STALLED: uint32 = 0x80000000

# ============================================================================
# SHIFTCTRL Register Bits
# ============================================================================

PIO_SHIFTCTRL_AUTOPUSH: uint32 = 0x10000
PIO_SHIFTCTRL_AUTOPULL: uint32 = 0x20000
PIO_SHIFTCTRL_IN_SHIFTDIR: uint32 = 0x40000    # 1=right, 0=left
PIO_SHIFTCTRL_OUT_SHIFTDIR: uint32 = 0x80000   # 1=right, 0=left
PIO_SHIFTCTRL_PUSH_THRESH_SHIFT: uint32 = 20
PIO_SHIFTCTRL_PULL_THRESH_SHIFT: uint32 = 25
PIO_SHIFTCTRL_FJOIN_TX: uint32 = 0x40000000
PIO_SHIFTCTRL_FJOIN_RX: uint32 = 0x80000000

# ============================================================================
# PINCTRL Register Bits
# ============================================================================

PIO_PINCTRL_OUT_BASE_SHIFT: uint32 = 0
PIO_PINCTRL_SET_BASE_SHIFT: uint32 = 5
PIO_PINCTRL_SIDESET_BASE_SHIFT: uint32 = 10
PIO_PINCTRL_IN_BASE_SHIFT: uint32 = 15
PIO_PINCTRL_OUT_COUNT_SHIFT: uint32 = 20
PIO_PINCTRL_SET_COUNT_SHIFT: uint32 = 26
PIO_PINCTRL_SIDESET_COUNT_SHIFT: uint32 = 29

# ============================================================================
# PIO Instruction Encoding Constants
# ============================================================================

# Instruction types (top 3 bits)
PIO_INSTR_JMP: uint32 = 0x0000
PIO_INSTR_WAIT: uint32 = 0x2000
PIO_INSTR_IN: uint32 = 0x4000
PIO_INSTR_OUT: uint32 = 0x6000
PIO_INSTR_PUSH: uint32 = 0x8000
PIO_INSTR_PULL: uint32 = 0x8080
PIO_INSTR_MOV: uint32 = 0xA000
PIO_INSTR_IRQ: uint32 = 0xC000
PIO_INSTR_SET: uint32 = 0xE000

# JMP conditions
PIO_JMP_ALWAYS: uint32 = 0x00
PIO_JMP_X_ZERO: uint32 = 0x20        # !X (X == 0)
PIO_JMP_X_DEC: uint32 = 0x40         # X-- (post-decrement)
PIO_JMP_Y_ZERO: uint32 = 0x60        # !Y (Y == 0)
PIO_JMP_Y_DEC: uint32 = 0x80         # Y-- (post-decrement)
PIO_JMP_X_NE_Y: uint32 = 0xA0        # X != Y
PIO_JMP_PIN: uint32 = 0xC0           # PIN
PIO_JMP_OSRE_NE: uint32 = 0xE0       # !OSRE (OSR not empty)

# WAIT sources
PIO_WAIT_GPIO: uint32 = 0x00
PIO_WAIT_PIN: uint32 = 0x20
PIO_WAIT_IRQ: uint32 = 0x40

# IN sources
PIO_IN_PINS: uint32 = 0x00
PIO_IN_X: uint32 = 0x20
PIO_IN_Y: uint32 = 0x40
PIO_IN_NULL: uint32 = 0x60
PIO_IN_ISR: uint32 = 0xC0
PIO_IN_OSR: uint32 = 0xE0

# OUT destinations
PIO_OUT_PINS: uint32 = 0x00
PIO_OUT_X: uint32 = 0x20
PIO_OUT_Y: uint32 = 0x40
PIO_OUT_NULL: uint32 = 0x60
PIO_OUT_PINDIRS: uint32 = 0x80
PIO_OUT_PC: uint32 = 0xA0
PIO_OUT_ISR: uint32 = 0xC0
PIO_OUT_EXEC: uint32 = 0xE0

# MOV destinations
PIO_MOV_DST_PINS: uint32 = 0x00
PIO_MOV_DST_X: uint32 = 0x20
PIO_MOV_DST_Y: uint32 = 0x40
PIO_MOV_DST_EXEC: uint32 = 0x80
PIO_MOV_DST_PC: uint32 = 0xA0
PIO_MOV_DST_ISR: uint32 = 0xC0
PIO_MOV_DST_OSR: uint32 = 0xE0

# MOV sources
PIO_MOV_SRC_PINS: uint32 = 0x00
PIO_MOV_SRC_X: uint32 = 0x01
PIO_MOV_SRC_Y: uint32 = 0x02
PIO_MOV_SRC_NULL: uint32 = 0x03
PIO_MOV_SRC_STATUS: uint32 = 0x05
PIO_MOV_SRC_ISR: uint32 = 0x06
PIO_MOV_SRC_OSR: uint32 = 0x07

# MOV operations
PIO_MOV_OP_NONE: uint32 = 0x00
PIO_MOV_OP_INVERT: uint32 = 0x08
PIO_MOV_OP_BITREV: uint32 = 0x10

# SET destinations
PIO_SET_PINS: uint32 = 0x00
PIO_SET_X: uint32 = 0x20
PIO_SET_Y: uint32 = 0x40
PIO_SET_PINDIRS: uint32 = 0x80

# ============================================================================
# Program Memory Tracking
# ============================================================================

# Track used instruction slots per PIO (bitmask of 32 bits)
_pio0_used_slots: uint32 = 0
_pio1_used_slots: uint32 = 0

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

def _pio_base(pio: uint32) -> uint32:
    """Get base address for PIO instance."""
    if pio == 0:
        return PIO0_BASE
    return PIO1_BASE

def _pio_sm_offset(sm: uint32) -> uint32:
    """Get register offset for state machine."""
    return sm * PIO_SM_STRIDE

def _pio_txf_offset(sm: uint32) -> uint32:
    """Get TX FIFO register offset for state machine."""
    return PIO_TXF0 + (sm * 4)

def _pio_rxf_offset(sm: uint32) -> uint32:
    """Get RX FIFO register offset for state machine."""
    return PIO_RXF0 + (sm * 4)

# ============================================================================
# PIO Core Functions
# ============================================================================

def pio_init(pio: uint32):
    """Initialize PIO block.

    Brings PIO out of reset and clears instruction memory.

    Args:
        pio: PIO instance (0 or 1)
    """
    global _pio0_used_slots
    global _pio1_used_slots

    if pio > 1:
        return

    # Unreset PIO from RESETS register
    reset_bit: uint32 = 10 if pio == 0 else 11
    reset_val: uint32 = mmio_read(RESETS_BASE)
    mmio_write(RESETS_BASE, reset_val & ~(1 << reset_bit))

    # Wait for reset done
    timeout: int32 = 10000
    while timeout > 0:
        done: uint32 = mmio_read(RESETS_BASE + 0x08)
        if (done & (1 << reset_bit)) != 0:
            break
        timeout = timeout - 1

    # Clear instruction memory and tracking
    pio_clear_instruction_memory(pio)

    # Clear used slots tracking
    if pio == 0:
        _pio0_used_slots = 0
    else:
        _pio1_used_slots = 0

def pio_get_index(pio: uint32) -> uint32:
    """Get PIO index from base address.

    Args:
        pio: PIO base address or index

    Returns:
        0 or 1
    """
    if pio == PIO0_BASE or pio == 0:
        return 0
    return 1

def pio_clear_instruction_memory(pio: uint32):
    """Clear all instruction memory slots.

    Args:
        pio: PIO instance (0 or 1)
    """
    global _pio0_used_slots
    global _pio1_used_slots

    base: uint32 = _pio_base(pio)

    i: uint32 = 0
    while i < 32:
        mmio_write(base + PIO_INSTR_MEM_BASE + (i * 4), 0)
        i = i + 1

    # Clear tracking
    if pio == 0:
        _pio0_used_slots = 0
    else:
        _pio1_used_slots = 0

# ============================================================================
# Program Loading Functions
# ============================================================================

def pio_can_add_program(pio: uint32, length: uint32) -> bool:
    """Check if program can be added to instruction memory.

    Args:
        pio: PIO instance (0 or 1)
        length: Number of instructions

    Returns:
        True if enough contiguous space is available
    """
    global _pio0_used_slots
    global _pio1_used_slots

    if length > 32 or length == 0:
        return False

    used: uint32 = _pio0_used_slots if pio == 0 else _pio1_used_slots

    # Find contiguous space
    offset: uint32 = 0
    while offset <= 32 - length:
        mask: uint32 = ((1 << length) - 1) << offset
        if (used & mask) == 0:
            return True
        offset = offset + 1

    return False

def pio_add_program(pio: uint32, instructions: Ptr[uint16], length: uint32) -> int32:
    """Add program to instruction memory.

    Args:
        pio: PIO instance (0 or 1)
        instructions: Array of PIO instructions
        length: Number of instructions

    Returns:
        Offset where program was loaded, or -1 on failure
    """
    global _pio0_used_slots
    global _pio1_used_slots

    if length > 32 or length == 0:
        return -1

    base: uint32 = _pio_base(pio)
    used: uint32 = _pio0_used_slots if pio == 0 else _pio1_used_slots

    # Find contiguous space
    offset: uint32 = 0
    while offset <= 32 - length:
        mask: uint32 = ((1 << length) - 1) << offset
        if (used & mask) == 0:
            # Found space, load program
            i: uint32 = 0
            while i < length:
                instr: uint32 = cast[uint32](instructions[i])
                mmio_write(base + PIO_INSTR_MEM_BASE + ((offset + i) * 4), instr)
                i = i + 1

            # Mark slots as used
            if pio == 0:
                _pio0_used_slots = used | mask
            else:
                _pio1_used_slots = used | mask

            return cast[int32](offset)

        offset = offset + 1

    return -1

def pio_add_program_at_offset(pio: uint32, instructions: Ptr[uint16], length: uint32, offset: uint32) -> bool:
    """Add program at specific offset in instruction memory.

    Args:
        pio: PIO instance (0 or 1)
        instructions: Array of PIO instructions
        length: Number of instructions
        offset: Offset to load program at

    Returns:
        True on success
    """
    global _pio0_used_slots
    global _pio1_used_slots

    if length > 32 or length == 0 or offset + length > 32:
        return False

    base: uint32 = _pio_base(pio)
    used: uint32 = _pio0_used_slots if pio == 0 else _pio1_used_slots

    mask: uint32 = ((1 << length) - 1) << offset
    if (used & mask) != 0:
        return False  # Space already in use

    # Load program
    i: uint32 = 0
    while i < length:
        instr: uint32 = cast[uint32](instructions[i])
        mmio_write(base + PIO_INSTR_MEM_BASE + ((offset + i) * 4), instr)
        i = i + 1

    # Mark slots as used
    if pio == 0:
        _pio0_used_slots = used | mask
    else:
        _pio1_used_slots = used | mask

    return True

def pio_remove_program(pio: uint32, offset: uint32, length: uint32):
    """Remove program from instruction memory.

    Args:
        pio: PIO instance (0 or 1)
        offset: Offset where program was loaded
        length: Number of instructions
    """
    global _pio0_used_slots
    global _pio1_used_slots

    if offset + length > 32:
        return

    base: uint32 = _pio_base(pio)
    used: uint32 = _pio0_used_slots if pio == 0 else _pio1_used_slots

    # Clear instruction memory
    i: uint32 = 0
    while i < length:
        mmio_write(base + PIO_INSTR_MEM_BASE + ((offset + i) * 4), 0)
        i = i + 1

    # Clear used bits
    mask: uint32 = ((1 << length) - 1) << offset
    if pio == 0:
        _pio0_used_slots = used & ~mask
    else:
        _pio1_used_slots = used & ~mask

# ============================================================================
# State Machine Control Functions
# ============================================================================

def pio_sm_init(pio: uint32, sm: uint32, offset: uint32):
    """Initialize state machine.

    Disables the SM, configures starting address, clears FIFOs.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        offset: Program offset in instruction memory
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)

    # Disable state machine
    pio_sm_set_enabled(pio, sm, False)

    # Clear FIFOs
    fdebug_clear: uint32 = (1 << (sm + 24)) | (1 << (sm + 16)) | (1 << (sm + 8)) | (1 << sm)
    mmio_write(base + PIO_FDEBUG, fdebug_clear)

    # Set starting address by executing JMP instruction
    pio_sm_exec(pio, sm, pio_encode_jmp(PIO_JMP_ALWAYS, offset))

    # Restart SM
    pio_sm_restart(pio, sm)
    pio_sm_clkdiv_restart(pio, sm)

def pio_sm_set_enabled(pio: uint32, sm: uint32, enabled: bool):
    """Enable or disable state machine.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        enabled: True to enable, False to disable
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    ctrl: uint32 = mmio_read(base + PIO_CTRL)

    mask: uint32 = 1 << (PIO_CTRL_SM_ENABLE_SHIFT + sm)
    if enabled:
        ctrl = ctrl | mask
    else:
        ctrl = ctrl & ~mask

    mmio_write(base + PIO_CTRL, ctrl)

def pio_sm_restart(pio: uint32, sm: uint32):
    """Restart state machine.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    ctrl: uint32 = mmio_read(base + PIO_CTRL)
    ctrl = ctrl | (1 << (PIO_CTRL_SM_RESTART_SHIFT + sm))
    mmio_write(base + PIO_CTRL, ctrl)

def pio_sm_clkdiv_restart(pio: uint32, sm: uint32):
    """Restart clock divider for state machine.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    ctrl: uint32 = mmio_read(base + PIO_CTRL)
    ctrl = ctrl | (1 << (PIO_CTRL_CLKDIV_RESTART_SHIFT + sm))
    mmio_write(base + PIO_CTRL, ctrl)

def pio_sm_exec(pio: uint32, sm: uint32, instr: uint32):
    """Execute instruction immediately.

    The instruction is not stored in instruction memory.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        instr: 16-bit PIO instruction
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)
    mmio_write(base + PIO_SM0_INSTR + sm_offset, instr & 0xFFFF)

def pio_sm_exec_wait(pio: uint32, sm: uint32, instr: uint32):
    """Execute instruction and wait for completion.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        instr: 16-bit PIO instruction
    """
    pio_sm_exec(pio, sm, instr)

    # Wait for stall to clear
    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    while True:
        execctrl: uint32 = mmio_read(base + PIO_SM0_EXECCTRL + sm_offset)
        if (execctrl & PIO_EXECCTRL_EXEC_STALLED) == 0:
            break

# ============================================================================
# Configuration Functions
# ============================================================================

def pio_sm_set_clkdiv(pio: uint32, sm: uint32, div: uint32):
    """Set clock divider for state machine.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        div: Clock divider (8.8 fixed point, so 256 = 1.0)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)
    # CLKDIV register: bits 16-31 are integer, bits 8-15 are fraction
    mmio_write(base + PIO_SM0_CLKDIV + sm_offset, div << 8)

def pio_sm_set_clkdiv_int_frac(pio: uint32, sm: uint32, int_div: uint32, frac_div: uint32):
    """Set clock divider with integer and fractional parts.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        int_div: Integer divisor (1-65535)
        frac_div: Fractional divisor (0-255)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)
    clkdiv: uint32 = (int_div << 16) | (frac_div << 8)
    mmio_write(base + PIO_SM0_CLKDIV + sm_offset, clkdiv)

def pio_sm_set_pins(pio: uint32, sm: uint32, values: uint32):
    """Set pin values using SET instruction.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        values: Pin values (5 bits)
    """
    pio_sm_exec(pio, sm, pio_encode_set(PIO_SET_PINS, values & 0x1F))

def pio_sm_set_pindirs(pio: uint32, sm: uint32, dirs: uint32):
    """Set pin directions using SET instruction.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        dirs: Pin directions (1 = output, 5 bits)
    """
    pio_sm_exec(pio, sm, pio_encode_set(PIO_SET_PINDIRS, dirs & 0x1F))

def pio_sm_set_wrap(pio: uint32, sm: uint32, wrap_target: uint32, wrap_top: uint32):
    """Set program wrap addresses.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        wrap_target: Address to wrap to (0-31)
        wrap_top: Address to wrap from (0-31)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    execctrl: uint32 = mmio_read(base + PIO_SM0_EXECCTRL + sm_offset)
    # Clear wrap bits
    execctrl = execctrl & ~((0x1F << PIO_EXECCTRL_WRAP_BOTTOM_SHIFT) | (0x1F << PIO_EXECCTRL_WRAP_TOP_SHIFT))
    # Set new wrap addresses
    execctrl = execctrl | ((wrap_target & 0x1F) << PIO_EXECCTRL_WRAP_BOTTOM_SHIFT)
    execctrl = execctrl | ((wrap_top & 0x1F) << PIO_EXECCTRL_WRAP_TOP_SHIFT)
    mmio_write(base + PIO_SM0_EXECCTRL + sm_offset, execctrl)

def pio_sm_set_sideset(pio: uint32, sm: uint32, bit_count: uint32, optional: bool, pindirs: bool):
    """Configure sideset options.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        bit_count: Number of sideset bits (0-5)
        optional: If True, sideset is optional (uses MSB as enable)
        pindirs: If True, sideset controls pin direction instead of value
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    # Update EXECCTRL
    execctrl: uint32 = mmio_read(base + PIO_SM0_EXECCTRL + sm_offset)

    if optional:
        execctrl = execctrl | PIO_EXECCTRL_SIDE_EN
    else:
        execctrl = execctrl & ~PIO_EXECCTRL_SIDE_EN

    if pindirs:
        execctrl = execctrl | PIO_EXECCTRL_SIDE_PINDIR
    else:
        execctrl = execctrl & ~PIO_EXECCTRL_SIDE_PINDIR

    mmio_write(base + PIO_SM0_EXECCTRL + sm_offset, execctrl)

    # Update PINCTRL with sideset count
    pinctrl: uint32 = mmio_read(base + PIO_SM0_PINCTRL + sm_offset)
    pinctrl = pinctrl & ~(0x7 << PIO_PINCTRL_SIDESET_COUNT_SHIFT)
    pinctrl = pinctrl | ((bit_count & 0x7) << PIO_PINCTRL_SIDESET_COUNT_SHIFT)
    mmio_write(base + PIO_SM0_PINCTRL + sm_offset, pinctrl)

# ============================================================================
# Pin Mapping Functions
# ============================================================================

def pio_sm_set_out_pins(pio: uint32, sm: uint32, base_pin: uint32, count: uint32):
    """Set OUT pin mapping.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        base_pin: First GPIO pin (0-31)
        count: Number of consecutive pins (1-32)
    """
    if sm > 3:
        return

    pio_base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    pinctrl: uint32 = mmio_read(pio_base + PIO_SM0_PINCTRL + sm_offset)
    pinctrl = pinctrl & ~((0x1F << PIO_PINCTRL_OUT_BASE_SHIFT) | (0x3F << PIO_PINCTRL_OUT_COUNT_SHIFT))
    pinctrl = pinctrl | ((base_pin & 0x1F) << PIO_PINCTRL_OUT_BASE_SHIFT)
    pinctrl = pinctrl | ((count & 0x3F) << PIO_PINCTRL_OUT_COUNT_SHIFT)
    mmio_write(pio_base + PIO_SM0_PINCTRL + sm_offset, pinctrl)

def pio_sm_set_set_pins(pio: uint32, sm: uint32, base_pin: uint32, count: uint32):
    """Set SET pin mapping.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        base_pin: First GPIO pin (0-31)
        count: Number of consecutive pins (1-5)
    """
    if sm > 3:
        return

    pio_base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    pinctrl: uint32 = mmio_read(pio_base + PIO_SM0_PINCTRL + sm_offset)
    pinctrl = pinctrl & ~((0x1F << PIO_PINCTRL_SET_BASE_SHIFT) | (0x7 << PIO_PINCTRL_SET_COUNT_SHIFT))
    pinctrl = pinctrl | ((base_pin & 0x1F) << PIO_PINCTRL_SET_BASE_SHIFT)
    pinctrl = pinctrl | ((count & 0x7) << PIO_PINCTRL_SET_COUNT_SHIFT)
    mmio_write(pio_base + PIO_SM0_PINCTRL + sm_offset, pinctrl)

def pio_sm_set_in_pins(pio: uint32, sm: uint32, base_pin: uint32):
    """Set IN pin mapping.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        base_pin: First GPIO pin (0-31)
    """
    if sm > 3:
        return

    pio_base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    pinctrl: uint32 = mmio_read(pio_base + PIO_SM0_PINCTRL + sm_offset)
    pinctrl = pinctrl & ~(0x1F << PIO_PINCTRL_IN_BASE_SHIFT)
    pinctrl = pinctrl | ((base_pin & 0x1F) << PIO_PINCTRL_IN_BASE_SHIFT)
    mmio_write(pio_base + PIO_SM0_PINCTRL + sm_offset, pinctrl)

def pio_sm_set_sideset_pins(pio: uint32, sm: uint32, base_pin: uint32):
    """Set sideset pin mapping.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        base_pin: First GPIO pin (0-31)
    """
    if sm > 3:
        return

    pio_base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    pinctrl: uint32 = mmio_read(pio_base + PIO_SM0_PINCTRL + sm_offset)
    pinctrl = pinctrl & ~(0x1F << PIO_PINCTRL_SIDESET_BASE_SHIFT)
    pinctrl = pinctrl | ((base_pin & 0x1F) << PIO_PINCTRL_SIDESET_BASE_SHIFT)
    mmio_write(pio_base + PIO_SM0_PINCTRL + sm_offset, pinctrl)

def pio_gpio_init(pio: uint32, gpio: uint32):
    """Set GPIO function to PIO.

    Args:
        pio: PIO instance (0 or 1)
        gpio: GPIO pin number (0-29)
    """
    if gpio > 29:
        return

    func: uint32 = GPIO_FUNC_PIO0 if pio == 0 else GPIO_FUNC_PIO1
    ctrl_addr: uint32 = IO_BANK0_BASE + 4 + (gpio * 8)
    mmio_write(ctrl_addr, func)

# ============================================================================
# FIFO Operations
# ============================================================================

def pio_sm_is_tx_fifo_empty(pio: uint32, sm: uint32) -> bool:
    """Check if TX FIFO is empty.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)

    Returns:
        True if TX FIFO is empty
    """
    base: uint32 = _pio_base(pio)
    fstat: uint32 = mmio_read(base + PIO_FSTAT)
    return ((fstat >> (PIO_FSTAT_TXEMPTY_SHIFT + sm)) & 1) != 0

def pio_sm_is_tx_fifo_full(pio: uint32, sm: uint32) -> bool:
    """Check if TX FIFO is full.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)

    Returns:
        True if TX FIFO is full
    """
    base: uint32 = _pio_base(pio)
    fstat: uint32 = mmio_read(base + PIO_FSTAT)
    return ((fstat >> (PIO_FSTAT_TXFULL_SHIFT + sm)) & 1) != 0

def pio_sm_get_tx_fifo_level(pio: uint32, sm: uint32) -> uint32:
    """Get TX FIFO level.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)

    Returns:
        Number of entries in TX FIFO (0-4, or 0-8 if joined)
    """
    base: uint32 = _pio_base(pio)
    flevel: uint32 = mmio_read(base + PIO_FLEVEL)
    shift: uint32 = (sm * 8) + 4
    return (flevel >> shift) & 0xF

def pio_sm_is_rx_fifo_empty(pio: uint32, sm: uint32) -> bool:
    """Check if RX FIFO is empty.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)

    Returns:
        True if RX FIFO is empty
    """
    base: uint32 = _pio_base(pio)
    fstat: uint32 = mmio_read(base + PIO_FSTAT)
    return ((fstat >> (PIO_FSTAT_RXEMPTY_SHIFT + sm)) & 1) != 0

def pio_sm_is_rx_fifo_full(pio: uint32, sm: uint32) -> bool:
    """Check if RX FIFO is full.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)

    Returns:
        True if RX FIFO is full
    """
    base: uint32 = _pio_base(pio)
    fstat: uint32 = mmio_read(base + PIO_FSTAT)
    return ((fstat >> (PIO_FSTAT_RXFULL_SHIFT + sm)) & 1) != 0

def pio_sm_get_rx_fifo_level(pio: uint32, sm: uint32) -> uint32:
    """Get RX FIFO level.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)

    Returns:
        Number of entries in RX FIFO (0-4, or 0-8 if joined)
    """
    base: uint32 = _pio_base(pio)
    flevel: uint32 = mmio_read(base + PIO_FLEVEL)
    shift: uint32 = sm * 8
    return (flevel >> shift) & 0xF

def pio_sm_put(pio: uint32, sm: uint32, data: uint32):
    """Write data to TX FIFO (non-blocking).

    Does not check if FIFO is full.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        data: 32-bit data to write
    """
    base: uint32 = _pio_base(pio)
    txf_offset: uint32 = _pio_txf_offset(sm)
    mmio_write(base + txf_offset, data)

def pio_sm_put_blocking(pio: uint32, sm: uint32, data: uint32):
    """Write data to TX FIFO (blocking).

    Waits until FIFO has space.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        data: 32-bit data to write
    """
    while pio_sm_is_tx_fifo_full(pio, sm):
        pass
    pio_sm_put(pio, sm, data)

def pio_sm_get(pio: uint32, sm: uint32) -> uint32:
    """Read data from RX FIFO (non-blocking).

    Does not check if FIFO is empty.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)

    Returns:
        32-bit data from RX FIFO
    """
    base: uint32 = _pio_base(pio)
    rxf_offset: uint32 = _pio_rxf_offset(sm)
    return mmio_read(base + rxf_offset)

def pio_sm_get_blocking(pio: uint32, sm: uint32) -> uint32:
    """Read data from RX FIFO (blocking).

    Waits until FIFO has data.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)

    Returns:
        32-bit data from RX FIFO
    """
    while pio_sm_is_rx_fifo_empty(pio, sm):
        pass
    return pio_sm_get(pio, sm)

def pio_sm_drain_tx_fifo(pio: uint32, sm: uint32):
    """Drain TX FIFO by executing OUT instructions.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
    """
    # Save autopull setting
    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)
    shiftctrl: uint32 = mmio_read(base + PIO_SM0_SHIFTCTRL + sm_offset)

    # Disable autopull
    mmio_write(base + PIO_SM0_SHIFTCTRL + sm_offset, shiftctrl & ~PIO_SHIFTCTRL_AUTOPULL)

    # Execute OUT NULL, 32 to drain OSR and trigger pull
    while not pio_sm_is_tx_fifo_empty(pio, sm):
        pio_sm_exec(pio, sm, pio_encode_out(PIO_OUT_NULL, 32))

    # Restore autopull
    mmio_write(base + PIO_SM0_SHIFTCTRL + sm_offset, shiftctrl)

# ============================================================================
# Interrupt Control
# ============================================================================

def pio_set_irq_enabled(pio: uint32, irq_num: uint32, enabled: bool):
    """Enable or disable PIO interrupt.

    Args:
        pio: PIO instance (0 or 1)
        irq_num: Interrupt number (0 or 1)
        enabled: True to enable
    """
    base: uint32 = _pio_base(pio)

    inte_offset: uint32 = PIO_IRQ0_INTE if irq_num == 0 else PIO_IRQ1_INTE
    inte: uint32 = mmio_read(base + inte_offset)

    if enabled:
        inte = inte | 0xFF  # Enable all SM interrupts
    else:
        inte = inte & ~0xFF

    mmio_write(base + inte_offset, inte)

def pio_set_sm_irq_enabled(pio: uint32, irq_num: uint32, sm: uint32, enabled: bool):
    """Enable or disable state machine interrupt.

    Args:
        pio: PIO instance (0 or 1)
        irq_num: IRQ number (0 or 1)
        sm: State machine (0-3)
        enabled: True to enable
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    inte_offset: uint32 = PIO_IRQ0_INTE if irq_num == 0 else PIO_IRQ1_INTE
    inte: uint32 = mmio_read(base + inte_offset)

    # SM interrupts are in bits 0-3 (TX not full) and 4-7 (RX not empty)
    mask: uint32 = (1 << sm) | (1 << (sm + 4))

    if enabled:
        inte = inte | mask
    else:
        inte = inte & ~mask

    mmio_write(base + inte_offset, inte)

def pio_interrupt_get(pio: uint32, num: uint32) -> bool:
    """Get PIO interrupt flag status.

    Args:
        pio: PIO instance (0 or 1)
        num: Interrupt flag number (0-7)

    Returns:
        True if interrupt flag is set
    """
    if num > 7:
        return False

    base: uint32 = _pio_base(pio)
    irq: uint32 = mmio_read(base + PIO_IRQ)
    return ((irq >> num) & 1) != 0

def pio_interrupt_clear(pio: uint32, num: uint32):
    """Clear PIO interrupt flag.

    Args:
        pio: PIO instance (0 or 1)
        num: Interrupt flag number (0-7)
    """
    if num > 7:
        return

    base: uint32 = _pio_base(pio)
    mmio_write(base + PIO_IRQ, 1 << num)

def pio_interrupt_force(pio: uint32, num: uint32):
    """Force PIO interrupt flag.

    Args:
        pio: PIO instance (0 or 1)
        num: Interrupt flag number (0-7)
    """
    if num > 7:
        return

    base: uint32 = _pio_base(pio)
    mmio_write(base + PIO_IRQ_FORCE, 1 << num)

# ============================================================================
# Shift Control Configuration
# ============================================================================

def pio_sm_set_autopush(pio: uint32, sm: uint32, enabled: bool, threshold: uint32):
    """Configure autopush.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        enabled: Enable autopush
        threshold: Push threshold (1-32, 0 = 32)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    shiftctrl: uint32 = mmio_read(base + PIO_SM0_SHIFTCTRL + sm_offset)

    # Clear autopush and threshold bits
    shiftctrl = shiftctrl & ~(PIO_SHIFTCTRL_AUTOPUSH | (0x1F << PIO_SHIFTCTRL_PUSH_THRESH_SHIFT))

    if enabled:
        shiftctrl = shiftctrl | PIO_SHIFTCTRL_AUTOPUSH

    shiftctrl = shiftctrl | ((threshold & 0x1F) << PIO_SHIFTCTRL_PUSH_THRESH_SHIFT)
    mmio_write(base + PIO_SM0_SHIFTCTRL + sm_offset, shiftctrl)

def pio_sm_set_autopull(pio: uint32, sm: uint32, enabled: bool, threshold: uint32):
    """Configure autopull.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        enabled: Enable autopull
        threshold: Pull threshold (1-32, 0 = 32)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    shiftctrl: uint32 = mmio_read(base + PIO_SM0_SHIFTCTRL + sm_offset)

    # Clear autopull and threshold bits
    shiftctrl = shiftctrl & ~(PIO_SHIFTCTRL_AUTOPULL | (0x1F << PIO_SHIFTCTRL_PULL_THRESH_SHIFT))

    if enabled:
        shiftctrl = shiftctrl | PIO_SHIFTCTRL_AUTOPULL

    shiftctrl = shiftctrl | ((threshold & 0x1F) << PIO_SHIFTCTRL_PULL_THRESH_SHIFT)
    mmio_write(base + PIO_SM0_SHIFTCTRL + sm_offset, shiftctrl)

def pio_sm_set_in_shift(pio: uint32, sm: uint32, shift_right: bool, autopush: bool, push_threshold: uint32):
    """Configure input shift register.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        shift_right: True to shift right, False for left
        autopush: Enable autopush
        push_threshold: Push threshold (1-32)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    shiftctrl: uint32 = mmio_read(base + PIO_SM0_SHIFTCTRL + sm_offset)

    # Clear relevant bits
    shiftctrl = shiftctrl & ~(PIO_SHIFTCTRL_IN_SHIFTDIR | PIO_SHIFTCTRL_AUTOPUSH | (0x1F << PIO_SHIFTCTRL_PUSH_THRESH_SHIFT))

    if shift_right:
        shiftctrl = shiftctrl | PIO_SHIFTCTRL_IN_SHIFTDIR
    if autopush:
        shiftctrl = shiftctrl | PIO_SHIFTCTRL_AUTOPUSH

    shiftctrl = shiftctrl | ((push_threshold & 0x1F) << PIO_SHIFTCTRL_PUSH_THRESH_SHIFT)
    mmio_write(base + PIO_SM0_SHIFTCTRL + sm_offset, shiftctrl)

def pio_sm_set_out_shift(pio: uint32, sm: uint32, shift_right: bool, autopull: bool, pull_threshold: uint32):
    """Configure output shift register.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        shift_right: True to shift right, False for left
        autopull: Enable autopull
        pull_threshold: Pull threshold (1-32)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    shiftctrl: uint32 = mmio_read(base + PIO_SM0_SHIFTCTRL + sm_offset)

    # Clear relevant bits
    shiftctrl = shiftctrl & ~(PIO_SHIFTCTRL_OUT_SHIFTDIR | PIO_SHIFTCTRL_AUTOPULL | (0x1F << PIO_SHIFTCTRL_PULL_THRESH_SHIFT))

    if shift_right:
        shiftctrl = shiftctrl | PIO_SHIFTCTRL_OUT_SHIFTDIR
    if autopull:
        shiftctrl = shiftctrl | PIO_SHIFTCTRL_AUTOPULL

    shiftctrl = shiftctrl | ((pull_threshold & 0x1F) << PIO_SHIFTCTRL_PULL_THRESH_SHIFT)
    mmio_write(base + PIO_SM0_SHIFTCTRL + sm_offset, shiftctrl)

def pio_sm_set_fifo_join(pio: uint32, sm: uint32, join_tx: bool, join_rx: bool):
    """Configure FIFO joining.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        join_tx: Join TX FIFO (8-entry TX, no RX)
        join_rx: Join RX FIFO (8-entry RX, no TX)
    """
    if sm > 3:
        return

    base: uint32 = _pio_base(pio)
    sm_offset: uint32 = _pio_sm_offset(sm)

    shiftctrl: uint32 = mmio_read(base + PIO_SM0_SHIFTCTRL + sm_offset)
    shiftctrl = shiftctrl & ~(PIO_SHIFTCTRL_FJOIN_TX | PIO_SHIFTCTRL_FJOIN_RX)

    if join_tx:
        shiftctrl = shiftctrl | PIO_SHIFTCTRL_FJOIN_TX
    if join_rx:
        shiftctrl = shiftctrl | PIO_SHIFTCTRL_FJOIN_RX

    mmio_write(base + PIO_SM0_SHIFTCTRL + sm_offset, shiftctrl)

# ============================================================================
# PIO Instruction Encoding Helpers
# ============================================================================

def pio_encode_jmp(condition: uint32, address: uint32) -> uint32:
    """Encode JMP instruction.

    Args:
        condition: Jump condition (PIO_JMP_*)
        address: Target address (0-31)

    Returns:
        Encoded 16-bit instruction
    """
    return PIO_INSTR_JMP | (condition & 0xE0) | (address & 0x1F)

def pio_encode_wait(polarity: uint32, source: uint32, index: uint32) -> uint32:
    """Encode WAIT instruction.

    Args:
        polarity: 1 to wait for high, 0 for low
        source: Wait source (PIO_WAIT_GPIO, PIO_WAIT_PIN, PIO_WAIT_IRQ)
        index: GPIO/pin/IRQ number

    Returns:
        Encoded 16-bit instruction
    """
    return PIO_INSTR_WAIT | ((polarity & 1) << 7) | (source & 0x60) | (index & 0x1F)

def pio_encode_in(source: uint32, bit_count: uint32) -> uint32:
    """Encode IN instruction.

    Args:
        source: Input source (PIO_IN_*)
        bit_count: Number of bits to shift in (1-32, 32 encoded as 0)

    Returns:
        Encoded 16-bit instruction
    """
    count: uint32 = bit_count & 0x1F
    if bit_count == 32:
        count = 0
    return PIO_INSTR_IN | (source & 0xE0) | count

def pio_encode_out(destination: uint32, bit_count: uint32) -> uint32:
    """Encode OUT instruction.

    Args:
        destination: Output destination (PIO_OUT_*)
        bit_count: Number of bits to shift out (1-32, 32 encoded as 0)

    Returns:
        Encoded 16-bit instruction
    """
    count: uint32 = bit_count & 0x1F
    if bit_count == 32:
        count = 0
    return PIO_INSTR_OUT | (destination & 0xE0) | count

def pio_encode_push(if_full: bool, block: bool) -> uint32:
    """Encode PUSH instruction.

    Args:
        if_full: Only push if ISR is full
        block: Block if RX FIFO is full

    Returns:
        Encoded 16-bit instruction
    """
    instr: uint32 = PIO_INSTR_PUSH
    if if_full:
        instr = instr | 0x40
    if block:
        instr = instr | 0x20
    return instr

def pio_encode_pull(if_empty: bool, block: bool) -> uint32:
    """Encode PULL instruction.

    Args:
        if_empty: Only pull if OSR is empty
        block: Block if TX FIFO is empty

    Returns:
        Encoded 16-bit instruction
    """
    instr: uint32 = PIO_INSTR_PULL
    if if_empty:
        instr = instr | 0x40
    if block:
        instr = instr | 0x20
    return instr

def pio_encode_mov(destination: uint32, source: uint32) -> uint32:
    """Encode MOV instruction.

    Args:
        destination: MOV destination (PIO_MOV_DST_*)
        source: MOV source (PIO_MOV_SRC_*)

    Returns:
        Encoded 16-bit instruction
    """
    return PIO_INSTR_MOV | (destination & 0xE0) | (source & 0x1F)

def pio_encode_mov_op(destination: uint32, op: uint32, source: uint32) -> uint32:
    """Encode MOV instruction with operation.

    Args:
        destination: MOV destination (PIO_MOV_DST_*)
        op: Operation (PIO_MOV_OP_NONE, PIO_MOV_OP_INVERT, PIO_MOV_OP_BITREV)
        source: MOV source (PIO_MOV_SRC_*)

    Returns:
        Encoded 16-bit instruction
    """
    return PIO_INSTR_MOV | (destination & 0xE0) | (op & 0x18) | (source & 0x07)

def pio_encode_irq(clear: bool, wait: bool, index: uint32) -> uint32:
    """Encode IRQ instruction.

    Args:
        clear: Clear interrupt flag
        wait: Wait for interrupt to be cleared
        index: IRQ number (0-7, or 0x10 for relative)

    Returns:
        Encoded 16-bit instruction
    """
    instr: uint32 = PIO_INSTR_IRQ | (index & 0x1F)
    if clear:
        instr = instr | 0x40
    if wait:
        instr = instr | 0x20
    return instr

def pio_encode_set(destination: uint32, data: uint32) -> uint32:
    """Encode SET instruction.

    Args:
        destination: SET destination (PIO_SET_*)
        data: 5-bit data value

    Returns:
        Encoded 16-bit instruction
    """
    return PIO_INSTR_SET | (destination & 0xE0) | (data & 0x1F)

def pio_encode_nop() -> uint32:
    """Encode NOP instruction (MOV Y, Y).

    Returns:
        Encoded 16-bit instruction
    """
    return pio_encode_mov(PIO_MOV_DST_Y, PIO_MOV_SRC_Y)

def pio_encode_sideset(value: uint32, bit_count: uint32) -> uint32:
    """Create sideset value to OR with instruction.

    Args:
        value: Sideset value
        bit_count: Number of sideset bits

    Returns:
        Value to OR with instruction
    """
    # Sideset is in bits 8-12 of instruction, shifted based on bit count
    shift: uint32 = 13 - bit_count
    return (value & ((1 << bit_count) - 1)) << shift

def pio_encode_delay(cycles: uint32) -> uint32:
    """Create delay value to OR with instruction.

    Args:
        cycles: Delay cycles (0-31)

    Returns:
        Value to OR with instruction (goes in bits 8-12)
    """
    return (cycles & 0x1F) << 8

# ============================================================================
# Example Programs
# ============================================================================

# Simple blink program - toggles pin every N cycles
# .wrap_target
# set pins, 1   [31]  ; Set pin high, delay 31
# set pins, 0   [31]  ; Set pin low, delay 31
# .wrap
BLINK_PROGRAM: Array[uint16, 2] = [
    cast[uint16](0xE001 | (31 << 8)),  # set pins, 1 [31]
    cast[uint16](0xE000 | (31 << 8)),  # set pins, 0 [31]
]
BLINK_PROGRAM_LENGTH: uint32 = 2

# UART TX program (8N1)
# .wrap_target
# pull block           ; Pull 32 bits from FIFO
# set x, 7       [7]   ; 8 data bits
# set pins, 0          ; Start bit
# bitloop:
# out pins, 1    [6]   ; Output bit, delay
# jmp x-- bitloop      ; Loop for all bits
# set pins, 1    [6]   ; Stop bit
# .wrap
UART_TX_PROGRAM: Array[uint16, 6] = [
    cast[uint16](0x80A0),              # pull block
    cast[uint16](0xE027 | (7 << 8)),   # set x, 7 [7]
    cast[uint16](0xE000),              # set pins, 0
    cast[uint16](0x6001 | (6 << 8)),   # out pins, 1 [6]
    cast[uint16](0x0043),              # jmp x-- 3
    cast[uint16](0xE001 | (6 << 8)),   # set pins, 1 [6]
]
UART_TX_PROGRAM_LENGTH: uint32 = 6

# WS2812 LED driver program
# T1 = 2 cycles, T2 = 5 cycles, T3 = 3 cycles (800kHz with 10MHz SM clock)
# .wrap_target
# bitloop:
# out x, 1             ; Get next bit
# jmp !x, do_zero      ; If zero, jump
# set pins, 1    [1]   ; High for T1+T2
# jmp bitloop    [4]   ; Low for T3
# do_zero:
# set pins, 1    [1]   ; High for T1
# set pins, 0    [4]   ; Low for T2+T3
# .wrap
WS2812_PROGRAM: Array[uint16, 6] = [
    cast[uint16](0x6021),              # out x, 1
    cast[uint16](0x0023),              # jmp !x, 3
    cast[uint16](0xE001 | (1 << 8)),   # set pins, 1 [1]
    cast[uint16](0x0000 | (4 << 8)),   # jmp 0 [4]
    cast[uint16](0xE001 | (1 << 8)),   # set pins, 1 [1]
    cast[uint16](0xE000 | (4 << 8)),   # set pins, 0 [4]
]
WS2812_PROGRAM_LENGTH: uint32 = 6

# ============================================================================
# High-Level Helper Functions
# ============================================================================

def pio_blink_init(pio: uint32, sm: uint32, pin: uint32, freq_hz: uint32):
    """Initialize blink program on a state machine.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        pin: GPIO pin to blink
        freq_hz: Blink frequency in Hz
    """
    # Load program
    offset: int32 = pio_add_program(pio, cast[Ptr[uint16]](BLINK_PROGRAM), BLINK_PROGRAM_LENGTH)
    if offset < 0:
        return

    # Configure GPIO
    pio_gpio_init(pio, pin)

    # Initialize SM
    pio_sm_init(pio, sm, cast[uint32](offset))

    # Configure pins
    pio_sm_set_set_pins(pio, sm, pin, 1)
    pio_sm_set_pindirs(pio, sm, 1)

    # Set wrap addresses
    pio_sm_set_wrap(pio, sm, cast[uint32](offset), cast[uint32](offset + 1))

    # Calculate clock divider
    # Each loop is 64 cycles (2 instructions * 32 delay each)
    # freq = clk_sys / (div * 64)
    # div = clk_sys / (freq * 64)
    div: uint32 = 125000000 / (freq_hz * 64)
    if div < 1:
        div = 1
    pio_sm_set_clkdiv(pio, sm, div)

def pio_uart_tx_init(pio: uint32, sm: uint32, pin: uint32, baud: uint32):
    """Initialize UART TX program on a state machine.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        pin: GPIO pin for TX
        baud: Baud rate
    """
    # Load program
    offset: int32 = pio_add_program(pio, cast[Ptr[uint16]](UART_TX_PROGRAM), UART_TX_PROGRAM_LENGTH)
    if offset < 0:
        return

    # Configure GPIO
    pio_gpio_init(pio, pin)

    # Initialize SM
    pio_sm_init(pio, sm, cast[uint32](offset))

    # Configure pins
    pio_sm_set_out_pins(pio, sm, pin, 1)
    pio_sm_set_set_pins(pio, sm, pin, 1)
    pio_sm_set_pindirs(pio, sm, 1)
    pio_sm_set_pins(pio, sm, 1)  # Idle high

    # Configure shift
    pio_sm_set_out_shift(pio, sm, True, False, 32)

    # Set wrap addresses
    pio_sm_set_wrap(pio, sm, cast[uint32](offset), cast[uint32](offset + 5))

    # Calculate clock divider (8 cycles per bit)
    div: uint32 = 125000000 / (baud * 8)
    pio_sm_set_clkdiv(pio, sm, div)

def pio_ws2812_init(pio: uint32, sm: uint32, pin: uint32):
    """Initialize WS2812 LED driver on a state machine.

    Args:
        pio: PIO instance (0 or 1)
        sm: State machine (0-3)
        pin: GPIO pin for data
    """
    # Load program
    offset: int32 = pio_add_program(pio, cast[Ptr[uint16]](WS2812_PROGRAM), WS2812_PROGRAM_LENGTH)
    if offset < 0:
        return

    # Configure GPIO
    pio_gpio_init(pio, pin)

    # Initialize SM
    pio_sm_init(pio, sm, cast[uint32](offset))

    # Configure pins
    pio_sm_set_set_pins(pio, sm, pin, 1)
    pio_sm_set_pindirs(pio, sm, 1)

    # Configure shift (MSB first, autopull at 24 bits for RGB)
    pio_sm_set_out_shift(pio, sm, False, True, 24)

    # Set wrap addresses
    pio_sm_set_wrap(pio, sm, cast[uint32](offset), cast[uint32](offset + 5))

    # Clock divider for 10MHz (T1+T2+T3 = 10 cycles = 1.25us = 800kHz)
    div: uint32 = 125000000 / 10000000  # 12.5 -> 12
    pio_sm_set_clkdiv(pio, sm, div)
