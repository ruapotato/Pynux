# Pynux Software Breakpoints Library
#
# Software breakpoint management for bare-metal ARM Cortex-M3.
# Implements software breakpoints by patching code with BKPT instructions.

from lib.io import print_str, print_int, print_hex, print_newline

# ============================================================================
# Configuration
# ============================================================================

# Maximum number of software breakpoints
MAX_BREAKPOINTS: int32 = 16

# ARM Cortex-M3 BKPT instruction (Thumb-2)
# BKPT #imm8 = 0xBExx where xx is the immediate value
BKPT_INSTR: uint16 = 0xBE00

# ============================================================================
# Breakpoint Storage
# ============================================================================

# Breakpoint entry structure (stored in arrays):
# - address: Target address of breakpoint
# - original: Original instruction at address (16-bit for Thumb)
# - enabled: Whether breakpoint is currently active
# - id: Breakpoint ID

# Breakpoint address table
_bp_addr: Array[16, uint32]

# Original instruction storage (Thumb-2 uses 16-bit or 32-bit instructions)
# We store the first 16-bit halfword
_bp_original: Array[16, uint16]

# Breakpoint enabled flags
_bp_enabled: Array[16, bool]

# Breakpoint in-use flags
_bp_active: Array[16, bool]

# Breakpoint hit counts
_bp_hitcount: Array[16, int32]

# Breakpoint conditions (0 = unconditional)
_bp_condition: Array[16, int32]

# Total number of active breakpoints
_bp_count: int32 = 0

# Breakpoint subsystem initialized flag
_bp_initialized: bool = False

# ============================================================================
# ARM Cortex-M3 Debug Registers
# ============================================================================

# Flash Patch and Breakpoint (FPB) unit
FPB_CTRL: uint32 = 0xE0002000     # FPB Control Register
FPB_REMAP: uint32 = 0xE0002004    # FPB Remap Register
FPB_COMP0: uint32 = 0xE0002008    # FPB Comparator 0

# FPB Control register bits
FPB_CTRL_ENABLE: uint32 = 0x00000001
FPB_CTRL_KEY: uint32 = 0x00000002

# FPB Comparator register bits
FPB_COMP_ENABLE: uint32 = 0x00000001
FPB_COMP_REPLACE_BKPT: uint32 = 0xC0000000  # Replace with BKPT
FPB_COMP_REPLACE_UPPER: uint32 = 0x80000000  # Replace upper halfword
FPB_COMP_REPLACE_LOWER: uint32 = 0x40000000  # Replace lower halfword

# Number of hardware breakpoint comparators
NUM_HW_BREAKPOINTS: int32 = 6  # Cortex-M3 has 6 instruction comparators

# ============================================================================
# Initialization
# ============================================================================

def bp_init():
    """Initialize breakpoint subsystem.

    Clears all breakpoints and initializes the FPB unit.
    """
    global _bp_count, _bp_initialized

    if _bp_initialized:
        return

    # Clear all breakpoint entries
    i: int32 = 0
    while i < MAX_BREAKPOINTS:
        _bp_addr[i] = 0
        _bp_original[i] = 0
        _bp_enabled[i] = False
        _bp_active[i] = False
        _bp_hitcount[i] = 0
        _bp_condition[i] = 0
        i = i + 1

    _bp_count = 0

    # Initialize FPB (Flash Patch and Breakpoint) unit
    _init_fpb()

    _bp_initialized = True

def _init_fpb():
    """Initialize the Flash Patch and Breakpoint unit."""
    # Enable FPB
    fpb_ctrl: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](FPB_CTRL)
    fpb_ctrl[0] = FPB_CTRL_KEY | FPB_CTRL_ENABLE

    # Clear all comparators
    i: int32 = 0
    while i < NUM_HW_BREAKPOINTS:
        comp_addr: uint32 = FPB_COMP0 + (cast[uint32](i) * 4)
        comp: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](comp_addr)
        comp[0] = 0
        i = i + 1

# ============================================================================
# Breakpoint Management
# ============================================================================

def bp_set(addr: uint32) -> int32:
    """Set a software breakpoint at address.

    Saves the original instruction and patches with BKPT.

    Args:
        addr: Address to set breakpoint (must be 2-byte aligned for Thumb)

    Returns:
        Breakpoint ID (0 to MAX_BREAKPOINTS-1) on success, -1 on failure
    """
    global _bp_count

    if not _bp_initialized:
        bp_init()

    # Check alignment (Thumb requires 2-byte alignment)
    if (addr & 1) != 0:
        return -1

    # Check if breakpoint already exists at this address
    i: int32 = 0
    while i < MAX_BREAKPOINTS:
        if _bp_active[i] and _bp_addr[i] == addr:
            # Already have a breakpoint here
            if not _bp_enabled[i]:
                bp_enable(i)
            return i
        i = i + 1

    # Find free slot
    slot: int32 = -1
    i = 0
    while i < MAX_BREAKPOINTS:
        if not _bp_active[i]:
            slot = i
            break
        i = i + 1

    if slot < 0:
        return -1  # No free slots

    # Save original instruction
    instr_ptr: Ptr[uint16] = cast[Ptr[uint16]](addr)
    _bp_original[slot] = instr_ptr[0]

    # Store breakpoint info
    _bp_addr[slot] = addr
    _bp_active[slot] = True
    _bp_enabled[slot] = True
    _bp_hitcount[slot] = 0
    _bp_count = _bp_count + 1

    # Patch instruction with BKPT
    _patch_bkpt(addr, slot)

    return slot

def bp_clear(id: int32) -> bool:
    """Remove a breakpoint.

    Restores the original instruction.

    Args:
        id: Breakpoint ID to remove

    Returns:
        True on success, False on invalid ID
    """
    global _bp_count

    if id < 0 or id >= MAX_BREAKPOINTS:
        return False

    if not _bp_active[id]:
        return False

    # Restore original instruction
    if _bp_enabled[id]:
        _restore_instr(id)

    # Clear entry
    _bp_addr[id] = 0
    _bp_original[id] = 0
    _bp_active[id] = False
    _bp_enabled[id] = False
    _bp_hitcount[id] = 0
    _bp_condition[id] = 0
    _bp_count = _bp_count - 1

    return True

def bp_enable(id: int32) -> bool:
    """Enable a disabled breakpoint.

    Args:
        id: Breakpoint ID to enable

    Returns:
        True on success, False on invalid ID
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return False

    if not _bp_active[id]:
        return False

    if _bp_enabled[id]:
        return True  # Already enabled

    # Patch instruction
    _patch_bkpt(_bp_addr[id], id)
    _bp_enabled[id] = True

    return True

def bp_disable(id: int32) -> bool:
    """Disable a breakpoint without removing it.

    The breakpoint can be re-enabled later.

    Args:
        id: Breakpoint ID to disable

    Returns:
        True on success, False on invalid ID
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return False

    if not _bp_active[id]:
        return False

    if not _bp_enabled[id]:
        return True  # Already disabled

    # Restore original instruction
    _restore_instr(id)
    _bp_enabled[id] = False

    return True

def bp_list():
    """List all active breakpoints."""
    print_str("\nBreakpoints:\n")
    print_str("ID  Address     Enabled  Hits\n")
    print_str("--- ----------- -------- -----\n")

    found: bool = False
    i: int32 = 0

    while i < MAX_BREAKPOINTS:
        if _bp_active[i]:
            found = True

            # Print ID
            if i < 10:
                print_str(" ")
            print_int(i)
            print_str("  ")

            # Print address
            print_str("0x")
            print_hex(_bp_addr[i])
            print_str(" ")

            # Print enabled status
            if _bp_enabled[i]:
                print_str("yes      ")
            else:
                print_str("no       ")

            # Print hit count
            print_int(_bp_hitcount[i])
            print_newline()

        i = i + 1

    if not found:
        print_str("No breakpoints set.\n")

    print_newline()

# ============================================================================
# Breakpoint Query Functions
# ============================================================================

def bp_get_addr(id: int32) -> uint32:
    """Get address of breakpoint.

    Args:
        id: Breakpoint ID

    Returns:
        Breakpoint address, or 0 if invalid
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return 0

    if not _bp_active[id]:
        return 0

    return _bp_addr[id]

def bp_is_enabled(id: int32) -> bool:
    """Check if breakpoint is enabled.

    Args:
        id: Breakpoint ID

    Returns:
        True if enabled, False otherwise
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return False

    return _bp_active[id] and _bp_enabled[id]

def bp_is_active(id: int32) -> bool:
    """Check if breakpoint slot is in use.

    Args:
        id: Breakpoint ID

    Returns:
        True if slot is in use, False otherwise
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return False

    return _bp_active[id]

def bp_get_hitcount(id: int32) -> int32:
    """Get breakpoint hit count.

    Args:
        id: Breakpoint ID

    Returns:
        Number of times breakpoint was hit, or -1 if invalid
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return -1

    if not _bp_active[id]:
        return -1

    return _bp_hitcount[id]

def bp_reset_hitcount(id: int32):
    """Reset breakpoint hit count to zero.

    Args:
        id: Breakpoint ID
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return

    if _bp_active[id]:
        _bp_hitcount[id] = 0

def bp_count() -> int32:
    """Get number of active breakpoints.

    Returns:
        Number of active breakpoints
    """
    return _bp_count

def bp_find(addr: uint32) -> int32:
    """Find breakpoint by address.

    Args:
        addr: Address to search for

    Returns:
        Breakpoint ID if found, -1 if not found
    """
    i: int32 = 0
    while i < MAX_BREAKPOINTS:
        if _bp_active[i] and _bp_addr[i] == addr:
            return i
        i = i + 1

    return -1

# ============================================================================
# Breakpoint Hit Handling
# ============================================================================

def bp_hit(addr: uint32) -> int32:
    """Called when a breakpoint is hit.

    Updates hit count and returns breakpoint ID.

    Args:
        addr: Address where breakpoint was hit

    Returns:
        Breakpoint ID, or -1 if no breakpoint at address
    """
    id: int32 = bp_find(addr)

    if id >= 0:
        _bp_hitcount[id] = _bp_hitcount[id] + 1

    return id

def bp_step_over(id: int32) -> bool:
    """Prepare to step over a breakpoint.

    Temporarily disables the breakpoint so we can execute
    the original instruction, then re-enables it.

    Args:
        id: Breakpoint ID to step over

    Returns:
        True on success, False on invalid ID
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return False

    if not _bp_active[id] or not _bp_enabled[id]:
        return False

    # Temporarily restore original instruction
    _restore_instr(id)

    # Execute single instruction (caller must handle this)
    # After step, caller should call bp_step_over_complete()

    return True

def bp_step_over_complete(id: int32) -> bool:
    """Complete stepping over a breakpoint.

    Re-patches the BKPT instruction after stepping.

    Args:
        id: Breakpoint ID that was stepped over

    Returns:
        True on success, False on invalid ID
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return False

    if not _bp_active[id] or not _bp_enabled[id]:
        return False

    # Re-patch BKPT instruction
    _patch_bkpt(_bp_addr[id], id)

    return True

# ============================================================================
# Internal Functions
# ============================================================================

def _patch_bkpt(addr: uint32, id: int32):
    """Patch memory with BKPT instruction.

    Args:
        addr: Address to patch
        id: Breakpoint ID (used as BKPT immediate value)
    """
    # Create BKPT instruction with ID as immediate
    # BKPT #id = 0xBE00 | (id & 0xFF)
    bkpt: uint16 = BKPT_INSTR | cast[uint16](id & 0xFF)

    # Write to memory
    instr_ptr: Ptr[uint16] = cast[Ptr[uint16]](addr)

    # Disable interrupts for atomic write
    state: int32 = critical_enter()

    instr_ptr[0] = bkpt

    # Memory barrier and instruction cache flush
    dsb()
    isb()

    critical_exit(state)

def _restore_instr(id: int32):
    """Restore original instruction at breakpoint.

    Args:
        id: Breakpoint ID
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return

    if not _bp_active[id]:
        return

    addr: uint32 = _bp_addr[id]
    instr_ptr: Ptr[uint16] = cast[Ptr[uint16]](addr)

    # Disable interrupts for atomic write
    state: int32 = critical_enter()

    instr_ptr[0] = _bp_original[id]

    # Memory barrier and instruction cache flush
    dsb()
    isb()

    critical_exit(state)

# ============================================================================
# Hardware Breakpoint Support
# ============================================================================

# Hardware breakpoint tracking
_hwbp_addr: Array[6, uint32]
_hwbp_enabled: Array[6, bool]

def hwbp_init():
    """Initialize hardware breakpoints."""
    i: int32 = 0
    while i < NUM_HW_BREAKPOINTS:
        _hwbp_addr[i] = 0
        _hwbp_enabled[i] = False
        i = i + 1

def hwbp_set(addr: uint32) -> int32:
    """Set a hardware breakpoint.

    Uses the FPB unit for flash breakpoints.

    Args:
        addr: Address for breakpoint

    Returns:
        Hardware breakpoint ID (0-5) on success, -1 on failure
    """
    # Find free comparator
    slot: int32 = -1
    i: int32 = 0

    while i < NUM_HW_BREAKPOINTS:
        if not _hwbp_enabled[i]:
            slot = i
            break
        i = i + 1

    if slot < 0:
        return -1

    # Configure FPB comparator
    comp_addr: uint32 = FPB_COMP0 + (cast[uint32](slot) * 4)
    comp: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](comp_addr)

    # Set comparator value
    # Bit 0 = enable
    # Bits 28:2 = address bits 28:2
    # Bits 31:30 = replace mode (11 = BKPT both halfwords)
    comp_val: uint32 = (addr & 0x1FFFFFFC) | FPB_COMP_REPLACE_BKPT | FPB_COMP_ENABLE

    comp[0] = comp_val

    _hwbp_addr[slot] = addr
    _hwbp_enabled[slot] = True

    return slot

def hwbp_clear(id: int32) -> bool:
    """Clear a hardware breakpoint.

    Args:
        id: Hardware breakpoint ID

    Returns:
        True on success, False on failure
    """
    if id < 0 or id >= NUM_HW_BREAKPOINTS:
        return False

    if not _hwbp_enabled[id]:
        return False

    # Disable comparator
    comp_addr: uint32 = FPB_COMP0 + (cast[uint32](id) * 4)
    comp: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](comp_addr)
    comp[0] = 0

    _hwbp_addr[id] = 0
    _hwbp_enabled[id] = False

    return True

def hwbp_count() -> int32:
    """Get number of available hardware breakpoints.

    Returns:
        Number of FPB instruction comparators
    """
    return NUM_HW_BREAKPOINTS

# ============================================================================
# Utility Functions
# ============================================================================

def bp_clear_all():
    """Clear all breakpoints (software and hardware)."""
    # Clear software breakpoints
    i: int32 = 0
    while i < MAX_BREAKPOINTS:
        if _bp_active[i]:
            bp_clear(i)
        i = i + 1

    # Clear hardware breakpoints
    i = 0
    while i < NUM_HW_BREAKPOINTS:
        if _hwbp_enabled[i]:
            hwbp_clear(i)
        i = i + 1

def bp_disable_all():
    """Disable all breakpoints without removing them."""
    i: int32 = 0
    while i < MAX_BREAKPOINTS:
        if _bp_active[i] and _bp_enabled[i]:
            bp_disable(i)
        i = i + 1

def bp_enable_all():
    """Re-enable all disabled breakpoints."""
    i: int32 = 0
    while i < MAX_BREAKPOINTS:
        if _bp_active[i] and not _bp_enabled[i]:
            bp_enable(i)
        i = i + 1

def bp_get_original(id: int32) -> uint16:
    """Get the original instruction at a breakpoint.

    Args:
        id: Breakpoint ID

    Returns:
        Original 16-bit instruction, or 0 if invalid
    """
    if id < 0 or id >= MAX_BREAKPOINTS:
        return 0

    if not _bp_active[id]:
        return 0

    return _bp_original[id]
