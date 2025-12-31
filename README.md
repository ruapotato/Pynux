# Pynux

**GNU for microcontrollers. Python syntax. Native speed.**

Pynux is a Python-syntax systems language that compiles to native ARM. Run `cat`, `ls`, `grep`, and `sh` on a $4 Raspberry Pi Pico.

## What is this?

- **Python syntax** you already know
- **Compiles to native ARM** Thumb-2 (Cortex-M)
- **Graphical desktop** - Multi-window DE over VTNext protocol
- **Job control** - Background tasks with `jobs`, `fg`, `bg`
- **User programs** - `programs/main.py` runs at boot like CircuitPython

## Quick Start

```bash
# Build
./build.sh

# Run in QEMU with VTNext graphical desktop
./boot_vm.sh

# Run in text mode
./boot_vm.sh --shell
```

## Desktop Environment

Pynux includes a graphical desktop environment with:

- **Menu** (ESC) - Launch apps, close windows
- **Terminal** - Full shell with file operations
- **Editor** - Text editor with Ctrl+S save
- **File Manager** - Navigate and open files

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| ESC | Toggle menu |
| TAB | Switch windows |
| j/k | Navigate (menu/files) |
| Enter | Select/execute |
| Ctrl+S | Save (editor) |
| Ctrl+C | Cancel (terminal) |

```
┌─────────────────────────────────────────────────────────┐
│ Menu                                                    │
├─────────────────────────────────────────────────────────┤
│ ┌─ Terminal 1 ────────────────────────────────────────┐ │
│ │ [1] main.py &                                       │ │
│ │ main.py: Uptime monitor started                     │ │
│ │                                                     │ │
│ │ pynux:/> ls                                         │ │
│ │ dev/  etc/  home/  tmp/                             │ │
│ │ pynux:/> _                                          │ │
│ └─────────────────────────────────────────────────────┘ │
│ ┌─ Files: / ─────────┐ ┌─ Editor ────────────────────┐ │
│ │ ..                  │ │                             │ │
│ │ dev/                │ │ (empty)                     │ │
│ │ etc/                │ │                             │ │
│ │ home/               │ └─────────────────────────────┘ │
│ └─────────────────────┘                                 │
├─────────────────────────────────────────────────────────┤
│ Heap: 2080/16384 | Win: 3 | F1:Menu F2:Switch          │
└─────────────────────────────────────────────────────────┘
```

## Shell Commands

### File Operations
`ls` `cat` `cp` `mv` `rm` `mkdir` `touch` `write` `head` `tail` `wc` `stat` `pwd` `cd`

### System
`uname` `hostname` `whoami` `uptime` `free` `date` `printenv` `arch` `tty` `groups`

### Job Control
`jobs` `fg` `bg`

### Utilities
`echo` `seq` `factor` `true` `false` `yes` `clear` `help` `version`

### Hardware
`sensors` `servo` `stepper` `motor` `drivers` `sensormon` `motorctl`

## User Programs

Create `programs/main.py` to run code at boot:

```python
# programs/main.py
from lib.io import console_puts, console_print_int
from kernel.timer import timer_get_ticks

last_print_time: int32 = 0

def user_main():
    console_puts("Hello from main.py!\n")

def user_tick():
    global last_print_time
    ticks: int32 = timer_get_ticks()
    if ticks - last_print_time >= 5000:
        last_print_time = ticks
        console_puts("Uptime: ")
        console_print_int(ticks / 1000)
        console_puts("s\n")
```

- `user_main()` - Called once at startup
- `user_tick()` - Called repeatedly (cooperative multitasking)
- Shows as `[1] main.py &` in job list

## Device Filesystem (devfs)

Pynux exposes hardware as virtual files under `/dev/`, following the Unix philosophy. Read sensors and control actuators using standard file operations.

### Reading Devices

```bash
# Read temperature sensor
cat /dev/sensors/temp0
> 23.45

# Read GPIO pin state
cat /dev/gpio/pin3
> 1

# Read accelerometer
cat /dev/sensors/accel0
> X=0 Y=0 Z=980
```

### Writing Devices

```bash
# Set GPIO pin high
echo 1 > /dev/gpio/pin3

# Set servo angle
echo 90 > /dev/motors/servo0

# Set DC motor speed
echo 50 > /dev/motors/dc0
```

### Driver Configuration

Create driver config files in `/etc/drivers/` (one device per file):

```ini
# /etc/drivers/temp0.conf
type=temp
id=0
pin=4
name=temp0
```

```ini
# /etc/drivers/servo0.conf
type=servo
id=0
pin=9
name=servo0
```

```ini
# /etc/drivers/motor0.conf
type=dc
id=0
pin=10
name=motor0
```

**Note:** By default, 12 demo devices are registered at boot:
- `/dev/gpio/pin0` through `/dev/gpio/pin3` - GPIO pins
- `/dev/sensors/temp0` - Temperature (simulated with noise)
- `/dev/sensors/accel0` - 3-axis accelerometer
- `/dev/sensors/light0` - Ambient light sensor
- `/dev/sensors/humid0` - Humidity sensor
- `/dev/sensors/press0` - Barometric pressure
- `/dev/motors/servo0` - Servo motor (0-180°)
- `/dev/motors/stepper0` - Stepper motor
- `/dev/motors/dc0` - DC motor (-100% to 100%)

### Supported Device Types

| Type | Path | Read | Write |
|------|------|------|-------|
| GPIO | /dev/gpio/pinN | 0/1 | 0/1/high/low |
| Temperature | /dev/sensors/tempN | XX.XX (C) | - |
| Accelerometer | /dev/sensors/accelN | X=n Y=n Z=n | - |
| Light | /dev/sensors/lightN | 0-65535 | - |
| Humidity | /dev/sensors/humidN | XX.X (%) | - |
| Pressure | /dev/sensors/pressN | XXXXX (Pa) | - |
| Servo | /dev/motors/servoN | angle | 0-180 |
| Stepper | /dev/motors/stepperN | position | steps |
| DC Motor | /dev/motors/dcN | speed% | -100 to 100 |

### Shell Commands

```bash
# List loaded drivers
drivers list

# Reload drivers from /etc/drivers/
drivers reload
```

## Libraries

Pynux includes 30+ libraries for embedded development:

### Core
| Library | Description |
|---------|-------------|
| `lib/io.py` | UART, console I/O |
| `lib/memory.py` | Heap allocator |
| `lib/string.py` | String operations |
| `lib/math.py` | Math functions, trig, sqrt |

### Data Structures
| Library | Description |
|---------|-------------|
| `lib/list.py` | Dynamic arrays |
| `lib/dict.py` | Hash maps |
| `lib/structures.py` | Stack, queue, ring buffer |
| `lib/algo.py` | Sorting, searching |

### Hardware
| Library | Description |
|---------|-------------|
| `lib/sensors.py` | Temp, accel, light, humid, pressure |
| `lib/motors.py` | Servo, stepper, DC motors |
| `lib/display.py` | HD44780 LCD, SSD1306 OLED, 7-segment |
| `lib/peripherals.py` | GPIO, SPI, I2C, ADC, PWM |

### Communication
| Library | Description |
|---------|-------------|
| `lib/onewire.py` | 1-Wire protocol (DS18B20) |
| `lib/canbus.py` | CAN bus messaging |
| `lib/json.py` | JSON parser |
| `lib/encoding.py` | Base64, hex encoding |

### Control Systems
| Library | Description |
|---------|-------------|
| `lib/pid.py` | PID controller |
| `lib/filters.py` | Low-pass, Kalman, moving average |
| `lib/fsm.py` | Finite state machine |

### System
| Library | Description |
|---------|-------------|
| `lib/rtc.py` | Real-time clock |
| `lib/watchdog.py` | Watchdog timer |
| `lib/eeprom.py` | EEPROM storage |
| `lib/logging.py` | Log levels, output |
| `lib/events.py` | Event queue |

## Target Hardware

| Platform | Status | Notes |
|----------|--------|-------|
| QEMU mps2-an385 | Primary | Cortex-M3, development |
| RP2040 (Pico) | Target | $4, huge community |
| RP2350 (Pico 2) | Future | RISC-V option |

## Project Structure

```
compiler/       # Python 3.10+ compiler (runs on host)
runtime/        # ARM assembly startup code
kernel/         # Kernel, RAMFS, timer, devfs
lib/            # 30+ libraries (sensors, motors, display, etc.)
programs/       # User programs (main.py runs at boot)
tests/          # Integration tests (expect scripts)
vtnext/         # Graphical terminal renderer (pygame)
```

## Building

```bash
# Requirements
sudo apt install gcc-arm-none-eabi qemu-system-arm python3-pygame

# Build
./build.sh

# Run (text mode)
./boot_vm.sh --shell

# Run (graphical mode)
./boot_vm.sh
```

## Memory

- 16KB heap (bump allocator)
- ~230KB code
- 512 bytes max file size
- RAMFS for files

## Ideas for Future

- **Network stack** - lwIP for TCP/IP on RP2040 W
- **USB support** - Mass storage, HID
- **Bluetooth** - BLE for RP2040 W
- **Flash filesystem** - LittleFS for persistent storage
- **Multitasking** - Cooperative scheduler with priorities
- **Package manager** - Install libraries from network
- **Remote debugging** - GDB stub over serial

## License

GPL-3.0 - See [LICENSE](LICENSE)
