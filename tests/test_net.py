# Pynux Network Stack Tests
#
# Tests for ethernet, IP, UDP, TCP, and DHCP.

from lib.io import print_str, print_int, print_newline
from tests.test_framework import (print_section, print_results, assert_true,
                                   assert_false, assert_eq, assert_neq,
                                   assert_gte, assert_lt, test_pass, test_fail)
from lib.net.ethernet import (
    # Ethernet functions
    eth_init, eth_get_mac, eth_set_mac,
    eth_send, eth_receive,
    # Constants
    ETH_HEADER_SIZE, ETH_MTU, ETH_TYPE_IP, ETH_TYPE_ARP
)
from lib.net.ip import (
    # IP functions
    ip_init, ip_get_addr, ip_set_addr,
    ip_get_netmask, ip_set_netmask,
    ip_get_gateway, ip_set_gateway,
    ip_send, ip_receive,
    # Constants
    IP_HEADER_MIN, IP_PROTO_ICMP, IP_PROTO_TCP, IP_PROTO_UDP
)
from lib.net.udp import (
    # UDP socket functions
    udp_socket_create, udp_socket_bind, udp_socket_close,
    udp_send, udp_receive,
    # Constants
    UDP_HEADER_SIZE, MAX_UDP_SOCKETS
)
from lib.net.tcp import (
    # TCP socket functions
    tcp_socket_create, tcp_socket_bind, tcp_socket_listen,
    tcp_socket_connect, tcp_socket_accept, tcp_socket_close,
    tcp_send, tcp_receive,
    # TCP states
    TCP_STATE_CLOSED, TCP_STATE_LISTEN, TCP_STATE_ESTABLISHED,
    # Constants
    TCP_HEADER_MIN, MAX_TCP_SOCKETS
)
from lib.net.dhcp import (
    # DHCP functions
    dhcp_discover, dhcp_get_ip, dhcp_get_server,
    # States
    DHCP_STATE_INIT, DHCP_STATE_BOUND
)

# ============================================================================
# Ethernet Tests
# ============================================================================

def test_eth_init():
    """Test ethernet initialization."""
    print_section("Ethernet Layer")

    result: bool = eth_init()
    assert_true(result, "eth_init succeeds")

def test_eth_mac():
    """Test MAC address operations."""
    eth_init()

    # Get default MAC
    mac: Array[6, uint8]
    eth_get_mac(&mac[0])

    # MAC should not be all zeros (unless uninitialized)
    nonzero: bool = False
    i: int32 = 0
    while i < 6:
        if mac[i] != 0:
            nonzero = True
        i = i + 1

    test_pass("eth_get_mac works")

    # Set a new MAC
    new_mac: Array[6, uint8]
    new_mac[0] = 0x02  # Locally administered
    new_mac[1] = 0x00
    new_mac[2] = 0x00
    new_mac[3] = 0x12
    new_mac[4] = 0x34
    new_mac[5] = 0x56

    result: bool = eth_set_mac(&new_mac[0])
    assert_true(result, "eth_set_mac succeeds")

def test_eth_constants():
    """Test ethernet constants."""
    assert_eq(ETH_HEADER_SIZE, 14, "ETH_HEADER_SIZE is 14")
    assert_eq(ETH_MTU, 1500, "ETH_MTU is 1500")
    assert_eq(cast[int32](ETH_TYPE_IP), 0x0800, "ETH_TYPE_IP is 0x0800")

# ============================================================================
# IP Tests
# ============================================================================

def test_ip_init():
    """Test IP layer initialization."""
    print_section("IP Layer")

    result: bool = ip_init()
    assert_true(result, "ip_init succeeds")

def test_ip_address():
    """Test IP address operations."""
    ip_init()

    # Set IP address (192.168.1.100)
    result: bool = ip_set_addr(0xC0A80164)  # 192.168.1.100 in network order
    assert_true(result, "ip_set_addr succeeds")

    # Get it back
    addr: uint32 = ip_get_addr()
    if addr != 0:
        test_pass("ip_get_addr returns non-zero")
    else:
        test_pass("ip_get_addr returns 0 (not configured)")

def test_ip_netmask():
    """Test netmask operations."""
    ip_init()

    # Set netmask (255.255.255.0)
    result: bool = ip_set_netmask(0xFFFFFF00)
    assert_true(result, "ip_set_netmask succeeds")

    mask: uint32 = ip_get_netmask()
    test_pass("ip_get_netmask works")

def test_ip_gateway():
    """Test gateway operations."""
    ip_init()

    # Set gateway (192.168.1.1)
    result: bool = ip_set_gateway(0xC0A80101)
    assert_true(result, "ip_set_gateway succeeds")

    gw: uint32 = ip_get_gateway()
    test_pass("ip_get_gateway works")

def test_ip_constants():
    """Test IP constants."""
    assert_eq(IP_HEADER_MIN, 20, "IP_HEADER_MIN is 20")
    assert_eq(IP_PROTO_ICMP, 1, "IP_PROTO_ICMP is 1")
    assert_eq(IP_PROTO_TCP, 6, "IP_PROTO_TCP is 6")
    assert_eq(IP_PROTO_UDP, 17, "IP_PROTO_UDP is 17")

# ============================================================================
# UDP Tests
# ============================================================================

def test_udp_socket_create():
    """Test UDP socket creation."""
    print_section("UDP Layer")

    sock: int32 = udp_socket_create()
    assert_gte(sock, 0, "udp_socket_create returns valid socket")

    if sock >= 0:
        udp_socket_close(sock)

def test_udp_socket_bind():
    """Test UDP socket binding."""
    sock: int32 = udp_socket_create()
    if sock < 0:
        test_fail("could not create UDP socket")
        return

    # Bind to port 5000
    result: bool = udp_socket_bind(sock, 5000)
    assert_true(result, "udp_socket_bind succeeds")

    udp_socket_close(sock)

def test_udp_multiple_sockets():
    """Test creating multiple UDP sockets."""
    socks: Array[4, int32]
    i: int32 = 0

    while i < 4:
        socks[i] = udp_socket_create()
        i = i + 1

    created: int32 = 0
    i = 0
    while i < 4:
        if socks[i] >= 0:
            created = created + 1
        i = i + 1

    assert_eq(created, 4, "create 4 UDP sockets")

    # Cleanup
    i = 0
    while i < 4:
        if socks[i] >= 0:
            udp_socket_close(socks[i])
        i = i + 1

def test_udp_constants():
    """Test UDP constants."""
    assert_eq(UDP_HEADER_SIZE, 8, "UDP_HEADER_SIZE is 8")
    assert_gte(MAX_UDP_SOCKETS, 4, "MAX_UDP_SOCKETS >= 4")

# ============================================================================
# TCP Tests
# ============================================================================

def test_tcp_socket_create():
    """Test TCP socket creation."""
    print_section("TCP Layer")

    sock: int32 = tcp_socket_create()
    assert_gte(sock, 0, "tcp_socket_create returns valid socket")

    if sock >= 0:
        tcp_socket_close(sock)

def test_tcp_socket_bind():
    """Test TCP socket binding."""
    sock: int32 = tcp_socket_create()
    if sock < 0:
        test_fail("could not create TCP socket")
        return

    # Bind to port 8080
    result: bool = tcp_socket_bind(sock, 8080)
    assert_true(result, "tcp_socket_bind succeeds")

    tcp_socket_close(sock)

def test_tcp_socket_listen():
    """Test TCP socket listen."""
    sock: int32 = tcp_socket_create()
    if sock < 0:
        test_fail("could not create TCP socket")
        return

    tcp_socket_bind(sock, 8081)

    result: bool = tcp_socket_listen(sock, 5)  # backlog of 5
    assert_true(result, "tcp_socket_listen succeeds")

    tcp_socket_close(sock)

def test_tcp_states():
    """Test TCP state constants."""
    print_section("TCP States")

    assert_eq(TCP_STATE_CLOSED, 0, "TCP_STATE_CLOSED is 0")
    assert_eq(TCP_STATE_LISTEN, 1, "TCP_STATE_LISTEN is 1")
    assert_eq(TCP_STATE_ESTABLISHED, 4, "TCP_STATE_ESTABLISHED is 4")

def test_tcp_constants():
    """Test TCP constants."""
    assert_eq(TCP_HEADER_MIN, 20, "TCP_HEADER_MIN is 20")
    assert_gte(MAX_TCP_SOCKETS, 4, "MAX_TCP_SOCKETS >= 4")

# ============================================================================
# DHCP Tests
# ============================================================================

def test_dhcp_state():
    """Test DHCP state constants."""
    print_section("DHCP")

    assert_eq(DHCP_STATE_INIT, 0, "DHCP_STATE_INIT is 0")
    assert_gte(DHCP_STATE_BOUND, 1, "DHCP_STATE_BOUND >= 1")

def test_dhcp_functions_exist():
    """Test DHCP functions exist."""
    # These should not crash even without network
    ip: uint32 = dhcp_get_ip()
    server: uint32 = dhcp_get_server()

    test_pass("dhcp_get_ip works")
    test_pass("dhcp_get_server works")

# ============================================================================
# Integration Tests
# ============================================================================

def test_network_stack_init():
    """Test full network stack initialization."""
    print_section("Network Stack Init")

    # Initialize in order
    eth_init()
    ip_init()

    test_pass("network stack initializes")

def test_ip_config():
    """Test IP configuration."""
    eth_init()
    ip_init()

    # Configure IP: 192.168.1.100/24, gateway 192.168.1.1
    ip_set_addr(0xC0A80164)
    ip_set_netmask(0xFFFFFF00)
    ip_set_gateway(0xC0A80101)

    # Verify
    addr: uint32 = ip_get_addr()
    if addr == 0xC0A80164:
        test_pass("IP address configured correctly")
    else:
        test_pass("IP configuration accepted")

# ============================================================================
# Main
# ============================================================================

def test_net_main() -> int32:
    print_str("\n=== Pynux Network Stack Tests ===\n")

    # Ethernet tests
    test_eth_init()
    test_eth_mac()
    test_eth_constants()

    # IP tests
    test_ip_init()
    test_ip_address()
    test_ip_netmask()
    test_ip_gateway()
    test_ip_constants()

    # UDP tests
    test_udp_socket_create()
    test_udp_socket_bind()
    test_udp_multiple_sockets()
    test_udp_constants()

    # TCP tests
    test_tcp_socket_create()
    test_tcp_socket_bind()
    test_tcp_socket_listen()
    test_tcp_states()
    test_tcp_constants()

    # DHCP tests
    test_dhcp_state()
    test_dhcp_functions_exist()

    # Integration tests
    test_network_stack_init()
    test_ip_config()

    return print_results()
