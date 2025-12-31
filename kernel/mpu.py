# Pynux MPU Configuration
#
# ARM Cortex-M Memory Protection Unit (MPU) configuration.
# Provides memory protection for flash, RAM, peripherals, and stack guard.
#
# The MPU allows partitioning memory into regions with different
# access permissions and memory attributes.

from lib.io import print_str, print_int, print_newline

# ============================================================================
# MPU Register Addresses (at 0xE000ED90)
# ============================================================================

MPU_TYPE: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED90)
MPU_CTRL: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED94)
MPU_RNR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED98)   # Region Number Register
MPU_RBAR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED9C)  # Region Base Address Register
MPU_RASR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000EDA0)  # Region Attribute and Size Register

# Alias registers for configuring multiple regions efficiently
MPU_RBAR_A1: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000EDA4)
MPU_RASR_A1: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000EDA8)
MPU_RBAR_A2: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000EDAC)
MPU_RASR_A2: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000EDB0)
MPU_RBAR_A3: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000EDB4)
MPU_RASR_A3: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000EDB8)

# ============================================================================
# MPU Control Register Bits
# ============================================================================

MPU_CTRL_ENABLE: uint32 = 0x01      # Enable MPU
MPU_CTRL_HFNMIENA: uint32 = 0x02    # Enable MPU during hard fault, NMI, FAULTMASK
MPU_CTRL_PRIVDEFENA: uint32 = 0x04  # Enable default memory map for privileged access

# ============================================================================
# MPU Region Base Address Register Bits
# ============================================================================

MPU_RBAR_VALID: uint32 = 0x10       # Region number valid
MPU_RBAR_REGION_MASK: uint32 = 0x0F # Region number mask (bits 0-3)

# ============================================================================
# Access Permission Constants (AP field, bits 26:24 in RASR)
# ============================================================================

MPU_AP_NO_ACCESS: uint32 = 0        # No access (privileged or unprivileged)
MPU_AP_PRIV_RW: uint32 = 1          # Privileged read-write, unprivileged no access
MPU_AP_PRIV_RW_USER_RO: uint32 = 2  # Privileged read-write, unprivileged read-only
MPU_AP_FULL_ACCESS: uint32 = 3      # Full access (privileged and unprivileged)
MPU_AP_PRIV_RO: uint32 = 5          # Privileged read-only, unprivileged no access
MPU_AP_PRIV_RO_USER_RO: uint32 = 6  # Privileged and unprivileged read-only

# Execute Never flag (XN bit, bit 28 in RASR)
MPU_XN: uint32 = 1 << 28

# ============================================================================
# Memory Attribute Constants (TEX, C, B, S fields in RASR)
# ============================================================================
# TEX[2:0] = bits 21:19, S = bit 18, C = bit 17, B = bit 16

# Strongly-ordered: TEX=0b000, C=0, B=0 (no caching, no buffering)
MPU_ATTR_STRONGLY_ORDERED: uint32 = 0x00000000

# Device (shared): TEX=0b000, C=0, B=1 (for memory-mapped peripherals)
MPU_ATTR_DEVICE: uint32 = 0x00010000

# Normal, Write-through, no write allocate: TEX=0b000, C=1, B=0
MPU_ATTR_NORMAL_WT: uint32 = 0x00020000

# Normal, Write-back, no write allocate: TEX=0b000, C=1, B=1
MPU_ATTR_NORMAL_WB: uint32 = 0x00030000

# Normal, Non-cacheable: TEX=0b001, C=0, B=0
MPU_ATTR_NORMAL_NC: uint32 = 0x00080000

# Normal, Write-back, write and read allocate: TEX=0b001, C=1, B=1
MPU_ATTR_NORMAL_WB_WRA: uint32 = 0x000B0000

# Shareable bit (for multi-core systems)
MPU_ATTR_SHAREABLE: uint32 = 0x00040000

# ============================================================================
# Region Size Constants (SIZE field, bits 5:1 in RASR)
# ============================================================================
# Size = 2^(SIZE+1) bytes, minimum SIZE=4 (32 bytes)

MPU_SIZE_32B: uint32 = 4        # 32 bytes (minimum)
MPU_SIZE_64B: uint32 = 5
MPU_SIZE_128B: uint32 = 6
MPU_SIZE_256B: uint32 = 7
MPU_SIZE_512B: uint32 = 8
MPU_SIZE_1KB: uint32 = 9
MPU_SIZE_2KB: uint32 = 10
MPU_SIZE_4KB: uint32 = 11
MPU_SIZE_8KB: uint32 = 12
MPU_SIZE_16KB: uint32 = 13
MPU_SIZE_32KB: uint32 = 14
MPU_SIZE_64KB: uint32 = 15
MPU_SIZE_128KB: uint32 = 16
MPU_SIZE_256KB: uint32 = 17
MPU_SIZE_512KB: uint32 = 18
MPU_SIZE_1MB: uint32 = 19
MPU_SIZE_2MB: uint32 = 20
MPU_SIZE_4MB: uint32 = 21
MPU_SIZE_8MB: uint32 = 22
MPU_SIZE_16MB: uint32 = 23
MPU_SIZE_32MB: uint32 = 24
MPU_SIZE_64MB: uint32 = 25
MPU_SIZE_128MB: uint32 = 26
MPU_SIZE_256MB: uint32 = 27
MPU_SIZE_512MB: uint32 = 28
MPU_SIZE_1GB: uint32 = 29
MPU_SIZE_2GB: uint32 = 30
MPU_SIZE_4GB: uint32 = 31

# Region enable bit (bit 0 in RASR)
MPU_RASR_ENABLE: uint32 = 0x01

# ============================================================================
# Default Memory Layout (QEMU mps2-an385)
# ============================================================================

# Flash: 0x00000000 - 0x003FFFFF (4MB)
PYNUX_FLASH_BASE: uint32 = 0x00000000
PYNUX_FLASH_SIZE: uint32 = MPU_SIZE_4MB

# RAM: 0x20000000 - 0x2003FFFF (256KB)
PYNUX_RAM_BASE: uint32 = 0x20000000
PYNUX_RAM_SIZE: uint32 = MPU_SIZE_256KB

# Peripherals: 0x40000000 - 0x5FFFFFFF (512MB)
PYNUX_PERIPH_BASE: uint32 = 0x40000000
PYNUX_PERIPH_SIZE: uint32 = MPU_SIZE_512MB

# Stack guard: Last 32 bytes of stack area
PYNUX_STACK_GUARD_BASE: uint32 = 0x20000000
PYNUX_STACK_GUARD_SIZE: uint32 = MPU_SIZE_32B

# ============================================================================
# MPU State
# ============================================================================

mpu_initialized: bool = False
mpu_enabled: bool = False

# ============================================================================
# Core MPU Functions
# ============================================================================

def mpu_init():
    """Initialize the MPU.

    Disables MPU, clears all regions, and prepares for configuration.
    """
    global mpu_initialized, mpu_enabled

    state: int32 = critical_enter()

    # Disable MPU first
    MPU_CTRL[0] = 0
    dsb()
    isb()

    # Clear all regions (typically 8 regions available)
    num_regions: int32 = mpu_get_num_regions()
    i: int32 = 0
    while i < num_regions:
        MPU_RNR[0] = cast[uint32](i)
        MPU_RBAR[0] = 0
        MPU_RASR[0] = 0
        i = i + 1

    dsb()
    isb()

    mpu_initialized = True
    mpu_enabled = False

    critical_exit(state)

def mpu_enable():
    """Enable the MPU with default memory map for privileged access."""
    global mpu_enabled

    state: int32 = critical_enter()

    # Enable MPU with:
    # - PRIVDEFENA: Use default memory map for privileged access to
    #   regions not covered by MPU regions (prevents lockout)
    # - ENABLE: Turn on MPU
    MPU_CTRL[0] = MPU_CTRL_ENABLE | MPU_CTRL_PRIVDEFENA
    dsb()
    isb()

    mpu_enabled = True

    critical_exit(state)

def mpu_enable_strict():
    """Enable the MPU in strict mode (no default memory map).

    Warning: All memory access must be covered by MPU regions or
    will cause a fault.
    """
    global mpu_enabled

    state: int32 = critical_enter()

    MPU_CTRL[0] = MPU_CTRL_ENABLE
    dsb()
    isb()

    mpu_enabled = True

    critical_exit(state)

def mpu_enable_hfnmi():
    """Enable the MPU including during hard fault and NMI handlers."""
    global mpu_enabled

    state: int32 = critical_enter()

    MPU_CTRL[0] = MPU_CTRL_ENABLE | MPU_CTRL_PRIVDEFENA | MPU_CTRL_HFNMIENA
    dsb()
    isb()

    mpu_enabled = True

    critical_exit(state)

def mpu_disable():
    """Disable the MPU."""
    global mpu_enabled

    state: int32 = critical_enter()

    MPU_CTRL[0] = 0
    dsb()
    isb()

    mpu_enabled = False

    critical_exit(state)

def mpu_get_num_regions() -> int32:
    """Get the number of MPU regions available.

    Returns:
        Number of regions (typically 8 for Cortex-M3/M4)
    """
    type_val: uint32 = MPU_TYPE[0]
    # DREGION field is bits 15:8
    num_regions: int32 = cast[int32]((type_val >> 8) & 0xFF)
    return num_regions

def mpu_is_present() -> bool:
    """Check if MPU is present on this device.

    Returns:
        True if MPU is present, False otherwise
    """
    type_val: uint32 = MPU_TYPE[0]
    # DREGION field > 0 means MPU is present
    return ((type_val >> 8) & 0xFF) > 0

# ============================================================================
# Region Configuration Functions
# ============================================================================

def mpu_configure_region(region: int32, base: uint32, size: uint32, attrs: uint32):
    """Configure an MPU region.

    Args:
        region: Region number (0-7 typically)
        base: Base address (must be aligned to region size)
        size: Region size constant (MPU_SIZE_*)
        attrs: Combined attributes (memory type | access permissions)

    Note: Region is enabled after configuration.
    """
    state: int32 = critical_enter()

    # Select region
    MPU_RNR[0] = cast[uint32](region)
    dsb()

    # Configure base address (must be aligned to size)
    # Clear lower bits to ensure alignment
    size_bytes: uint32 = 1 << (size + 1)
    aligned_base: uint32 = base & ~(size_bytes - 1)
    MPU_RBAR[0] = aligned_base

    # Configure attributes and size
    # RASR format: [XN][AP(3)][reserved(2)][TEX(3)][S][C][B][SRD(8)][reserved(2)][SIZE(5)][ENABLE]
    rasr: uint32 = attrs | (size << 1) | MPU_RASR_ENABLE
    MPU_RASR[0] = rasr

    dsb()
    isb()

    critical_exit(state)

def mpu_configure_region_ex(region: int32, base: uint32, size: uint32,
                            ap: uint32, xn: bool, mem_attr: uint32, srd: uint32):
    """Configure an MPU region with explicit parameters.

    Args:
        region: Region number (0-7 typically)
        base: Base address (must be aligned to region size)
        size: Region size constant (MPU_SIZE_*)
        ap: Access permission (MPU_AP_*)
        xn: Execute never flag (True to prevent code execution)
        mem_attr: Memory attributes (MPU_ATTR_*)
        srd: Subregion disable mask (8 bits, one per subregion)
    """
    state: int32 = critical_enter()

    # Select region
    MPU_RNR[0] = cast[uint32](region)
    dsb()

    # Configure base address
    size_bytes: uint32 = 1 << (size + 1)
    aligned_base: uint32 = base & ~(size_bytes - 1)
    MPU_RBAR[0] = aligned_base

    # Build RASR value
    rasr: uint32 = mem_attr
    rasr = rasr | (ap << 24)           # AP field at bits 26:24
    if xn:
        rasr = rasr | MPU_XN           # XN bit at bit 28
    rasr = rasr | ((srd & 0xFF) << 8)  # SRD field at bits 15:8
    rasr = rasr | (size << 1)          # SIZE field at bits 5:1
    rasr = rasr | MPU_RASR_ENABLE      # Enable bit

    MPU_RASR[0] = rasr

    dsb()
    isb()

    critical_exit(state)

def mpu_enable_region(region: int32):
    """Enable an MPU region.

    Args:
        region: Region number to enable
    """
    state: int32 = critical_enter()

    MPU_RNR[0] = cast[uint32](region)
    dsb()

    rasr: uint32 = MPU_RASR[0]
    MPU_RASR[0] = rasr | MPU_RASR_ENABLE

    dsb()
    isb()

    critical_exit(state)

def mpu_disable_region(region: int32):
    """Disable an MPU region.

    Args:
        region: Region number to disable
    """
    state: int32 = critical_enter()

    MPU_RNR[0] = cast[uint32](region)
    dsb()

    rasr: uint32 = MPU_RASR[0]
    MPU_RASR[0] = rasr & ~MPU_RASR_ENABLE

    dsb()
    isb()

    critical_exit(state)

def mpu_set_region_access(region: int32, ap: uint32, xn: bool):
    """Set access permissions for an MPU region.

    Args:
        region: Region number
        ap: Access permission (MPU_AP_*)
        xn: Execute never flag
    """
    state: int32 = critical_enter()

    MPU_RNR[0] = cast[uint32](region)
    dsb()

    # Read current RASR
    rasr: uint32 = MPU_RASR[0]

    # Clear AP and XN fields
    rasr = rasr & ~(0x07 << 24)  # Clear AP (bits 26:24)
    rasr = rasr & ~MPU_XN         # Clear XN (bit 28)

    # Set new values
    rasr = rasr | (ap << 24)
    if xn:
        rasr = rasr | MPU_XN

    MPU_RASR[0] = rasr

    dsb()
    isb()

    critical_exit(state)

def mpu_set_subregion_disable(region: int32, srd_mask: uint32):
    """Set subregion disable mask for an MPU region.

    Each region can be divided into 8 equal subregions. Setting a bit
    in the mask disables that subregion.

    Args:
        region: Region number
        srd_mask: 8-bit mask (bit N=1 disables subregion N)
    """
    state: int32 = critical_enter()

    MPU_RNR[0] = cast[uint32](region)
    dsb()

    # Read current RASR
    rasr: uint32 = MPU_RASR[0]

    # Clear SRD field (bits 15:8)
    rasr = rasr & ~(0xFF << 8)

    # Set new SRD
    rasr = rasr | ((srd_mask & 0xFF) << 8)

    MPU_RASR[0] = rasr

    dsb()
    isb()

    critical_exit(state)

# ============================================================================
# Convenience Functions
# ============================================================================

def mpu_protect_flash(base: uint32, size: uint32):
    """Configure region 0 to protect flash memory.

    Flash is configured as:
    - Read-only for privileged and unprivileged access
    - Executable
    - Normal memory with write-through caching

    Args:
        base: Flash base address
        size: Size constant (MPU_SIZE_*)
    """
    attrs: uint32 = MPU_ATTR_NORMAL_WT | (MPU_AP_PRIV_RO_USER_RO << 24)
    mpu_configure_region(0, base, size, attrs)

def mpu_protect_ram(base: uint32, size: uint32):
    """Configure region 1 to protect RAM.

    RAM is configured as:
    - Read-write for privileged and unprivileged access
    - No execute (XN) to prevent code injection attacks
    - Normal memory with write-back caching

    Args:
        base: RAM base address
        size: Size constant (MPU_SIZE_*)
    """
    attrs: uint32 = MPU_ATTR_NORMAL_WB | (MPU_AP_FULL_ACCESS << 24) | MPU_XN
    mpu_configure_region(1, base, size, attrs)

def mpu_protect_peripherals():
    """Configure region 2 to protect peripheral memory region.

    Peripherals are configured as:
    - Read-write for privileged access only
    - No execute (XN)
    - Device memory (no caching, strict ordering)
    """
    attrs: uint32 = MPU_ATTR_DEVICE | (MPU_AP_PRIV_RW << 24) | MPU_XN
    mpu_configure_region(2, PYNUX_PERIPH_BASE, PYNUX_PERIPH_SIZE, attrs)

def mpu_protect_null():
    """Configure region 3 as a null pointer guard.

    Region starting at address 0 is configured as:
    - No access for any mode
    - Causes fault on any access (catches null pointer dereferences)

    Uses smallest region size (32 bytes) at address 0.
    """
    attrs: uint32 = MPU_AP_NO_ACCESS << 24
    mpu_configure_region(3, 0x00000000, MPU_SIZE_32B, attrs)

def mpu_protect_stack_guard(stack_bottom: uint32):
    """Configure a stack guard region for stack overflow detection.

    Creates a 32-byte no-access region at the bottom of the stack.
    Any access to this region indicates stack overflow.

    Args:
        stack_bottom: Address at the bottom of the stack
    """
    attrs: uint32 = (MPU_AP_NO_ACCESS << 24) | MPU_XN
    mpu_configure_region(4, stack_bottom, MPU_SIZE_32B, attrs)

# ============================================================================
# Pynux Standard Configuration
# ============================================================================

def mpu_setup_pynux():
    """Set up MPU with standard Pynux memory layout.

    Region configuration:
    - Region 0: Flash (RO, executable) at 0x00000000
    - Region 1: RAM (RW, no-execute) at 0x20000000
    - Region 2: Peripherals (device memory) at 0x40000000
    - Region 3: Null guard (no access) at 0x00000000

    Note: Flash region overlaps null guard, but null guard has higher
    priority (higher region number) and takes precedence for address 0.
    """
    # Initialize MPU
    mpu_init()

    # Check if MPU is present
    if not mpu_is_present():
        print_str("[mpu] MPU not present\n")
        return

    print_str("[mpu] Configuring memory protection...\n")

    # Region 0: Flash (read-only, executable)
    mpu_protect_flash(PYNUX_FLASH_BASE, PYNUX_FLASH_SIZE)

    # Region 1: RAM (read-write, no execute)
    mpu_protect_ram(PYNUX_RAM_BASE, PYNUX_RAM_SIZE)

    # Region 2: Peripherals (device memory, privileged only)
    mpu_protect_peripherals()

    # Region 3: Null guard (catch null pointer access)
    # This region has higher priority than flash region 0
    mpu_protect_null()

    # Enable MPU with default background region for privileged access
    mpu_enable()

    print_str("[mpu] Memory protection enabled\n")

def mpu_setup_pynux_with_stack_guard(stack_bottom: uint32):
    """Set up MPU with standard layout plus stack overflow protection.

    Same as mpu_setup_pynux() but adds a stack guard region.

    Args:
        stack_bottom: Address at the bottom of the stack area
    """
    mpu_setup_pynux()

    # Add stack guard (Region 4)
    mpu_protect_stack_guard(stack_bottom)

    print_str("[mpu] Stack guard enabled at 0x")
    print_hex(stack_bottom)
    print_str("\n")

# ============================================================================
# Debug Functions
# ============================================================================

def mpu_dump_regions():
    """Dump all MPU region configurations for debugging."""
    print_str("[mpu] Region configuration:\n")

    num_regions: int32 = mpu_get_num_regions()
    print_str("  Available regions: ")
    print_int(num_regions)
    print_str("\n")

    ctrl: uint32 = MPU_CTRL[0]
    print_str("  MPU enabled: ")
    if (ctrl & MPU_CTRL_ENABLE) != 0:
        print_str("yes\n")
    else:
        print_str("no\n")

    i: int32 = 0
    while i < num_regions:
        MPU_RNR[0] = cast[uint32](i)
        dsb()

        rbar: uint32 = MPU_RBAR[0]
        rasr: uint32 = MPU_RASR[0]

        # Only show enabled regions
        if (rasr & MPU_RASR_ENABLE) != 0:
            print_str("  Region ")
            print_int(i)
            print_str(": base=0x")
            print_hex(rbar & 0xFFFFFFE0)

            size_field: uint32 = (rasr >> 1) & 0x1F
            size_bytes: uint32 = 1 << (size_field + 1)
            print_str(" size=")
            if size_bytes >= 0x100000:
                print_int(cast[int32](size_bytes >> 20))
                print_str("MB")
            elif size_bytes >= 0x400:
                print_int(cast[int32](size_bytes >> 10))
                print_str("KB")
            else:
                print_int(cast[int32](size_bytes))
                print_str("B")

            ap: uint32 = (rasr >> 24) & 0x07
            print_str(" AP=")
            print_int(cast[int32](ap))

            if (rasr & MPU_XN) != 0:
                print_str(" XN")

            print_str("\n")

        i = i + 1

def print_hex(val: uint32):
    """Print a 32-bit value in hexadecimal."""
    digits: Array[8, char]
    hex_chars: Ptr[char] = "0123456789ABCDEF"

    i: int32 = 0
    while i < 8:
        nibble: uint32 = (val >> (28 - i * 4)) & 0x0F
        digits[i] = hex_chars[nibble]
        i = i + 1

    i = 0
    while i < 8:
        # Print char (simplified - would use uart_putc in real implementation)
        print_char(digits[i])
        i = i + 1

def print_char(c: char):
    """Print a single character."""
    # Use UART directly for single char output
    uart_base: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0x40004000)
    uart_base[0] = cast[uint32](c)

# ============================================================================
# Fault Handler Support
# ============================================================================

def mpu_get_fault_address() -> uint32:
    """Get the address that caused an MPU fault.

    Returns:
        Faulting address from MMFAR (Memory Manage Fault Address Register)
    """
    mmfar: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED34)
    return mmfar[0]

def mpu_get_fault_status() -> uint32:
    """Get MPU fault status.

    Returns:
        MMFSR (Memory Manage Fault Status Register) value
    """
    # MMFSR is byte 0 of CFSR at 0xE000ED28
    cfsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED28)
    return cfsr[0] & 0xFF

def mpu_clear_fault_status():
    """Clear MPU fault status flags."""
    cfsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED28)
    # Write 1 to clear fault bits
    cfsr[0] = cfsr[0] & 0xFF

# MMFSR bit definitions
MMFSR_IACCVIOL: uint32 = 0x01   # Instruction access violation
MMFSR_DACCVIOL: uint32 = 0x02   # Data access violation
MMFSR_MUNSTKERR: uint32 = 0x08  # Unstacking error
MMFSR_MSTKERR: uint32 = 0x10    # Stacking error
MMFSR_MLSPERR: uint32 = 0x20    # Floating-point lazy state preservation error
MMFSR_MMARVALID: uint32 = 0x80  # MMFAR has valid address

def mpu_handle_fault():
    """Handle an MPU fault (called from MemManage_Handler).

    Prints fault information for debugging.
    """
    status: uint32 = mpu_get_fault_status()

    print_str("\n*** MPU FAULT ***\n")

    if (status & MMFSR_IACCVIOL) != 0:
        print_str("Instruction access violation\n")

    if (status & MMFSR_DACCVIOL) != 0:
        print_str("Data access violation\n")

    if (status & MMFSR_MUNSTKERR) != 0:
        print_str("Unstacking error\n")

    if (status & MMFSR_MSTKERR) != 0:
        print_str("Stacking error\n")

    if (status & MMFSR_MMARVALID) != 0:
        addr: uint32 = mpu_get_fault_address()
        print_str("Fault address: 0x")
        print_hex(addr)
        print_str("\n")

    # Clear fault status
    mpu_clear_fault_status()
