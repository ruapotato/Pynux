# Pynux RTOS Synchronization Primitives
#
# Provides mutex, semaphore, condition variable, and read-write lock
# synchronization primitives for multi-threaded RTOS environments.
# Uses proper blocking via process state changes.

from lib.io import print_str, print_int, print_newline
from kernel.process import current_pid, find_proc_slot, proc_state
from kernel.process import PROC_STATE_READY, PROC_STATE_BLOCKED
from kernel.process import process_yield, MAX_PROCESSES

# ============================================================================
# Configuration Constants
# ============================================================================

MAX_MUTEXES: int32 = 16
MAX_SEMAPHORES: int32 = 16
MAX_COND_VARS: int32 = 16
MAX_RWLOCKS: int32 = 16

# Maximum waiters per synchronization object
MAX_WAITERS: int32 = 8

# ============================================================================
# Mutex States
# ============================================================================

MUTEX_FREE: int32 = 0
MUTEX_LOCKED: int32 = 1
MUTEX_DESTROYED: int32 = -1

# ============================================================================
# Mutex Data Structures
# ============================================================================

# Mutex state: MUTEX_FREE, MUTEX_LOCKED, or MUTEX_DESTROYED
mutex_state: Array[16, int32]

# Owner PID of the mutex (-1 if not owned)
mutex_owner: Array[16, int32]

# Wait queue for each mutex (up to MAX_WAITERS PIDs)
# Indexed as: mutex_id * MAX_WAITERS + waiter_index
mutex_waiters: Array[128, int32]

# Number of waiters for each mutex
mutex_waiter_count: Array[16, int32]

# Next mutex ID to allocate
mutex_next_id: int32 = 0

# ============================================================================
# Semaphore Data Structures
# ============================================================================

# Semaphore value (count)
sem_value: Array[16, int32]

# Semaphore active flag (1 = active, 0 = free, -1 = destroyed)
sem_state: Array[16, int32]

# Wait queue for each semaphore
# Indexed as: sem_id * MAX_WAITERS + waiter_index
sem_waiters: Array[128, int32]

# Number of waiters for each semaphore
sem_waiter_count: Array[16, int32]

# Next semaphore ID to allocate
sem_next_id: int32 = 0

# ============================================================================
# Condition Variable Data Structures
# ============================================================================

# Condition variable active flag (1 = active, 0 = free, -1 = destroyed)
cond_state: Array[16, int32]

# Wait queue for each condition variable
# Indexed as: cond_id * MAX_WAITERS + waiter_index
cond_waiters: Array[128, int32]

# Number of waiters for each condition variable
cond_waiter_count: Array[16, int32]

# Next condition variable ID to allocate
cond_next_id: int32 = 0

# ============================================================================
# Read-Write Lock Data Structures
# ============================================================================

# RWLock state: number of readers (positive) or writer locked (-1), 0 = free
rwlock_state: Array[16, int32]

# RWLock active flag (1 = active, 0 = free, -1 = destroyed)
rwlock_active: Array[16, int32]

# Writer owner PID (-1 if no writer)
rwlock_writer: Array[16, int32]

# Reader wait queue for each rwlock
# Indexed as: rwlock_id * MAX_WAITERS + waiter_index
rwlock_rd_waiters: Array[128, int32]
rwlock_rd_waiter_count: Array[16, int32]

# Writer wait queue for each rwlock
rwlock_wr_waiters: Array[128, int32]
rwlock_wr_waiter_count: Array[16, int32]

# Next rwlock ID to allocate
rwlock_next_id: int32 = 0

# ============================================================================
# Initialization
# ============================================================================

def sync_init():
    """Initialize all synchronization primitives."""
    global mutex_next_id, sem_next_id, cond_next_id, rwlock_next_id

    state: int32 = critical_enter()

    # Initialize mutexes
    i: int32 = 0
    while i < MAX_MUTEXES:
        mutex_state[i] = MUTEX_DESTROYED
        mutex_owner[i] = -1
        mutex_waiter_count[i] = 0
        j: int32 = 0
        while j < MAX_WAITERS:
            mutex_waiters[i * MAX_WAITERS + j] = -1
            j = j + 1
        i = i + 1
    mutex_next_id = 0

    # Initialize semaphores
    i = 0
    while i < MAX_SEMAPHORES:
        sem_state[i] = -1
        sem_value[i] = 0
        sem_waiter_count[i] = 0
        j: int32 = 0
        while j < MAX_WAITERS:
            sem_waiters[i * MAX_WAITERS + j] = -1
            j = j + 1
        i = i + 1
    sem_next_id = 0

    # Initialize condition variables
    i = 0
    while i < MAX_COND_VARS:
        cond_state[i] = -1
        cond_waiter_count[i] = 0
        j: int32 = 0
        while j < MAX_WAITERS:
            cond_waiters[i * MAX_WAITERS + j] = -1
            j = j + 1
        i = i + 1
    cond_next_id = 0

    # Initialize read-write locks
    i = 0
    while i < MAX_RWLOCKS:
        rwlock_active[i] = -1
        rwlock_state[i] = 0
        rwlock_writer[i] = -1
        rwlock_rd_waiter_count[i] = 0
        rwlock_wr_waiter_count[i] = 0
        j: int32 = 0
        while j < MAX_WAITERS:
            rwlock_rd_waiters[i * MAX_WAITERS + j] = -1
            rwlock_wr_waiters[i * MAX_WAITERS + j] = -1
            j = j + 1
        i = i + 1
    rwlock_next_id = 0

    critical_exit(state)

# ============================================================================
# Helper Functions
# ============================================================================

def _find_free_mutex_slot() -> int32:
    """Find a free mutex slot. Returns -1 if none available."""
    i: int32 = 0
    while i < MAX_MUTEXES:
        if mutex_state[i] == MUTEX_DESTROYED:
            return i
        i = i + 1
    return -1

def _find_free_sem_slot() -> int32:
    """Find a free semaphore slot. Returns -1 if none available."""
    i: int32 = 0
    while i < MAX_SEMAPHORES:
        if sem_state[i] == -1:
            return i
        i = i + 1
    return -1

def _find_free_cond_slot() -> int32:
    """Find a free condition variable slot. Returns -1 if none available."""
    i: int32 = 0
    while i < MAX_COND_VARS:
        if cond_state[i] == -1:
            return i
        i = i + 1
    return -1

def _find_free_rwlock_slot() -> int32:
    """Find a free read-write lock slot. Returns -1 if none available."""
    i: int32 = 0
    while i < MAX_RWLOCKS:
        if rwlock_active[i] == -1:
            return i
        i = i + 1
    return -1

def _block_current_process():
    """Block the current process by setting its state to BLOCKED."""
    if current_pid < 0:
        return
    slot: int32 = find_proc_slot(current_pid)
    if slot >= 0:
        proc_state[slot] = PROC_STATE_BLOCKED

def _unblock_process(pid: int32):
    """Unblock a process by setting its state to READY."""
    if pid < 0:
        return
    slot: int32 = find_proc_slot(pid)
    if slot >= 0:
        proc_state[slot] = PROC_STATE_READY

def _add_to_wait_queue(queue: Ptr[int32], count: Ptr[int32], max_count: int32, pid: int32) -> bool:
    """Add a PID to a wait queue. Returns True on success."""
    if count[0] >= max_count:
        return False
    queue[count[0]] = pid
    count[0] = count[0] + 1
    return True

def _remove_first_from_wait_queue(queue: Ptr[int32], count: Ptr[int32]) -> int32:
    """Remove and return the first PID from a wait queue. Returns -1 if empty."""
    if count[0] <= 0:
        return -1

    first_pid: int32 = queue[0]

    # Shift remaining entries
    i: int32 = 0
    while i < count[0] - 1:
        queue[i] = queue[i + 1]
        i = i + 1

    count[0] = count[0] - 1
    return first_pid

# ============================================================================
# Mutex Functions
# ============================================================================

def mutex_create() -> int32:
    """Create a new mutex. Returns mutex ID or -1 on error."""
    global mutex_next_id

    state: int32 = critical_enter()

    slot: int32 = _find_free_mutex_slot()
    if slot < 0:
        critical_exit(state)
        return -1

    mutex_state[slot] = MUTEX_FREE
    mutex_owner[slot] = -1
    mutex_waiter_count[slot] = 0

    # Clear wait queue
    i: int32 = 0
    while i < MAX_WAITERS:
        mutex_waiters[slot * MAX_WAITERS + i] = -1
        i = i + 1

    mutex_next_id = mutex_next_id + 1

    critical_exit(state)
    return slot

def mutex_lock(id: int32) -> bool:
    """Lock a mutex. Blocks if already locked. Returns True on success."""
    if id < 0 or id >= MAX_MUTEXES:
        return False

    while True:
        state: int32 = critical_enter()

        # Check if mutex is valid
        if mutex_state[id] == MUTEX_DESTROYED:
            critical_exit(state)
            return False

        # Check if mutex is free
        if mutex_state[id] == MUTEX_FREE:
            mutex_state[id] = MUTEX_LOCKED
            mutex_owner[id] = current_pid
            critical_exit(state)
            return True

        # Check for recursive lock (same owner)
        if mutex_owner[id] == current_pid:
            # Already own this mutex - deadlock prevention
            critical_exit(state)
            return False

        # Mutex is locked by another process - add to wait queue and block
        queue_ptr: Ptr[int32] = &mutex_waiters[id * MAX_WAITERS]
        count_ptr: Ptr[int32] = &mutex_waiter_count[id]

        added: bool = _add_to_wait_queue(queue_ptr, count_ptr, MAX_WAITERS, current_pid)
        if not added:
            # Wait queue full
            critical_exit(state)
            return False

        _block_current_process()
        critical_exit(state)

        # Yield to scheduler
        process_yield()

        # When we wake up, try again to acquire the mutex

def mutex_trylock(id: int32) -> bool:
    """Try to lock a mutex without blocking. Returns True if lock acquired."""
    if id < 0 or id >= MAX_MUTEXES:
        return False

    state: int32 = critical_enter()

    # Check if mutex is valid
    if mutex_state[id] == MUTEX_DESTROYED:
        critical_exit(state)
        return False

    # Check if mutex is free
    if mutex_state[id] == MUTEX_FREE:
        mutex_state[id] = MUTEX_LOCKED
        mutex_owner[id] = current_pid
        critical_exit(state)
        return True

    # Mutex is locked - return immediately without blocking
    critical_exit(state)
    return False

def mutex_unlock(id: int32) -> bool:
    """Unlock a mutex. Returns True on success."""
    if id < 0 or id >= MAX_MUTEXES:
        return False

    state: int32 = critical_enter()

    # Check if mutex is valid and locked
    if mutex_state[id] != MUTEX_LOCKED:
        critical_exit(state)
        return False

    # Check if current process owns the mutex
    if mutex_owner[id] != current_pid:
        critical_exit(state)
        return False

    # Wake up first waiter if any
    queue_ptr: Ptr[int32] = &mutex_waiters[id * MAX_WAITERS]
    count_ptr: Ptr[int32] = &mutex_waiter_count[id]

    next_pid: int32 = _remove_first_from_wait_queue(queue_ptr, count_ptr)

    if next_pid >= 0:
        # Transfer ownership to next waiter
        mutex_owner[id] = next_pid
        _unblock_process(next_pid)
    else:
        # No waiters - mark mutex as free
        mutex_state[id] = MUTEX_FREE
        mutex_owner[id] = -1

    critical_exit(state)
    return True

def mutex_destroy(id: int32):
    """Destroy a mutex. Wakes all waiters with failure."""
    if id < 0 or id >= MAX_MUTEXES:
        return

    state: int32 = critical_enter()

    # Wake all waiters
    queue_ptr: Ptr[int32] = &mutex_waiters[id * MAX_WAITERS]
    count_ptr: Ptr[int32] = &mutex_waiter_count[id]

    while count_ptr[0] > 0:
        pid: int32 = _remove_first_from_wait_queue(queue_ptr, count_ptr)
        if pid >= 0:
            _unblock_process(pid)

    mutex_state[id] = MUTEX_DESTROYED
    mutex_owner[id] = -1

    critical_exit(state)

# ============================================================================
# Semaphore Functions
# ============================================================================

def sem_create(initial_count: int32) -> int32:
    """Create a counting semaphore. Returns semaphore ID or -1 on error."""
    global sem_next_id

    if initial_count < 0:
        return -1

    state: int32 = critical_enter()

    slot: int32 = _find_free_sem_slot()
    if slot < 0:
        critical_exit(state)
        return -1

    sem_state[slot] = 1  # Active
    sem_value[slot] = initial_count
    sem_waiter_count[slot] = 0

    # Clear wait queue
    i: int32 = 0
    while i < MAX_WAITERS:
        sem_waiters[slot * MAX_WAITERS + i] = -1
        i = i + 1

    sem_next_id = sem_next_id + 1

    critical_exit(state)
    return slot

def sem_wait(id: int32) -> bool:
    """Decrement semaphore, blocking if count is 0. Returns True on success."""
    if id < 0 or id >= MAX_SEMAPHORES:
        return False

    while True:
        state: int32 = critical_enter()

        # Check if semaphore is valid
        if sem_state[id] != 1:
            critical_exit(state)
            return False

        # Check if count > 0
        if sem_value[id] > 0:
            sem_value[id] = sem_value[id] - 1
            critical_exit(state)
            return True

        # Count is 0 - add to wait queue and block
        queue_ptr: Ptr[int32] = &sem_waiters[id * MAX_WAITERS]
        count_ptr: Ptr[int32] = &sem_waiter_count[id]

        added: bool = _add_to_wait_queue(queue_ptr, count_ptr, MAX_WAITERS, current_pid)
        if not added:
            # Wait queue full
            critical_exit(state)
            return False

        _block_current_process()
        critical_exit(state)

        # Yield to scheduler
        process_yield()

        # When we wake up, try again

def sem_trywait(id: int32) -> bool:
    """Try to decrement semaphore without blocking. Returns True if successful."""
    if id < 0 or id >= MAX_SEMAPHORES:
        return False

    state: int32 = critical_enter()

    # Check if semaphore is valid
    if sem_state[id] != 1:
        critical_exit(state)
        return False

    # Check if count > 0
    if sem_value[id] > 0:
        sem_value[id] = sem_value[id] - 1
        critical_exit(state)
        return True

    # Count is 0 - return immediately without blocking
    critical_exit(state)
    return False

def sem_post(id: int32) -> bool:
    """Increment semaphore, waking one waiter if any. Returns True on success."""
    if id < 0 or id >= MAX_SEMAPHORES:
        return False

    state: int32 = critical_enter()

    # Check if semaphore is valid
    if sem_state[id] != 1:
        critical_exit(state)
        return False

    # Increment count
    sem_value[id] = sem_value[id] + 1

    # Wake first waiter if any
    queue_ptr: Ptr[int32] = &sem_waiters[id * MAX_WAITERS]
    count_ptr: Ptr[int32] = &sem_waiter_count[id]

    next_pid: int32 = _remove_first_from_wait_queue(queue_ptr, count_ptr)
    if next_pid >= 0:
        _unblock_process(next_pid)

    critical_exit(state)
    return True

def sem_getvalue(id: int32) -> int32:
    """Get current semaphore value. Returns -1 on error."""
    if id < 0 or id >= MAX_SEMAPHORES:
        return -1

    state: int32 = critical_enter()

    # Check if semaphore is valid
    if sem_state[id] != 1:
        critical_exit(state)
        return -1

    value: int32 = sem_value[id]
    critical_exit(state)
    return value

def sem_destroy(id: int32):
    """Destroy a semaphore. Wakes all waiters with failure."""
    if id < 0 or id >= MAX_SEMAPHORES:
        return

    state: int32 = critical_enter()

    # Wake all waiters
    queue_ptr: Ptr[int32] = &sem_waiters[id * MAX_WAITERS]
    count_ptr: Ptr[int32] = &sem_waiter_count[id]

    while count_ptr[0] > 0:
        pid: int32 = _remove_first_from_wait_queue(queue_ptr, count_ptr)
        if pid >= 0:
            _unblock_process(pid)

    sem_state[id] = -1  # Destroyed
    sem_value[id] = 0

    critical_exit(state)

# ============================================================================
# Condition Variable Functions
# ============================================================================

def cond_create() -> int32:
    """Create a condition variable. Returns cond ID or -1 on error."""
    global cond_next_id

    state: int32 = critical_enter()

    slot: int32 = _find_free_cond_slot()
    if slot < 0:
        critical_exit(state)
        return -1

    cond_state[slot] = 1  # Active
    cond_waiter_count[slot] = 0

    # Clear wait queue
    i: int32 = 0
    while i < MAX_WAITERS:
        cond_waiters[slot * MAX_WAITERS + i] = -1
        i = i + 1

    cond_next_id = cond_next_id + 1

    critical_exit(state)
    return slot

def cond_wait(cond_id: int32, mutex_id: int32) -> bool:
    """Wait on condition variable, atomically releasing mutex.
    Re-acquires mutex before returning. Returns True on success."""
    if cond_id < 0 or cond_id >= MAX_COND_VARS:
        return False
    if mutex_id < 0 or mutex_id >= MAX_MUTEXES:
        return False

    state: int32 = critical_enter()

    # Check if cond is valid
    if cond_state[cond_id] != 1:
        critical_exit(state)
        return False

    # Check if mutex is valid and owned by current process
    if mutex_state[mutex_id] != MUTEX_LOCKED or mutex_owner[mutex_id] != current_pid:
        critical_exit(state)
        return False

    # Add to condition variable wait queue
    queue_ptr: Ptr[int32] = &cond_waiters[cond_id * MAX_WAITERS]
    count_ptr: Ptr[int32] = &cond_waiter_count[cond_id]

    added: bool = _add_to_wait_queue(queue_ptr, count_ptr, MAX_WAITERS, current_pid)
    if not added:
        critical_exit(state)
        return False

    # Release mutex (transfer to waiter or mark free)
    mx_queue_ptr: Ptr[int32] = &mutex_waiters[mutex_id * MAX_WAITERS]
    mx_count_ptr: Ptr[int32] = &mutex_waiter_count[mutex_id]

    next_mx_pid: int32 = _remove_first_from_wait_queue(mx_queue_ptr, mx_count_ptr)
    if next_mx_pid >= 0:
        mutex_owner[mutex_id] = next_mx_pid
        _unblock_process(next_mx_pid)
    else:
        mutex_state[mutex_id] = MUTEX_FREE
        mutex_owner[mutex_id] = -1

    # Block current process
    _block_current_process()
    critical_exit(state)

    # Yield to scheduler
    process_yield()

    # When signaled, re-acquire the mutex
    result: bool = mutex_lock(mutex_id)
    return result

def cond_signal(id: int32) -> bool:
    """Wake one thread waiting on condition variable. Returns True on success."""
    if id < 0 or id >= MAX_COND_VARS:
        return False

    state: int32 = critical_enter()

    # Check if cond is valid
    if cond_state[id] != 1:
        critical_exit(state)
        return False

    # Wake first waiter if any
    queue_ptr: Ptr[int32] = &cond_waiters[id * MAX_WAITERS]
    count_ptr: Ptr[int32] = &cond_waiter_count[id]

    next_pid: int32 = _remove_first_from_wait_queue(queue_ptr, count_ptr)
    if next_pid >= 0:
        _unblock_process(next_pid)

    critical_exit(state)
    return True

def cond_broadcast(id: int32) -> bool:
    """Wake all threads waiting on condition variable. Returns True on success."""
    if id < 0 or id >= MAX_COND_VARS:
        return False

    state: int32 = critical_enter()

    # Check if cond is valid
    if cond_state[id] != 1:
        critical_exit(state)
        return False

    # Wake all waiters
    queue_ptr: Ptr[int32] = &cond_waiters[id * MAX_WAITERS]
    count_ptr: Ptr[int32] = &cond_waiter_count[id]

    while count_ptr[0] > 0:
        pid: int32 = _remove_first_from_wait_queue(queue_ptr, count_ptr)
        if pid >= 0:
            _unblock_process(pid)

    critical_exit(state)
    return True

def cond_destroy(id: int32):
    """Destroy a condition variable. Wakes all waiters."""
    if id < 0 or id >= MAX_COND_VARS:
        return

    state: int32 = critical_enter()

    # Wake all waiters
    queue_ptr: Ptr[int32] = &cond_waiters[id * MAX_WAITERS]
    count_ptr: Ptr[int32] = &cond_waiter_count[id]

    while count_ptr[0] > 0:
        pid: int32 = _remove_first_from_wait_queue(queue_ptr, count_ptr)
        if pid >= 0:
            _unblock_process(pid)

    cond_state[id] = -1  # Destroyed

    critical_exit(state)

# ============================================================================
# Read-Write Lock Functions
# ============================================================================

def rwlock_create() -> int32:
    """Create a read-write lock. Returns rwlock ID or -1 on error."""
    global rwlock_next_id

    state: int32 = critical_enter()

    slot: int32 = _find_free_rwlock_slot()
    if slot < 0:
        critical_exit(state)
        return -1

    rwlock_active[slot] = 1  # Active
    rwlock_state[slot] = 0   # Free (no readers, no writer)
    rwlock_writer[slot] = -1
    rwlock_rd_waiter_count[slot] = 0
    rwlock_wr_waiter_count[slot] = 0

    # Clear wait queues
    i: int32 = 0
    while i < MAX_WAITERS:
        rwlock_rd_waiters[slot * MAX_WAITERS + i] = -1
        rwlock_wr_waiters[slot * MAX_WAITERS + i] = -1
        i = i + 1

    rwlock_next_id = rwlock_next_id + 1

    critical_exit(state)
    return slot

def rwlock_rdlock(id: int32) -> bool:
    """Acquire read lock. Multiple readers allowed. Blocks if writer holds lock.
    Returns True on success."""
    if id < 0 or id >= MAX_RWLOCKS:
        return False

    while True:
        state: int32 = critical_enter()

        # Check if rwlock is valid
        if rwlock_active[id] != 1:
            critical_exit(state)
            return False

        # Check if no writer holds the lock and no writers waiting
        # (to prevent writer starvation, block readers if writers are waiting)
        if rwlock_state[id] >= 0 and rwlock_wr_waiter_count[id] == 0:
            # Increment reader count
            rwlock_state[id] = rwlock_state[id] + 1
            critical_exit(state)
            return True

        # Writer holds lock or writers waiting - add to read wait queue and block
        queue_ptr: Ptr[int32] = &rwlock_rd_waiters[id * MAX_WAITERS]
        count_ptr: Ptr[int32] = &rwlock_rd_waiter_count[id]

        added: bool = _add_to_wait_queue(queue_ptr, count_ptr, MAX_WAITERS, current_pid)
        if not added:
            critical_exit(state)
            return False

        _block_current_process()
        critical_exit(state)

        # Yield to scheduler
        process_yield()

        # When we wake up, try again

def rwlock_wrlock(id: int32) -> bool:
    """Acquire write lock. Exclusive access. Blocks if any reader or writer holds lock.
    Returns True on success."""
    if id < 0 or id >= MAX_RWLOCKS:
        return False

    while True:
        state: int32 = critical_enter()

        # Check if rwlock is valid
        if rwlock_active[id] != 1:
            critical_exit(state)
            return False

        # Check if lock is completely free
        if rwlock_state[id] == 0:
            # Acquire write lock
            rwlock_state[id] = -1  # -1 indicates writer holds lock
            rwlock_writer[id] = current_pid
            critical_exit(state)
            return True

        # Lock is held - add to write wait queue and block
        queue_ptr: Ptr[int32] = &rwlock_wr_waiters[id * MAX_WAITERS]
        count_ptr: Ptr[int32] = &rwlock_wr_waiter_count[id]

        added: bool = _add_to_wait_queue(queue_ptr, count_ptr, MAX_WAITERS, current_pid)
        if not added:
            critical_exit(state)
            return False

        _block_current_process()
        critical_exit(state)

        # Yield to scheduler
        process_yield()

        # When we wake up, try again

def rwlock_unlock(id: int32) -> bool:
    """Unlock a read-write lock. Works for both read and write locks.
    Returns True on success."""
    if id < 0 or id >= MAX_RWLOCKS:
        return False

    state: int32 = critical_enter()

    # Check if rwlock is valid
    if rwlock_active[id] != 1:
        critical_exit(state)
        return False

    # Check if writer is unlocking
    if rwlock_state[id] == -1:
        if rwlock_writer[id] != current_pid:
            # Not the writer - error
            critical_exit(state)
            return False

        # Release writer lock
        rwlock_state[id] = 0
        rwlock_writer[id] = -1

        # Prefer waking writers first (to prevent writer starvation)
        wr_queue_ptr: Ptr[int32] = &rwlock_wr_waiters[id * MAX_WAITERS]
        wr_count_ptr: Ptr[int32] = &rwlock_wr_waiter_count[id]

        if wr_count_ptr[0] > 0:
            # Wake one writer
            next_pid: int32 = _remove_first_from_wait_queue(wr_queue_ptr, wr_count_ptr)
            if next_pid >= 0:
                _unblock_process(next_pid)
        else:
            # Wake all waiting readers
            rd_queue_ptr: Ptr[int32] = &rwlock_rd_waiters[id * MAX_WAITERS]
            rd_count_ptr: Ptr[int32] = &rwlock_rd_waiter_count[id]

            while rd_count_ptr[0] > 0:
                next_pid: int32 = _remove_first_from_wait_queue(rd_queue_ptr, rd_count_ptr)
                if next_pid >= 0:
                    _unblock_process(next_pid)

        critical_exit(state)
        return True

    # Reader is unlocking
    if rwlock_state[id] > 0:
        rwlock_state[id] = rwlock_state[id] - 1

        # If no more readers and writers waiting, wake one writer
        if rwlock_state[id] == 0:
            wr_queue_ptr: Ptr[int32] = &rwlock_wr_waiters[id * MAX_WAITERS]
            wr_count_ptr: Ptr[int32] = &rwlock_wr_waiter_count[id]

            if wr_count_ptr[0] > 0:
                next_pid: int32 = _remove_first_from_wait_queue(wr_queue_ptr, wr_count_ptr)
                if next_pid >= 0:
                    _unblock_process(next_pid)

        critical_exit(state)
        return True

    # Lock not held - error
    critical_exit(state)
    return False

def rwlock_destroy(id: int32):
    """Destroy a read-write lock. Wakes all waiters."""
    if id < 0 or id >= MAX_RWLOCKS:
        return

    state: int32 = critical_enter()

    # Wake all read waiters
    rd_queue_ptr: Ptr[int32] = &rwlock_rd_waiters[id * MAX_WAITERS]
    rd_count_ptr: Ptr[int32] = &rwlock_rd_waiter_count[id]

    while rd_count_ptr[0] > 0:
        pid: int32 = _remove_first_from_wait_queue(rd_queue_ptr, rd_count_ptr)
        if pid >= 0:
            _unblock_process(pid)

    # Wake all write waiters
    wr_queue_ptr: Ptr[int32] = &rwlock_wr_waiters[id * MAX_WAITERS]
    wr_count_ptr: Ptr[int32] = &rwlock_wr_waiter_count[id]

    while wr_count_ptr[0] > 0:
        pid: int32 = _remove_first_from_wait_queue(wr_queue_ptr, wr_count_ptr)
        if pid >= 0:
            _unblock_process(pid)

    rwlock_active[id] = -1  # Destroyed
    rwlock_state[id] = 0
    rwlock_writer[id] = -1

    critical_exit(state)

# ============================================================================
# Debug/Status Functions
# ============================================================================

def sync_dump_mutexes():
    """Dump mutex status for debugging."""
    print_str("[sync] Mutex status:\n")
    i: int32 = 0
    while i < MAX_MUTEXES:
        if mutex_state[i] != MUTEX_DESTROYED:
            print_str("  Mutex ")
            print_int(i)
            if mutex_state[i] == MUTEX_FREE:
                print_str(": FREE\n")
            else:
                print_str(": LOCKED by PID ")
                print_int(mutex_owner[i])
                print_str(", waiters=")
                print_int(mutex_waiter_count[i])
                print_str("\n")
        i = i + 1

def sync_dump_semaphores():
    """Dump semaphore status for debugging."""
    print_str("[sync] Semaphore status:\n")
    i: int32 = 0
    while i < MAX_SEMAPHORES:
        if sem_state[i] == 1:
            print_str("  Sem ")
            print_int(i)
            print_str(": value=")
            print_int(sem_value[i])
            print_str(", waiters=")
            print_int(sem_waiter_count[i])
            print_str("\n")
        i = i + 1

def sync_dump_condvars():
    """Dump condition variable status for debugging."""
    print_str("[sync] Condition variable status:\n")
    i: int32 = 0
    while i < MAX_COND_VARS:
        if cond_state[i] == 1:
            print_str("  Cond ")
            print_int(i)
            print_str(": waiters=")
            print_int(cond_waiter_count[i])
            print_str("\n")
        i = i + 1

def sync_dump_rwlocks():
    """Dump read-write lock status for debugging."""
    print_str("[sync] RWLock status:\n")
    i: int32 = 0
    while i < MAX_RWLOCKS:
        if rwlock_active[i] == 1:
            print_str("  RWLock ")
            print_int(i)
            if rwlock_state[i] == 0:
                print_str(": FREE")
            elif rwlock_state[i] == -1:
                print_str(": WRITE locked by PID ")
                print_int(rwlock_writer[i])
            else:
                print_str(": READ locked (")
                print_int(rwlock_state[i])
                print_str(" readers)")
            print_str(", rd_waiters=")
            print_int(rwlock_rd_waiter_count[i])
            print_str(", wr_waiters=")
            print_int(rwlock_wr_waiter_count[i])
            print_str("\n")
        i = i + 1

def sync_dump_all():
    """Dump all synchronization primitive status."""
    sync_dump_mutexes()
    sync_dump_semaphores()
    sync_dump_condvars()
    sync_dump_rwlocks()
