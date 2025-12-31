# Pynux Encoding Library
#
# Base64, Hex, CRC32, and RLE encoding/decoding for bare-metal ARM.

from lib.memory import memcpy

# ============================================================================
# Base64 Encoding/Decoding
# ============================================================================

# Base64 alphabet
_b64_chars: Ptr[char] = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

def _b64_char_to_val(c: char) -> int32:
    """Convert base64 character to 6-bit value, returns -1 for invalid."""
    if c >= 'A' and c <= 'Z':
        return cast[int32](c) - cast[int32]('A')
    if c >= 'a' and c <= 'z':
        return cast[int32](c) - cast[int32]('a') + 26
    if c >= '0' and c <= '9':
        return cast[int32](c) - cast[int32]('0') + 52
    if c == '+':
        return 62
    if c == '/':
        return 63
    if c == '=':
        return 0  # Padding
    return -1

def base64_encode(inp: Ptr[uint8], in_len: int32, out: Ptr[char]) -> int32:
    """Encode bytes to base64 string. Returns output length."""
    i: int32 = 0
    o: int32 = 0

    while i < in_len:
        # Gather up to 3 bytes
        b0: uint8 = inp[i]
        b1: uint8 = 0
        b2: uint8 = 0
        remaining: int32 = in_len - i

        if remaining > 1:
            b1 = inp[i + 1]
        if remaining > 2:
            b2 = inp[i + 2]

        # Convert to 4 base64 characters
        # First 6 bits of b0
        out[o] = _b64_chars[cast[int32](b0) >> 2]
        o = o + 1

        # Last 2 bits of b0 + first 4 bits of b1
        out[o] = _b64_chars[((cast[int32](b0) & 0x03) << 4) | (cast[int32](b1) >> 4)]
        o = o + 1

        if remaining > 1:
            # Last 4 bits of b1 + first 2 bits of b2
            out[o] = _b64_chars[((cast[int32](b1) & 0x0F) << 2) | (cast[int32](b2) >> 6)]
            o = o + 1
        else:
            out[o] = '='
            o = o + 1

        if remaining > 2:
            # Last 6 bits of b2
            out[o] = _b64_chars[cast[int32](b2) & 0x3F]
            o = o + 1
        else:
            out[o] = '='
            o = o + 1

        i = i + 3

    out[o] = '\0'
    return o

def base64_decode(inp: Ptr[char], in_len: int32, out: Ptr[uint8]) -> int32:
    """Decode base64 string to bytes. Returns output length, -1 on error."""
    i: int32 = 0
    o: int32 = 0

    while i < in_len:
        # Skip whitespace
        c: char = inp[i]
        if c == ' ' or c == '\n' or c == '\r' or c == '\t':
            i = i + 1
            continue

        # Need 4 characters
        if i + 3 >= in_len:
            break

        v0: int32 = _b64_char_to_val(inp[i])
        v1: int32 = _b64_char_to_val(inp[i + 1])
        v2: int32 = _b64_char_to_val(inp[i + 2])
        v3: int32 = _b64_char_to_val(inp[i + 3])

        if v0 < 0 or v1 < 0:
            return -1  # Invalid input

        # First byte: all 6 bits of v0 + top 2 bits of v1
        out[o] = cast[uint8]((v0 << 2) | (v1 >> 4))
        o = o + 1

        # Second byte (if not padding)
        if inp[i + 2] != '=':
            out[o] = cast[uint8](((v1 & 0x0F) << 4) | (v2 >> 2))
            o = o + 1

        # Third byte (if not padding)
        if inp[i + 3] != '=':
            out[o] = cast[uint8](((v2 & 0x03) << 6) | v3)
            o = o + 1

        i = i + 4

    return o

# ============================================================================
# Hexadecimal Encoding/Decoding
# ============================================================================

_hex_chars: Ptr[char] = "0123456789abcdef"

def _hex_char_to_val(c: char) -> int32:
    """Convert hex character to 4-bit value, returns -1 for invalid."""
    if c >= '0' and c <= '9':
        return cast[int32](c) - cast[int32]('0')
    if c >= 'a' and c <= 'f':
        return cast[int32](c) - cast[int32]('a') + 10
    if c >= 'A' and c <= 'F':
        return cast[int32](c) - cast[int32]('A') + 10
    return -1

def hex_encode(inp: Ptr[uint8], in_len: int32, out: Ptr[char]) -> int32:
    """Encode bytes to hex string. Returns output length."""
    i: int32 = 0
    o: int32 = 0

    while i < in_len:
        b: uint8 = inp[i]
        out[o] = _hex_chars[cast[int32](b) >> 4]
        out[o + 1] = _hex_chars[cast[int32](b) & 0x0F]
        i = i + 1
        o = o + 2

    out[o] = '\0'
    return o

def hex_decode(inp: Ptr[char], in_len: int32, out: Ptr[uint8]) -> int32:
    """Decode hex string to bytes. Returns output length, -1 on error."""
    i: int32 = 0
    o: int32 = 0

    while i + 1 < in_len:
        # Skip whitespace
        c: char = inp[i]
        if c == ' ' or c == '\n' or c == '\r' or c == '\t':
            i = i + 1
            continue

        hi: int32 = _hex_char_to_val(inp[i])
        lo: int32 = _hex_char_to_val(inp[i + 1])

        if hi < 0 or lo < 0:
            return -1  # Invalid hex character

        out[o] = cast[uint8]((hi << 4) | lo)
        i = i + 2
        o = o + 1

    return o

# ============================================================================
# CRC32 (IEEE 802.3 polynomial)
# ============================================================================

# CRC32 lookup table (generated for polynomial 0xEDB88320)
_crc32_table: Array[256, uint32]
_crc32_initialized: bool = False

def _init_crc32_table():
    """Initialize CRC32 lookup table."""
    global _crc32_initialized
    i: int32 = 0
    while i < 256:
        crc: uint32 = cast[uint32](i)
        j: int32 = 0
        while j < 8:
            if (crc & 1) != 0:
                crc = (crc >> 1) ^ 0xEDB88320
            else:
                crc = crc >> 1
            j = j + 1
        _crc32_table[i] = crc
        i = i + 1
    _crc32_initialized = True

def crc32(data: Ptr[uint8], length: int32) -> uint32:
    """Calculate CRC32 checksum of data."""
    global _crc32_initialized
    if not _crc32_initialized:
        _init_crc32_table()

    crc: uint32 = 0xFFFFFFFF
    i: int32 = 0

    while i < length:
        idx: int32 = cast[int32]((crc ^ cast[uint32](data[i])) & 0xFF)
        crc = (crc >> 8) ^ _crc32_table[idx]
        i = i + 1

    return crc ^ 0xFFFFFFFF

def crc32_update(crc: uint32, data: Ptr[uint8], length: int32) -> uint32:
    """Update running CRC32 with more data. Initialize crc to 0xFFFFFFFF."""
    global _crc32_initialized
    if not _crc32_initialized:
        _init_crc32_table()

    i: int32 = 0
    while i < length:
        idx: int32 = cast[int32]((crc ^ cast[uint32](data[i])) & 0xFF)
        crc = (crc >> 8) ^ _crc32_table[idx]
        i = i + 1

    return crc

def crc32_finalize(crc: uint32) -> uint32:
    """Finalize running CRC32."""
    return crc ^ 0xFFFFFFFF

# ============================================================================
# Run-Length Encoding (RLE)
# ============================================================================

# RLE format: For runs of 3+ identical bytes, encode as [marker][count][byte]
# where marker is 0xFF (escape), count is run length (3-258 stored as 0-255)
# Single 0xFF bytes are escaped as [0xFF][0x00]

RLE_MARKER: uint8 = 0xFF
RLE_MIN_RUN: int32 = 3  # Minimum run length to encode

def rle_encode(inp: Ptr[uint8], in_len: int32, out: Ptr[uint8]) -> int32:
    """Run-length encode data. Returns output length."""
    i: int32 = 0
    o: int32 = 0

    while i < in_len:
        # Count run of identical bytes
        run_byte: uint8 = inp[i]
        run_len: int32 = 1

        while i + run_len < in_len and inp[i + run_len] == run_byte and run_len < 258:
            run_len = run_len + 1

        if run_len >= RLE_MIN_RUN:
            # Encode as run
            out[o] = RLE_MARKER
            out[o + 1] = cast[uint8](run_len - RLE_MIN_RUN)
            out[o + 2] = run_byte
            o = o + 3
            i = i + run_len
        elif run_byte == RLE_MARKER:
            # Escape the marker byte
            out[o] = RLE_MARKER
            out[o + 1] = 0
            o = o + 2
            i = i + 1
        else:
            # Copy literal byte
            out[o] = run_byte
            o = o + 1
            i = i + 1

    return o

def rle_decode(inp: Ptr[uint8], in_len: int32, out: Ptr[uint8]) -> int32:
    """Run-length decode data. Returns output length, -1 on error."""
    i: int32 = 0
    o: int32 = 0

    while i < in_len:
        b: uint8 = inp[i]

        if b == RLE_MARKER:
            # Check for escape or run
            if i + 1 >= in_len:
                return -1  # Truncated input

            count: uint8 = inp[i + 1]

            if count == 0:
                # Escaped marker byte
                out[o] = RLE_MARKER
                o = o + 1
                i = i + 2
            else:
                # Run of bytes
                if i + 2 >= in_len:
                    return -1  # Truncated input

                run_byte: uint8 = inp[i + 2]
                run_len: int32 = cast[int32](count) + RLE_MIN_RUN

                j: int32 = 0
                while j < run_len:
                    out[o] = run_byte
                    o = o + 1
                    j = j + 1

                i = i + 3
        else:
            # Literal byte
            out[o] = b
            o = o + 1
            i = i + 1

    return o

# ============================================================================
# Utility Functions
# ============================================================================

def base64_encoded_len(in_len: int32) -> int32:
    """Calculate length of base64 encoded output (excluding null terminator)."""
    return ((in_len + 2) / 3) * 4

def base64_decoded_len(in_len: int32) -> int32:
    """Calculate maximum length of base64 decoded output."""
    return (in_len / 4) * 3

def hex_encoded_len(in_len: int32) -> int32:
    """Calculate length of hex encoded output (excluding null terminator)."""
    return in_len * 2

def hex_decoded_len(in_len: int32) -> int32:
    """Calculate length of hex decoded output."""
    return in_len / 2

def rle_max_encoded_len(in_len: int32) -> int32:
    """Calculate worst-case RLE encoded length (all 0xFF bytes)."""
    return in_len * 2
