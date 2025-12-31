# Pynux API Reference

Complete API documentation for Pynux libraries.

## Table of Contents

1. [Core Libraries](#core-libraries)
2. [Hardware Libraries](#hardware-libraries)
3. [Data Structures](#data-structures)
4. [Control Systems](#control-systems)
5. [Communication](#communication)
6. [System Services](#system-services)

---

## Core Libraries

### lib/io.py - Input/Output

```python
# UART operations
uart_init()                           # Initialize UART
uart_putc(c: char)                    # Write character
uart_getc() -> char                   # Read character (blocking)
uart_available() -> bool              # Check if data available

# Console output
print_str(s: Ptr[char])               # Print string
print_int(n: int32)                   # Print integer
print_newline()                       # Print newline
```

### lib/memory.py - Memory Management

```python
heap_init()                           # Initialize heap
alloc(size: int32) -> Ptr[void]       # Allocate memory
free(ptr: Ptr[void])                  # Free memory (no-op in bump allocator)
heap_used() -> int32                  # Get used heap bytes
heap_remaining() -> int32             # Get remaining heap bytes
heap_total() -> int32                 # Get total heap size
memset(ptr: Ptr[void], val: int32, n: int32)  # Set memory
memcpy(dst: Ptr[void], src: Ptr[void], n: int32)  # Copy memory
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
