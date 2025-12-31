# Pynux IPv4 Library
#
# IPv4 protocol handling for bare-metal ARM Cortex-M3.
# Provides IP packet construction, transmission, and reception.

from lib.memory import memset, memcpy
from lib.net.ethernet import eth_send, eth_receive, eth_get_mac, eth_is_initialized
from lib.net.ethernet import ETHERTYPE_IPV4, ETH_HEADER_LEN, ETH_MAX_PAYLOAD

# ============================================================================
# Constants
# ============================================================================

# IP header sizes
IP_HEADER_MIN: int32 = 20       # Minimum IP header size
IP_HEADER_MAX: int32 = 60       # Maximum IP header size (with options)

# IP version
IP_VERSION_4: uint8 = 4

# IP header field offsets
IP_VER_IHL_OFFSET: int32 = 0    # Version (4 bits) + IHL (4 bits)
IP_TOS_OFFSET: int32 = 1        # Type of Service
IP_LEN_OFFSET: int32 = 2        # Total Length (2 bytes)
IP_ID_OFFSET: int32 = 4         # Identification (2 bytes)
IP_FLAGS_OFFSET: int32 = 6      # Flags + Fragment Offset (2 bytes)
IP_TTL_OFFSET: int32 = 8        # Time to Live
IP_PROTO_OFFSET: int32 = 9      # Protocol
IP_CHECKSUM_OFFSET: int32 = 10  # Header Checksum (2 bytes)
IP_SRC_OFFSET: int32 = 12       # Source Address (4 bytes)
IP_DST_OFFSET: int32 = 16       # Destination Address (4 bytes)
IP_OPTIONS_OFFSET: int32 = 20   # Options (variable)

# IP flags
IP_FLAG_RESERVED: uint16 = 0x8000
IP_FLAG_DF: uint16 = 0x4000     # Don't Fragment
IP_FLAG_MF: uint16 = 0x2000     # More Fragments
IP_FRAG_MASK: uint16 = 0x1FFF   # Fragment offset mask

# Common protocols
IP_PROTO_ICMP: uint8 = 1
IP_PROTO_TCP: uint8 = 6
IP_PROTO_UDP: uint8 = 17

# Default values
IP_DEFAULT_TTL: uint8 = 64
IP_DEFAULT_TOS: uint8 = 0

# Maximum payload
IP_MAX_PAYLOAD: int32 = 1480    # MTU - IP header

# ============================================================================
# State
# ============================================================================

# IP configuration
_ip_addr: uint32 = 0            # Our IP address
_ip_netmask: uint32 = 0         # Network mask
_ip_gateway: uint32 = 0         # Default gateway
_ip_initialized: bool = False

# Packet ID counter
_ip_id_counter: uint16 = 0

# ARP cache (simple: 16 entries)
# Each entry: IP (4 bytes) + MAC (6 bytes) + valid (1 byte) + age (1 byte) = 12 bytes
ARP_CACHE_SIZE: int32 = 16
ARP_ENTRY_SIZE: int32 = 12
_arp_cache: Array[192, uint8]   # 16 * 12 = 192 bytes

# Statistics
_ip_tx_count: uint32 = 0
_ip_rx_count: uint32 = 0
_ip_errors: uint32 = 0

# ============================================================================
# IP Address Utilities
# ============================================================================

def ip_addr_from_bytes(a: uint8, b: uint8, c: uint8, d: uint8) -> uint32:
    """Create IP address from bytes (a.b.c.d)."""
    return (cast[uint32](a) << 24) | (cast[uint32](b) << 16) | (cast[uint32](c) << 8) | cast[uint32](d)

def ip_addr_to_ptr(addr: uint32, buf: Ptr[uint8]):
    """Write IP address to buffer (network byte order)."""
    buf[0] = cast[uint8]((addr >> 24) & 0xFF)
    buf[1] = cast[uint8]((addr >> 16) & 0xFF)
    buf[2] = cast[uint8]((addr >> 8) & 0xFF)
    buf[3] = cast[uint8](addr & 0xFF)

def ip_addr_from_ptr(buf: Ptr[uint8]) -> uint32:
    """Read IP address from buffer (network byte order)."""
    return (cast[uint32](buf[0]) << 24) | (cast[uint32](buf[1]) << 16) | \
           (cast[uint32](buf[2]) << 8) | cast[uint32](buf[3])

def ip_is_broadcast(addr: uint32) -> bool:
    """Check if IP address is broadcast."""
    if addr == 0xFFFFFFFF:
        return True
    # Check subnet broadcast
    if _ip_netmask != 0:
        subnet_broadcast: uint32 = (_ip_addr & _ip_netmask) | (~_ip_netmask)
        if addr == subnet_broadcast:
            return True
    return False

def ip_is_multicast(addr: uint32) -> bool:
    """Check if IP address is multicast (224.0.0.0 - 239.255.255.255)."""
    first_octet: uint32 = (addr >> 24) & 0xFF
    return first_octet >= 224 and first_octet <= 239

def ip_is_local(addr: uint32) -> bool:
    """Check if IP address is on our local network."""
    if _ip_netmask == 0:
        return True  # No netmask, assume local
    return (_ip_addr & _ip_netmask) == (addr & _ip_netmask)

# ============================================================================
# Initialization
# ============================================================================

def ip_init(ip_addr: uint32, netmask: uint32, gateway: uint32):
    """Initialize IP layer with network configuration.

    Args:
        ip_addr: Our IP address
        netmask: Network mask
        gateway: Default gateway
    """
    global _ip_addr, _ip_netmask, _ip_gateway, _ip_initialized
    global _ip_id_counter, _ip_tx_count, _ip_rx_count, _ip_errors

    _ip_addr = ip_addr
    _ip_netmask = netmask
    _ip_gateway = gateway

    _ip_id_counter = 1
    _ip_tx_count = 0
    _ip_rx_count = 0
    _ip_errors = 0

    # Clear ARP cache
    memset(&_arp_cache[0], 0, ARP_CACHE_SIZE * ARP_ENTRY_SIZE)

    _ip_initialized = True

def ip_set_addr(ip_addr: uint32):
    """Set IP address."""
    global _ip_addr
    _ip_addr = ip_addr

def ip_get_addr() -> uint32:
    """Get our IP address."""
    return _ip_addr

def ip_get_netmask() -> uint32:
    """Get network mask."""
    return _ip_netmask

def ip_get_gateway() -> uint32:
    """Get default gateway."""
    return _ip_gateway

def ip_is_initialized() -> bool:
    """Check if IP layer is initialized."""
    return _ip_initialized

# ============================================================================
# Checksum Calculation
# ============================================================================

def ip_checksum(data: Ptr[uint8], length: int32) -> uint16:
    """Calculate IP checksum (one's complement sum).

    Args:
        data: Data to checksum
        length: Length in bytes

    Returns:
        16-bit checksum
    """
    sum: uint32 = 0
    i: int32 = 0

    # Sum 16-bit words
    while i < length - 1:
        word: uint32 = (cast[uint32](data[i]) << 8) | cast[uint32](data[i + 1])
        sum = sum + word
        i = i + 2

    # Add odd byte if present
    if i < length:
        sum = sum + (cast[uint32](data[i]) << 8)

    # Fold 32-bit sum to 16 bits
    while (sum >> 16) != 0:
        sum = (sum & 0xFFFF) + (sum >> 16)

    # One's complement
    return cast[uint16](~sum & 0xFFFF)

def ip_verify_checksum(data: Ptr[uint8], length: int32) -> bool:
    """Verify IP checksum. Returns True if valid."""
    return ip_checksum(data, length) == 0

# ============================================================================
# ARP Cache (Simple Implementation)
# ============================================================================

def _arp_get_entry(index: int32) -> Ptr[uint8]:
    """Get pointer to ARP cache entry."""
    return &_arp_cache[index * ARP_ENTRY_SIZE]

def _arp_lookup(ip: uint32) -> Ptr[uint8]:
    """Look up MAC address for IP. Returns pointer to MAC or null."""
    i: int32 = 0
    while i < ARP_CACHE_SIZE:
        entry: Ptr[uint8] = _arp_get_entry(i)
        if entry[10] != 0:  # Valid flag
            entry_ip: uint32 = ip_addr_from_ptr(entry)
            if entry_ip == ip:
                return &entry[4]  # MAC address
        i = i + 1
    return Ptr[uint8](0)

def _arp_add(ip: uint32, mac: Ptr[uint8]):
    """Add entry to ARP cache."""
    # First check if already exists
    i: int32 = 0
    while i < ARP_CACHE_SIZE:
        entry: Ptr[uint8] = _arp_get_entry(i)
        if entry[10] != 0:
            entry_ip: uint32 = ip_addr_from_ptr(entry)
            if entry_ip == ip:
                # Update existing entry
                memcpy(&entry[4], mac, 6)
                entry[11] = 0  # Reset age
                return
        i = i + 1

    # Find empty or oldest entry
    oldest_idx: int32 = 0
    oldest_age: int32 = -1
    i = 0
    while i < ARP_CACHE_SIZE:
        entry: Ptr[uint8] = _arp_get_entry(i)
        if entry[10] == 0:
            # Empty slot
            oldest_idx = i
            break
        if cast[int32](entry[11]) > oldest_age:
            oldest_age = cast[int32](entry[11])
            oldest_idx = i
        i = i + 1

    # Add entry
    entry: Ptr[uint8] = _arp_get_entry(oldest_idx)
    ip_addr_to_ptr(ip, entry)
    memcpy(&entry[4], mac, 6)
    entry[10] = 1  # Valid
    entry[11] = 0  # Age

def arp_add_static(ip: uint32, mac: Ptr[uint8]):
    """Add static ARP entry."""
    _arp_add(ip, mac)

def arp_clear():
    """Clear ARP cache."""
    memset(&_arp_cache[0], 0, ARP_CACHE_SIZE * ARP_ENTRY_SIZE)

# ============================================================================
# Packet Transmission
# ============================================================================

def ip_send(dst_ip: uint32, protocol: uint8, data: Ptr[uint8], length: int32) -> bool:
    """Send an IP packet.

    Args:
        dst_ip: Destination IP address
        protocol: IP protocol (e.g., IP_PROTO_TCP, IP_PROTO_UDP)
        data: Payload data
        length: Payload length

    Returns:
        True on success, False on failure
    """
    global _ip_id_counter, _ip_tx_count, _ip_errors

    if not _ip_initialized:
        _ip_errors = _ip_errors + 1
        return False

    if length < 0 or length > IP_MAX_PAYLOAD:
        _ip_errors = _ip_errors + 1
        return False

    # Build IP header + payload
    packet: Array[1500, uint8]
    total_len: int32 = IP_HEADER_MIN + length

    # Version (4) + IHL (5 = 20 bytes)
    packet[IP_VER_IHL_OFFSET] = 0x45

    # Type of Service
    packet[IP_TOS_OFFSET] = IP_DEFAULT_TOS

    # Total Length
    packet[IP_LEN_OFFSET] = cast[uint8]((total_len >> 8) & 0xFF)
    packet[IP_LEN_OFFSET + 1] = cast[uint8](total_len & 0xFF)

    # Identification
    packet[IP_ID_OFFSET] = cast[uint8]((_ip_id_counter >> 8) & 0xFF)
    packet[IP_ID_OFFSET + 1] = cast[uint8](_ip_id_counter & 0xFF)
    _ip_id_counter = _ip_id_counter + 1

    # Flags + Fragment Offset (DF=1, no fragmentation)
    packet[IP_FLAGS_OFFSET] = 0x40  # Don't fragment
    packet[IP_FLAGS_OFFSET + 1] = 0x00

    # TTL
    packet[IP_TTL_OFFSET] = IP_DEFAULT_TTL

    # Protocol
    packet[IP_PROTO_OFFSET] = protocol

    # Checksum (set to 0 for calculation)
    packet[IP_CHECKSUM_OFFSET] = 0
    packet[IP_CHECKSUM_OFFSET + 1] = 0

    # Source address
    ip_addr_to_ptr(_ip_addr, &packet[IP_SRC_OFFSET])

    # Destination address
    ip_addr_to_ptr(dst_ip, &packet[IP_DST_OFFSET])

    # Calculate header checksum
    checksum: uint16 = ip_checksum(&packet[0], IP_HEADER_MIN)
    packet[IP_CHECKSUM_OFFSET] = cast[uint8]((checksum >> 8) & 0xFF)
    packet[IP_CHECKSUM_OFFSET + 1] = cast[uint8](checksum & 0xFF)

    # Copy payload
    i: int32 = 0
    while i < length:
        packet[IP_HEADER_MIN + i] = data[i]
        i = i + 1

    # Determine next-hop MAC address
    next_hop_ip: uint32 = dst_ip
    if not ip_is_local(dst_ip) and not ip_is_broadcast(dst_ip):
        next_hop_ip = _ip_gateway

    # Look up MAC in ARP cache
    dst_mac: Ptr[uint8] = _arp_lookup(next_hop_ip)

    if cast[uint32](dst_mac) == 0:
        # For loopback testing, use broadcast if not in cache
        if ip_is_broadcast(dst_ip):
            dst_mac = cast[Ptr[uint8]](&_arp_cache[0])
            # Set to broadcast MAC
            i = 0
            while i < 6:
                dst_mac[i] = 0xFF
                i = i + 1
        else:
            # Use our own MAC for loopback testing
            dst_mac = eth_get_mac()

    # Send via Ethernet
    result: bool = eth_send(dst_mac, ETHERTYPE_IPV4, &packet[0], total_len)

    if result:
        _ip_tx_count = _ip_tx_count + 1
    else:
        _ip_errors = _ip_errors + 1

    return result

# ============================================================================
# Packet Reception
# ============================================================================

def ip_receive(buf: Ptr[uint8], maxlen: int32) -> int32:
    """Receive an IP packet (payload only).

    Note: This extracts IP payload from Ethernet frames.

    Args:
        buf: Buffer for IP payload
        maxlen: Maximum buffer size

    Returns:
        Payload length on success, 0 if no packet, -1 on error
    """
    global _ip_rx_count, _ip_errors

    if not _ip_initialized:
        return -1

    # Receive Ethernet frame
    frame: Array[1514, uint8]
    frame_len: int32 = eth_receive(&frame[0], 1514)

    if frame_len <= 0:
        return frame_len

    # Skip Ethernet header, check if IP
    if frame_len < ETH_HEADER_LEN + IP_HEADER_MIN:
        _ip_errors = _ip_errors + 1
        return -1

    # Get IP header from payload
    ip_pkt: Ptr[uint8] = &frame[ETH_HEADER_LEN]

    # Verify IP version
    version: uint8 = (ip_pkt[IP_VER_IHL_OFFSET] >> 4) & 0x0F
    if version != 4:
        _ip_errors = _ip_errors + 1
        return -1

    # Get header length
    ihl: int32 = cast[int32](ip_pkt[IP_VER_IHL_OFFSET] & 0x0F) * 4
    if ihl < IP_HEADER_MIN:
        _ip_errors = _ip_errors + 1
        return -1

    # Verify checksum
    if not ip_verify_checksum(ip_pkt, ihl):
        _ip_errors = _ip_errors + 1
        return -1

    # Get total length
    total_len: int32 = (cast[int32](ip_pkt[IP_LEN_OFFSET]) << 8) | cast[int32](ip_pkt[IP_LEN_OFFSET + 1])
    payload_len: int32 = total_len - ihl

    if payload_len < 0 or payload_len > maxlen:
        _ip_errors = _ip_errors + 1
        return -1

    # Check if packet is for us
    dst_ip: uint32 = ip_addr_from_ptr(&ip_pkt[IP_DST_OFFSET])
    if dst_ip != _ip_addr and not ip_is_broadcast(dst_ip) and not ip_is_multicast(dst_ip):
        return 0  # Not for us

    # Copy payload
    i: int32 = 0
    while i < payload_len:
        buf[i] = ip_pkt[ihl + i]
        i = i + 1

    _ip_rx_count = _ip_rx_count + 1

    return payload_len

def ip_receive_full(buf: Ptr[uint8], maxlen: int32, src_ip: Ptr[uint32], protocol: Ptr[uint8]) -> int32:
    """Receive an IP packet with source info.

    Args:
        buf: Buffer for IP payload
        maxlen: Maximum buffer size
        src_ip: Output for source IP address
        protocol: Output for protocol

    Returns:
        Payload length on success, 0 if no packet, -1 on error
    """
    global _ip_rx_count, _ip_errors

    if not _ip_initialized:
        return -1

    # Receive Ethernet frame
    frame: Array[1514, uint8]
    frame_len: int32 = eth_receive(&frame[0], 1514)

    if frame_len <= 0:
        return frame_len

    if frame_len < ETH_HEADER_LEN + IP_HEADER_MIN:
        _ip_errors = _ip_errors + 1
        return -1

    ip_pkt: Ptr[uint8] = &frame[ETH_HEADER_LEN]

    # Verify IP version
    version: uint8 = (ip_pkt[IP_VER_IHL_OFFSET] >> 4) & 0x0F
    if version != 4:
        _ip_errors = _ip_errors + 1
        return -1

    ihl: int32 = cast[int32](ip_pkt[IP_VER_IHL_OFFSET] & 0x0F) * 4
    if ihl < IP_HEADER_MIN:
        _ip_errors = _ip_errors + 1
        return -1

    if not ip_verify_checksum(ip_pkt, ihl):
        _ip_errors = _ip_errors + 1
        return -1

    total_len: int32 = (cast[int32](ip_pkt[IP_LEN_OFFSET]) << 8) | cast[int32](ip_pkt[IP_LEN_OFFSET + 1])
    payload_len: int32 = total_len - ihl

    if payload_len < 0 or payload_len > maxlen:
        _ip_errors = _ip_errors + 1
        return -1

    dst_ip: uint32 = ip_addr_from_ptr(&ip_pkt[IP_DST_OFFSET])
    if dst_ip != _ip_addr and not ip_is_broadcast(dst_ip) and not ip_is_multicast(dst_ip):
        return 0

    # Extract source IP and protocol
    src_ip[0] = ip_addr_from_ptr(&ip_pkt[IP_SRC_OFFSET])
    protocol[0] = ip_pkt[IP_PROTO_OFFSET]

    # Copy payload
    i: int32 = 0
    while i < payload_len:
        buf[i] = ip_pkt[ihl + i]
        i = i + 1

    _ip_rx_count = _ip_rx_count + 1

    return payload_len

# ============================================================================
# Statistics
# ============================================================================

def ip_get_tx_count() -> uint32:
    """Get transmitted packet count."""
    return _ip_tx_count

def ip_get_rx_count() -> uint32:
    """Get received packet count."""
    return _ip_rx_count

def ip_get_errors() -> uint32:
    """Get error count."""
    return _ip_errors

def ip_clear_stats():
    """Clear all statistics."""
    global _ip_tx_count, _ip_rx_count, _ip_errors
    _ip_tx_count = 0
    _ip_rx_count = 0
    _ip_errors = 0
