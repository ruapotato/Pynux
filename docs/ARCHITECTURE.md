# Pynux Architecture

This document describes the internal architecture of Pynux OS.

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                      User Programs                               │
│                  (programs/*.py)                                 │
├─────────────────────────────────────────────────────────────────┤
│  Shell      │   Libraries    │  Debug Tools   │  DE/Graphics    │
│ (commands,  │ (io, string,   │ (trace,        │ (vtnext,        │
│  job ctrl)  │  math, etc.)   │  profiler)     │  widgets)       │
├─────────────────────────────────────────────────────────────────┤
│  Processes  │  Filesystem    │  Device FS     │  Drivers        │
│  (IPC,      │  (RAMFS)       │  (devfs)       │  (GPIO, I2C,    │
│  signals)   │                │                │   SPI, PWM)     │
├─────────────────────────────────────────────────────────────────┤
│                        Kernel                                    │
│        (memory, timer, critical sections, scheduler)            │
├─────────────────────────────────────────────────────────────────┤
│                     Runtime (startup.s)                          │
│        (vector table, reset handler, UART primitives)           │
├─────────────────────────────────────────────────────────────────┤
│                   ARM Cortex-M3 Hardware                         │
│            (QEMU mps2-an385 or physical board)                  │
└─────────────────────────────────────────────────────────────────┘
```

## Build Pipeline

```
  Pynux Source (.py)
         │
         ▼
  ┌─────────────┐
  │   Parser    │  compiler/parser.py
  │   (AST)     │  - Tokenizes Python-like syntax
  └─────────────┘  - Builds abstract syntax tree
         │
         ▼
  ┌─────────────┐
  │  Code Gen   │  compiler/codegen_arm.py
  │  (ARM ASM)  │  - Generates ARM Thumb-2 assembly
  └─────────────┘  - Handles types, pointers, arrays
         │
         ▼
  ┌─────────────┐
  │ Assembler   │  arm-none-eabi-as
  │  (.o)       │
  └─────────────┘
         │
         ▼
  ┌─────────────┐
  │  Linker     │  arm-none-eabi-ld
  │  (.elf)     │  - Uses mps2-an385.ld
  └─────────────┘
         │
         ▼
  ┌─────────────┐
  │  QEMU       │  qemu-system-arm
  │  (run)      │  - Emulates Cortex-M3
  └─────────────┘
```

## Memory Map (mps2-an385)

```
0x00000000 ┌─────────────────┐
           │    Flash        │  4MB (code)
0x00400000 ├─────────────────┤
           │   (unused)      │
0x20000000 ├─────────────────┤
           │     RAM         │
           │  ┌───────────┐  │
           │  │   .data   │  │  Initialized data
           │  ├───────────┤  │
           │  │   .bss    │  │  Zero-initialized
           │  ├───────────┤  │
           │  │   Stack   │  │  4KB per process
0x20010000 │  ├───────────┤  │
           │  │   Heap    │  │  16KB (alloc/free)
0x20014000 │  └───────────┤  │
           │   (unused)      │
0x20400000 └─────────────────┘

0x40000000 ┌─────────────────┐
           │  Peripherals    │  UART, GPIO, etc.
0xE0000000 ├─────────────────┤
           │  System         │  SysTick, NVIC
0xFFFFFFFF └─────────────────┘
```

## Kernel Components

### Memory Manager (lib/memory.py)

Free-list allocator with block coalescing.

```
Block Structure:
┌──────────────┬───────────────────────┐
│  Header (8B) │      User Data        │
│ size | flags │                       │
└──────────────┴───────────────────────┘

Allocation: First-fit search of free list
Free: Mark block free, coalesce adjacent blocks
```

### Timer (kernel/timer.py)

Uses ARM SysTick for millisecond timing.

```
SysTick @ 0xE000E010
  - 24-bit countdown timer
  - Reload value set for 1ms tick
  - Generates SysTick_Handler interrupt
```

### IPC (kernel/process.py)

Two IPC mechanisms:

**Pipes** - byte streams
```
pipe_create() -> fd
pipe_write(fd, data, len) -> bytes_written
pipe_read(fd, buf, len) -> bytes_read
```

**Message Queues** - discrete messages
```
mq_create() -> mqid
mq_send(mqid, msg, len) -> bool
mq_receive(mqid, buf, maxlen) -> msg_len
```

### Filesystem

**RAMFS** (kernel/ramfs.py)
- In-memory filesystem
- Supports files and directories
- Path-based API (create, read, write, delete)

**DevFS** (kernel/devfs.py)
- Virtual filesystem for hardware
- Devices appear as files under /dev/
- Read/write operations map to hardware

```
/dev/
├── gpio/
│   ├── pin0
│   └── pin1
├── sensors/
│   ├── temp0
│   └── light0
└── motors/
    ├── servo0
    └── dc0
```

## Execution Model

### Boot Sequence

1. **startup.s**: Reset_Handler
   - Set stack pointer
   - Zero .bss section
   - Copy .data from flash
   - Call kernel_main

2. **kernel.py**: kernel_main()
   - heap_init()
   - timer_init()
   - ramfs_init()
   - devfs_init()
   - Start shell or graphical DE

### Main Loop

```python
while True:
    # Process user program tick
    user_tick()

    # Handle shell input
    shell_tick()

    # Process background jobs
    process_tick()

    # Update timers
    timer_tick()
```

### Critical Sections

For interrupt-safe code:

```python
state: int32 = critical_enter()  # Disable interrupts
# ... critical code ...
critical_exit(state)             # Restore interrupts
```

## Driver Architecture

Drivers follow a consistent pattern:

```python
# Initialize
xxx_init(id: int32)

# Read value
xxx_read(id: int32) -> int32

# Write value
xxx_write(id: int32, value: int32)

# Status
xxx_is_ready(id: int32) -> bool
```

### Hardware Abstraction

Physical hardware access uses volatile pointers:

```python
# Direct register access
GPIO_BASE: Ptr[volatile uint32] = cast[Ptr[volatile uint32]](0x40010000)
GPIO_BASE[0] = value  # Write to hardware register
```

### Simulation Mode

For QEMU testing, drivers provide simulation:

```python
# Enable simulation (no real hardware)
xxx_sim_enable(id: int32)

# Set simulated value
xxx_sim_set_value(id: int32, value: int32)
```

## Type System

Pynux uses static types with C-like semantics:

| Type | Size | Description |
|------|------|-------------|
| int32 | 4 bytes | Signed 32-bit integer |
| uint32 | 4 bytes | Unsigned 32-bit integer |
| uint8 | 1 byte | Unsigned byte |
| char | 1 byte | Character |
| bool | 1 byte | Boolean |
| Ptr[T] | 4 bytes | Pointer to T |
| Array[N, T] | N * sizeof(T) | Fixed-size array |

### Pointer Operations

```python
# Address-of
ptr: Ptr[int32] = &variable

# Dereference
value: int32 = ptr[0]

# Array indexing
arr: Array[10, int32]
arr[5] = 42

# Casting
ptr: Ptr[uint8] = cast[Ptr[uint8]](raw_addr)
```

## Code Generation

The compiler generates ARM Thumb-2 assembly:

### Function Prologue/Epilogue
```asm
function_name:
    push {r4-r7, lr}      @ Save callee-saved registers
    sub sp, sp, #16       @ Allocate locals

    @ ... function body ...

    add sp, sp, #16       @ Deallocate locals
    pop {r4-r7, pc}       @ Return
```

### Calling Convention
- r0-r3: Arguments (first 4)
- r0: Return value
- r4-r11: Callee-saved
- r12: Scratch
- sp: Stack pointer
- lr: Link register
- pc: Program counter

## Testing

Tests are compiled as Pynux code and run on QEMU:

```
tests/
├── test_framework.py   # Test runner macros
├── test_ipc.py         # IPC tests (30)
├── test_memory.py      # Memory tests (41)
├── test_timer.py       # Timer tests (22)
├── test_ramfs.py       # Filesystem tests (41)
├── test_devfs.py       # Device tests (30)
├── test_trace.py       # Tracing tests (30)
├── test_profiler.py    # Profiler tests (25)
└── test_memtrack.py    # Memory tracking tests (47)
```

Run tests:
```bash
./boot_vm.sh --shell    # 266 tests, 8 suites
```

## Debug Tools

### Execution Tracing (lib/trace.py)
- Circular buffer of events
- Timestamps from SysTick
- Event types: function, IRQ, alloc, error, user

### Profiling (lib/profiler.py)
- Named section timing
- Cycle-accurate via SysTick
- Reports: calls, total, avg, max

### Memory Tracking (lib/memtrack.py)
- Tag allocations with names
- Track peak usage
- Detect memory leaks

### GDB Support (kernel/gdb_stub.py)
- Software breakpoints
- GDB remote protocol
- Register inspection
