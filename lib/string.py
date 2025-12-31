# Pynux String Library
#
# String operations for bare-metal ARM.

from lib.memory import alloc, free, memcpy, memset

# String structure
# Uses a length-prefixed format with null terminator for C compat
# Layout: [len: int32][cap: int32][data...]\0

STRING_HEADER: int32 = 8  # len + cap

# Get string length (C string)
def strlen(s: Ptr[char]) -> int32:
    length: int32 = 0
    while s[length] != '\0':
        length = length + 1
    return length

# Copy string
def strcpy(dst: Ptr[char], src: Ptr[char]) -> Ptr[char]:
    i: int32 = 0
    while src[i] != '\0':
        dst[i] = src[i]
        i = i + 1
    dst[i] = '\0'
    return dst

# Copy n characters
def strncpy(dst: Ptr[char], src: Ptr[char], n: int32) -> Ptr[char]:
    i: int32 = 0
    while i < n and src[i] != '\0':
        dst[i] = src[i]
        i = i + 1
    while i < n:
        dst[i] = '\0'
        i = i + 1
    return dst

# Concatenate strings
def strcat(dst: Ptr[char], src: Ptr[char]) -> Ptr[char]:
    dst_len: int32 = strlen(dst)
    i: int32 = 0
    while src[i] != '\0':
        dst[dst_len + i] = src[i]
        i = i + 1
    dst[dst_len + i] = '\0'
    return dst

# Concatenate with size limit (safe version)
# n is the total buffer size of dst (including existing content and null terminator)
def strncat(dst: Ptr[char], src: Ptr[char], n: int32) -> Ptr[char]:
    dst_len: int32 = strlen(dst)
    i: int32 = 0
    # Leave room for null terminator
    while src[i] != '\0' and (dst_len + i) < (n - 1):
        dst[dst_len + i] = src[i]
        i = i + 1
    dst[dst_len + i] = '\0'
    return dst

# Safe string copy with buffer size
# Returns number of characters copied (not including null), or -1 if truncated
def strcpy_s(dst: Ptr[char], dst_size: int32, src: Ptr[char]) -> int32:
    if dst_size <= 0:
        return -1
    i: int32 = 0
    while i < (dst_size - 1) and src[i] != '\0':
        dst[i] = src[i]
        i = i + 1
    dst[i] = '\0'
    # Check if we truncated
    if src[i] != '\0':
        return -1
    return i

# Compare strings
def strcmp(a: Ptr[char], b: Ptr[char]) -> int32:
    i: int32 = 0
    while a[i] != '\0' and b[i] != '\0':
        if a[i] != b[i]:
            return cast[int32](a[i]) - cast[int32](b[i])
        i = i + 1
    return cast[int32](a[i]) - cast[int32](b[i])

# Compare n characters
def strncmp(a: Ptr[char], b: Ptr[char], n: int32) -> int32:
    i: int32 = 0
    while i < n and a[i] != '\0' and b[i] != '\0':
        if a[i] != b[i]:
            return cast[int32](a[i]) - cast[int32](b[i])
        i = i + 1
    if i == n:
        return 0
    return cast[int32](a[i]) - cast[int32](b[i])

# Find character in string
def strchr(s: Ptr[char], c: char) -> Ptr[char]:
    i: int32 = 0
    while s[i] != '\0':
        if s[i] == c:
            return &s[i]
        i = i + 1
    if c == '\0':
        return &s[i]
    return Ptr[char](0)

# Find last occurrence
def strrchr(s: Ptr[char], c: char) -> Ptr[char]:
    last: Ptr[char] = Ptr[char](0)
    i: int32 = 0
    while s[i] != '\0':
        if s[i] == c:
            last = &s[i]
        i = i + 1
    if c == '\0':
        return &s[i]
    return last

# Find substring
def strstr(haystack: Ptr[char], needle: Ptr[char]) -> Ptr[char]:
    if needle[0] == '\0':
        return haystack

    i: int32 = 0
    while haystack[i] != '\0':
        j: int32 = 0
        while needle[j] != '\0' and haystack[i + j] == needle[j]:
            j = j + 1
        if needle[j] == '\0':
            return &haystack[i]
        i = i + 1
    return Ptr[char](0)

# Duplicate string (allocates memory)
def strdup(s: Ptr[char]) -> Ptr[char]:
    length: int32 = strlen(s)
    new_s: Ptr[char] = cast[Ptr[char]](alloc(length + 1))
    if cast[uint32](new_s) != 0:
        strcpy(new_s, s)
    return new_s

# Convert to uppercase
def toupper(c: char) -> char:
    if c >= 'a' and c <= 'z':
        return cast[char](cast[int32](c) - 32)
    return c

# Convert to lowercase
def tolower(c: char) -> char:
    if c >= 'A' and c <= 'Z':
        return cast[char](cast[int32](c) + 32)
    return c

# Check character types
def isdigit(c: char) -> bool:
    return c >= '0' and c <= '9'

def isalpha(c: char) -> bool:
    return (c >= 'a' and c <= 'z') or (c >= 'A' and c <= 'Z')

def isalnum(c: char) -> bool:
    return isdigit(c) or isalpha(c)

def isspace(c: char) -> bool:
    return c == ' ' or c == '\t' or c == '\n' or c == '\r'

def isprint(c: char) -> bool:
    return c >= ' ' and c <= '~'

# Parse integer from string
def atoi(s: Ptr[char]) -> int32:
    result: int32 = 0
    sign: int32 = 1
    i: int32 = 0

    # Skip whitespace
    while isspace(s[i]):
        i = i + 1

    # Handle sign
    if s[i] == '-':
        sign = -1
        i = i + 1
    elif s[i] == '+':
        i = i + 1

    # Parse digits
    while isdigit(s[i]):
        result = result * 10 + (cast[int32](s[i]) - cast[int32]('0'))
        i = i + 1

    return result * sign

# Integer to string
def itoa(n: int32, buf: Ptr[char]) -> Ptr[char]:
    if n == 0:
        buf[0] = '0'
        buf[1] = '\0'
        return buf

    neg: bool = n < 0
    if neg:
        n = -n

    # Build digits in reverse
    i: int32 = 0
    while n > 0:
        buf[i] = cast[char](cast[int32]('0') + (n % 10))
        n = n / 10
        i = i + 1

    if neg:
        buf[i] = '-'
        i = i + 1

    buf[i] = '\0'

    # Reverse
    j: int32 = 0
    k: int32 = i - 1
    while j < k:
        tmp: char = buf[j]
        buf[j] = buf[k]
        buf[k] = tmp
        j = j + 1
        k = k - 1

    return buf

# Split string by delimiter (modifies original, returns pointers)
def strtok(s: Ptr[char], delim: char) -> Ptr[char]:
    # Static state for continuation
    # For simplicity, just find and null-terminate at delimiter
    if s[0] == '\0':
        return Ptr[char](0)

    start: Ptr[char] = s
    i: int32 = 0
    while s[i] != '\0' and s[i] != delim:
        i = i + 1

    if s[i] == delim:
        s[i] = '\0'

    return start

# Trim whitespace from start
def ltrim(s: Ptr[char]) -> Ptr[char]:
    while isspace(s[0]):
        s = &s[1]
    return s

# Trim whitespace from end (modifies string)
def rtrim(s: Ptr[char]):
    length: int32 = strlen(s)
    while length > 0 and isspace(s[length - 1]):
        length = length - 1
    s[length] = '\0'

# Strip whitespace from both ends (modifies string, returns pointer)
def strip(s: Ptr[char]) -> Ptr[char]:
    rtrim(s)
    return ltrim(s)

# Replace first occurrence of old with new in string
# dst must have enough space, returns dst
def str_replace(dst: Ptr[char], src: Ptr[char], old: Ptr[char], new: Ptr[char]) -> Ptr[char]:
    old_len: int32 = strlen(old)
    new_len: int32 = strlen(new)
    src_len: int32 = strlen(src)

    # Find old in src
    pos: Ptr[char] = strstr(src, old)
    if cast[uint32](pos) == 0:
        # Not found, just copy
        strcpy(dst, src)
        return dst

    # Copy part before match
    prefix_len: int32 = cast[int32](pos) - cast[int32](src)
    i: int32 = 0
    while i < prefix_len:
        dst[i] = src[i]
        i = i + 1

    # Copy replacement
    j: int32 = 0
    while j < new_len:
        dst[i] = new[j]
        i = i + 1
        j = j + 1

    # Copy part after match
    suffix_start: int32 = prefix_len + old_len
    while suffix_start < src_len:
        dst[i] = src[suffix_start]
        i = i + 1
        suffix_start = suffix_start + 1

    dst[i] = '\0'
    return dst

# Replace all occurrences of old with new
def str_replace_all(dst: Ptr[char], src: Ptr[char], old: Ptr[char], new: Ptr[char]) -> Ptr[char]:
    old_len: int32 = strlen(old)
    new_len: int32 = strlen(new)
    src_len: int32 = strlen(src)

    si: int32 = 0  # Source index
    di: int32 = 0  # Dest index

    while si < src_len:
        # Check if old matches at current position
        is_match: bool = True
        k: int32 = 0
        while k < old_len:
            if src[si + k] != old[k]:
                is_match = False
                break
            k = k + 1

        if is_match:
            # Copy replacement
            j: int32 = 0
            while j < new_len:
                dst[di] = new[j]
                di = di + 1
                j = j + 1
            si = si + old_len
        else:
            dst[di] = src[si]
            di = di + 1
            si = si + 1

    dst[di] = '\0'
    return dst

# Split string by delimiter into array of pointers
# Modifies src in place, returns count of parts
# parts array must be pre-allocated with enough space
def str_split(src: Ptr[char], delim: char, parts: Ptr[Ptr[char]], max_parts: int32) -> int32:
    count: int32 = 0
    start: int32 = 0
    i: int32 = 0

    while src[i] != '\0' and count < max_parts:
        if src[i] == delim:
            src[i] = '\0'
            parts[count] = &src[start]
            count = count + 1
            start = i + 1
        i = i + 1

    # Add last part if any
    if start <= i and count < max_parts:
        parts[count] = &src[start]
        count = count + 1

    return count

# Join array of strings with delimiter
def str_join(dst: Ptr[char], parts: Ptr[Ptr[char]], count: int32, delim: Ptr[char]) -> Ptr[char]:
    dst[0] = '\0'
    delim_len: int32 = strlen(delim)

    i: int32 = 0
    di: int32 = 0

    while i < count:
        # Copy part
        p: Ptr[char] = parts[i]
        j: int32 = 0
        while p[j] != '\0':
            dst[di] = p[j]
            di = di + 1
            j = j + 1

        # Add delimiter if not last
        if i < count - 1:
            j = 0
            while j < delim_len:
                dst[di] = delim[j]
                di = di + 1
                j = j + 1

        i = i + 1

    dst[di] = '\0'
    return dst

# Count occurrences of substring
def str_count(s: Ptr[char], sub: Ptr[char]) -> int32:
    count: int32 = 0
    sub_len: int32 = strlen(sub)
    if sub_len == 0:
        return 0

    pos: Ptr[char] = strstr(s, sub)
    while cast[uint32](pos) != 0:
        count = count + 1
        pos = strstr(&pos[sub_len], sub)

    return count

# Find index of substring, returns -1 if not found
def str_index(s: Ptr[char], sub: Ptr[char]) -> int32:
    pos: Ptr[char] = strstr(s, sub)
    if cast[uint32](pos) == 0:
        return -1
    return cast[int32](pos) - cast[int32](s)
