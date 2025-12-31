# Pynux API Reference

Complete API documentation for Pynux libraries.

## Table of Contents

1. [Core Libraries](#core-libraries)
2. [Hardware Libraries](#hardware-libraries)
3. [Data Structures](#data-structures)
4. [Control Systems](#control-systems)
5. [Communication](#communication)
6. [System Services](#system-services)
7. [Kernel Services](#kernel-services)
8. [Debug & Profiling](#debug--profiling)
9. [Advanced Hardware](#advanced-hardware)

---

## Core Libraries

### lib/io.py - Input/Output

```python
# UART low-level (implemented in assembly)
uart_init()                           # Initialize UART
uart_putc(c: char)                    # Write character
uart_getc() -> char                   # Read character (blocking)
uart_available() -> bool              # Check if data available

# Direct UART output
print_str(s: Ptr[char])               # Print string to UART
print_int(n: int32)                   # Print integer to UART
print_hex(n: uint32)                  # Print hex to UART
print_newline()                       # Print newline

# Console abstraction (redirectable to DE terminal)
console_putc(c: char)                 # Output character
console_puts(s: Ptr[char])            # Output string
console_print_int(n: int32)           # Output integer
console_set_mode(mode: int32)         # 0=UART, 1=buffered for DE
console_flush() -> Ptr[char]          # Get buffer and reset
console_has_output() -> bool          # Check for buffered output

# Line input
read_char() -> char                   # Read single character
read_line() -> Ptr[char]              # Read line with editing
```

### lib/memory.py - Memory Management

Free-list allocator with coalescing support.

```python
# Allocation
heap_init()                           # Initialize heap (auto-called)
alloc(size: int32) -> Ptr[uint8]      # Allocate memory
calloc(count: int32, size: int32) -> Ptr[uint8]  # Allocate zeroed
realloc(ptr: Ptr[uint8], new_size: int32) -> Ptr[uint8]  # Resize
free(ptr: Ptr[uint8])                 # Free memory (with coalescing)

# Heap statistics
heap_used() -> int32                  # Get used heap bytes
heap_remaining() -> int32             # Get free heap bytes
heap_total() -> int32                 # Get total heap size (16KB)

# Memory operations
memset(dst: Ptr[uint8], val: uint8, size: int32)
memcpy(dst: Ptr[uint8], src: Ptr[uint8], size: int32)
memmove(dst: Ptr[uint8], src: Ptr[uint8], size: int32)  # Overlap-safe
memcmp(a: Ptr[uint8], b: Ptr[uint8], size: int32) -> int32
```

### lib/string.py - String Operations

```python
strlen(s: Ptr[char]) -> int32         # Get string length
strcmp(a: Ptr[char], b: Ptr[char]) -> int32  # Compare strings
strcpy(dst: Ptr[char], src: Ptr[char])  # Copy string
strcat(dst: Ptr[char], src: Ptr[char])  # Concatenate strings
atoi(s: Ptr[char]) -> int32           # String to integer
itoa(n: int32, buf: Ptr[char])        # Integer to string
isdigit(c: char) -> bool              # Check if digit
isalpha(c: char) -> bool              # Check if letter
toupper(c: char) -> char              # Convert to uppercase
tolower(c: char) -> char              # Convert to lowercase
```

### lib/math.py - Math Functions

```python
abs_int(x: int32) -> int32            # Absolute value
min_int(a: int32, b: int32) -> int32  # Minimum
max_int(a: int32, b: int32) -> int32  # Maximum
clamp(val: int32, lo: int32, hi: int32) -> int32  # Clamp to range
sqrt_int(x: int32) -> int32           # Integer square root
pow_int(base: int32, exp: int32) -> int32  # Integer power
gcd(a: int32, b: int32) -> int32      # Greatest common divisor
sin_lookup(deg: int32) -> int32       # Sine (scaled by 1000)
cos_lookup(deg: int32) -> int32       # Cosine (scaled by 1000)
```

---

## Hardware Libraries

### lib/sensors.py - Sensor Drivers

```python
# Initialization
sensors_init_all()                    # Initialize all sensors
sensors_seed(seed: int32)             # Set random seed for simulation
sensors_enable_noise(enable: bool)    # Enable/disable noise

# Temperature (returns centidegrees: 2350 = 23.50°C)
temp_init()
temp_read() -> int32
temp_set_base(base: int32)

# Accelerometer (returns mg: 980 = 0.98g)
accel_init()
accel_read_x() -> int32
accel_read_y() -> int32
accel_read_z() -> int32

# Light sensor (0-65535)
light_init()
light_read() -> int32
light_set_base(base: int32)

# Humidity (0.1% resolution: 654 = 65.4%)
humid_init()
humid_read() -> int32

# Pressure (Pa, e.g., 101325 = 1013.25 hPa)
press_init()
press_read() -> int32
press_to_altitude(pressure: int32) -> int32  # Pressure to altitude in meters
```

### lib/motors.py - Motor Control

```python
# Servo motors (0-180 degrees)
servo_init(id: int32)
servo_set_angle(id: int32, angle: int32)
servo_get_angle(id: int32) -> int32

# Stepper motors (position in steps)
stepper_init(id: int32, steps_per_rev: int32)
stepper_steps(id: int32, steps: int32)  # Positive = CW, negative = CCW
stepper_get_position(id: int32) -> int32
stepper_home(id: int32)               # Reset position to 0

# DC motors (-100 to 100 percent)
dc_init(id: int32)
dc_set_speed(id: int32, speed: int32)
dc_get_speed(id: int32) -> int32
dc_brake(id: int32)                   # Emergency stop
```

### lib/display.py - Display Drivers

```python
# HD44780 LCD (16x2 or 20x4)
lcd_init(cols: int32, rows: int32)
lcd_clear()
lcd_home()
lcd_set_cursor(col: int32, row: int32)
lcd_print(s: Ptr[char])
lcd_print_int(n: int32)

# SSD1306 OLED (128x64)
oled_init()
oled_clear()
oled_set_pixel(x: int32, y: int32, on: bool)
oled_draw_line(x0: int32, y0: int32, x1: int32, y1: int32)
oled_draw_rect(x: int32, y: int32, w: int32, h: int32)
oled_print(x: int32, y: int32, s: Ptr[char])
oled_update()                         # Flush buffer to display

# 7-segment display
seg7_init(digits: int32)
seg7_display(value: int32)
seg7_display_hex(value: int32)
seg7_clear()
```

### lib/peripherals.py - GPIO and Peripherals

```python
# GPIO
gpio_init(pin: int32, mode: int32)    # mode: 0=input, 1=output
gpio_write(pin: int32, value: int32)
gpio_read(pin: int32) -> int32
gpio_toggle(pin: int32)

# ADC (0-4095 for 12-bit)
adc_init(channel: int32)
adc_read(channel: int32) -> int32

# PWM (0-255 duty cycle)
pwm_init(channel: int32, freq: int32)
pwm_set_duty(channel: int32, duty: int32)

# SPI
spi_init(speed: int32)
spi_transfer(data: uint8) -> uint8
spi_write_buf(buf: Ptr[uint8], len: int32)
spi_read_buf(buf: Ptr[uint8], len: int32)

# I2C
i2c_init(speed: int32)
i2c_write(addr: uint8, data: Ptr[uint8], len: int32) -> bool
i2c_read(addr: uint8, buf: Ptr[uint8], len: int32) -> bool
```

---

## Data Structures

### lib/list.py - Dynamic Lists

```python
list_create() -> Ptr[List]
list_append(lst: Ptr[List], value: int32)
list_get(lst: Ptr[List], index: int32) -> int32
list_set(lst: Ptr[List], index: int32, value: int32)
list_len(lst: Ptr[List]) -> int32
list_pop(lst: Ptr[List]) -> int32
list_clear(lst: Ptr[List])
list_contains(lst: Ptr[List], value: int32) -> bool
list_index(lst: Ptr[List], value: int32) -> int32
list_remove(lst: Ptr[List], value: int32) -> bool
list_reverse(lst: Ptr[List])
list_sort(lst: Ptr[List])
```

### lib/dict.py - Hash Maps

```python
dict_create() -> Ptr[Dict]
dict_set(d: Ptr[Dict], key: Ptr[char], value: int32)
dict_get(d: Ptr[Dict], key: Ptr[char]) -> int32
dict_contains(d: Ptr[Dict], key: Ptr[char]) -> bool
dict_remove(d: Ptr[Dict], key: Ptr[char]) -> bool
dict_len(d: Ptr[Dict]) -> int32
dict_clear(d: Ptr[Dict])
```

### lib/structures.py - Stack, Queue, Ring Buffer

```python
# Stack
stack_create(capacity: int32) -> Ptr[Stack]
stack_push(s: Ptr[Stack], value: int32) -> bool
stack_pop(s: Ptr[Stack]) -> int32
stack_peek(s: Ptr[Stack]) -> int32
stack_is_empty(s: Ptr[Stack]) -> bool
stack_is_full(s: Ptr[Stack]) -> bool

# Queue
queue_create(capacity: int32) -> Ptr[Queue]
queue_enqueue(q: Ptr[Queue], value: int32) -> bool
queue_dequeue(q: Ptr[Queue]) -> int32
queue_peek(q: Ptr[Queue]) -> int32
queue_is_empty(q: Ptr[Queue]) -> bool
queue_is_full(q: Ptr[Queue]) -> bool

# Ring buffer
ring_create(capacity: int32) -> Ptr[RingBuffer]
ring_write(r: Ptr[RingBuffer], data: uint8) -> bool
ring_read(r: Ptr[RingBuffer]) -> int32
ring_available(r: Ptr[RingBuffer]) -> int32
ring_free(r: Ptr[RingBuffer]) -> int32
```

### lib/algo.py - Algorithms

```python
# Sorting
bubble_sort(arr: Ptr[int32], len: int32)
insertion_sort(arr: Ptr[int32], len: int32)
selection_sort(arr: Ptr[int32], len: int32)

# Searching
linear_search(arr: Ptr[int32], len: int32, target: int32) -> int32
binary_search(arr: Ptr[int32], len: int32, target: int32) -> int32

# Array utilities
array_reverse(arr: Ptr[int32], len: int32)
array_sum(arr: Ptr[int32], len: int32) -> int32
array_min(arr: Ptr[int32], len: int32) -> int32
array_max(arr: Ptr[int32], len: int32) -> int32
```

---

## Control Systems

### lib/pid.py - PID Controller

```python
pid_init(kp: int32, ki: int32, kd: int32)  # Gains scaled by 100
pid_set_setpoint(sp: int32)
pid_update(pv: int32) -> int32        # Process variable -> control output
pid_reset()
pid_set_limits(min_out: int32, max_out: int32)
```

### lib/filters.py - Signal Filters

```python
# Low-pass filter
lpf_init(alpha: int32)                # Alpha 0-100 (higher = more smoothing)
lpf_update(value: int32) -> int32

# Moving average
mavg_init(window_size: int32)
mavg_update(value: int32) -> int32
mavg_reset()

# Kalman filter (1D)
kalman_init(q: int32, r: int32)       # Process/measurement noise
kalman_update(measurement: int32) -> int32
```

### lib/fsm.py - Finite State Machine

```python
fsm_init(initial_state: int32)
fsm_add_transition(from_state: int32, event: int32, to_state: int32)
fsm_process_event(event: int32) -> int32  # Returns new state
fsm_get_state() -> int32
fsm_set_state(state: int32)
```

---

## Communication

### lib/onewire.py - 1-Wire Protocol

```python
ow_init(pin: int32)
ow_reset() -> bool                    # Returns True if device present
ow_write_byte(data: uint8)
ow_read_byte() -> uint8
ow_search_first() -> bool             # Search for first device
ow_search_next() -> bool              # Search for next device
ow_get_address(addr: Ptr[uint8])      # Get 8-byte address
```

### lib/canbus.py - CAN Bus

```python
can_init(bitrate: int32)
can_send(id: int32, data: Ptr[uint8], len: int32) -> bool
can_receive(id: Ptr[int32], data: Ptr[uint8], len: Ptr[int32]) -> bool
can_available() -> bool
can_set_filter(id: int32, mask: int32)
```

### lib/json.py - JSON Parser

```python
json_parse(s: Ptr[char]) -> Ptr[JsonValue]
json_get_type(v: Ptr[JsonValue]) -> int32  # 0=null, 1=bool, 2=int, 3=string, 4=array, 5=object
json_get_int(v: Ptr[JsonValue]) -> int32
json_get_string(v: Ptr[JsonValue]) -> Ptr[char]
json_get_bool(v: Ptr[JsonValue]) -> bool
json_array_len(v: Ptr[JsonValue]) -> int32
json_array_get(v: Ptr[JsonValue], index: int32) -> Ptr[JsonValue]
json_object_get(v: Ptr[JsonValue], key: Ptr[char]) -> Ptr[JsonValue]
```

### lib/encoding.py - Encoding/Decoding

```python
# Base64
base64_encode(input: Ptr[uint8], len: int32, output: Ptr[char]) -> int32
base64_decode(input: Ptr[char], output: Ptr[uint8]) -> int32

# Hex
hex_encode(input: Ptr[uint8], len: int32, output: Ptr[char])
hex_decode(input: Ptr[char], output: Ptr[uint8]) -> int32
```

---

## System Services

### lib/rtc.py - Real-Time Clock

```python
rtc_init()
rtc_get_time(hour: Ptr[int32], min: Ptr[int32], sec: Ptr[int32])
rtc_set_time(hour: int32, min: int32, sec: int32)
rtc_get_date(year: Ptr[int32], month: Ptr[int32], day: Ptr[int32])
rtc_set_date(year: int32, month: int32, day: int32)
rtc_get_timestamp() -> int32          # Unix timestamp
```

### lib/watchdog.py - Watchdog Timer

```python
watchdog_init(timeout_ms: int32)
watchdog_feed()                       # Reset watchdog timer
watchdog_disable()
watchdog_get_timeout() -> int32
```

### lib/eeprom.py - EEPROM Storage

```python
eeprom_init()
eeprom_read(addr: int32) -> uint8
eeprom_write(addr: int32, data: uint8)
eeprom_read_int(addr: int32) -> int32
eeprom_write_int(addr: int32, value: int32)
eeprom_size() -> int32
```

### lib/logging.py - Logging System

```python
# Log levels: 0=DEBUG, 1=INFO, 2=WARN, 3=ERROR
log_set_level(level: int32)
log_debug(msg: Ptr[char])
log_info(msg: Ptr[char])
log_warn(msg: Ptr[char])
log_error(msg: Ptr[char])
log_int(label: Ptr[char], value: int32)
```

### lib/events.py - Event System

```python
event_init()
event_post(event_id: int32, data: int32)
event_poll() -> int32                 # Returns event_id or -1
event_get_data() -> int32             # Get data from last polled event
event_wait() -> int32                 # Block until event available
event_clear()
```

---

## Kernel Services

### kernel/process.py - Process Management

```python
# Process creation
proc_create(name: Ptr[char]) -> int32  # Returns PID or -1

# Signals
signal_send(pid: int32, sig: int32) -> bool
signal_handler(sig: int32, handler: Ptr[void]) -> bool

# Pipes (IPC)
pipe_create() -> int32                # Returns file descriptor
pipe_read(fd: int32, buf: Ptr[uint8], len: int32) -> int32
pipe_write(fd: int32, buf: Ptr[uint8], len: int32) -> int32
pipe_close(fd: int32) -> bool

# Message queues (IPC)
mq_create() -> int32                  # Returns queue ID
mq_send(mqid: int32, buf: Ptr[uint8], len: int32) -> bool
mq_receive(mqid: int32, buf: Ptr[uint8], maxlen: int32) -> int32
mq_close(mqid: int32) -> bool
```

### kernel/devfs.py - Device Filesystem

```python
devfs_register(dtype: int32, id: int32, pin: int32, name: Ptr[char]) -> int32
devfs_find_by_path(path: Ptr[char]) -> int32
devfs_read(dev_idx: int32) -> Ptr[char]
devfs_write(dev_idx: int32, value: Ptr[char]) -> int32
devfs_get_count() -> int32
devfs_get_path(idx: int32) -> Ptr[char]
devfs_scan_drivers()                  # Reload /etc/drivers/*.conf
```

### kernel/ramfs.py - RAM Filesystem

```python
ramfs_create(path: Ptr[char], is_dir: bool) -> bool
ramfs_delete(path: Ptr[char]) -> bool
ramfs_exists(path: Ptr[char]) -> bool
ramfs_isdir(path: Ptr[char]) -> bool
ramfs_read(path: Ptr[char], buf: Ptr[uint8], maxlen: int32) -> int32
ramfs_write(path: Ptr[char], data: Ptr[char]) -> int32
ramfs_size(path: Ptr[char]) -> int32
ramfs_readdir(path: Ptr[char], index: int32, name: Ptr[char], maxlen: int32) -> int32
```

### kernel/timer.py - Timer Services

```python
timer_init()
timer_get_ticks() -> int32            # Milliseconds since boot
timer_delay_ms(ms: int32)             # Blocking delay
timer_tick()                          # Called by interrupt handler
```

---

## Debug & Profiling

### lib/trace.py - Execution Tracing

Lightweight event tracing using a circular buffer. Useful for debugging timing issues, tracking IRQs, and profiling execution flow.

```python
# Event types (constants)
TRACE_FUNC_ENTER = 0x01     # Function entry
TRACE_FUNC_EXIT = 0x02      # Function exit
TRACE_IRQ = 0x03            # IRQ entry
TRACE_IRQ_EXIT = 0x04       # IRQ exit
TRACE_ALLOC = 0x06          # Memory allocation
TRACE_FREE = 0x07           # Memory free
TRACE_ERROR = 0x0C          # Error event
TRACE_USER = 0x10           # User-defined event

# Initialization and control
trace_init()                          # Initialize tracing
trace_enable()                        # Start tracing
trace_disable()                       # Stop tracing
trace_is_enabled() -> bool            # Check if enabled
trace_clear()                         # Clear buffer

# Logging events
trace_log(event: int32, data: uint32) # Log generic event
trace_log_func_enter(func_addr: uint32)
trace_log_func_exit(func_addr: uint32)
trace_log_irq(irq_num: int32)
trace_log_irq_exit(irq_num: int32)
trace_log_alloc(ptr: uint32, size: int32)
trace_log_free(ptr: uint32)
trace_log_error(code: int32)
trace_log_user(data: uint32)

# Filtering
trace_set_filter(mask: int32)         # Set event filter bitmask
trace_get_filter() -> int32           # Get current filter

# Analysis
trace_get_count() -> int32            # Number of entries
trace_get_overflow() -> int32         # Lost entries count
trace_count_events(event_type: int32) -> int32
trace_find_event(event_type: int32, start_from: int32) -> int32
trace_get_last(event_out: Ptr[int32], data_out: Ptr[uint32]) -> bool

# Output
trace_dump()                          # Print all entries
trace_dump_range(start_idx: int32, count: int32)
```

### lib/profiler.py - Function Timing

Cycle-accurate timing profiler for measuring code performance.

```python
# Initialization and control
profile_init()                        # Initialize profiler
profile_enable()                      # Enable profiling
profile_disable()                     # Disable (start/stop become no-ops)
profile_is_enabled() -> bool
profile_reset()                       # Clear all data

# Timing sections
profile_start(name: Ptr[char])        # Start timing named section
profile_stop(name: Ptr[char])         # Stop timing named section

# Query statistics (all times in cycles)
profile_get_calls(name: Ptr[char]) -> int32   # Call count
profile_get_total(name: Ptr[char]) -> int32   # Total cycles
profile_get_avg(name: Ptr[char]) -> int32     # Average cycles per call
profile_get_max(name: Ptr[char]) -> int32     # Max cycles

# Output
profile_report()                      # Print timing report
profile_get_count() -> int32          # Number of profiled sections
```

**Example:**
```python
profile_init()
profile_start("sensor_read")
temp: int32 = temp_read()
profile_stop("sensor_read")
profile_report()  # Shows timing stats
```

### lib/memtrack.py - Memory Leak Detection

Tracks allocations with tags for debugging memory usage and detecting leaks.

```python
# Initialization and control
memtrack_init()                       # Initialize tracker
memtrack_enable()                     # Enable tracking
memtrack_disable()                    # Disable tracking
memtrack_is_enabled() -> bool
memtrack_reset()                      # Clear all data

# Tracking allocations
memtrack_alloc(ptr: Ptr[uint8], size: int32, tag: Ptr[char])
memtrack_free(ptr: Ptr[uint8])

# Query
memtrack_get_total() -> int32         # Total bytes ever allocated
memtrack_get_peak() -> int32          # Peak memory usage
memtrack_get_current() -> int32       # Current allocated bytes
memtrack_get_count() -> int32         # Active allocation count
memtrack_get_size(ptr: Ptr[uint8]) -> int32   # Size of allocation
memtrack_get_tag(ptr: Ptr[uint8]) -> Ptr[char]

# Analysis
memtrack_check_leaks() -> int32       # Returns leak count, prints report
memtrack_report()                     # Print full report
```

**Example:**
```python
memtrack_init()
ptr: Ptr[uint8] = alloc(256)
memtrack_alloc(ptr, 256, "buffer")
# ... use memory ...
memtrack_check_leaks()  # Reports if not freed
```

### lib/breakpoint.py - Debug Breakpoints

Software breakpoint support for debugging.

```python
breakpoint_init()
breakpoint_trigger()                  # Trigger breakpoint (BKPT instruction)
breakpoint_set(addr: uint32) -> bool  # Set breakpoint at address
breakpoint_clear(addr: uint32) -> bool
breakpoint_enable()
breakpoint_disable()
```

---

## Advanced Hardware

### lib/i2c.py - Advanced I2C Bus

Full I2C bus implementation with device scanning, multi-bus support, and simulation mode.

```python
# Bus initialization
i2c_bus_init(bus: int32, speed: int32)    # Initialize bus (0=100kHz, 1=400kHz)
i2c_bus_reset(bus: int32)                 # Reset bus

# Device communication
i2c_bus_write(bus: int32, addr: uint8, data: Ptr[uint8], len: int32) -> int32
i2c_bus_read(bus: int32, addr: uint8, buf: Ptr[uint8], len: int32) -> int32
i2c_bus_write_reg(bus: int32, addr: uint8, reg: uint8, val: uint8) -> int32
i2c_bus_read_reg(bus: int32, addr: uint8, reg: uint8) -> int32

# Bus scanning
i2c_bus_scan(bus: int32)                  # Print detected devices
i2c_bus_probe(bus: int32, addr: uint8) -> bool  # Check if device responds

# Simulation
i2c_sim_enable(bus: int32)                # Enable simulation mode
i2c_sim_add_device(bus: int32, addr: uint8, device_type: int32)
i2c_sim_set_reg(bus: int32, addr: uint8, reg: uint8, val: uint8)
```

### lib/spi.py - Advanced SPI Bus

Full SPI implementation with multiple buses and chip select management.

```python
# Bus initialization
spi_bus_init(bus: int32, speed: int32, mode: int32)
spi_bus_reset(bus: int32)

# Data transfer
spi_bus_transfer(bus: int32, tx: Ptr[uint8], rx: Ptr[uint8], len: int32) -> int32
spi_bus_write(bus: int32, data: Ptr[uint8], len: int32) -> int32
spi_bus_read(bus: int32, buf: Ptr[uint8], len: int32) -> int32

# Chip select
spi_bus_select(bus: int32, cs: int32)     # Assert CS
spi_bus_deselect(bus: int32, cs: int32)   # Deassert CS

# Simulation
spi_sim_enable(bus: int32)
spi_sim_add_device(bus: int32, cs: int32, device_type: int32)
```
