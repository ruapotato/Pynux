# Pynux UDP Library
#
# UDP protocol implementation for bare-metal ARM Cortex-M3.
# Provides connectionless datagram sockets.

from lib.memory import memset, memcpy
from lib.net.ip import ip_send, ip_receive_full, ip_checksum, ip_get_addr, ip_is_initialized
from lib.net.ip import IP_PROTO_UDP, ip_addr_to_ptr, ip_addr_from_ptr

# ============================================================================
# Constants
# ============================================================================

# UDP header size
UDP_HEADER_LEN: int32 = 8

# UDP header field offsets
UDP_SRC_PORT_OFFSET: int32 = 0   # Source port (2 bytes)
UDP_DST_PORT_OFFSET: int32 = 2   # Destination port (2 bytes)
UDP_LENGTH_OFFSET: int32 = 4     # Length (2 bytes)
UDP_CHECKSUM_OFFSET: int32 = 6   # Checksum (2 bytes)
UDP_DATA_OFFSET: int32 = 8       # Data starts here

# Maximum UDP payload (IP payload - UDP header)
UDP_MAX_PAYLOAD: int32 = 1472    # 1480 - 8

# Maximum sockets
MAX_UDP_SOCKETS: int32 = 8

# Socket states
UDP_SOCK_FREE: int32 = 0
UDP_SOCK_OPEN: int32 = 1
UDP_SOCK_BOUND: int32 = 2

# Receive buffer size per socket
UDP_RECV_BUF_SIZE: int32 = 2048

# ============================================================================
# UDP Socket Structure
# ============================================================================
#
# Socket layout:
#   state: int32        - Socket state (offset 0)
#   local_port: uint16  - Bound local port (offset 4)
#   recv_buf: Array     - Receive buffer (offset 8)
#   recv_head: int32    - Buffer read position (offset 2056)
#   recv_tail: int32    - Buffer write position (offset 2060)
#   recv_count: int32   - Bytes in buffer (offset 2064)
# Total: 2068 bytes per socket

UDP_SOCK_STATE_OFFSET: int32 = 0
UDP_SOCK_PORT_OFFSET: int32 = 4
UDP_SOCK_BUF_OFFSET: int32 = 8
UDP_SOCK_HEAD_OFFSET: int32 = 2056
UDP_SOCK_TAIL_OFFSET: int32 = 2060
UDP_SOCK_COUNT_OFFSET: int32 = 2064
UDP_SOCK_SIZE: int32 = 2068

# ============================================================================
# State
# ============================================================================

# Socket array: 8 sockets * 2068 bytes = 16544 bytes
_udp_sockets: Array[16544, uint8]
_udp_initialized: bool = False

# Statistics
_udp_tx_count: uint32 = 0
_udp_rx_count: uint32 = 0
_udp_errors: uint32 = 0

# ============================================================================
# Internal Helpers
# ============================================================================

def _udp_get_socket(sock: int32) -> Ptr[uint8]:
    """Get pointer to socket structure."""
    if sock < 0 or sock >= MAX_UDP_SOCKETS:
        return Ptr[uint8](0)
    return &_udp_sockets[sock * UDP_SOCK_SIZE]

def _udp_sock_get_state(s: Ptr[uint8]) -> int32:
    """Get socket state."""
    ptr: Ptr[int32] = cast[Ptr[int32]](s)
    return ptr[0]

def _udp_sock_set_state(s: Ptr[uint8], state: int32):
    """Set socket state."""
    ptr: Ptr[int32] = cast[Ptr[int32]](s)
    ptr[0] = state

def _udp_sock_get_port(s: Ptr[uint8]) -> uint16:
    """Get socket port."""
    ptr: Ptr[uint16] = cast[Ptr[uint16]](&s[UDP_SOCK_PORT_OFFSET])
    return ptr[0]

def _udp_sock_set_port(s: Ptr[uint8], port: uint16):
    """Set socket port."""
    ptr: Ptr[uint16] = cast[Ptr[uint16]](&s[UDP_SOCK_PORT_OFFSET])
    ptr[0] = port

def _udp_sock_get_buf(s: Ptr[uint8]) -> Ptr[uint8]:
    """Get socket receive buffer."""
    return &s[UDP_SOCK_BUF_OFFSET]

def _udp_sock_get_int(s: Ptr[uint8], offset: int32) -> int32:
    """Get int32 from socket at offset."""
    ptr: Ptr[int32] = cast[Ptr[int32]](&s[offset])
    return ptr[0]

def _udp_sock_set_int(s: Ptr[uint8], offset: int32, val: int32):
    """Set int32 in socket at offset."""
    ptr: Ptr[int32] = cast[Ptr[int32]](&s[offset])
    ptr[0] = val

# ============================================================================
# Initialization
# ============================================================================

def _udp_init():
    """Initialize UDP layer (called automatically)."""
    global _udp_initialized, _udp_tx_count, _udp_rx_count, _udp_errors

    # Clear all sockets
    memset(&_udp_sockets[0], 0, MAX_UDP_SOCKETS * UDP_SOCK_SIZE)

    _udp_tx_count = 0
    _udp_rx_count = 0
    _udp_errors = 0
    _udp_initialized = True

# ============================================================================
# Socket Operations
# ============================================================================

def udp_socket() -> int32:
    """Create a new UDP socket.

    Returns:
        Socket descriptor (0-7) on success, -1 if no sockets available
    """
    if not _udp_initialized:
        _udp_init()

    # Find free socket
    i: int32 = 0
    while i < MAX_UDP_SOCKETS:
        s: Ptr[uint8] = _udp_get_socket(i)
        if _udp_sock_get_state(s) == UDP_SOCK_FREE:
            _udp_sock_set_state(s, UDP_SOCK_OPEN)
            _udp_sock_set_port(s, 0)
            _udp_sock_set_int(s, UDP_SOCK_HEAD_OFFSET, 0)
            _udp_sock_set_int(s, UDP_SOCK_TAIL_OFFSET, 0)
            _udp_sock_set_int(s, UDP_SOCK_COUNT_OFFSET, 0)
            return i
        i = i + 1

    return -1

def udp_bind(sock: int32, port: uint16) -> bool:
    """Bind socket to a local port.

    Args:
        sock: Socket descriptor
        port: Local port number

    Returns:
        True on success, False on failure
    """
    s: Ptr[uint8] = _udp_get_socket(sock)
    if cast[uint32](s) == 0:
        return False

    state: int32 = _udp_sock_get_state(s)
    if state == UDP_SOCK_FREE:
        return False

    # Check if port is already in use
    i: int32 = 0
    while i < MAX_UDP_SOCKETS:
        if i != sock:
            other: Ptr[uint8] = _udp_get_socket(i)
            if _udp_sock_get_state(other) == UDP_SOCK_BOUND:
                if _udp_sock_get_port(other) == port:
                    return False  # Port in use
        i = i + 1

    _udp_sock_set_port(s, port)
    _udp_sock_set_state(s, UDP_SOCK_BOUND)

    return True

def udp_close(sock: int32):
    """Close a UDP socket.

    Args:
        sock: Socket descriptor
    """
    s: Ptr[uint8] = _udp_get_socket(sock)
    if cast[uint32](s) == 0:
        return

    _udp_sock_set_state(s, UDP_SOCK_FREE)
    _udp_sock_set_port(s, 0)
    _udp_sock_set_int(s, UDP_SOCK_HEAD_OFFSET, 0)
    _udp_sock_set_int(s, UDP_SOCK_TAIL_OFFSET, 0)
    _udp_sock_set_int(s, UDP_SOCK_COUNT_OFFSET, 0)

# ============================================================================
# UDP Checksum (with pseudo-header)
# ============================================================================

def _udp_checksum(src_ip: uint32, dst_ip: uint32, udp_pkt: Ptr[uint8], udp_len: int32) -> uint16:
    """Calculate UDP checksum with IP pseudo-header."""
    sum: uint32 = 0

    # Pseudo-header: src IP (4) + dst IP (4) + zero (1) + protocol (1) + UDP length (2)
    # Sum source IP
    sum = sum + ((src_ip >> 16) & 0xFFFF)
    sum = sum + (src_ip & 0xFFFF)

    # Sum destination IP
    sum = sum + ((dst_ip >> 16) & 0xFFFF)
    sum = sum + (dst_ip & 0xFFFF)

    # Protocol (UDP = 17)
    sum = sum + IP_PROTO_UDP

    # UDP length
    sum = sum + cast[uint32](udp_len)

    # Sum UDP header and data
    i: int32 = 0
    while i < udp_len - 1:
        word: uint32 = (cast[uint32](udp_pkt[i]) << 8) | cast[uint32](udp_pkt[i + 1])
        sum = sum + word
        i = i + 2

    # Handle odd byte
    if i < udp_len:
        sum = sum + (cast[uint32](udp_pkt[i]) << 8)

    # Fold to 16 bits
    while (sum >> 16) != 0:
        sum = (sum & 0xFFFF) + (sum >> 16)

    result: uint16 = cast[uint16](~sum & 0xFFFF)

    # UDP uses 0xFFFF instead of 0x0000 for zero checksum
    if result == 0:
        result = 0xFFFF

    return result

# ============================================================================
# Data Transmission
# ============================================================================

def udp_sendto(sock: int32, dst_ip: uint32, dst_port: uint16, data: Ptr[uint8], length: int32) -> int32:
    """Send UDP datagram to destination.

    Args:
        sock: Socket descriptor
        dst_ip: Destination IP address
        dst_port: Destination port
        data: Data to send
        length: Data length

    Returns:
        Bytes sent on success, -1 on error
    """
    global _udp_tx_count, _udp_errors

    s: Ptr[uint8] = _udp_get_socket(sock)
    if cast[uint32](s) == 0:
        _udp_errors = _udp_errors + 1
        return -1

    if _udp_sock_get_state(s) == UDP_SOCK_FREE:
        _udp_errors = _udp_errors + 1
        return -1

    if length < 0 or length > UDP_MAX_PAYLOAD:
        _udp_errors = _udp_errors + 1
        return -1

    # Build UDP packet
    packet: Array[1480, uint8]
    udp_len: int32 = UDP_HEADER_LEN + length

    # Source port (use bound port or ephemeral)
    src_port: uint16 = _udp_sock_get_port(s)
    if src_port == 0:
        src_port = 49152  # Default ephemeral port

    packet[UDP_SRC_PORT_OFFSET] = cast[uint8]((src_port >> 8) & 0xFF)
    packet[UDP_SRC_PORT_OFFSET + 1] = cast[uint8](src_port & 0xFF)

    # Destination port
    packet[UDP_DST_PORT_OFFSET] = cast[uint8]((dst_port >> 8) & 0xFF)
    packet[UDP_DST_PORT_OFFSET + 1] = cast[uint8](dst_port & 0xFF)

    # Length
    packet[UDP_LENGTH_OFFSET] = cast[uint8]((udp_len >> 8) & 0xFF)
    packet[UDP_LENGTH_OFFSET + 1] = cast[uint8](udp_len & 0xFF)

    # Checksum (set to 0 for calculation)
    packet[UDP_CHECKSUM_OFFSET] = 0
    packet[UDP_CHECKSUM_OFFSET + 1] = 0

    # Copy data
    i: int32 = 0
    while i < length:
        packet[UDP_DATA_OFFSET + i] = data[i]
        i = i + 1

    # Calculate checksum
    src_ip: uint32 = ip_get_addr()
    checksum: uint16 = _udp_checksum(src_ip, dst_ip, &packet[0], udp_len)
    packet[UDP_CHECKSUM_OFFSET] = cast[uint8]((checksum >> 8) & 0xFF)
    packet[UDP_CHECKSUM_OFFSET + 1] = cast[uint8](checksum & 0xFF)

    # Send via IP
    if ip_send(dst_ip, IP_PROTO_UDP, &packet[0], udp_len):
        _udp_tx_count = _udp_tx_count + 1
        return length
    else:
        _udp_errors = _udp_errors + 1
        return -1

# ============================================================================
# Data Reception
# ============================================================================

def udp_recvfrom(sock: int32, buf: Ptr[uint8], maxlen: int32, src_ip: Ptr[uint32], src_port: Ptr[uint16]) -> int32:
    """Receive UDP datagram.

    Args:
        sock: Socket descriptor
        buf: Buffer for received data
        maxlen: Maximum buffer size
        src_ip: Output for source IP address
        src_port: Output for source port

    Returns:
        Bytes received on success, 0 if no data, -1 on error
    """
    global _udp_rx_count, _udp_errors

    s: Ptr[uint8] = _udp_get_socket(sock)
    if cast[uint32](s) == 0:
        return -1

    if _udp_sock_get_state(s) != UDP_SOCK_BOUND:
        return -1

    local_port: uint16 = _udp_sock_get_port(s)

    # Receive IP packet
    ip_buf: Array[1480, uint8]
    ip_src: uint32 = 0
    protocol: uint8 = 0

    recv_len: int32 = ip_receive_full(&ip_buf[0], 1480, &ip_src, &protocol)

    if recv_len <= 0:
        return recv_len

    if protocol != IP_PROTO_UDP:
        return 0  # Not UDP

    if recv_len < UDP_HEADER_LEN:
        _udp_errors = _udp_errors + 1
        return -1

    # Parse UDP header
    udp_dst_port: uint16 = (cast[uint16](ip_buf[UDP_DST_PORT_OFFSET]) << 8) | cast[uint16](ip_buf[UDP_DST_PORT_OFFSET + 1])

    if udp_dst_port != local_port:
        return 0  # Not for this socket

    udp_src_port: uint16 = (cast[uint16](ip_buf[UDP_SRC_PORT_OFFSET]) << 8) | cast[uint16](ip_buf[UDP_SRC_PORT_OFFSET + 1])
    udp_len: int32 = (cast[int32](ip_buf[UDP_LENGTH_OFFSET]) << 8) | cast[int32](ip_buf[UDP_LENGTH_OFFSET + 1])

    data_len: int32 = udp_len - UDP_HEADER_LEN
    if data_len < 0 or data_len > maxlen:
        _udp_errors = _udp_errors + 1
        return -1

    # Copy data
    i: int32 = 0
    while i < data_len:
        buf[i] = ip_buf[UDP_DATA_OFFSET + i]
        i = i + 1

    # Return source info
    src_ip[0] = ip_src
    src_port[0] = udp_src_port

    _udp_rx_count = _udp_rx_count + 1

    return data_len

# ============================================================================
# Utility Functions
# ============================================================================

def udp_get_local_port(sock: int32) -> uint16:
    """Get local port for socket."""
    s: Ptr[uint8] = _udp_get_socket(sock)
    if cast[uint32](s) == 0:
        return 0
    return _udp_sock_get_port(s)

def udp_is_bound(sock: int32) -> bool:
    """Check if socket is bound."""
    s: Ptr[uint8] = _udp_get_socket(sock)
    if cast[uint32](s) == 0:
        return False
    return _udp_sock_get_state(s) == UDP_SOCK_BOUND

# ============================================================================
# Statistics
# ============================================================================

def udp_get_tx_count() -> uint32:
    """Get transmitted datagram count."""
    return _udp_tx_count

def udp_get_rx_count() -> uint32:
    """Get received datagram count."""
    return _udp_rx_count

def udp_get_errors() -> uint32:
    """Get error count."""
    return _udp_errors

def udp_clear_stats():
    """Clear all statistics."""
    global _udp_tx_count, _udp_rx_count, _udp_errors
    _udp_tx_count = 0
    _udp_rx_count = 0
    _udp_errors = 0
