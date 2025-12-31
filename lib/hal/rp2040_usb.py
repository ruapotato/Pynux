# RP2040 USB Device Hardware Abstraction Layer
#
# USB 1.1 device driver for RP2040 with CDC (serial port) class support.
# The RP2040 has a built-in USB 1.1 device/host controller.
#
# Memory Map:
#   USB_DPRAM_BASE: 0x50100000 - 4KB DPRAM for USB buffers
#   USB_BASE:       0x50110000 - USB controller registers

# ============================================================================
# Base Addresses
# ============================================================================

USB_BASE: uint32 = 0x50110000
USB_DPRAM_BASE: uint32 = 0x50100000
USB_DPRAM_SIZE: uint32 = 4096

RESETS_BASE: uint32 = 0x4000C000

# ============================================================================
# USB Controller Register Offsets
# ============================================================================

USB_ADDR_ENDP: uint32 = 0x00              # Device address and endpoint control
USB_ADDR_ENDP1: uint32 = 0x04             # Interrupt endpoint 1
USB_ADDR_ENDP2: uint32 = 0x08             # Interrupt endpoint 2
USB_ADDR_ENDP3: uint32 = 0x0C             # Interrupt endpoint 3
USB_ADDR_ENDP4: uint32 = 0x10             # Interrupt endpoint 4
USB_ADDR_ENDP5: uint32 = 0x14             # Interrupt endpoint 5
USB_ADDR_ENDP6: uint32 = 0x18             # Interrupt endpoint 6
USB_ADDR_ENDP7: uint32 = 0x1C             # Interrupt endpoint 7
USB_ADDR_ENDP8: uint32 = 0x20             # Interrupt endpoint 8
USB_ADDR_ENDP9: uint32 = 0x24             # Interrupt endpoint 9
USB_ADDR_ENDP10: uint32 = 0x28            # Interrupt endpoint 10
USB_ADDR_ENDP11: uint32 = 0x2C            # Interrupt endpoint 11
USB_ADDR_ENDP12: uint32 = 0x30            # Interrupt endpoint 12
USB_ADDR_ENDP13: uint32 = 0x34            # Interrupt endpoint 13
USB_ADDR_ENDP14: uint32 = 0x38            # Interrupt endpoint 14
USB_ADDR_ENDP15: uint32 = 0x3C            # Interrupt endpoint 15

USB_MAIN_CTRL: uint32 = 0x40              # Main control register
USB_SOF_WR: uint32 = 0x44                 # Set SOF value (host mode)
USB_SOF_RD: uint32 = 0x48                 # Read current SOF value
USB_SIE_CTRL: uint32 = 0x4C               # SIE control register
USB_SIE_STATUS: uint32 = 0x50             # SIE status register
USB_INT_EP_CTRL: uint32 = 0x54            # Interrupt endpoint control
USB_BUFF_STATUS: uint32 = 0x58            # Buffer status register
USB_BUFF_CPU_SHOULD_HANDLE: uint32 = 0x5C # CPU should handle buffer
USB_ABORT: uint32 = 0x60                  # Abort control
USB_ABORT_DONE: uint32 = 0x64             # Abort done status
USB_EP_STALL_ARM: uint32 = 0x68           # Stall arm for endpoints
USB_NAK_POLL: uint32 = 0x6C               # NAK polling interval
USB_EP_STATUS_STALL_NAK: uint32 = 0x70    # Endpoint stall/NAK status
USB_USB_MUXING: uint32 = 0x74             # USB muxing control
USB_USB_PWR: uint32 = 0x78                # USB power control
USB_USBPHY_DIRECT: uint32 = 0x7C          # Direct PHY control
USB_USBPHY_DIRECT_OVERRIDE: uint32 = 0x80 # PHY direct override
USB_USBPHY_TRIM: uint32 = 0x84            # PHY trim values
USB_INTR: uint32 = 0x8C                   # Raw interrupts
USB_INTE: uint32 = 0x90                   # Interrupt enable
USB_INTF: uint32 = 0x94                   # Interrupt force
USB_INTS: uint32 = 0x98                   # Interrupt status

# ============================================================================
# USB MAIN_CTRL Register Bits
# ============================================================================

USB_MAIN_CTRL_CONTROLLER_EN: uint32 = 0x01        # Enable controller
USB_MAIN_CTRL_HOST_NDEVICE: uint32 = 0x02         # Host mode (0=device)
USB_MAIN_CTRL_SIM_TIMING: uint32 = 0x80000000     # Reduced timing for sim

# ============================================================================
# USB SIE_CTRL Register Bits
# ============================================================================

USB_SIE_CTRL_START_TRANS: uint32 = 0x01           # Start transaction
USB_SIE_CTRL_SEND_SETUP: uint32 = 0x02            # Send setup packet
USB_SIE_CTRL_SEND_DATA: uint32 = 0x04             # Send data packet
USB_SIE_CTRL_RECEIVE_DATA: uint32 = 0x08          # Receive data
USB_SIE_CTRL_STOP_TRANS: uint32 = 0x10            # Stop transaction
USB_SIE_CTRL_PREAMBLE_EN: uint32 = 0x40           # Preamble enable
USB_SIE_CTRL_SOF_SYNC: uint32 = 0x80              # SOF sync enable
USB_SIE_CTRL_SOF_EN: uint32 = 0x100               # SOF enable (host)
USB_SIE_CTRL_KEEP_ALIVE_EN: uint32 = 0x200        # Keep alive enable
USB_SIE_CTRL_VBUS_EN: uint32 = 0x400              # VBUS enable
USB_SIE_CTRL_RESUME: uint32 = 0x800               # Resume signaling
USB_SIE_CTRL_RESET_BUS: uint32 = 0x1000           # Reset bus
USB_SIE_CTRL_PULLUP_EN: uint32 = 0x10000          # Pull-up enable (device)
USB_SIE_CTRL_PULLDOWN_EN: uint32 = 0x20000        # Pull-down enable
USB_SIE_CTRL_TRANSCEIVER_PD: uint32 = 0x40000     # Transceiver power down
USB_SIE_CTRL_EP0_INT_NAK: uint32 = 0x4000000      # EP0 interrupt on NAK
USB_SIE_CTRL_EP0_INT_2BUF: uint32 = 0x8000000     # EP0 double buffer IRQ
USB_SIE_CTRL_EP0_INT_1BUF: uint32 = 0x10000000    # EP0 single buffer IRQ
USB_SIE_CTRL_EP0_DOUBLE_BUF: uint32 = 0x20000000  # EP0 double buffering
USB_SIE_CTRL_EP0_INT_STALL: uint32 = 0x40000000   # EP0 interrupt on stall
USB_SIE_CTRL_DIRECT_EN: uint32 = 0x80000000       # Direct control enable

# ============================================================================
# USB SIE_STATUS Register Bits
# ============================================================================

USB_SIE_STATUS_VBUS_DETECTED: uint32 = 0x01       # VBUS detected
USB_SIE_STATUS_LINE_STATE_MASK: uint32 = 0x06     # Line state
USB_SIE_STATUS_SUSPENDED: uint32 = 0x10           # Bus suspended
USB_SIE_STATUS_SPEED: uint32 = 0x100              # Speed (0=FS, 1=LS)
USB_SIE_STATUS_VBUS_OVER_CURR: uint32 = 0x200     # VBUS overcurrent
USB_SIE_STATUS_RESUME: uint32 = 0x800             # Resume detected
USB_SIE_STATUS_CONNECTED: uint32 = 0x10000        # Device connected
USB_SIE_STATUS_SETUP_REC: uint32 = 0x20000        # Setup received
USB_SIE_STATUS_TRANS_COMPLETE: uint32 = 0x40000   # Transaction complete
USB_SIE_STATUS_BUS_RESET: uint32 = 0x80000        # Bus reset detected
USB_SIE_STATUS_CRC_ERROR: uint32 = 0x1000000      # CRC error
USB_SIE_STATUS_BIT_STUFF_ERROR: uint32 = 0x2000000 # Bit stuffing error
USB_SIE_STATUS_RX_OVERFLOW: uint32 = 0x4000000    # RX overflow
USB_SIE_STATUS_RX_TIMEOUT: uint32 = 0x8000000     # RX timeout
USB_SIE_STATUS_NAK_REC: uint32 = 0x10000000       # NAK received
USB_SIE_STATUS_STALL_REC: uint32 = 0x20000000     # Stall received
USB_SIE_STATUS_ACK_REC: uint32 = 0x40000000       # ACK received
USB_SIE_STATUS_DATA_SEQ_ERROR: uint32 = 0x80000000 # Data sequence error

# ============================================================================
# USB Interrupt Bits
# ============================================================================

USB_INT_SETUP_REQ: uint32 = 0x01             # Setup packet received
USB_INT_DEV_CONN_DIS: uint32 = 0x02          # Device connect/disconnect
USB_INT_DEV_SUSPEND: uint32 = 0x04           # Device suspended
USB_INT_DEV_RESUME_FROM_HOST: uint32 = 0x08  # Resume from host
USB_INT_DEV_SOF: uint32 = 0x10               # Start of frame
USB_INT_BUFF_STATUS: uint32 = 0x20           # Buffer status
USB_INT_ERROR_CRC: uint32 = 0x40             # CRC error
USB_INT_ERROR_BIT_STUFF: uint32 = 0x80       # Bit stuff error
USB_INT_ERROR_RX_OVERFLOW: uint32 = 0x100    # RX overflow
USB_INT_ERROR_RX_TIMEOUT: uint32 = 0x200     # RX timeout
USB_INT_ERROR_DATA_SEQ: uint32 = 0x400       # Data sequence error
USB_INT_STALL: uint32 = 0x800                # Stall detected
USB_INT_VBUS_DETECT: uint32 = 0x1000         # VBUS detected
USB_INT_BUS_RESET: uint32 = 0x2000           # Bus reset
USB_INT_DEV_CONN: uint32 = 0x4000            # Device connected
USB_INT_EP_STALL_NAK: uint32 = 0x8000        # Endpoint stall/NAK
USB_INT_ABORT_DONE: uint32 = 0x10000         # Abort done

# ============================================================================
# USB Muxing Register Bits
# ============================================================================

USB_MUX_TO_PHY: uint32 = 0x01                # Route to internal PHY
USB_MUX_SOFTCON: uint32 = 0x08               # Soft connect

# ============================================================================
# USB Power Register Bits
# ============================================================================

USB_PWR_VBUS_DETECT: uint32 = 0x04           # VBUS detect enable
USB_PWR_VBUS_DETECT_OVERRIDE_EN: uint32 = 0x08

# ============================================================================
# Endpoint Types
# ============================================================================

USB_EP_TYPE_CONTROL: uint32 = 0x00
USB_EP_TYPE_ISOCHRONOUS: uint32 = 0x01
USB_EP_TYPE_BULK: uint32 = 0x02
USB_EP_TYPE_INTERRUPT: uint32 = 0x03

# ============================================================================
# USB Standard Request Codes (bRequest)
# ============================================================================

USB_REQ_GET_STATUS: uint8 = 0x00
USB_REQ_CLEAR_FEATURE: uint8 = 0x01
USB_REQ_SET_FEATURE: uint8 = 0x03
USB_REQ_SET_ADDRESS: uint8 = 0x05
USB_REQ_GET_DESCRIPTOR: uint8 = 0x06
USB_REQ_SET_DESCRIPTOR: uint8 = 0x07
USB_REQ_GET_CONFIGURATION: uint8 = 0x08
USB_REQ_SET_CONFIGURATION: uint8 = 0x09
USB_REQ_GET_INTERFACE: uint8 = 0x0A
USB_REQ_SET_INTERFACE: uint8 = 0x0B
USB_REQ_SYNCH_FRAME: uint8 = 0x0C

# ============================================================================
# USB Descriptor Types
# ============================================================================

USB_DESC_TYPE_DEVICE: uint8 = 0x01
USB_DESC_TYPE_CONFIGURATION: uint8 = 0x02
USB_DESC_TYPE_STRING: uint8 = 0x03
USB_DESC_TYPE_INTERFACE: uint8 = 0x04
USB_DESC_TYPE_ENDPOINT: uint8 = 0x05
USB_DESC_TYPE_DEVICE_QUALIFIER: uint8 = 0x06
USB_DESC_TYPE_OTHER_SPEED_CONFIG: uint8 = 0x07
USB_DESC_TYPE_INTERFACE_POWER: uint8 = 0x08
USB_DESC_TYPE_OTG: uint8 = 0x09
USB_DESC_TYPE_DEBUG: uint8 = 0x0A
USB_DESC_TYPE_INTERFACE_ASSOC: uint8 = 0x0B

# ============================================================================
# USB Request Type Bits
# ============================================================================

USB_REQ_TYPE_DIRECTION_MASK: uint8 = 0x80
USB_REQ_TYPE_DIRECTION_OUT: uint8 = 0x00
USB_REQ_TYPE_DIRECTION_IN: uint8 = 0x80
USB_REQ_TYPE_TYPE_MASK: uint8 = 0x60
USB_REQ_TYPE_TYPE_STANDARD: uint8 = 0x00
USB_REQ_TYPE_TYPE_CLASS: uint8 = 0x20
USB_REQ_TYPE_TYPE_VENDOR: uint8 = 0x40
USB_REQ_TYPE_RECIPIENT_MASK: uint8 = 0x1F
USB_REQ_TYPE_RECIPIENT_DEVICE: uint8 = 0x00
USB_REQ_TYPE_RECIPIENT_INTERFACE: uint8 = 0x01
USB_REQ_TYPE_RECIPIENT_ENDPOINT: uint8 = 0x02
USB_REQ_TYPE_RECIPIENT_OTHER: uint8 = 0x03

# ============================================================================
# CDC Class Codes
# ============================================================================

USB_CDC_CLASS_COMM: uint8 = 0x02             # Communications class
USB_CDC_CLASS_DATA: uint8 = 0x0A             # Data class
USB_CDC_SUBCLASS_ACM: uint8 = 0x02           # Abstract Control Model
USB_CDC_PROTOCOL_AT: uint8 = 0x01            # AT commands

# CDC Class Request Codes
USB_CDC_REQ_SEND_ENCAPSULATED_CMD: uint8 = 0x00
USB_CDC_REQ_GET_ENCAPSULATED_RESP: uint8 = 0x01
USB_CDC_REQ_SET_LINE_CODING: uint8 = 0x20
USB_CDC_REQ_GET_LINE_CODING: uint8 = 0x21
USB_CDC_REQ_SET_CONTROL_LINE_STATE: uint8 = 0x22
USB_CDC_REQ_SEND_BREAK: uint8 = 0x23

# ============================================================================
# DPRAM Buffer Layout
# ============================================================================
# DPRAM (4KB) layout for USB buffers:
#   0x000-0x07F: EP0 buffer control (setup packet + EP0 IN/OUT)
#   0x080-0x0FF: EP0 data buffer (64 bytes each direction)
#   0x100-0x17F: EP1 buffer control
#   0x180-0xXXX: EP1-15 data buffers

USB_DPRAM_EP0_BUF_CTRL: uint32 = 0x00
USB_DPRAM_SETUP_PACKET: uint32 = 0x00        # Setup packet at start
USB_DPRAM_EP0_IN_CTRL: uint32 = 0x08         # EP0 IN buffer control
USB_DPRAM_EP0_OUT_CTRL: uint32 = 0x0C        # EP0 OUT buffer control
USB_DPRAM_EP_CTRL_BASE: uint32 = 0x10        # EP1-15 control starts here
USB_DPRAM_EP_BUF_BASE: uint32 = 0x180        # EP data buffers start here

USB_EP0_BUFFER_SIZE: uint32 = 64
USB_MAX_PACKET_SIZE: uint32 = 64

# Buffer control bits (in DPRAM)
USB_BUF_CTRL_FULL: uint32 = 0x8000           # Buffer full
USB_BUF_CTRL_LAST: uint32 = 0x4000           # Last buffer of transfer
USB_BUF_CTRL_DATA_PID: uint32 = 0x2000       # Data PID (0=DATA0, 1=DATA1)
USB_BUF_CTRL_SEL: uint32 = 0x1000            # Double buffer select
USB_BUF_CTRL_STALL: uint32 = 0x800           # Stall
USB_BUF_CTRL_AVAIL: uint32 = 0x400           # Buffer available
USB_BUF_CTRL_LEN_MASK: uint32 = 0x3FF        # Transfer length mask

# Endpoint control bits
USB_EP_CTRL_ENABLE: uint32 = 0x80000000      # Endpoint enable
USB_EP_CTRL_DOUBLE_BUF: uint32 = 0x40000000  # Double buffer enable
USB_EP_CTRL_INT_1BUF: uint32 = 0x20000000    # IRQ on each buffer
USB_EP_CTRL_INT_2BUF: uint32 = 0x10000000    # IRQ every 2 buffers
USB_EP_CTRL_EP_TYPE_SHIFT: uint32 = 26       # Endpoint type shift
USB_EP_CTRL_INT_STALL: uint32 = 0x00020000   # IRQ on stall
USB_EP_CTRL_INT_NAK: uint32 = 0x00010000     # IRQ on NAK
USB_EP_CTRL_ADDR_MASK: uint32 = 0xFFFF       # Buffer address mask

# ============================================================================
# Driver State
# ============================================================================

# Device address
_usb_device_addr: uint8 = 0
_usb_pending_addr: uint8 = 0           # Address to set after STATUS

# Endpoint state tracking
_usb_ep_data_pid: Array[uint8, 16]     # Data toggle PID for each EP
_usb_ep_stalled: Array[bool, 16]       # Stall state for each EP
_usb_ep_buffer_addr: Array[uint32, 16] # Buffer address in DPRAM

# Callback function pointers
_usb_cb_setup: Ptr[Fn(Ptr[uint8])]                    # Setup packet callback
_usb_cb_transfer_complete: Ptr[Fn(uint8, int32)]      # Transfer complete (ep, len)
_usb_cb_bus_reset: Ptr[Fn()]                          # Bus reset callback
_usb_cb_suspend: Ptr[Fn()]                            # Suspend callback
_usb_cb_resume: Ptr[Fn()]                             # Resume callback

# CDC state
_cdc_connected: bool = False
_cdc_line_coding: Array[uint8, 7]      # Line coding (baud, stop, parity, bits)
_cdc_control_line_state: uint16 = 0

# ============================================================================
# Helper Functions
# ============================================================================

def mmio_read(addr: uint32) -> uint32:
    """Read from memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    return ptr[0]

def mmio_write(addr: uint32, val: uint32):
    """Write to memory-mapped I/O register."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](addr)
    ptr[0] = val

def dpram_read8(offset: uint32) -> uint8:
    """Read byte from DPRAM."""
    ptr: Ptr[volatile uint8] = cast[Ptr[volatile uint8]](USB_DPRAM_BASE + offset)
    return ptr[0]

def dpram_write8(offset: uint32, val: uint8):
    """Write byte to DPRAM."""
    ptr: Ptr[volatile uint8] = cast[Ptr[volatile uint8]](USB_DPRAM_BASE + offset)
    ptr[0] = val

def dpram_read32(offset: uint32) -> uint32:
    """Read 32-bit value from DPRAM."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](USB_DPRAM_BASE + offset)
    return ptr[0]

def dpram_write32(offset: uint32, val: uint32):
    """Write 32-bit value to DPRAM."""
    ptr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](USB_DPRAM_BASE + offset)
    ptr[0] = val

def memcpy_to_dpram(offset: uint32, src: Ptr[uint8], len: int32):
    """Copy data to DPRAM."""
    i: int32 = 0
    while i < len:
        dpram_write8(offset + cast[uint32](i), src[i])
        i = i + 1

def memcpy_from_dpram(dst: Ptr[uint8], offset: uint32, len: int32):
    """Copy data from DPRAM."""
    i: int32 = 0
    while i < len:
        dst[i] = dpram_read8(offset + cast[uint32](i))
        i = i + 1

# ============================================================================
# USB Device Core Functions
# ============================================================================

def usb_init():
    """Initialize USB hardware for device mode.

    Configures the USB controller, PHY, and prepares for device operation.
    Must be called before any other USB functions.
    """
    # Reset USB controller
    reset_val: uint32 = mmio_read(RESETS_BASE)
    mmio_write(RESETS_BASE, reset_val | (1 << 24))  # Assert reset

    # Short delay
    i: int32 = 0
    while i < 100:
        i = i + 1

    # Release reset
    mmio_write(RESETS_BASE, reset_val & ~(1 << 24))

    # Wait for reset done
    timeout: int32 = 10000
    while timeout > 0:
        done: uint32 = mmio_read(RESETS_BASE + 0x08)
        if (done & (1 << 24)) != 0:
            break
        timeout = timeout - 1

    # Clear DPRAM
    i = 0
    while i < cast[int32](USB_DPRAM_SIZE):
        dpram_write8(cast[uint32](i), 0)
        i = i + 1

    # Configure USB muxing to use internal PHY
    mmio_write(USB_BASE + USB_USB_MUXING, USB_MUX_TO_PHY | USB_MUX_SOFTCON)

    # Power on USB PHY
    mmio_write(USB_BASE + USB_USB_PWR,
               USB_PWR_VBUS_DETECT | USB_PWR_VBUS_DETECT_OVERRIDE_EN)

    # Enable USB controller in device mode
    mmio_write(USB_BASE + USB_MAIN_CTRL, USB_MAIN_CTRL_CONTROLLER_EN)

    # Initialize device address to 0
    _usb_device_addr = 0
    _usb_pending_addr = 0
    mmio_write(USB_BASE + USB_ADDR_ENDP, 0)

    # Initialize endpoint state
    ep: int32 = 0
    while ep < 16:
        _usb_ep_data_pid[ep] = 0
        _usb_ep_stalled[ep] = False
        _usb_ep_buffer_addr[ep] = 0
        ep = ep + 1

    # Clear all pending interrupts
    mmio_write(USB_BASE + USB_SIE_STATUS, 0xFFFFFFFF)

    # Enable device interrupts
    mmio_write(USB_BASE + USB_INTE,
               USB_INT_BUFF_STATUS |
               USB_INT_BUS_RESET |
               USB_INT_SETUP_REQ |
               USB_INT_DEV_SUSPEND |
               USB_INT_DEV_RESUME_FROM_HOST)

def usb_connect():
    """Connect USB device to the bus.

    Enables the pull-up resistor to signal device presence to the host.
    """
    ctrl: uint32 = mmio_read(USB_BASE + USB_SIE_CTRL)
    ctrl = ctrl | USB_SIE_CTRL_PULLUP_EN
    mmio_write(USB_BASE + USB_SIE_CTRL, ctrl)

def usb_disconnect():
    """Disconnect USB device from the bus.

    Disables the pull-up resistor to signal device disconnection.
    """
    ctrl: uint32 = mmio_read(USB_BASE + USB_SIE_CTRL)
    ctrl = ctrl & ~USB_SIE_CTRL_PULLUP_EN
    mmio_write(USB_BASE + USB_SIE_CTRL, ctrl)

def usb_set_address(addr: uint8):
    """Set USB device address.

    Args:
        addr: Device address (0-127) assigned by host

    Note: Address change takes effect after the STATUS stage.
    """
    _usb_pending_addr = addr

def _usb_apply_address():
    """Apply pending address after STATUS stage."""
    if _usb_pending_addr != 0:
        _usb_device_addr = _usb_pending_addr
        mmio_write(USB_BASE + USB_ADDR_ENDP, cast[uint32](_usb_device_addr))
        _usb_pending_addr = 0

def usb_get_address() -> uint8:
    """Get current USB device address.

    Returns:
        Current device address (0-127)
    """
    return _usb_device_addr

# ============================================================================
# Endpoint Management
# ============================================================================

def usb_endpoint_init(ep: uint8, ep_type: uint32, max_packet_size: uint16):
    """Configure an endpoint.

    Args:
        ep: Endpoint number (0-15, bit 7 = direction: 0=OUT, 0x80=IN)
        ep_type: USB_EP_TYPE_CONTROL, _BULK, _INTERRUPT, or _ISOCHRONOUS
        max_packet_size: Maximum packet size (up to 64 for FS)
    """
    ep_num: uint8 = ep & 0x0F
    ep_dir_in: bool = (ep & 0x80) != 0

    if ep_num >= 16:
        return

    # Calculate buffer address in DPRAM
    # EP0 uses fixed buffers, others get allocated space
    buf_addr: uint32 = 0
    if ep_num == 0:
        buf_addr = USB_DPRAM_EP_BUF_BASE
    else:
        # Simple allocation: each EP gets 128 bytes (64 per direction)
        buf_addr = USB_DPRAM_EP_BUF_BASE + (cast[uint32](ep_num) * 128)
        if ep_dir_in:
            buf_addr = buf_addr + 64

    _usb_ep_buffer_addr[cast[int32](ep_num)] = buf_addr

    # Configure endpoint control in DPRAM
    # EP0 is special and handled separately
    if ep_num > 0:
        # Calculate endpoint control register offset
        ctrl_offset: uint32 = USB_DPRAM_EP_CTRL_BASE + ((cast[uint32](ep_num) - 1) * 8)
        if ep_dir_in:
            ctrl_offset = ctrl_offset + 4

        # Configure endpoint
        ctrl: uint32 = USB_EP_CTRL_ENABLE
        ctrl = ctrl | (ep_type << USB_EP_CTRL_EP_TYPE_SHIFT)
        ctrl = ctrl | USB_EP_CTRL_INT_1BUF
        ctrl = ctrl | (buf_addr & USB_EP_CTRL_ADDR_MASK)

        dpram_write32(ctrl_offset, ctrl)

    # Reset data toggle
    _usb_ep_data_pid[cast[int32](ep_num)] = 0
    _usb_ep_stalled[cast[int32](ep_num)] = False

def usb_endpoint_start_transfer(ep: uint8, buffer: Ptr[uint8], len: int32):
    """Start a transfer on an endpoint.

    Args:
        ep: Endpoint number with direction (bit 7: 0=OUT, 0x80=IN)
        buffer: Data buffer
        len: Transfer length

    For IN endpoints, data is copied to DPRAM and transfer is started.
    For OUT endpoints, buffer is prepared to receive data.
    """
    ep_num: uint8 = ep & 0x0F
    ep_dir_in: bool = (ep & 0x80) != 0

    if ep_num >= 16:
        return

    buf_addr: uint32 = _usb_ep_buffer_addr[cast[int32](ep_num)]

    # Limit to max packet size
    xfer_len: int32 = len
    if xfer_len > cast[int32](USB_MAX_PACKET_SIZE):
        xfer_len = cast[int32](USB_MAX_PACKET_SIZE)

    # For IN transfers, copy data to DPRAM
    if ep_dir_in and buffer != cast[Ptr[uint8]](0) and xfer_len > 0:
        memcpy_to_dpram(buf_addr, buffer, xfer_len)

    # Calculate buffer control register offset
    buf_ctrl_offset: uint32 = 0
    if ep_num == 0:
        if ep_dir_in:
            buf_ctrl_offset = USB_DPRAM_EP0_IN_CTRL
        else:
            buf_ctrl_offset = USB_DPRAM_EP0_OUT_CTRL
    else:
        buf_ctrl_offset = USB_DPRAM_EP_CTRL_BASE + ((cast[uint32](ep_num) - 1) * 8)
        if ep_dir_in:
            buf_ctrl_offset = buf_ctrl_offset + 0x80  # Buffer control offset

    # Build buffer control value
    buf_ctrl: uint32 = cast[uint32](xfer_len) & USB_BUF_CTRL_LEN_MASK
    buf_ctrl = buf_ctrl | USB_BUF_CTRL_AVAIL

    # Set data PID
    if _usb_ep_data_pid[cast[int32](ep_num)] != 0:
        buf_ctrl = buf_ctrl | USB_BUF_CTRL_DATA_PID

    # For IN, mark buffer as full
    if ep_dir_in:
        buf_ctrl = buf_ctrl | USB_BUF_CTRL_FULL

    # Toggle data PID for next transfer
    if _usb_ep_data_pid[cast[int32](ep_num)] == 0:
        _usb_ep_data_pid[cast[int32](ep_num)] = 1
    else:
        _usb_ep_data_pid[cast[int32](ep_num)] = 0

    # Write buffer control
    dpram_write32(buf_ctrl_offset, buf_ctrl)

def usb_endpoint_stall(ep: uint8):
    """Stall an endpoint.

    Args:
        ep: Endpoint number with direction
    """
    ep_num: uint8 = ep & 0x0F

    if ep_num >= 16:
        return

    _usb_ep_stalled[cast[int32](ep_num)] = True

    # Set stall in endpoint buffer control
    if ep_num == 0:
        # Stall both directions for EP0
        buf_ctrl: uint32 = dpram_read32(USB_DPRAM_EP0_IN_CTRL)
        dpram_write32(USB_DPRAM_EP0_IN_CTRL, buf_ctrl | USB_BUF_CTRL_STALL)
        buf_ctrl = dpram_read32(USB_DPRAM_EP0_OUT_CTRL)
        dpram_write32(USB_DPRAM_EP0_OUT_CTRL, buf_ctrl | USB_BUF_CTRL_STALL)
    else:
        # Set EP_STALL_ARM register
        arm: uint32 = mmio_read(USB_BASE + USB_EP_STALL_ARM)
        arm = arm | (1 << ep_num)
        mmio_write(USB_BASE + USB_EP_STALL_ARM, arm)

def usb_endpoint_unstall(ep: uint8):
    """Clear stall condition on an endpoint.

    Args:
        ep: Endpoint number with direction
    """
    ep_num: uint8 = ep & 0x0F

    if ep_num >= 16:
        return

    _usb_ep_stalled[cast[int32](ep_num)] = False

    # Clear stall and reset data toggle
    _usb_ep_data_pid[cast[int32](ep_num)] = 0

    if ep_num == 0:
        buf_ctrl: uint32 = dpram_read32(USB_DPRAM_EP0_IN_CTRL)
        dpram_write32(USB_DPRAM_EP0_IN_CTRL, buf_ctrl & ~USB_BUF_CTRL_STALL)
        buf_ctrl = dpram_read32(USB_DPRAM_EP0_OUT_CTRL)
        dpram_write32(USB_DPRAM_EP0_OUT_CTRL, buf_ctrl & ~USB_BUF_CTRL_STALL)
    else:
        arm: uint32 = mmio_read(USB_BASE + USB_EP_STALL_ARM)
        arm = arm & ~(1 << ep_num)
        mmio_write(USB_BASE + USB_EP_STALL_ARM, arm)

def usb_endpoint_is_stalled(ep: uint8) -> bool:
    """Check if endpoint is stalled.

    Args:
        ep: Endpoint number with direction

    Returns:
        True if endpoint is stalled
    """
    ep_num: uint8 = ep & 0x0F

    if ep_num >= 16:
        return False

    return _usb_ep_stalled[cast[int32](ep_num)]

def usb_endpoint_reset_toggle(ep: uint8):
    """Reset data toggle for endpoint.

    Args:
        ep: Endpoint number with direction
    """
    ep_num: uint8 = ep & 0x0F

    if ep_num < 16:
        _usb_ep_data_pid[cast[int32](ep_num)] = 0

# ============================================================================
# Buffer Management
# ============================================================================

def usb_buffer_alloc(size: uint32) -> uint32:
    """Allocate buffer space in DPRAM.

    Args:
        size: Size needed in bytes

    Returns:
        Offset in DPRAM or 0 if allocation failed

    Note: This is a simple bump allocator. For complex applications,
    implement proper buffer management.
    """
    # Static allocation pointer
    # Start after EP control and standard buffers
    alloc_ptr: uint32 = USB_DPRAM_EP_BUF_BASE + (16 * 128)

    if alloc_ptr + size > USB_DPRAM_SIZE:
        return 0

    result: uint32 = alloc_ptr
    # Note: In a real implementation, track allocations
    return result

def usb_buffer_get_addr(ep: uint8) -> uint32:
    """Get DPRAM buffer address for endpoint.

    Args:
        ep: Endpoint number

    Returns:
        Buffer address in DPRAM
    """
    ep_num: uint8 = ep & 0x0F

    if ep_num >= 16:
        return 0

    return _usb_ep_buffer_addr[cast[int32](ep_num)]

def usb_buffer_read(ep: uint8, data: Ptr[uint8], max_len: int32) -> int32:
    """Read data from endpoint buffer.

    Args:
        ep: Endpoint number
        data: Destination buffer
        max_len: Maximum bytes to read

    Returns:
        Number of bytes read
    """
    ep_num: uint8 = ep & 0x0F

    if ep_num >= 16:
        return 0

    buf_addr: uint32 = _usb_ep_buffer_addr[cast[int32](ep_num)]

    # Get actual length from buffer control
    buf_ctrl_offset: uint32 = 0
    if ep_num == 0:
        buf_ctrl_offset = USB_DPRAM_EP0_OUT_CTRL
    else:
        buf_ctrl_offset = USB_DPRAM_EP_CTRL_BASE + ((cast[uint32](ep_num) - 1) * 8) + 0x80

    buf_ctrl: uint32 = dpram_read32(buf_ctrl_offset)
    len: int32 = cast[int32](buf_ctrl & USB_BUF_CTRL_LEN_MASK)

    if len > max_len:
        len = max_len

    memcpy_from_dpram(data, buf_addr, len)
    return len

def usb_buffer_write(ep: uint8, data: Ptr[uint8], len: int32):
    """Write data to endpoint buffer.

    Args:
        ep: Endpoint number
        data: Source data
        len: Number of bytes to write
    """
    ep_num: uint8 = ep & 0x0F

    if ep_num >= 16:
        return

    buf_addr: uint32 = _usb_ep_buffer_addr[cast[int32](ep_num)]

    if len > cast[int32](USB_MAX_PACKET_SIZE):
        len = cast[int32](USB_MAX_PACKET_SIZE)

    memcpy_to_dpram(buf_addr, data, len)

# ============================================================================
# Interrupt Handling
# ============================================================================

def usb_set_callback_setup(cb: Ptr[Fn(Ptr[uint8])]):
    """Set callback for setup packets.

    Args:
        cb: Callback function receiving pointer to 8-byte setup packet
    """
    _usb_cb_setup = cb

def usb_set_callback_transfer_complete(cb: Ptr[Fn(uint8, int32)]):
    """Set callback for transfer completion.

    Args:
        cb: Callback function receiving endpoint and transfer length
    """
    _usb_cb_transfer_complete = cb

def usb_set_callback_bus_reset(cb: Ptr[Fn()]):
    """Set callback for bus reset.

    Args:
        cb: Callback function
    """
    _usb_cb_bus_reset = cb

def usb_set_callback_suspend(cb: Ptr[Fn()]):
    """Set callback for bus suspend.

    Args:
        cb: Callback function
    """
    _usb_cb_suspend = cb

def usb_set_callback_resume(cb: Ptr[Fn()]):
    """Set callback for bus resume.

    Args:
        cb: Callback function
    """
    _usb_cb_resume = cb

def usb_irq_handler():
    """Main USB interrupt handler.

    Should be called from the USB interrupt vector.
    Dispatches to appropriate callbacks based on interrupt source.
    """
    status: uint32 = mmio_read(USB_BASE + USB_INTS)

    # Bus reset
    if (status & USB_INT_BUS_RESET) != 0:
        mmio_write(USB_BASE + USB_SIE_STATUS, USB_SIE_STATUS_BUS_RESET)
        _usb_device_addr = 0
        _usb_pending_addr = 0
        mmio_write(USB_BASE + USB_ADDR_ENDP, 0)

        # Reset all endpoint states
        ep: int32 = 0
        while ep < 16:
            _usb_ep_data_pid[ep] = 0
            _usb_ep_stalled[ep] = False
            ep = ep + 1

        if _usb_cb_bus_reset != cast[Ptr[Fn()]](0):
            _usb_cb_bus_reset()

    # Setup packet received
    if (status & USB_INT_SETUP_REQ) != 0:
        mmio_write(USB_BASE + USB_SIE_STATUS, USB_SIE_STATUS_SETUP_REC)

        # Reset EP0 data toggle
        _usb_ep_data_pid[0] = 1  # First data packet is DATA1

        if _usb_cb_setup != cast[Ptr[Fn(Ptr[uint8])]](0):
            # Setup packet is at start of DPRAM
            setup: Array[uint8, 8]
            i: int32 = 0
            while i < 8:
                setup[i] = dpram_read8(cast[uint32](i))
                i = i + 1
            _usb_cb_setup(cast[Ptr[uint8]](setup))

    # Buffer status (transfer complete)
    if (status & USB_INT_BUFF_STATUS) != 0:
        buf_status: uint32 = mmio_read(USB_BASE + USB_BUFF_STATUS)

        # Check each endpoint
        ep: int32 = 0
        while ep < 16:
            # Check IN endpoint (even bits)
            if (buf_status & (1 << (ep * 2))) != 0:
                if _usb_cb_transfer_complete != cast[Ptr[Fn(uint8, int32)]](0):
                    _usb_cb_transfer_complete(cast[uint8](ep) | 0x80, 0)

                # Apply pending address after EP0 IN (STATUS stage)
                if ep == 0:
                    _usb_apply_address()

            # Check OUT endpoint (odd bits)
            if (buf_status & (1 << (ep * 2 + 1))) != 0:
                if _usb_cb_transfer_complete != cast[Ptr[Fn(uint8, int32)]](0):
                    _usb_cb_transfer_complete(cast[uint8](ep), 0)

            ep = ep + 1

        # Clear buffer status
        mmio_write(USB_BASE + USB_BUFF_STATUS, buf_status)

    # Suspend
    if (status & USB_INT_DEV_SUSPEND) != 0:
        mmio_write(USB_BASE + USB_SIE_STATUS, USB_SIE_STATUS_SUSPENDED)
        if _usb_cb_suspend != cast[Ptr[Fn()]](0):
            _usb_cb_suspend()

    # Resume
    if (status & USB_INT_DEV_RESUME_FROM_HOST) != 0:
        mmio_write(USB_BASE + USB_SIE_STATUS, USB_SIE_STATUS_RESUME)
        if _usb_cb_resume != cast[Ptr[Fn()]](0):
            _usb_cb_resume()

# ============================================================================
# USB Utility Functions
# ============================================================================

def usb_is_configured() -> bool:
    """Check if device is configured (has address).

    Returns:
        True if device has been assigned an address
    """
    return _usb_device_addr != 0

def usb_get_frame_number() -> uint16:
    """Get current USB frame number.

    Returns:
        Frame number (0-2047)
    """
    return cast[uint16](mmio_read(USB_BASE + USB_SOF_RD) & 0x7FF)

def usb_remote_wakeup():
    """Signal remote wakeup to host."""
    ctrl: uint32 = mmio_read(USB_BASE + USB_SIE_CTRL)
    ctrl = ctrl | USB_SIE_CTRL_RESUME
    mmio_write(USB_BASE + USB_SIE_CTRL, ctrl)

    # Resume signal should be held for 1-15ms
    # In practice, hardware handles timing
    i: int32 = 0
    while i < 10000:
        i = i + 1

    ctrl = ctrl & ~USB_SIE_CTRL_RESUME
    mmio_write(USB_BASE + USB_SIE_CTRL, ctrl)

# ============================================================================
# CDC (Communications Device Class) Implementation
# ============================================================================

# CDC Endpoint configuration
CDC_EP_NOTIF: uint8 = 0x81        # Interrupt IN for notifications
CDC_EP_DATA_OUT: uint8 = 0x02     # Bulk OUT for data
CDC_EP_DATA_IN: uint8 = 0x82      # Bulk IN for data

# CDC internal buffers
_cdc_rx_buffer: Array[uint8, 64]
_cdc_rx_len: int32 = 0
_cdc_tx_buffer: Array[uint8, 64]
_cdc_tx_pending: bool = False

def cdc_init():
    """Initialize CDC serial port device.

    Configures the USB device as a CDC ACM (serial port) device.
    Call usb_init() first, then cdc_init(), then usb_connect().
    """
    # Initialize USB first if not done
    # (caller should do this, but check state)

    # Configure endpoints for CDC
    usb_endpoint_init(CDC_EP_NOTIF, USB_EP_TYPE_INTERRUPT, 8)
    usb_endpoint_init(CDC_EP_DATA_OUT, USB_EP_TYPE_BULK, 64)
    usb_endpoint_init(CDC_EP_DATA_IN, USB_EP_TYPE_BULK, 64)

    # Initialize line coding to defaults (115200 8N1)
    # dwDTERate (4 bytes, little endian): 115200 = 0x0001C200
    _cdc_line_coding[0] = 0x00
    _cdc_line_coding[1] = 0xC2
    _cdc_line_coding[2] = 0x01
    _cdc_line_coding[3] = 0x00
    # bCharFormat: 0 = 1 stop bit
    _cdc_line_coding[4] = 0x00
    # bParityType: 0 = none
    _cdc_line_coding[5] = 0x00
    # bDataBits: 8
    _cdc_line_coding[6] = 0x08

    _cdc_connected = False
    _cdc_control_line_state = 0
    _cdc_rx_len = 0
    _cdc_tx_pending = False

    # Prepare to receive data
    usb_endpoint_start_transfer(CDC_EP_DATA_OUT, cast[Ptr[uint8]](0), 64)

def cdc_write(data: Ptr[uint8], len: int32) -> int32:
    """Send data over CDC serial port.

    Args:
        data: Data to send
        len: Number of bytes to send

    Returns:
        Number of bytes queued for transmission
    """
    if not _cdc_connected:
        return 0

    # Wait for previous transfer to complete
    if _cdc_tx_pending:
        return 0

    # Limit to max packet size
    send_len: int32 = len
    if send_len > 64:
        send_len = 64

    # Copy to TX buffer and start transfer
    i: int32 = 0
    while i < send_len:
        _cdc_tx_buffer[i] = data[i]
        i = i + 1

    usb_endpoint_start_transfer(CDC_EP_DATA_IN,
                                cast[Ptr[uint8]](_cdc_tx_buffer), send_len)
    _cdc_tx_pending = True

    return send_len

def cdc_read(buffer: Ptr[uint8], max_len: int32) -> int32:
    """Read data from CDC serial port.

    Args:
        buffer: Buffer to store received data
        max_len: Maximum bytes to read

    Returns:
        Number of bytes read (0 if no data available)
    """
    if _cdc_rx_len == 0:
        return 0

    # Copy available data
    read_len: int32 = _cdc_rx_len
    if read_len > max_len:
        read_len = max_len

    i: int32 = 0
    while i < read_len:
        buffer[i] = _cdc_rx_buffer[i]
        i = i + 1

    # Shift remaining data (simple implementation)
    if read_len < _cdc_rx_len:
        j: int32 = 0
        while j < _cdc_rx_len - read_len:
            _cdc_rx_buffer[j] = _cdc_rx_buffer[j + read_len]
            j = j + 1

    _cdc_rx_len = _cdc_rx_len - read_len

    # If buffer empty, prepare for more data
    if _cdc_rx_len == 0:
        usb_endpoint_start_transfer(CDC_EP_DATA_OUT, cast[Ptr[uint8]](0), 64)

    return read_len

def cdc_connected() -> bool:
    """Check if CDC port is connected.

    Returns:
        True if host has opened the serial port
    """
    return _cdc_connected

def cdc_available() -> int32:
    """Get number of bytes available to read.

    Returns:
        Number of bytes in receive buffer
    """
    return _cdc_rx_len

def cdc_flush():
    """Wait for all pending transmissions to complete."""
    timeout: int32 = 100000
    while _cdc_tx_pending and timeout > 0:
        timeout = timeout - 1

def cdc_set_line_coding(coding: Ptr[uint8]):
    """Set line coding (called by USB stack on SET_LINE_CODING).

    Args:
        coding: 7-byte line coding structure
    """
    i: int32 = 0
    while i < 7:
        _cdc_line_coding[i] = coding[i]
        i = i + 1

def cdc_get_line_coding(coding: Ptr[uint8]):
    """Get current line coding.

    Args:
        coding: Buffer to receive 7-byte line coding structure
    """
    i: int32 = 0
    while i < 7:
        coding[i] = _cdc_line_coding[i]
        i = i + 1

def cdc_set_control_line_state(state: uint16):
    """Set control line state (called by USB stack).

    Args:
        state: Control line state (bit 0 = DTR, bit 1 = RTS)
    """
    _cdc_control_line_state = state
    # DTR is typically used to indicate terminal ready
    _cdc_connected = (state & 0x01) != 0

def cdc_handle_class_request(setup: Ptr[uint8]) -> bool:
    """Handle CDC class-specific requests.

    Args:
        setup: 8-byte setup packet

    Returns:
        True if request was handled
    """
    request: uint8 = setup[1]
    wValue: uint16 = cast[uint16](setup[2]) | (cast[uint16](setup[3]) << 8)
    wIndex: uint16 = cast[uint16](setup[4]) | (cast[uint16](setup[5]) << 8)
    wLength: uint16 = cast[uint16](setup[6]) | (cast[uint16](setup[7]) << 8)

    if request == USB_CDC_REQ_SET_LINE_CODING:
        # Host will send 7 bytes of line coding data
        # Prepare to receive it on EP0 OUT
        usb_endpoint_start_transfer(0x00, cast[Ptr[uint8]](0),
                                    cast[int32](wLength))
        return True

    elif request == USB_CDC_REQ_GET_LINE_CODING:
        # Send current line coding
        usb_endpoint_start_transfer(0x80, cast[Ptr[uint8]](_cdc_line_coding), 7)
        return True

    elif request == USB_CDC_REQ_SET_CONTROL_LINE_STATE:
        cdc_set_control_line_state(wValue)
        # Send zero-length status
        usb_endpoint_start_transfer(0x80, cast[Ptr[uint8]](0), 0)
        return True

    return False

def cdc_handle_transfer_complete(ep: uint8, len: int32):
    """Handle transfer completion for CDC endpoints.

    Args:
        ep: Endpoint that completed
        len: Transfer length
    """
    ep_num: uint8 = ep & 0x0F
    ep_dir_in: bool = (ep & 0x80) != 0

    if ep == CDC_EP_DATA_IN:
        # TX complete
        _cdc_tx_pending = False

    elif ep == CDC_EP_DATA_OUT:
        # RX complete - read data from buffer
        if _cdc_rx_len < 64:
            received: int32 = usb_buffer_read(ep,
                cast[Ptr[uint8]](_cdc_rx_buffer) + _cdc_rx_len,
                64 - _cdc_rx_len)
            _cdc_rx_len = _cdc_rx_len + received

        # Prepare for more data if buffer has space
        if _cdc_rx_len < 64:
            usb_endpoint_start_transfer(CDC_EP_DATA_OUT, cast[Ptr[uint8]](0), 64)

def cdc_putc(c: uint8):
    """Send single character over CDC.

    Args:
        c: Character to send
    """
    buf: Array[uint8, 1]
    buf[0] = c
    while cdc_write(cast[Ptr[uint8]](buf), 1) == 0:
        pass

def cdc_getc() -> int32:
    """Read single character from CDC.

    Returns:
        Character (0-255) or -1 if no data available
    """
    buf: Array[uint8, 1]
    if cdc_read(cast[Ptr[uint8]](buf), 1) > 0:
        return cast[int32](buf[0])
    return -1

def cdc_puts(s: Ptr[char]):
    """Send null-terminated string over CDC.

    Args:
        s: String to send
    """
    i: int32 = 0
    while s[i] != 0:
        cdc_putc(cast[uint8](s[i]))
        i = i + 1
