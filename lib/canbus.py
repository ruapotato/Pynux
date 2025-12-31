# Pynux CAN Bus Library
#
# CAN Bus emulation for bare-metal ARM Cortex-M3.
# Provides standard/extended ID support, message queuing,
# filtering, and loopback mode for testing.
#
# Note: This is an emulation layer - no real CAN hardware.

from lib.memory import memset, memcpy

# ============================================================================
# Constants
# ============================================================================

# CAN bitrate presets (values represent divisor for timing calculations)
CAN_BITRATE_125K: uint32 = 125000
CAN_BITRATE_250K: uint32 = 250000
CAN_BITRATE_500K: uint32 = 500000
CAN_BITRATE_1M: uint32 = 1000000

# CAN frame flags
CAN_FLAG_EXTENDED: uint32 = 0x80000000   # Extended 29-bit ID
CAN_FLAG_RTR: uint32 = 0x40000000        # Remote transmission request
CAN_FLAG_ERROR: uint32 = 0x20000000      # Error frame

# Standard ID mask (11 bits)
CAN_STD_ID_MASK: uint32 = 0x7FF

# Extended ID mask (29 bits)
CAN_EXT_ID_MASK: uint32 = 0x1FFFFFFF

# Maximum data length
CAN_MAX_DATA_LEN: int32 = 8

# Queue sizes
CAN_TX_QUEUE_SIZE: int32 = 16
CAN_RX_QUEUE_SIZE: int32 = 32

# Filter modes
CAN_FILTER_DISABLED: int32 = 0
CAN_FILTER_MASK: int32 = 1      # ID & mask == filter & mask
CAN_FILTER_LIST: int32 = 2      # ID matches one of list entries

# Maximum filters
MAX_CAN_FILTERS: int32 = 8

# Return codes
CAN_OK: int32 = 0
CAN_ERR_FULL: int32 = -1
CAN_ERR_EMPTY: int32 = -2
CAN_ERR_INVALID: int32 = -3
CAN_ERR_NOT_INIT: int32 = -4

# ============================================================================
# CAN Message Structure
# ============================================================================
#
# Message layout:
#   id: uint32        - CAN ID with flags (offset 0)
#   length: int32     - Data length 0-8 (offset 4)
#   data: Array[8]    - Data bytes (offset 8)
#   timestamp: uint32 - Reception timestamp (offset 16)
# Total: 20 bytes

CAN_MSG_ID_OFFSET: int32 = 0
CAN_MSG_LEN_OFFSET: int32 = 4
CAN_MSG_DATA_OFFSET: int32 = 8
CAN_MSG_TIME_OFFSET: int32 = 16
CAN_MSG_SIZE: int32 = 20

# ============================================================================
# CAN Filter Structure
# ============================================================================
#
# Filter layout:
#   mode: int32       - Filter mode (offset 0)
#   id: uint32        - Filter ID (offset 4)
#   mask: uint32      - Filter mask (offset 8)
#   enabled: bool     - Filter enabled (offset 12)
# Total: 16 bytes

CAN_FILTER_MODE_OFFSET: int32 = 0
CAN_FILTER_ID_OFFSET: int32 = 4
CAN_FILTER_MASK_OFFSET: int32 = 8
CAN_FILTER_ENABLED_OFFSET: int32 = 12
CAN_FILTER_SIZE: int32 = 16

# ============================================================================
# CAN State
# ============================================================================

# Initialization state
_can_initialized: bool = False
_can_bitrate: uint32 = 0
_can_loopback: bool = False

# TX queue: 16 messages * 20 bytes = 320 bytes
_can_tx_queue: Array[320, uint8]
_can_tx_head: int32 = 0
_can_tx_tail: int32 = 0
_can_tx_count: int32 = 0

# RX queue: 32 messages * 20 bytes = 640 bytes
_can_rx_queue: Array[640, uint8]
_can_rx_head: int32 = 0
_can_rx_tail: int32 = 0
_can_rx_count: int32 = 0

# Filters: 8 filters * 16 bytes = 128 bytes
_can_filters: Array[128, uint8]
_can_filter_count: int32 = 0

# Statistics
_can_tx_count_total: uint32 = 0
_can_rx_count_total: uint32 = 0
_can_error_count: uint32 = 0

# Timestamp counter (emulated)
_can_timestamp: uint32 = 0

# ============================================================================
# Internal Helper Functions
# ============================================================================

def _can_get_tx_msg(index: int32) -> Ptr[uint8]:
    """Get pointer to TX queue message."""
    return &_can_tx_queue[index * CAN_MSG_SIZE]

def _can_get_rx_msg(index: int32) -> Ptr[uint8]:
    """Get pointer to RX queue message."""
    return &_can_rx_queue[index * CAN_MSG_SIZE]

def _can_get_filter(index: int32) -> Ptr[int32]:
    """Get pointer to filter entry."""
    return cast[Ptr[int32]](&_can_filters[index * CAN_FILTER_SIZE])

def _can_check_filter(id: uint32) -> bool:
    """Check if message ID passes filters. Returns True if accepted."""
    # If no filters enabled, accept all
    has_enabled: bool = False
    i: int32 = 0
    while i < MAX_CAN_FILTERS:
        filt: Ptr[int32] = _can_get_filter(i)
        if filt[3] != 0:  # enabled
            has_enabled = True
            break
        i = i + 1

    if not has_enabled:
        return True

    # Check each enabled filter
    i = 0
    while i < MAX_CAN_FILTERS:
        filt: Ptr[int32] = _can_get_filter(i)
        if filt[3] != 0:  # enabled
            mode: int32 = filt[0]
            filt_id: uint32 = cast[uint32](filt[1])
            mask: uint32 = cast[uint32](filt[2])

            # Extract just the ID portion (remove flags)
            msg_id: uint32 = id & CAN_EXT_ID_MASK

            if mode == CAN_FILTER_MASK:
                if (msg_id & mask) == (filt_id & mask):
                    return True
            elif mode == CAN_FILTER_LIST:
                if msg_id == filt_id:
                    return True
        i = i + 1

    return False

def _can_copy_msg(dst: Ptr[uint8], src: Ptr[uint8]):
    """Copy CAN message."""
    memcpy(dst, src, CAN_MSG_SIZE)

# ============================================================================
# Initialization
# ============================================================================

def can_init(bitrate: uint32) -> int32:
    """Initialize CAN bus with specified bitrate.

    Args:
        bitrate: Bitrate in bps (e.g., CAN_BITRATE_500K)

    Returns:
        CAN_OK on success
    """
    global _can_initialized, _can_bitrate, _can_loopback
    global _can_tx_head, _can_tx_tail, _can_tx_count
    global _can_rx_head, _can_rx_tail, _can_rx_count
    global _can_filter_count, _can_timestamp
    global _can_tx_count_total, _can_rx_count_total, _can_error_count

    _can_bitrate = bitrate
    _can_loopback = False

    # Clear queues
    _can_tx_head = 0
    _can_tx_tail = 0
    _can_tx_count = 0
    _can_rx_head = 0
    _can_rx_tail = 0
    _can_rx_count = 0

    # Clear filters
    memset(&_can_filters[0], 0, 128)
    _can_filter_count = 0

    # Reset statistics
    _can_tx_count_total = 0
    _can_rx_count_total = 0
    _can_error_count = 0
    _can_timestamp = 0

    _can_initialized = True
    return CAN_OK

def can_deinit():
    """Deinitialize CAN bus."""
    global _can_initialized
    _can_initialized = False

def can_set_loopback(enabled: bool):
    """Enable/disable loopback mode for testing.

    In loopback mode, transmitted messages are received back.
    """
    global _can_loopback
    _can_loopback = enabled

def can_is_initialized() -> bool:
    """Check if CAN is initialized."""
    return _can_initialized

# ============================================================================
# Message Transmission
# ============================================================================

def can_send(id: uint32, data: Ptr[uint8], length: int32) -> int32:
    """Send a standard CAN message.

    Args:
        id: 11-bit standard CAN ID
        data: Pointer to data bytes
        length: Number of data bytes (0-8)

    Returns:
        CAN_OK on success, error code on failure
    """
    return can_send_ext(id & CAN_STD_ID_MASK, data, length, False)

def can_send_ext(id: uint32, data: Ptr[uint8], length: int32, extended: bool) -> int32:
    """Send a CAN message with extended ID option.

    Args:
        id: CAN ID (11-bit standard or 29-bit extended)
        data: Pointer to data bytes
        length: Number of data bytes (0-8)
        extended: True for 29-bit extended ID

    Returns:
        CAN_OK on success, error code on failure
    """
    global _can_tx_tail, _can_tx_count, _can_tx_count_total, _can_timestamp

    if not _can_initialized:
        return CAN_ERR_NOT_INIT

    if _can_tx_count >= CAN_TX_QUEUE_SIZE:
        return CAN_ERR_FULL

    if length < 0:
        length = 0
    if length > CAN_MAX_DATA_LEN:
        length = CAN_MAX_DATA_LEN

    # Build message
    msg: Ptr[uint8] = _can_get_tx_msg(_can_tx_tail)
    msg_ptr: Ptr[int32] = cast[Ptr[int32]](msg)

    # Set ID with flags
    msg_id: uint32 = id
    if extended:
        msg_id = (id & CAN_EXT_ID_MASK) | CAN_FLAG_EXTENDED
    else:
        msg_id = id & CAN_STD_ID_MASK

    msg_ptr[0] = cast[int32](msg_id)
    msg_ptr[1] = length

    # Copy data
    i: int32 = 0
    while i < length:
        msg[CAN_MSG_DATA_OFFSET + i] = data[i]
        i = i + 1

    # Set timestamp
    msg_ptr[4] = cast[int32](_can_timestamp)
    _can_timestamp = _can_timestamp + 1

    _can_tx_tail = (_can_tx_tail + 1) % CAN_TX_QUEUE_SIZE
    _can_tx_count = _can_tx_count + 1
    _can_tx_count_total = _can_tx_count_total + 1

    # In loopback mode, also add to RX queue
    if _can_loopback:
        _can_loopback_msg(msg)

    return CAN_OK

def can_send_rtr(id: uint32, length: int32, extended: bool) -> int32:
    """Send a Remote Transmission Request (RTR) frame.

    Args:
        id: CAN ID
        length: Requested data length
        extended: True for extended ID

    Returns:
        CAN_OK on success, error code on failure
    """
    global _can_tx_tail, _can_tx_count, _can_tx_count_total, _can_timestamp

    if not _can_initialized:
        return CAN_ERR_NOT_INIT

    if _can_tx_count >= CAN_TX_QUEUE_SIZE:
        return CAN_ERR_FULL

    msg: Ptr[uint8] = _can_get_tx_msg(_can_tx_tail)
    msg_ptr: Ptr[int32] = cast[Ptr[int32]](msg)

    msg_id: uint32 = id | CAN_FLAG_RTR
    if extended:
        msg_id = msg_id | CAN_FLAG_EXTENDED

    msg_ptr[0] = cast[int32](msg_id)
    msg_ptr[1] = length
    msg_ptr[4] = cast[int32](_can_timestamp)
    _can_timestamp = _can_timestamp + 1

    _can_tx_tail = (_can_tx_tail + 1) % CAN_TX_QUEUE_SIZE
    _can_tx_count = _can_tx_count + 1
    _can_tx_count_total = _can_tx_count_total + 1

    return CAN_OK

def _can_loopback_msg(msg: Ptr[uint8]):
    """Internal: Add message to RX queue for loopback."""
    global _can_rx_tail, _can_rx_count, _can_rx_count_total

    if _can_rx_count >= CAN_RX_QUEUE_SIZE:
        return  # RX queue full, drop

    msg_ptr: Ptr[int32] = cast[Ptr[int32]](msg)
    msg_id: uint32 = cast[uint32](msg_ptr[0])

    # Check filters
    if not _can_check_filter(msg_id):
        return

    rx_msg: Ptr[uint8] = _can_get_rx_msg(_can_rx_tail)
    _can_copy_msg(rx_msg, msg)

    _can_rx_tail = (_can_rx_tail + 1) % CAN_RX_QUEUE_SIZE
    _can_rx_count = _can_rx_count + 1
    _can_rx_count_total = _can_rx_count_total + 1

# ============================================================================
# Message Reception
# ============================================================================

def can_receive(id_out: Ptr[uint32], data_out: Ptr[uint8], len_out: Ptr[int32]) -> int32:
    """Receive a CAN message from the queue.

    Args:
        id_out: Output for message ID (with flags)
        data_out: Output buffer for data (8 bytes)
        len_out: Output for data length

    Returns:
        CAN_OK on success, CAN_ERR_EMPTY if no message
    """
    global _can_rx_head, _can_rx_count

    if not _can_initialized:
        return CAN_ERR_NOT_INIT

    if _can_rx_count == 0:
        return CAN_ERR_EMPTY

    msg: Ptr[uint8] = _can_get_rx_msg(_can_rx_head)
    msg_ptr: Ptr[int32] = cast[Ptr[int32]](msg)

    id_out[0] = cast[uint32](msg_ptr[0])
    len_out[0] = msg_ptr[1]

    # Copy data
    length: int32 = msg_ptr[1]
    i: int32 = 0
    while i < length:
        data_out[i] = msg[CAN_MSG_DATA_OFFSET + i]
        i = i + 1

    _can_rx_head = (_can_rx_head + 1) % CAN_RX_QUEUE_SIZE
    _can_rx_count = _can_rx_count - 1

    return CAN_OK

def can_peek(id_out: Ptr[uint32], data_out: Ptr[uint8], len_out: Ptr[int32]) -> int32:
    """Peek at next CAN message without removing from queue."""
    if not _can_initialized:
        return CAN_ERR_NOT_INIT

    if _can_rx_count == 0:
        return CAN_ERR_EMPTY

    msg: Ptr[uint8] = _can_get_rx_msg(_can_rx_head)
    msg_ptr: Ptr[int32] = cast[Ptr[int32]](msg)

    id_out[0] = cast[uint32](msg_ptr[0])
    len_out[0] = msg_ptr[1]

    length: int32 = msg_ptr[1]
    i: int32 = 0
    while i < length:
        data_out[i] = msg[CAN_MSG_DATA_OFFSET + i]
        i = i + 1

    return CAN_OK

def can_available() -> int32:
    """Get number of messages waiting in RX queue."""
    return _can_rx_count

def can_tx_pending() -> int32:
    """Get number of messages waiting in TX queue."""
    return _can_tx_count

# ============================================================================
# Message Filtering
# ============================================================================

def can_filter_add(id: uint32, mask: uint32, extended: bool) -> int32:
    """Add a mask-based filter.

    Messages pass if (msg_id & mask) == (filter_id & mask)

    Args:
        id: Filter ID
        mask: Filter mask
        extended: True if filtering extended IDs

    Returns:
        Filter index (0-7) on success, CAN_ERR_FULL if no slots
    """
    global _can_filter_count

    if _can_filter_count >= MAX_CAN_FILTERS:
        return CAN_ERR_FULL

    # Find free slot
    i: int32 = 0
    while i < MAX_CAN_FILTERS:
        filt: Ptr[int32] = _can_get_filter(i)
        if filt[3] == 0:  # Not enabled
            filt[0] = CAN_FILTER_MASK
            filt[1] = cast[int32](id)
            filt[2] = cast[int32](mask)
            filt[3] = 1  # Enabled
            _can_filter_count = _can_filter_count + 1
            return i
        i = i + 1

    return CAN_ERR_FULL

def can_filter_add_id(id: uint32, extended: bool) -> int32:
    """Add an exact ID filter.

    Only messages with exactly this ID pass.

    Args:
        id: Exact ID to match
        extended: True if filtering extended IDs

    Returns:
        Filter index on success, CAN_ERR_FULL if no slots
    """
    global _can_filter_count

    if _can_filter_count >= MAX_CAN_FILTERS:
        return CAN_ERR_FULL

    i: int32 = 0
    while i < MAX_CAN_FILTERS:
        filt: Ptr[int32] = _can_get_filter(i)
        if filt[3] == 0:
            filt[0] = CAN_FILTER_LIST
            filt[1] = cast[int32](id)
            filt[2] = 0
            filt[3] = 1
            _can_filter_count = _can_filter_count + 1
            return i
        i = i + 1

    return CAN_ERR_FULL

def can_filter_remove(index: int32) -> int32:
    """Remove a filter by index."""
    global _can_filter_count

    if index < 0 or index >= MAX_CAN_FILTERS:
        return CAN_ERR_INVALID

    filt: Ptr[int32] = _can_get_filter(index)
    if filt[3] != 0:
        filt[0] = 0
        filt[1] = 0
        filt[2] = 0
        filt[3] = 0
        _can_filter_count = _can_filter_count - 1

    return CAN_OK

def can_filter_clear():
    """Remove all filters."""
    global _can_filter_count
    memset(&_can_filters[0], 0, 128)
    _can_filter_count = 0

def can_filter_count() -> int32:
    """Get number of active filters."""
    return _can_filter_count

# ============================================================================
# ID Helper Functions
# ============================================================================

def can_id_is_extended(id: uint32) -> bool:
    """Check if message ID has extended flag."""
    return (id & CAN_FLAG_EXTENDED) != 0

def can_id_is_rtr(id: uint32) -> bool:
    """Check if message ID has RTR flag."""
    return (id & CAN_FLAG_RTR) != 0

def can_id_is_error(id: uint32) -> bool:
    """Check if message ID has error flag."""
    return (id & CAN_FLAG_ERROR) != 0

def can_id_get(id: uint32) -> uint32:
    """Extract just the ID portion (without flags)."""
    if (id & CAN_FLAG_EXTENDED) != 0:
        return id & CAN_EXT_ID_MASK
    return id & CAN_STD_ID_MASK

def can_id_make_extended(id: uint32) -> uint32:
    """Make an extended ID with flag."""
    return (id & CAN_EXT_ID_MASK) | CAN_FLAG_EXTENDED

# ============================================================================
# Emulation Functions
# ============================================================================

def can_inject_message(id: uint32, data: Ptr[uint8], length: int32) -> int32:
    """Inject a message into the RX queue (for testing/emulation).

    Args:
        id: Message ID (with flags)
        data: Message data
        length: Data length

    Returns:
        CAN_OK on success
    """
    global _can_rx_tail, _can_rx_count, _can_rx_count_total, _can_timestamp

    if not _can_initialized:
        return CAN_ERR_NOT_INIT

    if _can_rx_count >= CAN_RX_QUEUE_SIZE:
        return CAN_ERR_FULL

    # Check filters
    if not _can_check_filter(id):
        return CAN_OK  # Filtered out, but not an error

    msg: Ptr[uint8] = _can_get_rx_msg(_can_rx_tail)
    msg_ptr: Ptr[int32] = cast[Ptr[int32]](msg)

    msg_ptr[0] = cast[int32](id)
    msg_ptr[1] = length

    i: int32 = 0
    while i < length and i < CAN_MAX_DATA_LEN:
        msg[CAN_MSG_DATA_OFFSET + i] = data[i]
        i = i + 1

    msg_ptr[4] = cast[int32](_can_timestamp)
    _can_timestamp = _can_timestamp + 1

    _can_rx_tail = (_can_rx_tail + 1) % CAN_RX_QUEUE_SIZE
    _can_rx_count = _can_rx_count + 1
    _can_rx_count_total = _can_rx_count_total + 1

    return CAN_OK

def can_process_tx() -> int32:
    """Process TX queue (simulates transmission). Returns messages processed."""
    global _can_tx_head, _can_tx_count

    processed: int32 = 0
    while _can_tx_count > 0:
        # In real hardware, this would transmit on bus
        # For emulation, just remove from queue
        _can_tx_head = (_can_tx_head + 1) % CAN_TX_QUEUE_SIZE
        _can_tx_count = _can_tx_count - 1
        processed = processed + 1

    return processed

# ============================================================================
# Statistics
# ============================================================================

def can_get_tx_total() -> uint32:
    """Get total transmitted message count."""
    return _can_tx_count_total

def can_get_rx_total() -> uint32:
    """Get total received message count."""
    return _can_rx_count_total

def can_get_error_count() -> uint32:
    """Get error count."""
    return _can_error_count

def can_clear_stats():
    """Clear statistics counters."""
    global _can_tx_count_total, _can_rx_count_total, _can_error_count
    _can_tx_count_total = 0
    _can_rx_count_total = 0
    _can_error_count = 0

def can_get_bitrate() -> uint32:
    """Get configured bitrate."""
    return _can_bitrate
