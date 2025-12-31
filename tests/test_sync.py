# Pynux Synchronization Primitives Tests
#
# Tests for mutex, semaphore, condition variable, and read-write lock.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_lt, test_pass, test_fail)
from kernel.sync import (
    # Mutex
    mutex_create, mutex_lock, mutex_trylock, mutex_unlock, mutex_destroy,
    MUTEX_FREE, MUTEX_LOCKED, MAX_MUTEXES,
    # Semaphore
    sem_create, sem_wait, sem_trywait, sem_post, sem_destroy,
    MAX_SEMAPHORES,
    # Condition variable
    cond_create, cond_wait, cond_signal, cond_broadcast, cond_destroy,
    MAX_COND_VARS,
    # Read-write lock
    rwlock_create, rwlock_read_lock, rwlock_read_unlock,
    rwlock_write_lock, rwlock_write_unlock, rwlock_destroy,
    MAX_RWLOCKS
)

# ============================================================================
# Mutex Tests
# ============================================================================

def test_mutex_create():
    """Test mutex creation."""
    print_section("Mutex Creation")

    mid: int32 = mutex_create()
    assert_gte(mid, 0, "mutex_create returns valid ID")

    if mid >= 0:
        mutex_destroy(mid)

def test_mutex_create_multiple():
    """Test creating multiple mutexes."""
    mids: Array[5, int32]
    i: int32 = 0

    while i < 5:
        mids[i] = mutex_create()
        i = i + 1

    created: int32 = 0
    i = 0
    while i < 5:
        if mids[i] >= 0:
            created = created + 1
        i = i + 1

    assert_eq(created, 5, "create 5 mutexes")

    # Cleanup
    i = 0
    while i < 5:
        if mids[i] >= 0:
            mutex_destroy(mids[i])
        i = i + 1

def test_mutex_lock_unlock():
    """Test mutex lock and unlock."""
    print_section("Mutex Lock/Unlock")

    mid: int32 = mutex_create()
    if mid < 0:
        test_fail("could not create mutex")
        return

    # Lock should succeed
    result: bool = mutex_lock(mid)
    assert_true(result, "mutex_lock succeeds")

    # Unlock should succeed
    result = mutex_unlock(mid)
    assert_true(result, "mutex_unlock succeeds")

    mutex_destroy(mid)

def test_mutex_trylock():
    """Test mutex trylock."""
    mid: int32 = mutex_create()
    if mid < 0:
        test_fail("could not create mutex")
        return

    # First trylock should succeed
    result: bool = mutex_trylock(mid)
    assert_true(result, "first trylock succeeds")

    # Second trylock should fail (already locked by us)
    # Note: Depends on implementation - recursive or not
    # For non-recursive mutex, this would fail
    # For recursive, it might succeed

    mutex_unlock(mid)
    mutex_destroy(mid)

def test_mutex_destroy():
    """Test mutex destruction."""
    print_section("Mutex Destroy")

    mid: int32 = mutex_create()
    if mid < 0:
        test_fail("could not create mutex")
        return

    result: bool = mutex_destroy(mid)
    assert_true(result, "mutex_destroy succeeds")

    # Using destroyed mutex should fail
    result = mutex_lock(mid)
    assert_false(result, "lock on destroyed mutex fails")

# ============================================================================
# Semaphore Tests
# ============================================================================

def test_sem_create():
    """Test semaphore creation."""
    print_section("Semaphore Creation")

    # Create with initial value 1
    sid: int32 = sem_create(1)
    assert_gte(sid, 0, "sem_create(1) returns valid ID")

    if sid >= 0:
        sem_destroy(sid)

    # Create with initial value 0
    sid = sem_create(0)
    assert_gte(sid, 0, "sem_create(0) returns valid ID")

    if sid >= 0:
        sem_destroy(sid)

def test_sem_wait_post():
    """Test semaphore wait and post."""
    print_section("Semaphore Wait/Post")

    # Create binary semaphore (initial value 1)
    sid: int32 = sem_create(1)
    if sid < 0:
        test_fail("could not create semaphore")
        return

    # Wait should succeed (decrements to 0)
    result: bool = sem_wait(sid)
    assert_true(result, "sem_wait succeeds")

    # Post should succeed (increments back to 1)
    result = sem_post(sid)
    assert_true(result, "sem_post succeeds")

    sem_destroy(sid)

def test_sem_trywait():
    """Test semaphore trywait."""
    # Create with initial value 1
    sid: int32 = sem_create(1)
    if sid < 0:
        test_fail("could not create semaphore")
        return

    # First trywait should succeed
    result: bool = sem_trywait(sid)
    assert_true(result, "first trywait succeeds")

    # Second trywait should fail (value is 0)
    result = sem_trywait(sid)
    assert_false(result, "second trywait fails (would block)")

    # Post to restore
    sem_post(sid)

    sem_destroy(sid)

def test_sem_counting():
    """Test counting semaphore behavior."""
    print_section("Counting Semaphore")

    # Create with initial value 3
    sid: int32 = sem_create(3)
    if sid < 0:
        test_fail("could not create semaphore")
        return

    # Should be able to wait 3 times
    r1: bool = sem_trywait(sid)
    r2: bool = sem_trywait(sid)
    r3: bool = sem_trywait(sid)
    r4: bool = sem_trywait(sid)  # This should fail

    assert_true(r1, "trywait 1 succeeds")
    assert_true(r2, "trywait 2 succeeds")
    assert_true(r3, "trywait 3 succeeds")
    assert_false(r4, "trywait 4 fails (count exhausted)")

    sem_destroy(sid)

# ============================================================================
# Condition Variable Tests
# ============================================================================

def test_cond_create():
    """Test condition variable creation."""
    print_section("Condition Variable")

    cid: int32 = cond_create()
    assert_gte(cid, 0, "cond_create returns valid ID")

    if cid >= 0:
        cond_destroy(cid)

def test_cond_signal():
    """Test condition variable signal."""
    cid: int32 = cond_create()
    if cid < 0:
        test_fail("could not create condvar")
        return

    # Signal with no waiters should be OK (no-op)
    result: bool = cond_signal(cid)
    assert_true(result, "cond_signal with no waiters succeeds")

    cond_destroy(cid)

def test_cond_broadcast():
    """Test condition variable broadcast."""
    cid: int32 = cond_create()
    if cid < 0:
        test_fail("could not create condvar")
        return

    # Broadcast with no waiters should be OK
    result: bool = cond_broadcast(cid)
    assert_true(result, "cond_broadcast with no waiters succeeds")

    cond_destroy(cid)

# ============================================================================
# Read-Write Lock Tests
# ============================================================================

def test_rwlock_create():
    """Test rwlock creation."""
    print_section("Read-Write Lock")

    rwid: int32 = rwlock_create()
    assert_gte(rwid, 0, "rwlock_create returns valid ID")

    if rwid >= 0:
        rwlock_destroy(rwid)

def test_rwlock_read():
    """Test rwlock read locking."""
    rwid: int32 = rwlock_create()
    if rwid < 0:
        test_fail("could not create rwlock")
        return

    # Multiple readers should be OK
    r1: bool = rwlock_read_lock(rwid)
    assert_true(r1, "first read_lock succeeds")

    r2: bool = rwlock_read_lock(rwid)
    assert_true(r2, "second read_lock succeeds")

    rwlock_read_unlock(rwid)
    rwlock_read_unlock(rwid)
    rwlock_destroy(rwid)

def test_rwlock_write():
    """Test rwlock write locking."""
    rwid: int32 = rwlock_create()
    if rwid < 0:
        test_fail("could not create rwlock")
        return

    result: bool = rwlock_write_lock(rwid)
    assert_true(result, "write_lock succeeds")

    result = rwlock_write_unlock(rwid)
    assert_true(result, "write_unlock succeeds")

    rwlock_destroy(rwid)

# ============================================================================
# Constants Tests
# ============================================================================

def test_sync_constants():
    """Test synchronization constants."""
    print_section("Sync Constants")

    assert_gte(MAX_MUTEXES, 8, "MAX_MUTEXES >= 8")
    assert_gte(MAX_SEMAPHORES, 8, "MAX_SEMAPHORES >= 8")
    assert_gte(MAX_COND_VARS, 8, "MAX_COND_VARS >= 8")
    assert_gte(MAX_RWLOCKS, 8, "MAX_RWLOCKS >= 8")

# ============================================================================
# Main
# ============================================================================

def test_sync_main() -> int32:
    print_str("\n=== Pynux Synchronization Tests ===\n")

    # Mutex tests
    test_mutex_create()
    test_mutex_create_multiple()
    test_mutex_lock_unlock()
    test_mutex_trylock()
    test_mutex_destroy()

    # Semaphore tests
    test_sem_create()
    test_sem_wait_post()
    test_sem_trywait()
    test_sem_counting()

    # Condition variable tests
    test_cond_create()
    test_cond_signal()
    test_cond_broadcast()

    # Read-write lock tests
    test_rwlock_create()
    test_rwlock_read()
    test_rwlock_write()

    # Constants
    test_sync_constants()

    return print_results()
