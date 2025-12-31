# Pynux Debug Infrastructure
#
# Debug utilities for bare-metal ARM Cortex-M3.
# Provides debug output, assertions, memory dumps, and backtracing.

from lib.io import print_str, print_int, print_hex, print_newline, uart_putc

# ============================================================================
# Debug Configuration
# ============================================================================

# Debug output enable flag (set to False to disable all debug output)
DEBUG_ENABLED: volatile bool = True

# Debug level: 0=off, 1=errors, 2=warnings, 3=info, 4=verbose
DEBUG_LEVEL: int32 = 3

# Debug level constants
DEBUG_LEVEL_OFF: int32 = 0
DEBUG_LEVEL_ERROR: int32 = 1
DEBUG_LEVEL_WARN: int32 = 2
DEBUG_LEVEL_INFO: int32 = 3
DEBUG_LEVEL_VERBOSE: int32 = 4

# ============================================================================
# ARM Cortex-M3 Register Definitions
# ============================================================================

# Core registers (R0-R15)
REG_R0: int32 = 0
REG_R1: int32 = 1
REG_R2: int32 = 2
REG_R3: int32 = 3
REG_R4: int32 = 4
REG_R5: int32 = 5
REG_R6: int32 = 6
REG_R7: int32 = 7
REG_R8: int32 = 8
REG_R9: int32 = 9
REG_R10: int32 = 10
REG_R11: int32 = 11
REG_R12: int32 = 12
REG_SP: int32 = 13   # Stack pointer
REG_LR: int32 = 14   # Link register
REG_PC: int32 = 15   # Program counter

# Special registers
REG_PSR: int32 = 16      # Program status register
REG_MSP: int32 = 17      # Main stack pointer
REG_PSP: int32 = 18      # Process stack pointer
REG_PRIMASK: int32 = 19  # Priority mask
REG_BASEPRI: int32 = 20  # Base priority
REG_FAULTMASK: int32 = 21  # Fault mask
REG_CONTROL: int32 = 22  # Control register

# Number of core registers for GDB protocol
NUM_CORE_REGS: int32 = 17  # R0-R12, SP, LR, PC, xPSR

# System Control Block (SCB) addresses
SCB_BASE: uint32 = 0xE000ED00
SCB_CPUID: uint32 = 0xE000ED00
SCB_ICSR: uint32 = 0xE000ED04
SCB_VTOR: uint32 = 0xE000ED08
SCB_AIRCR: uint32 = 0xE000ED0C
SCB_SCR: uint32 = 0xE000ED10
SCB_CCR: uint32 = 0xE000ED14
SCB_SHPR1: uint32 = 0xE000ED18
SCB_SHPR2: uint32 = 0xE000ED1C
SCB_SHPR3: uint32 = 0xE000ED20
SCB_SHCSR: uint32 = 0xE000ED24
SCB_CFSR: uint32 = 0xE000ED28
SCB_HFSR: uint32 = 0xE000ED2C
SCB_DFSR: uint32 = 0xE000ED30
SCB_MMFAR: uint32 = 0xE000ED34
SCB_BFAR: uint32 = 0xE000ED38
SCB_AFSR: uint32 = 0xE000ED3C

# Debug Control Block (DCB) addresses
DCB_DHCSR: uint32 = 0xE000EDF0  # Debug Halting Control and Status Register
DCB_DCRSR: uint32 = 0xE000EDF4  # Debug Core Register Selector Register
DCB_DCRDR: uint32 = 0xE000EDF8  # Debug Core Register Data Register
DCB_DEMCR: uint32 = 0xE000EDFC  # Debug Exception and Monitor Control Register

# DHCSR bits
DHCSR_C_DEBUGEN: uint32 = 0x00000001
DHCSR_C_HALT: uint32 = 0x00000002
DHCSR_C_STEP: uint32 = 0x00000004
DHCSR_C_MASKINTS: uint32 = 0x00000008
DHCSR_S_REGRDY: uint32 = 0x00010000
DHCSR_S_HALT: uint32 = 0x00020000
DHCSR_S_SLEEP: uint32 = 0x00040000
DHCSR_S_LOCKUP: uint32 = 0x00080000
DHCSR_DBGKEY: uint32 = 0xA05F0000

# DEMCR bits
DEMCR_TRCENA: uint32 = 0x01000000
DEMCR_MON_EN: uint32 = 0x00010000
DEMCR_MON_PEND: uint32 = 0x00020000
DEMCR_MON_STEP: uint32 = 0x00040000
DEMCR_MON_REQ: uint32 = 0x00080000
DEMCR_VC_HARDERR: uint32 = 0x00000400
DEMCR_VC_INTERR: uint32 = 0x00000200
DEMCR_VC_BUSERR: uint32 = 0x00000100
DEMCR_VC_STATERR: uint32 = 0x00000080
DEMCR_VC_CHKERR: uint32 = 0x00000040
DEMCR_VC_NOCPERR: uint32 = 0x00000020
DEMCR_VC_MMERR: uint32 = 0x00000010
DEMCR_VC_CORERESET: uint32 = 0x00000001

# ============================================================================
# Debug State
# ============================================================================

# Debug subsystem initialized flag
_debug_initialized: bool = False

# Saved register context (for backtrace and debugging)
_saved_regs: Array[17, uint32]

# Breakpoint hit flag
_breakpoint_hit: volatile bool = False

# ============================================================================
# Debug Initialization
# ============================================================================

def debug_init():
    """Initialize debug subsystem.

    Sets up debug registers and enables debug monitor mode.
    """
    global _debug_initialized

    if _debug_initialized:
        return

    # Enable trace (required for DWT and ITM)
    demcr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](DCB_DEMCR)
    demcr[0] = demcr[0] | DEMCR_TRCENA

    # Enable debug monitor exception
    demcr[0] = demcr[0] | DEMCR_MON_EN

    # Initialize saved registers to zero
    i: int32 = 0
    while i < 17:
        _saved_regs[i] = 0
        i = i + 1

    _debug_initialized = True

    if DEBUG_ENABLED:
        print_str("[debug] Debug subsystem initialized\n")

# ============================================================================
# Debug Break / Halt
# ============================================================================

def debug_break():
    """Trigger a software breakpoint.

    On Cortex-M3, this triggers the debug monitor exception or
    halts the CPU if a debugger is attached.
    """
    global _breakpoint_hit

    _breakpoint_hit = True

    if DEBUG_ENABLED:
        print_str("[debug] Breakpoint triggered\n")

    # Save current context
    _save_context()

    # Execute BKPT instruction (software breakpoint)
    # BKPT #0 = 0xBE00
    bkpt()

def bkpt():
    """Execute ARM BKPT instruction (inline assembly placeholder)."""
    # In real implementation, this would be:
    # asm volatile ("bkpt #0")
    # For now, we simulate by reading debug registers
    dhcsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](DCB_DHCSR)
    # Write debug key with halt request
    dhcsr[0] = DHCSR_DBGKEY | DHCSR_C_DEBUGEN | DHCSR_C_HALT

# ============================================================================
# Debug Assert
# ============================================================================

def debug_assert(condition: bool, msg: Ptr[char]):
    """Assert with message.

    If condition is false, prints the assertion message and triggers
    a breakpoint. Useful for catching programming errors during development.

    Args:
        condition: Condition that should be true
        msg: Message to display if assertion fails
    """
    if not condition:
        print_str("\n*** ASSERTION FAILED ***\n")
        print_str(msg)
        print_newline()

        # Print call location (if available from saved context)
        if _saved_regs[REG_PC] != 0:
            print_str("PC: 0x")
            print_hex(_saved_regs[REG_PC])
            print_newline()

        # Trigger breakpoint
        debug_break()

def debug_assert_eq(a: int32, b: int32, msg: Ptr[char]):
    """Assert two integers are equal."""
    if a != b:
        print_str("\n*** ASSERTION FAILED ***\n")
        print_str(msg)
        print_str("\nExpected: ")
        print_int(a)
        print_str(", Got: ")
        print_int(b)
        print_newline()
        debug_break()

def debug_assert_ne(a: int32, b: int32, msg: Ptr[char]):
    """Assert two integers are not equal."""
    if a == b:
        print_str("\n*** ASSERTION FAILED ***\n")
        print_str(msg)
        print_str("\nBoth values: ")
        print_int(a)
        print_newline()
        debug_break()

def debug_assert_ptr(ptr: Ptr[uint8], msg: Ptr[char]):
    """Assert pointer is not null."""
    if cast[uint32](ptr) == 0:
        print_str("\n*** ASSERTION FAILED (NULL PTR) ***\n")
        print_str(msg)
        print_newline()
        debug_break()

# ============================================================================
# Debug Print
# ============================================================================

def debug_print(msg: Ptr[char]):
    """Debug output (can be disabled via DEBUG_ENABLED).

    Args:
        msg: Message to print
    """
    if DEBUG_ENABLED:
        print_str("[debug] ")
        print_str(msg)
        print_newline()

def debug_print_level(level: int32, msg: Ptr[char]):
    """Debug output with level filtering.

    Args:
        level: Debug level (1=error, 2=warn, 3=info, 4=verbose)
        msg: Message to print
    """
    if not DEBUG_ENABLED:
        return
    if level > DEBUG_LEVEL:
        return

    if level == DEBUG_LEVEL_ERROR:
        print_str("[ERROR] ")
    elif level == DEBUG_LEVEL_WARN:
        print_str("[WARN]  ")
    elif level == DEBUG_LEVEL_INFO:
        print_str("[INFO]  ")
    elif level == DEBUG_LEVEL_VERBOSE:
        print_str("[VERB]  ")

    print_str(msg)
    print_newline()

def debug_print_val(msg: Ptr[char], val: int32):
    """Debug print with integer value.

    Args:
        msg: Message prefix
        val: Integer value to print
    """
    if DEBUG_ENABLED:
        print_str("[debug] ")
        print_str(msg)
        print_int(val)
        print_newline()

def debug_print_hex_val(msg: Ptr[char], val: uint32):
    """Debug print with hex value.

    Args:
        msg: Message prefix
        val: Value to print in hex
    """
    if DEBUG_ENABLED:
        print_str("[debug] ")
        print_str(msg)
        print_str("0x")
        print_hex(val)
        print_newline()

def debug_set_enabled(enabled: bool):
    """Enable or disable debug output.

    Args:
        enabled: True to enable, False to disable
    """
    global DEBUG_ENABLED
    DEBUG_ENABLED = enabled

def debug_set_level(level: int32):
    """Set debug output level.

    Args:
        level: Debug level (0-4)
    """
    global DEBUG_LEVEL
    if level >= 0 and level <= 4:
        DEBUG_LEVEL = level

# ============================================================================
# Hex Dump
# ============================================================================

def debug_hexdump(addr: uint32, length: int32):
    """Hex dump memory region.

    Displays memory contents in hex format with ASCII representation.
    Format: ADDR: XX XX XX XX ... | ASCII |

    Args:
        addr: Start address to dump
        length: Number of bytes to dump
    """
    if not DEBUG_ENABLED:
        return

    if length <= 0:
        return

    ptr: Ptr[uint8] = cast[Ptr[uint8]](addr)
    offset: int32 = 0

    print_str("[debug] Memory dump at 0x")
    print_hex(addr)
    print_str(", ")
    print_int(length)
    print_str(" bytes:\n")

    while offset < length:
        # Print address
        print_hex(addr + cast[uint32](offset))
        print_str(": ")

        # Calculate bytes for this line
        line_bytes: int32 = 16
        if offset + 16 > length:
            line_bytes = length - offset

        # Print hex values
        i: int32 = 0
        while i < 16:
            if i < line_bytes:
                _print_hex_byte(ptr[offset + i])
                uart_putc(' ')
            else:
                print_str("   ")

            # Extra space in middle
            if i == 7:
                uart_putc(' ')

            i = i + 1

        # Print ASCII representation
        print_str(" |")
        i = 0
        while i < line_bytes:
            c: char = cast[char](ptr[offset + i])
            if c >= ' ' and c <= '~':
                uart_putc(c)
            else:
                uart_putc('.')
            i = i + 1

        # Pad ASCII if short line
        while i < 16:
            uart_putc(' ')
            i = i + 1

        print_str("|\n")
        offset = offset + 16

    print_newline()

def _print_hex_byte(val: uint8):
    """Print a single byte as two hex digits."""
    hex_chars: Ptr[char] = "0123456789ABCDEF"
    uart_putc(hex_chars[cast[int32](val) >> 4])
    uart_putc(hex_chars[cast[int32](val) & 0x0F])

def debug_hexdump_line(addr: uint32, length: int32):
    """Single-line hex dump (no ASCII).

    Args:
        addr: Start address
        length: Number of bytes (max 32)
    """
    if not DEBUG_ENABLED:
        return

    if length > 32:
        length = 32

    ptr: Ptr[uint8] = cast[Ptr[uint8]](addr)
    print_str("0x")
    print_hex(addr)
    print_str(": ")

    i: int32 = 0
    while i < length:
        _print_hex_byte(ptr[i])
        uart_putc(' ')
        i = i + 1

    print_newline()

# ============================================================================
# Backtrace
# ============================================================================

# Stack frame structure for Cortex-M3
# Exception stack frame layout (8 words):
#   [SP+0]  = R0
#   [SP+4]  = R1
#   [SP+8]  = R2
#   [SP+12] = R3
#   [SP+16] = R12
#   [SP+20] = LR (return address)
#   [SP+24] = PC (exception address)
#   [SP+28] = xPSR

# Maximum stack frames to trace
MAX_BACKTRACE_DEPTH: int32 = 16

def debug_backtrace():
    """Print call stack backtrace.

    Walks the stack and prints return addresses.
    Note: This requires frame pointers (R11/FP) to be preserved.
    """
    if not DEBUG_ENABLED:
        return

    print_str("\n[debug] Backtrace:\n")

    # Get current stack pointer
    sp: uint32 = _get_sp()

    # Get frame pointer (R11 on ARM)
    fp: uint32 = _saved_regs[REG_R11]
    if fp == 0:
        fp = _get_fp()

    # Get current PC
    pc: uint32 = _saved_regs[REG_PC]
    if pc == 0:
        pc = _get_lr()

    print_str("  #0  0x")
    print_hex(pc)
    print_str(" (current)\n")

    # Walk the frame chain
    depth: int32 = 1
    while depth < MAX_BACKTRACE_DEPTH and fp != 0:
        # Validate frame pointer
        if not _is_valid_stack_addr(fp):
            break

        # Read saved LR from stack frame
        # On Cortex-M3, the frame looks like:
        #   [FP-4] = saved LR
        #   [FP]   = saved FP (previous frame)
        fp_ptr: Ptr[uint32] = cast[Ptr[uint32]](fp)

        # Get return address (LR from caller's frame)
        lr: uint32 = 0
        if _is_valid_stack_addr(fp - 4):
            lr_ptr: Ptr[uint32] = cast[Ptr[uint32]](fp - 4)
            lr = lr_ptr[0]

        if lr == 0:
            break

        print_str("  #")
        print_int(depth)
        print_str("  0x")
        print_hex(lr)
        print_newline()

        # Move to previous frame
        prev_fp: uint32 = fp_ptr[0]

        # Detect end of chain
        if prev_fp == 0 or prev_fp == fp:
            break

        fp = prev_fp
        depth = depth + 1

    if depth >= MAX_BACKTRACE_DEPTH:
        print_str("  ... (truncated)\n")

    print_newline()

def debug_print_regs():
    """Print all saved registers."""
    if not DEBUG_ENABLED:
        return

    print_str("\n[debug] Registers:\n")

    # Print R0-R7
    i: int32 = 0
    while i < 8:
        print_str("  R")
        print_int(i)
        print_str(": 0x")
        print_hex(_saved_regs[i])

        if (i & 1) == 1:
            print_newline()
        else:
            print_str("    ")

        i = i + 1

    # Print R8-R12
    while i < 13:
        print_str("  R")
        print_int(i)
        print_str(": 0x")
        print_hex(_saved_regs[i])

        if i == 9 or i == 11:
            print_newline()
        else:
            print_str("   ")

        i = i + 1

    print_newline()

    # Print special registers
    print_str("  SP:  0x")
    print_hex(_saved_regs[REG_SP])
    print_str("    LR:  0x")
    print_hex(_saved_regs[REG_LR])
    print_newline()

    print_str("  PC:  0x")
    print_hex(_saved_regs[REG_PC])
    print_str("    PSR: 0x")
    print_hex(_saved_regs[REG_PSR])
    print_newline()
    print_newline()

# ============================================================================
# Internal Helpers
# ============================================================================

def _save_context():
    """Save current register context (inline assembly placeholder)."""
    # In real implementation, this would save all registers
    # For now, we try to read what we can from debug registers
    global _saved_regs

    # Read PC from link register approximation
    _saved_regs[REG_LR] = _get_lr()
    _saved_regs[REG_SP] = _get_sp()
    _saved_regs[REG_PC] = _saved_regs[REG_LR]

def _get_sp() -> uint32:
    """Get current stack pointer (inline assembly placeholder)."""
    # In real implementation: asm volatile ("mov %0, sp" : "=r" (sp))
    # Return a simulated stack pointer in RAM range
    return 0x20008000

def _get_lr() -> uint32:
    """Get current link register (inline assembly placeholder)."""
    # In real implementation: asm volatile ("mov %0, lr" : "=r" (lr))
    return 0x00000000

def _get_fp() -> uint32:
    """Get current frame pointer (R11)."""
    # In real implementation: asm volatile ("mov %0, r11" : "=r" (fp))
    return 0x00000000

def _is_valid_stack_addr(addr: uint32) -> bool:
    """Check if address is in valid stack range."""
    # Stack is typically in RAM (0x20000000 - 0x20010000 for mps2-an385)
    if addr >= 0x20000000 and addr < 0x20020000:
        return True
    return False

def _is_valid_code_addr(addr: uint32) -> bool:
    """Check if address is in valid code range."""
    # Code is typically in flash (0x00000000 - 0x00400000)
    if addr < 0x00400000:
        return True
    return False

# ============================================================================
# Fault Handler Support
# ============================================================================

def debug_fault_handler(fault_type: int32, sp: uint32):
    """Handle fault exception and print debug info.

    Called from fault exception handlers with the stack pointer
    at the time of the fault.

    Args:
        fault_type: 0=HardFault, 1=MemManage, 2=BusFault, 3=UsageFault
        sp: Stack pointer at time of fault
    """
    print_str("\n*** FAULT EXCEPTION ***\n")

    if fault_type == 0:
        print_str("Type: HardFault\n")
    elif fault_type == 1:
        print_str("Type: MemManage\n")
    elif fault_type == 2:
        print_str("Type: BusFault\n")
    elif fault_type == 3:
        print_str("Type: UsageFault\n")
    else:
        print_str("Type: Unknown\n")

    # Read fault registers
    cfsr: uint32 = cast[Ptr[volatile uint32]](SCB_CFSR)[0]
    hfsr: uint32 = cast[Ptr[volatile uint32]](SCB_HFSR)[0]

    print_str("CFSR: 0x")
    print_hex(cfsr)
    print_newline()

    print_str("HFSR: 0x")
    print_hex(hfsr)
    print_newline()

    # Decode exception stack frame
    if sp != 0:
        _decode_exception_frame(sp)

    # Print backtrace
    debug_backtrace()

    # Halt
    print_str("\nSystem halted.\n")
    while True:
        pass

def _decode_exception_frame(sp: uint32):
    """Decode and print exception stack frame."""
    global _saved_regs

    frame: Ptr[uint32] = cast[Ptr[uint32]](sp)

    print_str("\nException Frame:\n")

    # Load registers from exception frame
    _saved_regs[REG_R0] = frame[0]
    _saved_regs[REG_R1] = frame[1]
    _saved_regs[REG_R2] = frame[2]
    _saved_regs[REG_R3] = frame[3]
    _saved_regs[REG_R12] = frame[4]
    _saved_regs[REG_LR] = frame[5]
    _saved_regs[REG_PC] = frame[6]
    _saved_regs[REG_PSR] = frame[7]

    print_str("  R0:  0x")
    print_hex(frame[0])
    print_str("  R1:  0x")
    print_hex(frame[1])
    print_newline()

    print_str("  R2:  0x")
    print_hex(frame[2])
    print_str("  R3:  0x")
    print_hex(frame[3])
    print_newline()

    print_str("  R12: 0x")
    print_hex(frame[4])
    print_str("  LR:  0x")
    print_hex(frame[5])
    print_newline()

    print_str("  PC:  0x")
    print_hex(frame[6])
    print_str("  PSR: 0x")
    print_hex(frame[7])
    print_newline()
