# Pico W WiFi Driver (CYW43439)
#
# The Raspberry Pi Pico W uses an Infineon CYW43439 WiFi chip
# connected via SPI (directly to RP2040, not to exposed SPI pins).
#
# This driver provides a high-level WiFi API for networking.
#
# Hardware connections (internal):
#   GPIO23 - WL_ON (WiFi power enable)
#   GPIO24 - SPI_DATA/SPI_MOSI (directly connected, no GPIO function)
#   GPIO25 - SPI_CLK
#   GPIO29 - SPI_CS (directly connected)
#   RP2040 uses PIO for WiFi SPI communication
#
# Note: The LED on Pico W is connected through the WiFi chip (GPIO0 on CYW43)

# WiFi states
WIFI_STATE_OFF: int = 0
WIFI_STATE_IDLE: int = 1
WIFI_STATE_SCANNING: int = 2
WIFI_STATE_CONNECTING: int = 3
WIFI_STATE_CONNECTED: int = 4
WIFI_STATE_ERROR: int = 5

# Security modes
WIFI_SEC_OPEN: int = 0
WIFI_SEC_WPA: int = 1
WIFI_SEC_WPA2: int = 2
WIFI_SEC_WPA3: int = 3

# CYW43439 register addresses
CYW43_REG_STATUS: int = 0x0000
CYW43_REG_CONTROL: int = 0x0004
CYW43_REG_WLAN_DATA: int = 0x0008

# Power management
CYW43_PM_AGGRESSIVE: int = 0       # Maximum power savings
CYW43_PM_POWERSAVE: int = 1        # Balance power/performance
CYW43_PM_PERFORMANCE: int = 2     # Maximum performance

# GPIO for WiFi control
WL_GPIO_ON: int = 23

# Global state
_wifi_state: int = WIFI_STATE_OFF
_wifi_ssid: int = 0  # Pointer to SSID string
_wifi_ip: int = 0
_wifi_gateway: int = 0
_wifi_netmask: int = 0
_wifi_mac: int = 0  # Pointer to 6-byte MAC address

# Receive buffer
_rx_buffer: int = 0
_rx_buffer_size: int = 1500
_rx_data_len: int = 0


def wifi_init() -> int:
    """Initialize the WiFi subsystem.

    Returns 0 on success, negative on error.
    """
    global _wifi_state

    # Power on the WiFi chip via GPIO23
    # This requires SIO access for GPIO
    sio_base: int = 0xD0000000
    gpio_out_set: int = sio_base + 0x14
    gpio_oe_set: int = sio_base + 0x24

    # Set GPIO23 as output
    poke(gpio_oe_set, 1 << WL_GPIO_ON)

    # Power on WiFi chip
    poke(gpio_out_set, 1 << WL_GPIO_ON)

    # Wait for chip to initialize (about 150ms)
    delay_ms(150)

    # Initialize SPI communication with CYW43439
    # The Pico W uses PIO for WiFi SPI at higher speeds
    result: int = _cyw43_spi_init()
    if result < 0:
        _wifi_state = WIFI_STATE_ERROR
        return -1

    # Read chip ID and verify
    chip_id: int = _cyw43_read_reg(CYW43_REG_STATUS)
    if chip_id == 0 or chip_id == 0xFFFFFFFF:
        _wifi_state = WIFI_STATE_ERROR
        return -2

    # Initialize WLAN firmware
    result = _cyw43_init_wlan()
    if result < 0:
        _wifi_state = WIFI_STATE_ERROR
        return -3

    _wifi_state = WIFI_STATE_IDLE
    return 0


def wifi_deinit():
    """Shutdown the WiFi subsystem."""
    global _wifi_state

    if _wifi_state == WIFI_STATE_CONNECTED:
        wifi_disconnect()

    # Power off WiFi chip
    sio_base: int = 0xD0000000
    gpio_out_clr: int = sio_base + 0x18
    poke(gpio_out_clr, 1 << WL_GPIO_ON)

    _wifi_state = WIFI_STATE_OFF


def wifi_scan_start() -> int:
    """Start scanning for available networks.

    Returns 0 on success, negative on error.
    """
    global _wifi_state

    if _wifi_state != WIFI_STATE_IDLE:
        return -1

    result: int = _cyw43_cmd_scan()
    if result < 0:
        return result

    _wifi_state = WIFI_STATE_SCANNING
    return 0


def wifi_scan_get_result(index: int, ssid_buf: int, rssi_ptr: int) -> int:
    """Get scan result at index.

    Args:
        index: Result index (0-based)
        ssid_buf: Pointer to buffer for SSID (32 bytes)
        rssi_ptr: Pointer to store RSSI value

    Returns: 0 if result available, 1 if no more results, negative on error.
    """
    return _cyw43_get_scan_result(index, ssid_buf, rssi_ptr)


def wifi_connect(ssid: int, password: int, security: int) -> int:
    """Connect to a WiFi network.

    Args:
        ssid: Pointer to null-terminated SSID string
        password: Pointer to null-terminated password (or 0 for open)
        security: Security mode (WIFI_SEC_*)

    Returns: 0 on success, negative on error.
    """
    global _wifi_state, _wifi_ssid

    if _wifi_state != WIFI_STATE_IDLE and _wifi_state != WIFI_STATE_SCANNING:
        return -1

    _wifi_state = WIFI_STATE_CONNECTING
    _wifi_ssid = ssid

    # Send connect command to CYW43
    result: int = _cyw43_cmd_join(ssid, password, security)
    if result < 0:
        _wifi_state = WIFI_STATE_IDLE
        return result

    return 0


def wifi_connect_poll() -> int:
    """Poll connection status.

    Returns:
        0: Still connecting
        1: Connected successfully
        -1: Connection failed
    """
    global _wifi_state, _wifi_ip

    if _wifi_state != WIFI_STATE_CONNECTING:
        return -1

    status: int = _cyw43_get_link_status()

    if status == 0:
        # Still connecting
        return 0
    elif status == 1:
        # Connected, now get IP via DHCP
        result: int = _dhcp_request()
        if result < 0:
            _wifi_state = WIFI_STATE_ERROR
            return -1

        _wifi_state = WIFI_STATE_CONNECTED
        return 1
    else:
        # Connection failed
        _wifi_state = WIFI_STATE_IDLE
        return -1


def wifi_disconnect() -> int:
    """Disconnect from current network.

    Returns: 0 on success.
    """
    global _wifi_state

    if _wifi_state == WIFI_STATE_CONNECTED or _wifi_state == WIFI_STATE_CONNECTING:
        _cyw43_cmd_leave()

    _wifi_state = WIFI_STATE_IDLE
    return 0


def wifi_get_state() -> int:
    """Get current WiFi state."""
    return _wifi_state


def wifi_get_ip() -> int:
    """Get assigned IP address (as 32-bit integer)."""
    return _wifi_ip


def wifi_get_rssi() -> int:
    """Get current signal strength (RSSI in dBm)."""
    if _wifi_state != WIFI_STATE_CONNECTED:
        return 0

    return _cyw43_get_rssi()


# LED control (the Pico W LED is on the WiFi chip)
def wifi_led_on():
    """Turn on the onboard LED (requires WiFi initialized)."""
    _cyw43_gpio_set(0, 1)  # GPIO0 on CYW43 is the LED


def wifi_led_off():
    """Turn off the onboard LED."""
    _cyw43_gpio_set(0, 0)


# ============================================================================
# TCP/IP Functions (using chip's internal stack)
# ============================================================================

def wifi_tcp_connect(ip: int, port: int) -> int:
    """Open a TCP connection.

    Args:
        ip: Destination IP as 32-bit integer
        port: Destination port

    Returns: Socket handle (>= 0) or negative on error.
    """
    if _wifi_state != WIFI_STATE_CONNECTED:
        return -1

    return _cyw43_tcp_open(ip, port)


def wifi_tcp_send(sock: int, data: int, length: int) -> int:
    """Send data over TCP connection.

    Args:
        sock: Socket handle
        data: Pointer to data buffer
        length: Number of bytes to send

    Returns: Bytes sent or negative on error.
    """
    return _cyw43_tcp_send(sock, data, length)


def wifi_tcp_recv(sock: int, buf: int, max_len: int) -> int:
    """Receive data from TCP connection.

    Args:
        sock: Socket handle
        buf: Pointer to receive buffer
        max_len: Maximum bytes to receive

    Returns: Bytes received (0 = no data, negative = error/closed).
    """
    return _cyw43_tcp_recv(sock, buf, max_len)


def wifi_tcp_close(sock: int):
    """Close a TCP connection."""
    _cyw43_tcp_close(sock)


def wifi_udp_open(port: int) -> int:
    """Open a UDP socket.

    Args:
        port: Local port to bind (0 for any)

    Returns: Socket handle (>= 0) or negative on error.
    """
    if _wifi_state != WIFI_STATE_CONNECTED:
        return -1

    return _cyw43_udp_open(port)


def wifi_udp_send(sock: int, ip: int, port: int, data: int, length: int) -> int:
    """Send UDP datagram.

    Args:
        sock: Socket handle
        ip: Destination IP
        port: Destination port
        data: Pointer to data
        length: Data length

    Returns: Bytes sent or negative on error.
    """
    return _cyw43_udp_send(sock, ip, port, data, length)


def wifi_udp_recv(sock: int, buf: int, max_len: int, src_ip: int, src_port: int) -> int:
    """Receive UDP datagram.

    Args:
        sock: Socket handle
        buf: Receive buffer
        max_len: Buffer size
        src_ip: Pointer to store source IP
        src_port: Pointer to store source port

    Returns: Bytes received or negative on error.
    """
    return _cyw43_udp_recv(sock, buf, max_len, src_ip, src_port)


def wifi_udp_close(sock: int):
    """Close UDP socket."""
    _cyw43_udp_close(sock)


# ============================================================================
# Helper: IP address utilities
# ============================================================================

def ip_to_int(a: int, b: int, c: int, d: int) -> int:
    """Convert IP octets to 32-bit integer (network byte order)."""
    return (a << 24) | (b << 16) | (c << 8) | d


def ip_from_int(ip: int, buf: int):
    """Convert 32-bit IP to dotted string in buffer."""
    # This would format "192.168.1.1" etc.
    a: int = (ip >> 24) & 0xFF
    b: int = (ip >> 16) & 0xFF
    c: int = (ip >> 8) & 0xFF
    d: int = ip & 0xFF

    # Simple format into buffer (caller must provide 16 bytes)
    _format_octet(buf, a)
    pos: int = _strlen_simple(buf)
    pokeb(buf + pos, 46)  # '.'
    _format_octet(buf + pos + 1, b)
    pos = _strlen_simple(buf)
    pokeb(buf + pos, 46)
    _format_octet(buf + pos + 1, c)
    pos = _strlen_simple(buf)
    pokeb(buf + pos, 46)
    _format_octet(buf + pos + 1, d)


def _format_octet(buf: int, val: int):
    """Format a single octet (0-255) as decimal string."""
    if val >= 100:
        pokeb(buf, 48 + val // 100)
        pokeb(buf + 1, 48 + (val // 10) % 10)
        pokeb(buf + 2, 48 + val % 10)
        pokeb(buf + 3, 0)
    elif val >= 10:
        pokeb(buf, 48 + val // 10)
        pokeb(buf + 1, 48 + val % 10)
        pokeb(buf + 2, 0)
    else:
        pokeb(buf, 48 + val)
        pokeb(buf + 1, 0)


def _strlen_simple(s: int) -> int:
    """Get string length."""
    n: int = 0
    while peekb(s + n) != 0:
        n = n + 1
    return n


# ============================================================================
# Low-level CYW43439 driver (stub implementations)
# These would be implemented in assembly or use PIO for SPI
# ============================================================================

def _cyw43_spi_init() -> int:
    """Initialize PIO-based SPI for CYW43439."""
    # TODO: Initialize PIO state machine for high-speed SPI
    return 0


def _cyw43_read_reg(addr: int) -> int:
    """Read a 32-bit register from CYW43439."""
    # Placeholder - would use PIO SPI
    return 0


def _cyw43_write_reg(addr: int, value: int):
    """Write a 32-bit register to CYW43439."""
    pass


def _cyw43_init_wlan() -> int:
    """Initialize WLAN firmware and bring up interface."""
    # This loads firmware blob and configures the wireless interface
    return 0


def _cyw43_cmd_scan() -> int:
    """Start network scan."""
    return 0


def _cyw43_get_scan_result(index: int, ssid_buf: int, rssi_ptr: int) -> int:
    """Get scan result at index."""
    return 1  # No results (stub)


def _cyw43_cmd_join(ssid: int, password: int, security: int) -> int:
    """Join a wireless network."""
    return 0


def _cyw43_cmd_leave():
    """Leave current network."""
    pass


def _cyw43_get_link_status() -> int:
    """Get link status (0=disconnected, 1=connected)."""
    return 0


def _cyw43_get_rssi() -> int:
    """Get current RSSI."""
    return -50  # Placeholder


def _cyw43_gpio_set(gpio: int, value: int):
    """Set a GPIO pin on the CYW43439 (e.g., LED)."""
    pass


def _cyw43_tcp_open(ip: int, port: int) -> int:
    """Open TCP connection."""
    return -1  # Not implemented


def _cyw43_tcp_send(sock: int, data: int, length: int) -> int:
    """Send TCP data."""
    return -1


def _cyw43_tcp_recv(sock: int, buf: int, max_len: int) -> int:
    """Receive TCP data."""
    return -1


def _cyw43_tcp_close(sock: int):
    """Close TCP connection."""
    pass


def _cyw43_udp_open(port: int) -> int:
    """Open UDP socket."""
    return -1


def _cyw43_udp_send(sock: int, ip: int, port: int, data: int, length: int) -> int:
    """Send UDP datagram."""
    return -1


def _cyw43_udp_recv(sock: int, buf: int, max_len: int, src_ip: int, src_port: int) -> int:
    """Receive UDP datagram."""
    return -1


def _cyw43_udp_close(sock: int):
    """Close UDP socket."""
    pass


def _dhcp_request() -> int:
    """Request IP address via DHCP."""
    global _wifi_ip, _wifi_gateway, _wifi_netmask

    # Placeholder - would use CYW43's internal DHCP client
    # or implement our own over UDP
    _wifi_ip = ip_to_int(192, 168, 1, 100)
    _wifi_gateway = ip_to_int(192, 168, 1, 1)
    _wifi_netmask = ip_to_int(255, 255, 255, 0)

    return 0


def delay_ms(ms: int):
    """Simple delay in milliseconds."""
    # Busy-wait loop - should use timer for real implementation
    count: int = ms * 1000
    i: int = 0
    while i < count:
        i = i + 1


# Memory access primitives (these are built-in to Pynux)
def poke(addr: int, value: int):
    """Write 32-bit value to memory address."""
    pass  # Intrinsic


def peek(addr: int) -> int:
    """Read 32-bit value from memory address."""
    return 0  # Intrinsic


def pokeb(addr: int, value: int):
    """Write 8-bit value to memory address."""
    pass  # Intrinsic


def peekb(addr: int) -> int:
    """Read 8-bit value from memory address."""
    return 0  # Intrinsic
