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
DEFAULT_PRIORITY: int32 = 10
MAX_PIPES: int32 = 8
MAX_MESSAGE_QUEUES: int32 = 4
PIPE_BUFFER_SIZE: int32 = 256
MQ_MAX_MESSAGES: int32 = 8
MQ_MAX_MSG_SIZE: int32 = 64

# ============================================================================
# Process Control Block (PCB) - stored in BSS
# ============================================================================
# Each process has:
# - pid: Process ID
# - state: Current process state
# - stack_ptr: Saved stack pointer (sp)
# - priority: Process priority (lower = higher priority)
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

# Signal handlers: 16 processes x 32 signals = 512 entries
# Indexed as: proc_id * MAX_SIGNALS + signal_num
signal_handlers: Array[512, uint32]

# Process context save area for r4-r11 (8 registers per process)
# Indexed as: proc_id * 8 + register_index
proc_saved_regs: Array[128, uint32]

# Scheduler state
current_pid: int32 = -1
next_pid: int32 = 0
scheduler_running: bool = False
proc_count: int32 = 0

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
    global current_pid, next_pid, scheduler_running, proc_count, next_fd

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
    next_pid = 0
    scheduler_running = False
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

    proc_count = proc_count + 1

    critical_exit(state)
    return pid

def process_exit_wrapper():
    """Wrapper that calls process_exit when a process returns."""
    process_exit()

def process_exit():
    """Terminate the current process."""
    global current_pid, proc_count

    if current_pid < 0:
        return

    state: int32 = critical_enter()

    # Find current process slot
    slot: int32 = find_proc_slot(current_pid)
    if slot >= 0:
        # Free stack
        if proc_stack_base[slot] != 0:
            free(cast[Ptr[uint8]](proc_stack_base[slot]))
            proc_stack_base[slot] = 0

        # Mark as terminated
        proc_state[slot] = PROC_STATE_TERMINATED
        proc_pid[slot] = -1
        proc_count = proc_count - 1

    critical_exit(state)

    # Yield to let scheduler pick next process
    process_yield()

def process_yield():
    """Cooperative yield - give up CPU to scheduler."""
    # Trigger PendSV for context switch
    trigger_pendsv()

def find_proc_slot(pid: int32) -> int32:
    """Find the slot index for a given pid. Returns -1 if not found."""
    i: int32 = 0
    while i < MAX_PROCESSES:
        if proc_pid[i] == pid and proc_state[i] != PROC_STATE_TERMINATED:
            return i
        i = i + 1
    return -1

def process_get_priority(pid: int32) -> int32:
    """Get process priority. Returns -1 if process not found."""
    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return -1
    return proc_priority[slot]

def process_set_priority(pid: int32, priority: int32) -> bool:
    """Set process priority. Returns True on success."""
    slot: int32 = find_proc_slot(pid)
    if slot < 0:
        return False
    proc_priority[slot] = priority
    return True

def process_getpid() -> int32:
    """Get current process ID."""
    return current_pid

# ============================================================================
# Scheduler - Round Robin
# ============================================================================

def scheduler_start():
    """Start the scheduler and begin running processes."""
    global scheduler_running

    if proc_count == 0:
        return

    scheduler_running = True

    # Find first ready process and start it
    schedule_next()

def schedule_next():
    """Select next process to run using round-robin scheduling."""
    global current_pid

    if proc_count == 0:
        current_pid = -1
        return

    state: int32 = critical_enter()

    # Find current slot
    current_slot: int32 = -1
    if current_pid >= 0:
        current_slot = find_proc_slot(current_pid)
        if current_slot >= 0 and proc_state[current_slot] == PROC_STATE_RUNNING:
            proc_state[current_slot] = PROC_STATE_READY

    # Round-robin: start from next slot after current
    start: int32 = 0
    if current_slot >= 0:
        start = (current_slot + 1) % MAX_PROCESSES

    # Find next ready process
    i: int32 = 0
    found: int32 = -1
    while i < MAX_PROCESSES:
        slot: int32 = (start + i) % MAX_PROCESSES
        if proc_state[slot] == PROC_STATE_READY:
            found = slot
            break
        i = i + 1

    if found >= 0:
        proc_state[found] = PROC_STATE_RUNNING
        current_pid = proc_pid[found]
    else:
        current_pid = -1

    critical_exit(state)

# ============================================================================
# Context Switch (called from PendSV handler)
# ============================================================================

def context_switch_out(sp: uint32) -> uint32:
    """Save context of current process. Called from PendSV with current SP."""
    if current_pid < 0:
        return sp

    slot: int32 = find_proc_slot(current_pid)
    if slot < 0:
        return sp

    # Save stack pointer
    proc_stack_ptr[slot] = sp

    return sp

def context_switch_in() -> uint32:
    """Load context of next process. Returns new SP."""
    # Select next process
    schedule_next()

    if current_pid < 0:
        # No process to run, return to idle
        return 0

    slot: int32 = find_proc_slot(current_pid)
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
        result = process_get_priority(arg1)

    elif num == SYS_SETPRIORITY:
        if process_set_priority(arg1, arg2):
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
            print_str("\n")
        i = i + 1
    print_str("[process] Current PID: ")
    print_int(current_pid)
    print_str("\n")
