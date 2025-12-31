# Pynux Data Structures Library
#
# Additional data structures for bare-metal ARM:
# - Priority Queue (min-heap) - pq_* functions
# - Ring Buffer (circular buffer) - ring_* functions
# - Bitset (bit array) - bitset_* functions
# - Binary Search Tree - bst_* functions
# - Deque (double-ended queue) - deque_* functions

from lib.memory import alloc, free, memcpy

# ============================================================================
# Priority Queue (Min-Heap)
# ============================================================================
#
# Structure layout:
#   data: Ptr[int32]  - Array of elements (offset 0)
#   len: int32        - Number of elements (offset 4)
#   cap: int32        - Capacity (offset 8)
# Total: 12 bytes

PQ_DATA_OFFSET: int32 = 0
PQ_LEN_OFFSET: int32 = 4
PQ_CAP_OFFSET: int32 = 8
PQ_STRUCT_SIZE: int32 = 12

DEFAULT_PQ_CAP: int32 = 16

def pq_init(h: Ptr[int32]):
    """Initialize a new min-heap priority queue."""
    data: Ptr[int32] = cast[Ptr[int32]](alloc(DEFAULT_PQ_CAP * 4))
    h[0] = cast[int32](data)
    h[1] = 0  # len
    h[2] = DEFAULT_PQ_CAP

def pq_free(h: Ptr[int32]):
    """Free priority queue memory."""
    data: Ptr[int32] = cast[Ptr[int32]](h[0])
    if cast[uint32](data) != 0:
        free(cast[Ptr[uint8]](data))
    h[0] = 0
    h[1] = 0
    h[2] = 0

def pq_len(h: Ptr[int32]) -> int32:
    """Return number of elements in priority queue."""
    return h[1]

def pq_is_empty(h: Ptr[int32]) -> bool:
    """Check if priority queue is empty."""
    return h[1] == 0

def pq_peek(h: Ptr[int32]) -> int32:
    """Return minimum element without removing it. Returns 0 if empty."""
    if h[1] == 0:
        return 0
    data: Ptr[int32] = cast[Ptr[int32]](h[0])
    return data[0]

def _pq_grow(h: Ptr[int32]):
    """Grow priority queue capacity."""
    old_cap: int32 = h[2]
    new_cap: int32 = old_cap * 2
    old_data: Ptr[int32] = cast[Ptr[int32]](h[0])
    new_data: Ptr[int32] = cast[Ptr[int32]](alloc(new_cap * 4))
    if cast[uint32](new_data) != 0:
        memcpy(cast[Ptr[uint8]](new_data), cast[Ptr[uint8]](old_data), h[1] * 4)
        free(cast[Ptr[uint8]](old_data))
        h[0] = cast[int32](new_data)
        h[2] = new_cap

def _pq_sift_up(h: Ptr[int32], idx: int32):
    """Move element up to maintain heap property."""
    data: Ptr[int32] = cast[Ptr[int32]](h[0])
    while idx > 0:
        parent: int32 = (idx - 1) / 2
        if data[idx] < data[parent]:
            # Swap
            tmp: int32 = data[idx]
            data[idx] = data[parent]
            data[parent] = tmp
            idx = parent
        else:
            break

def _pq_sift_down(h: Ptr[int32], idx: int32):
    """Move element down to maintain heap property."""
    data: Ptr[int32] = cast[Ptr[int32]](h[0])
    length: int32 = h[1]
    while True:
        smallest: int32 = idx
        left: int32 = 2 * idx + 1
        right: int32 = 2 * idx + 2

        if left < length and data[left] < data[smallest]:
            smallest = left
        if right < length and data[right] < data[smallest]:
            smallest = right

        if smallest != idx:
            # Swap
            tmp: int32 = data[idx]
            data[idx] = data[smallest]
            data[smallest] = tmp
            idx = smallest
        else:
            break

def pq_push(h: Ptr[int32], val: int32):
    """Push a value onto the priority queue."""
    if h[1] >= h[2]:
        _pq_grow(h)
    data: Ptr[int32] = cast[Ptr[int32]](h[0])
    idx: int32 = h[1]
    data[idx] = val
    h[1] = h[1] + 1
    _pq_sift_up(h, idx)

def pq_pop(h: Ptr[int32]) -> int32:
    """Remove and return minimum element. Returns 0 if empty."""
    if h[1] == 0:
        return 0
    data: Ptr[int32] = cast[Ptr[int32]](h[0])
    result: int32 = data[0]
    h[1] = h[1] - 1
    if h[1] > 0:
        data[0] = data[h[1]]
        _pq_sift_down(h, 0)
    return result

def pq_heapify(h: Ptr[int32], arr: Ptr[int32], length: int32):
    """Build priority queue from array."""
    # Ensure capacity
    while h[2] < length:
        _pq_grow(h)

    # Copy array
    data: Ptr[int32] = cast[Ptr[int32]](h[0])
    i: int32 = 0
    while i < length:
        data[i] = arr[i]
        i = i + 1
    h[1] = length

    # Heapify from bottom up
    i = (length / 2) - 1
    while i >= 0:
        _pq_sift_down(h, i)
        i = i - 1

# ============================================================================
# Ring Buffer (Circular Buffer)
# ============================================================================
#
# Structure layout:
#   data: Ptr[int32]  - Array of elements (offset 0)
#   head: int32       - Read position (offset 4)
#   tail: int32       - Write position (offset 8)
#   cap: int32        - Capacity (offset 12)
#   count: int32      - Number of elements (offset 16)
# Total: 20 bytes

RING_DATA_OFFSET: int32 = 0
RING_HEAD_OFFSET: int32 = 4
RING_TAIL_OFFSET: int32 = 8
RING_CAP_OFFSET: int32 = 12
RING_COUNT_OFFSET: int32 = 16
RING_STRUCT_SIZE: int32 = 20

def ring_init(r: Ptr[int32], capacity: int32):
    """Initialize a ring buffer with given capacity."""
    data: Ptr[int32] = cast[Ptr[int32]](alloc(capacity * 4))
    r[0] = cast[int32](data)
    r[1] = 0  # head
    r[2] = 0  # tail
    r[3] = capacity
    r[4] = 0  # count

def ring_free(r: Ptr[int32]):
    """Free ring buffer memory."""
    data: Ptr[int32] = cast[Ptr[int32]](r[0])
    if cast[uint32](data) != 0:
        free(cast[Ptr[uint8]](data))
    r[0] = 0
    r[1] = 0
    r[2] = 0
    r[3] = 0
    r[4] = 0

def ring_is_empty(r: Ptr[int32]) -> bool:
    """Check if ring buffer is empty."""
    return r[4] == 0

def ring_is_full(r: Ptr[int32]) -> bool:
    """Check if ring buffer is full."""
    return r[4] == r[3]

def ring_len(r: Ptr[int32]) -> int32:
    """Return number of elements in ring buffer."""
    return r[4]

def ring_cap(r: Ptr[int32]) -> int32:
    """Return capacity of ring buffer."""
    return r[3]

def ring_push(r: Ptr[int32], val: int32) -> bool:
    """Push value to ring buffer. Returns False if full."""
    if r[4] >= r[3]:
        return False  # Full
    data: Ptr[int32] = cast[Ptr[int32]](r[0])
    data[r[2]] = val
    r[2] = (r[2] + 1) % r[3]  # Advance tail
    r[4] = r[4] + 1
    return True

def ring_pop(r: Ptr[int32]) -> int32:
    """Pop value from ring buffer. Returns 0 if empty."""
    if r[4] == 0:
        return 0  # Empty
    data: Ptr[int32] = cast[Ptr[int32]](r[0])
    val: int32 = data[r[1]]
    r[1] = (r[1] + 1) % r[3]  # Advance head
    r[4] = r[4] - 1
    return val

def ring_peek(r: Ptr[int32]) -> int32:
    """Peek at front element without removing. Returns 0 if empty."""
    if r[4] == 0:
        return 0
    data: Ptr[int32] = cast[Ptr[int32]](r[0])
    return data[r[1]]

def ring_clear(r: Ptr[int32]):
    """Clear all elements from ring buffer."""
    r[1] = 0  # head
    r[2] = 0  # tail
    r[4] = 0  # count

# ============================================================================
# Bitset (Bit Array)
# ============================================================================
#
# Structure layout:
#   data: Ptr[uint32] - Array of 32-bit words (offset 0)
#   nbits: int32      - Number of bits (offset 4)
#   nwords: int32     - Number of words (offset 8)
# Total: 12 bytes

BITSET_DATA_OFFSET: int32 = 0
BITSET_NBITS_OFFSET: int32 = 4
BITSET_NWORDS_OFFSET: int32 = 8
BITSET_STRUCT_SIZE: int32 = 12

def bitset_init(b: Ptr[int32], nbits: int32):
    """Initialize a bitset with given number of bits."""
    nwords: int32 = (nbits + 31) / 32
    data: Ptr[uint32] = cast[Ptr[uint32]](alloc(nwords * 4))
    # Clear all bits
    i: int32 = 0
    while i < nwords:
        data[i] = 0
        i = i + 1
    b[0] = cast[int32](data)
    b[1] = nbits
    b[2] = nwords

def bitset_free(b: Ptr[int32]):
    """Free bitset memory."""
    data: Ptr[uint32] = cast[Ptr[uint32]](b[0])
    if cast[uint32](data) != 0:
        free(cast[Ptr[uint8]](data))
    b[0] = 0
    b[1] = 0
    b[2] = 0

def bitset_size(b: Ptr[int32]) -> int32:
    """Return number of bits in bitset."""
    return b[1]

def bitset_set(b: Ptr[int32], bit: int32):
    """Set bit at given index."""
    if bit < 0 or bit >= b[1]:
        return
    data: Ptr[uint32] = cast[Ptr[uint32]](b[0])
    word: int32 = bit / 32
    offset: int32 = bit % 32
    data[word] = data[word] | (1 << offset)

def bitset_clear(b: Ptr[int32], bit: int32):
    """Clear bit at given index."""
    if bit < 0 or bit >= b[1]:
        return
    data: Ptr[uint32] = cast[Ptr[uint32]](b[0])
    word: int32 = bit / 32
    offset: int32 = bit % 32
    data[word] = data[word] & ~(1 << offset)

def bitset_test(b: Ptr[int32], bit: int32) -> bool:
    """Test if bit is set at given index."""
    if bit < 0 or bit >= b[1]:
        return False
    data: Ptr[uint32] = cast[Ptr[uint32]](b[0])
    word: int32 = bit / 32
    offset: int32 = bit % 32
    return (data[word] & (1 << offset)) != 0

def bitset_toggle(b: Ptr[int32], bit: int32):
    """Toggle bit at given index."""
    if bit < 0 or bit >= b[1]:
        return
    data: Ptr[uint32] = cast[Ptr[uint32]](b[0])
    word: int32 = bit / 32
    offset: int32 = bit % 32
    data[word] = data[word] ^ (1 << offset)

def _popcount32(val: uint32) -> int32:
    """Count number of set bits in a 32-bit word."""
    count: int32 = 0
    while val != 0:
        count = count + cast[int32](val & 1)
        val = val >> 1
    return count

def bitset_count(b: Ptr[int32]) -> int32:
    """Count number of set bits in bitset."""
    data: Ptr[uint32] = cast[Ptr[uint32]](b[0])
    nwords: int32 = b[2]
    total: int32 = 0
    i: int32 = 0
    while i < nwords:
        total = total + _popcount32(data[i])
        i = i + 1
    return total

def bitset_clear_all(b: Ptr[int32]):
    """Clear all bits."""
    data: Ptr[uint32] = cast[Ptr[uint32]](b[0])
    nwords: int32 = b[2]
    i: int32 = 0
    while i < nwords:
        data[i] = 0
        i = i + 1

def bitset_set_all(b: Ptr[int32]):
    """Set all bits."""
    data: Ptr[uint32] = cast[Ptr[uint32]](b[0])
    nwords: int32 = b[2]
    i: int32 = 0
    while i < nwords:
        data[i] = 0xFFFFFFFF
        i = i + 1

# ============================================================================
# Binary Search Tree
# ============================================================================
#
# Node structure layout:
#   key: int32    - Key value (offset 0)
#   left: Ptr     - Left child (offset 4)
#   right: Ptr    - Right child (offset 8)
# Total: 12 bytes per node
#
# Tree structure layout:
#   root: Ptr     - Root node (offset 0)
#   size: int32   - Number of nodes (offset 4)
# Total: 8 bytes

BST_NODE_KEY_OFFSET: int32 = 0
BST_NODE_LEFT_OFFSET: int32 = 4
BST_NODE_RIGHT_OFFSET: int32 = 8
BST_NODE_SIZE: int32 = 12

BST_ROOT_OFFSET: int32 = 0
BST_SIZE_OFFSET: int32 = 4
BST_STRUCT_SIZE: int32 = 8

def bst_init(t: Ptr[int32]):
    """Initialize an empty binary search tree."""
    t[0] = 0  # root = null
    t[1] = 0  # size = 0

def _bst_new_node(key: int32) -> Ptr[int32]:
    """Allocate a new BST node."""
    node: Ptr[int32] = cast[Ptr[int32]](alloc(BST_NODE_SIZE))
    node[0] = key    # key
    node[1] = 0      # left = null
    node[2] = 0      # right = null
    return node

def _bst_free_node(node: Ptr[int32]):
    """Free a single BST node."""
    free(cast[Ptr[uint8]](node))

def _bst_free_subtree(node: Ptr[int32]):
    """Recursively free a subtree."""
    if cast[uint32](node) == 0:
        return
    left: Ptr[int32] = cast[Ptr[int32]](node[1])
    right: Ptr[int32] = cast[Ptr[int32]](node[2])
    _bst_free_subtree(left)
    _bst_free_subtree(right)
    _bst_free_node(node)

def bst_free(t: Ptr[int32]):
    """Free all BST memory."""
    root: Ptr[int32] = cast[Ptr[int32]](t[0])
    _bst_free_subtree(root)
    t[0] = 0
    t[1] = 0

def bst_len(t: Ptr[int32]) -> int32:
    """Return number of nodes in BST."""
    return t[1]

def bst_is_empty(t: Ptr[int32]) -> bool:
    """Check if BST is empty."""
    return t[1] == 0

def bst_insert(t: Ptr[int32], key: int32):
    """Insert a key into the BST."""
    new_node: Ptr[int32] = _bst_new_node(key)

    if t[0] == 0:
        t[0] = cast[int32](new_node)
        t[1] = 1
        return

    current: Ptr[int32] = cast[Ptr[int32]](t[0])
    while True:
        if key < current[0]:
            if current[1] == 0:
                current[1] = cast[int32](new_node)
                break
            current = cast[Ptr[int32]](current[1])
        elif key > current[0]:
            if current[2] == 0:
                current[2] = cast[int32](new_node)
                break
            current = cast[Ptr[int32]](current[2])
        else:
            # Key already exists - free new node and return
            _bst_free_node(new_node)
            return

    t[1] = t[1] + 1

def bst_find(t: Ptr[int32], key: int32) -> bool:
    """Check if key exists in BST."""
    current: Ptr[int32] = cast[Ptr[int32]](t[0])
    while cast[uint32](current) != 0:
        if key < current[0]:
            current = cast[Ptr[int32]](current[1])
        elif key > current[0]:
            current = cast[Ptr[int32]](current[2])
        else:
            return True
    return False

def _bst_find_min(node: Ptr[int32]) -> Ptr[int32]:
    """Find minimum node in subtree."""
    while node[1] != 0:
        node = cast[Ptr[int32]](node[1])
    return node

def _bst_delete_node(node: Ptr[int32], key: int32) -> Ptr[int32]:
    """Delete key from subtree rooted at node. Returns new root of subtree."""
    if cast[uint32](node) == 0:
        return Ptr[int32](0)

    if key < node[0]:
        node[1] = cast[int32](_bst_delete_node(cast[Ptr[int32]](node[1]), key))
    elif key > node[0]:
        node[2] = cast[int32](_bst_delete_node(cast[Ptr[int32]](node[2]), key))
    else:
        # Found the node to delete
        left: Ptr[int32] = cast[Ptr[int32]](node[1])
        right: Ptr[int32] = cast[Ptr[int32]](node[2])

        if cast[uint32](left) == 0:
            _bst_free_node(node)
            return right
        elif cast[uint32](right) == 0:
            _bst_free_node(node)
            return left
        else:
            # Node has two children - find in-order successor
            successor: Ptr[int32] = _bst_find_min(right)
            node[0] = successor[0]  # Copy successor's key
            node[2] = cast[int32](_bst_delete_node(right, successor[0]))

    return node

def bst_delete(t: Ptr[int32], key: int32) -> bool:
    """Delete key from BST. Returns True if key was found and deleted."""
    if not bst_find(t, key):
        return False

    root: Ptr[int32] = cast[Ptr[int32]](t[0])
    t[0] = cast[int32](_bst_delete_node(root, key))
    t[1] = t[1] - 1
    return True

def _bst_inorder_helper(node: Ptr[int32], out: Ptr[int32], idx: Ptr[int32]):
    """In-order traversal helper."""
    if cast[uint32](node) == 0:
        return

    _bst_inorder_helper(cast[Ptr[int32]](node[1]), out, idx)
    out[idx[0]] = node[0]
    idx[0] = idx[0] + 1
    _bst_inorder_helper(cast[Ptr[int32]](node[2]), out, idx)

def bst_inorder(t: Ptr[int32], out: Ptr[int32]) -> int32:
    """Fill output array with keys in sorted order. Returns count."""
    idx: int32 = 0
    _bst_inorder_helper(cast[Ptr[int32]](t[0]), out, &idx)
    return idx

def bst_min(t: Ptr[int32]) -> int32:
    """Return minimum key in BST. Returns 0 if empty."""
    if t[0] == 0:
        return 0
    node: Ptr[int32] = _bst_find_min(cast[Ptr[int32]](t[0]))
    return node[0]

def bst_max(t: Ptr[int32]) -> int32:
    """Return maximum key in BST. Returns 0 if empty."""
    if t[0] == 0:
        return 0
    node: Ptr[int32] = cast[Ptr[int32]](t[0])
    while node[2] != 0:
        node = cast[Ptr[int32]](node[2])
    return node[0]

# ============================================================================
# Deque (Double-Ended Queue)
# ============================================================================
#
# Uses a circular buffer with head and tail pointers.
#
# Structure layout:
#   data: Ptr[int32]  - Array of elements (offset 0)
#   head: int32       - Front position (offset 4)
#   tail: int32       - Back position (offset 8)
#   cap: int32        - Capacity (offset 12)
#   count: int32      - Number of elements (offset 16)
# Total: 20 bytes

DEQUE_DATA_OFFSET: int32 = 0
DEQUE_HEAD_OFFSET: int32 = 4
DEQUE_TAIL_OFFSET: int32 = 8
DEQUE_CAP_OFFSET: int32 = 12
DEQUE_COUNT_OFFSET: int32 = 16
DEQUE_STRUCT_SIZE: int32 = 20

DEFAULT_DEQUE_CAP: int32 = 16

def deque_init(d: Ptr[int32]):
    """Initialize a new deque."""
    data: Ptr[int32] = cast[Ptr[int32]](alloc(DEFAULT_DEQUE_CAP * 4))
    d[0] = cast[int32](data)
    d[1] = 0  # head
    d[2] = 0  # tail
    d[3] = DEFAULT_DEQUE_CAP
    d[4] = 0  # count

def deque_free(d: Ptr[int32]):
    """Free deque memory."""
    data: Ptr[int32] = cast[Ptr[int32]](d[0])
    if cast[uint32](data) != 0:
        free(cast[Ptr[uint8]](data))
    d[0] = 0
    d[1] = 0
    d[2] = 0
    d[3] = 0
    d[4] = 0

def deque_is_empty(d: Ptr[int32]) -> bool:
    """Check if deque is empty."""
    return d[4] == 0

def deque_is_full(d: Ptr[int32]) -> bool:
    """Check if deque is full."""
    return d[4] == d[3]

def deque_len(d: Ptr[int32]) -> int32:
    """Return number of elements in deque."""
    return d[4]

def _deque_grow(d: Ptr[int32]):
    """Grow deque capacity."""
    old_cap: int32 = d[3]
    new_cap: int32 = old_cap * 2
    old_data: Ptr[int32] = cast[Ptr[int32]](d[0])
    new_data: Ptr[int32] = cast[Ptr[int32]](alloc(new_cap * 4))

    if cast[uint32](new_data) == 0:
        return

    # Copy elements in order from head to tail
    count: int32 = d[4]
    old_head: int32 = d[1]
    i: int32 = 0
    while i < count:
        new_data[i] = old_data[(old_head + i) % old_cap]
        i = i + 1

    free(cast[Ptr[uint8]](old_data))
    d[0] = cast[int32](new_data)
    d[1] = 0  # head at beginning
    d[2] = count  # tail after last element
    d[3] = new_cap

def deque_push_back(d: Ptr[int32], val: int32):
    """Push value to back of deque."""
    if d[4] >= d[3]:
        _deque_grow(d)
    data: Ptr[int32] = cast[Ptr[int32]](d[0])
    data[d[2]] = val
    d[2] = (d[2] + 1) % d[3]
    d[4] = d[4] + 1

def deque_push_front(d: Ptr[int32], val: int32):
    """Push value to front of deque."""
    if d[4] >= d[3]:
        _deque_grow(d)
    data: Ptr[int32] = cast[Ptr[int32]](d[0])
    d[1] = (d[1] - 1 + d[3]) % d[3]  # Move head back
    data[d[1]] = val
    d[4] = d[4] + 1

def deque_pop_back(d: Ptr[int32]) -> int32:
    """Pop value from back of deque. Returns 0 if empty."""
    if d[4] == 0:
        return 0
    data: Ptr[int32] = cast[Ptr[int32]](d[0])
    d[2] = (d[2] - 1 + d[3]) % d[3]  # Move tail back
    d[4] = d[4] - 1
    return data[d[2]]

def deque_pop_front(d: Ptr[int32]) -> int32:
    """Pop value from front of deque. Returns 0 if empty."""
    if d[4] == 0:
        return 0
    data: Ptr[int32] = cast[Ptr[int32]](d[0])
    val: int32 = data[d[1]]
    d[1] = (d[1] + 1) % d[3]
    d[4] = d[4] - 1
    return val

def deque_front(d: Ptr[int32]) -> int32:
    """Peek at front element. Returns 0 if empty."""
    if d[4] == 0:
        return 0
    data: Ptr[int32] = cast[Ptr[int32]](d[0])
    return data[d[1]]

def deque_back(d: Ptr[int32]) -> int32:
    """Peek at back element. Returns 0 if empty."""
    if d[4] == 0:
        return 0
    data: Ptr[int32] = cast[Ptr[int32]](d[0])
    back_idx: int32 = (d[2] - 1 + d[3]) % d[3]
    return data[back_idx]

def deque_get(d: Ptr[int32], idx: int32) -> int32:
    """Get element at index (0 = front). Returns 0 if out of bounds."""
    if idx < 0 or idx >= d[4]:
        return 0
    data: Ptr[int32] = cast[Ptr[int32]](d[0])
    actual_idx: int32 = (d[1] + idx) % d[3]
    return data[actual_idx]

def deque_clear(d: Ptr[int32]):
    """Clear all elements from deque."""
    d[1] = 0  # head
    d[2] = 0  # tail
    d[4] = 0  # count
