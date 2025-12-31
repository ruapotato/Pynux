# Pynux GDB Debugging Tools

This directory contains GDB scripts and Python extensions for debugging Pynux OS.

## Quick Start

```bash
# Start GDB and load Pynux scripts
arm-none-eabi-gdb kernel.elf

# In GDB, source the main script
(gdb) source tools/gdb/pynux.gdb

# Connect to your target
(gdb) pynux-connect-qemu        # For QEMU
(gdb) pynux-connect-openocd     # For hardware via OpenOCD
```

## Files

| File | Description |
|------|-------------|
| `pynux.gdb` | Main GDB script - loads all others |
| `registers.gdb` | ARM register inspection commands |
| `memory.gdb` | Memory inspection and peripheral debugging |
| `breakpoints.gdb` | Predefined breakpoint helpers |
| `pynux_printers.py` | Python pretty printers for Pynux structures |
| `pynux_commands.py` | Python GDB commands for Pynux inspection |

## Connection Commands

### pynux-connect-qemu

Connect to QEMU's built-in GDB server.

```gdb
(gdb) pynux-connect-qemu              # Connect to localhost:1234
(gdb) pynux-connect-qemu 192.168.1.10:1234  # Connect to remote host
```

### pynux-connect-openocd

Connect to OpenOCD for hardware debugging.

```gdb
(gdb) pynux-connect-openocd           # Connect to localhost:3333
(gdb) pynux-connect-openocd 192.168.1.10:3333  # Connect to remote host
```

### pynux-reset

Reset the target processor (requires OpenOCD).

```gdb
(gdb) pynux-reset
```

## Register Commands

### arm-regs

Display all ARM core registers in a formatted view.

```gdb
(gdb) arm-regs
=== ARM Core Registers ===
R0:  0x00000000    R1:  0x20001000    R2:  0x00000001    R3:  0x08001234
R4:  0x00000000    R5:  0x00000000    R6:  0x00000000    R7:  0x20003FF0
...
```

### arm-cpsr

Decode the CPSR/xPSR program status register.

```gdb
(gdb) arm-cpsr
=== Program Status Register ===
xPSR: 0x01000000
Flags:
  N (Negative): 0 - Result was positive or zero
  Z (Zero):     0 - Result was non-zero
  C (Carry):    0 - No carry/borrow
  V (Overflow): 0 - No overflow
  T (Thumb):    1 - Thumb state
Exception number: 0 (Thread mode)
```

### arm-stack

Display stack contents with annotations.

```gdb
(gdb) arm-stack          # Show 16 words
(gdb) arm-stack 32       # Show 32 words

=== Stack Contents ===
SP: 0x20003FF0

SP+00 [0x20003FF0]: 0x08001234 (Flash address)
SP+04 [0x20003FF4]: 0xFFFFFFF9 (EXC_RETURN: Thread, MSP)
SP+08 [0x20003FF8]: 0x20001000 (SRAM address)
...
```

### arm-stack-frame

Display the Cortex-M exception stack frame.

```gdb
(gdb) arm-stack-frame
=== Exception Stack Frame ===
R0:     0x00000000 (SP+0x00)
R1:     0x20001000 (SP+0x04)
...
PC:     0x08001234 (SP+0x18)
xPSR:   0x01000000 (SP+0x1C)
```

### arm-fault

Decode fault status registers (CFSR, HFSR, DFSR).

```gdb
(gdb) arm-fault
=== Fault Status Registers ===

CFSR:  0x00020000
  Usage Fault (UFSR = 0x0002):
    INVSTATE: Invalid state (Thumb bit)

HFSR:  0x40000000
  FORCED: Forced HardFault (escalated from configurable fault)

DFSR:  0x00000000
```

### arm-nvic

Display NVIC interrupt controller status.

```gdb
(gdb) arm-nvic
=== NVIC Status ===

Enabled Interrupts (ISER):
  ISER[0]: 0x00000040 (IRQs 0-31)
    IRQ 6 enabled

Pending Interrupts (ISPR):
  No interrupts pending

Active Interrupts (IABR):
  No interrupts active
```

### arm-systick

Display SysTick timer status.

```gdb
(gdb) arm-systick
=== SysTick Status ===

CSR (Control): 0x00000007
  ENABLE:    1
  TICKINT:   1 (interrupt enabled)
  CLKSOURCE: 1 (processor clock)
  COUNTFLAG: 0

RVR (Reload):  0x0000F9FF (63999)
CVR (Current): 0x0000A123 (41251)
Progress:      35%
```

## Memory Commands

### mem-dump

Hex dump memory.

```gdb
(gdb) mem-dump 0x20000000 64
20000000: 00 00 00 00 01 00 00 00  02 00 00 00 03 00 00 00 |................|
20000010: 48 65 6c 6c 6f 20 57 6f  72 6c 64 21 00 00 00 00 |Hello World!....|
...
```

### mem-regions

Display standard Cortex-M memory map.

```gdb
(gdb) mem-regions
=== Memory Regions (Typical Cortex-M) ===

Region          Start        End          Size         Description
--------------- ------------ ------------ ------------ -----------
Code            0x00000000   0x1FFFFFFF   512 MB       Flash, ROM
SRAM            0x20000000   0x3FFFFFFF   512 MB       On-chip SRAM
...
```

### periph-dump

Dump peripheral registers.

```gdb
(gdb) periph-dump 0x40021000 8     # Dump RCC registers
(gdb) periph-rcc                    # Shortcut for RCC
(gdb) periph-gpio 0                 # GPIO Port A
(gdb) periph-usart 1                # USART1
```

### mem-find

Search memory for a pattern.

```gdb
(gdb) mem-find 0x20000000 0x20010000 0xDEADBEEF
Searching for 0xDEADBEEF in range 0x20000000 - 0x20010000
Found at 0x20001234
Total matches: 1
```

## Breakpoint Commands

### break-fault

Set breakpoints on all fault handlers.

```gdb
(gdb) break-fault
Setting breakpoints on all fault handlers...
Breakpoint 1 at 0x08000100: file fault.c, line 10.
Breakpoint 2 at 0x08000120: file fault.c, line 20.
...
```

### break-hardfault

Set breakpoint on HardFault handler only.

```gdb
(gdb) break-hardfault
```

### break-malloc-fail

Break when memory allocation fails (returns NULL).

```gdb
(gdb) break-malloc-fail
Setting breakpoint on allocation failures...
Note: Breaks when allocation returns NULL.
```

### break-assert

Break on assertion failures.

```gdb
(gdb) break-assert
Setting breakpoints on assertions...
```

### break-context-switch

Break on context switches.

```gdb
(gdb) break-context-switch
```

### Watchpoints

```gdb
(gdb) watch-var my_variable    # Break on write
(gdb) watch-read my_variable   # Break on read
(gdb) watch-access my_variable # Break on any access
```

## Pynux-Specific Commands

These commands inspect Pynux kernel data structures.

### pynux-processes

List all processes.

```gdb
(gdb) pynux-processes
=== Pynux Processes ===

PID    STATE        PRIORITY   STACK        NAME
--------------------------------------------------------------
1      RUNNING      10         0x20002000   init
2      READY        5          0x20003000   worker
3      BLOCKED      5          0x20004000   uart_handler
```

### pynux-timers

Show active timers.

```gdb
(gdb) pynux-timers
=== Pynux Timers ===

Current tick: 12345

ID     EXPIRES      PERIOD       STATUS     CALLBACK
--------------------------------------------------------------
1      15000        1000         active     0x08001234
2      20000        0            active     0x08001456
```

### pynux-heap

Show heap status.

```gdb
(gdb) pynux-heap
=== Pynux Heap Status ===

Heap start: 0x20005000
Heap end:   0x20008000
Heap size:  12288 bytes (12 KB)

Total: 12288 bytes
Used:  4096 bytes (33%)
Free:  8192 bytes (66%)
```

### pynux-tasks

Show scheduler state.

```gdb
(gdb) pynux-tasks
=== Pynux Scheduler State ===

Current task: Process(pid=1, name="init", state=RUNNING, priority=10)
Scheduler: running

Ready Queue:
  ready_queue: [2 tasks]

Context switches: 1234
```

### pynux-trace

Show trace buffer contents.

```gdb
(gdb) pynux-trace
=== Pynux Trace Buffer ===

Trace buffer at: 0x20001000
Current index: 45
Buffer size: 64

Recent entries (newest first):
------------------------------------------------------------
[     12345] Event   1: 0x00000001
[     12340] Event   2: 0x08001234
...
```

## Pretty Printers

The Python pretty printers automatically format Pynux structures:

```gdb
(gdb) print current_process
$1 = Process(pid=1, name="init", state=RUNNING, priority=10)

(gdb) print my_timer
$2 = Timer(id=1, expires=15000, period=1000, active, periodic)

(gdb) print my_mutex
$3 = Mutex(locked, owner=1)
```

## Tips and Tricks

### Debugging a HardFault

```gdb
(gdb) break-hardfault
(gdb) continue
# ... fault occurs ...
(gdb) arm-fault          # See what caused the fault
(gdb) arm-stack-frame    # See where it happened
(gdb) backtrace          # Get call stack
```

### Finding Memory Corruption

```gdb
(gdb) watch-var heap_header->magic
(gdb) mem-find 0x20000000 0x20010000 0xDEADC0DE
```

### Debugging Context Switches

```gdb
(gdb) break-context-switch
(gdb) pynux-tasks
(gdb) arm-stack
```

### Checking Interrupt State

```gdb
(gdb) arm-nvic
(gdb) arm-systick
(gdb) print $primask
```

## Loading Scripts Manually

If the scripts don't load automatically:

```gdb
(gdb) source /path/to/pynux/tools/gdb/pynux.gdb
```

Or add to your `~/.gdbinit`:

```gdb
add-auto-load-safe-path /path/to/pynux
```

## Requirements

- GDB with Python support (arm-none-eabi-gdb)
- Python 3.x (built into GDB)
- QEMU or OpenOCD for target connection

## Troubleshooting

### "No symbol table loaded"

Make sure to compile with debug symbols (`-g` flag) and load the ELF file:

```gdb
(gdb) file kernel.elf
```

### "Cannot access memory"

The target may not be halted. Try:

```gdb
(gdb) monitor halt
```

### Python commands not loading

Check that Python support is enabled in your GDB:

```gdb
(gdb) python print("Hello")
```

If this fails, you need a GDB build with Python support.
