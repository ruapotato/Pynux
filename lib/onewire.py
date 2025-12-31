# Pynux 1-Wire Library
#
# 1-Wire protocol implementation for bare-metal ARM Cortex-M3.
# Includes DS18B20 temperature sensor emulation.
#
# Note: This is an emulation layer using software delays.
# Actual timing may vary based on system clock.

from lib.memory import memset, memcpy

# ============================================================================
# Constants
# ============================================================================

# 1-Wire timing constants (in microseconds, for reference)
# Actual delays use loop iterations calibrated for ~25MHz
ONEWIRE_RESET_PULSE: int32 = 480    # Reset pulse duration
ONEWIRE_PRESENCE_WAIT: int32 = 70   # Wait after reset for presence
ONEWIRE_PRESENCE_PULSE: int32 = 240 # Max presence pulse duration
ONEWIRE_SLOT_TIME: int32 = 60       # Time slot for bit
ONEWIRE_WRITE_LOW: int32 = 6        # Low time for write-1
ONEWIRE_WRITE_HIGH: int32 = 60      # Low time for write-0
ONEWIRE_READ_SAMPLE: int32 = 15     # Sample time for read

# ROM commands
ONEWIRE_CMD_SEARCH_ROM: uint8 = 0xF0
ONEWIRE_CMD_READ_ROM: uint8 = 0x33
ONEWIRE_CMD_MATCH_ROM: uint8 = 0x55
ONEWIRE_CMD_SKIP_ROM: uint8 = 0xCC
ONEWIRE_CMD_ALARM_SEARCH: uint8 = 0xEC

# DS18B20 commands
DS18B20_CMD_CONVERT: uint8 = 0x44
DS18B20_CMD_READ_SCRATCH: uint8 = 0xBE
DS18B20_CMD_WRITE_SCRATCH: uint8 = 0x4E
DS18B20_CMD_COPY_SCRATCH: uint8 = 0x48
DS18B20_CMD_RECALL_EEPROM: uint8 = 0xB8
DS18B20_CMD_READ_POWER: uint8 = 0xB4

# DS18B20 family code
DS18B20_FAMILY: uint8 = 0x28

# CRC8 polynomial (x^8 + x^5 + x^4 + 1)
CRC8_POLY: uint8 = 0x8C

# Maximum devices on bus
MAX_ONEWIRE_DEVICES: int32 = 8

# ROM code size
ROM_SIZE: int32 = 8

# Search state values
SEARCH_DONE: int32 = 0
SEARCH_MORE: int32 = 1
SEARCH_ERROR: int32 = -1

# ============================================================================
# Emulated Bus State
# ============================================================================

# GPIO emulation for 1-Wire pin
_ow_pin_state: int32 = 1    # 1 = high (idle), 0 = low
_ow_pin_port: uint32 = 0
_ow_pin_number: uint32 = 0
_ow_initialized: bool = False

# Emulated devices on bus
# Each device: ROM code (8 bytes) + scratchpad (9 bytes) = 17 bytes
_ow_devices: Array[136, uint8]  # 8 devices * 17 bytes
_ow_device_count: int32 = 0

# Search algorithm state
_search_last_discrepancy: int32 = 0
_search_last_device: bool = False
_search_rom: Array[8, uint8]

# Temperature emulation (scaled by 16, DS18B20 format)
_ds18b20_temp: Array[8, int32]  # Temperature for each device slot

# ============================================================================
# Delay Functions (Software Timing)
# ============================================================================

def _ow_delay_us(us: int32):
    """Software delay in approximate microseconds.

    Calibrated for ~25MHz system clock.
    Each loop iteration is approximately 4 cycles.
    """
    # For 25MHz: ~6 iterations per microsecond
    iterations: int32 = us * 6
    i: int32 = 0
    while i < iterations:
        # Volatile-style no-op to prevent optimization
        i = i + 1

def _ow_delay_short():
    """Very short delay (~1-2us)."""
    i: int32 = 0
    while i < 12:
        i = i + 1

def _ow_delay_slot():
    """Standard time slot delay (~60us)."""
    _ow_delay_us(60)

# ============================================================================
# Low-Level Pin Control (Emulated)
# ============================================================================

def _ow_pin_low():
    """Drive pin low."""
    global _ow_pin_state
    _ow_pin_state = 0

def _ow_pin_release():
    """Release pin (high via pull-up)."""
    global _ow_pin_state
    _ow_pin_state = 1

def _ow_pin_read() -> int32:
    """Read pin state.

    In emulation, also simulates device responses.
    """
    return _ow_pin_state

# ============================================================================
# Initialization
# ============================================================================

def onewire_init(port: uint32, pin: uint32):
    """Initialize 1-Wire bus on specified GPIO pin.

    Args:
        port: GPIO port number
        pin: GPIO pin number
    """
    global _ow_pin_port, _ow_pin_number, _ow_initialized
    global _ow_device_count, _search_last_device, _search_last_discrepancy

    _ow_pin_port = port
    _ow_pin_number = pin
    _ow_initialized = True

    # Clear device list
    memset(&_ow_devices[0], 0, 136)
    _ow_device_count = 0

    # Clear search state
    _search_last_discrepancy = 0
    _search_last_device = False
    memset(&_search_rom[0], 0, ROM_SIZE)

    # Initialize temperatures to 25C (400 in DS18B20 format)
    i: int32 = 0
    while i < 8:
        _ds18b20_temp[i] = 400
        i = i + 1

    # Release bus
    _ow_pin_release()

# ============================================================================
# Reset and Presence Detection
# ============================================================================

def onewire_reset() -> bool:
    """Send reset pulse and check for device presence.

    Returns:
        True if device presence detected
    """
    if not _ow_initialized:
        return False

    # Drive low for 480us
    _ow_pin_low()
    _ow_delay_us(480)

    # Release and wait 70us
    _ow_pin_release()
    _ow_delay_us(70)

    # Check for presence (devices pull low)
    # In emulation, simulate presence if devices exist
    presence: bool = _ow_device_count > 0

    # Wait for recovery
    _ow_delay_us(410)

    return presence

# ============================================================================
# Bit-Level Operations
# ============================================================================

def onewire_write_bit(bit: int32):
    """Write a single bit to the bus.

    Args:
        bit: 0 or 1 to write
    """
    if bit != 0:
        # Write 1: short low pulse, then release
        _ow_pin_low()
        _ow_delay_us(6)
        _ow_pin_release()
        _ow_delay_us(64)
    else:
        # Write 0: long low pulse
        _ow_pin_low()
        _ow_delay_us(60)
        _ow_pin_release()
        _ow_delay_us(10)

def onewire_read_bit() -> int32:
    """Read a single bit from the bus.

    Returns:
        0 or 1
    """
    # Initiate read: short low pulse
    _ow_pin_low()
    _ow_delay_us(3)
    _ow_pin_release()

    # Sample after 10us
    _ow_delay_us(10)
    bit: int32 = _ow_pin_read()

    # Wait for slot end
    _ow_delay_us(53)

    return bit

# ============================================================================
# Byte-Level Operations
# ============================================================================

def onewire_write_byte(byte: uint8):
    """Write a byte to the bus (LSB first).

    Args:
        byte: Byte to write
    """
    i: int32 = 0
    while i < 8:
        onewire_write_bit(cast[int32](byte) & 1)
        byte = byte >> 1
        i = i + 1

def onewire_read_byte() -> uint8:
    """Read a byte from the bus (LSB first).

    Returns:
        Byte read from bus
    """
    result: uint8 = 0
    i: int32 = 0
    while i < 8:
        if onewire_read_bit() != 0:
            result = result | (1 << i)
        i = i + 1
    return result

def onewire_write_bytes(data: Ptr[uint8], count: int32):
    """Write multiple bytes to the bus."""
    i: int32 = 0
    while i < count:
        onewire_write_byte(data[i])
        i = i + 1

def onewire_read_bytes(data: Ptr[uint8], count: int32):
    """Read multiple bytes from the bus."""
    i: int32 = 0
    while i < count:
        data[i] = onewire_read_byte()
        i = i + 1

# ============================================================================
# CRC8 Calculation
# ============================================================================

def onewire_crc8(data: Ptr[uint8], length: int32) -> uint8:
    """Calculate CRC8 for 1-Wire (Dallas/Maxim polynomial).

    Args:
        data: Data buffer
        length: Number of bytes

    Returns:
        CRC8 value
    """
    crc: uint8 = 0
    i: int32 = 0

    while i < length:
        byte: uint8 = data[i]
        j: int32 = 0
        while j < 8:
            mix: uint8 = (crc ^ byte) & 0x01
            crc = crc >> 1
            if mix != 0:
                crc = crc ^ CRC8_POLY
            byte = byte >> 1
            j = j + 1
        i = i + 1

    return crc

def onewire_check_crc8(data: Ptr[uint8], length: int32) -> bool:
    """Verify CRC8 (last byte should be CRC of preceding bytes).

    Args:
        data: Data buffer including CRC byte at end
        length: Total length including CRC

    Returns:
        True if CRC valid
    """
    if length < 2:
        return False
    crc: uint8 = onewire_crc8(data, length - 1)
    return crc == data[length - 1]

# ============================================================================
# ROM Commands
# ============================================================================

def onewire_read_rom(rom: Ptr[uint8]) -> bool:
    """Read ROM code from single device on bus.

    Only works if exactly one device present.

    Args:
        rom: Output buffer for 8-byte ROM code

    Returns:
        True on success
    """
    if not onewire_reset():
        return False

    onewire_write_byte(ONEWIRE_CMD_READ_ROM)
    onewire_read_bytes(rom, ROM_SIZE)

    # Verify CRC
    return onewire_check_crc8(rom, ROM_SIZE)

def onewire_match_rom(rom: Ptr[uint8]) -> bool:
    """Select device by ROM code.

    Args:
        rom: 8-byte ROM code

    Returns:
        True on success
    """
    if not onewire_reset():
        return False

    onewire_write_byte(ONEWIRE_CMD_MATCH_ROM)
    onewire_write_bytes(rom, ROM_SIZE)

    return True

def onewire_skip_rom() -> bool:
    """Skip ROM selection (address all devices).

    Returns:
        True on success
    """
    if not onewire_reset():
        return False

    onewire_write_byte(ONEWIRE_CMD_SKIP_ROM)
    return True

# ============================================================================
# ROM Search Algorithm
# ============================================================================

def onewire_search_reset():
    """Reset search state for new search."""
    global _search_last_discrepancy, _search_last_device
    _search_last_discrepancy = 0
    _search_last_device = False
    memset(&_search_rom[0], 0, ROM_SIZE)

def onewire_search_next(rom_out: Ptr[uint8]) -> int32:
    """Find next device on bus using search algorithm.

    Args:
        rom_out: Output buffer for found ROM code

    Returns:
        SEARCH_MORE if device found and more may exist,
        SEARCH_DONE if device found and search complete,
        SEARCH_ERROR on error
    """
    global _search_last_discrepancy, _search_last_device

    if _search_last_device:
        return SEARCH_DONE

    if not onewire_reset():
        onewire_search_reset()
        return SEARCH_ERROR

    onewire_write_byte(ONEWIRE_CMD_SEARCH_ROM)

    last_zero: int32 = 0
    bit_number: int32 = 1
    rom_byte_number: int32 = 0
    rom_byte_mask: uint8 = 1

    while bit_number <= 64:
        # Read bit and complement
        bit: int32 = onewire_read_bit()
        cmp_bit: int32 = onewire_read_bit()

        if bit == 1 and cmp_bit == 1:
            # No devices responding
            onewire_search_reset()
            return SEARCH_ERROR

        direction: int32 = 0
        if bit != cmp_bit:
            # All devices have same bit
            direction = bit
        else:
            # Discrepancy - devices differ
            if bit_number < _search_last_discrepancy:
                # Use direction from last search
                direction = cast[int32](_search_rom[rom_byte_number] & rom_byte_mask)
                if direction != 0:
                    direction = 1
            elif bit_number == _search_last_discrepancy:
                direction = 1
            else:
                direction = 0

            if direction == 0:
                last_zero = bit_number

        # Write search direction
        if direction != 0:
            _search_rom[rom_byte_number] = _search_rom[rom_byte_number] | rom_byte_mask
        else:
            _search_rom[rom_byte_number] = _search_rom[rom_byte_number] & ~rom_byte_mask

        onewire_write_bit(direction)

        # Advance to next bit
        rom_byte_mask = rom_byte_mask << 1
        if rom_byte_mask == 0:
            rom_byte_number = rom_byte_number + 1
            rom_byte_mask = 1

        bit_number = bit_number + 1

    _search_last_discrepancy = last_zero

    if _search_last_discrepancy == 0:
        _search_last_device = True

    # Verify CRC
    if not onewire_check_crc8(&_search_rom[0], ROM_SIZE):
        onewire_search_reset()
        return SEARCH_ERROR

    # Copy result
    memcpy(rom_out, &_search_rom[0], ROM_SIZE)

    if _search_last_device:
        return SEARCH_DONE
    return SEARCH_MORE

def onewire_search_all(rom_array: Ptr[uint8], max_devices: int32) -> int32:
    """Find all devices on bus.

    Args:
        rom_array: Output array for ROM codes (8 bytes each)
        max_devices: Maximum devices to find

    Returns:
        Number of devices found
    """
    onewire_search_reset()

    count: int32 = 0
    result: int32 = SEARCH_MORE

    while result == SEARCH_MORE and count < max_devices:
        result = onewire_search_next(&rom_array[count * ROM_SIZE])
        if result != SEARCH_ERROR:
            count = count + 1

    return count

# ============================================================================
# DS18B20 Temperature Sensor Functions
# ============================================================================

def ds18b20_start_conversion():
    """Start temperature conversion on all DS18B20 sensors.

    Call onewire_skip_rom() first, or onewire_match_rom() for specific device.
    """
    onewire_write_byte(DS18B20_CMD_CONVERT)

def ds18b20_read_temperature(rom: Ptr[uint8]) -> int32:
    """Read temperature from DS18B20 sensor.

    Temperature is returned in 1/16 degree Celsius units.
    For example: 400 = 25.0C, 384 = 24.0C

    Args:
        rom: 8-byte ROM code of device (or NULL to skip ROM)

    Returns:
        Temperature in 1/16 C, or -9999 on error
    """
    # Select device
    if cast[uint32](rom) == 0:
        if not onewire_skip_rom():
            return -9999
    else:
        if not onewire_match_rom(rom):
            return -9999

    # Read scratchpad
    onewire_write_byte(DS18B20_CMD_READ_SCRATCH)

    scratch: Array[9, uint8]
    onewire_read_bytes(&scratch[0], 9)

    # Verify CRC
    if not onewire_check_crc8(&scratch[0], 9):
        return -9999

    # Temperature is in bytes 0 (LSB) and 1 (MSB)
    temp_lsb: int32 = cast[int32](scratch[0])
    temp_msb: int32 = cast[int32](scratch[1])
    temp: int32 = (temp_msb << 8) | temp_lsb

    # Handle negative temperatures (two's complement)
    if (temp_msb & 0x80) != 0:
        temp = temp - 65536

    return temp

def ds18b20_convert_to_celsius(raw: int32) -> int32:
    """Convert raw DS18B20 reading to degrees Celsius (integer part).

    Args:
        raw: Raw temperature reading from ds18b20_read_temperature()

    Returns:
        Temperature in whole degrees Celsius
    """
    # Each unit is 1/16 degree
    return raw / 16

def ds18b20_convert_to_celsius_frac(raw: int32) -> int32:
    """Get fractional part of temperature (0-9375, representing .0000-.9375).

    Args:
        raw: Raw temperature reading

    Returns:
        Fractional part scaled to 0-9375 (each unit is 0.0001 C)
    """
    # Fraction is (raw % 16) * 625
    frac: int32 = raw % 16
    if frac < 0:
        frac = frac + 16
    return frac * 625

# ============================================================================
# Emulation Functions
# ============================================================================

def onewire_add_device(rom: Ptr[uint8]) -> int32:
    """Add emulated device to bus.

    Args:
        rom: 8-byte ROM code for device

    Returns:
        Device index (0-7) on success, -1 if full
    """
    global _ow_device_count

    if _ow_device_count >= MAX_ONEWIRE_DEVICES:
        return -1

    idx: int32 = _ow_device_count
    base: int32 = idx * 17

    # Copy ROM code
    memcpy(&_ow_devices[base], rom, ROM_SIZE)

    # Initialize scratchpad (9 bytes after ROM)
    memset(&_ow_devices[base + ROM_SIZE], 0, 9)

    _ow_device_count = _ow_device_count + 1
    return idx

def onewire_add_ds18b20(serial: Ptr[uint8]) -> int32:
    """Add emulated DS18B20 sensor.

    Args:
        serial: 6-byte serial number (ROM will be: family + serial + CRC)

    Returns:
        Device index on success, -1 if full
    """
    rom: Array[8, uint8]

    # Family code
    rom[0] = DS18B20_FAMILY

    # Serial number (6 bytes)
    i: int32 = 0
    while i < 6:
        rom[i + 1] = serial[i]
        i = i + 1

    # Calculate CRC
    rom[7] = onewire_crc8(&rom[0], 7)

    return onewire_add_device(&rom[0])

def onewire_set_temperature(device_idx: int32, temp_raw: int32):
    """Set emulated temperature for DS18B20.

    Args:
        device_idx: Device index from onewire_add_ds18b20()
        temp_raw: Temperature in DS18B20 format (1/16 degree units)
    """
    if device_idx >= 0 and device_idx < MAX_ONEWIRE_DEVICES:
        _ds18b20_temp[device_idx] = temp_raw

        # Update scratchpad
        base: int32 = device_idx * 17 + ROM_SIZE
        _ow_devices[base] = cast[uint8](temp_raw & 0xFF)
        _ow_devices[base + 1] = cast[uint8]((temp_raw >> 8) & 0xFF)

def onewire_set_temperature_c(device_idx: int32, celsius: int32):
    """Set emulated temperature in whole degrees Celsius.

    Args:
        device_idx: Device index
        celsius: Temperature in degrees Celsius
    """
    # Convert to raw format (multiply by 16)
    raw: int32 = celsius * 16
    onewire_set_temperature(device_idx, raw)

def onewire_get_device_count() -> int32:
    """Get number of emulated devices on bus."""
    return _ow_device_count

def onewire_clear_devices():
    """Remove all emulated devices from bus."""
    global _ow_device_count
    memset(&_ow_devices[0], 0, 136)
    _ow_device_count = 0
    onewire_search_reset()

def onewire_get_device_rom(device_idx: int32, rom_out: Ptr[uint8]) -> bool:
    """Get ROM code of emulated device.

    Args:
        device_idx: Device index
        rom_out: Output buffer for 8-byte ROM

    Returns:
        True if device exists
    """
    if device_idx < 0 or device_idx >= _ow_device_count:
        return False

    base: int32 = device_idx * 17
    memcpy(rom_out, &_ow_devices[base], ROM_SIZE)
    return True

# ============================================================================
# Utility Functions
# ============================================================================

def onewire_rom_to_string(rom: Ptr[uint8], out: Ptr[char]):
    """Convert ROM code to hex string.

    Args:
        rom: 8-byte ROM code
        out: Output buffer (at least 17 bytes for "XX:XX:XX:XX:XX:XX:XX:XX\\0")
    """
    hex_chars: Ptr[char] = "0123456789ABCDEF"
    o: int32 = 0
    i: int32 = 0

    while i < ROM_SIZE:
        byte: uint8 = rom[i]
        out[o] = hex_chars[cast[int32](byte) >> 4]
        out[o + 1] = hex_chars[cast[int32](byte) & 0x0F]
        o = o + 2
        if i < ROM_SIZE - 1:
            out[o] = ':'
            o = o + 1
        i = i + 1

    out[o] = '\0'

def onewire_get_family(rom: Ptr[uint8]) -> uint8:
    """Get family code from ROM.

    Args:
        rom: 8-byte ROM code

    Returns:
        Family code (first byte)
    """
    return rom[0]

def onewire_is_ds18b20(rom: Ptr[uint8]) -> bool:
    """Check if device is DS18B20.

    Args:
        rom: 8-byte ROM code

    Returns:
        True if DS18B20 family code
    """
    return rom[0] == DS18B20_FAMILY
