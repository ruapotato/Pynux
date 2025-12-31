# Pynux

**A tiny OS for microcontrollers. Python syntax. Native speed.**

Pynux is a Python-syntax systems language that compiles to native ARM Thumb-2. Write familiar Python code, get bare-metal performance on Cortex-M microcontrollers.

## Features

- **Python syntax** you already know (with static types)
- **Compiles to native ARM** - no interpreter, no VM
- **Full OS** - processes, IPC, filesystem, device drivers
- **266 passing tests** across 8 test suites
- **Graphical desktop** via VTNext protocol
- **QEMU simulation** - develop without hardware

## Quick Start

```bash
# Install dependencies
sudo apt install gcc-arm-none-eabi qemu-system-arm python3

# Build
./build.sh

# Run tests
./boot_vm.sh --shell   # Watch 266 tests pass

# Run graphical mode (requires pygame)
pip install pygame
./boot_vm.sh
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    User Programs                             │
│              (programs/main.py, sensors, motors)             │
├─────────────────────────────────────────────────────────────┤
│     Shell      │    Libraries    │   Debug Tools            │
│  (commands,    │  (io, string,   │  (trace, profiler,       │
│   job control) │   math, etc.)   │   memtrack, GDB stub)    │
├─────────────────────────────────────────────────────────────┤
│  Process Mgmt  │   Filesystem    │   Device Drivers         │
│  (IPC, pipes,  │   (RAMFS,       │   (GPIO, PWM, ADC,       │
│   msg queues)  │    devfs)       │    I2C, SPI, sensors)    │
├─────────────────────────────────────────────────────────────┤
│                    Kernel / HAL                              │
│              (timer, memory, interrupts)                     │
├─────────────────────────────────────────────────────────────┤
│                  ARM Cortex-M3 Hardware                      │
└─────────────────────────────────────────────────────────────┘
```

## Writing Programs

Create `programs/main.py` - it runs automatically at boot:

```python
# programs/main.py
from lib.io import console_puts, console_print_int
from kernel.timer import timer_get_ticks

last_print_time: int32 = 0

def user_main():
    """Called once at startup."""
    console_puts("Hello from Pynux!\n")

def user_tick():
    """Called repeatedly - cooperative multitasking."""
    global last_print_time
    ticks: int32 = timer_get_ticks()
    if ticks - last_print_time >= 5000:
        last_print_time = ticks
        console_puts("Uptime: ")
        console_print_int(ticks / 1000)
        console_puts("s\n")
```

### Reading Sensors

```python
from lib.sensors import temp_read, accel_read, light_read

def user_main():
    # Read temperature (returns millidegrees C)
    temp: int32 = temp_read(0)
    console_puts("Temp: ")
    console_print_int(temp / 1000)
    console_puts(" C\n")

    # Read accelerometer
    x: int32 = 0
    y: int32 = 0
    z: int32 = 0
    accel_read(0, &x, &y, &z)
```

### Controlling Motors

```python
from lib.motors import servo_write, dc_set_speed

def user_main():
    servo_write(0, 90)       # Servo to 90 degrees
    dc_set_speed(0, 50)      # DC motor at 50%
```

## Shell Commands

### File Operations
```bash
ls  cat  cp  mv  rm  mkdir  touch  pwd  cd  head  tail  wc  stat
```

### System Info
```bash
uname  uptime  free  date  hostname  arch
```

### Hardware
```bash
sensors          # Read all sensors
servo 0 90       # Set servo angle
motor 0 50       # Set motor speed
drivers list     # Show loaded drivers
```

### Job Control
```bash
command &        # Run in background
jobs             # List background jobs
fg %1            # Bring to foreground
```

## Device Filesystem

Hardware appears as files under `/dev/`:

```bash
# Read temperature
cat /dev/sensors/temp0
> 23.45

# Set servo angle
echo 90 > /dev/motors/servo0

# Read GPIO pin
cat /dev/gpio/pin0
> 1
```

### Available Devices

| Path | Read | Write |
|------|------|-------|
| `/dev/gpio/pinN` | 0/1 | 0/1 |
| `/dev/sensors/tempN` | degrees C | - |
| `/dev/sensors/accelN` | X Y Z | - |
| `/dev/sensors/lightN` | 0-65535 | - |
| `/dev/motors/servoN` | angle | 0-180 |
| `/dev/motors/stepperN` | position | steps |
| `/dev/motors/dcN` | speed% | -100 to 100 |

## Libraries

### Core
| Library | Purpose |
|---------|---------|
| `lib/io.py` | Console I/O, UART |
| `lib/memory.py` | Heap allocation |
| `lib/string.py` | String operations |
| `lib/math.py` | Math, trig, sqrt |

### Hardware
| Library | Purpose |
|---------|---------|
| `lib/peripherals.py` | GPIO, SPI, I2C, PWM, ADC |
| `lib/sensors.py` | Temperature, accelerometer, light |
| `lib/motors.py` | Servo, stepper, DC motors |
| `lib/i2c.py` | Advanced I2C with simulation |
| `lib/spi.py` | Advanced SPI with simulation |

### Debug & Profiling
| Library | Purpose |
|---------|---------|
| `lib/trace.py` | Event tracing with timestamps |
| `lib/profiler.py` | Function timing |
| `lib/memtrack.py` | Memory leak detection |

### Data Structures
| Library | Purpose |
|---------|---------|
| `lib/list.py` | Dynamic arrays |
| `lib/dict.py` | Hash maps |
| `lib/structures.py` | Stack, queue, ring buffer |

### Control Systems
| Library | Purpose |
|---------|---------|
| `lib/pid.py` | PID controller |
| `lib/filters.py` | Low-pass, Kalman filters |
| `lib/fsm.py` | Finite state machines |

### Networking (Advanced)
| Library | Purpose |
|---------|---------|
| `lib/net/` | TCP/IP stack for raw Ethernet |

> **Note:** Most microcontroller projects use WiFi chips (ESP8266/ESP32) or hardware TCP/IP chips (Wiznet W5500) that handle networking internally. The `lib/net/` stack is for advanced use cases with raw Ethernet MACs.

## Testing

Pynux has comprehensive tests:

```bash
./boot_vm.sh --shell
# Runs automatically, shows:
# Test Suites: 8 passed
# Individual Tests: 266 passed
```

Test suites cover:
- IPC (pipes, message queues)
- Memory management
- Timer operations
- RAM filesystem
- Device filesystem
- Event tracing
- Profiler
- Memory tracking

## Project Structure

```
compiler/       # Python-to-ARM compiler (runs on host)
runtime/        # ARM assembly startup
kernel/         # Kernel, scheduler, filesystem
lib/            # 30+ libraries
programs/       # User programs (main.py runs at boot)
tests/          # Test suites (266 tests)
vtnext/         # Graphical terminal (pygame)
```

## Target Hardware

| Platform | Status | Notes |
|----------|--------|-------|
| QEMU mps2-an385 | **Working** | Primary development target |
| RP2040 (Pico) | Experimental | BSP ready, needs hardware testing |
| STM32F4 | Experimental | BSP ready, needs hardware testing |

### Building for Hardware Targets

```bash
# Default: QEMU (recommended for development)
./build.sh
./build.sh --run                    # Build and run in QEMU

# RP2040 (Raspberry Pi Pico) - EXPERIMENTAL
./build.sh --target=rp2040          # Build for Pico
./build.sh --target=rp2040 --flash  # Build and flash (hold BOOTSEL)

# STM32F4 - EXPERIMENTAL
./build.sh --target=stm32f4         # Build for STM32F4
./build.sh --target=stm32f4 --flash # Build and flash via ST-Link
```

> **Note:** Hardware targets are experimental. The BSP (linker scripts, startup code, clock configuration) is complete, but has not been tested on real hardware yet. QEMU remains the recommended development environment.

## Memory Usage

- **Code:** ~485KB
- **Data:** ~175KB
- **Heap:** 16KB available
- **Stack:** 4KB per process

## Building from Source

Requirements:
- GCC ARM toolchain (`gcc-arm-none-eabi`)
- QEMU ARM (`qemu-system-arm`)
- Python 3.10+
- pygame (optional, for graphical mode)

```bash
# Ubuntu/Debian
sudo apt install gcc-arm-none-eabi qemu-system-arm python3

# Build
./build.sh

# Run
./boot_vm.sh --shell    # Text mode
./boot_vm.sh            # Graphical mode
```

## Language Features

Pynux uses Python syntax with static types:

```python
# Type annotations required
count: int32 = 0
name: Ptr[char] = "hello"
data: Array[100, uint8]

# Functions with types
def add(a: int32, b: int32) -> int32:
    return a + b

# Pointers
ptr: Ptr[int32] = &count
value: int32 = ptr[0]

# Arrays
buffer: Array[256, uint8]
buffer[0] = 42
```

See [LANGUAGE.md](LANGUAGE.md) for full syntax reference.

## License

GPL-3.0 - See [LICENSE](LICENSE)
