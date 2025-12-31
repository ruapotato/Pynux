# Pynux Fault Handler Infrastructure
#
# ARM Cortex-M3 fault handling with detailed diagnostics.
# Provides handlers for HardFault, MemManage, BusFault, and UsageFault.

from lib.io import print_str, print_int, print_hex, print_newline, uart_putc

# ============================================================================
# ARM Cortex-M3 Fault Registers
# ============================================================================

# System Control Block (SCB) fault registers
SCB_SHCSR: uint32 = 0xE000ED24    # System Handler Control and State Register
SCB_CFSR: uint32 = 0xE000ED28    # Configurable Fault Status Register
SCB_HFSR: uint32 = 0xE000ED2C    # HardFault Status Register
SCB_DFSR: uint32 = 0xE000ED30    # Debug Fault Status Register
SCB_MMFAR: uint32 = 0xE000ED34   # MemManage Fault Address Register
SCB_BFAR: uint32 = 0xE000ED38    # BusFault Address Register
SCB_AFSR: uint32 = 0xE000ED3C    # Auxiliary Fault Status Register

# Application Interrupt and Reset Control Register
SCB_AIRCR: uint32 = 0xE000ED0C
AIRCR_VECTKEY: uint32 = 0x05FA0000
AIRCR_SYSRESETREQ: uint32 = 0x00000004

# ============================================================================
# SHCSR - System Handler Control and State Register bits
# ============================================================================

SHCSR_MEMFAULTACT: uint32 = 0x00000001    # MemManage active
SHCSR_BUSFAULTACT: uint32 = 0x00000002    # BusFault active
SHCSR_USGFAULTACT: uint32 = 0x00000008    # UsageFault active
SHCSR_SVCALLACT: uint32 = 0x00000080      # SVCall active
SHCSR_MONITORACT: uint32 = 0x00000100     # Debug monitor active
SHCSR_PENDSVACT: uint32 = 0x00000400      # PendSV active
SHCSR_SYSTICKACT: uint32 = 0x00000800     # SysTick active
SHCSR_USGFAULTPENDED: uint32 = 0x00001000 # UsageFault pended
SHCSR_MEMFAULTPENDED: uint32 = 0x00002000 # MemManage pended
SHCSR_BUSFAULTPENDED: uint32 = 0x00004000 # BusFault pended
SHCSR_SVCALLPENDED: uint32 = 0x00008000   # SVCall pended
SHCSR_MEMFAULTENA: uint32 = 0x00010000    # MemManage enable
SHCSR_BUSFAULTENA: uint32 = 0x00020000    # BusFault enable
SHCSR_USGFAULTENA: uint32 = 0x00040000    # UsageFault enable

# ============================================================================
# CFSR - Configurable Fault Status Register
# ============================================================================
# CFSR = UFSR[31:16] | BFSR[15:8] | MMFSR[7:0]

# MMFSR - MemManage Fault Status Register (bits 7:0 of CFSR)
MMFSR_IACCVIOL: uint32 = 0x00000001   # Instruction access violation
MMFSR_DACCVIOL: uint32 = 0x00000002   # Data access violation
MMFSR_MUNSTKERR: uint32 = 0x00000008  # MemManage on unstacking (exception return)
MMFSR_MSTKERR: uint32 = 0x00000010    # MemManage on stacking (exception entry)
MMFSR_MLSPERR: uint32 = 0x00000020    # MemManage during lazy FP state preservation
MMFSR_MMARVALID: uint32 = 0x00000080  # MMFAR holds valid address

# BFSR - BusFault Status Register (bits 15:8 of CFSR)
BFSR_IBUSERR: uint32 = 0x00000100     # Instruction bus error
BFSR_PRECISERR: uint32 = 0x00000200   # Precise data bus error
BFSR_IMPRECISERR: uint32 = 0x00000400 # Imprecise data bus error
BFSR_UNSTKERR: uint32 = 0x00000800    # BusFault on unstacking
BFSR_STKERR: uint32 = 0x00001000      # BusFault on stacking
BFSR_LSPERR: uint32 = 0x00002000      # BusFault during lazy FP state preservation
BFSR_BFARVALID: uint32 = 0x00008000   # BFAR holds valid address

# UFSR - UsageFault Status Register (bits 31:16 of CFSR)
UFSR_UNDEFINSTR: uint32 = 0x00010000  # Undefined instruction
UFSR_INVSTATE: uint32 = 0x00020000    # Invalid state (e.g., Thumb bit)
UFSR_INVPC: uint32 = 0x00040000       # Invalid PC load
UFSR_NOCP: uint32 = 0x00080000        # No coprocessor
UFSR_UNALIGNED: uint32 = 0x01000000   # Unaligned access
UFSR_DIVBYZERO: uint32 = 0x02000000   # Divide by zero

# ============================================================================
# HFSR - HardFault Status Register bits
# ============================================================================

HFSR_VECTTBL: uint32 = 0x00000002     # Vector table read fault
HFSR_FORCED: uint32 = 0x40000000      # Forced (escalated from configurable fault)
HFSR_DEBUGEVT: uint32 = 0x80000000    # Debug event

# ============================================================================
# Fault Types
# ============================================================================

FAULT_HARDFAULT: int32 = 0
FAULT_MEMMANAGE: int32 = 1
FAULT_BUSFAULT: int32 = 2
FAULT_USAGEFAULT: int32 = 3

# ============================================================================
# Exception Stack Frame Offsets
# ============================================================================
# When exception occurs, hardware pushes 8 registers:
#   [SP+0]  = R0
#   [SP+4]  = R1
#   [SP+8]  = R2
#   [SP+12] = R3
#   [SP+16] = R12
#   [SP+20] = LR (return address)
#   [SP+24] = PC (faulting instruction)
#   [SP+28] = xPSR

FRAME_R0: int32 = 0
FRAME_R1: int32 = 1
FRAME_R2: int32 = 2
FRAME_R3: int32 = 3
FRAME_R12: int32 = 4
FRAME_LR: int32 = 5
FRAME_PC: int32 = 6
FRAME_XPSR: int32 = 7

# ============================================================================
# Fault Handler State
# ============================================================================

# Last fault information
_fault_type: int32 = -1
_fault_pc: uint32 = 0
_fault_lr: uint32 = 0
_fault_cfsr: uint32 = 0
_fault_hfsr: uint32 = 0
_fault_mmfar: uint32 = 0
_fault_bfar: uint32 = 0

# Fault handlers initialized flag
_fault_initialized: bool = False

# ============================================================================
# Fault Enable Functions
# ============================================================================

def fault_enable_memmanage():
    """Enable MemManage fault handler.

    By default, MemManage faults escalate to HardFault.
    Enabling gives more detailed information about MPU violations.
    """
    shcsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_SHCSR)
    shcsr[0] = shcsr[0] | SHCSR_MEMFAULTENA
    dsb()

def fault_enable_busfault():
    """Enable BusFault handler.

    By default, BusFaults escalate to HardFault.
    Enabling gives more detailed information about bus errors.
    """
    shcsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_SHCSR)
    shcsr[0] = shcsr[0] | SHCSR_BUSFAULTENA
    dsb()

def fault_enable_usagefault():
    """Enable UsageFault handler.

    By default, UsageFaults escalate to HardFault.
    Enabling gives more detailed information about instruction errors.
    """
    shcsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_SHCSR)
    shcsr[0] = shcsr[0] | SHCSR_USGFAULTENA
    dsb()

def fault_enable_all():
    """Enable all configurable fault handlers."""
    shcsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_SHCSR)
    shcsr[0] = shcsr[0] | SHCSR_MEMFAULTENA | SHCSR_BUSFAULTENA | SHCSR_USGFAULTENA
    dsb()

def fault_init():
    """Initialize fault handling subsystem.

    Enables all configurable fault handlers for detailed diagnostics.
    """
    global _fault_initialized

    if _fault_initialized:
        return

    # Enable all fault handlers
    fault_enable_all()

    _fault_initialized = True

# ============================================================================
# Stack Frame Dump
# ============================================================================

def _dump_stack_frame(sp: uint32):
    """Dump exception stack frame registers.

    Args:
        sp: Stack pointer at time of exception (MSP or PSP)
    """
    global _fault_pc, _fault_lr

    if sp == 0:
        print_str("  Stack pointer invalid\n")
        return

    frame: Ptr[uint32] = cast[Ptr[uint32]](sp)

    # Save PC and LR for later use
    _fault_pc = frame[FRAME_PC]
    _fault_lr = frame[FRAME_LR]

    print_str("\n=== Exception Stack Frame ===\n")

    # Print R0-R3
    print_str("  R0:   0x")
    print_hex(frame[FRAME_R0])
    print_str("    R1:   0x")
    print_hex(frame[FRAME_R1])
    print_newline()

    print_str("  R2:   0x")
    print_hex(frame[FRAME_R2])
    print_str("    R3:   0x")
    print_hex(frame[FRAME_R3])
    print_newline()

    # Print R12, LR, PC, xPSR
    print_str("  R12:  0x")
    print_hex(frame[FRAME_R12])
    print_str("    LR:   0x")
    print_hex(frame[FRAME_LR])
    print_newline()

    print_str("  PC:   0x")
    print_hex(frame[FRAME_PC])
    print_str("    xPSR: 0x")
    print_hex(frame[FRAME_XPSR])
    print_newline()

    # Print stack pointer
    print_str("  SP:   0x")
    print_hex(sp)
    print_newline()

def _detect_stack_type(exc_return: uint32) -> bool:
    """Detect which stack was in use from EXC_RETURN value.

    Args:
        exc_return: The EXC_RETURN value in LR when exception occurred

    Returns:
        True if PSP (Process Stack), False if MSP (Main Stack)
    """
    # Bit 2 of EXC_RETURN: 0 = MSP, 1 = PSP
    return (exc_return & 0x04) != 0

def _print_stack_type(exc_return: uint32):
    """Print which stack was in use."""
    if _detect_stack_type(exc_return):
        print_str("  Stack: PSP (Process Stack)\n")
    else:
        print_str("  Stack: MSP (Main Stack)\n")

# ============================================================================
# Fault Status Register Parsing
# ============================================================================

def _read_fault_registers():
    """Read all fault status registers."""
    global _fault_cfsr, _fault_hfsr, _fault_mmfar, _fault_bfar

    cfsr_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_CFSR)
    hfsr_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_HFSR)
    mmfar_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_MMFAR)
    bfar_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_BFAR)

    _fault_cfsr = cfsr_ptr[0]
    _fault_hfsr = hfsr_ptr[0]
    _fault_mmfar = mmfar_ptr[0]
    _fault_bfar = bfar_ptr[0]

def _clear_fault_registers():
    """Clear fault status registers (write-1-to-clear)."""
    cfsr_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_CFSR)
    hfsr_ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_HFSR)

    # Write-1-to-clear the bits
    cfsr_ptr[0] = _fault_cfsr
    hfsr_ptr[0] = _fault_hfsr
    dsb()

def _print_cfsr_status():
    """Print human-readable CFSR (Configurable Fault Status Register) info."""
    cfsr: uint32 = _fault_cfsr

    print_str("\n=== Fault Status Registers ===\n")
    print_str("  CFSR: 0x")
    print_hex(cfsr)
    print_newline()

    # MMFSR (MemManage Fault Status - bits 7:0)
    if (cfsr & 0xFF) != 0:
        print_str("\n  MemManage Fault:\n")

        if (cfsr & MMFSR_IACCVIOL) != 0:
            print_str("    - Instruction access violation\n")
        if (cfsr & MMFSR_DACCVIOL) != 0:
            print_str("    - Data access violation\n")
        if (cfsr & MMFSR_MUNSTKERR) != 0:
            print_str("    - Fault on exception return (unstacking)\n")
        if (cfsr & MMFSR_MSTKERR) != 0:
            print_str("    - Fault on exception entry (stacking)\n")
        if (cfsr & MMFSR_MLSPERR) != 0:
            print_str("    - Fault during lazy FP save\n")
        if (cfsr & MMFSR_MMARVALID) != 0:
            print_str("    - Fault address: 0x")
            print_hex(_fault_mmfar)
            print_newline()

    # BFSR (BusFault Status - bits 15:8)
    if (cfsr & 0xFF00) != 0:
        print_str("\n  BusFault:\n")

        if (cfsr & BFSR_IBUSERR) != 0:
            print_str("    - Instruction bus error\n")
        if (cfsr & BFSR_PRECISERR) != 0:
            print_str("    - Precise data bus error\n")
        if (cfsr & BFSR_IMPRECISERR) != 0:
            print_str("    - Imprecise data bus error\n")
        if (cfsr & BFSR_UNSTKERR) != 0:
            print_str("    - Fault on exception return (unstacking)\n")
        if (cfsr & BFSR_STKERR) != 0:
            print_str("    - Fault on exception entry (stacking)\n")
        if (cfsr & BFSR_LSPERR) != 0:
            print_str("    - Fault during lazy FP save\n")
        if (cfsr & BFSR_BFARVALID) != 0:
            print_str("    - Fault address: 0x")
            print_hex(_fault_bfar)
            print_newline()

    # UFSR (UsageFault Status - bits 31:16)
    if (cfsr & 0xFFFF0000) != 0:
        print_str("\n  UsageFault:\n")

        if (cfsr & UFSR_UNDEFINSTR) != 0:
            print_str("    - Undefined instruction\n")
        if (cfsr & UFSR_INVSTATE) != 0:
            print_str("    - Invalid state (EPSR.T or EPSR.IT)\n")
        if (cfsr & UFSR_INVPC) != 0:
            print_str("    - Invalid PC load (illegal EXC_RETURN)\n")
        if (cfsr & UFSR_NOCP) != 0:
            print_str("    - No coprocessor (FPU/DSP disabled)\n")
        if (cfsr & UFSR_UNALIGNED) != 0:
            print_str("    - Unaligned memory access\n")
        if (cfsr & UFSR_DIVBYZERO) != 0:
            print_str("    - Divide by zero\n")

def _print_hfsr_status():
    """Print human-readable HFSR (HardFault Status Register) info."""
    hfsr: uint32 = _fault_hfsr

    print_str("  HFSR: 0x")
    print_hex(hfsr)
    print_newline()

    if hfsr != 0:
        print_str("\n  HardFault Status:\n")

        if (hfsr & HFSR_VECTTBL) != 0:
            print_str("    - Vector table read fault\n")
        if (hfsr & HFSR_FORCED) != 0:
            print_str("    - Forced (escalated from configurable fault)\n")
        if (hfsr & HFSR_DEBUGEVT) != 0:
            print_str("    - Debug event\n")

# ============================================================================
# Fault Handlers
# ============================================================================

def hardfault_handler(sp: uint32, exc_return: uint32):
    """HardFault exception handler.

    Called when a HardFault occurs. Can be escalated from other faults
    or occur directly (e.g., vector table error).

    Args:
        sp: Stack pointer at time of fault
        exc_return: EXC_RETURN value (for stack detection)
    """
    global _fault_type
    _fault_type = FAULT_HARDFAULT

    # Disable interrupts
    cpsid_i()

    print_str("\n")
    print_str("****************************************\n")
    print_str("***         HARD FAULT               ***\n")
    print_str("****************************************\n")

    # Read fault registers
    _read_fault_registers()

    # Print stack type
    _print_stack_type(exc_return)

    # Dump stack frame
    _dump_stack_frame(sp)

    # Print fault status
    _print_hfsr_status()
    _print_cfsr_status()

    # Print summary
    print_str("\n=== Fault Summary ===\n")
    print_str("  Faulting PC: 0x")
    print_hex(_fault_pc)
    print_newline()
    print_str("  Return LR:   0x")
    print_hex(_fault_lr)
    print_newline()

    # Check if escalated
    if (_fault_hfsr & HFSR_FORCED) != 0:
        print_str("  Cause: Escalated from configurable fault\n")

    # Clear fault registers
    _clear_fault_registers()

    # Halt
    fault_infinite_loop()

def memmanage_handler(sp: uint32, exc_return: uint32):
    """MemManage fault exception handler.

    Called when an MPU violation or memory access error occurs.

    Args:
        sp: Stack pointer at time of fault
        exc_return: EXC_RETURN value
    """
    global _fault_type
    _fault_type = FAULT_MEMMANAGE

    # Disable interrupts
    cpsid_i()

    print_str("\n")
    print_str("****************************************\n")
    print_str("***      MEMORY MANAGE FAULT         ***\n")
    print_str("****************************************\n")

    # Read fault registers
    _read_fault_registers()

    # Print stack type
    _print_stack_type(exc_return)

    # Dump stack frame
    _dump_stack_frame(sp)

    # Print fault status
    _print_cfsr_status()

    # Print summary
    print_str("\n=== Fault Summary ===\n")
    print_str("  Faulting PC: 0x")
    print_hex(_fault_pc)
    print_newline()

    if (_fault_cfsr & MMFSR_MMARVALID) != 0:
        print_str("  Fault Address: 0x")
        print_hex(_fault_mmfar)
        print_newline()

    # Clear fault registers
    _clear_fault_registers()

    # Halt
    fault_infinite_loop()

def busfault_handler(sp: uint32, exc_return: uint32):
    """BusFault exception handler.

    Called when an invalid memory access occurs (e.g., accessing
    non-existent peripheral, alignment error on bus).

    Args:
        sp: Stack pointer at time of fault
        exc_return: EXC_RETURN value
    """
    global _fault_type
    _fault_type = FAULT_BUSFAULT

    # Disable interrupts
    cpsid_i()

    print_str("\n")
    print_str("****************************************\n")
    print_str("***          BUS FAULT               ***\n")
    print_str("****************************************\n")

    # Read fault registers
    _read_fault_registers()

    # Print stack type
    _print_stack_type(exc_return)

    # Dump stack frame
    _dump_stack_frame(sp)

    # Print fault status
    _print_cfsr_status()

    # Print summary
    print_str("\n=== Fault Summary ===\n")
    print_str("  Faulting PC: 0x")
    print_hex(_fault_pc)
    print_newline()

    if (_fault_cfsr & BFSR_BFARVALID) != 0:
        print_str("  Fault Address: 0x")
        print_hex(_fault_bfar)
        print_newline()

    if (_fault_cfsr & BFSR_IMPRECISERR) != 0:
        print_str("  Note: Imprecise fault - PC may not be exact\n")

    # Clear fault registers
    _clear_fault_registers()

    # Halt
    fault_infinite_loop()

def usagefault_handler(sp: uint32, exc_return: uint32):
    """UsageFault exception handler.

    Called when an instruction execution error occurs (undefined
    instruction, invalid state, divide by zero, etc.).

    Args:
        sp: Stack pointer at time of fault
        exc_return: EXC_RETURN value
    """
    global _fault_type
    _fault_type = FAULT_USAGEFAULT

    # Disable interrupts
    cpsid_i()

    print_str("\n")
    print_str("****************************************\n")
    print_str("***        USAGE FAULT               ***\n")
    print_str("****************************************\n")

    # Read fault registers
    _read_fault_registers()

    # Print stack type
    _print_stack_type(exc_return)

    # Dump stack frame
    _dump_stack_frame(sp)

    # Print fault status
    _print_cfsr_status()

    # Print summary
    print_str("\n=== Fault Summary ===\n")
    print_str("  Faulting PC: 0x")
    print_hex(_fault_pc)
    print_newline()

    # Provide specific error messages
    if (_fault_cfsr & UFSR_UNDEFINSTR) != 0:
        print_str("  Cause: Undefined instruction at 0x")
        print_hex(_fault_pc)
        print_newline()
    elif (_fault_cfsr & UFSR_DIVBYZERO) != 0:
        print_str("  Cause: Division by zero\n")
    elif (_fault_cfsr & UFSR_UNALIGNED) != 0:
        print_str("  Cause: Unaligned memory access\n")
    elif (_fault_cfsr & UFSR_INVSTATE) != 0:
        print_str("  Cause: Invalid execution state (Thumb bit?)\n")
    elif (_fault_cfsr & UFSR_INVPC) != 0:
        print_str("  Cause: Invalid PC load on exception return\n")
    elif (_fault_cfsr & UFSR_NOCP) != 0:
        print_str("  Cause: Coprocessor instruction (FPU disabled?)\n")

    # Clear fault registers
    _clear_fault_registers()

    # Halt
    fault_infinite_loop()

# ============================================================================
# Recovery Options
# ============================================================================

def fault_reset():
    """Trigger a system reset.

    Performs a software system reset via AIRCR register.
    Use this to recover from a fault by restarting the system.
    """
    # Ensure all memory writes complete
    dsb()

    # Request system reset
    aircr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](SCB_AIRCR)
    aircr[0] = AIRCR_VECTKEY | AIRCR_SYSRESETREQ

    # Wait for reset
    dsb()
    while True:
        pass

def fault_infinite_loop():
    """Halt the system in an infinite loop.

    Use this for debugging - allows connecting a debugger
    to inspect the fault state.
    """
    print_str("\n*** System Halted ***\n")
    print_str("Connect debugger or press reset to continue.\n")

    # Ensure output is flushed
    dsb()

    while True:
        wfi()  # Low power wait

# ============================================================================
# Fault Query Functions
# ============================================================================

def fault_get_last_type() -> int32:
    """Get the type of the last fault.

    Returns:
        FAULT_HARDFAULT, FAULT_MEMMANAGE, FAULT_BUSFAULT,
        FAULT_USAGEFAULT, or -1 if no fault
    """
    return _fault_type

def fault_get_last_pc() -> uint32:
    """Get the PC (Program Counter) of the last fault.

    Returns:
        Address where fault occurred
    """
    return _fault_pc

def fault_get_last_cfsr() -> uint32:
    """Get the CFSR value from the last fault.

    Returns:
        Configurable Fault Status Register value
    """
    return _fault_cfsr

def fault_get_last_hfsr() -> uint32:
    """Get the HFSR value from the last fault.

    Returns:
        HardFault Status Register value
    """
    return _fault_hfsr

def fault_get_fault_address() -> uint32:
    """Get the faulting address (MMFAR or BFAR).

    Returns:
        The memory address that caused the fault, or 0 if not applicable
    """
    if (_fault_cfsr & MMFSR_MMARVALID) != 0:
        return _fault_mmfar
    if (_fault_cfsr & BFSR_BFARVALID) != 0:
        return _fault_bfar
    return 0

# ============================================================================
# Inline Assembly Stubs
# ============================================================================
# These are placeholders for inline assembly instructions.
# The actual implementation is in runtime/fault_handler.s

def cpsid_i():
    """Disable interrupts (CPSID I instruction)."""
    # Implemented in assembly
    pass

def cpsie_i():
    """Enable interrupts (CPSIE I instruction)."""
    # Implemented in assembly
    pass

def wfi():
    """Wait For Interrupt (WFI instruction)."""
    # Implemented in assembly
    pass

def dsb():
    """Data Synchronization Barrier."""
    # Implemented in assembly
    pass

def dmb():
    """Data Memory Barrier."""
    # Implemented in assembly
    pass

def isb():
    """Instruction Synchronization Barrier."""
    # Implemented in assembly
    pass
