# Pynux Process Management
#
# Provides process scheduling, signals, IPC (pipes and message queues),
# and syscall interface for ARM Cortex-M3.

from lib.io import print_str, print_int, print_newline
from lib.memory import alloc, free, memset, memcpy

# ============================================================================
# Syscall Numbers
# ============================================================================
# Process management
SYS_EXIT: int32 = 0
SYS_YIELD: int32 = 1
SYS_GETPID: int32 = 2
SYS_CREATE: int32 = 3
SYS_KILL: int32 = 4
SYS_WAIT: int32 = 5
SYS_GETPRIORITY: int32 = 6
SYS_SETPRIORITY: int32 = 7
SYS_GETTIMESLICE: int32 = 8
SYS_SETTIMESLICE: int32 = 9

# Signals
SYS_SIGNAL: int32 = 10
SYS_SIGACTION: int32 = 11
SYS_SIGRETURN: int32 = 12

# IPC - Pipes
SYS_PIPE: int32 = 20
SYS_PIPE_READ: int32 = 21
SYS_PIPE_WRITE: int32 = 22
SYS_PIPE_CLOSE: int32 = 23

# IPC - Message Queues
SYS_MQ_CREATE: int32 = 30
SYS_MQ_SEND: int32 = 31
SYS_MQ_RECEIVE: int32 = 32
SYS_MQ_CLOSE: int32 = 33

# ============================================================================
# Process States
# ============================================================================
PROC_STATE_READY: int32 = 0
PROC_STATE_RUNNING: int32 = 1
PROC_STATE_BLOCKED: int32 = 2
PROC_STATE_TERMINATED: int32 = 3

# ============================================================================
# Signals
# ============================================================================
SIGTERM: int32 = 15
SIGKILL: int32 = 9
SIGUSR1: int32 = 10
SIGUSR2: int32 = 12

# Maximum number of signals
MAX_SIGNALS: int32 = 32

# ============================================================================
# Configuration
# ============================================================================
MAX_PROCESSES: int32 = 16
STACK_SIZE: int32 = 1024        # Per-process stack size
MAX_PIPES: int32 = 8
MAX_MESSAGE_QUEUES: int32 = 4
PIPE_BUFFER_SIZE: int32 = 256
MQ_MAX_MESSAGES: int32 = 8
MQ_MAX_MSG_SIZE: int32 = 64

# ============================================================================
# Priority and Scheduling Configuration
# ============================================================================
# Priority range: 0-31, higher value = higher priority
MIN_PRIORITY: int32 = 0
MAX_PRIORITY: int32 = 31
DEFAULT_PRIORITY: int32 = 16
NUM_PRIORITY_LEVELS: int32 = 32

# Time slicing configuration
DEFAULT_TIMESLICE: int32 = 10   # Default time quantum in ticks
MIN_TIMESLICE: int32 = 1
MAX_TIMESLICE: int32 = 100

# ============================================================================
# Process Control Block (PCB) - stored in BSS
# ============================================================================
# Each process has:
# - pid: Process ID
# - state: Current process state
# - stack_ptr: Saved stack pointer (sp)
# - priority: Process priority (0-31, higher value = more important)
# - timeslice: Configured time quantum in ticks
# - ticks_remaining: Remaining ticks before preemption
# - entry_func: Entry function pointer
# - stack_base: Base of allocated stack
# - pending_signals: Bitmask of pending signals
# - signal_handlers: Array of signal handler function pointers

# Process table (arrays for each field)
proc_pid: Array[16, int32]
proc_state: Array[16, int32]
proc_stack_ptr: Array[16, uint32]
proc_priority: Array[16, int32]
proc_entry: Array[16, uint32]
proc_stack_base: Array[16, uint32]
proc_pending_signals: Array[16, uint32]

# Time slicing: timeslice quota and remaining ticks for each process
proc_timeslice: Array[16, int32]        # Configured time quantum
proc_ticks_remaining: Array[16, int32]  # Remaining ticks before preemption

# Signal handlers: 16 processes x 32 signals = 512 entries
# Indexed as: proc_id * MAX_SIGNALS + signal_num
signal_handlers: Array[512, uint32]

# Process context save area for r4-r11 (8 registers per process)
# Indexed as: proc_id * 8 + register_index
proc_saved_regs: Array[128, uint32]

# ============================================================================
# Ready Queue Structure - Priority-based with round-robin per level
# ============================================================================
# For each priority level (0-31), we maintain a circular queue of process slots
# ready_queue[priority][position] = process slot index
# We use arrays to implement the queues:
#   - ready_queue: 32 priority levels x 16 max entries per level = 512 entries
#   - ready_head: head index for each priority level
#   - ready_tail: tail index for each priority level
#   - ready_count: number of entries at each priority level

ready_queue: Array[512, int32]          # 32 levels x 16 slots
ready_head: Array[32, int32]            # Head index per priority
ready_tail: Array[32, int32]            # Tail index per priority
ready_count: Array[32, int32]           # Count per priority

# Bitmap of non-empty priority levels for fast highest-priority lookup
# Each bit represents whether that priority level has any ready tasks
ready_bitmap: uint32 = 0

# Scheduler state
current_pid: int32 = -1
current_slot: int32 = -1                # Cache the current process slot
next_pid: int32 = 0
scheduler_running: bool = False
proc_count: int32 = 0
scheduler_locked: bool = False          # Prevent nested scheduling

# ============================================================================
# Pipe structures - stored in BSS
# ============================================================================
# Pipe state: 0 = unused, 1 = active
pipe_state: Array[8, int32]
pipe_read_fd: Array[8, int32]      # Read file descriptor
pipe_write_fd: Array[8, int32]     # Write file descriptor
pipe_read_pos: Array[8, int32]     # Read position in buffer
pipe_write_pos: Array[8, int32]    # Write position in buffer
pipe_count: Array[8, int32]        # Bytes in buffer

# Pipe buffers: 8 pipes x 256 bytes = 2048 bytes
pipe_buffers: Array[2048, uint8]

# File descriptor allocation
next_fd: int32 = 3  # Start after stdin(0), stdout(1), stderr(2)

# ============================================================================
# Message Queue structures - stored in BSS
# ============================================================================
# Message queue state: 0 = unused, 1 = active
mq_state: Array[4, int32]
mq_head: Array[4, int32]           # Head index
mq_tail: Array[4, int32]           # Tail index
mq_count: Array[4, int32]          # Number of messages

# Message sizes for each slot: 4 queues x 8 messages = 32 entries
mq_msg_sizes: Array[32, int32]

# Message buffers: 4 queues x 8 messages x 64 bytes = 2048 bytes
mq_buffers: Array[2048, uint8]

# ============================================================================
# Process Management Functions
# ============================================================================

def process_init():
    """Initialize the process subsystem."""
    global current_pid, current_slot, next_pid, scheduler_running, proc_count
    global next_fd, ready_bitmap, scheduler_locked

    state: int32 = critical_enter()

    # Clear all process slots
    i: int32 = 0
    while i < MAX_PROCESSES:
        proc_pid[i] = -1
        proc_state[i] = PROC_STATE_TERMINATED
        proc_stack_ptr[i] = 0
        proc_priority[i] = DEFAULT_PRIORITY
        proc_entry[i] = 0
        proc_stack_base[i] = 0
        proc_pending_signals[i] = 0
        proc_timeslice[i] = DEFAULT_TIMESLICE
        proc_ticks_remaining[i] = 0
        i = i + 1

    # Clear signal handlers
    i = 0
    while i < 512:
        signal_handlers[i] = 0
        i = i + 1

    # Clear saved registers
    i = 0
    while i < 128:
        proc_saved_regs[i] = 0
        i = i + 1

    # Initialize ready queues for all priority levels
    i = 0
    while i < NUM_PRIORITY_LEVELS:
        ready_head[i] = 0
        ready_tail[i] = 0
        ready_count[i] = 0
        i = i + 1

    # Clear ready queue entries
    i = 0
    while i < 512:
        ready_queue[i] = -1
        i = i + 1

    ready_bitmap = 0

    # Clear pipes
    i = 0
    while i < MAX_PIPES:
        pipe_state[i] = 0
        pipe_read_fd[i] = -1
        pipe_write_fd[i] = -1
        pipe_read_pos[i] = 0
        pipe_write_pos[i] = 0
        pipe_count[i] = 0
        i = i + 1

    # Clear message queues
    i = 0
    while i < MAX_MESSAGE_QUEUES:
        mq_state[i] = 0
        mq_head[i] = 0
        mq_tail[i] = 0
        mq_count[i] = 0
        i = i + 1

    current_pid = -1
    current_slot = -1
    next_pid = 0
    scheduler_running = False
    scheduler_locked = False
    proc_count = 0
    next_fd = 3

    critical_exit(state)

def find_free_slot() -> int32:
    """Find a free process slot. Returns -1 if none available."""
    i: int32 = 0
    while i < MAX_PROCESSES:
        if proc_state[i] == PROC_STATE_TERMINATED:
            return i
        i = i + 1
    return -1

def process_create(entry_func: Ptr[void]) -> int32:
    """Create a new process with the given entry function. Returns pid or -1 on error."""
    global next_pid, proc_count

    state: int32 = critical_enter()

    # Find free slot
    slot: int32 = find_free_slot()
    if slot < 0:
        critical_exit(state)
        return -1

    # Allocate stack
    stack: Ptr[uint8] = alloc(STACK_SIZE)
    if cast[uint32](stack) == 0:
        critical_exit(state)
        return -1

    # Initialize process
    pid: int32 = next_pid
    next_pid = next_pid + 1

    proc_pid[slot] = pid
    proc_state[slot] = PROC_STATE_READY
    proc_priority[slot] = DEFAULT_PRIORITY
    proc_entry[slot] = cast[uint32](entry_func)
    proc_stack_base[slot] = cast[uint32](stack)
    proc_pending_signals[slot] = 0

    # Initialize timeslice
    proc_timeslice[slot] = DEFAULT_TIMESLICE
    proc_ticks_remaining[slot] = DEFAULT_TIMESLICE

    # Set up initial stack pointer (stack grows down)
    # ARM Cortex-M requires 8-byte aligned stack
    stack_top: uint32 = cast[uint32](stack) + STACK_SIZE
    stack_top = stack_top & ~7  # Align to 8 bytes

    # Set up initial context on stack for context switch
    # We need to set up the stack as if the process had been interrupted
    # Stack layout (growing down):
    # xPSR, PC (entry), LR, R12, R3, R2, R1, R0 (pushed by hardware on exception)
    # Then we save R4-R11 manually

    # Reserve space for hardware-pushed context (8 words = 32 bytes)
    stack_top = stack_top - 32

    # Initialize hardware exception frame
    hw_frame: Ptr[uint32] = cast[Ptr[uint32]](stack_top)
    hw_frame[0] = 0                          # R0
    hw_frame[1] = 0                          # R1
    hw_frame[2] = 0                          # R2
    hw_frame[3] = 0                          # R3
    hw_frame[4] = 0                          # R12
    hw_frame[5] = cast[uint32](&process_exit_wrapper)  # LR - return to exit wrapper
    hw_frame[6] = cast[uint32](entry_func) | 1  # PC (entry point, Thumb bit set)
    hw_frame[7] = 0x01000000                 # xPSR (Thumb bit set)

    # Save initial stack pointer (after hardware frame)
    proc_stack_ptr[slot] = stack_top

    # Initialize saved registers (R4-R11) to zero
    i: int32 = 0
    while i < 8:
        proc_saved_regs[slot * 8 + i] = 0
        i = i + 1

    # Add to ready queue at default priority
    sched_add_ready_internal(slot, DEFAULT_PRIORITY)

    proc_count = proc_count + 1

    critical_exit(state)
    return pid

def process_create_with_priority(entry_func: Ptr[void], priority: int32) -> int32:
    """Create a new process with specified priority. Returns pid or -1 on error."""
    global next_pid, proc_count

    # Validate priority
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        priority = DEFAULT_PRIORITY

    state: int32 = critical_enter()

    # Find free slot
    slot: int32 = find_free_slot()
    if slot < 0:
        critical_exit(state)
        return -1

    # Allocate stack
    stack: Ptr[uint8] = alloc(STACK_SIZE)
    if cast[uint32](stack) == 0:
        critical_exit(state)
        return -1

    # Initialize process
    pid: int32 = next_pid
    next_pid = next_pid + 1

    proc_pid[slot] = pid
    proc_state[slot] = PROC_STATE_READY
    proc_priority[slot] = priority
    proc_entry[slot] = cast[uint32](entry_func)
    proc_stack_base[slot] = cast[uint32](stack)
    proc_pending_signals[slot] = 0

    # Initialize timeslice
    proc_timeslice[slot] = DEFAULT_TIMESLICE
    proc_ticks_remaining[slot] = DEFAULT_TIMESLICE

    # Set up initial stack pointer (stack grows down)
    stack_top: uint32 = cast[uint32](stack) + STACK_SIZE
    stack_top = stack_top & ~7  # Align to 8 bytes

    # Reserve space for hardware-pushed context (8 words = 32 bytes)
    stack_top = stack_top - 32

    # Initialize hardware exception frame
    hw_frame: Ptr[uint32] = cast[Ptr[uint32]](stack_top)
    hw_frame[0] = 0                          # R0
    hw_frame[1] = 0                          # R1
    hw_frame[2] = 0                          # R2
    hw_frame[3] = 0                          # R3
    hw_frame[4] = 0                          # R12
    hw_frame[5] = cast[uint32](&process_exit_wrapper)  # LR - return to exit wrapper
    hw_frame[6] = cast[uint32](entry_func) | 1  # PC (entry point, Thumb bit set)
    hw_frame[7] = 0x01000000                 # xPSR (Thumb bit set)

    # Save initial stack pointer (after hardware frame)
    proc_stack_ptr[slot] = stack_top

    # Initialize saved registers (R4-R11) to zero
    i: int32 = 0
    while i < 8:
        proc_saved_regs[slot * 8 + i] = 0
        i = i + 1

    # Add to ready queue at specified priority
    sched_add_ready_internal(slot, priority)

    proc_count = proc_count + 1

    critical_exit(state)
    return pid

def process_exit_wrapper():
    """Wrapper that calls process_exit when a process returns."""
    process_exit()

def process_exit():
    """Terminate the current process."""
    global current_pid, current_slot, proc_count

    if current_pid < 0:
        return

    state: int32 = critical_enter()

    # Find current process slot
    slot: int32 = current_slot
    if slot < 0:
        slot = find_proc_slot(current_pid)

    if slot >= 0:
        # Remove from ready queue if somehow still there
        if proc_state[slot] == PROC_STATE_READY:
            sched_remove_internal(slot, proc_priority[slot])

        # Free stack
        if proc_stack_base[slot] != 0:
            free(cast[Ptr[uint8]](proc_stack_base[slot]))
            proc_stack_base[slot] = 0

        # Mark as terminated
        proc_state[slot] = PROC_STATE_TERMINATED
        proc_pid[slot] = -1
        proc_count = proc_count - 1

    # Clear current process
    current_pid = -1
    current_slot = -1

    critical_exit(state)

    # Yield to let scheduler pick next process
    proc_yield()

def find_proc_slot(pid: int32) -> int32:
    """Find the slot index for a given pid. Returns -1 if not found."""
    i: int32 = 0
    while i < MAX_PROCESSES:
        if proc_pid[i] == pid and proc_state[i] != PROC_STATE_TERMINATED:
            return i
        i = i + 1
    return -1

def process_getpid() -> int32:
    """Get current process ID."""
    return current_pid

# ============================================================================
# Priority Management API
# ============================================================================

def proc_get_priority(pid: int32) -> int32:
    """Get process priority (0-31, higher = more important). Returns -1 if not found."""
    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return -1
    return proc_priority[slot]

def proc_set_priority(pid: int32, priority: int32) -> bool:
    """Set process priority (0-31, higher = more important). Returns True on success.

    If the process is in the ready queue, it will be moved to the new priority level.
    """
    # Validate priority range
    if priority < MIN_PRIORITY or priority > MAX_PRIORITY:
        return False

    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return False

    state: int32 = critical_enter()

    old_priority: int32 = proc_priority[slot]

    # If priority unchanged, nothing to do
    if old_priority == priority:
        critical_exit(state)
        return True

    # If process is in ready state, move it between priority queues
    if proc_state[slot] == PROC_STATE_READY:
        # Remove from old priority queue
        sched_remove_internal(slot, old_priority)
        # Update priority
        proc_priority[slot] = priority
        # Add to new priority queue
        sched_add_ready_internal(slot, priority)
    else:
        # Just update the priority field
        proc_priority[slot] = priority

    critical_exit(state)
    return True

# Backwards-compatible aliases
def process_get_priority(pid: int32) -> int32:
    """Alias for proc_get_priority for backward compatibility."""
    return proc_get_priority(pid)

def process_set_priority(pid: int32, priority: int32) -> bool:
    """Alias for proc_set_priority for backward compatibility."""
    return proc_set_priority(pid, priority)

# ============================================================================
# Time Slice Management
# ============================================================================

def proc_set_timeslice(pid: int32, ticks: int32) -> bool:
    """Set the time slice (quantum) for a process. Returns True on success.

    Args:
        pid: Process ID
        ticks: Number of timer ticks for the time quantum (1-100)
    """
    if ticks < MIN_TIMESLICE or ticks > MAX_TIMESLICE:
        return False

    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return False

    state: int32 = critical_enter()
    proc_timeslice[slot] = ticks
    critical_exit(state)
    return True

def proc_get_timeslice(pid: int32) -> int32:
    """Get the time slice (quantum) for a process. Returns -1 if not found."""
    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return -1
    return proc_timeslice[slot]

# ============================================================================
# Preemption and Yield
# ============================================================================

def proc_yield():
    """Voluntarily give up the CPU to allow other tasks to run.

    The current task will be moved to the back of its priority queue
    and the scheduler will pick the next task.
    """
    global current_slot

    if current_pid < 0:
        return

    state: int32 = critical_enter()

    slot: int32 = current_slot
    if slot < 0:
        slot = find_proc_slot(current_pid)

    if slot >= 0 and proc_state[slot] == PROC_STATE_RUNNING:
        # Reset timeslice for next run
        proc_ticks_remaining[slot] = proc_timeslice[slot]
        # Move to ready state and add to back of queue
        proc_state[slot] = PROC_STATE_READY
        sched_add_ready_internal(slot, proc_priority[slot])

    critical_exit(state)

    # Trigger context switch
    trigger_pendsv()

# Backwards-compatible alias
def process_yield():
    """Alias for proc_yield for backward compatibility."""
    proc_yield()

# ============================================================================
# Ready Queue Management (Internal Functions)
# ============================================================================

def sched_add_ready_internal(slot: int32, priority: int32):
    """Internal: Add a process slot to the ready queue at given priority.

    Must be called with interrupts disabled.
    """
    global ready_bitmap

    if priority < 0 or priority >= NUM_PRIORITY_LEVELS:
        return
    if slot < 0 or slot >= MAX_PROCESSES:
        return

    # Check if queue is full
    if ready_count[priority] >= MAX_PROCESSES:
        return

    # Calculate queue base for this priority level
    queue_base: int32 = priority * MAX_PROCESSES

    # Add to tail of queue
    tail_pos: int32 = ready_tail[priority]
    ready_queue[queue_base + tail_pos] = slot

    # Advance tail (circular)
    ready_tail[priority] = (tail_pos + 1) % MAX_PROCESSES
    ready_count[priority] = ready_count[priority] + 1

    # Set bit in bitmap to indicate this priority has tasks
    ready_bitmap = ready_bitmap | cast[uint32](1 << priority)

def sched_remove_internal(slot: int32, priority: int32):
    """Internal: Remove a process slot from the ready queue at given priority.

    Must be called with interrupts disabled.
    """
    global ready_bitmap

    if priority < 0 or priority >= NUM_PRIORITY_LEVELS:
        return
    if slot < 0 or slot >= MAX_PROCESSES:
        return
    if ready_count[priority] == 0:
        return

    queue_base: int32 = priority * MAX_PROCESSES
    count: int32 = ready_count[priority]
    head: int32 = ready_head[priority]

    # Search for the slot in the queue
    i: int32 = 0
    found_idx: int32 = -1
    while i < count:
        pos: int32 = (head + i) % MAX_PROCESSES
        if ready_queue[queue_base + pos] == slot:
            found_idx = i
            break
        i = i + 1

    if found_idx < 0:
        return  # Not found

    # Shift remaining elements forward
    i = found_idx
    while i < count - 1:
        src_pos: int32 = (head + i + 1) % MAX_PROCESSES
        dst_pos: int32 = (head + i) % MAX_PROCESSES
        ready_queue[queue_base + dst_pos] = ready_queue[queue_base + src_pos]
        i = i + 1

    # Decrease tail and count
    ready_tail[priority] = (ready_tail[priority] - 1 + MAX_PROCESSES) % MAX_PROCESSES
    ready_count[priority] = ready_count[priority] - 1

    # Clear bitmap bit if queue is now empty
    if ready_count[priority] == 0:
        ready_bitmap = ready_bitmap & ~cast[uint32](1 << priority)

def sched_pop_highest() -> int32:
    """Internal: Pop the highest priority ready task from the queue.

    Returns the slot index of the highest priority ready task, or -1 if none.
    Must be called with interrupts disabled.
    """
    global ready_bitmap

    if ready_bitmap == 0:
        return -1

    # Find highest priority with tasks (highest bit set)
    # Priority 31 is highest, priority 0 is lowest
    priority: int32 = MAX_PRIORITY
    while priority >= 0:
        mask: uint32 = cast[uint32](1 << priority)
        if (ready_bitmap & mask) != 0:
            break
        priority = priority - 1

    if priority < 0:
        return -1

    # Pop from head of this priority's queue
    queue_base: int32 = priority * MAX_PROCESSES
    head: int32 = ready_head[priority]
    slot: int32 = ready_queue[queue_base + head]

    # Advance head
    ready_head[priority] = (head + 1) % MAX_PROCESSES
    ready_count[priority] = ready_count[priority] - 1

    # Clear bitmap bit if queue is now empty
    if ready_count[priority] == 0:
        ready_bitmap = ready_bitmap & ~cast[uint32](1 << priority)

    return slot

# ============================================================================
# Scheduler Public API
# ============================================================================

def sched_add_ready(pid: int32):
    """Add a process to the ready queue based on its priority.

    This should be called when a process becomes ready to run
    (e.g., after creation, after unblocking from I/O, etc.)
    """
    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return

    state: int32 = critical_enter()

    # Only add if not already ready/running
    if proc_state[slot] != PROC_STATE_READY and proc_state[slot] != PROC_STATE_RUNNING:
        proc_state[slot] = PROC_STATE_READY
        proc_ticks_remaining[slot] = proc_timeslice[slot]
        sched_add_ready_internal(slot, proc_priority[slot])

    critical_exit(state)

def sched_remove(pid: int32):
    """Remove a process from the scheduler (ready queue).

    This should be called when a process blocks or terminates.
    """
    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return

    state: int32 = critical_enter()

    if proc_state[slot] == PROC_STATE_READY:
        sched_remove_internal(slot, proc_priority[slot])

    critical_exit(state)

def sched_schedule() -> int32:
    """Select the next task to run. Returns the PID of the selected task, or -1 if none.

    This function picks the highest priority ready task. Among tasks of equal
    priority, it uses round-robin scheduling (tasks are at the front of queue).
    """
    global current_pid, current_slot, scheduler_locked

    if scheduler_locked:
        return current_pid

    state: int32 = critical_enter()
    scheduler_locked = True

    # Get highest priority ready task
    next_slot: int32 = sched_pop_highest()

    if next_slot >= 0:
        proc_state[next_slot] = PROC_STATE_RUNNING
        proc_ticks_remaining[next_slot] = proc_timeslice[next_slot]
        current_pid = proc_pid[next_slot]
        current_slot = next_slot
    else:
        current_pid = -1
        current_slot = -1

    scheduler_locked = False
    critical_exit(state)

    return current_pid

def sched_tick():
    """Handle a timer tick for preemptive scheduling.

    This function should be called from the timer interrupt handler.
    It decrements the current task's remaining timeslice and triggers
    preemption when the timeslice expires.
    """
    global current_slot

    if current_pid < 0:
        return

    if not scheduler_running:
        return

    state: int32 = critical_enter()

    slot: int32 = current_slot
    if slot < 0:
        slot = find_proc_slot(current_pid)
        current_slot = slot

    if slot >= 0 and proc_state[slot] == PROC_STATE_RUNNING:
        # Decrement timeslice counter
        proc_ticks_remaining[slot] = proc_ticks_remaining[slot] - 1

        if proc_ticks_remaining[slot] <= 0:
            # Time quantum expired - preempt
            # Reset timeslice for next run
            proc_ticks_remaining[slot] = proc_timeslice[slot]
            # Move to back of ready queue
            proc_state[slot] = PROC_STATE_READY
            sched_add_ready_internal(slot, proc_priority[slot])

            critical_exit(state)

            # Trigger context switch
            trigger_pendsv()
            return

    critical_exit(state)

# ============================================================================
# Scheduler Start and Legacy Functions
# ============================================================================

def scheduler_start():
    """Start the scheduler and begin running processes."""
    global scheduler_running

    if proc_count == 0:
        return

    scheduler_running = True

    # Select and run first task
    sched_schedule()

def schedule_next():
    """Legacy function: Select next process to run.

    This now uses the priority-based scheduler internally.
    """
    global current_pid, current_slot

    if proc_count == 0:
        current_pid = -1
        current_slot = -1
        return

    state: int32 = critical_enter()

    # If current process is still running, put it back in ready queue
    if current_slot >= 0 and proc_state[current_slot] == PROC_STATE_RUNNING:
        proc_state[current_slot] = PROC_STATE_READY
        sched_add_ready_internal(current_slot, proc_priority[current_slot])

    critical_exit(state)

    # Use new scheduler to pick next task
    sched_schedule()

# ============================================================================
# Context Switch (called from PendSV handler)
# ============================================================================

def context_switch_out(sp: uint32) -> uint32:
    """Save context of current process. Called from PendSV with current SP."""
    global current_slot

    if current_pid < 0:
        return sp

    slot: int32 = current_slot
    if slot < 0:
        slot = find_proc_slot(current_pid)
        current_slot = slot

    if slot < 0:
        return sp

    # Save stack pointer
    proc_stack_ptr[slot] = sp

    return sp

def context_switch_in() -> uint32:
    """Load context of next process. Returns new SP."""
    global current_slot

    # Select next process using the priority scheduler
    schedule_next()

    if current_pid < 0:
        # No process to run, return to idle
        return 0

    slot: int32 = current_slot
    if slot < 0:
        slot = find_proc_slot(current_pid)
        current_slot = slot

    if slot < 0:
        return 0

    # Check for pending signals before resuming
    process_check_signals(slot)

    # Return saved stack pointer
    return proc_stack_ptr[slot]

def process_check_signals(slot: int32):
    """Check and handle pending signals for a process."""
    pending: uint32 = proc_pending_signals[slot]
    if pending == 0:
        return

    # Check each signal
    sig: int32 = 0
    while sig < MAX_SIGNALS:
        mask: uint32 = cast[uint32](1 << sig)
        if (pending & mask) != 0:
            # Clear pending bit
            proc_pending_signals[slot] = proc_pending_signals[slot] & ~mask

            # Handle signal
            if sig == SIGKILL:
                # SIGKILL cannot be caught - terminate process
                proc_state[slot] = PROC_STATE_TERMINATED
                return
            else:
                # Check for handler
                handler_idx: int32 = slot * MAX_SIGNALS + sig
                handler: uint32 = signal_handlers[handler_idx]
                if handler != 0:
                    # Call handler with signal number
                    # Cast to function pointer type and invoke
                    handler_fn: Fn[void, int32] = cast[Fn[void, int32]](handler)
                    handler_fn(sig)
                elif sig == SIGTERM:
                    # Default action for SIGTERM is terminate
                    proc_state[slot] = PROC_STATE_TERMINATED
                    return
        sig = sig + 1

# ============================================================================
# Signal Functions
# ============================================================================

def signal_send(pid: int32, sig: int32) -> bool:
    """Send a signal to a process. Returns True on success."""
    if sig < 0 or sig >= MAX_SIGNALS:
        return False

    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return False

    state: int32 = critical_enter()

    # Set pending bit
    mask: uint32 = cast[uint32](1 << sig)
    proc_pending_signals[slot] = proc_pending_signals[slot] | mask

    # If process is blocked, make it ready to handle signal
    if proc_state[slot] == PROC_STATE_BLOCKED:
        proc_state[slot] = PROC_STATE_READY
        proc_ticks_remaining[slot] = proc_timeslice[slot]
        sched_add_ready_internal(slot, proc_priority[slot])

    critical_exit(state)
    return True

def signal_handler(sig: int32, handler: Ptr[void]) -> bool:
    """Register a signal handler for the current process. Returns True on success."""
    if current_pid < 0:
        return False
    if sig < 0 or sig >= MAX_SIGNALS:
        return False
    if sig == SIGKILL:
        return False  # Cannot catch SIGKILL

    slot: int32 = find_proc_slot(current_pid)
    if slot < 0:
        return False

    handler_idx: int32 = slot * MAX_SIGNALS + sig
    signal_handlers[handler_idx] = cast[uint32](handler)
    return True

# ============================================================================
# Pipe Functions
# ============================================================================

def find_free_pipe() -> int32:
    """Find a free pipe slot. Returns -1 if none available."""
    i: int32 = 0
    while i < MAX_PIPES:
        if pipe_state[i] == 0:
            return i
        i = i + 1
    return -1

def pipe_create() -> int32:
    """Create a pipe. Returns read_fd in low 16 bits, write_fd in high 16 bits, or -1 on error."""
    global next_fd

    state: int32 = critical_enter()

    slot: int32 = find_free_pipe()
    if slot < 0:
        critical_exit(state)
        return -1

    # Allocate file descriptors
    read_fd: int32 = next_fd
    next_fd = next_fd + 1
    write_fd: int32 = next_fd
    next_fd = next_fd + 1

    # Initialize pipe
    pipe_state[slot] = 1
    pipe_read_fd[slot] = read_fd
    pipe_write_fd[slot] = write_fd
    pipe_read_pos[slot] = 0
    pipe_write_pos[slot] = 0
    pipe_count[slot] = 0

    critical_exit(state)

    # Pack both fds into return value
    result: int32 = read_fd | (write_fd << 16)
    return result

def find_pipe_by_fd(fd: int32) -> int32:
    """Find pipe slot by file descriptor. Returns slot or -1."""
    i: int32 = 0
    while i < MAX_PIPES:
        if pipe_state[i] == 1:
            if pipe_read_fd[i] == fd or pipe_write_fd[i] == fd:
                return i
        i = i + 1
    return -1

def pipe_write(fd: int32, buf: Ptr[uint8], len: int32) -> int32:
    """Write to a pipe. Returns bytes written or -1 on error."""
    slot: int32 = find_pipe_by_fd(fd)
    if slot < 0:
        return -1

    # Check if this is the write end
    if pipe_write_fd[slot] != fd:
        return -1

    state: int32 = critical_enter()

    # Calculate available space
    available: int32 = PIPE_BUFFER_SIZE - pipe_count[slot]
    if available <= 0:
        critical_exit(state)
        return 0  # Buffer full, would block

    # Write up to available bytes
    to_write: int32 = len
    if to_write > available:
        to_write = available

    # Get buffer offset for this pipe
    buf_base: int32 = slot * PIPE_BUFFER_SIZE

    # Write bytes with circular buffer
    written: int32 = 0
    while written < to_write:
        pos: int32 = (pipe_write_pos[slot] + written) % PIPE_BUFFER_SIZE
        pipe_buffers[buf_base + pos] = buf[written]
        written = written + 1

    # Update write position and count
    pipe_write_pos[slot] = (pipe_write_pos[slot] + written) % PIPE_BUFFER_SIZE
    pipe_count[slot] = pipe_count[slot] + written

    critical_exit(state)
    return written

def pipe_read(fd: int32, buf: Ptr[uint8], len: int32) -> int32:
    """Read from a pipe. Returns bytes read or -1 on error."""
    slot: int32 = find_pipe_by_fd(fd)
    if slot < 0:
        return -1

    # Check if this is the read end
    if pipe_read_fd[slot] != fd:
        return -1

    state: int32 = critical_enter()

    # Check available data
    available: int32 = pipe_count[slot]
    if available <= 0:
        critical_exit(state)
        return 0  # No data, would block

    # Read up to len bytes
    to_read: int32 = len
    if to_read > available:
        to_read = available

    # Get buffer offset for this pipe
    buf_base: int32 = slot * PIPE_BUFFER_SIZE

    # Read bytes with circular buffer
    read_count: int32 = 0
    while read_count < to_read:
        pos: int32 = (pipe_read_pos[slot] + read_count) % PIPE_BUFFER_SIZE
        buf[read_count] = pipe_buffers[buf_base + pos]
        read_count = read_count + 1

    # Update read position and count
    pipe_read_pos[slot] = (pipe_read_pos[slot] + read_count) % PIPE_BUFFER_SIZE
    pipe_count[slot] = pipe_count[slot] - read_count

    critical_exit(state)
    return read_count

def pipe_close(fd: int32) -> bool:
    """Close a pipe end. Returns True on success."""
    slot: int32 = find_pipe_by_fd(fd)
    if slot < 0:
        return False

    state: int32 = critical_enter()

    if pipe_read_fd[slot] == fd:
        pipe_read_fd[slot] = -1
    elif pipe_write_fd[slot] == fd:
        pipe_write_fd[slot] = -1

    # If both ends closed, free the pipe
    if pipe_read_fd[slot] == -1 and pipe_write_fd[slot] == -1:
        pipe_state[slot] = 0

    critical_exit(state)
    return True

# ============================================================================
# Message Queue Functions
# ============================================================================

def mq_create() -> int32:
    """Create a message queue. Returns queue id or -1 on error."""
    state: int32 = critical_enter()

    # Find free slot
    slot: int32 = -1
    i: int32 = 0
    while i < MAX_MESSAGE_QUEUES:
        if mq_state[i] == 0:
            slot = i
            break
        i = i + 1

    if slot < 0:
        critical_exit(state)
        return -1

    # Initialize queue
    mq_state[slot] = 1
    mq_head[slot] = 0
    mq_tail[slot] = 0
    mq_count[slot] = 0

    critical_exit(state)
    return slot

def mq_send(mqid: int32, buf: Ptr[uint8], len: int32) -> bool:
    """Send a message to a queue. Returns True on success."""
    if mqid < 0 or mqid >= MAX_MESSAGE_QUEUES:
        return False
    if mq_state[mqid] == 0:
        return False
    if len > MQ_MAX_MSG_SIZE:
        return False

    state: int32 = critical_enter()

    # Check if queue is full
    if mq_count[mqid] >= MQ_MAX_MESSAGES:
        critical_exit(state)
        return False

    # Calculate buffer position
    msg_slot: int32 = mq_tail[mqid]
    buf_offset: int32 = (mqid * MQ_MAX_MESSAGES + msg_slot) * MQ_MAX_MSG_SIZE

    # Copy message to buffer
    i: int32 = 0
    while i < len:
        mq_buffers[buf_offset + i] = buf[i]
        i = i + 1

    # Store message size
    mq_msg_sizes[mqid * MQ_MAX_MESSAGES + msg_slot] = len

    # Update tail and count
    mq_tail[mqid] = (mq_tail[mqid] + 1) % MQ_MAX_MESSAGES
    mq_count[mqid] = mq_count[mqid] + 1

    critical_exit(state)
    return True

def mq_receive(mqid: int32, buf: Ptr[uint8], maxlen: int32) -> int32:
    """Receive a message from a queue. Returns message length or -1 on error."""
    if mqid < 0 or mqid >= MAX_MESSAGE_QUEUES:
        return -1
    if mq_state[mqid] == 0:
        return -1

    state: int32 = critical_enter()

    # Check if queue is empty
    if mq_count[mqid] == 0:
        critical_exit(state)
        return 0  # No message available

    # Get message from head
    msg_slot: int32 = mq_head[mqid]
    buf_offset: int32 = (mqid * MQ_MAX_MESSAGES + msg_slot) * MQ_MAX_MSG_SIZE
    msg_len: int32 = mq_msg_sizes[mqid * MQ_MAX_MESSAGES + msg_slot]

    # Limit to maxlen
    copy_len: int32 = msg_len
    if copy_len > maxlen:
        copy_len = maxlen

    # Copy message from buffer
    i: int32 = 0
    while i < copy_len:
        buf[i] = mq_buffers[buf_offset + i]
        i = i + 1

    # Update head and count
    mq_head[mqid] = (mq_head[mqid] + 1) % MQ_MAX_MESSAGES
    mq_count[mqid] = mq_count[mqid] - 1

    critical_exit(state)
    return copy_len

def mq_close(mqid: int32) -> bool:
    """Close a message queue. Returns True on success."""
    if mqid < 0 or mqid >= MAX_MESSAGE_QUEUES:
        return False
    if mq_state[mqid] == 0:
        return False

    state: int32 = critical_enter()
    mq_state[mqid] = 0
    mq_head[mqid] = 0
    mq_tail[mqid] = 0
    mq_count[mqid] = 0
    critical_exit(state)

    return True

# ============================================================================
# Syscall Interface
# ============================================================================

def syscall(num: int32, arg1: int32, arg2: int32, arg3: int32) -> int32:
    """Syscall wrapper - invokes SVC instruction with syscall number."""
    # Use inline assembly to trigger SVC
    # The SVC handler will read num from r0 and dispatch appropriately
    result: int32 = 0

    # On ARM Cortex-M, we use SVC instruction
    # Arguments in r0-r3, syscall number in r0 (will be moved)
    # This is a simplified wrapper - real implementation uses SVC

    # For now, directly call the syscall handler
    result = syscall_dispatch(num, arg1, arg2, arg3)

    return result

def syscall_dispatch(num: int32, arg1: int32, arg2: int32, arg3: int32) -> int32:
    """Dispatch syscall to appropriate handler."""
    result: int32 = 0

    if num == SYS_EXIT:
        process_exit()
        result = 0

    elif num == SYS_YIELD:
        process_yield()
        result = 0

    elif num == SYS_GETPID:
        result = process_getpid()

    elif num == SYS_CREATE:
        result = process_create(cast[Ptr[void]](arg1))

    elif num == SYS_KILL:
        if signal_send(arg1, SIGKILL):
            result = 0
        else:
            result = -1

    elif num == SYS_WAIT:
        # Simplified wait - just yield for now
        process_yield()
        result = 0

    elif num == SYS_GETPRIORITY:
        result = proc_get_priority(arg1)

    elif num == SYS_SETPRIORITY:
        if proc_set_priority(arg1, arg2):
            result = 0
        else:
            result = -1

    elif num == SYS_GETTIMESLICE:
        result = proc_get_timeslice(arg1)

    elif num == SYS_SETTIMESLICE:
        if proc_set_timeslice(arg1, arg2):
            result = 0
        else:
            result = -1

    elif num == SYS_SIGNAL:
        if signal_send(arg1, arg2):
            result = 0
        else:
            result = -1

    elif num == SYS_SIGACTION:
        if signal_handler(arg1, cast[Ptr[void]](arg2)):
            result = 0
        else:
            result = -1

    elif num == SYS_PIPE:
        result = pipe_create()

    elif num == SYS_PIPE_READ:
        result = pipe_read(arg1, cast[Ptr[uint8]](arg2), arg3)

    elif num == SYS_PIPE_WRITE:
        result = pipe_write(arg1, cast[Ptr[uint8]](arg2), arg3)

    elif num == SYS_PIPE_CLOSE:
        if pipe_close(arg1):
            result = 0
        else:
            result = -1

    elif num == SYS_MQ_CREATE:
        result = mq_create()

    elif num == SYS_MQ_SEND:
        if mq_send(arg1, cast[Ptr[uint8]](arg2), arg3):
            result = 0
        else:
            result = -1

    elif num == SYS_MQ_RECEIVE:
        result = mq_receive(arg1, cast[Ptr[uint8]](arg2), arg3)

    elif num == SYS_MQ_CLOSE:
        if mq_close(arg1):
            result = 0
        else:
            result = -1

    else:
        result = -1  # Unknown syscall

    return result

# ============================================================================
# PendSV Trigger (for context switch)
# ============================================================================

# ICSR register for triggering PendSV
ICSR: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED04)
PENDSVSET: uint32 = 0x10000000

def trigger_pendsv():
    """Trigger PendSV interrupt for context switch."""
    ICSR[0] = PENDSVSET
    dsb()
    isb()

# ============================================================================
# Debug/Status Functions
# ============================================================================

def process_dump():
    """Dump process table for debugging."""
    print_str("[process] Process table:\n")
    i: int32 = 0
    while i < MAX_PROCESSES:
        if proc_pid[i] >= 0:
            print_str("  PID ")
            print_int(proc_pid[i])
            print_str(" state=")
            print_int(proc_state[i])
            print_str(" prio=")
            print_int(proc_priority[i])
            print_str(" slice=")
            print_int(proc_timeslice[i])
            print_str("/")
            print_int(proc_ticks_remaining[i])
            print_str("\n")
        i = i + 1
    print_str("[process] Current PID: ")
    print_int(current_pid)
    print_str("\n")
    print_str("[process] Ready bitmap: ")
    print_int(cast[int32](ready_bitmap))
    print_str("\n")

def sched_dump():
    """Dump scheduler ready queue state for debugging."""
    print_str("[sched] Ready queue state:\n")
    print_str("  Bitmap: 0x")
    # Print bitmap in hex (simplified - just print decimal)
    print_int(cast[int32](ready_bitmap))
    print_str("\n")

    # Show non-empty priority levels
    prio: int32 = MAX_PRIORITY
    while prio >= 0:
        if ready_count[prio] > 0:
            print_str("  Prio ")
            print_int(prio)
            print_str(": count=")
            print_int(ready_count[prio])
            print_str(" head=")
            print_int(ready_head[prio])
            print_str(" tail=")
            print_int(ready_tail[prio])
            print_str("\n")
        prio = prio - 1

    print_str("[sched] Current: PID=")
    print_int(current_pid)
    print_str(" slot=")
    print_int(current_slot)
    print_str("\n")
