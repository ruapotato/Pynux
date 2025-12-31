# Pynux Events Library
#
# Event/callback system for bare-metal ARM Cortex-M3.
# Supports event registration, emission, priority handlers,
# one-shot vs persistent handlers, and event queues.
#
# Max 16 event types, 8 handlers per event.

from lib.memory import memset

# ============================================================================
# Constants
# ============================================================================

MAX_EVENT_TYPES: int32 = 16
MAX_HANDLERS_PER_EVENT: int32 = 8
MAX_QUEUED_EVENTS: int32 = 32

# Handler flags
HANDLER_FLAG_ACTIVE: uint32 = 0x01
HANDLER_FLAG_ONESHOT: uint32 = 0x02

# Event queue entry size (event_id + data)
EVENT_QUEUE_ENTRY_SIZE: int32 = 8

# Priority levels (lower = higher priority)
PRIORITY_HIGH: int32 = 0
PRIORITY_NORMAL: int32 = 4
PRIORITY_LOW: int32 = 7

# ============================================================================
# Handler Structure
# ============================================================================
#
# Each handler entry:
#   callback: Ptr[fn(int32, int32)]  - Callback function (event_id, data) (offset 0)
#   priority: int32                   - Priority level 0-7 (offset 4)
#   flags: uint32                     - HANDLER_FLAG_* (offset 8)
# Total: 12 bytes per handler

HANDLER_CALLBACK_OFFSET: int32 = 0
HANDLER_PRIORITY_OFFSET: int32 = 4
HANDLER_FLAGS_OFFSET: int32 = 8
HANDLER_SIZE: int32 = 12

# ============================================================================
# Event Storage
# ============================================================================

# Handler storage: 16 events * 8 handlers * 12 bytes = 1536 bytes
_event_handlers: Array[1536, uint8]

# Handler counts per event type
_handler_counts: Array[16, int32]

# Event queue for deferred processing
# Each entry: event_id (int32) + data (int32) = 8 bytes
_event_queue: Array[256, uint8]  # 32 entries * 8 bytes
_queue_head: int32 = 0
_queue_tail: int32 = 0
_queue_count: int32 = 0

# Initialization flag
_events_initialized: bool = False

# ============================================================================
# Internal Helper Functions
# ============================================================================

def _get_handler_ptr(event_id: int32, handler_idx: int32) -> Ptr[int32]:
    """Get pointer to handler entry."""
    base_offset: int32 = (event_id * MAX_HANDLERS_PER_EVENT * HANDLER_SIZE) + (handler_idx * HANDLER_SIZE)
    return cast[Ptr[int32]](&_event_handlers[base_offset])

def _find_free_handler_slot(event_id: int32) -> int32:
    """Find free handler slot for event. Returns -1 if none available."""
    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return -1

    i: int32 = 0
    while i < MAX_HANDLERS_PER_EVENT:
        handler: Ptr[int32] = _get_handler_ptr(event_id, i)
        flags: uint32 = cast[uint32](handler[2])
        if (flags & HANDLER_FLAG_ACTIVE) == 0:
            return i
        i = i + 1
    return -1

def _find_handler_by_callback(event_id: int32, callback: Ptr[int32]) -> int32:
    """Find handler slot by callback address. Returns -1 if not found."""
    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return -1

    i: int32 = 0
    while i < MAX_HANDLERS_PER_EVENT:
        handler: Ptr[int32] = _get_handler_ptr(event_id, i)
        flags: uint32 = cast[uint32](handler[2])
        if (flags & HANDLER_FLAG_ACTIVE) != 0:
            if handler[0] == cast[int32](callback):
                return i
        i = i + 1
    return -1

def _sort_handlers_by_priority(event_id: int32):
    """Sort handlers by priority (bubble sort, low priority value = high priority)."""
    count: int32 = _handler_counts[event_id]
    if count <= 1:
        return

    # Simple bubble sort
    i: int32 = 0
    while i < count - 1:
        j: int32 = 0
        while j < count - i - 1:
            h1: Ptr[int32] = _get_handler_ptr(event_id, j)
            h2: Ptr[int32] = _get_handler_ptr(event_id, j + 1)

            # Only compare active handlers
            if (cast[uint32](h1[2]) & HANDLER_FLAG_ACTIVE) != 0:
                if (cast[uint32](h2[2]) & HANDLER_FLAG_ACTIVE) != 0:
                    if h1[1] > h2[1]:  # Compare priorities
                        # Swap
                        tmp0: int32 = h1[0]
                        tmp1: int32 = h1[1]
                        tmp2: int32 = h1[2]
                        h1[0] = h2[0]
                        h1[1] = h2[1]
                        h1[2] = h2[2]
                        h2[0] = tmp0
                        h2[1] = tmp1
                        h2[2] = tmp2
            j = j + 1
        i = i + 1

# ============================================================================
# Initialization
# ============================================================================

def events_init():
    """Initialize the event system."""
    global _events_initialized, _queue_head, _queue_tail, _queue_count

    # Clear all handler storage
    memset(&_event_handlers[0], 0, 1536)

    # Clear handler counts
    i: int32 = 0
    while i < MAX_EVENT_TYPES:
        _handler_counts[i] = 0
        i = i + 1

    # Clear event queue
    _queue_head = 0
    _queue_tail = 0
    _queue_count = 0

    _events_initialized = True

# ============================================================================
# Event Registration
# ============================================================================

def event_subscribe(event_id: int32, callback: Ptr[int32], priority: int32) -> bool:
    """Subscribe to an event with priority. Returns True on success.

    Args:
        event_id: Event type (0 to MAX_EVENT_TYPES-1)
        callback: Function pointer fn(event_id: int32, data: int32)
        priority: Priority level (0=highest, 7=lowest)
    """
    global _events_initialized
    if not _events_initialized:
        events_init()

    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return False

    if priority < 0:
        priority = 0
    if priority > 7:
        priority = 7

    # Find free slot
    slot: int32 = _find_free_handler_slot(event_id)
    if slot < 0:
        return False

    # Set up handler
    handler: Ptr[int32] = _get_handler_ptr(event_id, slot)
    handler[0] = cast[int32](callback)
    handler[1] = priority
    handler[2] = cast[int32](HANDLER_FLAG_ACTIVE)

    _handler_counts[event_id] = _handler_counts[event_id] + 1

    # Keep handlers sorted by priority
    _sort_handlers_by_priority(event_id)

    return True

def event_subscribe_once(event_id: int32, callback: Ptr[int32], priority: int32) -> bool:
    """Subscribe to an event for one-shot handling (auto-unsubscribe after first call).

    Args:
        event_id: Event type (0 to MAX_EVENT_TYPES-1)
        callback: Function pointer fn(event_id: int32, data: int32)
        priority: Priority level (0=highest, 7=lowest)
    """
    global _events_initialized
    if not _events_initialized:
        events_init()

    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return False

    if priority < 0:
        priority = 0
    if priority > 7:
        priority = 7

    # Find free slot
    slot: int32 = _find_free_handler_slot(event_id)
    if slot < 0:
        return False

    # Set up handler with oneshot flag
    handler: Ptr[int32] = _get_handler_ptr(event_id, slot)
    handler[0] = cast[int32](callback)
    handler[1] = priority
    handler[2] = cast[int32](HANDLER_FLAG_ACTIVE | HANDLER_FLAG_ONESHOT)

    _handler_counts[event_id] = _handler_counts[event_id] + 1

    _sort_handlers_by_priority(event_id)

    return True

def event_unsubscribe(event_id: int32, callback: Ptr[int32]) -> bool:
    """Unsubscribe from an event. Returns True if handler was found and removed."""
    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return False

    slot: int32 = _find_handler_by_callback(event_id, callback)
    if slot < 0:
        return False

    # Clear handler slot
    handler: Ptr[int32] = _get_handler_ptr(event_id, slot)
    handler[0] = 0
    handler[1] = 0
    handler[2] = 0

    _handler_counts[event_id] = _handler_counts[event_id] - 1

    return True

def event_unsubscribe_all(event_id: int32):
    """Unsubscribe all handlers from an event."""
    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return

    i: int32 = 0
    while i < MAX_HANDLERS_PER_EVENT:
        handler: Ptr[int32] = _get_handler_ptr(event_id, i)
        handler[0] = 0
        handler[1] = 0
        handler[2] = 0
        i = i + 1

    _handler_counts[event_id] = 0

# ============================================================================
# Event Emission
# ============================================================================

def event_emit(event_id: int32, data: int32):
    """Emit an event immediately, calling all registered handlers.

    Handlers are called in priority order (low value = high priority).
    One-shot handlers are automatically unsubscribed after being called.

    Args:
        event_id: Event type to emit
        data: Event data to pass to handlers
    """
    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return

    # Call handlers in order (already sorted by priority)
    i: int32 = 0
    while i < MAX_HANDLERS_PER_EVENT:
        handler: Ptr[int32] = _get_handler_ptr(event_id, i)
        flags: uint32 = cast[uint32](handler[2])

        if (flags & HANDLER_FLAG_ACTIVE) != 0:
            # Get callback and call it
            callback_addr: int32 = handler[0]
            if callback_addr != 0:
                # Cast to function pointer and call
                # fn(event_id: int32, data: int32)
                callback: Ptr[fn(int32, int32)] = cast[Ptr[fn(int32, int32)]](callback_addr)
                callback[0](event_id, data)

                # Remove one-shot handlers after calling
                if (flags & HANDLER_FLAG_ONESHOT) != 0:
                    handler[0] = 0
                    handler[1] = 0
                    handler[2] = 0
                    _handler_counts[event_id] = _handler_counts[event_id] - 1

        i = i + 1

def event_emit_to_priority(event_id: int32, data: int32, max_priority: int32):
    """Emit event only to handlers at or above given priority level.

    Args:
        event_id: Event type to emit
        data: Event data to pass to handlers
        max_priority: Maximum priority level to call (0-7, lower = higher priority)
    """
    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return

    i: int32 = 0
    while i < MAX_HANDLERS_PER_EVENT:
        handler: Ptr[int32] = _get_handler_ptr(event_id, i)
        flags: uint32 = cast[uint32](handler[2])

        if (flags & HANDLER_FLAG_ACTIVE) != 0:
            # Check priority
            if handler[1] <= max_priority:
                callback_addr: int32 = handler[0]
                if callback_addr != 0:
                    callback: Ptr[fn(int32, int32)] = cast[Ptr[fn(int32, int32)]](callback_addr)
                    callback[0](event_id, data)

                    if (flags & HANDLER_FLAG_ONESHOT) != 0:
                        handler[0] = 0
                        handler[1] = 0
                        handler[2] = 0
                        _handler_counts[event_id] = _handler_counts[event_id] - 1

        i = i + 1

# ============================================================================
# Event Queue (Deferred Processing)
# ============================================================================

def event_queue(event_id: int32, data: int32) -> bool:
    """Queue an event for deferred processing. Returns True on success.

    Use event_process() to process queued events later.
    """
    global _queue_tail, _queue_count

    if _queue_count >= MAX_QUEUED_EVENTS:
        return False  # Queue full

    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return False

    # Add to queue
    entry_offset: int32 = _queue_tail * EVENT_QUEUE_ENTRY_SIZE
    entry: Ptr[int32] = cast[Ptr[int32]](&_event_queue[entry_offset])
    entry[0] = event_id
    entry[1] = data

    _queue_tail = (_queue_tail + 1) % MAX_QUEUED_EVENTS
    _queue_count = _queue_count + 1

    return True

def event_process() -> int32:
    """Process all queued events. Returns number of events processed."""
    global _queue_head, _queue_count

    processed: int32 = 0

    while _queue_count > 0:
        # Get event from queue
        entry_offset: int32 = _queue_head * EVENT_QUEUE_ENTRY_SIZE
        entry: Ptr[int32] = cast[Ptr[int32]](&_event_queue[entry_offset])
        event_id: int32 = entry[0]
        data: int32 = entry[1]

        _queue_head = (_queue_head + 1) % MAX_QUEUED_EVENTS
        _queue_count = _queue_count - 1

        # Emit the event
        event_emit(event_id, data)
        processed = processed + 1

    return processed

def event_process_one() -> bool:
    """Process one queued event. Returns True if an event was processed."""
    global _queue_head, _queue_count

    if _queue_count == 0:
        return False

    # Get event from queue
    entry_offset: int32 = _queue_head * EVENT_QUEUE_ENTRY_SIZE
    entry: Ptr[int32] = cast[Ptr[int32]](&_event_queue[entry_offset])
    event_id: int32 = entry[0]
    data: int32 = entry[1]

    _queue_head = (_queue_head + 1) % MAX_QUEUED_EVENTS
    _queue_count = _queue_count - 1

    event_emit(event_id, data)
    return True

def event_queue_count() -> int32:
    """Get number of events in queue."""
    return _queue_count

def event_queue_clear():
    """Clear all queued events without processing them."""
    global _queue_head, _queue_tail, _queue_count
    _queue_head = 0
    _queue_tail = 0
    _queue_count = 0

# ============================================================================
# Query Functions
# ============================================================================

def event_handler_count(event_id: int32) -> int32:
    """Get number of handlers registered for an event."""
    if event_id < 0 or event_id >= MAX_EVENT_TYPES:
        return 0
    return _handler_counts[event_id]

def event_has_handlers(event_id: int32) -> bool:
    """Check if an event has any handlers registered."""
    return event_handler_count(event_id) > 0

def event_is_subscribed(event_id: int32, callback: Ptr[int32]) -> bool:
    """Check if a callback is subscribed to an event."""
    return _find_handler_by_callback(event_id, callback) >= 0

# ============================================================================
# Utility Functions
# ============================================================================

def events_clear_all():
    """Clear all event handlers and queued events."""
    events_init()
