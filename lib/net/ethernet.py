# Pynux Ethernet Library
#
# Ethernet frame handling for bare-metal ARM Cortex-M3.
# Provides frame construction, transmission, and reception.
# Uses simulated loopback for testing.

from lib.memory import memset, memcpy, alloc, free

# ============================================================================
# Constants
# ============================================================================

# Ethernet frame limits
ETH_ADDR_LEN: int32 = 6         # MAC address length
ETH_HEADER_LEN: int32 = 14      # Ethernet header size
ETH_MIN_PAYLOAD: int32 = 46     # Minimum payload
ETH_MAX_PAYLOAD: int32 = 1500   # MTU
ETH_MIN_FRAME: int32 = 60       # Minimum frame size (excl. FCS)
ETH_MAX_FRAME: int32 = 1514     # Maximum frame size (excl. FCS)
ETH_FCS_LEN: int32 = 4          # Frame check sequence

# Common EtherTypes
ETHERTYPE_IPV4: uint16 = 0x0800
ETHERTYPE_ARP: uint16 = 0x0806
ETHERTYPE_IPV6: uint16 = 0x86DD
ETHERTYPE_VLAN: uint16 = 0x8100

# Broadcast MAC address
ETH_BROADCAST: Array[6, uint8] = [0xFF, 0xFF, 0xFF, 0xFF, 0xFF, 0xFF]

# ============================================================================
# Ethernet Frame Structure
# ============================================================================
#
# Standard Ethernet II frame layout:
#   dst_mac: 6 bytes  - Destination MAC address (offset 0)
#   src_mac: 6 bytes  - Source MAC address (offset 6)
#   ethertype: 2 bytes - EtherType/Length (offset 12)
#   payload: 46-1500 bytes - Data (offset 14)
#
# Header offsets
ETH_DST_OFFSET: int32 = 0
ETH_SRC_OFFSET: int32 = 6
ETH_TYPE_OFFSET: int32 = 12
ETH_PAYLOAD_OFFSET: int32 = 14

# ============================================================================
# State
# ============================================================================

# Local MAC address
_eth_mac: Array[6, uint8]
_eth_initialized: bool = False

# Loopback mode for testing
_eth_loopback: bool = True

# Loopback buffer (simulates network interface)
ETH_LOOPBACK_BUF_SIZE: int32 = 8192
_eth_loopback_buf: Array[8192, uint8]
_eth_loopback_head: int32 = 0
_eth_loopback_tail: int32 = 0
_eth_loopback_count: int32 = 0

# Maximum queued frames in loopback
MAX_LOOPBACK_FRAMES: int32 = 16

# Frame size prefix (2 bytes per frame)
_eth_frame_sizes: Array[16, int32]

# Statistics
_eth_tx_count: uint32 = 0
_eth_rx_count: uint32 = 0
_eth_tx_bytes: uint32 = 0
_eth_rx_bytes: uint32 = 0
_eth_errors: uint32 = 0

# ============================================================================
# Initialization
# ============================================================================

def eth_init(mac_addr: Ptr[uint8]):
    """Initialize Ethernet layer with MAC address.

    Args:
        mac_addr: Pointer to 6-byte MAC address
    """
    global _eth_initialized, _eth_loopback_head, _eth_loopback_tail, _eth_loopback_count
    global _eth_tx_count, _eth_rx_count, _eth_tx_bytes, _eth_rx_bytes, _eth_errors

    # Copy MAC address
    i: int32 = 0
    while i < ETH_ADDR_LEN:
        _eth_mac[i] = mac_addr[i]
        i = i + 1

    # Reset loopback buffer
    _eth_loopback_head = 0
    _eth_loopback_tail = 0
    _eth_loopback_count = 0

    # Reset statistics
    _eth_tx_count = 0
    _eth_rx_count = 0
    _eth_tx_bytes = 0
    _eth_rx_bytes = 0
    _eth_errors = 0

    _eth_initialized = True

def eth_get_mac() -> Ptr[uint8]:
    """Get pointer to local MAC address.

    Returns:
        Pointer to 6-byte MAC address
    """
    return &_eth_mac[0]

def eth_set_loopback(enabled: bool):
    """Enable or disable loopback mode for testing."""
    global _eth_loopback
    _eth_loopback = enabled

def eth_is_initialized() -> bool:
    """Check if Ethernet is initialized."""
    return _eth_initialized

# ============================================================================
# MAC Address Utilities
# ============================================================================

def eth_mac_cmp(a: Ptr[uint8], b: Ptr[uint8]) -> bool:
    """Compare two MAC addresses. Returns True if equal."""
    i: int32 = 0
    while i < ETH_ADDR_LEN:
        if a[i] != b[i]:
            return False
        i = i + 1
    return True

def eth_mac_copy(dst: Ptr[uint8], src: Ptr[uint8]):
    """Copy MAC address from src to dst."""
    i: int32 = 0
    while i < ETH_ADDR_LEN:
        dst[i] = src[i]
        i = i + 1

def eth_is_broadcast(mac: Ptr[uint8]) -> bool:
    """Check if MAC address is broadcast."""
    i: int32 = 0
    while i < ETH_ADDR_LEN:
        if mac[i] != 0xFF:
            return False
        i = i + 1
    return True

def eth_is_multicast(mac: Ptr[uint8]) -> bool:
    """Check if MAC address is multicast (group bit set)."""
    return (mac[0] & 0x01) != 0

def eth_is_local(mac: Ptr[uint8]) -> bool:
    """Check if MAC address is locally administered."""
    return (mac[0] & 0x02) != 0

# ============================================================================
# Frame Transmission
# ============================================================================

def eth_send(dst_mac: Ptr[uint8], ethertype: uint16, data: Ptr[uint8], length: int32) -> bool:
    """Send an Ethernet frame.

    Args:
        dst_mac: Destination MAC address (6 bytes)
        ethertype: EtherType field
        data: Pointer to payload data
        length: Length of payload (1-1500)

    Returns:
        True on success, False on failure
    """
    global _eth_tx_count, _eth_tx_bytes, _eth_errors
    global _eth_loopback_tail, _eth_loopback_count

    if not _eth_initialized:
        return False

    if length < 0 or length > ETH_MAX_PAYLOAD:
        _eth_errors = _eth_errors + 1
        return False

    # Calculate frame size (with padding if needed)
    payload_len: int32 = length
    if payload_len < ETH_MIN_PAYLOAD:
        payload_len = ETH_MIN_PAYLOAD

    frame_len: int32 = ETH_HEADER_LEN + payload_len

    # Build frame in loopback buffer (for testing)
    if _eth_loopback:
        if _eth_loopback_count >= MAX_LOOPBACK_FRAMES:
            _eth_errors = _eth_errors + 1
            return False  # Buffer full

        # Check if we have space
        space_needed: int32 = frame_len + 2  # +2 for length prefix
        space_available: int32 = ETH_LOOPBACK_BUF_SIZE - _eth_loopback_tail

        if space_available < space_needed:
            # Wrap around (simple implementation - just check if head is far enough)
            if _eth_loopback_head > frame_len + 2:
                _eth_loopback_tail = 0
            else:
                _eth_errors = _eth_errors + 1
                return False  # Not enough space

        # Store frame length first (as 2 bytes)
        frame_start: int32 = _eth_loopback_tail
        _eth_loopback_buf[frame_start] = cast[uint8](frame_len & 0xFF)
        _eth_loopback_buf[frame_start + 1] = cast[uint8]((frame_len >> 8) & 0xFF)

        # Build Ethernet header
        frame_data: int32 = frame_start + 2

        # Destination MAC
        i: int32 = 0
        while i < ETH_ADDR_LEN:
            _eth_loopback_buf[frame_data + i] = dst_mac[i]
            i = i + 1

        # Source MAC
        i = 0
        while i < ETH_ADDR_LEN:
            _eth_loopback_buf[frame_data + ETH_SRC_OFFSET + i] = _eth_mac[i]
            i = i + 1

        # EtherType (big-endian)
        _eth_loopback_buf[frame_data + ETH_TYPE_OFFSET] = cast[uint8]((ethertype >> 8) & 0xFF)
        _eth_loopback_buf[frame_data + ETH_TYPE_OFFSET + 1] = cast[uint8](ethertype & 0xFF)

        # Copy payload
        i = 0
        while i < length:
            _eth_loopback_buf[frame_data + ETH_PAYLOAD_OFFSET + i] = data[i]
            i = i + 1

        # Pad if necessary
        while i < payload_len:
            _eth_loopback_buf[frame_data + ETH_PAYLOAD_OFFSET + i] = 0
            i = i + 1

        # Store frame size for retrieval
        _eth_frame_sizes[_eth_loopback_count] = frame_len

        _eth_loopback_tail = frame_start + 2 + frame_len
        _eth_loopback_count = _eth_loopback_count + 1

    _eth_tx_count = _eth_tx_count + 1
    _eth_tx_bytes = _eth_tx_bytes + cast[uint32](frame_len)

    return True

# ============================================================================
# Frame Reception
# ============================================================================

def eth_receive(buf: Ptr[uint8], maxlen: int32) -> int32:
    """Receive an Ethernet frame.

    Args:
        buf: Buffer to receive frame
        maxlen: Maximum buffer size

    Returns:
        Frame length on success, 0 if no frame available, -1 on error
    """
    global _eth_rx_count, _eth_rx_bytes
    global _eth_loopback_head, _eth_loopback_count

    if not _eth_initialized:
        return -1

    if _eth_loopback:
        if _eth_loopback_count == 0:
            return 0  # No frames available

        # Read frame length
        frame_len: int32 = cast[int32](_eth_loopback_buf[_eth_loopback_head])
        frame_len = frame_len | (cast[int32](_eth_loopback_buf[_eth_loopback_head + 1]) << 8)

        if frame_len > maxlen:
            # Frame too large for buffer
            # Skip this frame
            _eth_loopback_head = _eth_loopback_head + 2 + frame_len
            _eth_loopback_count = _eth_loopback_count - 1
            return -1

        # Copy frame to buffer
        frame_data: int32 = _eth_loopback_head + 2
        i: int32 = 0
        while i < frame_len:
            buf[i] = _eth_loopback_buf[frame_data + i]
            i = i + 1

        # Advance head
        _eth_loopback_head = _eth_loopback_head + 2 + frame_len
        _eth_loopback_count = _eth_loopback_count - 1

        # Reset if buffer is empty
        if _eth_loopback_count == 0:
            _eth_loopback_head = 0
            _eth_loopback_tail = 0

        _eth_rx_count = _eth_rx_count + 1
        _eth_rx_bytes = _eth_rx_bytes + cast[uint32](frame_len)

        return frame_len

    return 0

def eth_available() -> int32:
    """Get number of frames waiting to be received."""
    return _eth_loopback_count

# ============================================================================
# Frame Parsing Utilities
# ============================================================================

def eth_get_dst(frame: Ptr[uint8]) -> Ptr[uint8]:
    """Get destination MAC from frame."""
    return &frame[ETH_DST_OFFSET]

def eth_get_src(frame: Ptr[uint8]) -> Ptr[uint8]:
    """Get source MAC from frame."""
    return &frame[ETH_SRC_OFFSET]

def eth_get_ethertype(frame: Ptr[uint8]) -> uint16:
    """Get EtherType from frame."""
    high: uint16 = cast[uint16](frame[ETH_TYPE_OFFSET])
    low: uint16 = cast[uint16](frame[ETH_TYPE_OFFSET + 1])
    return (high << 8) | low

def eth_get_payload(frame: Ptr[uint8]) -> Ptr[uint8]:
    """Get payload pointer from frame."""
    return &frame[ETH_PAYLOAD_OFFSET]

def eth_is_for_us(frame: Ptr[uint8]) -> bool:
    """Check if frame is addressed to us (unicast or broadcast)."""
    dst: Ptr[uint8] = eth_get_dst(frame)
    if eth_is_broadcast(dst):
        return True
    return eth_mac_cmp(dst, &_eth_mac[0])

# ============================================================================
# Statistics
# ============================================================================

def eth_get_tx_count() -> uint32:
    """Get transmitted frame count."""
    return _eth_tx_count

def eth_get_rx_count() -> uint32:
    """Get received frame count."""
    return _eth_rx_count

def eth_get_tx_bytes() -> uint32:
    """Get transmitted byte count."""
    return _eth_tx_bytes

def eth_get_rx_bytes() -> uint32:
    """Get received byte count."""
    return _eth_rx_bytes

def eth_get_errors() -> uint32:
    """Get error count."""
    return _eth_errors

def eth_clear_stats():
    """Clear all statistics."""
    global _eth_tx_count, _eth_rx_count, _eth_tx_bytes, _eth_rx_bytes, _eth_errors
    _eth_tx_count = 0
    _eth_rx_count = 0
    _eth_tx_bytes = 0
    _eth_rx_bytes = 0
    _eth_errors = 0

# ============================================================================
# Debug/Testing
# ============================================================================

def eth_inject_frame(frame: Ptr[uint8], length: int32) -> bool:
    """Inject a raw frame into the receive queue (for testing).

    Args:
        frame: Complete Ethernet frame
        length: Frame length

    Returns:
        True on success
    """
    global _eth_loopback_tail, _eth_loopback_count

    if not _eth_initialized:
        return False

    if length < ETH_HEADER_LEN or length > ETH_MAX_FRAME:
        return False

    if _eth_loopback_count >= MAX_LOOPBACK_FRAMES:
        return False

    # Store in loopback buffer
    frame_start: int32 = _eth_loopback_tail
    _eth_loopback_buf[frame_start] = cast[uint8](length & 0xFF)
    _eth_loopback_buf[frame_start + 1] = cast[uint8]((length >> 8) & 0xFF)

    i: int32 = 0
    while i < length:
        _eth_loopback_buf[frame_start + 2 + i] = frame[i]
        i = i + 1

    _eth_loopback_tail = frame_start + 2 + length
    _eth_loopback_count = _eth_loopback_count + 1

    return True

def eth_flush():
    """Flush all pending frames from the loopback buffer."""
    global _eth_loopback_head, _eth_loopback_tail, _eth_loopback_count
    _eth_loopback_head = 0
    _eth_loopback_tail = 0
    _eth_loopback_count = 0
