# RP2040 Multicore Hardware Abstraction Layer
#
# The RP2040 has two identical Cortex-M0+ cores (Core 0 and Core 1).
# After reset, Core 1 is held in a sleep state waiting for commands
# via the inter-core FIFO. This module provides functions to:
#   - Launch code on Core 1
#   - Inter-core communication via hardware FIFOs
#   - Hardware spinlocks for synchronization
#   - Doorbell interrupts between cores
#
# Memory Map:
#   SIO_BASE: 0xD0000000 - Single-cycle IO (core-specific view)
#   Each core sees its own CPUID in SIO
#
# FIFO Protocol for Core 1 Launch:
#   Core 1 waits in bootrom for command sequence via FIFO:
#   Send: 0, 0, 1, vector_table, stack_pointer, entry_point
#   Core 1 acknowledges each value by echoing it back

# ============================================================================
# Base Addresses
# ============================================================================

SIO_BASE: uint32 = 0xD0000000

# PSM (Power-on State Machine) for core reset control
PSM_BASE: uint32 = 0x40010000

# ============================================================================
# SIO Register Offsets (Multicore-related)
# ============================================================================

# Core identification
SIO_CPUID: uint32 = 0x000           # Processor core ID (0 or 1)

# Inter-core FIFOs
SIO_FIFO_ST: uint32 = 0x050         # FIFO status
SIO_FIFO_WR: uint32 = 0x054         # Write to other core's RX FIFO
SIO_FIFO_RD: uint32 = 0x058         # Read from own RX FIFO

# FIFO Status bits
FIFO_ST_VLD: uint32 = 0x01          # FIFO has data for us (RX valid)
FIFO_ST_RDY: uint32 = 0x02          # FIFO can accept data (TX ready)
FIFO_ST_WOF: uint32 = 0x04          # TX FIFO overflow (write when full)
FIFO_ST_ROE: uint32 = 0x08          # RX FIFO underflow (read when empty)

# Hardware Spinlocks (32 locks)
SIO_SPINLOCK_BASE: uint32 = 0x100   # SPINLOCK0
SIO_SPINLOCK_ST: uint32 = 0x05C     # Spinlock state (bitmask of claimed)

# Doorbell registers
SIO_DOORBELL_OUT_SET: uint32 = 0x1A0   # Set doorbell to other core
SIO_DOORBELL_OUT_CLR: uint32 = 0x1A4   # Clear doorbell to other core
SIO_DOORBELL_IN: uint32 = 0x1A8        # Read doorbell from other core

# ============================================================================
# PSM Register Offsets (for core control)
# ============================================================================

PSM_FRCE_ON: uint32 = 0x00          # Force block power on
PSM_FRCE_OFF: uint32 = 0x04         # Force block power off
PSM_WDSEL: uint32 = 0x08            # Watchdog power off select
PSM_DONE: uint32 = 0x0C             # Block power status

PSM_PROC1: uint32 = (1 << 16)       # Core 1 power domain bit

# ============================================================================
# Constants
# ============================================================================

# Default Core 1 stack size (4KB)
CORE1_STACK_SIZE: uint32 = 4096

# Number of hardware spinlocks
NUM_SPINLOCKS: uint32 = 32

# Special values for core 1 launch sequence
CORE1_LAUNCH_SEQ_0: uint32 = 0
CORE1_LAUNCH_SEQ_1: uint32 = 0
CORE1_LAUNCH_SEQ_2: uint32 = 1

# Spinlock claiming bitmask (which locks are owned by software)
_spinlock_claimed: uint32 = 0

# Core 1 stack (statically allocated)
_core1_stack: Array[uint32, 1024]   # 4KB (1024 * 4 bytes)
_core1_launched: bool = False

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

def _save_and_disable_interrupts() -> uint32:
    """Save interrupt state and disable interrupts."""
    # On Cortex-M0+, read PRIMASK and disable
    primask: uint32
    asm("mrs %0, primask" : "=r"(primask))
    asm("cpsid i")
    return primask

def _restore_interrupts(state: uint32):
    """Restore interrupt state."""
    asm("msr primask, %0" : : "r"(state))

def _dsb():
    """Data synchronization barrier."""
    asm("dsb")

def _sev():
    """Send event to other core."""
    asm("sev")

def _wfe():
    """Wait for event."""
    asm("wfe")

# ============================================================================
# Core Identification
# ============================================================================

def multicore_get_core_num() -> uint32:
    """Get the current core number.

    Returns:
        0 for Core 0, 1 for Core 1
    """
    return mmio_read(SIO_BASE + SIO_CPUID)

# ============================================================================
# Inter-core FIFO Functions
# ============================================================================

def multicore_fifo_rvalid() -> bool:
    """Check if read data is available in FIFO.

    Returns:
        True if data is available to read
    """
    st: uint32 = mmio_read(SIO_BASE + SIO_FIFO_ST)
    return (st & FIFO_ST_VLD) != 0

def multicore_fifo_wready() -> bool:
    """Check if FIFO can accept write data.

    Returns:
        True if FIFO has space for a write
    """
    st: uint32 = mmio_read(SIO_BASE + SIO_FIFO_ST)
    return (st & FIFO_ST_RDY) != 0

def multicore_fifo_get_status() -> uint32:
    """Get raw FIFO status flags.

    Returns:
        FIFO status register value (VLD, RDY, WOF, ROE bits)
    """
    return mmio_read(SIO_BASE + SIO_FIFO_ST)

def multicore_fifo_push_blocking(data: uint32):
    """Push data to the other core's FIFO (blocking).

    Waits until the FIFO has space, then writes.
    Sends an event to wake the other core.

    Args:
        data: 32-bit value to send
    """
    while not multicore_fifo_wready():
        pass  # Busy wait

    mmio_write(SIO_BASE + SIO_FIFO_WR, data)
    _sev()  # Wake other core

def multicore_fifo_pop_blocking() -> uint32:
    """Pop data from our FIFO (blocking).

    Waits until data is available, then reads.

    Returns:
        32-bit value received from other core
    """
    while not multicore_fifo_rvalid():
        _wfe()  # Wait for event

    return mmio_read(SIO_BASE + SIO_FIFO_RD)

def multicore_fifo_push_timeout_us(data: uint32, timeout_us: uint32) -> bool:
    """Push data to FIFO with timeout.

    Args:
        data: 32-bit value to send
        timeout_us: Timeout in microseconds

    Returns:
        True if data was sent, False if timeout
    """
    # Approximate timeout using busy loop (assumes ~125MHz)
    timeout_loops: uint32 = timeout_us * 10  # ~10 loops per us at 125MHz

    while timeout_loops > 0:
        if multicore_fifo_wready():
            mmio_write(SIO_BASE + SIO_FIFO_WR, data)
            _sev()
            return True
        timeout_loops = timeout_loops - 1

    return False

def multicore_fifo_pop_timeout_us(timeout_us: uint32) -> (uint32, bool):
    """Pop data from FIFO with timeout.

    Args:
        timeout_us: Timeout in microseconds

    Returns:
        Tuple of (data, success). If timeout, success is False and data is 0.
    """
    timeout_loops: uint32 = timeout_us * 10

    while timeout_loops > 0:
        if multicore_fifo_rvalid():
            return (mmio_read(SIO_BASE + SIO_FIFO_RD), True)
        timeout_loops = timeout_loops - 1

    return (0, False)

def multicore_fifo_drain():
    """Drain any pending data from our FIFO.

    Reads and discards all data currently in the receive FIFO.
    Also clears overflow/underflow status flags.
    """
    while multicore_fifo_rvalid():
        discard: uint32 = mmio_read(SIO_BASE + SIO_FIFO_RD)

    # Clear status flags by writing to them
    mmio_write(SIO_BASE + SIO_FIFO_ST, FIFO_ST_WOF | FIFO_ST_ROE)

def multicore_fifo_wfe():
    """Wait for FIFO event.

    Use WFE to sleep until an inter-core event occurs.
    Call this instead of busy-waiting when waiting for FIFO data.
    """
    _wfe()

def multicore_fifo_clear_irq():
    """Clear FIFO interrupt flags.

    Clears the overflow and underflow error flags.
    """
    mmio_write(SIO_BASE + SIO_FIFO_ST, FIFO_ST_WOF | FIFO_ST_ROE)

# ============================================================================
# Core 1 Launch Functions
# ============================================================================

def _multicore_launch_core1_raw(entry: uint32, sp: uint32, vtor: uint32):
    """Low-level core 1 launch sequence.

    Core 1 sits in ROM waiting for a specific sequence via FIFO.
    The sequence is: 0, 0, 1, vector_table, stack_pointer, entry_point
    Core 1 echoes each value back for synchronization.

    Args:
        entry: Entry point address for Core 1
        sp: Stack pointer for Core 1
        vtor: Vector table address for Core 1
    """
    # Command sequence for Core 1 bootrom
    seq: Array[uint32, 6]
    seq[0] = 0          # Synchronization
    seq[1] = 0          # Synchronization
    seq[2] = 1          # Command: launch
    seq[3] = vtor       # Vector table
    seq[4] = sp         # Stack pointer
    seq[5] = entry      # Entry point

    attempts: uint32 = 0
    max_attempts: uint32 = 10

    while attempts < max_attempts:
        # Drain any stale data
        multicore_fifo_drain()

        # Send the sequence
        i: uint32 = 0
        success: bool = True

        while i < 6:
            # Wait to send
            while not multicore_fifo_wready():
                pass

            mmio_write(SIO_BASE + SIO_FIFO_WR, seq[i])
            _sev()

            # Wait for echo
            response: uint32
            got_response: bool
            response, got_response = multicore_fifo_pop_timeout_us(100000)  # 100ms timeout

            if not got_response:
                success = False
                break

            # Verify echo matches what we sent
            if response != seq[i]:
                success = False
                break

            i = i + 1

        if success:
            return  # Core 1 launched successfully

        attempts = attempts + 1

    # Failed to launch - should we panic?

def multicore_reset_core1():
    """Reset Core 1 to its initial state.

    After reset, Core 1 returns to ROM and waits for launch sequence.
    """
    global _core1_launched

    # Force Core 1 power off
    mmio_write(PSM_BASE + PSM_FRCE_OFF, PSM_PROC1)

    # Wait for power down
    while (mmio_read(PSM_BASE + PSM_DONE) & PSM_PROC1) != 0:
        pass

    # Release force off to let Core 1 power back on
    mmio_write(PSM_BASE + PSM_FRCE_OFF, 0)

    # Wait for power up
    while (mmio_read(PSM_BASE + PSM_DONE) & PSM_PROC1) == 0:
        pass

    _core1_launched = False

def multicore_launch_core1(entry_func: Ptr[void]):
    """Launch Core 1 with the given entry function.

    Uses the default Core 1 stack (4KB). Core 1 uses the same
    vector table as Core 0.

    Args:
        entry_func: Function pointer for Core 1 to execute.
                    Must be a void function with no arguments.
    """
    global _core1_launched

    if _core1_launched:
        multicore_reset_core1()

    # Calculate stack top (stack grows down)
    stack_bottom: uint32 = cast[uint32](addr(_core1_stack[0]))
    stack_top: uint32 = stack_bottom + CORE1_STACK_SIZE

    # Use Core 0's vector table (read from VTOR)
    vtor: uint32 = mmio_read(0xE000ED08)  # PPB VTOR register

    # Entry point
    entry: uint32 = cast[uint32](entry_func)

    # Ensure thumb bit is set for Cortex-M
    entry = entry | 1

    _multicore_launch_core1_raw(entry, stack_top, vtor)
    _core1_launched = True

def multicore_launch_core1_with_stack(entry_func: Ptr[void],
                                       stack_bottom: Ptr[uint32],
                                       stack_size: uint32):
    """Launch Core 1 with a custom stack.

    Args:
        entry_func: Function pointer for Core 1 to execute
        stack_bottom: Pointer to the base of the stack memory
        stack_size: Size of the stack in bytes
    """
    global _core1_launched

    if _core1_launched:
        multicore_reset_core1()

    # Calculate stack top (stack grows down, must be 8-byte aligned)
    stack_base: uint32 = cast[uint32](stack_bottom)
    stack_top: uint32 = (stack_base + stack_size) & ~7

    # Use Core 0's vector table
    vtor: uint32 = mmio_read(0xE000ED08)

    # Entry point with thumb bit
    entry: uint32 = cast[uint32](entry_func) | 1

    _multicore_launch_core1_raw(entry, stack_top, vtor)
    _core1_launched = True

# ============================================================================
# Hardware Spinlocks
# ============================================================================

def spin_lock_claim(lock_num: uint32):
    """Claim ownership of a spinlock.

    Marks the lock as claimed by software. Does not acquire the lock.
    Use this for static allocation of spinlock resources.

    Args:
        lock_num: Spinlock number (0-31)
    """
    global _spinlock_claimed

    if lock_num >= NUM_SPINLOCKS:
        return

    saved: uint32 = _save_and_disable_interrupts()
    _spinlock_claimed = _spinlock_claimed | (1 << lock_num)
    _restore_interrupts(saved)

def spin_lock_unclaim(lock_num: uint32):
    """Release ownership claim on a spinlock.

    Args:
        lock_num: Spinlock number (0-31)
    """
    global _spinlock_claimed

    if lock_num >= NUM_SPINLOCKS:
        return

    saved: uint32 = _save_and_disable_interrupts()
    _spinlock_claimed = _spinlock_claimed & ~(1 << lock_num)
    _restore_interrupts(saved)

def spin_lock_is_claimed(lock_num: uint32) -> bool:
    """Check if a spinlock is claimed by software.

    Args:
        lock_num: Spinlock number (0-31)

    Returns:
        True if claimed
    """
    if lock_num >= NUM_SPINLOCKS:
        return False

    return (_spinlock_claimed & (1 << lock_num)) != 0

def spin_lock_claim_unused(required: bool) -> int32:
    """Find and claim an unused spinlock.

    Args:
        required: If True, panic if no lock available

    Returns:
        Lock number (0-31), or -1 if none available and not required
    """
    global _spinlock_claimed

    saved: uint32 = _save_and_disable_interrupts()

    i: uint32 = 0
    while i < NUM_SPINLOCKS:
        if (_spinlock_claimed & (1 << i)) == 0:
            _spinlock_claimed = _spinlock_claimed | (1 << i)
            _restore_interrupts(saved)
            return cast[int32](i)
        i = i + 1

    _restore_interrupts(saved)

    if required:
        # Should panic here
        while True:
            pass

    return -1

def spin_lock_blocking(lock_num: uint32) -> uint32:
    """Acquire a spinlock, blocking until available.

    Disables interrupts before acquiring to prevent deadlock.
    The returned value must be passed to spin_unlock.

    Args:
        lock_num: Spinlock number (0-31)

    Returns:
        Saved interrupt state (pass to spin_unlock)
    """
    if lock_num >= NUM_SPINLOCKS:
        return 0

    # Disable interrupts first to prevent IRQ handler deadlock
    saved: uint32 = _save_and_disable_interrupts()

    # Address of this spinlock register
    lock_addr: uint32 = SIO_BASE + SIO_SPINLOCK_BASE + (lock_num * 4)

    # Try to acquire the lock
    # Reading the register attempts to acquire - returns 0 if already held
    while mmio_read(lock_addr) == 0:
        pass  # Spin until we get it

    _dsb()  # Ensure lock acquisition is visible before proceeding

    return saved

def spin_lock_unsafe_blocking(lock_num: uint32):
    """Acquire a spinlock without disabling interrupts.

    Warning: This can deadlock if an interrupt handler tries to acquire
    the same lock. Only use when you know the lock is not used in IRQs.

    Args:
        lock_num: Spinlock number (0-31)
    """
    if lock_num >= NUM_SPINLOCKS:
        return

    lock_addr: uint32 = SIO_BASE + SIO_SPINLOCK_BASE + (lock_num * 4)

    while mmio_read(lock_addr) == 0:
        pass

    _dsb()

def spin_unlock(lock_num: uint32, saved_irq: uint32):
    """Release a spinlock and restore interrupt state.

    Args:
        lock_num: Spinlock number (0-31)
        saved_irq: Value returned from spin_lock_blocking
    """
    if lock_num >= NUM_SPINLOCKS:
        return

    _dsb()  # Ensure all writes complete before releasing lock

    # Write any value to release the lock
    lock_addr: uint32 = SIO_BASE + SIO_SPINLOCK_BASE + (lock_num * 4)
    mmio_write(lock_addr, 1)

    _restore_interrupts(saved_irq)

def spin_unlock_unsafe(lock_num: uint32):
    """Release a spinlock without restoring interrupts.

    Use with spin_lock_unsafe_blocking.

    Args:
        lock_num: Spinlock number (0-31)
    """
    if lock_num >= NUM_SPINLOCKS:
        return

    _dsb()

    lock_addr: uint32 = SIO_BASE + SIO_SPINLOCK_BASE + (lock_num * 4)
    mmio_write(lock_addr, 1)

def spin_lock_get_hw_state() -> uint32:
    """Get the hardware spinlock state.

    Returns:
        Bitmask of currently held spinlocks (1 = held)
    """
    return mmio_read(SIO_BASE + SIO_SPINLOCK_ST)

def spin_lock_is_held(lock_num: uint32) -> bool:
    """Check if a spinlock is currently held.

    Args:
        lock_num: Spinlock number (0-31)

    Returns:
        True if the lock is held by any core
    """
    if lock_num >= NUM_SPINLOCKS:
        return False

    state: uint32 = mmio_read(SIO_BASE + SIO_SPINLOCK_ST)
    return (state & (1 << lock_num)) != 0

# ============================================================================
# Doorbell (Inter-core Interrupts)
# ============================================================================

def multicore_doorbell_set(mask: uint32):
    """Set doorbell bits to signal the other core.

    The other core can read these bits and receive an interrupt
    (SIO_IRQ_PROC0 or SIO_IRQ_PROC1).

    Args:
        mask: Bitmask of doorbell bits to set
    """
    mmio_write(SIO_BASE + SIO_DOORBELL_OUT_SET, mask)

def multicore_doorbell_clear(mask: uint32):
    """Clear doorbell bits.

    Args:
        mask: Bitmask of doorbell bits to clear
    """
    mmio_write(SIO_BASE + SIO_DOORBELL_OUT_CLR, mask)

def multicore_doorbell_get() -> uint32:
    """Get doorbell bits set by the other core.

    Returns:
        Bitmask of doorbell bits set by the other core
    """
    return mmio_read(SIO_BASE + SIO_DOORBELL_IN)

# ============================================================================
# Core Lockout (Pause/Resume other core)
# ============================================================================

# Lockout state
_lockout_in_progress: bool = False
LOCKOUT_MAGIC: uint32 = 0xDEADBEEF
LOCKOUT_ACK: uint32 = 0xCAFEBABE

def multicore_lockout_start():
    """Pause the other core.

    Sends a signal to the other core to enter a lockout state.
    The other core will spin waiting for release.

    Note: The other core must be running the lockout victim handler
    or periodically checking for lockout requests.
    """
    global _lockout_in_progress

    if _lockout_in_progress:
        return

    _lockout_in_progress = True

    # Send lockout request via FIFO
    multicore_fifo_drain()
    multicore_fifo_push_blocking(LOCKOUT_MAGIC)

    # Wait for acknowledgment
    response: uint32 = multicore_fifo_pop_blocking()
    # Expected: LOCKOUT_ACK

def multicore_lockout_end():
    """Resume the other core after lockout.

    Signals the other core to exit the lockout state and continue.
    """
    global _lockout_in_progress

    if not _lockout_in_progress:
        return

    # Send release signal
    multicore_fifo_push_blocking(0)
    _lockout_in_progress = False

def multicore_lockout_victim_handler():
    """Handler for the core being locked out.

    Call this periodically or from FIFO IRQ handler.
    When a lockout request is received, this function will
    spin until released.
    """
    if not multicore_fifo_rvalid():
        return

    request: uint32 = mmio_read(SIO_BASE + SIO_FIFO_RD)

    if request != LOCKOUT_MAGIC:
        return

    # Acknowledge lockout
    multicore_fifo_push_blocking(LOCKOUT_ACK)

    # Wait for release
    while True:
        if multicore_fifo_rvalid():
            release: uint32 = mmio_read(SIO_BASE + SIO_FIFO_RD)
            if release == 0:
                break

# ============================================================================
# Utility Functions
# ============================================================================

def multicore_is_core1_running() -> bool:
    """Check if Core 1 has been launched.

    Returns:
        True if Core 1 has been launched
    """
    return _core1_launched

def multicore_fifo_irq_enable():
    """Enable FIFO interrupt for this core.

    Enables SIO_IRQ_PROC0 or SIO_IRQ_PROC1 depending on current core.
    """
    core: uint32 = multicore_get_core_num()

    # NVIC interrupt numbers: SIO_IRQ_PROC0 = 15, SIO_IRQ_PROC1 = 16
    irq_num: uint32 = 15 + core

    # Enable in NVIC (PPB + 0xE100 is NVIC_ISER)
    nvic_iser: uint32 = 0xE000E100
    mmio_write(nvic_iser, 1 << irq_num)

def multicore_fifo_irq_disable():
    """Disable FIFO interrupt for this core."""
    core: uint32 = multicore_get_core_num()
    irq_num: uint32 = 15 + core

    # Disable in NVIC (PPB + 0xE180 is NVIC_ICER)
    nvic_icer: uint32 = 0xE000E180
    mmio_write(nvic_icer, 1 << irq_num)
