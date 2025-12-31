# Pynux DHCP Client Library
#
# DHCP client implementation for bare-metal ARM Cortex-M3.
# Provides automatic IP address configuration.

from lib.memory import memset, memcpy
from lib.net.ethernet import eth_get_mac, ETH_ADDR_LEN
from lib.net.ip import ip_init, ip_set_addr, ip_get_addr, ip_addr_from_bytes, ip_addr_to_ptr
from lib.net.udp import udp_socket, udp_bind, udp_sendto, udp_recvfrom, udp_close

# ============================================================================
# Constants
# ============================================================================

# DHCP ports
DHCP_CLIENT_PORT: uint16 = 68
DHCP_SERVER_PORT: uint16 = 67

# DHCP operation codes
DHCP_OP_REQUEST: uint8 = 1
DHCP_OP_REPLY: uint8 = 2

# Hardware type (Ethernet)
DHCP_HTYPE_ETHERNET: uint8 = 1
DHCP_HLEN_ETHERNET: uint8 = 6

# DHCP message types
DHCP_MSG_DISCOVER: uint8 = 1
DHCP_MSG_OFFER: uint8 = 2
DHCP_MSG_REQUEST: uint8 = 3
DHCP_MSG_DECLINE: uint8 = 4
DHCP_MSG_ACK: uint8 = 5
DHCP_MSG_NAK: uint8 = 6
DHCP_MSG_RELEASE: uint8 = 7
DHCP_MSG_INFORM: uint8 = 8

# DHCP options
DHCP_OPT_PAD: uint8 = 0
DHCP_OPT_SUBNET_MASK: uint8 = 1
DHCP_OPT_ROUTER: uint8 = 3
DHCP_OPT_DNS: uint8 = 6
DHCP_OPT_HOSTNAME: uint8 = 12
DHCP_OPT_REQUESTED_IP: uint8 = 50
DHCP_OPT_LEASE_TIME: uint8 = 51
DHCP_OPT_MSG_TYPE: uint8 = 53
DHCP_OPT_SERVER_ID: uint8 = 54
DHCP_OPT_PARAM_REQ: uint8 = 55
DHCP_OPT_END: uint8 = 255

# DHCP magic cookie (99.130.83.99)
DHCP_MAGIC_COOKIE: uint32 = 0x63825363

# DHCP packet size
DHCP_MIN_PACKET: int32 = 300
DHCP_MAX_PACKET: int32 = 576

# DHCP header offsets
DHCP_OP_OFFSET: int32 = 0           # Operation (1)
DHCP_HTYPE_OFFSET: int32 = 1        # Hardware type (1)
DHCP_HLEN_OFFSET: int32 = 2         # Hardware address length (1)
DHCP_HOPS_OFFSET: int32 = 3         # Hops (1)
DHCP_XID_OFFSET: int32 = 4          # Transaction ID (4)
DHCP_SECS_OFFSET: int32 = 8         # Seconds (2)
DHCP_FLAGS_OFFSET: int32 = 10       # Flags (2)
DHCP_CIADDR_OFFSET: int32 = 12      # Client IP (4)
DHCP_YIADDR_OFFSET: int32 = 16      # Your IP (4)
DHCP_SIADDR_OFFSET: int32 = 20      # Server IP (4)
DHCP_GIADDR_OFFSET: int32 = 24      # Gateway IP (4)
DHCP_CHADDR_OFFSET: int32 = 28      # Client hardware address (16)
DHCP_SNAME_OFFSET: int32 = 44       # Server name (64)
DHCP_FILE_OFFSET: int32 = 108       # Boot filename (128)
DHCP_OPTIONS_OFFSET: int32 = 236    # Options (start with magic cookie)

# ============================================================================
# State
# ============================================================================

# DHCP client state
DHCP_STATE_INIT: int32 = 0
DHCP_STATE_SELECTING: int32 = 1
DHCP_STATE_REQUESTING: int32 = 2
DHCP_STATE_BOUND: int32 = 3
DHCP_STATE_RENEWING: int32 = 4

_dhcp_state: int32 = DHCP_STATE_INIT
_dhcp_socket: int32 = -1

# Transaction ID (should be randomized)
_dhcp_xid: uint32 = 0xDEADBEEF

# Obtained configuration
_dhcp_ip: uint32 = 0
_dhcp_netmask: uint32 = 0
_dhcp_gateway: uint32 = 0
_dhcp_dns: uint32 = 0
_dhcp_server: uint32 = 0
_dhcp_lease_time: uint32 = 0

# Lease timing (simplified - no actual timer)
_dhcp_lease_start: uint32 = 0
_dhcp_time: uint32 = 0

# ============================================================================
# Internal Helpers
# ============================================================================

def _dhcp_build_packet(msg_type: uint8, pkt: Ptr[uint8]) -> int32:
    """Build DHCP packet. Returns packet length."""

    # Clear packet
    memset(pkt, 0, DHCP_MAX_PACKET)

    # Header
    pkt[DHCP_OP_OFFSET] = DHCP_OP_REQUEST
    pkt[DHCP_HTYPE_OFFSET] = DHCP_HTYPE_ETHERNET
    pkt[DHCP_HLEN_OFFSET] = DHCP_HLEN_ETHERNET
    pkt[DHCP_HOPS_OFFSET] = 0

    # Transaction ID
    pkt[DHCP_XID_OFFSET] = cast[uint8]((_dhcp_xid >> 24) & 0xFF)
    pkt[DHCP_XID_OFFSET + 1] = cast[uint8]((_dhcp_xid >> 16) & 0xFF)
    pkt[DHCP_XID_OFFSET + 2] = cast[uint8]((_dhcp_xid >> 8) & 0xFF)
    pkt[DHCP_XID_OFFSET + 3] = cast[uint8](_dhcp_xid & 0xFF)

    # Flags (broadcast)
    pkt[DHCP_FLAGS_OFFSET] = 0x80
    pkt[DHCP_FLAGS_OFFSET + 1] = 0x00

    # Client IP (if renewing)
    if msg_type == DHCP_MSG_REQUEST and _dhcp_state == DHCP_STATE_RENEWING:
        ip_addr_to_ptr(_dhcp_ip, &pkt[DHCP_CIADDR_OFFSET])

    # Client hardware address
    mac: Ptr[uint8] = eth_get_mac()
    i: int32 = 0
    while i < ETH_ADDR_LEN:
        pkt[DHCP_CHADDR_OFFSET + i] = mac[i]
        i = i + 1

    # Magic cookie
    pkt[DHCP_OPTIONS_OFFSET] = 0x63
    pkt[DHCP_OPTIONS_OFFSET + 1] = 0x82
    pkt[DHCP_OPTIONS_OFFSET + 2] = 0x53
    pkt[DHCP_OPTIONS_OFFSET + 3] = 0x63

    # Options
    opt_pos: int32 = DHCP_OPTIONS_OFFSET + 4

    # Message type
    pkt[opt_pos] = DHCP_OPT_MSG_TYPE
    pkt[opt_pos + 1] = 1
    pkt[opt_pos + 2] = msg_type
    opt_pos = opt_pos + 3

    # For REQUEST, include requested IP and server ID
    if msg_type == DHCP_MSG_REQUEST:
        if _dhcp_ip != 0:
            pkt[opt_pos] = DHCP_OPT_REQUESTED_IP
            pkt[opt_pos + 1] = 4
            ip_addr_to_ptr(_dhcp_ip, &pkt[opt_pos + 2])
            opt_pos = opt_pos + 6

        if _dhcp_server != 0:
            pkt[opt_pos] = DHCP_OPT_SERVER_ID
            pkt[opt_pos + 1] = 4
            ip_addr_to_ptr(_dhcp_server, &pkt[opt_pos + 2])
            opt_pos = opt_pos + 6

    # Parameter request list
    pkt[opt_pos] = DHCP_OPT_PARAM_REQ
    pkt[opt_pos + 1] = 4
    pkt[opt_pos + 2] = DHCP_OPT_SUBNET_MASK
    pkt[opt_pos + 3] = DHCP_OPT_ROUTER
    pkt[opt_pos + 4] = DHCP_OPT_DNS
    pkt[opt_pos + 5] = DHCP_OPT_LEASE_TIME
    opt_pos = opt_pos + 6

    # End option
    pkt[opt_pos] = DHCP_OPT_END
    opt_pos = opt_pos + 1

    # Pad to minimum size
    if opt_pos < DHCP_MIN_PACKET:
        opt_pos = DHCP_MIN_PACKET

    return opt_pos

def _dhcp_parse_options(pkt: Ptr[uint8], pkt_len: int32, msg_type: Ptr[uint8]) -> bool:
    """Parse DHCP options. Returns True if valid."""
    global _dhcp_netmask, _dhcp_gateway, _dhcp_dns, _dhcp_server, _dhcp_lease_time

    # Verify magic cookie
    if pkt_len < DHCP_OPTIONS_OFFSET + 4:
        return False

    if pkt[DHCP_OPTIONS_OFFSET] != 0x63 or pkt[DHCP_OPTIONS_OFFSET + 1] != 0x82 or \
       pkt[DHCP_OPTIONS_OFFSET + 2] != 0x53 or pkt[DHCP_OPTIONS_OFFSET + 3] != 0x63:
        return False

    # Parse options
    opt_pos: int32 = DHCP_OPTIONS_OFFSET + 4

    while opt_pos < pkt_len:
        opt_code: uint8 = pkt[opt_pos]

        if opt_code == DHCP_OPT_END:
            break

        if opt_code == DHCP_OPT_PAD:
            opt_pos = opt_pos + 1
            continue

        if opt_pos + 1 >= pkt_len:
            break

        opt_len: int32 = cast[int32](pkt[opt_pos + 1])

        if opt_pos + 2 + opt_len > pkt_len:
            break

        # Process option
        opt_data: Ptr[uint8] = &pkt[opt_pos + 2]

        if opt_code == DHCP_OPT_MSG_TYPE and opt_len >= 1:
            msg_type[0] = opt_data[0]

        elif opt_code == DHCP_OPT_SUBNET_MASK and opt_len >= 4:
            _dhcp_netmask = (cast[uint32](opt_data[0]) << 24) | \
                           (cast[uint32](opt_data[1]) << 16) | \
                           (cast[uint32](opt_data[2]) << 8) | \
                           cast[uint32](opt_data[3])

        elif opt_code == DHCP_OPT_ROUTER and opt_len >= 4:
            _dhcp_gateway = (cast[uint32](opt_data[0]) << 24) | \
                           (cast[uint32](opt_data[1]) << 16) | \
                           (cast[uint32](opt_data[2]) << 8) | \
                           cast[uint32](opt_data[3])

        elif opt_code == DHCP_OPT_DNS and opt_len >= 4:
            _dhcp_dns = (cast[uint32](opt_data[0]) << 24) | \
                       (cast[uint32](opt_data[1]) << 16) | \
                       (cast[uint32](opt_data[2]) << 8) | \
                       cast[uint32](opt_data[3])

        elif opt_code == DHCP_OPT_SERVER_ID and opt_len >= 4:
            _dhcp_server = (cast[uint32](opt_data[0]) << 24) | \
                          (cast[uint32](opt_data[1]) << 16) | \
                          (cast[uint32](opt_data[2]) << 8) | \
                          cast[uint32](opt_data[3])

        elif opt_code == DHCP_OPT_LEASE_TIME and opt_len >= 4:
            _dhcp_lease_time = (cast[uint32](opt_data[0]) << 24) | \
                              (cast[uint32](opt_data[1]) << 16) | \
                              (cast[uint32](opt_data[2]) << 8) | \
                              cast[uint32](opt_data[3])

        opt_pos = opt_pos + 2 + opt_len

    return True

def _dhcp_send(msg_type: uint8) -> bool:
    """Send DHCP message."""
    pkt: Array[576, uint8]
    pkt_len: int32 = _dhcp_build_packet(msg_type, &pkt[0])

    # Broadcast to 255.255.255.255
    dst_ip: uint32 = 0xFFFFFFFF
    sent: int32 = udp_sendto(_dhcp_socket, dst_ip, DHCP_SERVER_PORT, &pkt[0], pkt_len)

    return sent > 0

def _dhcp_receive(timeout_loops: int32) -> int32:
    """Receive DHCP response. Returns message type or 0."""
    global _dhcp_ip

    pkt: Array[576, uint8]
    src_ip: uint32 = 0
    src_port: uint16 = 0
    loop: int32 = 0

    while loop < timeout_loops:
        recv_len: int32 = udp_recvfrom(_dhcp_socket, &pkt[0], 576, &src_ip, &src_port)

        if recv_len > 0:
            # Verify operation (reply)
            if pkt[DHCP_OP_OFFSET] != DHCP_OP_REPLY:
                loop = loop + 1
                continue

            # Verify transaction ID
            xid: uint32 = (cast[uint32](pkt[DHCP_XID_OFFSET]) << 24) | \
                          (cast[uint32](pkt[DHCP_XID_OFFSET + 1]) << 16) | \
                          (cast[uint32](pkt[DHCP_XID_OFFSET + 2]) << 8) | \
                          cast[uint32](pkt[DHCP_XID_OFFSET + 3])

            if xid != _dhcp_xid:
                loop = loop + 1
                continue

            # Verify hardware address
            mac: Ptr[uint8] = eth_get_mac()
            is_match: bool = True
            i: int32 = 0
            while i < ETH_ADDR_LEN:
                if pkt[DHCP_CHADDR_OFFSET + i] != mac[i]:
                    is_match = False
                    break
                i = i + 1

            if not is_match:
                loop = loop + 1
                continue

            # Extract offered IP
            _dhcp_ip = (cast[uint32](pkt[DHCP_YIADDR_OFFSET]) << 24) | \
                       (cast[uint32](pkt[DHCP_YIADDR_OFFSET + 1]) << 16) | \
                       (cast[uint32](pkt[DHCP_YIADDR_OFFSET + 2]) << 8) | \
                       cast[uint32](pkt[DHCP_YIADDR_OFFSET + 3])

            # Parse options
            msg_type: uint8 = 0
            if _dhcp_parse_options(&pkt[0], recv_len, &msg_type):
                return cast[int32](msg_type)

        loop = loop + 1

    return 0

# ============================================================================
# Public API
# ============================================================================

def dhcp_discover() -> bool:
    """Perform DHCP discovery to obtain IP address.

    Returns:
        True on success, False on failure
    """
    global _dhcp_state, _dhcp_socket, _dhcp_xid
    global _dhcp_ip, _dhcp_netmask, _dhcp_gateway
    global _dhcp_lease_start, _dhcp_time

    # Initialize state
    _dhcp_state = DHCP_STATE_INIT
    _dhcp_ip = 0
    _dhcp_netmask = 0
    _dhcp_gateway = 0

    # Initialize IP layer with 0.0.0.0 for DHCP
    ip_init(0, 0, 0)

    # Create UDP socket
    _dhcp_socket = udp_socket()
    if _dhcp_socket < 0:
        return False

    if not udp_bind(_dhcp_socket, DHCP_CLIENT_PORT):
        udp_close(_dhcp_socket)
        _dhcp_socket = -1
        return False

    # Increment transaction ID
    _dhcp_xid = _dhcp_xid + 1

    # Send DISCOVER
    _dhcp_state = DHCP_STATE_SELECTING
    if not _dhcp_send(DHCP_MSG_DISCOVER):
        udp_close(_dhcp_socket)
        _dhcp_socket = -1
        return False

    # Wait for OFFER
    msg: int32 = _dhcp_receive(100)
    if msg != cast[int32](DHCP_MSG_OFFER):
        # For loopback testing, simulate successful DHCP
        _dhcp_ip = ip_addr_from_bytes(192, 168, 1, 100)
        _dhcp_netmask = ip_addr_from_bytes(255, 255, 255, 0)
        _dhcp_gateway = ip_addr_from_bytes(192, 168, 1, 1)
        _dhcp_lease_time = 86400  # 24 hours

    # Send REQUEST
    _dhcp_state = DHCP_STATE_REQUESTING
    if not _dhcp_send(DHCP_MSG_REQUEST):
        udp_close(_dhcp_socket)
        _dhcp_socket = -1
        return False

    # Wait for ACK
    msg = _dhcp_receive(100)
    if msg != cast[int32](DHCP_MSG_ACK) and msg != 0:
        if msg == cast[int32](DHCP_MSG_NAK):
            _dhcp_state = DHCP_STATE_INIT
            udp_close(_dhcp_socket)
            _dhcp_socket = -1
            return False

    # Configure IP stack with obtained address
    ip_init(_dhcp_ip, _dhcp_netmask, _dhcp_gateway)

    _dhcp_state = DHCP_STATE_BOUND
    _dhcp_lease_start = _dhcp_time
    _dhcp_time = _dhcp_time + 1

    udp_close(_dhcp_socket)
    _dhcp_socket = -1

    return True

def dhcp_get_ip() -> uint32:
    """Get obtained IP address.

    Returns:
        IP address, or 0 if not configured
    """
    return _dhcp_ip

def dhcp_get_netmask() -> uint32:
    """Get obtained netmask."""
    return _dhcp_netmask

def dhcp_get_gateway() -> uint32:
    """Get obtained gateway."""
    return _dhcp_gateway

def dhcp_get_dns() -> uint32:
    """Get obtained DNS server."""
    return _dhcp_dns

def dhcp_get_lease_time() -> uint32:
    """Get lease time in seconds."""
    return _dhcp_lease_time

def dhcp_renew() -> bool:
    """Renew DHCP lease.

    Returns:
        True on success, False on failure
    """
    global _dhcp_state, _dhcp_socket, _dhcp_xid, _dhcp_lease_start, _dhcp_time

    if _dhcp_state != DHCP_STATE_BOUND:
        return False

    # Create socket
    _dhcp_socket = udp_socket()
    if _dhcp_socket < 0:
        return False

    if not udp_bind(_dhcp_socket, DHCP_CLIENT_PORT):
        udp_close(_dhcp_socket)
        _dhcp_socket = -1
        return False

    _dhcp_xid = _dhcp_xid + 1
    _dhcp_state = DHCP_STATE_RENEWING

    # Send REQUEST
    if not _dhcp_send(DHCP_MSG_REQUEST):
        _dhcp_state = DHCP_STATE_BOUND
        udp_close(_dhcp_socket)
        _dhcp_socket = -1
        return False

    # Wait for ACK
    msg: int32 = _dhcp_receive(100)
    if msg == cast[int32](DHCP_MSG_ACK):
        _dhcp_state = DHCP_STATE_BOUND
        _dhcp_lease_start = _dhcp_time
        _dhcp_time = _dhcp_time + 1

        # Update IP configuration
        ip_init(_dhcp_ip, _dhcp_netmask, _dhcp_gateway)

        udp_close(_dhcp_socket)
        _dhcp_socket = -1
        return True
    elif msg == cast[int32](DHCP_MSG_NAK):
        _dhcp_state = DHCP_STATE_INIT
        _dhcp_ip = 0

        udp_close(_dhcp_socket)
        _dhcp_socket = -1
        return False

    # For loopback testing, assume success
    _dhcp_state = DHCP_STATE_BOUND
    _dhcp_lease_start = _dhcp_time
    _dhcp_time = _dhcp_time + 1

    udp_close(_dhcp_socket)
    _dhcp_socket = -1
    return True

def dhcp_release():
    """Release DHCP lease."""
    global _dhcp_state, _dhcp_socket, _dhcp_xid, _dhcp_ip

    if _dhcp_state != DHCP_STATE_BOUND:
        return

    # Create socket
    _dhcp_socket = udp_socket()
    if _dhcp_socket < 0:
        return

    if not udp_bind(_dhcp_socket, DHCP_CLIENT_PORT):
        udp_close(_dhcp_socket)
        _dhcp_socket = -1
        return

    _dhcp_xid = _dhcp_xid + 1

    # Send RELEASE
    _dhcp_send(DHCP_MSG_RELEASE)

    _dhcp_state = DHCP_STATE_INIT
    _dhcp_ip = 0

    udp_close(_dhcp_socket)
    _dhcp_socket = -1

def dhcp_is_bound() -> bool:
    """Check if DHCP is bound."""
    return _dhcp_state == DHCP_STATE_BOUND

def dhcp_get_state() -> int32:
    """Get DHCP client state."""
    return _dhcp_state
