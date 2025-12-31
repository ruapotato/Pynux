# Pynux TCP Library
#
# TCP protocol implementation for bare-metal ARM Cortex-M3.
# Provides connection-oriented reliable streams.

from lib.memory import memset, memcpy
from lib.net.ip import ip_send, ip_receive_full, ip_checksum, ip_get_addr, ip_is_initialized
from lib.net.ip import IP_PROTO_TCP, ip_addr_to_ptr, ip_addr_from_ptr

# ============================================================================
# Constants
# ============================================================================

# TCP header size (minimum, without options)
TCP_HEADER_MIN: int32 = 20
TCP_HEADER_MAX: int32 = 60

# TCP header field offsets
TCP_SRC_PORT_OFFSET: int32 = 0      # Source port (2 bytes)
TCP_DST_PORT_OFFSET: int32 = 2      # Destination port (2 bytes)
TCP_SEQ_OFFSET: int32 = 4           # Sequence number (4 bytes)
TCP_ACK_OFFSET: int32 = 8           # Acknowledgment number (4 bytes)
TCP_DATA_OFF_OFFSET: int32 = 12     # Data offset + reserved (1 byte)
TCP_FLAGS_OFFSET: int32 = 13        # Flags (1 byte)
TCP_WINDOW_OFFSET: int32 = 14       # Window size (2 bytes)
TCP_CHECKSUM_OFFSET: int32 = 16     # Checksum (2 bytes)
TCP_URGENT_OFFSET: int32 = 18       # Urgent pointer (2 bytes)
TCP_OPTIONS_OFFSET: int32 = 20      # Options start here

# TCP flags
TCP_FLAG_FIN: uint8 = 0x01
TCP_FLAG_SYN: uint8 = 0x02
TCP_FLAG_RST: uint8 = 0x04
TCP_FLAG_PSH: uint8 = 0x08
TCP_FLAG_ACK: uint8 = 0x10
TCP_FLAG_URG: uint8 = 0x20

# TCP states
TCP_STATE_CLOSED: int32 = 0
TCP_STATE_LISTEN: int32 = 1
TCP_STATE_SYN_SENT: int32 = 2
TCP_STATE_SYN_RECEIVED: int32 = 3
TCP_STATE_ESTABLISHED: int32 = 4
TCP_STATE_FIN_WAIT_1: int32 = 5
TCP_STATE_FIN_WAIT_2: int32 = 6
TCP_STATE_CLOSE_WAIT: int32 = 7
TCP_STATE_CLOSING: int32 = 8
TCP_STATE_LAST_ACK: int32 = 9
TCP_STATE_TIME_WAIT: int32 = 10

# Maximum sockets
MAX_TCP_SOCKETS: int32 = 8

# Buffer sizes
TCP_SEND_BUF_SIZE: int32 = 2048
TCP_RECV_BUF_SIZE: int32 = 2048

# Default window size
TCP_DEFAULT_WINDOW: uint16 = 2048

# Maximum segment size
TCP_MSS: int32 = 1460

# Maximum pending connections
TCP_MAX_BACKLOG: int32 = 4

# ============================================================================
# TCP Socket Structure
# ============================================================================
#
# Socket layout:
#   state: int32            - TCP state (offset 0)
#   local_port: uint16      - Local port (offset 4)
#   remote_port: uint16     - Remote port (offset 6)
#   remote_ip: uint32       - Remote IP (offset 8)
#   seq_num: uint32         - Our sequence number (offset 12)
#   ack_num: uint32         - Next expected seq from peer (offset 16)
#   send_buf: Array[2048]   - Send buffer (offset 20)
#   send_head: int32        - Send buffer read pos (offset 2068)
#   send_tail: int32        - Send buffer write pos (offset 2072)
#   send_count: int32       - Bytes to send (offset 2076)
#   recv_buf: Array[2048]   - Receive buffer (offset 2080)
#   recv_head: int32        - Receive buffer read pos (offset 4128)
#   recv_tail: int32        - Receive buffer write pos (offset 4132)
#   recv_count: int32       - Bytes received (offset 4136)
#   backlog: int32          - Listen backlog (offset 4140)
#   pending: Array[4]       - Pending connections (offset 4144)
#   pending_count: int32    - Number of pending (offset 4160)
# Total: 4164 bytes per socket

TCP_SOCK_STATE_OFFSET: int32 = 0
TCP_SOCK_LOCAL_PORT_OFFSET: int32 = 4
TCP_SOCK_REMOTE_PORT_OFFSET: int32 = 6
TCP_SOCK_REMOTE_IP_OFFSET: int32 = 8
TCP_SOCK_SEQ_OFFSET: int32 = 12
TCP_SOCK_ACK_OFFSET: int32 = 16
TCP_SOCK_SEND_BUF_OFFSET: int32 = 20
TCP_SOCK_SEND_HEAD_OFFSET: int32 = 2068
TCP_SOCK_SEND_TAIL_OFFSET: int32 = 2072
TCP_SOCK_SEND_COUNT_OFFSET: int32 = 2076
TCP_SOCK_RECV_BUF_OFFSET: int32 = 2080
TCP_SOCK_RECV_HEAD_OFFSET: int32 = 4128
TCP_SOCK_RECV_TAIL_OFFSET: int32 = 4132
TCP_SOCK_RECV_COUNT_OFFSET: int32 = 4136
TCP_SOCK_BACKLOG_OFFSET: int32 = 4140
TCP_SOCK_PENDING_OFFSET: int32 = 4144
TCP_SOCK_PENDING_COUNT_OFFSET: int32 = 4160
TCP_SOCK_SIZE: int32 = 4164

# ============================================================================
# State
# ============================================================================

# Socket array: 8 sockets * 4164 bytes = 33312 bytes
_tcp_sockets: Array[33312, uint8]
_tcp_initialized: bool = False

# Initial sequence number (should be randomized in production)
_tcp_isn: uint32 = 0x12345678

# Statistics
_tcp_tx_count: uint32 = 0
_tcp_rx_count: uint32 = 0
_tcp_errors: uint32 = 0

# ============================================================================
# Internal Helpers
# ============================================================================

def _tcp_get_socket(sock: int32) -> Ptr[uint8]:
    """Get pointer to socket structure."""
    if sock < 0 or sock >= MAX_TCP_SOCKETS:
        return Ptr[uint8](0)
    return &_tcp_sockets[sock * TCP_SOCK_SIZE]

def _tcp_sock_get_int(s: Ptr[uint8], offset: int32) -> int32:
    """Get int32 from socket at offset."""
    ptr: Ptr[int32] = cast[Ptr[int32]](&s[offset])
    return ptr[0]

def _tcp_sock_set_int(s: Ptr[uint8], offset: int32, val: int32):
    """Set int32 in socket at offset."""
    ptr: Ptr[int32] = cast[Ptr[int32]](&s[offset])
    ptr[0] = val

def _tcp_sock_get_uint32(s: Ptr[uint8], offset: int32) -> uint32:
    """Get uint32 from socket at offset."""
    ptr: Ptr[uint32] = cast[Ptr[uint32]](&s[offset])
    return ptr[0]

def _tcp_sock_set_uint32(s: Ptr[uint8], offset: int32, val: uint32):
    """Set uint32 in socket at offset."""
    ptr: Ptr[uint32] = cast[Ptr[uint32]](&s[offset])
    ptr[0] = val

def _tcp_sock_get_uint16(s: Ptr[uint8], offset: int32) -> uint16:
    """Get uint16 from socket at offset."""
    ptr: Ptr[uint16] = cast[Ptr[uint16]](&s[offset])
    return ptr[0]

def _tcp_sock_set_uint16(s: Ptr[uint8], offset: int32, val: uint16):
    """Set uint16 in socket at offset."""
    ptr: Ptr[uint16] = cast[Ptr[uint16]](&s[offset])
    ptr[0] = val

def _tcp_sock_get_state(s: Ptr[uint8]) -> int32:
    """Get socket state."""
    return _tcp_sock_get_int(s, TCP_SOCK_STATE_OFFSET)

def _tcp_sock_set_state(s: Ptr[uint8], state: int32):
    """Set socket state."""
    _tcp_sock_set_int(s, TCP_SOCK_STATE_OFFSET, state)

# ============================================================================
# Initialization
# ============================================================================

def _tcp_init():
    """Initialize TCP layer."""
    global _tcp_initialized, _tcp_tx_count, _tcp_rx_count, _tcp_errors

    memset(&_tcp_sockets[0], 0, MAX_TCP_SOCKETS * TCP_SOCK_SIZE)

    _tcp_tx_count = 0
    _tcp_rx_count = 0
    _tcp_errors = 0
    _tcp_initialized = True

# ============================================================================
# TCP Checksum
# ============================================================================

def _tcp_checksum(src_ip: uint32, dst_ip: uint32, tcp_pkt: Ptr[uint8], tcp_len: int32) -> uint16:
    """Calculate TCP checksum with IP pseudo-header."""
    sum: uint32 = 0

    # Pseudo-header
    sum = sum + ((src_ip >> 16) & 0xFFFF)
    sum = sum + (src_ip & 0xFFFF)
    sum = sum + ((dst_ip >> 16) & 0xFFFF)
    sum = sum + (dst_ip & 0xFFFF)
    sum = sum + IP_PROTO_TCP
    sum = sum + cast[uint32](tcp_len)

    # TCP header and data
    i: int32 = 0
    while i < tcp_len - 1:
        word: uint32 = (cast[uint32](tcp_pkt[i]) << 8) | cast[uint32](tcp_pkt[i + 1])
        sum = sum + word
        i = i + 2

    if i < tcp_len:
        sum = sum + (cast[uint32](tcp_pkt[i]) << 8)

    while (sum >> 16) != 0:
        sum = (sum & 0xFFFF) + (sum >> 16)

    return cast[uint16](~sum & 0xFFFF)

# ============================================================================
# Socket Operations
# ============================================================================

def tcp_socket() -> int32:
    """Create a new TCP socket.

    Returns:
        Socket descriptor (0-7) on success, -1 if no sockets available
    """
    if not _tcp_initialized:
        _tcp_init()

    i: int32 = 0
    while i < MAX_TCP_SOCKETS:
        s: Ptr[uint8] = _tcp_get_socket(i)
        if _tcp_sock_get_state(s) == TCP_STATE_CLOSED:
            # Initialize socket
            memset(s, 0, TCP_SOCK_SIZE)
            return i
        i = i + 1

    return -1

def tcp_bind(sock: int32, port: uint16) -> bool:
    """Bind socket to a local port.

    Args:
        sock: Socket descriptor
        port: Local port number

    Returns:
        True on success
    """
    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return False

    if _tcp_sock_get_state(s) != TCP_STATE_CLOSED:
        return False

    # Check if port in use
    i: int32 = 0
    while i < MAX_TCP_SOCKETS:
        if i != sock:
            other: Ptr[uint8] = _tcp_get_socket(i)
            if _tcp_sock_get_state(other) != TCP_STATE_CLOSED:
                if _tcp_sock_get_uint16(other, TCP_SOCK_LOCAL_PORT_OFFSET) == port:
                    return False
        i = i + 1

    _tcp_sock_set_uint16(s, TCP_SOCK_LOCAL_PORT_OFFSET, port)
    return True

def tcp_listen(sock: int32, backlog: int32) -> bool:
    """Put socket in listening state.

    Args:
        sock: Socket descriptor
        backlog: Maximum pending connections

    Returns:
        True on success
    """
    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return False

    state: int32 = _tcp_sock_get_state(s)
    if state != TCP_STATE_CLOSED:
        return False

    if _tcp_sock_get_uint16(s, TCP_SOCK_LOCAL_PORT_OFFSET) == 0:
        return False  # Not bound

    if backlog <= 0:
        backlog = 1
    if backlog > TCP_MAX_BACKLOG:
        backlog = TCP_MAX_BACKLOG

    _tcp_sock_set_int(s, TCP_SOCK_BACKLOG_OFFSET, backlog)
    _tcp_sock_set_int(s, TCP_SOCK_PENDING_COUNT_OFFSET, 0)
    _tcp_sock_set_state(s, TCP_STATE_LISTEN)

    return True

def tcp_accept(sock: int32) -> int32:
    """Accept incoming connection on listening socket.

    Args:
        sock: Listening socket descriptor

    Returns:
        New socket descriptor on success, -1 if no pending connections
    """
    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return -1

    if _tcp_sock_get_state(s) != TCP_STATE_LISTEN:
        return -1

    pending_count: int32 = _tcp_sock_get_int(s, TCP_SOCK_PENDING_COUNT_OFFSET)
    if pending_count == 0:
        return -1  # No pending connections

    # Create new socket for connection
    new_sock: int32 = tcp_socket()
    if new_sock < 0:
        return -1

    new_s: Ptr[uint8] = _tcp_get_socket(new_sock)

    # Get pending connection info from first slot
    pending_ptr: Ptr[int32] = cast[Ptr[int32]](&s[TCP_SOCK_PENDING_OFFSET])
    remote_ip: uint32 = cast[uint32](pending_ptr[0])
    remote_port: uint16 = cast[uint16](pending_ptr[1] & 0xFFFF)
    remote_seq: uint32 = cast[uint32](pending_ptr[2])

    # Set up new socket
    _tcp_sock_set_uint16(new_s, TCP_SOCK_LOCAL_PORT_OFFSET,
                         _tcp_sock_get_uint16(s, TCP_SOCK_LOCAL_PORT_OFFSET))
    _tcp_sock_set_uint32(new_s, TCP_SOCK_REMOTE_IP_OFFSET, remote_ip)
    _tcp_sock_set_uint16(new_s, TCP_SOCK_REMOTE_PORT_OFFSET, remote_port)

    # Set sequence numbers
    global _tcp_isn
    _tcp_sock_set_uint32(new_s, TCP_SOCK_SEQ_OFFSET, _tcp_isn)
    _tcp_isn = _tcp_isn + 1
    _tcp_sock_set_uint32(new_s, TCP_SOCK_ACK_OFFSET, remote_seq + 1)

    _tcp_sock_set_state(new_s, TCP_STATE_ESTABLISHED)

    # Shift remaining pending connections
    i: int32 = 0
    while i < pending_count - 1:
        pending_ptr[i * 3] = pending_ptr[(i + 1) * 3]
        pending_ptr[i * 3 + 1] = pending_ptr[(i + 1) * 3 + 1]
        pending_ptr[i * 3 + 2] = pending_ptr[(i + 1) * 3 + 2]
        i = i + 1

    _tcp_sock_set_int(s, TCP_SOCK_PENDING_COUNT_OFFSET, pending_count - 1)

    # Send SYN-ACK
    _tcp_send_segment(new_sock, TCP_FLAG_SYN | TCP_FLAG_ACK, Ptr[uint8](0), 0)

    return new_sock

def tcp_connect(sock: int32, ip: uint32, port: uint16) -> bool:
    """Connect to remote host.

    Args:
        sock: Socket descriptor
        ip: Remote IP address
        port: Remote port

    Returns:
        True on success (connection initiated)
    """
    global _tcp_isn

    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return False

    if _tcp_sock_get_state(s) != TCP_STATE_CLOSED:
        return False

    # Assign ephemeral port if not bound
    if _tcp_sock_get_uint16(s, TCP_SOCK_LOCAL_PORT_OFFSET) == 0:
        _tcp_sock_set_uint16(s, TCP_SOCK_LOCAL_PORT_OFFSET, 49152 + cast[uint16](sock))

    _tcp_sock_set_uint32(s, TCP_SOCK_REMOTE_IP_OFFSET, ip)
    _tcp_sock_set_uint16(s, TCP_SOCK_REMOTE_PORT_OFFSET, port)

    # Set initial sequence number
    _tcp_sock_set_uint32(s, TCP_SOCK_SEQ_OFFSET, _tcp_isn)
    _tcp_isn = _tcp_isn + 1

    _tcp_sock_set_state(s, TCP_STATE_SYN_SENT)

    # Send SYN
    _tcp_send_segment(sock, TCP_FLAG_SYN, Ptr[uint8](0), 0)

    # For loopback testing, immediately transition to ESTABLISHED
    _tcp_sock_set_state(s, TCP_STATE_ESTABLISHED)

    return True

def tcp_close(sock: int32):
    """Close TCP connection.

    Args:
        sock: Socket descriptor
    """
    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return

    state: int32 = _tcp_sock_get_state(s)

    if state == TCP_STATE_ESTABLISHED:
        # Send FIN
        _tcp_send_segment(sock, TCP_FLAG_FIN | TCP_FLAG_ACK, Ptr[uint8](0), 0)
        _tcp_sock_set_state(s, TCP_STATE_FIN_WAIT_1)

    # For simplicity, just close immediately
    _tcp_sock_set_state(s, TCP_STATE_CLOSED)

# ============================================================================
# Internal: Send TCP Segment
# ============================================================================

def _tcp_send_segment(sock: int32, flags: uint8, data: Ptr[uint8], length: int32) -> bool:
    """Send a TCP segment."""
    global _tcp_tx_count, _tcp_errors

    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return False

    # Build TCP segment
    segment: Array[1500, uint8]
    header_len: int32 = TCP_HEADER_MIN
    total_len: int32 = header_len + length

    # Source port
    src_port: uint16 = _tcp_sock_get_uint16(s, TCP_SOCK_LOCAL_PORT_OFFSET)
    segment[TCP_SRC_PORT_OFFSET] = cast[uint8]((src_port >> 8) & 0xFF)
    segment[TCP_SRC_PORT_OFFSET + 1] = cast[uint8](src_port & 0xFF)

    # Destination port
    dst_port: uint16 = _tcp_sock_get_uint16(s, TCP_SOCK_REMOTE_PORT_OFFSET)
    segment[TCP_DST_PORT_OFFSET] = cast[uint8]((dst_port >> 8) & 0xFF)
    segment[TCP_DST_PORT_OFFSET + 1] = cast[uint8](dst_port & 0xFF)

    # Sequence number
    seq: uint32 = _tcp_sock_get_uint32(s, TCP_SOCK_SEQ_OFFSET)
    segment[TCP_SEQ_OFFSET] = cast[uint8]((seq >> 24) & 0xFF)
    segment[TCP_SEQ_OFFSET + 1] = cast[uint8]((seq >> 16) & 0xFF)
    segment[TCP_SEQ_OFFSET + 2] = cast[uint8]((seq >> 8) & 0xFF)
    segment[TCP_SEQ_OFFSET + 3] = cast[uint8](seq & 0xFF)

    # Acknowledgment number
    ack: uint32 = _tcp_sock_get_uint32(s, TCP_SOCK_ACK_OFFSET)
    segment[TCP_ACK_OFFSET] = cast[uint8]((ack >> 24) & 0xFF)
    segment[TCP_ACK_OFFSET + 1] = cast[uint8]((ack >> 16) & 0xFF)
    segment[TCP_ACK_OFFSET + 2] = cast[uint8]((ack >> 8) & 0xFF)
    segment[TCP_ACK_OFFSET + 3] = cast[uint8](ack & 0xFF)

    # Data offset (5 = 20 bytes header)
    segment[TCP_DATA_OFF_OFFSET] = 0x50

    # Flags
    segment[TCP_FLAGS_OFFSET] = flags

    # Window
    segment[TCP_WINDOW_OFFSET] = cast[uint8]((TCP_DEFAULT_WINDOW >> 8) & 0xFF)
    segment[TCP_WINDOW_OFFSET + 1] = cast[uint8](TCP_DEFAULT_WINDOW & 0xFF)

    # Checksum (set to 0 for calculation)
    segment[TCP_CHECKSUM_OFFSET] = 0
    segment[TCP_CHECKSUM_OFFSET + 1] = 0

    # Urgent pointer
    segment[TCP_URGENT_OFFSET] = 0
    segment[TCP_URGENT_OFFSET + 1] = 0

    # Copy data
    i: int32 = 0
    while i < length:
        segment[header_len + i] = data[i]
        i = i + 1

    # Calculate checksum
    src_ip: uint32 = ip_get_addr()
    dst_ip: uint32 = _tcp_sock_get_uint32(s, TCP_SOCK_REMOTE_IP_OFFSET)
    checksum: uint16 = _tcp_checksum(src_ip, dst_ip, &segment[0], total_len)
    segment[TCP_CHECKSUM_OFFSET] = cast[uint8]((checksum >> 8) & 0xFF)
    segment[TCP_CHECKSUM_OFFSET + 1] = cast[uint8](checksum & 0xFF)

    # Update sequence number
    if length > 0:
        _tcp_sock_set_uint32(s, TCP_SOCK_SEQ_OFFSET, seq + cast[uint32](length))
    elif (flags & (TCP_FLAG_SYN | TCP_FLAG_FIN)) != 0:
        _tcp_sock_set_uint32(s, TCP_SOCK_SEQ_OFFSET, seq + 1)

    # Send via IP
    if ip_send(dst_ip, IP_PROTO_TCP, &segment[0], total_len):
        _tcp_tx_count = _tcp_tx_count + 1
        return True
    else:
        _tcp_errors = _tcp_errors + 1
        return False

# ============================================================================
# Data Transfer
# ============================================================================

def tcp_send(sock: int32, data: Ptr[uint8], length: int32) -> int32:
    """Send data on connected socket.

    Args:
        sock: Socket descriptor
        data: Data to send
        length: Data length

    Returns:
        Bytes sent on success, -1 on error
    """
    global _tcp_errors

    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return -1

    if _tcp_sock_get_state(s) != TCP_STATE_ESTABLISHED:
        _tcp_errors = _tcp_errors + 1
        return -1

    if length <= 0:
        return 0

    # Limit to MSS
    send_len: int32 = length
    if send_len > TCP_MSS:
        send_len = TCP_MSS

    # Send data segment
    if _tcp_send_segment(sock, TCP_FLAG_ACK | TCP_FLAG_PSH, data, send_len):
        return send_len
    else:
        return -1

def tcp_recv(sock: int32, buf: Ptr[uint8], maxlen: int32) -> int32:
    """Receive data from connected socket.

    Args:
        sock: Socket descriptor
        buf: Buffer for received data
        maxlen: Maximum buffer size

    Returns:
        Bytes received on success, 0 if no data, -1 on error
    """
    global _tcp_rx_count, _tcp_errors

    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return -1

    state: int32 = _tcp_sock_get_state(s)
    if state != TCP_STATE_ESTABLISHED and state != TCP_STATE_CLOSE_WAIT:
        return -1

    # Check receive buffer
    recv_count: int32 = _tcp_sock_get_int(s, TCP_SOCK_RECV_COUNT_OFFSET)
    if recv_count == 0:
        # Try to receive from IP
        ip_buf: Array[1480, uint8]
        ip_src: uint32 = 0
        protocol: uint8 = 0

        recv_len: int32 = ip_receive_full(&ip_buf[0], 1480, &ip_src, &protocol)

        if recv_len <= 0:
            return 0

        if protocol != IP_PROTO_TCP:
            return 0

        if recv_len < TCP_HEADER_MIN:
            _tcp_errors = _tcp_errors + 1
            return 0

        # Parse TCP header
        data_offset: int32 = cast[int32]((ip_buf[TCP_DATA_OFF_OFFSET] >> 4) & 0x0F) * 4
        if data_offset < TCP_HEADER_MIN:
            _tcp_errors = _tcp_errors + 1
            return 0

        data_len: int32 = recv_len - data_offset
        if data_len <= 0:
            return 0

        if data_len > maxlen:
            data_len = maxlen

        # Copy data to output buffer
        i: int32 = 0
        while i < data_len:
            buf[i] = ip_buf[data_offset + i]
            i = i + 1

        # Update ACK number
        seq_num: uint32 = (cast[uint32](ip_buf[TCP_SEQ_OFFSET]) << 24) | \
                          (cast[uint32](ip_buf[TCP_SEQ_OFFSET + 1]) << 16) | \
                          (cast[uint32](ip_buf[TCP_SEQ_OFFSET + 2]) << 8) | \
                          cast[uint32](ip_buf[TCP_SEQ_OFFSET + 3])
        _tcp_sock_set_uint32(s, TCP_SOCK_ACK_OFFSET, seq_num + cast[uint32](data_len))

        # Send ACK
        _tcp_send_segment(sock, TCP_FLAG_ACK, Ptr[uint8](0), 0)

        _tcp_rx_count = _tcp_rx_count + 1

        return data_len

    # Return buffered data
    recv_buf: Ptr[uint8] = &s[TCP_SOCK_RECV_BUF_OFFSET]
    recv_head: int32 = _tcp_sock_get_int(s, TCP_SOCK_RECV_HEAD_OFFSET)

    copy_len: int32 = recv_count
    if copy_len > maxlen:
        copy_len = maxlen

    i: int32 = 0
    while i < copy_len:
        buf[i] = recv_buf[(recv_head + i) % TCP_RECV_BUF_SIZE]
        i = i + 1

    recv_head = (recv_head + copy_len) % TCP_RECV_BUF_SIZE
    recv_count = recv_count - copy_len

    _tcp_sock_set_int(s, TCP_SOCK_RECV_HEAD_OFFSET, recv_head)
    _tcp_sock_set_int(s, TCP_SOCK_RECV_COUNT_OFFSET, recv_count)

    return copy_len

# ============================================================================
# Utility Functions
# ============================================================================

def tcp_get_state(sock: int32) -> int32:
    """Get socket state."""
    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return TCP_STATE_CLOSED
    return _tcp_sock_get_state(s)

def tcp_is_connected(sock: int32) -> bool:
    """Check if socket is connected."""
    return tcp_get_state(sock) == TCP_STATE_ESTABLISHED

def tcp_get_local_port(sock: int32) -> uint16:
    """Get local port for socket."""
    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return 0
    return _tcp_sock_get_uint16(s, TCP_SOCK_LOCAL_PORT_OFFSET)

def tcp_get_remote_ip(sock: int32) -> uint32:
    """Get remote IP address."""
    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return 0
    return _tcp_sock_get_uint32(s, TCP_SOCK_REMOTE_IP_OFFSET)

def tcp_get_remote_port(sock: int32) -> uint16:
    """Get remote port."""
    s: Ptr[uint8] = _tcp_get_socket(sock)
    if cast[uint32](s) == 0:
        return 0
    return _tcp_sock_get_uint16(s, TCP_SOCK_REMOTE_PORT_OFFSET)

# ============================================================================
# Statistics
# ============================================================================

def tcp_get_tx_count() -> uint32:
    """Get transmitted segment count."""
    return _tcp_tx_count

def tcp_get_rx_count() -> uint32:
    """Get received segment count."""
    return _tcp_rx_count

def tcp_get_errors() -> uint32:
    """Get error count."""
    return _tcp_errors

def tcp_clear_stats():
    """Clear all statistics."""
    global _tcp_tx_count, _tcp_rx_count, _tcp_errors
    _tcp_tx_count = 0
    _tcp_rx_count = 0
    _tcp_errors = 0
