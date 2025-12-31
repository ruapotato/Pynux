"""
Pynux OS GDB Custom Commands

Custom GDB commands for inspecting Pynux kernel state.
Automatically registered when loaded via pynux.gdb.

Usage:
    (gdb) python import pynux_commands
    (gdb) pynux-processes
    (gdb) pynux-timers
    (gdb) pynux-heap
"""

import gdb
import struct


class PynuxProcessesCommand(gdb.Command):
    """List all Pynux processes."""

    def __init__(self):
        super().__init__("pynux-processes", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== Pynux Processes ===\n")

        state_names = {
            0: 'READY',
            1: 'RUNNING',
            2: 'BLOCKED',
            3: 'SLEEPING',
            4: 'ZOMBIE',
            5: 'TERMINATED'
        }

        # Try different common variable names
        process_vars = ['process_list', 'processes', 'task_list', 'all_processes']
        count_vars = ['process_count', 'num_processes', 'task_count']

        found = False

        # Try to find process array
        for pvar in process_vars:
            try:
                processes = gdb.parse_and_eval(pvar)

                # Find count
                count = 16  # Default
                for cvar in count_vars:
                    try:
                        count = int(gdb.parse_and_eval(cvar))
                        break
                    except:
                        continue

                print(f"{'PID':<6} {'STATE':<12} {'PRIORITY':<10} {'STACK':<12} {'NAME'}")
                print("-" * 60)

                for i in range(count):
                    try:
                        proc = processes[i]
                        if int(proc['pid']) == 0 and i > 0:
                            continue  # Skip empty slots

                        pid = int(proc['pid'])
                        state = int(proc['state'])
                        state_str = state_names.get(state, f'?{state}')
                        priority = int(proc['priority']) if 'priority' in str(proc.type) else 0
                        stack = int(proc['stack_ptr']) if 'stack_ptr' in str(proc.type) else 0
                        name = proc['name'].string() if 'name' in str(proc.type) else f'task{pid}'

                        print(f"{pid:<6} {state_str:<12} {priority:<10} 0x{stack:08x}   {name}")
                        found = True
                    except:
                        break

                if found:
                    break
            except:
                continue

        if not found:
            print("No process list found.")
            print("Expected variables: process_list, processes, task_list")
            print("\nTrying to show current process...")

            for name in ['current_process', 'current_task', 'running']:
                try:
                    current = gdb.parse_and_eval(name)
                    print(f"\nCurrent: {current}")
                    found = True
                    break
                except:
                    continue

        print()


class PynuxTimersCommand(gdb.Command):
    """Show active Pynux timers."""

    def __init__(self):
        super().__init__("pynux-timers", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== Pynux Timers ===\n")

        timer_vars = ['timer_list', 'timers', 'active_timers', 'software_timers']
        count_vars = ['timer_count', 'num_timers', 'active_timer_count']

        found = False

        # Try to get current tick
        tick = 0
        for tvar in ['system_ticks', 'tick_count', 'jiffies', 'os_ticks']:
            try:
                tick = int(gdb.parse_and_eval(tvar))
                print(f"Current tick: {tick}\n")
                break
            except:
                continue

        for tvar in timer_vars:
            try:
                timers = gdb.parse_and_eval(tvar)

                count = 16
                for cvar in count_vars:
                    try:
                        count = int(gdb.parse_and_eval(cvar))
                        break
                    except:
                        continue

                print(f"{'ID':<6} {'EXPIRES':<12} {'PERIOD':<12} {'STATUS':<10} {'CALLBACK'}")
                print("-" * 60)

                for i in range(count):
                    try:
                        timer = timers[i]

                        timer_id = int(timer['id'])
                        if timer_id == 0 and i > 0:
                            continue

                        expires = int(timer['expires'])
                        period = int(timer['period']) if 'period' in str(timer.type) else 0
                        active = bool(timer['active']) if 'active' in str(timer.type) else True
                        callback = int(timer['callback']) if 'callback' in str(timer.type) else 0

                        status = 'active' if active else 'inactive'
                        if period > 0:
                            status += '/periodic'

                        remaining = expires - tick if tick > 0 else expires

                        print(f"{timer_id:<6} {expires:<12} {period:<12} {status:<10} 0x{callback:08x}")
                        found = True
                    except:
                        break

                if found:
                    break
            except:
                continue

        if not found:
            print("No timer list found.")
            print("Expected variables: timer_list, timers, active_timers")

        print()


class PynuxHeapCommand(gdb.Command):
    """Show Pynux heap status."""

    def __init__(self):
        super().__init__("pynux-heap", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== Pynux Heap Status ===\n")

        # Try to find heap info
        heap_start = None
        heap_end = None

        for name in ['_heap_start', 'heap_start', '__heap_start']:
            try:
                heap_start = int(gdb.parse_and_eval(f'&{name}'))
                break
            except:
                try:
                    heap_start = int(gdb.parse_and_eval(name))
                    break
                except:
                    continue

        for name in ['_heap_end', 'heap_end', '__heap_end']:
            try:
                heap_end = int(gdb.parse_and_eval(f'&{name}'))
                break
            except:
                try:
                    heap_end = int(gdb.parse_and_eval(name))
                    break
                except:
                    continue

        if heap_start and heap_end:
            print(f"Heap start: 0x{heap_start:08x}")
            print(f"Heap end:   0x{heap_end:08x}")
            print(f"Heap size:  {heap_end - heap_start} bytes ({(heap_end - heap_start) // 1024} KB)\n")

        # Try to find heap statistics
        stats_found = False
        for prefix in ['heap_', 'mem_', '']:
            try:
                total = int(gdb.parse_and_eval(f'{prefix}total_size'))
                used = int(gdb.parse_and_eval(f'{prefix}used_size'))
                free = int(gdb.parse_and_eval(f'{prefix}free_size'))

                print(f"Total: {total} bytes")
                print(f"Used:  {used} bytes ({100 * used // total}%)")
                print(f"Free:  {free} bytes ({100 * free // total}%)")
                stats_found = True
                break
            except:
                continue

        # Try to walk heap blocks
        block_vars = ['heap_blocks', 'free_list', 'heap_head']
        for bvar in block_vars:
            try:
                block = gdb.parse_and_eval(bvar)

                print("\nHeap Blocks:")
                print(f"{'ADDRESS':<12} {'SIZE':<10} {'STATUS'}")
                print("-" * 40)

                count = 0
                while int(block) != 0 and count < 100:
                    addr = int(block)
                    size = int(block['size'])
                    free = bool(block['free'])
                    status = 'free' if free else 'used'

                    print(f"0x{addr:08x}   {size:<10} {status}")

                    if 'next' in str(block.type):
                        block = block['next']
                    else:
                        break
                    count += 1

                stats_found = True
                break
            except:
                continue

        if not stats_found:
            print("No detailed heap info found.")
            print("Expected variables: heap_start/end, heap_blocks, free_list")

        print()


class PynuxTasksCommand(gdb.Command):
    """Show scheduler state."""

    def __init__(self):
        super().__init__("pynux-tasks", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== Pynux Scheduler State ===\n")

        # Current task
        for name in ['current_task', 'current_process', 'running_task']:
            try:
                current = gdb.parse_and_eval(name)
                print(f"Current task: {current}")
                break
            except:
                continue

        # Scheduler state
        for name in ['scheduler_running', 'scheduler_enabled', 'os_running']:
            try:
                state = bool(gdb.parse_and_eval(name))
                print(f"Scheduler: {'running' if state else 'stopped'}")
                break
            except:
                continue

        # Ready queue
        print("\nReady Queue:")
        for name in ['ready_queue', 'ready_list', 'runnable']:
            try:
                queue = gdb.parse_and_eval(name)
                print(f"  {name}: {queue}")
                break
            except:
                continue

        # Blocked tasks
        print("\nBlocked Tasks:")
        for name in ['blocked_list', 'wait_queue', 'sleeping']:
            try:
                blocked = gdb.parse_and_eval(name)
                print(f"  {name}: {blocked}")
                break
            except:
                continue

        # Context switches
        for name in ['context_switches', 'switch_count', 'num_switches']:
            try:
                switches = int(gdb.parse_and_eval(name))
                print(f"\nContext switches: {switches}")
                break
            except:
                continue

        print()


class PynuxTraceCommand(gdb.Command):
    """Show trace buffer contents."""

    def __init__(self):
        super().__init__("pynux-trace", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== Pynux Trace Buffer ===\n")

        trace_vars = ['trace_buffer', 'trace_log', 'debug_trace']
        index_vars = ['trace_index', 'trace_head', 'trace_pos']
        size_vars = ['trace_size', 'trace_buffer_size', 'TRACE_SIZE']

        found = False

        for tvar in trace_vars:
            try:
                trace = gdb.parse_and_eval(tvar)

                # Find index
                index = 0
                for ivar in index_vars:
                    try:
                        index = int(gdb.parse_and_eval(ivar))
                        break
                    except:
                        continue

                # Find size
                size = 64  # Default
                for svar in size_vars:
                    try:
                        size = int(gdb.parse_and_eval(svar))
                        break
                    except:
                        continue

                print(f"Trace buffer at: 0x{int(trace.address):08x}")
                print(f"Current index: {index}")
                print(f"Buffer size: {size}\n")

                print("Recent entries (newest first):")
                print("-" * 60)

                for i in range(min(size, 20)):
                    entry_idx = (index - 1 - i) % size
                    try:
                        entry = trace[entry_idx]

                        # Try to interpret as trace entry struct
                        if 'timestamp' in str(entry.type):
                            ts = int(entry['timestamp'])
                            event = int(entry['event'])
                            data = int(entry['data']) if 'data' in str(entry.type) else 0
                            print(f"[{ts:10}] Event {event:3}: 0x{data:08x}")
                        else:
                            # Simple integer/char array
                            print(f"[{entry_idx:3}] {entry}")

                        found = True
                    except:
                        break

                if found:
                    break
            except:
                continue

        if not found:
            # Check if tracing is enabled
            for name in ['trace_enabled', 'TRACE_ENABLED', 'debug_enabled']:
                try:
                    enabled = bool(gdb.parse_and_eval(name))
                    if not enabled:
                        print("Tracing is disabled.")
                        return
                except:
                    continue

            print("No trace buffer found.")
            print("Expected variables: trace_buffer, trace_log, debug_trace")

        print()


class PynuxMemoryCommand(gdb.Command):
    """Show memory usage summary."""

    def __init__(self):
        super().__init__("pynux-memory", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== Pynux Memory Summary ===\n")

        # Try to find linker symbols
        sections = [
            ('_text_start', '_text_end', 'Code (.text)'),
            ('_data_start', '_data_end', 'Data (.data)'),
            ('_bss_start', '_bss_end', 'BSS (.bss)'),
            ('_stack_start', '_stack_end', 'Stack'),
            ('_heap_start', '_heap_end', 'Heap'),
        ]

        print(f"{'Section':<20} {'Start':<12} {'End':<12} {'Size'}")
        print("-" * 60)

        total = 0
        for start_sym, end_sym, name in sections:
            try:
                start = int(gdb.parse_and_eval(f'&{start_sym}'))
                end = int(gdb.parse_and_eval(f'&{end_sym}'))
                size = end - start
                total += size
                print(f"{name:<20} 0x{start:08x}   0x{end:08x}   {size} bytes")
            except:
                try:
                    start = int(gdb.parse_and_eval(start_sym))
                    end = int(gdb.parse_and_eval(end_sym))
                    size = end - start
                    total += size
                    print(f"{name:<20} 0x{start:08x}   0x{end:08x}   {size} bytes")
                except:
                    pass

        if total > 0:
            print("-" * 60)
            print(f"{'Total':<20} {'':<12} {'':<12} {total} bytes ({total // 1024} KB)")

        print()


class PynuxInterruptsCommand(gdb.Command):
    """Show interrupt statistics."""

    def __init__(self):
        super().__init__("pynux-interrupts", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== Pynux Interrupt Statistics ===\n")

        # Try to find interrupt counters
        for name in ['irq_count', 'interrupt_count', 'isr_count']:
            try:
                counts = gdb.parse_and_eval(name)

                print(f"{'IRQ':<6} {'COUNT':<12} {'HANDLER'}")
                print("-" * 40)

                for i in range(32):
                    try:
                        count = int(counts[i])
                        if count > 0:
                            print(f"{i:<6} {count:<12}")
                    except:
                        break

                return
            except:
                continue

        # Try to show current interrupt state
        print("No interrupt statistics found.")
        print("\nCurrent interrupt state:")

        try:
            primask = gdb.parse_and_eval('$primask')
            print(f"  PRIMASK: {primask}")
        except:
            pass

        try:
            basepri = gdb.parse_and_eval('$basepri')
            print(f"  BASEPRI: {basepri}")
        except:
            pass

        print()


class PynuxDevicesCommand(gdb.Command):
    """List registered devices."""

    def __init__(self):
        super().__init__("pynux-devices", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== Pynux Devices ===\n")

        device_vars = ['device_list', 'devices', 'registered_devices']

        for dvar in device_vars:
            try:
                devices = gdb.parse_and_eval(dvar)

                print(f"{'NAME':<16} {'BASE':<12} {'IRQ':<6} {'STATUS'}")
                print("-" * 50)

                for i in range(32):
                    try:
                        dev = devices[i]

                        name = dev['name'].string() if 'name' in str(dev.type) else f'dev{i}'
                        base = int(dev['base']) if 'base' in str(dev.type) else 0
                        irq = int(dev['irq']) if 'irq' in str(dev.type) else -1
                        enabled = bool(dev['enabled']) if 'enabled' in str(dev.type) else True

                        status = 'enabled' if enabled else 'disabled'

                        if name and name != '':
                            print(f"{name:<16} 0x{base:08x}   {irq:<6} {status}")
                    except:
                        break

                return
            except:
                continue

        print("No device list found.")
        print("Expected variables: device_list, devices")
        print()


class PynuxBacktraceAllCommand(gdb.Command):
    """Show backtrace for all threads/processes."""

    def __init__(self):
        super().__init__("pynux-bt-all", gdb.COMMAND_USER)

    def invoke(self, arg, from_tty):
        print("=== All Process Backtraces ===\n")

        # First show current thread
        print("Current thread:")
        print("-" * 40)
        gdb.execute("backtrace")
        print()

        # Try to iterate through all threads if supported
        try:
            for thread in gdb.selected_inferior().threads():
                if thread.is_valid():
                    print(f"\nThread {thread.num}: {thread.name or 'unnamed'}")
                    print("-" * 40)
                    thread.switch()
                    gdb.execute("backtrace 10")
        except:
            print("Multi-thread backtrace not available.")


# Register all commands
def register_commands():
    """Register all Pynux GDB commands."""
    PynuxProcessesCommand()
    PynuxTimersCommand()
    PynuxHeapCommand()
    PynuxTasksCommand()
    PynuxTraceCommand()
    PynuxMemoryCommand()
    PynuxInterruptsCommand()
    PynuxDevicesCommand()
    PynuxBacktraceAllCommand()


# Auto-register when module is imported
try:
    register_commands()
except Exception as e:
    print(f"Warning: Could not register Pynux commands: {e}")
