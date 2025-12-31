# Pynux Developer Tools Library
#
# Developer utilities for testing, debugging, and disassembly.
# For bare-metal ARM Cortex-M3.

from lib.io import print_str, print_int, print_hex, print_newline, uart_putc
from lib.memory import HEAP_START, HEAP_SIZE, HEADER_SIZE

# ============================================================================
# Simple Inline Test Framework (for production code assertions)
# Note: For full test suites, use tests/framework.py instead
# ============================================================================

# Test state
_dev_test_name: Ptr[char] = Ptr[char](0)
_dev_test_pass_count: int32 = 0
_dev_test_fail_count: int32 = 0
_dev_test_active: bool = False

def dev_test_start(name: Ptr[char]):
    """Begin a test suite with the given name."""
    global _dev_test_name, _dev_test_pass_count, _dev_test_fail_count, _dev_test_active
    _dev_test_name = name
    _dev_test_pass_count = 0
    _dev_test_fail_count = 0
    _dev_test_active = True
    print_str("=== Test Suite: ")
    print_str(name)
    print_str(" ===")
    print_newline()

def dev_test_end() -> bool:
    """End test suite and report results. Returns True if all passed."""
    global _dev_test_active
    _dev_test_active = False
    print_newline()
    print_str("--- Results: ")
    print_str(_dev_test_name)
    print_str(" ---")
    print_newline()
    print_str("  Passed: ")
    print_int(_dev_test_pass_count)
    print_newline()
    print_str("  Failed: ")
    print_int(_dev_test_fail_count)
    print_newline()
    total: int32 = _dev_test_pass_count + _dev_test_fail_count
    print_str("  Total:  ")
    print_int(total)
    print_newline()
    if _dev_test_fail_count == 0:
        print_str("  Status: PASS")
        print_newline()
        return True
    else:
        print_str("  Status: FAIL")
        print_newline()
        return False

def _dev_record_pass():
    """Record a passing test."""
    global _dev_test_pass_count
    _dev_test_pass_count = _dev_test_pass_count + 1
    uart_putc('.')

def _dev_record_fail(msg: Ptr[char]):
    """Record a failing test with message."""
    global _dev_test_fail_count
    _dev_test_fail_count = _dev_test_fail_count + 1
    print_newline()
    print_str("  FAIL: ")
    print_str(msg)
    print_newline()

def dev_assert(cond: bool, msg: Ptr[char]):
    """Assert a condition is true."""
    if cond:
        _dev_record_pass()
    else:
        _dev_record_fail(msg)

def dev_assert_eq(a: int32, b: int32, msg: Ptr[char]):
    """Assert two integers are equal."""
    if a == b:
        _dev_record_pass()
    else:
        _dev_record_fail(msg)
        print_str("    Expected: ")
        print_int(b)
        print_str(", Got: ")
        print_int(a)
        print_newline()

def dev_assert_neq(a: int32, b: int32, msg: Ptr[char]):
    """Assert two integers are not equal."""
    if a != b:
        _dev_record_pass()
    else:
        _dev_record_fail(msg)
        print_str("    Values should differ but both are: ")
        print_int(a)
        print_newline()

def dev_assert_gt(a: int32, b: int32, msg: Ptr[char]):
    """Assert a > b."""
    if a > b:
        _dev_record_pass()
    else:
        _dev_record_fail(msg)
        print_str("    Expected ")
        print_int(a)
        print_str(" > ")
        print_int(b)
        print_newline()

def dev_assert_lt(a: int32, b: int32, msg: Ptr[char]):
    """Assert a < b."""
    if a < b:
        _dev_record_pass()
    else:
        _dev_record_fail(msg)
        print_str("    Expected ")
        print_int(a)
        print_str(" < ")
        print_int(b)
        print_newline()

def dev_assert_ptr_not_null(p: Ptr[uint8], msg: Ptr[char]):
    """Assert pointer is not null."""
    if cast[uint32](p) != 0:
        _dev_record_pass()
    else:
        _dev_record_fail(msg)
        print_str("    Pointer is NULL")
        print_newline()

def dev_assert_ptr_null(p: Ptr[uint8], msg: Ptr[char]):
    """Assert pointer is null."""
    if cast[uint32](p) == 0:
        _dev_record_pass()
    else:
        _dev_record_fail(msg)
        print_str("    Pointer should be NULL but is: 0x")
        print_hex(cast[uint32](p))
        print_newline()

def dev_get_pass_count() -> int32:
    """Get number of passed tests."""
    return _dev_test_pass_count

def dev_get_fail_count() -> int32:
    """Get number of failed tests."""
    return _dev_test_fail_count

# ============================================================================
# Memory Debugger
# ============================================================================

# Memory debug tracking state
_mem_debug_enabled: bool = False
_mem_debug_alloc_count: int32 = 0
_mem_debug_free_count: int32 = 0
_mem_debug_alloc_bytes: int32 = 0
_mem_debug_free_bytes: int32 = 0
_mem_debug_peak_bytes: int32 = 0
_mem_debug_current_bytes: int32 = 0

# Allocation tracking table (simple fixed-size table)
# Each entry: [addr: uint32, size: int32, in_use: int32]
MAX_TRACKED_ALLOCS: int32 = 64
ALLOC_ENTRY_SIZE: int32 = 12
_alloc_table: Array[768, uint8]  # 64 * 12 = 768 bytes

def mem_debug_enable():
    """Start tracking memory allocations."""
    global _mem_debug_enabled, _mem_debug_alloc_count, _mem_debug_free_count
    global _mem_debug_alloc_bytes, _mem_debug_free_bytes
    global _mem_debug_peak_bytes, _mem_debug_current_bytes
    _mem_debug_enabled = True
    _mem_debug_alloc_count = 0
    _mem_debug_free_count = 0
    _mem_debug_alloc_bytes = 0
    _mem_debug_free_bytes = 0
    _mem_debug_peak_bytes = 0
    _mem_debug_current_bytes = 0
    # Clear allocation table
    i: int32 = 0
    while i < MAX_TRACKED_ALLOCS * ALLOC_ENTRY_SIZE:
        _alloc_table[i] = 0
        i = i + 1

def mem_debug_disable():
    """Stop tracking memory allocations."""
    global _mem_debug_enabled
    _mem_debug_enabled = False

def mem_debug_is_enabled() -> bool:
    """Check if memory debugging is enabled."""
    return _mem_debug_enabled

def _mem_debug_find_slot() -> int32:
    """Find an empty slot in allocation table. Returns -1 if full."""
    table: Ptr[int32] = cast[Ptr[int32]](&_alloc_table[0])
    i: int32 = 0
    while i < MAX_TRACKED_ALLOCS:
        # Check if slot is empty (addr == 0)
        if table[i * 3] == 0:
            return i
        i = i + 1
    return -1

def _mem_debug_find_addr(addr: uint32) -> int32:
    """Find slot containing address. Returns -1 if not found."""
    table: Ptr[int32] = cast[Ptr[int32]](&_alloc_table[0])
    i: int32 = 0
    while i < MAX_TRACKED_ALLOCS:
        if table[i * 3] == cast[int32](addr) and table[i * 3 + 2] == 1:
            return i
        i = i + 1
    return -1

def mem_debug_record_alloc(ptr: Ptr[uint8], size: int32):
    """Record an allocation (called by alloc wrapper)."""
    global _mem_debug_alloc_count, _mem_debug_alloc_bytes
    global _mem_debug_current_bytes, _mem_debug_peak_bytes
    if not _mem_debug_enabled:
        return
    if cast[uint32](ptr) == 0:
        return

    _mem_debug_alloc_count = _mem_debug_alloc_count + 1
    _mem_debug_alloc_bytes = _mem_debug_alloc_bytes + size

    _mem_debug_current_bytes = _mem_debug_current_bytes + size
    if _mem_debug_current_bytes > _mem_debug_peak_bytes:
        _mem_debug_peak_bytes = _mem_debug_current_bytes

    # Record in table
    slot: int32 = _mem_debug_find_slot()
    if slot >= 0:
        table: Ptr[int32] = cast[Ptr[int32]](&_alloc_table[0])
        table[slot * 3] = cast[int32](ptr)
        table[slot * 3 + 1] = size
        table[slot * 3 + 2] = 1  # in_use

def mem_debug_record_free(ptr: Ptr[uint8]):
    """Record a free (called by free wrapper)."""
    global _mem_debug_free_count, _mem_debug_free_bytes, _mem_debug_current_bytes
    if not _mem_debug_enabled:
        return
    if cast[uint32](ptr) == 0:
        return

    # Find in table
    slot: int32 = _mem_debug_find_addr(cast[uint32](ptr))
    if slot >= 0:
        table: Ptr[int32] = cast[Ptr[int32]](&_alloc_table[0])
        size: int32 = table[slot * 3 + 1]
        _mem_debug_free_count = _mem_debug_free_count + 1
        _mem_debug_free_bytes = _mem_debug_free_bytes + size
        _mem_debug_current_bytes = _mem_debug_current_bytes - size
        # Mark slot as free
        table[slot * 3] = 0
        table[slot * 3 + 1] = 0
        table[slot * 3 + 2] = 0

def mem_debug_report():
    """Print memory allocation statistics."""
    print_str("=== Memory Debug Report ===")
    print_newline()
    print_str("  Allocations:    ")
    print_int(_mem_debug_alloc_count)
    print_newline()
    print_str("  Frees:          ")
    print_int(_mem_debug_free_count)
    print_newline()
    print_str("  Bytes allocated:")
    print_int(_mem_debug_alloc_bytes)
    print_newline()
    print_str("  Bytes freed:    ")
    print_int(_mem_debug_free_bytes)
    print_newline()
    print_str("  Current used:   ")
    print_int(_mem_debug_current_bytes)
    print_newline()
    print_str("  Peak usage:     ")
    print_int(_mem_debug_peak_bytes)
    print_newline()

def mem_debug_check_leaks() -> int32:
    """Report unfreed allocations. Returns count of leaks."""
    table: Ptr[int32] = cast[Ptr[int32]](&_alloc_table[0])
    leak_count: int32 = 0
    leak_bytes: int32 = 0

    print_str("=== Memory Leak Check ===")
    print_newline()

    i: int32 = 0
    while i < MAX_TRACKED_ALLOCS:
        if table[i * 3] != 0 and table[i * 3 + 2] == 1:
            addr: uint32 = cast[uint32](table[i * 3])
            size: int32 = table[i * 3 + 1]
            print_str("  Leak: addr=0x")
            print_hex(addr)
            print_str(" size=")
            print_int(size)
            print_newline()
            leak_count = leak_count + 1
            leak_bytes = leak_bytes + size
        i = i + 1

    if leak_count == 0:
        print_str("  No leaks detected")
        print_newline()
    else:
        print_str("  Total leaks: ")
        print_int(leak_count)
        print_str(" (")
        print_int(leak_bytes)
        print_str(" bytes)")
        print_newline()

    return leak_count

def mem_debug_heap_walk():
    """Walk the heap and print block information."""
    print_str("=== Heap Walk ===")
    print_newline()

    addr: uint32 = HEAP_START
    heap_end: uint32 = HEAP_START + HEAP_SIZE
    block_num: int32 = 0

    while addr < heap_end:
        header: Ptr[int32] = cast[Ptr[int32]](addr)
        block_size: int32 = header[0]
        in_use: int32 = header[1]

        if block_size <= 0:
            break

        print_str("  Block ")
        print_int(block_num)
        print_str(": addr=0x")
        print_hex(addr)
        print_str(" size=")
        print_int(block_size)
        if in_use == 1:
            print_str(" [USED]")
        else:
            print_str(" [FREE]")
        print_newline()

        block_num = block_num + 1
        addr = addr + cast[uint32](block_size)

    print_str("  Total blocks: ")
    print_int(block_num)
    print_newline()

# ============================================================================
# Disassembler (ARM Thumb) - Helper functions
# ============================================================================

def _disasm_print_reg(reg: int32):
    """Print register name."""
    if reg == 0:
        print_str("r0")
    elif reg == 1:
        print_str("r1")
    elif reg == 2:
        print_str("r2")
    elif reg == 3:
        print_str("r3")
    elif reg == 4:
        print_str("r4")
    elif reg == 5:
        print_str("r5")
    elif reg == 6:
        print_str("r6")
    elif reg == 7:
        print_str("r7")
    elif reg == 8:
        print_str("r8")
    elif reg == 9:
        print_str("r9")
    elif reg == 10:
        print_str("r10")
    elif reg == 11:
        print_str("r11")
    elif reg == 12:
        print_str("r12")
    elif reg == 13:
        print_str("sp")
    elif reg == 14:
        print_str("lr")
    elif reg == 15:
        print_str("pc")

def _disasm_print_reglist(mask: int32, include_lr: bool, include_pc: bool):
    """Print register list for push/pop."""
    uart_putc('{')
    first: bool = True
    i: int32 = 0
    while i < 8:
        if (mask & (1 << i)) != 0:
            if not first:
                print_str(", ")
            first = False
            _disasm_print_reg(i)
        i = i + 1
    if include_lr:
        if not first:
            print_str(", ")
        print_str("lr")
        first = False
    if include_pc:
        if not first:
            print_str(", ")
        print_str("pc")
    uart_putc('}')

def _disasm_print_cond(cond: int32):
    """Print condition code suffix."""
    if cond == 0:
        print_str("eq")
    elif cond == 1:
        print_str("ne")
    elif cond == 2:
        print_str("cs")
    elif cond == 3:
        print_str("cc")
    elif cond == 4:
        print_str("mi")
    elif cond == 5:
        print_str("pl")
    elif cond == 6:
        print_str("vs")
    elif cond == 7:
        print_str("vc")
    elif cond == 8:
        print_str("hi")
    elif cond == 9:
        print_str("ls")
    elif cond == 10:
        print_str("ge")
    elif cond == 11:
        print_str("lt")
    elif cond == 12:
        print_str("gt")
    elif cond == 13:
        print_str("le")

# ============================================================================
# Disassembler - MOV instructions
# ============================================================================

def _disasm_mov_imm(instr: uint32) -> bool:
    """MOV (immediate) - 00100xxxiiiiiiii"""
    if (instr & 0xF800) != 0x2000:
        return False
    rd: int32 = (cast[int32](instr) >> 8) & 0x7
    imm: int32 = cast[int32](instr) & 0xFF
    print_str("mov     ")
    _disasm_print_reg(rd)
    print_str(", #")
    print_int(imm)
    return True

def _disasm_mov_reg(instr: uint32) -> bool:
    """MOV (register) - 01000110xxxxxxxx"""
    if (instr & 0xFF00) != 0x4600:
        return False
    rd: int32 = (cast[int32](instr) & 0x7) | ((cast[int32](instr) >> 4) & 0x8)
    rm: int32 = (cast[int32](instr) >> 3) & 0xF
    print_str("mov     ")
    _disasm_print_reg(rd)
    print_str(", ")
    _disasm_print_reg(rm)
    return True

# ============================================================================
# Disassembler - ADD instructions
# ============================================================================

def _disasm_add_imm3(instr: uint32) -> bool:
    """ADD (immediate, 3-bit) - 0001110iiixxxxxx"""
    if (instr & 0xFE00) != 0x1C00:
        return False
    rd: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    imm: int32 = (cast[int32](instr) >> 6) & 0x7
    print_str("add     ")
    _disasm_print_reg(rd)
    print_str(", ")
    _disasm_print_reg(rn)
    print_str(", #")
    print_int(imm)
    return True

def _disasm_add_imm8(instr: uint32) -> bool:
    """ADD (immediate, 8-bit) - 00110xxxiiiiiiii"""
    if (instr & 0xF800) != 0x3000:
        return False
    rd: int32 = (cast[int32](instr) >> 8) & 0x7
    imm: int32 = cast[int32](instr) & 0xFF
    print_str("add     ")
    _disasm_print_reg(rd)
    print_str(", #")
    print_int(imm)
    return True

def _disasm_add_reg(instr: uint32) -> bool:
    """ADD (register) - 0001100xxxxxxxxx"""
    if (instr & 0xFE00) != 0x1800:
        return False
    rd: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    rm: int32 = (cast[int32](instr) >> 6) & 0x7
    print_str("add     ")
    _disasm_print_reg(rd)
    print_str(", ")
    _disasm_print_reg(rn)
    print_str(", ")
    _disasm_print_reg(rm)
    return True

def _disasm_add_sp_imm(instr: uint32) -> bool:
    """ADD (SP + immediate) - 10101xxxiiiiiiii or 101100000xxxxxxx"""
    if (instr & 0xF800) == 0xA800:
        rd: int32 = (cast[int32](instr) >> 8) & 0x7
        imm: int32 = (cast[int32](instr) & 0xFF) << 2
        print_str("add     ")
        _disasm_print_reg(rd)
        print_str(", sp, #")
        print_int(imm)
        return True
    if (instr & 0xFF80) == 0xB000:
        imm: int32 = (cast[int32](instr) & 0x7F) << 2
        print_str("add     sp, #")
        print_int(imm)
        return True
    return False

# ============================================================================
# Disassembler - SUB instructions
# ============================================================================

def _disasm_sub_imm3(instr: uint32) -> bool:
    """SUB (immediate, 3-bit) - 0001111iiixxxxxx"""
    if (instr & 0xFE00) != 0x1E00:
        return False
    rd: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    imm: int32 = (cast[int32](instr) >> 6) & 0x7
    print_str("sub     ")
    _disasm_print_reg(rd)
    print_str(", ")
    _disasm_print_reg(rn)
    print_str(", #")
    print_int(imm)
    return True

def _disasm_sub_imm8(instr: uint32) -> bool:
    """SUB (immediate, 8-bit) - 00111xxxiiiiiiii"""
    if (instr & 0xF800) != 0x3800:
        return False
    rd: int32 = (cast[int32](instr) >> 8) & 0x7
    imm: int32 = cast[int32](instr) & 0xFF
    print_str("sub     ")
    _disasm_print_reg(rd)
    print_str(", #")
    print_int(imm)
    return True

def _disasm_sub_reg(instr: uint32) -> bool:
    """SUB (register) - 0001101xxxxxxxxx"""
    if (instr & 0xFE00) != 0x1A00:
        return False
    rd: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    rm: int32 = (cast[int32](instr) >> 6) & 0x7
    print_str("sub     ")
    _disasm_print_reg(rd)
    print_str(", ")
    _disasm_print_reg(rn)
    print_str(", ")
    _disasm_print_reg(rm)
    return True

def _disasm_sub_sp(instr: uint32) -> bool:
    """SUB SP - 101100001xxxxxxx"""
    if (instr & 0xFF80) != 0xB080:
        return False
    imm: int32 = (cast[int32](instr) & 0x7F) << 2
    print_str("sub     sp, #")
    print_int(imm)
    return True

# ============================================================================
# Disassembler - LDR instructions
# ============================================================================

def _disasm_ldr_lit(instr: uint32) -> bool:
    """LDR (literal) - 01001xxxiiiiiiii"""
    if (instr & 0xF800) != 0x4800:
        return False
    rt: int32 = (cast[int32](instr) >> 8) & 0x7
    imm: int32 = (cast[int32](instr) & 0xFF) << 2
    print_str("ldr     ")
    _disasm_print_reg(rt)
    print_str(", [pc, #")
    print_int(imm)
    uart_putc(']')
    return True

def _disasm_ldr_reg(instr: uint32) -> bool:
    """LDR (register) - 0101100xxxxxxxxx"""
    if (instr & 0xFE00) != 0x5800:
        return False
    rt: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    rm: int32 = (cast[int32](instr) >> 6) & 0x7
    print_str("ldr     ")
    _disasm_print_reg(rt)
    print_str(", [")
    _disasm_print_reg(rn)
    print_str(", ")
    _disasm_print_reg(rm)
    uart_putc(']')
    return True

def _disasm_ldr_imm(instr: uint32) -> bool:
    """LDR (immediate) - 01101xxxiiiiiiii"""
    if (instr & 0xF800) != 0x6800:
        return False
    rt: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    imm: int32 = ((cast[int32](instr) >> 6) & 0x1F) << 2
    print_str("ldr     ")
    _disasm_print_reg(rt)
    print_str(", [")
    _disasm_print_reg(rn)
    print_str(", #")
    print_int(imm)
    uart_putc(']')
    return True

def _disasm_ldr_sp(instr: uint32) -> bool:
    """LDR (SP + immediate) - 10011xxxiiiiiiii"""
    if (instr & 0xF800) != 0x9800:
        return False
    rt: int32 = (cast[int32](instr) >> 8) & 0x7
    imm: int32 = (cast[int32](instr) & 0xFF) << 2
    print_str("ldr     ")
    _disasm_print_reg(rt)
    print_str(", [sp, #")
    print_int(imm)
    uart_putc(']')
    return True

def _disasm_ldrb(instr: uint32) -> bool:
    """LDRB (immediate) - 01111xxxiiiiiiii"""
    if (instr & 0xF800) != 0x7800:
        return False
    rt: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    imm: int32 = (cast[int32](instr) >> 6) & 0x1F
    print_str("ldrb    ")
    _disasm_print_reg(rt)
    print_str(", [")
    _disasm_print_reg(rn)
    print_str(", #")
    print_int(imm)
    uart_putc(']')
    return True

def _disasm_ldrh(instr: uint32) -> bool:
    """LDRH (immediate) - 10001xxxiiiiiiii"""
    if (instr & 0xF800) != 0x8800:
        return False
    rt: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    imm: int32 = ((cast[int32](instr) >> 6) & 0x1F) << 1
    print_str("ldrh    ")
    _disasm_print_reg(rt)
    print_str(", [")
    _disasm_print_reg(rn)
    print_str(", #")
    print_int(imm)
    uart_putc(']')
    return True

# ============================================================================
# Disassembler - STR instructions
# ============================================================================

def _disasm_str_reg(instr: uint32) -> bool:
    """STR (register) - 0101000xxxxxxxxx"""
    if (instr & 0xFE00) != 0x5000:
        return False
    rt: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    rm: int32 = (cast[int32](instr) >> 6) & 0x7
    print_str("str     ")
    _disasm_print_reg(rt)
    print_str(", [")
    _disasm_print_reg(rn)
    print_str(", ")
    _disasm_print_reg(rm)
    uart_putc(']')
    return True

def _disasm_str_imm(instr: uint32) -> bool:
    """STR (immediate) - 01100xxxiiiiiiii"""
    if (instr & 0xF800) != 0x6000:
        return False
    rt: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    imm: int32 = ((cast[int32](instr) >> 6) & 0x1F) << 2
    print_str("str     ")
    _disasm_print_reg(rt)
    print_str(", [")
    _disasm_print_reg(rn)
    print_str(", #")
    print_int(imm)
    uart_putc(']')
    return True

def _disasm_str_sp(instr: uint32) -> bool:
    """STR (SP + immediate) - 10010xxxiiiiiiii"""
    if (instr & 0xF800) != 0x9000:
        return False
    rt: int32 = (cast[int32](instr) >> 8) & 0x7
    imm: int32 = (cast[int32](instr) & 0xFF) << 2
    print_str("str     ")
    _disasm_print_reg(rt)
    print_str(", [sp, #")
    print_int(imm)
    uart_putc(']')
    return True

def _disasm_strb(instr: uint32) -> bool:
    """STRB (immediate) - 01110xxxiiiiiiii"""
    if (instr & 0xF800) != 0x7000:
        return False
    rt: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    imm: int32 = (cast[int32](instr) >> 6) & 0x1F
    print_str("strb    ")
    _disasm_print_reg(rt)
    print_str(", [")
    _disasm_print_reg(rn)
    print_str(", #")
    print_int(imm)
    uart_putc(']')
    return True

def _disasm_strh(instr: uint32) -> bool:
    """STRH (immediate) - 10000xxxiiiiiiii"""
    if (instr & 0xF800) != 0x8000:
        return False
    rt: int32 = cast[int32](instr) & 0x7
    rn: int32 = (cast[int32](instr) >> 3) & 0x7
    imm: int32 = ((cast[int32](instr) >> 6) & 0x1F) << 1
    print_str("strh    ")
    _disasm_print_reg(rt)
    print_str(", [")
    _disasm_print_reg(rn)
    print_str(", #")
    print_int(imm)
    uart_putc(']')
    return True

# ============================================================================
# Disassembler - Stack and branch instructions
# ============================================================================

def _disasm_push(instr: uint32) -> bool:
    """PUSH - 1011010xxxxxxxxx"""
    if (instr & 0xFE00) != 0xB400:
        return False
    reglist: int32 = cast[int32](instr) & 0xFF
    lr_bit: bool = ((cast[int32](instr) >> 8) & 1) == 1
    print_str("push    ")
    _disasm_print_reglist(reglist, lr_bit, False)
    return True

def _disasm_pop(instr: uint32) -> bool:
    """POP - 1011110xxxxxxxxx"""
    if (instr & 0xFE00) != 0xBC00:
        return False
    reglist: int32 = cast[int32](instr) & 0xFF
    pc_bit: bool = ((cast[int32](instr) >> 8) & 1) == 1
    print_str("pop     ")
    _disasm_print_reglist(reglist, False, pc_bit)
    return True

def _disasm_b_uncond(addr: uint32, instr: uint32) -> bool:
    """B (unconditional) - 11100xxxxxxxxxxx"""
    if (instr & 0xF800) != 0xE000:
        return False
    offset: int32 = cast[int32](instr) & 0x7FF
    # Sign extend 11-bit offset
    if (offset & 0x400) != 0:
        offset = offset | 0xFFFFF800
    offset = offset << 1
    target: uint32 = addr + 4 + cast[uint32](offset)
    print_str("b       0x")
    print_hex(target)
    return True

def _disasm_b_cond(addr: uint32, instr: uint32) -> bool:
    """B (conditional) - 1101ccccxxxxxxxx"""
    if (instr & 0xF000) != 0xD000:
        return False
    cond: int32 = (cast[int32](instr) >> 8) & 0xF
    if cond >= 14:
        return False
    offset: int32 = cast[int32](instr) & 0xFF
    # Sign extend 8-bit offset
    if (offset & 0x80) != 0:
        offset = offset | 0xFFFFFF00
    offset = offset << 1
    target: uint32 = addr + 4 + cast[uint32](offset)
    print_str("b")
    _disasm_print_cond(cond)
    print_str("     0x")
    print_hex(target)
    return True

def _disasm_bx_blx(instr: uint32) -> bool:
    """BX/BLX - 01000111xxxxxxxx"""
    if (instr & 0xFF80) == 0x4700:
        rm: int32 = (cast[int32](instr) >> 3) & 0xF
        print_str("bx      ")
        _disasm_print_reg(rm)
        return True
    if (instr & 0xFF80) == 0x4780:
        rm: int32 = (cast[int32](instr) >> 3) & 0xF
        print_str("blx     ")
        _disasm_print_reg(rm)
        return True
    return False

# ============================================================================
# Disassembler - Compare and other instructions
# ============================================================================

def _disasm_cmp(instr: uint32) -> bool:
    """CMP instructions"""
    # CMP (immediate) - 00101xxxiiiiiiii
    if (instr & 0xF800) == 0x2800:
        rn: int32 = (cast[int32](instr) >> 8) & 0x7
        imm: int32 = cast[int32](instr) & 0xFF
        print_str("cmp     ")
        _disasm_print_reg(rn)
        print_str(", #")
        print_int(imm)
        return True
    # CMP (register low) - 0100001010xxxxxx
    if (instr & 0xFFC0) == 0x4280:
        rn: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        print_str("cmp     ")
        _disasm_print_reg(rn)
        print_str(", ")
        _disasm_print_reg(rm)
        return True
    # CMP (register high) - 01000101xxxxxxxx
    if (instr & 0xFF00) == 0x4500:
        rn: int32 = (cast[int32](instr) & 0x7) | ((cast[int32](instr) >> 4) & 0x8)
        rm: int32 = (cast[int32](instr) >> 3) & 0xF
        print_str("cmp     ")
        _disasm_print_reg(rn)
        print_str(", ")
        _disasm_print_reg(rm)
        return True
    return False

def _disasm_shift(instr: uint32) -> bool:
    """Shift instructions - LSL, LSR, ASR"""
    # LSL (immediate) - 00000xxxxxxxxxxx
    if (instr & 0xF800) == 0x0000:
        rd: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        imm: int32 = (cast[int32](instr) >> 6) & 0x1F
        print_str("lsl     ")
        _disasm_print_reg(rd)
        print_str(", ")
        _disasm_print_reg(rm)
        print_str(", #")
        print_int(imm)
        return True
    # LSR (immediate) - 00001xxxxxxxxxxx
    if (instr & 0xF800) == 0x0800:
        rd: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        imm: int32 = (cast[int32](instr) >> 6) & 0x1F
        if imm == 0:
            imm = 32
        print_str("lsr     ")
        _disasm_print_reg(rd)
        print_str(", ")
        _disasm_print_reg(rm)
        print_str(", #")
        print_int(imm)
        return True
    # ASR (immediate) - 00010xxxxxxxxxxx
    if (instr & 0xF800) == 0x1000:
        rd: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        imm: int32 = (cast[int32](instr) >> 6) & 0x1F
        if imm == 0:
            imm = 32
        print_str("asr     ")
        _disasm_print_reg(rd)
        print_str(", ")
        _disasm_print_reg(rm)
        print_str(", #")
        print_int(imm)
        return True
    return False

def _disasm_logic(instr: uint32) -> bool:
    """Logic instructions - AND, ORR, EOR, MVN, MUL"""
    # AND (register) - 0100000000xxxxxx
    if (instr & 0xFFC0) == 0x4000:
        rd: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        print_str("and     ")
        _disasm_print_reg(rd)
        print_str(", ")
        _disasm_print_reg(rm)
        return True
    # ORR (register) - 0100001100xxxxxx
    if (instr & 0xFFC0) == 0x4300:
        rd: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        print_str("orr     ")
        _disasm_print_reg(rd)
        print_str(", ")
        _disasm_print_reg(rm)
        return True
    # EOR (register) - 0100000001xxxxxx
    if (instr & 0xFFC0) == 0x4040:
        rd: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        print_str("eor     ")
        _disasm_print_reg(rd)
        print_str(", ")
        _disasm_print_reg(rm)
        return True
    # MVN (register) - 0100001111xxxxxx
    if (instr & 0xFFC0) == 0x43C0:
        rd: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        print_str("mvn     ")
        _disasm_print_reg(rd)
        print_str(", ")
        _disasm_print_reg(rm)
        return True
    # MUL - 0100001101xxxxxx
    if (instr & 0xFFC0) == 0x4340:
        rd: int32 = cast[int32](instr) & 0x7
        rm: int32 = (cast[int32](instr) >> 3) & 0x7
        print_str("mul     ")
        _disasm_print_reg(rd)
        print_str(", ")
        _disasm_print_reg(rm)
        return True
    return False

def _disasm_nop(instr: uint32) -> bool:
    """NOP - 10111111 00000000"""
    if instr == 0xBF00:
        print_str("nop")
        return True
    return False

# ============================================================================
# Disassembler - Main dispatch functions
# ============================================================================

def _disasm_thumb16(addr: uint32, instr: uint32) -> bool:
    """Disassemble a 16-bit Thumb instruction."""
    # Try each instruction category
    if _disasm_mov_imm(instr):
        return True
    if _disasm_mov_reg(instr):
        return True
    if _disasm_add_imm3(instr):
        return True
    if _disasm_add_imm8(instr):
        return True
    if _disasm_add_reg(instr):
        return True
    if _disasm_add_sp_imm(instr):
        return True
    if _disasm_sub_imm3(instr):
        return True
    if _disasm_sub_imm8(instr):
        return True
    if _disasm_sub_reg(instr):
        return True
    if _disasm_sub_sp(instr):
        return True
    if _disasm_ldr_lit(instr):
        return True
    if _disasm_ldr_reg(instr):
        return True
    if _disasm_ldr_imm(instr):
        return True
    if _disasm_ldr_sp(instr):
        return True
    if _disasm_ldrb(instr):
        return True
    if _disasm_ldrh(instr):
        return True
    if _disasm_str_reg(instr):
        return True
    if _disasm_str_imm(instr):
        return True
    if _disasm_str_sp(instr):
        return True
    if _disasm_strb(instr):
        return True
    if _disasm_strh(instr):
        return True
    if _disasm_push(instr):
        return True
    if _disasm_pop(instr):
        return True
    if _disasm_b_uncond(addr, instr):
        return True
    if _disasm_b_cond(addr, instr):
        return True
    if _disasm_bx_blx(instr):
        return True
    if _disasm_cmp(instr):
        return True
    if _disasm_shift(instr):
        return True
    if _disasm_logic(instr):
        return True
    if _disasm_nop(instr):
        return True
    return False

def _disasm_thumb32(addr: uint32, instr_hi: uint32, instr_lo: uint32) -> bool:
    """Disassemble a 32-bit Thumb instruction."""
    # BL - 11110xxxxxxxxxxx 11x1xxxxxxxxxxxx
    if (instr_hi & 0xF800) == 0xF000 and (instr_lo & 0xD000) == 0xD000:
        s: int32 = (cast[int32](instr_hi) >> 10) & 1
        imm10: int32 = cast[int32](instr_hi) & 0x3FF
        j1: int32 = (cast[int32](instr_lo) >> 13) & 1
        j2: int32 = (cast[int32](instr_lo) >> 11) & 1
        imm11: int32 = cast[int32](instr_lo) & 0x7FF

        i1: int32 = 1 - (j1 ^ s)
        i2: int32 = 1 - (j2 ^ s)

        offset: int32 = (s << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
        if s == 1:
            offset = offset | 0xFE000000

        target: uint32 = addr + 4 + cast[uint32](offset)
        print_str("bl      0x")
        print_hex(target)
        return True

    # B.W (unconditional wide) - 11110xxxxxxxxxxx 10x1xxxxxxxxxxxx
    if (instr_hi & 0xF800) == 0xF000 and (instr_lo & 0xD000) == 0x9000:
        s: int32 = (cast[int32](instr_hi) >> 10) & 1
        imm10: int32 = cast[int32](instr_hi) & 0x3FF
        j1: int32 = (cast[int32](instr_lo) >> 13) & 1
        j2: int32 = (cast[int32](instr_lo) >> 11) & 1
        imm11: int32 = cast[int32](instr_lo) & 0x7FF

        i1: int32 = 1 - (j1 ^ s)
        i2: int32 = 1 - (j2 ^ s)

        offset: int32 = (s << 24) | (i1 << 23) | (i2 << 22) | (imm10 << 12) | (imm11 << 1)
        if s == 1:
            offset = offset | 0xFE000000

        target: uint32 = addr + 4 + cast[uint32](offset)
        print_str("b.w     0x")
        print_hex(target)
        return True

    return False

# ============================================================================
# Disassembler - Public API
# ============================================================================

def disasm(addr: uint32, count: int32):
    """Disassemble 'count' instructions starting at address."""
    print_str("Disassembly at 0x")
    print_hex(addr)
    print_str(":")
    print_newline()

    i: int32 = 0
    while i < count:
        # Read 16-bit instruction
        ptr16: Ptr[uint16] = cast[Ptr[uint16]](addr)
        instr: uint32 = cast[uint32](ptr16[0])

        # Print address
        print_str("  0x")
        print_hex(addr)
        print_str(":  ")

        # Check if 32-bit instruction
        prefix: uint32 = (instr >> 11) & 0x1F
        if prefix == 0x1D or prefix == 0x1E or prefix == 0x1F:
            # 32-bit instruction
            instr_hi: uint32 = instr
            instr_lo: uint32 = cast[uint32](ptr16[1])

            print_hex(instr_hi)
            print_str(" ")
            print_hex(instr_lo)
            print_str("  ")

            if not _disasm_thumb32(addr, instr_hi, instr_lo):
                print_str(".word   0x")
                print_hex((instr_hi << 16) | instr_lo)

            addr = addr + 4
        else:
            # 16-bit instruction
            print_hex(instr)
            print_str("       ")

            if not _disasm_thumb16(addr, instr):
                print_str(".short  0x")
                print_hex(instr)

            addr = addr + 2

        print_newline()
        i = i + 1

def disasm_at(addr: uint32):
    """Disassemble a single instruction at address."""
    disasm(addr, 1)
