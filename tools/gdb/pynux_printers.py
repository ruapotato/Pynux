"""
Pynux OS GDB Pretty Printers

Pretty print Pynux kernel structures for easier debugging.
Automatically registered when loaded via pynux.gdb.

Usage:
    (gdb) python import pynux_printers
    (gdb) python pynux_printers.register_printers(None)
"""

import gdb
import gdb.printing
import re


class PynuxProcessPrinter:
    """Pretty printer for Process structures."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            pid = int(self.val['pid'])
            name = self.val['name'].string()
            state = int(self.val['state'])
            priority = int(self.val['priority'])

            state_names = {
                0: 'READY',
                1: 'RUNNING',
                2: 'BLOCKED',
                3: 'SLEEPING',
                4: 'ZOMBIE',
                5: 'TERMINATED'
            }
            state_str = state_names.get(state, f'UNKNOWN({state})')

            return f'Process(pid={pid}, name="{name}", state={state_str}, priority={priority})'
        except Exception as e:
            return f'Process(<error: {e}>)'

    def children(self):
        """Return child elements for detailed display."""
        try:
            yield ('pid', self.val['pid'])
            yield ('name', self.val['name'])
            yield ('state', self.val['state'])
            yield ('priority', self.val['priority'])
            if 'stack_ptr' in [f.name for f in self.val.type.fields()]:
                yield ('stack_ptr', self.val['stack_ptr'])
            if 'stack_size' in [f.name for f in self.val.type.fields()]:
                yield ('stack_size', self.val['stack_size'])
        except:
            pass


class PynuxTimerPrinter:
    """Pretty printer for Timer structures."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            timer_id = int(self.val['id'])
            expires = int(self.val['expires'])
            period = int(self.val['period'])
            active = bool(self.val['active'])

            status = 'active' if active else 'inactive'
            if period > 0:
                return f'Timer(id={timer_id}, expires={expires}, period={period}, {status}, periodic)'
            else:
                return f'Timer(id={timer_id}, expires={expires}, {status}, one-shot)'
        except Exception as e:
            return f'Timer(<error: {e}>)'


class PynuxHeapBlockPrinter:
    """Pretty printer for heap block structures."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            size = int(self.val['size'])
            free = bool(self.val['free'])

            status = 'free' if free else 'allocated'
            return f'HeapBlock(size={size}, {status})'
        except Exception as e:
            return f'HeapBlock(<error: {e}>)'


class PynuxMutexPrinter:
    """Pretty printer for Mutex structures."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            locked = bool(self.val['locked'])
            owner = int(self.val['owner']) if self.val['owner'] else 0

            if locked:
                return f'Mutex(locked, owner={owner})'
            else:
                return f'Mutex(unlocked)'
        except Exception as e:
            return f'Mutex(<error: {e}>)'


class PynuxSemaphorePrinter:
    """Pretty printer for Semaphore structures."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            count = int(self.val['count'])
            max_count = int(self.val['max_count'])
            return f'Semaphore(count={count}/{max_count})'
        except Exception as e:
            return f'Semaphore(<error: {e}>)'


class PynuxQueuePrinter:
    """Pretty printer for Queue structures."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            head = int(self.val['head'])
            tail = int(self.val['tail'])
            capacity = int(self.val['capacity'])
            count = int(self.val['count'])
            return f'Queue(count={count}/{capacity}, head={head}, tail={tail})'
        except Exception as e:
            return f'Queue(<error: {e}>)'


class PynuxRegistersPrinter:
    """Pretty printer for saved register context."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            pc = int(self.val['pc'])
            lr = int(self.val['lr'])
            sp = int(self.val['sp'])
            return f'Registers(PC=0x{pc:08x}, LR=0x{lr:08x}, SP=0x{sp:08x})'
        except Exception as e:
            return f'Registers(<error: {e}>)'

    def children(self):
        """Return all registers for detailed display."""
        try:
            for i in range(13):
                reg_name = f'r{i}'
                if reg_name in [f.name for f in self.val.type.fields()]:
                    yield (reg_name, self.val[reg_name])
            yield ('sp', self.val['sp'])
            yield ('lr', self.val['lr'])
            yield ('pc', self.val['pc'])
            if 'xpsr' in [f.name for f in self.val.type.fields()]:
                yield ('xpsr', self.val['xpsr'])
        except:
            pass


class PynuxListNodePrinter:
    """Pretty printer for linked list nodes."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            next_ptr = self.val['next']
            prev_ptr = self.val['prev'] if 'prev' in [f.name for f in self.val.type.fields()] else None

            if prev_ptr:
                return f'ListNode(next=0x{int(next_ptr):08x}, prev=0x{int(prev_ptr):08x})'
            else:
                return f'ListNode(next=0x{int(next_ptr):08x})'
        except Exception as e:
            return f'ListNode(<error: {e}>)'


class PynuxArrayPrinter:
    """Generic array printer with better formatting."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        return None  # Use children() for display

    def children(self):
        try:
            array_type = self.val.type
            if array_type.code == gdb.TYPE_CODE_ARRAY:
                length = array_type.range()[1] - array_type.range()[0] + 1
                for i in range(min(length, 32)):  # Limit to 32 elements
                    yield (f'[{i}]', self.val[i])
                if length > 32:
                    yield ('...', f'({length - 32} more elements)')
        except:
            pass

    def display_hint(self):
        return 'array'


class PynuxPointerPrinter:
    """Better pointer printer with dereferencing hints."""

    def __init__(self, val):
        self.val = val

    def to_string(self):
        try:
            addr = int(self.val)
            if addr == 0:
                return 'NULL'

            # Try to provide context based on address
            if 0x08000000 <= addr < 0x08100000:
                return f'0x{addr:08x} (Flash)'
            elif 0x20000000 <= addr < 0x20020000:
                return f'0x{addr:08x} (SRAM)'
            elif 0x40000000 <= addr < 0x50000000:
                return f'0x{addr:08x} (Peripheral)'
            elif 0xE0000000 <= addr < 0xFFFFFFFF:
                return f'0x{addr:08x} (System)'
            else:
                return f'0x{addr:08x}'
        except:
            return str(self.val)


def build_pynux_printer():
    """Build and return the pretty printer collection."""
    pp = gdb.printing.RegexpCollectionPrettyPrinter("pynux")

    # Process and task structures
    pp.add_printer('Process', r'^(struct )?Process$', PynuxProcessPrinter)
    pp.add_printer('Task', r'^(struct )?Task$', PynuxProcessPrinter)
    pp.add_printer('TCB', r'^(struct )?TCB$', PynuxProcessPrinter)
    pp.add_printer('thread_t', r'^(struct )?thread_t$', PynuxProcessPrinter)

    # Timer structures
    pp.add_printer('Timer', r'^(struct )?Timer$', PynuxTimerPrinter)
    pp.add_printer('timer_t', r'^(struct )?timer_t$', PynuxTimerPrinter)

    # Heap structures
    pp.add_printer('HeapBlock', r'^(struct )?HeapBlock$', PynuxHeapBlockPrinter)
    pp.add_printer('heap_block_t', r'^(struct )?heap_block_t$', PynuxHeapBlockPrinter)

    # Synchronization primitives
    pp.add_printer('Mutex', r'^(struct )?Mutex$', PynuxMutexPrinter)
    pp.add_printer('mutex_t', r'^(struct )?mutex_t$', PynuxMutexPrinter)
    pp.add_printer('Semaphore', r'^(struct )?Semaphore$', PynuxSemaphorePrinter)
    pp.add_printer('sem_t', r'^(struct )?sem_t$', PynuxSemaphorePrinter)
    pp.add_printer('Queue', r'^(struct )?Queue$', PynuxQueuePrinter)
    pp.add_printer('queue_t', r'^(struct )?queue_t$', PynuxQueuePrinter)

    # Register context
    pp.add_printer('Registers', r'^(struct )?Registers$', PynuxRegistersPrinter)
    pp.add_printer('context_t', r'^(struct )?context_t$', PynuxRegistersPrinter)

    # List nodes
    pp.add_printer('ListNode', r'^(struct )?ListNode$', PynuxListNodePrinter)
    pp.add_printer('list_node_t', r'^(struct )?list_node_t$', PynuxListNodePrinter)

    return pp


def register_printers(objfile):
    """
    Register Pynux pretty printers with GDB.

    Args:
        objfile: The object file to register with, or None for global
    """
    printers = build_pynux_printer()

    if objfile is None:
        objfile = gdb

    # Check if already registered
    for printer in objfile.pretty_printers:
        if hasattr(printer, 'name') and printer.name == 'pynux':
            return  # Already registered

    gdb.printing.register_pretty_printer(objfile, printers)


# Helper functions for manual inspection

def get_process_list():
    """Get list of all processes (helper function)."""
    try:
        # Try common process list variable names
        for name in ['process_list', 'processes', 'task_list', 'ready_queue']:
            try:
                val = gdb.parse_and_eval(name)
                return val
            except:
                continue
    except:
        pass
    return None


def get_current_process():
    """Get the currently running process."""
    try:
        for name in ['current_process', 'current_task', 'running']:
            try:
                val = gdb.parse_and_eval(name)
                return val
            except:
                continue
    except:
        pass
    return None


# Auto-register when module is loaded
try:
    register_printers(None)
except:
    pass  # Silently fail if GDB environment not ready
