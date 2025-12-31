# Pynux Sensors Library
#
# Emulated sensor drivers for QEMU ARM Cortex-M3.
# Simulates real hardware sensor behavior with configurable
# random variations for realistic testing.
#
# Sensors included:
#   - Temperature (DS18B20/TMP36 style)
#   - Accelerometer (3-axis)
#   - Light sensor (LDR/photoresistor)
#   - Humidity sensor
#   - Pressure sensor (barometric)

from lib.math import rand, rand_range, srand, abs_int, clamp

# ============================================================================
# Simulation Configuration
# ============================================================================

# Global simulation tick counter (incremented by update functions)
_sim_tick: int32 = 0

# Master random variation enable
_sim_noise_enabled: bool = True

# Set simulation noise on/off
def sensors_enable_noise(enabled: bool):
    """Enable or disable random noise in sensor readings."""
    global _sim_noise_enabled
    _sim_noise_enabled = enabled

# Seed random for all sensors
def sensors_seed(seed: int32):
    """Set random seed for sensor simulation."""
    srand(seed)

# ============================================================================
# Temperature Sensor (DS18B20 / TMP36 style)
# ============================================================================
# Emulates a digital temperature sensor
# Returns temperature in centidegrees (value * 100) to avoid floating point
# e.g., 2350 = 23.50 degrees Celsius

# Temperature sensor state
_temp_initialized: bool = False
_temp_base: int32 = 2200        # Base temperature: 22.00 C
_temp_variance: int32 = 50      # Max variance: +/- 0.50 C
_temp_drift: int32 = 0          # Slow drift value
_temp_drift_rate: int32 = 2     # How fast drift changes
_temp_last_raw: int32 = 0       # Last raw ADC-like value

# Temperature sensor configuration
TEMP_MIN: int32 = -4000         # -40.00 C minimum
TEMP_MAX: int32 = 12500         # 125.00 C maximum
TEMP_RESOLUTION: int32 = 6      # 0.06 C resolution (like DS18B20)

def temp_init():
    """Initialize temperature sensor."""
    global _temp_initialized, _temp_drift, _temp_last_raw
    _temp_initialized = True
    _temp_drift = 0
    _temp_last_raw = 0

def temp_set_base(base_centidegrees: int32):
    """Set base temperature for simulation (in centidegrees)."""
    global _temp_base
    _temp_base = clamp(base_centidegrees, TEMP_MIN, TEMP_MAX)

def temp_set_variance(variance: int32):
    """Set temperature variance for noise (in centidegrees)."""
    global _temp_variance
    _temp_variance = abs_int(variance)

def temp_read() -> int32:
    """Read temperature in centidegrees (e.g., 2350 = 23.50 C).

    Returns:
        Temperature in centidegrees Celsius
    """
    global _temp_drift, _temp_last_raw, _sim_tick

    if not _temp_initialized:
        temp_init()

    # Update drift slowly
    _sim_tick = _sim_tick + 1
    if (_sim_tick % 10) == 0:
        drift_change: int32 = rand_range(-_temp_drift_rate, _temp_drift_rate)
        _temp_drift = clamp(_temp_drift + drift_change, -100, 100)

    # Calculate temperature with noise
    temp: int32 = _temp_base + _temp_drift

    if _sim_noise_enabled:
        noise: int32 = rand_range(-_temp_variance, _temp_variance)
        temp = temp + noise

    # Clamp to valid range
    temp = clamp(temp, TEMP_MIN, TEMP_MAX)

    # Round to resolution
    temp = (temp / TEMP_RESOLUTION) * TEMP_RESOLUTION

    # Store raw value (12-bit ADC simulation: 0-4095)
    # Map -40C to 125C to 0-4095
    _temp_last_raw = ((temp - TEMP_MIN) * 4095) / (TEMP_MAX - TEMP_MIN)

    return temp

def temp_get_raw() -> int32:
    """Get raw ADC value from last temperature read (0-4095).

    Returns:
        12-bit ADC value
    """
    return _temp_last_raw

def temp_to_fahrenheit(centidegrees: int32) -> int32:
    """Convert centidegrees Celsius to centidegrees Fahrenheit.

    Args:
        centidegrees: Temperature in centidegrees C

    Returns:
        Temperature in centidegrees F
    """
    # F = C * 9/5 + 32
    # For centidegrees: F*100 = (C*100) * 9/5 + 3200
    return (centidegrees * 9) / 5 + 3200

# ============================================================================
# Accelerometer (3-axis, like ADXL345 / MPU6050)
# ============================================================================
# Returns acceleration in milli-g (mg)
# 1000 mg = 1g = 9.8 m/s^2
# At rest, Z axis should read ~1000 mg (gravity)

# Accelerometer state
_accel_initialized: bool = False
_accel_x_base: int32 = 0        # Base X (at rest: 0)
_accel_y_base: int32 = 0        # Base Y (at rest: 0)
_accel_z_base: int32 = 1000     # Base Z (at rest: 1g = 1000mg)
_accel_variance: int32 = 20     # Noise variance in mg
_accel_x_raw: int32 = 0
_accel_y_raw: int32 = 0
_accel_z_raw: int32 = 0

# Accelerometer configuration
ACCEL_RANGE: int32 = 16000      # +/- 16g range in mg
ACCEL_RESOLUTION: int32 = 4     # 4mg per LSB (like ADXL345 at +/-16g)

def accel_init():
    """Initialize accelerometer."""
    global _accel_initialized
    _accel_initialized = True

def accel_set_base(x: int32, y: int32, z: int32):
    """Set base acceleration values for simulation (in mg).

    Args:
        x: X-axis base acceleration in mg
        y: Y-axis base acceleration in mg
        z: Z-axis base acceleration in mg (typically 1000 for gravity)
    """
    global _accel_x_base, _accel_y_base, _accel_z_base
    _accel_x_base = clamp(x, -ACCEL_RANGE, ACCEL_RANGE)
    _accel_y_base = clamp(y, -ACCEL_RANGE, ACCEL_RANGE)
    _accel_z_base = clamp(z, -ACCEL_RANGE, ACCEL_RANGE)

def accel_set_variance(variance: int32):
    """Set noise variance for accelerometer (in mg)."""
    global _accel_variance
    _accel_variance = abs_int(variance)

def accel_read_x() -> int32:
    """Read X-axis acceleration in milli-g.

    Returns:
        X acceleration in mg
    """
    global _accel_x_raw

    if not _accel_initialized:
        accel_init()

    x: int32 = _accel_x_base
    if _sim_noise_enabled:
        x = x + rand_range(-_accel_variance, _accel_variance)

    x = clamp(x, -ACCEL_RANGE, ACCEL_RANGE)
    x = (x / ACCEL_RESOLUTION) * ACCEL_RESOLUTION

    # Raw: 16-bit signed, map to 0-65535
    _accel_x_raw = ((x + ACCEL_RANGE) * 65535) / (2 * ACCEL_RANGE)

    return x

def accel_read_y() -> int32:
    """Read Y-axis acceleration in milli-g.

    Returns:
        Y acceleration in mg
    """
    global _accel_y_raw

    if not _accel_initialized:
        accel_init()

    y: int32 = _accel_y_base
    if _sim_noise_enabled:
        y = y + rand_range(-_accel_variance, _accel_variance)

    y = clamp(y, -ACCEL_RANGE, ACCEL_RANGE)
    y = (y / ACCEL_RESOLUTION) * ACCEL_RESOLUTION

    _accel_y_raw = ((y + ACCEL_RANGE) * 65535) / (2 * ACCEL_RANGE)

    return y

def accel_read_z() -> int32:
    """Read Z-axis acceleration in milli-g.

    Returns:
        Z acceleration in mg (typically ~1000 at rest due to gravity)
    """
    global _accel_z_raw

    if not _accel_initialized:
        accel_init()

    z: int32 = _accel_z_base
    if _sim_noise_enabled:
        z = z + rand_range(-_accel_variance, _accel_variance)

    z = clamp(z, -ACCEL_RANGE, ACCEL_RANGE)
    z = (z / ACCEL_RESOLUTION) * ACCEL_RESOLUTION

    _accel_z_raw = ((z + ACCEL_RANGE) * 65535) / (2 * ACCEL_RANGE)

    return z

def accel_read(x_out: Ptr[int32], y_out: Ptr[int32], z_out: Ptr[int32]):
    """Read all three accelerometer axes at once.

    Args:
        x_out: Pointer to store X value
        y_out: Pointer to store Y value
        z_out: Pointer to store Z value
    """
    x_out[0] = accel_read_x()
    y_out[0] = accel_read_y()
    z_out[0] = accel_read_z()

def accel_get_raw_x() -> int32:
    """Get raw X-axis value from last read (0-65535)."""
    return _accel_x_raw

def accel_get_raw_y() -> int32:
    """Get raw Y-axis value from last read (0-65535)."""
    return _accel_y_raw

def accel_get_raw_z() -> int32:
    """Get raw Z-axis value from last read (0-65535)."""
    return _accel_z_raw

# ============================================================================
# Light Sensor (LDR / Photoresistor style)
# ============================================================================
# Returns light level as 0-1023 (10-bit ADC)
# 0 = complete darkness, 1023 = bright light

# Light sensor state
_light_initialized: bool = False
_light_base: int32 = 512        # Base light level (medium)
_light_variance: int32 = 10     # Noise variance
_light_last_raw: int32 = 0

def light_init():
    """Initialize light sensor."""
    global _light_initialized
    _light_initialized = True

def light_set_base(level: int32):
    """Set base light level for simulation (0-1023)."""
    global _light_base
    _light_base = clamp(level, 0, 1023)

def light_set_variance(variance: int32):
    """Set noise variance for light sensor."""
    global _light_variance
    _light_variance = abs_int(variance)

def light_read() -> int32:
    """Read light level (0-1023).

    Returns:
        Light level (0=dark, 1023=bright)
    """
    global _light_last_raw

    if not _light_initialized:
        light_init()

    level: int32 = _light_base
    if _sim_noise_enabled:
        level = level + rand_range(-_light_variance, _light_variance)

    level = clamp(level, 0, 1023)
    _light_last_raw = level

    return level

def light_get_raw() -> int32:
    """Get raw ADC value from last light read (0-1023)."""
    return _light_last_raw

def light_to_lux(raw: int32) -> int32:
    """Convert raw light value to approximate lux.

    This is a rough approximation assuming typical LDR response.

    Args:
        raw: Raw light value (0-1023)

    Returns:
        Approximate lux value
    """
    # Non-linear mapping: 0->0, 512->100, 1023->10000 (exponential-ish)
    if raw < 100:
        return raw / 10
    elif raw < 512:
        return 10 + ((raw - 100) * 90) / 412
    else:
        return 100 + ((raw - 512) * 9900) / 511

# ============================================================================
# Humidity Sensor (DHT11/DHT22 style)
# ============================================================================
# Returns relative humidity as percentage * 10 (0-1000 = 0.0-100.0%)
# e.g., 650 = 65.0% RH

# Humidity sensor state
_humid_initialized: bool = False
_humid_base: int32 = 500        # Base: 50.0% RH
_humid_variance: int32 = 20     # Noise: +/- 2.0%
_humid_last_raw: int32 = 0

def humid_init():
    """Initialize humidity sensor."""
    global _humid_initialized
    _humid_initialized = True

def humid_set_base(rh_x10: int32):
    """Set base humidity for simulation (0-1000 = 0.0-100.0% RH)."""
    global _humid_base
    _humid_base = clamp(rh_x10, 0, 1000)

def humid_set_variance(variance: int32):
    """Set noise variance for humidity sensor."""
    global _humid_variance
    _humid_variance = abs_int(variance)

def humid_read() -> int32:
    """Read humidity as percentage * 10 (e.g., 650 = 65.0% RH).

    Returns:
        Relative humidity * 10 (0-1000)
    """
    global _humid_last_raw

    if not _humid_initialized:
        humid_init()

    rh: int32 = _humid_base
    if _sim_noise_enabled:
        rh = rh + rand_range(-_humid_variance, _humid_variance)

    rh = clamp(rh, 0, 1000)
    _humid_last_raw = (rh * 255) / 1000  # 8-bit raw

    return rh

def humid_get_raw() -> int32:
    """Get raw sensor value from last humidity read (0-255)."""
    return _humid_last_raw

def humid_read_percent() -> int32:
    """Read humidity as integer percentage (0-100).

    Returns:
        Relative humidity percentage (0-100)
    """
    return humid_read() / 10

# ============================================================================
# Pressure Sensor (BMP180/BMP280 style)
# ============================================================================
# Returns pressure in Pascals (Pa)
# Standard atmosphere: 101325 Pa = 1013.25 hPa = 1 atm
# Also provides altitude estimation

# Pressure sensor state
_press_initialized: bool = False
_press_base: int32 = 101325     # Base: standard atmosphere in Pa
_press_variance: int32 = 50     # Noise: +/- 50 Pa (0.5 hPa)
_press_last_raw: int32 = 0

# Pressure range (typical for barometric sensors)
PRESS_MIN: int32 = 30000        # ~300 hPa (very high altitude)
PRESS_MAX: int32 = 110000       # ~1100 hPa (below sea level)

def press_init():
    """Initialize pressure sensor."""
    global _press_initialized
    _press_initialized = True

def press_set_base(pascals: int32):
    """Set base pressure for simulation (in Pascals)."""
    global _press_base
    _press_base = clamp(pascals, PRESS_MIN, PRESS_MAX)

def press_set_variance(variance: int32):
    """Set noise variance for pressure sensor (in Pascals)."""
    global _press_variance
    _press_variance = abs_int(variance)

def press_read() -> int32:
    """Read pressure in Pascals.

    Returns:
        Pressure in Pascals (e.g., 101325 = 1 atm)
    """
    global _press_last_raw

    if not _press_initialized:
        press_init()

    p: int32 = _press_base
    if _sim_noise_enabled:
        p = p + rand_range(-_press_variance, _press_variance)

    p = clamp(p, PRESS_MIN, PRESS_MAX)

    # Raw: 24-bit value (like BMP280), scaled to 0-16777215
    _press_last_raw = ((p - PRESS_MIN) * 16777215) / (PRESS_MAX - PRESS_MIN)

    return p

def press_get_raw() -> int32:
    """Get raw sensor value from last pressure read."""
    return _press_last_raw

def press_read_hpa() -> int32:
    """Read pressure in hectopascals (hPa/mbar) * 10.

    Returns:
        Pressure in hPa * 10 (e.g., 10132 = 1013.2 hPa)
    """
    return press_read() / 10

def press_to_altitude(pascals: int32) -> int32:
    """Estimate altitude from pressure reading.

    Uses simplified barometric formula.
    Assumes sea level pressure of 101325 Pa.

    Args:
        pascals: Pressure reading in Pascals

    Returns:
        Estimated altitude in meters
    """
    # Simplified formula: altitude ~= 44330 * (1 - (P/P0)^0.1903)
    # For integer math, we use a linear approximation:
    # altitude ~= (101325 - P) * 8 / 100
    # This is accurate to within ~5% for altitudes < 3000m
    diff: int32 = 101325 - pascals
    return (diff * 8) / 100

# ============================================================================
# Combined Sensor Update (for simulation tick)
# ============================================================================

def sensors_update():
    """Update all sensor simulations (call periodically).

    This function should be called regularly to update drift
    and other time-based simulation effects.
    """
    global _sim_tick
    _sim_tick = _sim_tick + 1

def sensors_get_tick() -> int32:
    """Get current simulation tick count."""
    return _sim_tick

# ============================================================================
# Sensor Status and Information
# ============================================================================

def temp_is_initialized() -> bool:
    """Check if temperature sensor is initialized."""
    return _temp_initialized

def accel_is_initialized() -> bool:
    """Check if accelerometer is initialized."""
    return _accel_initialized

def light_is_initialized() -> bool:
    """Check if light sensor is initialized."""
    return _light_initialized

def humid_is_initialized() -> bool:
    """Check if humidity sensor is initialized."""
    return _humid_initialized

def press_is_initialized() -> bool:
    """Check if pressure sensor is initialized."""
    return _press_initialized

# ============================================================================
# Convenience: Initialize All Sensors
# ============================================================================

def sensors_init_all():
    """Initialize all sensors at once."""
    temp_init()
    accel_init()
    light_init()
    humid_init()
    press_init()
