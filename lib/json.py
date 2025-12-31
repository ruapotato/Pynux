# Pynux JSON Library
#
# Simple JSON parser and builder for bare-metal ARM Cortex-M3.
# Supports strings, integers, booleans, null, arrays, and objects.
# Limited nesting depth (max 2 levels).

from lib.string import strlen, strcmp, strcpy, isdigit, isspace, atoi, itoa

# ============================================================================
# Constants
# ============================================================================

# JSON value types
JSON_NULL: int32 = 0
JSON_BOOL: int32 = 1
JSON_INT: int32 = 2
JSON_STRING: int32 = 3
JSON_ARRAY: int32 = 4
JSON_OBJECT: int32 = 5
JSON_ERROR: int32 = -1

# Maximum limits
MAX_JSON_STRING: int32 = 256
MAX_JSON_KEYS: int32 = 16
MAX_JSON_ARRAY: int32 = 16
MAX_JSON_DEPTH: int32 = 2

# Parser state
PARSE_OK: int32 = 0
PARSE_ERROR: int32 = -1

# ============================================================================
# JSON Value Structure
# ============================================================================
#
# Simple representation for parsed JSON values:
#   type: int32       - JSON_* type constant (offset 0)
#   int_val: int32    - Integer value or bool (0/1) or array/object count (offset 4)
#   str_val: Array    - String value buffer (offset 8)
# Total: 8 + MAX_JSON_STRING bytes

JSON_TYPE_OFFSET: int32 = 0
JSON_INT_OFFSET: int32 = 4
JSON_STR_OFFSET: int32 = 8
JSON_VALUE_SIZE: int32 = 264  # 8 + 256

# Object storage for key-value pairs
# Each entry: key (64 bytes) + value_type (4) + value_int (4) + value_str (256) = 328
MAX_KEY_LEN: int32 = 64
JSON_ENTRY_SIZE: int32 = 328

# ============================================================================
# Parser State
# ============================================================================

_parse_pos: int32 = 0
_parse_error: int32 = 0

# Temporary buffers for parsing
_parse_buf: Array[256, char]
_key_buf: Array[64, char]

# ============================================================================
# Helper Functions
# ============================================================================

def _skip_whitespace(s: Ptr[char]):
    """Skip whitespace characters in parse input."""
    global _parse_pos
    while s[_parse_pos] != '\0':
        c: char = s[_parse_pos]
        if c == ' ' or c == '\t' or c == '\n' or c == '\r':
            _parse_pos = _parse_pos + 1
        else:
            break

def _parse_string(s: Ptr[char], out: Ptr[char], max_len: int32) -> bool:
    """Parse a JSON string. Returns True on success."""
    global _parse_pos

    if s[_parse_pos] != '"':
        return False

    _parse_pos = _parse_pos + 1  # Skip opening quote
    out_idx: int32 = 0

    while s[_parse_pos] != '\0' and out_idx < max_len - 1:
        c: char = s[_parse_pos]

        if c == '"':
            # End of string
            out[out_idx] = '\0'
            _parse_pos = _parse_pos + 1
            return True

        if c == '\\':
            # Escape sequence
            _parse_pos = _parse_pos + 1
            esc: char = s[_parse_pos]
            if esc == 'n':
                out[out_idx] = '\n'
            elif esc == 't':
                out[out_idx] = '\t'
            elif esc == 'r':
                out[out_idx] = '\r'
            elif esc == '"':
                out[out_idx] = '"'
            elif esc == '\\':
                out[out_idx] = '\\'
            elif esc == '/':
                out[out_idx] = '/'
            else:
                out[out_idx] = esc  # Unknown escape, copy as-is
            out_idx = out_idx + 1
            _parse_pos = _parse_pos + 1
        else:
            out[out_idx] = c
            out_idx = out_idx + 1
            _parse_pos = _parse_pos + 1

    out[out_idx] = '\0'
    return False  # Unterminated string

def _parse_number(s: Ptr[char]) -> int32:
    """Parse a JSON integer. Updates _parse_pos."""
    global _parse_pos

    negative: bool = False
    if s[_parse_pos] == '-':
        negative = True
        _parse_pos = _parse_pos + 1

    result: int32 = 0
    while isdigit(s[_parse_pos]):
        result = result * 10 + (cast[int32](s[_parse_pos]) - cast[int32]('0'))
        _parse_pos = _parse_pos + 1

    if negative:
        return -result
    return result

# ============================================================================
# JSON Parsing
# ============================================================================

def json_parse_value(s: Ptr[char], val: Ptr[int32]) -> int32:
    """Parse a JSON value from string.

    Args:
        s: JSON string to parse
        val: Output value structure (must be at least JSON_VALUE_SIZE bytes)

    Returns:
        JSON_* type on success, JSON_ERROR on failure
    """
    global _parse_pos, _parse_error
    _parse_pos = 0
    _parse_error = 0

    return _json_parse_value_internal(s, val)

def _json_parse_value_internal(s: Ptr[char], val: Ptr[int32]) -> int32:
    """Internal value parser at current position."""
    global _parse_pos

    _skip_whitespace(s)

    c: char = s[_parse_pos]

    if c == '\0':
        val[0] = JSON_ERROR
        return JSON_ERROR

    # Null
    if c == 'n':
        if s[_parse_pos + 1] == 'u' and s[_parse_pos + 2] == 'l' and s[_parse_pos + 3] == 'l':
            _parse_pos = _parse_pos + 4
            val[0] = JSON_NULL
            val[1] = 0
            return JSON_NULL
        val[0] = JSON_ERROR
        return JSON_ERROR

    # Boolean true
    if c == 't':
        if s[_parse_pos + 1] == 'r' and s[_parse_pos + 2] == 'u' and s[_parse_pos + 3] == 'e':
            _parse_pos = _parse_pos + 4
            val[0] = JSON_BOOL
            val[1] = 1
            return JSON_BOOL
        val[0] = JSON_ERROR
        return JSON_ERROR

    # Boolean false
    if c == 'f':
        if s[_parse_pos + 1] == 'a' and s[_parse_pos + 2] == 'l' and s[_parse_pos + 3] == 's' and s[_parse_pos + 4] == 'e':
            _parse_pos = _parse_pos + 5
            val[0] = JSON_BOOL
            val[1] = 0
            return JSON_BOOL
        val[0] = JSON_ERROR
        return JSON_ERROR

    # String
    if c == '"':
        str_ptr: Ptr[char] = cast[Ptr[char]](&val[2])  # String starts at offset 8
        if _parse_string(s, str_ptr, MAX_JSON_STRING):
            val[0] = JSON_STRING
            val[1] = strlen(str_ptr)
            return JSON_STRING
        val[0] = JSON_ERROR
        return JSON_ERROR

    # Number
    if c == '-' or isdigit(c):
        num: int32 = _parse_number(s)
        val[0] = JSON_INT
        val[1] = num
        return JSON_INT

    # Array - store count in val[1], cannot store full array here
    if c == '[':
        _parse_pos = _parse_pos + 1
        _skip_whitespace(s)
        count: int32 = 0

        if s[_parse_pos] == ']':
            _parse_pos = _parse_pos + 1
            val[0] = JSON_ARRAY
            val[1] = 0
            return JSON_ARRAY

        # Count elements (simplified - just count, don't store)
        while s[_parse_pos] != '\0' and s[_parse_pos] != ']':
            # Skip this value
            _json_skip_value(s)
            count = count + 1
            _skip_whitespace(s)
            if s[_parse_pos] == ',':
                _parse_pos = _parse_pos + 1
                _skip_whitespace(s)

        if s[_parse_pos] == ']':
            _parse_pos = _parse_pos + 1
            val[0] = JSON_ARRAY
            val[1] = count
            return JSON_ARRAY

        val[0] = JSON_ERROR
        return JSON_ERROR

    # Object - store count in val[1]
    if c == '{':
        _parse_pos = _parse_pos + 1
        _skip_whitespace(s)
        count: int32 = 0

        if s[_parse_pos] == '}':
            _parse_pos = _parse_pos + 1
            val[0] = JSON_OBJECT
            val[1] = 0
            return JSON_OBJECT

        while s[_parse_pos] != '\0' and s[_parse_pos] != '}':
            # Skip key
            _skip_whitespace(s)
            if s[_parse_pos] != '"':
                break
            _json_skip_string(s)
            _skip_whitespace(s)
            if s[_parse_pos] != ':':
                break
            _parse_pos = _parse_pos + 1
            _skip_whitespace(s)
            # Skip value
            _json_skip_value(s)
            count = count + 1
            _skip_whitespace(s)
            if s[_parse_pos] == ',':
                _parse_pos = _parse_pos + 1

        if s[_parse_pos] == '}':
            _parse_pos = _parse_pos + 1
            val[0] = JSON_OBJECT
            val[1] = count
            return JSON_OBJECT

        val[0] = JSON_ERROR
        return JSON_ERROR

    val[0] = JSON_ERROR
    return JSON_ERROR

def _json_skip_string(s: Ptr[char]):
    """Skip over a JSON string without parsing it."""
    global _parse_pos

    if s[_parse_pos] != '"':
        return

    _parse_pos = _parse_pos + 1
    while s[_parse_pos] != '\0':
        if s[_parse_pos] == '\\':
            _parse_pos = _parse_pos + 2
        elif s[_parse_pos] == '"':
            _parse_pos = _parse_pos + 1
            return
        else:
            _parse_pos = _parse_pos + 1

def _json_skip_value(s: Ptr[char]):
    """Skip over any JSON value without parsing it."""
    global _parse_pos

    _skip_whitespace(s)
    c: char = s[_parse_pos]

    if c == '"':
        _json_skip_string(s)
    elif c == '-' or isdigit(c):
        if c == '-':
            _parse_pos = _parse_pos + 1
        while isdigit(s[_parse_pos]):
            _parse_pos = _parse_pos + 1
    elif c == 't':
        _parse_pos = _parse_pos + 4
    elif c == 'f':
        _parse_pos = _parse_pos + 5
    elif c == 'n':
        _parse_pos = _parse_pos + 4
    elif c == '[':
        _parse_pos = _parse_pos + 1
        _skip_whitespace(s)
        while s[_parse_pos] != '\0' and s[_parse_pos] != ']':
            _json_skip_value(s)
            _skip_whitespace(s)
            if s[_parse_pos] == ',':
                _parse_pos = _parse_pos + 1
        if s[_parse_pos] == ']':
            _parse_pos = _parse_pos + 1
    elif c == '{':
        _parse_pos = _parse_pos + 1
        _skip_whitespace(s)
        while s[_parse_pos] != '\0' and s[_parse_pos] != '}':
            _skip_whitespace(s)
            _json_skip_string(s)
            _skip_whitespace(s)
            if s[_parse_pos] == ':':
                _parse_pos = _parse_pos + 1
            _json_skip_value(s)
            _skip_whitespace(s)
            if s[_parse_pos] == ',':
                _parse_pos = _parse_pos + 1
        if s[_parse_pos] == '}':
            _parse_pos = _parse_pos + 1

# ============================================================================
# Object Access Functions
# ============================================================================

def json_get_string(json: Ptr[char], key: Ptr[char], out: Ptr[char], max_len: int32) -> bool:
    """Get string value by key from JSON object.

    Args:
        json: JSON object string
        key: Key to look up
        out: Output buffer for string value
        max_len: Maximum output length

    Returns:
        True if key found and value is string
    """
    global _parse_pos
    _parse_pos = 0

    _skip_whitespace(json)
    if json[_parse_pos] != '{':
        return False

    _parse_pos = _parse_pos + 1

    while json[_parse_pos] != '\0' and json[_parse_pos] != '}':
        _skip_whitespace(json)

        # Parse key
        if json[_parse_pos] != '"':
            return False

        if not _parse_string(json, &_key_buf[0], MAX_KEY_LEN):
            return False

        _skip_whitespace(json)
        if json[_parse_pos] != ':':
            return False
        _parse_pos = _parse_pos + 1
        _skip_whitespace(json)

        # Check if this is the key we want
        if strcmp(&_key_buf[0], key) == 0:
            # Parse value as string
            if json[_parse_pos] == '"':
                return _parse_string(json, out, max_len)
            return False

        # Skip value
        _json_skip_value(json)
        _skip_whitespace(json)

        if json[_parse_pos] == ',':
            _parse_pos = _parse_pos + 1

    return False

def json_get_int(json: Ptr[char], key: Ptr[char]) -> int32:
    """Get integer value by key from JSON object.

    Returns 0 if not found or not an integer.
    """
    global _parse_pos
    _parse_pos = 0

    _skip_whitespace(json)
    if json[_parse_pos] != '{':
        return 0

    _parse_pos = _parse_pos + 1

    while json[_parse_pos] != '\0' and json[_parse_pos] != '}':
        _skip_whitespace(json)

        if json[_parse_pos] != '"':
            return 0

        if not _parse_string(json, &_key_buf[0], MAX_KEY_LEN):
            return 0

        _skip_whitespace(json)
        if json[_parse_pos] != ':':
            return 0
        _parse_pos = _parse_pos + 1
        _skip_whitespace(json)

        if strcmp(&_key_buf[0], key) == 0:
            c: char = json[_parse_pos]
            if c == '-' or isdigit(c):
                return _parse_number(json)
            return 0

        _json_skip_value(json)
        _skip_whitespace(json)

        if json[_parse_pos] == ',':
            _parse_pos = _parse_pos + 1

    return 0

def json_get_bool(json: Ptr[char], key: Ptr[char]) -> int32:
    """Get boolean value by key from JSON object.

    Returns: 1 for true, 0 for false, -1 if not found or not boolean.
    """
    global _parse_pos
    _parse_pos = 0

    _skip_whitespace(json)
    if json[_parse_pos] != '{':
        return -1

    _parse_pos = _parse_pos + 1

    while json[_parse_pos] != '\0' and json[_parse_pos] != '}':
        _skip_whitespace(json)

        if json[_parse_pos] != '"':
            return -1

        if not _parse_string(json, &_key_buf[0], MAX_KEY_LEN):
            return -1

        _skip_whitespace(json)
        if json[_parse_pos] != ':':
            return -1
        _parse_pos = _parse_pos + 1
        _skip_whitespace(json)

        if strcmp(&_key_buf[0], key) == 0:
            if json[_parse_pos] == 't':
                if json[_parse_pos + 1] == 'r' and json[_parse_pos + 2] == 'u' and json[_parse_pos + 3] == 'e':
                    return 1
            if json[_parse_pos] == 'f':
                if json[_parse_pos + 1] == 'a' and json[_parse_pos + 2] == 'l' and json[_parse_pos + 3] == 's' and json[_parse_pos + 4] == 'e':
                    return 0
            return -1

        _json_skip_value(json)
        _skip_whitespace(json)

        if json[_parse_pos] == ',':
            _parse_pos = _parse_pos + 1

    return -1

def json_has_key(json: Ptr[char], key: Ptr[char]) -> bool:
    """Check if JSON object has a key."""
    global _parse_pos
    _parse_pos = 0

    _skip_whitespace(json)
    if json[_parse_pos] != '{':
        return False

    _parse_pos = _parse_pos + 1

    while json[_parse_pos] != '\0' and json[_parse_pos] != '}':
        _skip_whitespace(json)

        if json[_parse_pos] != '"':
            return False

        if not _parse_string(json, &_key_buf[0], MAX_KEY_LEN):
            return False

        if strcmp(&_key_buf[0], key) == 0:
            return True

        _skip_whitespace(json)
        if json[_parse_pos] != ':':
            return False
        _parse_pos = _parse_pos + 1

        _json_skip_value(json)
        _skip_whitespace(json)

        if json[_parse_pos] == ',':
            _parse_pos = _parse_pos + 1

    return False

# ============================================================================
# Array Access Functions
# ============================================================================

def json_array_length(json: Ptr[char]) -> int32:
    """Get length of JSON array. Returns -1 if not an array."""
    global _parse_pos
    _parse_pos = 0

    _skip_whitespace(json)
    if json[_parse_pos] != '[':
        return -1

    _parse_pos = _parse_pos + 1
    _skip_whitespace(json)

    if json[_parse_pos] == ']':
        return 0

    count: int32 = 0
    while json[_parse_pos] != '\0' and json[_parse_pos] != ']':
        _json_skip_value(json)
        count = count + 1
        _skip_whitespace(json)
        if json[_parse_pos] == ',':
            _parse_pos = _parse_pos + 1
            _skip_whitespace(json)

    return count

def json_array_get_int(json: Ptr[char], index: int32) -> int32:
    """Get integer at index from JSON array. Returns 0 if invalid."""
    global _parse_pos
    _parse_pos = 0

    _skip_whitespace(json)
    if json[_parse_pos] != '[':
        return 0

    _parse_pos = _parse_pos + 1
    _skip_whitespace(json)

    current: int32 = 0
    while json[_parse_pos] != '\0' and json[_parse_pos] != ']':
        if current == index:
            c: char = json[_parse_pos]
            if c == '-' or isdigit(c):
                return _parse_number(json)
            return 0

        _json_skip_value(json)
        current = current + 1
        _skip_whitespace(json)
        if json[_parse_pos] == ',':
            _parse_pos = _parse_pos + 1
            _skip_whitespace(json)

    return 0

def json_array_get_string(json: Ptr[char], index: int32, out: Ptr[char], max_len: int32) -> bool:
    """Get string at index from JSON array."""
    global _parse_pos
    _parse_pos = 0

    _skip_whitespace(json)
    if json[_parse_pos] != '[':
        return False

    _parse_pos = _parse_pos + 1
    _skip_whitespace(json)

    current: int32 = 0
    while json[_parse_pos] != '\0' and json[_parse_pos] != ']':
        if current == index:
            if json[_parse_pos] == '"':
                return _parse_string(json, out, max_len)
            return False

        _json_skip_value(json)
        current = current + 1
        _skip_whitespace(json)
        if json[_parse_pos] == ',':
            _parse_pos = _parse_pos + 1
            _skip_whitespace(json)

    return False

# ============================================================================
# Type Checking Functions
# ============================================================================

def json_is_null(json: Ptr[char]) -> bool:
    """Check if JSON value is null."""
    global _parse_pos
    _parse_pos = 0
    _skip_whitespace(json)
    return json[_parse_pos] == 'n' and json[_parse_pos + 1] == 'u' and json[_parse_pos + 2] == 'l' and json[_parse_pos + 3] == 'l'

def json_is_bool(json: Ptr[char]) -> bool:
    """Check if JSON value is boolean."""
    global _parse_pos
    _parse_pos = 0
    _skip_whitespace(json)
    c: char = json[_parse_pos]
    if c == 't':
        return json[_parse_pos + 1] == 'r' and json[_parse_pos + 2] == 'u' and json[_parse_pos + 3] == 'e'
    if c == 'f':
        return json[_parse_pos + 1] == 'a' and json[_parse_pos + 2] == 'l' and json[_parse_pos + 3] == 's' and json[_parse_pos + 4] == 'e'
    return False

def json_is_int(json: Ptr[char]) -> bool:
    """Check if JSON value is integer."""
    global _parse_pos
    _parse_pos = 0
    _skip_whitespace(json)
    c: char = json[_parse_pos]
    return c == '-' or isdigit(c)

def json_is_string(json: Ptr[char]) -> bool:
    """Check if JSON value is string."""
    global _parse_pos
    _parse_pos = 0
    _skip_whitespace(json)
    return json[_parse_pos] == '"'

def json_is_array(json: Ptr[char]) -> bool:
    """Check if JSON value is array."""
    global _parse_pos
    _parse_pos = 0
    _skip_whitespace(json)
    return json[_parse_pos] == '['

def json_is_object(json: Ptr[char]) -> bool:
    """Check if JSON value is object."""
    global _parse_pos
    _parse_pos = 0
    _skip_whitespace(json)
    return json[_parse_pos] == '{'

def json_get_type(json: Ptr[char]) -> int32:
    """Get the type of a JSON value."""
    global _parse_pos
    _parse_pos = 0
    _skip_whitespace(json)
    c: char = json[_parse_pos]

    if c == 'n':
        return JSON_NULL
    if c == 't' or c == 'f':
        return JSON_BOOL
    if c == '-' or isdigit(c):
        return JSON_INT
    if c == '"':
        return JSON_STRING
    if c == '[':
        return JSON_ARRAY
    if c == '{':
        return JSON_OBJECT
    return JSON_ERROR

# ============================================================================
# JSON Builder Functions
# ============================================================================

# Builder state
_build_buf: Array[1024, char]
_build_pos: int32 = 0
_build_first: Array[8, bool]  # Stack for tracking first element at each depth
_build_depth: int32 = 0

def json_build_start() -> Ptr[char]:
    """Start building a JSON value. Returns pointer to output buffer."""
    global _build_pos, _build_depth
    _build_pos = 0
    _build_depth = 0
    _build_buf[0] = '\0'
    return &_build_buf[0]

def json_build_object_start():
    """Start a JSON object."""
    global _build_pos, _build_depth
    _build_buf[_build_pos] = '{'
    _build_pos = _build_pos + 1
    _build_first[_build_depth] = True
    _build_depth = _build_depth + 1

def json_build_object_end():
    """End a JSON object."""
    global _build_pos, _build_depth
    _build_depth = _build_depth - 1
    _build_buf[_build_pos] = '}'
    _build_pos = _build_pos + 1
    _build_buf[_build_pos] = '\0'

def json_build_array_start():
    """Start a JSON array."""
    global _build_pos, _build_depth
    _build_buf[_build_pos] = '['
    _build_pos = _build_pos + 1
    _build_first[_build_depth] = True
    _build_depth = _build_depth + 1

def json_build_array_end():
    """End a JSON array."""
    global _build_pos, _build_depth
    _build_depth = _build_depth - 1
    _build_buf[_build_pos] = ']'
    _build_pos = _build_pos + 1
    _build_buf[_build_pos] = '\0'

def _json_build_comma():
    """Add comma if not first element."""
    global _build_pos
    if _build_depth > 0:
        if not _build_first[_build_depth - 1]:
            _build_buf[_build_pos] = ','
            _build_pos = _build_pos + 1
        _build_first[_build_depth - 1] = False

def _json_build_key(key: Ptr[char]):
    """Add a key for object property."""
    global _build_pos
    _json_build_comma()
    _build_buf[_build_pos] = '"'
    _build_pos = _build_pos + 1
    i: int32 = 0
    while key[i] != '\0' and _build_pos < 1020:
        _build_buf[_build_pos] = key[i]
        _build_pos = _build_pos + 1
        i = i + 1
    _build_buf[_build_pos] = '"'
    _build_pos = _build_pos + 1
    _build_buf[_build_pos] = ':'
    _build_pos = _build_pos + 1

def json_build_string(key: Ptr[char], value: Ptr[char]):
    """Add a string property to object."""
    global _build_pos
    _json_build_key(key)
    _build_buf[_build_pos] = '"'
    _build_pos = _build_pos + 1
    i: int32 = 0
    while value[i] != '\0' and _build_pos < 1020:
        c: char = value[i]
        # Escape special characters
        if c == '"' or c == '\\':
            _build_buf[_build_pos] = '\\'
            _build_pos = _build_pos + 1
        elif c == '\n':
            _build_buf[_build_pos] = '\\'
            _build_pos = _build_pos + 1
            c = 'n'
        elif c == '\t':
            _build_buf[_build_pos] = '\\'
            _build_pos = _build_pos + 1
            c = 't'
        elif c == '\r':
            _build_buf[_build_pos] = '\\'
            _build_pos = _build_pos + 1
            c = 'r'
        _build_buf[_build_pos] = c
        _build_pos = _build_pos + 1
        i = i + 1
    _build_buf[_build_pos] = '"'
    _build_pos = _build_pos + 1
    _build_buf[_build_pos] = '\0'

def json_build_int(key: Ptr[char], value: int32):
    """Add an integer property to object."""
    global _build_pos
    _json_build_key(key)
    num_buf: Array[16, char]
    itoa(value, &num_buf[0])
    i: int32 = 0
    while num_buf[i] != '\0' and _build_pos < 1020:
        _build_buf[_build_pos] = num_buf[i]
        _build_pos = _build_pos + 1
        i = i + 1
    _build_buf[_build_pos] = '\0'

def json_build_bool(key: Ptr[char], value: bool):
    """Add a boolean property to object."""
    global _build_pos
    _json_build_key(key)
    if value:
        _build_buf[_build_pos] = 't'
        _build_buf[_build_pos + 1] = 'r'
        _build_buf[_build_pos + 2] = 'u'
        _build_buf[_build_pos + 3] = 'e'
        _build_pos = _build_pos + 4
    else:
        _build_buf[_build_pos] = 'f'
        _build_buf[_build_pos + 1] = 'a'
        _build_buf[_build_pos + 2] = 'l'
        _build_buf[_build_pos + 3] = 's'
        _build_buf[_build_pos + 4] = 'e'
        _build_pos = _build_pos + 5
    _build_buf[_build_pos] = '\0'

def json_build_null(key: Ptr[char]):
    """Add a null property to object."""
    global _build_pos
    _json_build_key(key)
    _build_buf[_build_pos] = 'n'
    _build_buf[_build_pos + 1] = 'u'
    _build_buf[_build_pos + 2] = 'l'
    _build_buf[_build_pos + 3] = 'l'
    _build_pos = _build_pos + 4
    _build_buf[_build_pos] = '\0'

def json_build_array_int(value: int32):
    """Add an integer to array."""
    global _build_pos
    _json_build_comma()
    num_buf: Array[16, char]
    itoa(value, &num_buf[0])
    i: int32 = 0
    while num_buf[i] != '\0' and _build_pos < 1020:
        _build_buf[_build_pos] = num_buf[i]
        _build_pos = _build_pos + 1
        i = i + 1
    _build_buf[_build_pos] = '\0'

def json_build_array_string(value: Ptr[char]):
    """Add a string to array."""
    global _build_pos
    _json_build_comma()
    _build_buf[_build_pos] = '"'
    _build_pos = _build_pos + 1
    i: int32 = 0
    while value[i] != '\0' and _build_pos < 1020:
        c: char = value[i]
        if c == '"' or c == '\\':
            _build_buf[_build_pos] = '\\'
            _build_pos = _build_pos + 1
        _build_buf[_build_pos] = c
        _build_pos = _build_pos + 1
        i = i + 1
    _build_buf[_build_pos] = '"'
    _build_pos = _build_pos + 1
    _build_buf[_build_pos] = '\0'

def json_build_get() -> Ptr[char]:
    """Get the built JSON string."""
    return &_build_buf[0]

def json_build_length() -> int32:
    """Get length of built JSON string."""
    return _build_pos
