# Pynux Algorithm Library
#
# Common algorithms for bare-metal ARM.
# Includes searching, sorting, and pattern matching.

from lib.memory import alloc, free, memcpy

# ============================================================================
# Binary Search
# ============================================================================

def binary_search(arr: Ptr[int32], length: int32, val: int32) -> int32:
    """Binary search for val in sorted array.

    Returns index of val if found, -1 otherwise.
    Array must be sorted in ascending order.
    """
    lo: int32 = 0
    hi: int32 = length - 1

    while lo <= hi:
        mid: int32 = lo + (hi - lo) / 2

        if arr[mid] == val:
            return mid
        elif arr[mid] < val:
            lo = mid + 1
        else:
            hi = mid - 1

    return -1

# ============================================================================
# Quicksort (in-place)
# ============================================================================

def _swap(arr: Ptr[int32], i: int32, j: int32):
    """Swap two elements in array."""
    tmp: int32 = arr[i]
    arr[i] = arr[j]
    arr[j] = tmp

def _partition(arr: Ptr[int32], lo: int32, hi: int32) -> int32:
    """Partition array around pivot (last element).

    Returns final position of pivot.
    """
    pivot: int32 = arr[hi]
    i: int32 = lo - 1

    j: int32 = lo
    while j < hi:
        if arr[j] <= pivot:
            i = i + 1
            _swap(arr, i, j)
        j = j + 1

    _swap(arr, i + 1, hi)
    return i + 1

def _quicksort_impl(arr: Ptr[int32], lo: int32, hi: int32):
    """Recursive quicksort implementation."""
    if lo < hi:
        p: int32 = _partition(arr, lo, hi)
        _quicksort_impl(arr, lo, p - 1)
        _quicksort_impl(arr, p + 1, hi)

def quicksort(arr: Ptr[int32], length: int32):
    """Sort array in-place using quicksort.

    Average case O(n log n), worst case O(n^2).
    Uses last element as pivot.
    """
    if length <= 1:
        return
    _quicksort_impl(arr, 0, length - 1)

# ============================================================================
# Mergesort (stable, needs temp buffer)
# ============================================================================

def _merge(arr: Ptr[int32], temp: Ptr[int32], lo: int32, mid: int32, hi: int32):
    """Merge two sorted subarrays [lo..mid] and [mid+1..hi]."""
    # Copy to temp buffer
    i: int32 = lo
    while i <= hi:
        temp[i] = arr[i]
        i = i + 1

    # Merge back
    left: int32 = lo
    right: int32 = mid + 1
    curr: int32 = lo

    while left <= mid and right <= hi:
        if temp[left] <= temp[right]:
            arr[curr] = temp[left]
            left = left + 1
        else:
            arr[curr] = temp[right]
            right = right + 1
        curr = curr + 1

    # Copy remaining elements from left half
    while left <= mid:
        arr[curr] = temp[left]
        left = left + 1
        curr = curr + 1

    # Right half elements are already in place

def _mergesort_impl(arr: Ptr[int32], temp: Ptr[int32], lo: int32, hi: int32):
    """Recursive mergesort implementation."""
    if lo < hi:
        mid: int32 = lo + (hi - lo) / 2
        _mergesort_impl(arr, temp, lo, mid)
        _mergesort_impl(arr, temp, mid + 1, hi)
        _merge(arr, temp, lo, mid, hi)

def mergesort(arr: Ptr[int32], length: int32):
    """Sort array using mergesort (stable).

    O(n log n) guaranteed. Allocates temporary buffer.
    Stable sort: equal elements maintain relative order.
    """
    if length <= 1:
        return

    # Allocate temp buffer
    temp: Ptr[int32] = cast[Ptr[int32]](alloc(length * 4))
    if cast[uint32](temp) == 0:
        return  # Allocation failed

    _mergesort_impl(arr, temp, 0, length - 1)

    # Free temp buffer
    free(cast[Ptr[uint8]](temp))

# ============================================================================
# Simple Regex Pattern Matching
# ============================================================================

# Supports:
#   Literal characters
#   .  - matches any single character
#   *  - matches zero or more of the preceding element
#   ^  - matches start of text (only at pattern start)
#   $  - matches end of text (only at pattern end)

def _regex_match_here(pattern: Ptr[char], pi: int32, text: Ptr[char], ti: int32) -> bool:
    """Match pattern starting at pi against text starting at ti."""

    # End of pattern
    if pattern[pi] == '\0':
        return True

    # Handle $ at end of pattern
    if pattern[pi] == '$' and pattern[pi + 1] == '\0':
        return text[ti] == '\0'

    # Handle * (zero or more of previous)
    if pattern[pi + 1] == '*':
        return _regex_match_star(pattern[pi], pattern, pi + 2, text, ti)

    # Handle . (any char) or literal match
    if text[ti] != '\0':
        if pattern[pi] == '.' or pattern[pi] == text[ti]:
            return _regex_match_here(pattern, pi + 1, text, ti + 1)

    return False

def _regex_match_star(c: char, pattern: Ptr[char], pi: int32, text: Ptr[char], ti: int32) -> bool:
    """Match c* at pattern[pi-2..] against text[ti..]."""

    # Try zero occurrences first
    if _regex_match_here(pattern, pi, text, ti):
        return True

    # Try one or more occurrences
    while text[ti] != '\0' and (c == '.' or text[ti] == c):
        ti = ti + 1
        if _regex_match_here(pattern, pi, text, ti):
            return True

    return False

def regex_match(pattern: Ptr[char], text: Ptr[char]) -> bool:
    """Match regex pattern against text.

    Supports:
      - Literal characters
      - . (any single character)
      - * (zero or more of preceding element)
      - ^ (start anchor, must be at pattern start)
      - $ (end anchor, must be at pattern end)

    Returns True if pattern matches text, False otherwise.
    """
    # Handle empty pattern
    if pattern[0] == '\0':
        return True

    # Handle ^ anchor at start
    if pattern[0] == '^':
        return _regex_match_here(pattern, 1, text, 0)

    # Try matching at each position in text
    ti: int32 = 0
    while True:
        if _regex_match_here(pattern, 0, text, ti):
            return True
        if text[ti] == '\0':
            break
        ti = ti + 1

    return False

# ============================================================================
# Additional Utility Functions
# ============================================================================

def linear_search(arr: Ptr[int32], length: int32, val: int32) -> int32:
    """Linear search for val in array.

    Returns index of first occurrence, -1 if not found.
    Works on unsorted arrays.
    """
    i: int32 = 0
    while i < length:
        if arr[i] == val:
            return i
        i = i + 1
    return -1

def is_sorted(arr: Ptr[int32], length: int32) -> bool:
    """Check if array is sorted in ascending order."""
    if length <= 1:
        return True
    i: int32 = 1
    while i < length:
        if arr[i] < arr[i - 1]:
            return False
        i = i + 1
    return True

def reverse(arr: Ptr[int32], length: int32):
    """Reverse array in-place."""
    lo: int32 = 0
    hi: int32 = length - 1
    while lo < hi:
        _swap(arr, lo, hi)
        lo = lo + 1
        hi = hi - 1

def find_min(arr: Ptr[int32], length: int32) -> int32:
    """Find index of minimum element."""
    if length <= 0:
        return -1
    min_idx: int32 = 0
    i: int32 = 1
    while i < length:
        if arr[i] < arr[min_idx]:
            min_idx = i
        i = i + 1
    return min_idx

def find_max(arr: Ptr[int32], length: int32) -> int32:
    """Find index of maximum element."""
    if length <= 0:
        return -1
    max_idx: int32 = 0
    i: int32 = 1
    while i < length:
        if arr[i] > arr[max_idx]:
            max_idx = i
        i = i + 1
    return max_idx
