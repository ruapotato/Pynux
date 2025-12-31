# Pynux Device Filesystem
#
# Provides /dev/ device files with read/write handlers.
# Supports driver auto-loading from /etc/drivers/*.conf

from lib.memory import alloc, free, memset, memcpy
from lib.string import strcmp, strcpy, strlen, strcat, atoi, itoa, isdigit
from lib.io import print_str, print_int, print_newline
from kernel.ramfs import ramfs_create, ramfs_lookup, ramfs_read, ramfs_write
from kernel.ramfs import ramfs_readdir, ramfs_exists, ramfs_size
from lib.sensors import sensors_init_all, sensors_seed, sensors_enable_noise
from lib.sensors import temp_init, temp_read, temp_set_base
from lib.sensors import accel_init, accel_read_x, accel_read_y, accel_read_z
from lib.sensors import light_init, light_read, light_set_base
from lib.sensors import humid_init, humid_read
from lib.sensors import press_init, press_read
from lib.motors import servo_init, servo_set_angle, servo_get_angle
from lib.motors import stepper_init, stepper_steps, stepper_get_position
from lib.motors import dc_init, dc_set_speed, dc_get_speed, dc_brake

# ============================================================================
# Device Registry
# ============================================================================

# Device types
DEV_NONE: int32 = 0
DEV_GPIO: int32 = 1
DEV_TEMP: int32 = 2
DEV_ACCEL: int32 = 3
DEV_LIGHT: int32 = 4
DEV_HUMID: int32 = 5
DEV_PRESS: int32 = 6
DEV_SERVO: int32 = 7
DEV_STEPPER: int32 = 8
DEV_DC: int32 = 9
DEV_ADC: int32 = 10
DEV_PWM: int32 = 11

# Maximum devices
MAX_DEVICES: int32 = 32

# Device registry arrays
dev_types: Array[32, int32]       # Device type (DEV_*)
dev_ids: Array[32, int32]         # Hardware ID (e.g., servo 0, gpio 5)
dev_pins: Array[32, int32]        # Primary pin number
dev_pin2: Array[32, int32]        # Secondary pin (for motors with 2 pins)
dev_pin3: Array[32, int32]        # Third pin (PWM pin for DC motors)
dev_names: Array[32, Array[16, char]]  # Device name (e.g., "temp0", "servo1")
dev_paths: Array[32, Array[32, char]]  # Full path (e.g., "/dev/sensors/temp0")
dev_count: int32 = 0

# GPIO state (8 pins for now)
gpio_states: Array[8, int32]      # 0=low, 1=high
gpio_modes: Array[8, int32]       # 0=input, 1=output

# Response buffer for device reads
dev_response: Array[64, char]

# ============================================================================
# Device Operations
# ============================================================================

def dev_read_gpio(id: int32) -> Ptr[char]:
    """Read GPIO pin state."""
    if id < 0 or id >= 8:
        strcpy(&dev_response[0], "error")
        return &dev_response[0]

    if gpio_states[id] == 0:
        strcpy(&dev_response[0], "0")
    else:
        strcpy(&dev_response[0], "1")
    return &dev_response[0]

def dev_write_gpio(id: int32, value: Ptr[char]) -> int32:
    """Write GPIO pin state."""
    if id < 0 or id >= 8:
        return -1

    gpio_modes[id] = 1  # Set to output

    if value[0] == '1' or value[0] == 'h' or value[0] == 'H':
        gpio_states[id] = 1
    else:
        gpio_states[id] = 0
    return 0

def dev_read_temp(id: int32) -> Ptr[char]:
    """Read temperature sensor."""
    t: int32 = temp_read()
    # Format as XX.XX
    whole: int32 = t / 100
    frac: int32 = t % 100
    if frac < 0:
        frac = -frac

    itoa(whole, &dev_response[0])
    len: int32 = strlen(&dev_response[0])
    dev_response[len] = '.'
    if frac < 10:
        dev_response[len + 1] = '0'
        itoa(frac, &dev_response[len + 2])
    else:
        itoa(frac, &dev_response[len + 1])
    return &dev_response[0]

def dev_read_accel(id: int32) -> Ptr[char]:
    """Read accelerometer (X Y Z in mg)."""
    x: int32 = accel_read_x()
    y: int32 = accel_read_y()
    z: int32 = accel_read_z()

    itoa(x, &dev_response[0])
    len: int32 = strlen(&dev_response[0])
    dev_response[len] = ' '
    itoa(y, &dev_response[len + 1])
    len = strlen(&dev_response[0])
    dev_response[len] = ' '
    itoa(z, &dev_response[len + 1])
    return &dev_response[0]

def dev_read_light(id: int32) -> Ptr[char]:
    """Read light sensor (0-1023)."""
    v: int32 = light_read()
    itoa(v, &dev_response[0])
    return &dev_response[0]

def dev_read_humid(id: int32) -> Ptr[char]:
    """Read humidity sensor (X.X %)."""
    h: int32 = humid_read()
    whole: int32 = h / 10
    frac: int32 = h % 10

    itoa(whole, &dev_response[0])
    len: int32 = strlen(&dev_response[0])
    dev_response[len] = '.'
    itoa(frac, &dev_response[len + 1])
    return &dev_response[0]

def dev_read_press(id: int32) -> Ptr[char]:
    """Read pressure sensor (hPa)."""
    p: int32 = press_read()
    itoa(p / 100, &dev_response[0])
    return &dev_response[0]

def dev_read_servo(id: int32) -> Ptr[char]:
    """Read servo angle."""
    angle: int32 = servo_get_angle(id)
    itoa(angle, &dev_response[0])
    return &dev_response[0]

def dev_write_servo(id: int32, value: Ptr[char]) -> int32:
    """Write servo angle (0-180)."""
    angle: int32 = atoi(value)
    if angle < 0:
        angle = 0
    if angle > 180:
        angle = 180
    servo_set_angle(id, angle)
    return 0

def dev_read_stepper(id: int32) -> Ptr[char]:
    """Read stepper position."""
    pos: int32 = stepper_get_position(id)
    itoa(pos, &dev_response[0])
    return &dev_response[0]

def dev_write_stepper(id: int32, value: Ptr[char]) -> int32:
    """Write stepper steps (positive or negative)."""
    steps: int32 = atoi(value)
    stepper_steps(id, steps)
    return 0

def dev_read_dc(id: int32) -> Ptr[char]:
    """Read DC motor speed."""
    speed: int32 = dc_get_speed(id)
    itoa(speed, &dev_response[0])
    return &dev_response[0]

def dev_write_dc(id: int32, value: Ptr[char]) -> int32:
    """Write DC motor speed (-100 to 100) or 'brake'."""
    if value[0] == 'b' or value[0] == 'B':
        dc_brake(id)
        return 0

    speed: int32 = atoi(value)
    if speed < -100:
        speed = -100
    if speed > 100:
        speed = 100
    dc_set_speed(id, speed)
    return 0

def dev_read_adc(id: int32) -> Ptr[char]:
    """Read ADC value (simulated, 0-4095)."""
    # Simulate ADC based on GPIO state
    v: int32 = 2048
    if id < 8:
        v = gpio_states[id] * 4095
    itoa(v, &dev_response[0])
    return &dev_response[0]

def dev_write_pwm(id: int32, value: Ptr[char]) -> int32:
    """Write PWM duty cycle (0-255)."""
    # Simulated - would control PWM hardware
    return 0

# ============================================================================
# Device Read/Write Dispatch
# ============================================================================

def devfs_read(dev_idx: int32) -> Ptr[char]:
    """Read from a device by registry index."""
    if dev_idx < 0 or dev_idx >= dev_count:
        strcpy(&dev_response[0], "error")
        return &dev_response[0]

    dtype: int32 = dev_types[dev_idx]
    id: int32 = dev_ids[dev_idx]

    if dtype == DEV_GPIO:
        return dev_read_gpio(id)
    elif dtype == DEV_TEMP:
        return dev_read_temp(id)
    elif dtype == DEV_ACCEL:
        return dev_read_accel(id)
    elif dtype == DEV_LIGHT:
        return dev_read_light(id)
    elif dtype == DEV_HUMID:
        return dev_read_humid(id)
    elif dtype == DEV_PRESS:
        return dev_read_press(id)
    elif dtype == DEV_SERVO:
        return dev_read_servo(id)
    elif dtype == DEV_STEPPER:
        return dev_read_stepper(id)
    elif dtype == DEV_DC:
        return dev_read_dc(id)
    elif dtype == DEV_ADC:
        return dev_read_adc(id)
    else:
        strcpy(&dev_response[0], "error")
        return &dev_response[0]

def devfs_write(dev_idx: int32, value: Ptr[char]) -> int32:
    """Write to a device by registry index."""
    if dev_idx < 0 or dev_idx >= dev_count:
        return -1

    dtype: int32 = dev_types[dev_idx]
    id: int32 = dev_ids[dev_idx]

    if dtype == DEV_GPIO:
        return dev_write_gpio(id, value)
    elif dtype == DEV_SERVO:
        return dev_write_servo(id, value)
    elif dtype == DEV_STEPPER:
        return dev_write_stepper(id, value)
    elif dtype == DEV_DC:
        return dev_write_dc(id, value)
    elif dtype == DEV_PWM:
        return dev_write_pwm(id, value)
    else:
        return -1  # Read-only device

# ============================================================================
# Device Registration
# ============================================================================

def devfs_register(dtype: int32, id: int32, pin: int32, name: Ptr[char]) -> int32:
    """Register a device and create /dev/ entry."""
    global dev_count

    if dev_count >= MAX_DEVICES:
        return -1

    idx: int32 = dev_count
    dev_types[idx] = dtype
    dev_ids[idx] = id
    dev_pins[idx] = pin
    dev_pin2[idx] = -1
    dev_pin3[idx] = -1

    # Copy name
    strcpy(&dev_names[idx][0], name)

    # Build path based on type
    if dtype == DEV_GPIO:
        strcpy(&dev_paths[idx][0], "/dev/gpio/")
    elif dtype == DEV_TEMP or dtype == DEV_ACCEL or dtype == DEV_LIGHT or dtype == DEV_HUMID or dtype == DEV_PRESS:
        strcpy(&dev_paths[idx][0], "/dev/sensors/")
    elif dtype == DEV_SERVO or dtype == DEV_STEPPER or dtype == DEV_DC:
        strcpy(&dev_paths[idx][0], "/dev/motors/")
    elif dtype == DEV_ADC:
        strcpy(&dev_paths[idx][0], "/dev/adc/")
    elif dtype == DEV_PWM:
        strcpy(&dev_paths[idx][0], "/dev/pwm/")
    else:
        strcpy(&dev_paths[idx][0], "/dev/")

    strcat(&dev_paths[idx][0], name)

    # Initialize hardware based on type
    if dtype == DEV_SERVO:
        servo_init(id)
    elif dtype == DEV_STEPPER:
        stepper_init(id, 200)  # Default 200 steps/rev
    elif dtype == DEV_DC:
        dc_init(id)
    elif dtype == DEV_TEMP:
        temp_init()
    elif dtype == DEV_ACCEL:
        accel_init()
    elif dtype == DEV_LIGHT:
        light_init()
    elif dtype == DEV_HUMID:
        humid_init()
    elif dtype == DEV_PRESS:
        press_init()

    dev_count = dev_count + 1
    return idx

# ============================================================================
# Device Lookup
# ============================================================================

def devfs_find_by_path(path: Ptr[char]) -> int32:
    """Find device index by path."""
    i: int32 = 0
    while i < dev_count:
        if strcmp(&dev_paths[i][0], path) == 0:
            return i
        i = i + 1
    return -1

def devfs_find_by_name(name: Ptr[char]) -> int32:
    """Find device index by name."""
    i: int32 = 0
    while i < dev_count:
        if strcmp(&dev_names[i][0], name) == 0:
            return i
        i = i + 1
    return -1

# ============================================================================
# Config File Parsing
# ============================================================================

# Config parsing buffers
_cfg_key: Array[32, char]
_cfg_val: Array[64, char]
_cfg_line: Array[128, char]
_cfg_data: Array[512, uint8]

def _parse_config_line(line: Ptr[char]) -> bool:
    """Parse a config line into key/value. Returns True if valid."""
    # Skip whitespace
    i: int32 = 0
    while line[i] == ' ' or line[i] == '\t':
        i = i + 1

    # Skip comments and empty lines
    if line[i] == '#' or line[i] == '\0' or line[i] == '\n':
        return False

    # Read key
    k: int32 = 0
    while line[i] != '=' and line[i] != '\0' and k < 31:
        _cfg_key[k] = line[i]
        k = k + 1
        i = i + 1
    _cfg_key[k] = '\0'

    if line[i] != '=':
        return False
    i = i + 1

    # Read value
    k = 0
    while line[i] != '\0' and line[i] != '\n' and line[i] != '\r' and k < 63:
        _cfg_val[k] = line[i]
        k = k + 1
        i = i + 1
    _cfg_val[k] = '\0'

    return True

def devfs_load_config(path: Ptr[char]) -> int32:
    """Load a driver config file and register the device."""
    # Read config file
    size: int32 = ramfs_size(path)
    if size <= 0 or size > 500:
        return -1

    read_count: int32 = ramfs_read(path, &_cfg_data[0], 500)
    if read_count <= 0:
        return -1

    # Parse variables
    cfg_type: int32 = DEV_NONE
    cfg_id: int32 = 0
    cfg_pin: int32 = 0
    cfg_name: Array[16, char]
    cfg_name[0] = '\0'

    # Process line by line
    line_start: int32 = 0
    i: int32 = 0
    while i <= read_count:
        if i == read_count or _cfg_data[i] == '\n':
            # Copy line
            line_len: int32 = i - line_start
            j: int32 = 0
            while j < line_len and j < 127:
                _cfg_line[j] = cast[char](_cfg_data[line_start + j])
                j = j + 1
            _cfg_line[j] = '\0'
            line_start = i + 1

            # Parse line
            if _parse_config_line(&_cfg_line[0]):
                if strcmp(&_cfg_key[0], "type") == 0:
                    if strcmp(&_cfg_val[0], "gpio") == 0:
                        cfg_type = DEV_GPIO
                    elif strcmp(&_cfg_val[0], "temp") == 0 or strcmp(&_cfg_val[0], "ds18b20") == 0:
                        cfg_type = DEV_TEMP
                    elif strcmp(&_cfg_val[0], "accel") == 0:
                        cfg_type = DEV_ACCEL
                    elif strcmp(&_cfg_val[0], "light") == 0:
                        cfg_type = DEV_LIGHT
                    elif strcmp(&_cfg_val[0], "humid") == 0 or strcmp(&_cfg_val[0], "dht") == 0:
                        cfg_type = DEV_HUMID
                    elif strcmp(&_cfg_val[0], "press") == 0 or strcmp(&_cfg_val[0], "bmp") == 0:
                        cfg_type = DEV_PRESS
                    elif strcmp(&_cfg_val[0], "servo") == 0:
                        cfg_type = DEV_SERVO
                    elif strcmp(&_cfg_val[0], "stepper") == 0:
                        cfg_type = DEV_STEPPER
                    elif strcmp(&_cfg_val[0], "dc") == 0:
                        cfg_type = DEV_DC
                    elif strcmp(&_cfg_val[0], "adc") == 0:
                        cfg_type = DEV_ADC
                    elif strcmp(&_cfg_val[0], "pwm") == 0:
                        cfg_type = DEV_PWM
                elif strcmp(&_cfg_key[0], "id") == 0:
                    cfg_id = atoi(&_cfg_val[0])
                elif strcmp(&_cfg_key[0], "pin") == 0:
                    cfg_pin = atoi(&_cfg_val[0])
                elif strcmp(&_cfg_key[0], "name") == 0:
                    strcpy(&cfg_name[0], &_cfg_val[0])
        i = i + 1

    # Generate default name if not specified
    if cfg_name[0] == '\0':
        if cfg_type == DEV_GPIO:
            strcpy(&cfg_name[0], "gpio")
        elif cfg_type == DEV_TEMP:
            strcpy(&cfg_name[0], "temp")
        elif cfg_type == DEV_ACCEL:
            strcpy(&cfg_name[0], "accel")
        elif cfg_type == DEV_LIGHT:
            strcpy(&cfg_name[0], "light")
        elif cfg_type == DEV_HUMID:
            strcpy(&cfg_name[0], "humid")
        elif cfg_type == DEV_PRESS:
            strcpy(&cfg_name[0], "press")
        elif cfg_type == DEV_SERVO:
            strcpy(&cfg_name[0], "servo")
        elif cfg_type == DEV_STEPPER:
            strcpy(&cfg_name[0], "stepper")
        elif cfg_type == DEV_DC:
            strcpy(&cfg_name[0], "dc")
        elif cfg_type == DEV_ADC:
            strcpy(&cfg_name[0], "adc")
        elif cfg_type == DEV_PWM:
            strcpy(&cfg_name[0], "pwm")

        # Append ID
        num_buf: Array[8, char]
        itoa(cfg_id, &num_buf[0])
        strcat(&cfg_name[0], &num_buf[0])

    if cfg_type == DEV_NONE:
        return -1

    return devfs_register(cfg_type, cfg_id, cfg_pin, &cfg_name[0])

# ============================================================================
# Driver Directory Scanning
# ============================================================================

_scan_name: Array[64, char]
_scan_path: Array[128, char]

def devfs_scan_drivers():
    """Scan /etc/drivers/ and load all .conf files."""
    # Ensure /etc/drivers exists
    if not ramfs_exists("/etc/drivers"):
        ramfs_create("/etc/drivers", True)
        return

    # Read directory entries
    idx: int32 = 0
    while True:
        result: int32 = ramfs_readdir("/etc/drivers", idx, &_scan_name[0], 63)
        if result < 0:
            break

        # Check if it ends with .conf
        name_len: int32 = strlen(&_scan_name[0])
        if name_len > 5:
            # Check extension
            if _scan_name[name_len - 5] == '.' and _scan_name[name_len - 4] == 'c':
                # Build full path
                strcpy(&_scan_path[0], "/etc/drivers/")
                strcat(&_scan_path[0], &_scan_name[0])

                # Load config
                devfs_load_config(&_scan_path[0])

        idx = idx + 1

# ============================================================================
# Initialization
# ============================================================================

def devfs_init():
    """Initialize device filesystem."""
    global dev_count

    # Clear device registry
    dev_count = 0
    i: int32 = 0
    while i < MAX_DEVICES:
        dev_types[i] = DEV_NONE
        i = i + 1

    # Initialize GPIO states
    i = 0
    while i < 8:
        gpio_states[i] = 0
        gpio_modes[i] = 0  # Input by default
        i = i + 1

    # Initialize sensors
    sensors_seed(12345)
    sensors_enable_noise(True)
    sensors_init_all()

    # Create /dev directories
    if not ramfs_exists("/dev"):
        ramfs_create("/dev", True)
    if not ramfs_exists("/dev/gpio"):
        ramfs_create("/dev/gpio", True)
    if not ramfs_exists("/dev/sensors"):
        ramfs_create("/dev/sensors", True)
    if not ramfs_exists("/dev/motors"):
        ramfs_create("/dev/motors", True)
    if not ramfs_exists("/dev/adc"):
        ramfs_create("/dev/adc", True)
    if not ramfs_exists("/dev/pwm"):
        ramfs_create("/dev/pwm", True)

    # Create /etc/drivers if needed
    if not ramfs_exists("/etc/drivers"):
        ramfs_create("/etc/drivers", True)

    # Register default demo devices for emulator testing
    # GPIO pins
    devfs_register(DEV_GPIO, 0, 0, "pin0")
    devfs_register(DEV_GPIO, 1, 1, "pin1")
    devfs_register(DEV_GPIO, 2, 2, "pin2")
    devfs_register(DEV_GPIO, 3, 3, "pin3")
    # Sensors
    devfs_register(DEV_TEMP, 0, 4, "temp0")
    devfs_register(DEV_ACCEL, 0, 5, "accel0")
    devfs_register(DEV_LIGHT, 0, 6, "light0")
    devfs_register(DEV_HUMID, 0, 7, "humid0")
    devfs_register(DEV_PRESS, 0, 8, "press0")
    # Motors
    devfs_register(DEV_SERVO, 0, 9, "servo0")
    devfs_register(DEV_STEPPER, 0, 10, "stepper0")
    devfs_register(DEV_DC, 0, 11, "dc0")

    # Scan and load additional drivers from config
    devfs_scan_drivers()

# ============================================================================
# Proc Interface
# ============================================================================

def devfs_list_drivers():
    """Print list of loaded drivers."""
    print_str("Loaded drivers:\n")

    if dev_count == 0:
        print_str("  (none)\n")
        return

    i: int32 = 0
    while i < dev_count:
        print_str("  ")
        print_str(&dev_paths[i][0])
        print_str(" (pin ")
        print_int(dev_pins[i])
        print_str(")\n")
        i = i + 1

def devfs_get_count() -> int32:
    """Get number of registered devices."""
    return dev_count

def devfs_get_path(idx: int32) -> Ptr[char]:
    """Get device path by index."""
    if idx < 0 or idx >= dev_count:
        return cast[Ptr[char]](0)
    return &dev_paths[idx][0]

def devfs_get_type(idx: int32) -> int32:
    """Get device type by index."""
    if idx < 0 or idx >= dev_count:
        return DEV_NONE
    return dev_types[idx]
