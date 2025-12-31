# Pynux GDB Remote Protocol Stub
#
# GDB RSP (Remote Serial Protocol) implementation for bare-metal ARM Cortex-M3.
# Allows debugging via GDB over UART.
#
# Protocol reference: https://sourceware.org/gdb/current/onlinedocs/gdb/Remote-Protocol.html

from lib.io import uart_putc, uart_getc, uart_available, print_str, print_hex, print_newline
from kernel.debug import _saved_regs, NUM_CORE_REGS, REG_PC, REG_SP, REG_LR, REG_PSR
from kernel.debug import DCB_DHCSR, DHCSR_DBGKEY, DHCSR_C_DEBUGEN, DHCSR_C_HALT, DHCSR_C_STEP
from lib.breakpoint import bp_set, bp_clear, bp_list, bp_get_addr, bp_is_enabled, MAX_BREAKPOINTS

# ============================================================================
# GDB Stub Configuration
# ============================================================================

# Maximum packet size (must accommodate register dump)
GDB_PACKET_SIZE: int32 = 512

# UART instance for GDB (default to UART0)
_gdb_uart: int32 = 0

# GDB stub state
_gdb_initialized: bool = False
_gdb_connected: bool = False
_gdb_running: bool = False
_gdb_single_step: bool = False

# Packet buffers
_gdb_rx_buf: Array[512, char]
_gdb_tx_buf: Array[512, char]
_gdb_rx_len: int32 = 0
_gdb_tx_len: int32 = 0

# Signal numbers (Unix-style)
SIGNAL_TRAP: int32 = 5      # SIGTRAP (breakpoint, single-step)
SIGNAL_INT: int32 = 2       # SIGINT (interrupt)
SIGNAL_SEGV: int32 = 11     # SIGSEGV (memory fault)
SIGNAL_ILL: int32 = 4       # SIGILL (illegal instruction)
SIGNAL_BUS: int32 = 7       # SIGBUS (bus error)

# Current stop reason
_stop_signal: int32 = SIGNAL_TRAP

# ============================================================================
# GDB Stub Initialization
# ============================================================================

def gdb_init(uart_id: int32):
    """Initialize GDB stub on specified UART.

    Args:
        uart_id: UART instance number (0-2)
    """
    global _gdb_uart, _gdb_initialized, _gdb_connected, _gdb_running

    _gdb_uart = uart_id
    _gdb_initialized = True
    _gdb_connected = False
    _gdb_running = False

    # Clear buffers
    i: int32 = 0
    while i < GDB_PACKET_SIZE:
        _gdb_rx_buf[i] = '\0'
        _gdb_tx_buf[i] = '\0'
        i = i + 1

    print_str("[gdb] GDB stub initialized on UART")
    print_hex(cast[uint32](uart_id))
    print_newline()
    print_str("[gdb] Waiting for GDB connection...\n")

def gdb_is_initialized() -> bool:
    """Check if GDB stub is initialized."""
    return _gdb_initialized

def gdb_is_connected() -> bool:
    """Check if GDB is connected."""
    return _gdb_connected

# ============================================================================
# Packet Reception
# ============================================================================

def gdb_handle_packet():
    """Process incoming GDB command.

    Reads a packet from UART, processes it, and sends a response.
    Returns after processing one complete packet.
    """
    global _gdb_connected

    if not _gdb_initialized:
        return

    # Wait for packet start character '$'
    if not _wait_for_packet_start():
        return

    _gdb_connected = True

    # Read packet data until '#'
    if not _read_packet_data():
        _send_nak()
        return

    # Read and verify checksum
    if not _verify_checksum():
        _send_nak()
        return

    # Send ACK
    _send_ack()

    # Process the packet
    _process_packet()

def _wait_for_packet_start() -> bool:
    """Wait for '$' packet start character."""
    timeout: int32 = 100000

    while timeout > 0:
        if uart_available():
            c: char = uart_getc()

            if c == '$':
                return True
            elif c == 0x03:
                # Ctrl-C: interrupt
                _handle_interrupt()
                return False
            elif c == '+':
                # ACK from GDB, ignore
                pass
            elif c == '-':
                # NAK from GDB, retransmit last response
                _retransmit_last()
                return False

        timeout = timeout - 1

    return False

def _read_packet_data() -> bool:
    """Read packet data until '#' delimiter."""
    global _gdb_rx_len
    _gdb_rx_len = 0

    while True:
        if not uart_available():
            continue

        c: char = uart_getc()

        if c == '#':
            _gdb_rx_buf[_gdb_rx_len] = '\0'
            return True

        if c == '$':
            # New packet starting, reset
            _gdb_rx_len = 0
            continue

        if _gdb_rx_len < GDB_PACKET_SIZE - 1:
            _gdb_rx_buf[_gdb_rx_len] = c
            _gdb_rx_len = _gdb_rx_len + 1
        else:
            # Packet too long
            return False

def _verify_checksum() -> bool:
    """Read and verify packet checksum."""
    # Read two hex digits
    c1: char = uart_getc()
    c2: char = uart_getc()

    expected: int32 = (_hex_char_to_int(c1) << 4) | _hex_char_to_int(c2)

    # Calculate actual checksum
    actual: int32 = _calculate_checksum(&_gdb_rx_buf[0], _gdb_rx_len)

    return expected == actual

def _calculate_checksum(data: Ptr[char], length: int32) -> int32:
    """Calculate modulo 256 sum of packet data."""
    sum: int32 = 0
    i: int32 = 0

    while i < length:
        sum = sum + cast[int32](data[i])
        i = i + 1

    return sum & 0xFF

# ============================================================================
# Packet Transmission
# ============================================================================

def gdb_send_packet(data: Ptr[char]):
    """Send response packet to GDB.

    Formats and sends a complete packet with checksum.

    Args:
        data: Null-terminated response data
    """
    # Calculate length
    length: int32 = 0
    while data[length] != '\0':
        length = length + 1

    # Copy to TX buffer for potential retransmit
    i: int32 = 0
    while i < length and i < GDB_PACKET_SIZE - 1:
        _gdb_tx_buf[i] = data[i]
        i = i + 1
    _gdb_tx_buf[length] = '\0'
    _gdb_tx_len = length

    _send_raw_packet(data, length)

def _send_raw_packet(data: Ptr[char], length: int32):
    """Send raw packet with framing."""
    # Send start
    uart_putc('$')

    # Send data
    i: int32 = 0
    while i < length:
        uart_putc(data[i])
        i = i + 1

    # Send checksum
    checksum: int32 = _calculate_checksum(data, length)
    uart_putc('#')
    uart_putc(_int_to_hex_char((checksum >> 4) & 0x0F))
    uart_putc(_int_to_hex_char(checksum & 0x0F))

def _send_ack():
    """Send ACK (+)."""
    uart_putc('+')

def _send_nak():
    """Send NAK (-)."""
    uart_putc('-')

def _retransmit_last():
    """Retransmit last response packet."""
    if _gdb_tx_len > 0:
        _send_raw_packet(&_gdb_tx_buf[0], _gdb_tx_len)

def _send_ok():
    """Send OK response."""
    gdb_send_packet("OK")

def _send_empty():
    """Send empty response (unsupported command)."""
    gdb_send_packet("")

def _send_error(code: int32):
    """Send error response."""
    buf: Array[4, char]
    buf[0] = 'E'
    buf[1] = _int_to_hex_char((code >> 4) & 0x0F)
    buf[2] = _int_to_hex_char(code & 0x0F)
    buf[3] = '\0'
    gdb_send_packet(&buf[0])

# ============================================================================
# Packet Processing
# ============================================================================

def _process_packet():
    """Process received packet and dispatch to handler."""
    if _gdb_rx_len == 0:
        _send_empty()
        return

    cmd: char = _gdb_rx_buf[0]

    if cmd == '?':
        # Query halt reason
        _handle_halt_reason()
    elif cmd == 'g':
        # Read all registers
        _handle_read_registers()
    elif cmd == 'G':
        # Write all registers
        _handle_write_registers()
    elif cmd == 'p':
        # Read single register
        _handle_read_register()
    elif cmd == 'P':
        # Write single register
        _handle_write_register()
    elif cmd == 'm':
        # Read memory
        _handle_read_memory()
    elif cmd == 'M':
        # Write memory
        _handle_write_memory()
    elif cmd == 'X':
        # Write memory (binary)
        _handle_write_memory_binary()
    elif cmd == 'c':
        # Continue
        _handle_continue()
    elif cmd == 's':
        # Single step
        _handle_step()
    elif cmd == 'C':
        # Continue with signal
        _handle_continue_signal()
    elif cmd == 'S':
        # Step with signal
        _handle_step_signal()
    elif cmd == 'Z':
        # Set breakpoint/watchpoint
        _handle_set_breakpoint()
    elif cmd == 'z':
        # Remove breakpoint/watchpoint
        _handle_remove_breakpoint()
    elif cmd == 'k':
        # Kill (reset target)
        _handle_kill()
    elif cmd == 'D':
        # Detach
        _handle_detach()
    elif cmd == 'q':
        # Query
        _handle_query()
    elif cmd == 'Q':
        # Set (general set)
        _handle_set()
    elif cmd == 'v':
        # Extended commands
        _handle_extended()
    elif cmd == 'H':
        # Set thread (we're single-threaded)
        _send_ok()
    elif cmd == 'T':
        # Thread alive check
        _send_ok()
    else:
        # Unknown command
        _send_empty()

# ============================================================================
# Register Handling ('g', 'G', 'p', 'P')
# ============================================================================

def _handle_read_registers():
    """Handle 'g' - read all registers.

    Returns registers as hex string:
    R0-R12, SP, LR, PC, xPSR (17 x 32-bit = 68 hex chars per reg = 136 chars)
    """
    buf: Array[140, char]
    pos: int32 = 0

    # Output all 17 registers (R0-R12, SP, LR, PC, xPSR)
    i: int32 = 0
    while i < NUM_CORE_REGS:
        pos = _append_hex32(&buf[0], pos, _saved_regs[i])
        i = i + 1

    buf[pos] = '\0'
    gdb_send_packet(&buf[0])

def _handle_write_registers():
    """Handle 'G' - write all registers.

    Expects hex string with all register values.
    """
    # Skip 'G' command byte
    pos: int32 = 1

    i: int32 = 0
    while i < NUM_CORE_REGS and pos + 8 <= _gdb_rx_len:
        _saved_regs[i] = _parse_hex32(&_gdb_rx_buf[pos])
        pos = pos + 8
        i = i + 1

    _send_ok()

def _handle_read_register():
    """Handle 'p' - read single register."""
    # Parse register number after 'p'
    reg: int32 = _parse_hex(&_gdb_rx_buf[1])

    if reg < 0 or reg >= NUM_CORE_REGS:
        _send_error(0)
        return

    buf: Array[12, char]
    pos: int32 = _append_hex32(&buf[0], 0, _saved_regs[reg])
    buf[pos] = '\0'

    gdb_send_packet(&buf[0])

def _handle_write_register():
    """Handle 'P' - write single register."""
    # Parse register number
    pos: int32 = 1
    reg: int32 = 0

    while _gdb_rx_buf[pos] != '=' and pos < _gdb_rx_len:
        reg = (reg << 4) | _hex_char_to_int(_gdb_rx_buf[pos])
        pos = pos + 1

    if _gdb_rx_buf[pos] != '=' or reg >= NUM_CORE_REGS:
        _send_error(0)
        return

    pos = pos + 1  # Skip '='

    # Parse value
    value: uint32 = _parse_hex32(&_gdb_rx_buf[pos])
    _saved_regs[reg] = value

    _send_ok()

# ============================================================================
# Memory Handling ('m', 'M', 'X')
# ============================================================================

def _handle_read_memory():
    """Handle 'm' - read memory.

    Format: m<addr>,<length>
    """
    # Parse address
    pos: int32 = 1
    addr: uint32 = 0

    while _gdb_rx_buf[pos] != ',' and pos < _gdb_rx_len:
        addr = (addr << 4) | cast[uint32](_hex_char_to_int(_gdb_rx_buf[pos]))
        pos = pos + 1

    if _gdb_rx_buf[pos] != ',':
        _send_error(0)
        return

    pos = pos + 1  # Skip ','

    # Parse length
    length: int32 = _parse_hex(&_gdb_rx_buf[pos])

    if length <= 0 or length > 256:
        _send_error(0)
        return

    # Read memory and format as hex
    buf: Array[520, char]
    out_pos: int32 = 0
    ptr: Ptr[uint8] = cast[Ptr[uint8]](addr)

    i: int32 = 0
    while i < length:
        out_pos = _append_hex8(&buf[0], out_pos, ptr[i])
        i = i + 1

    buf[out_pos] = '\0'
    gdb_send_packet(&buf[0])

def _handle_write_memory():
    """Handle 'M' - write memory (hex).

    Format: M<addr>,<length>:<data>
    """
    # Parse address
    pos: int32 = 1
    addr: uint32 = 0

    while _gdb_rx_buf[pos] != ',' and pos < _gdb_rx_len:
        addr = (addr << 4) | cast[uint32](_hex_char_to_int(_gdb_rx_buf[pos]))
        pos = pos + 1

    if _gdb_rx_buf[pos] != ',':
        _send_error(0)
        return

    pos = pos + 1

    # Parse length
    length: int32 = 0
    while _gdb_rx_buf[pos] != ':' and pos < _gdb_rx_len:
        length = (length << 4) | _hex_char_to_int(_gdb_rx_buf[pos])
        pos = pos + 1

    if _gdb_rx_buf[pos] != ':':
        _send_error(0)
        return

    pos = pos + 1  # Skip ':'

    # Write hex data to memory
    ptr: Ptr[uint8] = cast[Ptr[uint8]](addr)
    i: int32 = 0

    while i < length and pos + 1 < _gdb_rx_len:
        hi: int32 = _hex_char_to_int(_gdb_rx_buf[pos])
        lo: int32 = _hex_char_to_int(_gdb_rx_buf[pos + 1])
        ptr[i] = cast[uint8]((hi << 4) | lo)
        pos = pos + 2
        i = i + 1

    _send_ok()

def _handle_write_memory_binary():
    """Handle 'X' - write memory (binary).

    Format: X<addr>,<length>:<binary data>
    Binary data may have escape sequences.
    """
    # Parse address
    pos: int32 = 1
    addr: uint32 = 0

    while _gdb_rx_buf[pos] != ',' and pos < _gdb_rx_len:
        addr = (addr << 4) | cast[uint32](_hex_char_to_int(_gdb_rx_buf[pos]))
        pos = pos + 1

    if _gdb_rx_buf[pos] != ',':
        _send_error(0)
        return

    pos = pos + 1

    # Parse length
    length: int32 = 0
    while _gdb_rx_buf[pos] != ':' and pos < _gdb_rx_len:
        length = (length << 4) | _hex_char_to_int(_gdb_rx_buf[pos])
        pos = pos + 1

    if _gdb_rx_buf[pos] != ':':
        _send_error(0)
        return

    pos = pos + 1  # Skip ':'

    # Write binary data to memory (handle escape sequences)
    ptr: Ptr[uint8] = cast[Ptr[uint8]](addr)
    i: int32 = 0

    while i < length and pos < _gdb_rx_len:
        c: char = _gdb_rx_buf[pos]

        if c == '}':
            # Escape sequence: next byte XOR 0x20
            pos = pos + 1
            if pos < _gdb_rx_len:
                ptr[i] = cast[uint8](cast[int32](_gdb_rx_buf[pos]) ^ 0x20)
            i = i + 1
        else:
            ptr[i] = cast[uint8](c)
            i = i + 1

        pos = pos + 1

    _send_ok()

# ============================================================================
# Execution Control ('c', 's', 'C', 'S')
# ============================================================================

def _handle_continue():
    """Handle 'c' - continue execution.

    Optional format: c<addr> to continue from address.
    """
    global _gdb_running, _gdb_single_step

    # Check for optional address
    if _gdb_rx_len > 1:
        addr: uint32 = _parse_hex32(&_gdb_rx_buf[1])
        _saved_regs[REG_PC] = addr

    _gdb_running = True
    _gdb_single_step = False

    # Resume execution
    _resume_execution()

def _handle_step():
    """Handle 's' - single step.

    Optional format: s<addr> to step from address.
    """
    global _gdb_running, _gdb_single_step

    # Check for optional address
    if _gdb_rx_len > 1:
        addr: uint32 = _parse_hex32(&_gdb_rx_buf[1])
        _saved_regs[REG_PC] = addr

    _gdb_running = True
    _gdb_single_step = True

    # Execute single instruction
    _step_execution()

def _handle_continue_signal():
    """Handle 'C' - continue with signal.

    Format: C<signal>[;addr]
    """
    global _gdb_running

    _gdb_running = True
    _resume_execution()

def _handle_step_signal():
    """Handle 'S' - step with signal.

    Format: S<signal>[;addr]
    """
    global _gdb_running, _gdb_single_step

    _gdb_running = True
    _gdb_single_step = True
    _step_execution()

def _resume_execution():
    """Resume program execution."""
    # Clear halt bit in DHCSR
    dhcsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](DCB_DHCSR)
    dhcsr[0] = DHCSR_DBGKEY | DHCSR_C_DEBUGEN

    # Execution will resume; we'll get a new debug event when it stops

def _step_execution():
    """Execute single instruction."""
    # Set step bit in DHCSR
    dhcsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](DCB_DHCSR)
    dhcsr[0] = DHCSR_DBGKEY | DHCSR_C_DEBUGEN | DHCSR_C_STEP

    # After step completes, send stop reply
    _send_stop_reply(SIGNAL_TRAP)

def _handle_interrupt():
    """Handle Ctrl-C interrupt from GDB."""
    global _gdb_running, _stop_signal

    _gdb_running = False
    _stop_signal = SIGNAL_INT

    # Halt execution
    dhcsr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](DCB_DHCSR)
    dhcsr[0] = DHCSR_DBGKEY | DHCSR_C_DEBUGEN | DHCSR_C_HALT

    _send_stop_reply(SIGNAL_INT)

def _send_stop_reply(signal: int32):
    """Send stop reply packet.

    Format: S<signal> or T<signal><info>
    """
    buf: Array[4, char]
    buf[0] = 'S'
    buf[1] = _int_to_hex_char((signal >> 4) & 0x0F)
    buf[2] = _int_to_hex_char(signal & 0x0F)
    buf[3] = '\0'
    gdb_send_packet(&buf[0])

# ============================================================================
# Breakpoint Handling ('Z', 'z')
# ============================================================================

def _handle_set_breakpoint():
    """Handle 'Z' - set breakpoint/watchpoint.

    Format: Z<type>,<addr>,<kind>
    Type: 0=software BP, 1=hardware BP, 2=write WP, 3=read WP, 4=access WP
    """
    # Parse type
    pos: int32 = 1
    bp_type: int32 = _hex_char_to_int(_gdb_rx_buf[pos])
    pos = pos + 1

    if _gdb_rx_buf[pos] != ',':
        _send_error(0)
        return

    pos = pos + 1

    # Parse address
    addr: uint32 = 0
    while _gdb_rx_buf[pos] != ',' and pos < _gdb_rx_len:
        addr = (addr << 4) | cast[uint32](_hex_char_to_int(_gdb_rx_buf[pos]))
        pos = pos + 1

    if _gdb_rx_buf[pos] != ',':
        _send_error(0)
        return

    pos = pos + 1

    # Parse kind (size)
    kind: int32 = _parse_hex(&_gdb_rx_buf[pos])

    # Handle based on type
    if bp_type == 0 or bp_type == 1:
        # Software or hardware breakpoint
        bp_id: int32 = bp_set(addr)
        if bp_id >= 0:
            _send_ok()
        else:
            _send_error(0x0E)  # No more breakpoints
    else:
        # Watchpoints not supported yet
        _send_empty()

def _handle_remove_breakpoint():
    """Handle 'z' - remove breakpoint/watchpoint.

    Format: z<type>,<addr>,<kind>
    """
    # Parse type
    pos: int32 = 1
    bp_type: int32 = _hex_char_to_int(_gdb_rx_buf[pos])
    pos = pos + 1

    if _gdb_rx_buf[pos] != ',':
        _send_error(0)
        return

    pos = pos + 1

    # Parse address
    addr: uint32 = 0
    while _gdb_rx_buf[pos] != ',' and pos < _gdb_rx_len:
        addr = (addr << 4) | cast[uint32](_hex_char_to_int(_gdb_rx_buf[pos]))
        pos = pos + 1

    if bp_type == 0 or bp_type == 1:
        # Find and remove breakpoint by address
        i: int32 = 0
        while i < MAX_BREAKPOINTS:
            if bp_get_addr(i) == addr and bp_is_enabled(i):
                if bp_clear(i):
                    _send_ok()
                    return
            i = i + 1
        _send_error(0)
    else:
        _send_empty()

# ============================================================================
# Query/Set Handling ('q', 'Q')
# ============================================================================

def _handle_query():
    """Handle 'q' - query commands."""
    # qSupported - query supported features
    if _match_prefix(&_gdb_rx_buf[1], "Supported"):
        gdb_send_packet("PacketSize=200;qXfer:features:read-;swbreak+;hwbreak+")
        return

    # qAttached - are we attached to existing process
    if _match_prefix(&_gdb_rx_buf[1], "Attached"):
        gdb_send_packet("1")
        return

    # qC - current thread ID
    if _gdb_rx_buf[1] == 'C' and _gdb_rx_len == 2:
        gdb_send_packet("QC1")
        return

    # qfThreadInfo - first thread info
    if _match_prefix(&_gdb_rx_buf[1], "fThreadInfo"):
        gdb_send_packet("m1")
        return

    # qsThreadInfo - subsequent thread info
    if _match_prefix(&_gdb_rx_buf[1], "sThreadInfo"):
        gdb_send_packet("l")
        return

    # qOffsets - section offsets
    if _match_prefix(&_gdb_rx_buf[1], "Offsets"):
        gdb_send_packet("Text=0;Data=0;Bss=0")
        return

    # qSymbol - symbol lookup
    if _match_prefix(&_gdb_rx_buf[1], "Symbol"):
        gdb_send_packet("OK")
        return

    # qTStatus - trace status
    if _match_prefix(&_gdb_rx_buf[1], "TStatus"):
        gdb_send_packet("")
        return

    # Unknown query
    _send_empty()

def _handle_set():
    """Handle 'Q' - set commands."""
    # QStartNoAckMode - disable ACKs
    if _match_prefix(&_gdb_rx_buf[1], "StartNoAckMode"):
        _send_ok()
        return

    _send_empty()

# ============================================================================
# Extended Commands ('v')
# ============================================================================

def _handle_extended():
    """Handle 'v' - extended commands."""
    # vCont? - query continue actions
    if _match_prefix(&_gdb_rx_buf[1], "Cont?"):
        gdb_send_packet("vCont;c;s;C;S")
        return

    # vCont - continue actions
    if _match_prefix(&_gdb_rx_buf[1], "Cont"):
        _handle_vcont()
        return

    # vMustReplyEmpty - test for new commands
    if _match_prefix(&_gdb_rx_buf[1], "MustReplyEmpty"):
        _send_empty()
        return

    _send_empty()

def _handle_vcont():
    """Handle vCont command."""
    global _gdb_running, _gdb_single_step

    # Parse action after "vCont;"
    pos: int32 = 5  # Skip "vCont"

    if _gdb_rx_buf[pos] == ';':
        pos = pos + 1

    action: char = _gdb_rx_buf[pos]

    if action == 'c':
        _gdb_running = True
        _gdb_single_step = False
        _resume_execution()
    elif action == 's':
        _gdb_running = True
        _gdb_single_step = True
        _step_execution()
    elif action == 'C':
        _gdb_running = True
        _resume_execution()
    elif action == 'S':
        _gdb_running = True
        _gdb_single_step = True
        _step_execution()
    else:
        _send_empty()

# ============================================================================
# Other Commands
# ============================================================================

def _handle_halt_reason():
    """Handle '?' - query halt reason."""
    _send_stop_reply(_stop_signal)

def _handle_kill():
    """Handle 'k' - kill/reset target."""
    global _gdb_connected

    _send_ok()
    _gdb_connected = False

    # Reset target (write to AIRCR)
    aircr: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0xE000ED0C)
    aircr[0] = 0x05FA0004  # Request system reset

def _handle_detach():
    """Handle 'D' - detach from target."""
    global _gdb_connected

    _send_ok()
    _gdb_connected = False

    # Resume execution
    _resume_execution()

# ============================================================================
# Utility Functions
# ============================================================================

def _hex_char_to_int(c: char) -> int32:
    """Convert hex character to integer (0-15)."""
    if c >= '0' and c <= '9':
        return cast[int32](c) - cast[int32]('0')
    if c >= 'a' and c <= 'f':
        return cast[int32](c) - cast[int32]('a') + 10
    if c >= 'A' and c <= 'F':
        return cast[int32](c) - cast[int32]('A') + 10
    return 0

def _int_to_hex_char(val: int32) -> char:
    """Convert integer (0-15) to hex character."""
    if val < 10:
        return cast[char](cast[int32]('0') + val)
    return cast[char](cast[int32]('a') + val - 10)

def _parse_hex(s: Ptr[char]) -> int32:
    """Parse hex string to integer."""
    result: int32 = 0
    i: int32 = 0

    while s[i] != '\0' and s[i] != ',' and s[i] != ':' and s[i] != ';':
        c: char = s[i]
        if (c >= '0' and c <= '9') or (c >= 'a' and c <= 'f') or (c >= 'A' and c <= 'F'):
            result = (result << 4) | _hex_char_to_int(c)
        else:
            break
        i = i + 1

    return result

def _parse_hex32(s: Ptr[char]) -> uint32:
    """Parse hex string to 32-bit unsigned integer (big-endian byte order)."""
    result: uint32 = 0
    i: int32 = 0

    # GDB sends registers in target byte order (little-endian for ARM)
    # Read 8 hex chars (4 bytes) and swap byte order
    bytes_arr: Array[4, uint8]
    j: int32 = 0

    while j < 4 and s[i] != '\0':
        hi: int32 = _hex_char_to_int(s[i])
        lo: int32 = _hex_char_to_int(s[i + 1])
        bytes_arr[j] = cast[uint8]((hi << 4) | lo)
        i = i + 2
        j = j + 1

    # Little-endian: first byte is LSB
    result = cast[uint32](bytes_arr[0])
    result = result | (cast[uint32](bytes_arr[1]) << 8)
    result = result | (cast[uint32](bytes_arr[2]) << 16)
    result = result | (cast[uint32](bytes_arr[3]) << 24)

    return result

def _append_hex8(buf: Ptr[char], pos: int32, val: uint8) -> int32:
    """Append byte as 2 hex chars to buffer."""
    buf[pos] = _int_to_hex_char((cast[int32](val) >> 4) & 0x0F)
    buf[pos + 1] = _int_to_hex_char(cast[int32](val) & 0x0F)
    return pos + 2

def _append_hex32(buf: Ptr[char], pos: int32, val: uint32) -> int32:
    """Append 32-bit value as 8 hex chars (little-endian byte order)."""
    # ARM is little-endian, so we send LSB first
    pos = _append_hex8(buf, pos, cast[uint8](val & 0xFF))
    pos = _append_hex8(buf, pos, cast[uint8]((val >> 8) & 0xFF))
    pos = _append_hex8(buf, pos, cast[uint8]((val >> 16) & 0xFF))
    pos = _append_hex8(buf, pos, cast[uint8]((val >> 24) & 0xFF))
    return pos

def _match_prefix(s: Ptr[char], prefix: Ptr[char]) -> bool:
    """Check if string starts with prefix."""
    i: int32 = 0

    while prefix[i] != '\0':
        if s[i] != prefix[i]:
            return False
        i = i + 1

    return True

# ============================================================================
# GDB Stub Main Loop
# ============================================================================

def gdb_main_loop():
    """Main GDB stub loop.

    Call this when the target is halted to handle GDB commands.
    """
    global _gdb_running

    _gdb_running = False

    while not _gdb_running:
        gdb_handle_packet()

def gdb_notify_stop(signal: int32):
    """Notify GDB that target has stopped.

    Call this from breakpoint/exception handlers.

    Args:
        signal: Stop signal (SIGNAL_TRAP, etc.)
    """
    global _stop_signal, _gdb_running

    _stop_signal = signal
    _gdb_running = False

    if _gdb_connected:
        _send_stop_reply(signal)
