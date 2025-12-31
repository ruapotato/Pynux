# Pynux Signal Processing Filters Library
#
# Digital signal filters for bare-metal ARM microcontrollers.
# All filters use integer math (no floating point).
# Includes moving average, EMA, low/high pass, median, Kalman, and debounce.

from lib.memory import alloc, free

# ============================================================================
# Constants
# ============================================================================

# Fixed-point scale (16.16 format)
FILTER_FP_SHIFT: int32 = 16
FILTER_FP_ONE: int32 = 65536   # 1.0 in 16.16 fixed-point
FILTER_FP_HALF: int32 = 32768  # 0.5 in 16.16 fixed-point

# Maximum filter window sizes
FILTER_MAX_WINDOW: int32 = 64
FILTER_MAX_MEDIAN: int32 = 31  # Must be odd, reasonable limit

# ============================================================================
# Moving Average Filter
# ============================================================================
#
# Simple moving average over a configurable window.
# Good for smoothing noisy signals with constant group delay.
#
# Structure layout:
#   buffer: Ptr[int32]  - Circular buffer of samples (offset 0)
#   sum: int32          - Running sum for efficiency (offset 4)
#   index: int32        - Current write index (offset 8)
#   count: int32        - Number of samples added (offset 12)
#   size: int32         - Window size (offset 16)
# Total: 20 bytes

MA_BUFFER_OFFSET: int32 = 0
MA_SUM_OFFSET: int32 = 4
MA_INDEX_OFFSET: int32 = 8
MA_COUNT_OFFSET: int32 = 12
MA_SIZE_OFFSET: int32 = 16
MA_STRUCT_SIZE: int32 = 20

def ma_create(window_size: int32) -> Ptr[int32]:
    """Create a moving average filter.

    Args:
        window_size: Number of samples to average (2 to FILTER_MAX_WINDOW)

    Returns:
        Pointer to filter structure, or null on failure
    """
    if window_size < 2:
        window_size = 2
    if window_size > FILTER_MAX_WINDOW:
        window_size = FILTER_MAX_WINDOW

    # Allocate structure
    ma: Ptr[int32] = cast[Ptr[int32]](alloc(MA_STRUCT_SIZE))
    if cast[uint32](ma) == 0:
        return cast[Ptr[int32]](0)

    # Allocate buffer
    buffer: Ptr[int32] = cast[Ptr[int32]](alloc(window_size * 4))
    if cast[uint32](buffer) == 0:
        free(cast[Ptr[uint8]](ma))
        return cast[Ptr[int32]](0)

    # Initialize buffer to zero
    i: int32 = 0
    while i < window_size:
        buffer[i] = 0
        i = i + 1

    # Initialize structure
    ma[0] = cast[int32](buffer)
    ma[1] = 0           # sum
    ma[2] = 0           # index
    ma[3] = 0           # count
    ma[4] = window_size # size

    return ma

def ma_destroy(ma: Ptr[int32]):
    """Destroy moving average filter and free memory."""
    if cast[uint32](ma) == 0:
        return

    buffer: Ptr[int32] = cast[Ptr[int32]](ma[0])
    if cast[uint32](buffer) != 0:
        free(cast[Ptr[uint8]](buffer))

    free(cast[Ptr[uint8]](ma))

def ma_reset(ma: Ptr[int32]):
    """Reset filter to initial state."""
    buffer: Ptr[int32] = cast[Ptr[int32]](ma[0])
    size: int32 = ma[4]

    i: int32 = 0
    while i < size:
        buffer[i] = 0
        i = i + 1

    ma[1] = 0  # sum
    ma[2] = 0  # index
    ma[3] = 0  # count

def ma_update(ma: Ptr[int32], sample: int32) -> int32:
    """Add a new sample and return the filtered value.

    Args:
        ma: Pointer to filter structure
        sample: New input sample

    Returns:
        Moving average of samples in window
    """
    buffer: Ptr[int32] = cast[Ptr[int32]](ma[0])
    size: int32 = ma[4]
    index: int32 = ma[2]
    count: int32 = ma[3]

    # Subtract oldest sample from sum (if buffer is full)
    if count >= size:
        ma[1] = ma[1] - buffer[index]
    else:
        count = count + 1
        ma[3] = count

    # Add new sample
    buffer[index] = sample
    ma[1] = ma[1] + sample

    # Advance index
    index = index + 1
    if index >= size:
        index = 0
    ma[2] = index

    # Return average
    if count > 0:
        return ma[1] / count
    return 0

def ma_get_value(ma: Ptr[int32]) -> int32:
    """Get current filtered value without adding a sample."""
    count: int32 = ma[3]
    if count > 0:
        return ma[1] / count
    return 0

# ============================================================================
# Exponential Moving Average (EMA) Filter
# ============================================================================
#
# First-order IIR filter: y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
# Lower alpha = more smoothing, slower response.
#
# Structure layout:
#   value: int32        - Current filtered value (16.16 FP) (offset 0)
#   alpha: int32        - Filter coefficient (16.16 FP) (offset 4)
#   initialized: int32  - Has received first sample (offset 8)
# Total: 12 bytes

EMA_VALUE_OFFSET: int32 = 0
EMA_ALPHA_OFFSET: int32 = 4
EMA_INIT_OFFSET: int32 = 8
EMA_STRUCT_SIZE: int32 = 12

def ema_create(alpha: int32) -> Ptr[int32]:
    """Create an exponential moving average filter.

    Args:
        alpha: Smoothing factor in 16.16 fixed-point (0 to FP_ONE)
               Lower values = more smoothing
               Typical: 0.1 = 6554, 0.2 = 13107, 0.5 = 32768

    Returns:
        Pointer to filter structure, or null on failure
    """
    ema: Ptr[int32] = cast[Ptr[int32]](alloc(EMA_STRUCT_SIZE))
    if cast[uint32](ema) == 0:
        return cast[Ptr[int32]](0)

    # Clamp alpha
    if alpha < 0:
        alpha = 0
    if alpha > FILTER_FP_ONE:
        alpha = FILTER_FP_ONE

    ema[0] = 0      # value
    ema[1] = alpha  # alpha
    ema[2] = 0      # not initialized

    return ema

def ema_create_tc(time_constant: int32, sample_period: int32) -> Ptr[int32]:
    """Create EMA filter from time constant.

    Args:
        time_constant: Time constant in same units as sample_period
        sample_period: Sample period in same units

    Returns:
        Pointer to filter structure
    """
    # alpha = 1 - exp(-dt/tau) ~= dt/tau for small dt
    # In fixed-point: alpha = (sample_period * FP_ONE) / time_constant
    alpha: int32 = 0
    if time_constant > 0:
        alpha = (sample_period * FILTER_FP_ONE) / time_constant
        if alpha > FILTER_FP_ONE:
            alpha = FILTER_FP_ONE

    return ema_create(alpha)

def ema_destroy(ema: Ptr[int32]):
    """Destroy EMA filter and free memory."""
    if cast[uint32](ema) != 0:
        free(cast[Ptr[uint8]](ema))

def ema_reset(ema: Ptr[int32]):
    """Reset filter to initial state."""
    ema[0] = 0  # value
    ema[2] = 0  # not initialized

def ema_update(ema: Ptr[int32], sample: int32) -> int32:
    """Add a new sample and return the filtered value.

    Args:
        ema: Pointer to filter structure
        sample: New input sample

    Returns:
        Filtered output value
    """
    alpha: int32 = ema[1]

    if ema[2] == 0:
        # First sample, initialize directly
        ema[0] = sample << FILTER_FP_SHIFT
        ema[2] = 1
        return sample

    # y = alpha * x + (1 - alpha) * y_prev
    sample_fp: int32 = sample << FILTER_FP_SHIFT
    prev_fp: int32 = ema[0]

    # Use 8-bit shifts to avoid overflow
    new_term: int32 = (alpha >> 8) * (sample_fp >> 8)
    old_term: int32 = ((FILTER_FP_ONE - alpha) >> 8) * (prev_fp >> 8)
    result_fp: int32 = new_term + old_term

    ema[0] = result_fp

    return result_fp >> FILTER_FP_SHIFT

def ema_get_value(ema: Ptr[int32]) -> int32:
    """Get current filtered value without adding a sample."""
    return ema[0] >> FILTER_FP_SHIFT

def ema_set_alpha(ema: Ptr[int32], alpha: int32):
    """Set filter smoothing factor.

    Args:
        ema: Pointer to filter structure
        alpha: New smoothing factor (16.16 fixed-point)
    """
    if alpha < 0:
        alpha = 0
    if alpha > FILTER_FP_ONE:
        alpha = FILTER_FP_ONE
    ema[1] = alpha

# ============================================================================
# Low-Pass Filter (First Order IIR)
# ============================================================================
#
# Implements a simple RC low-pass filter approximation.
# Cutoff frequency determined by coefficient.
#
# Uses same structure as EMA (they're mathematically equivalent).

def lpf_create(cutoff_ratio: int32) -> Ptr[int32]:
    """Create a low-pass filter.

    Args:
        cutoff_ratio: Cutoff frequency / sample frequency (16.16 FP)
                      Range 0 to 0.5 (0 to 32768 in FP)
                      Lower = more filtering

    Returns:
        Pointer to filter structure
    """
    # Convert cutoff ratio to alpha
    # alpha ~= 2 * pi * cutoff_ratio (for small values)
    # Simplified: alpha = cutoff_ratio * 6 (approximate 2*pi)
    alpha: int32 = cutoff_ratio * 6
    if alpha > FILTER_FP_ONE:
        alpha = FILTER_FP_ONE

    return ema_create(alpha)

def lpf_destroy(lpf: Ptr[int32]):
    """Destroy low-pass filter."""
    ema_destroy(lpf)

def lpf_reset(lpf: Ptr[int32]):
    """Reset low-pass filter."""
    ema_reset(lpf)

def lpf_update(lpf: Ptr[int32], sample: int32) -> int32:
    """Update low-pass filter with new sample."""
    return ema_update(lpf, sample)

def lpf_get_value(lpf: Ptr[int32]) -> int32:
    """Get current low-pass filter output."""
    return ema_get_value(lpf)

# ============================================================================
# High-Pass Filter (First Order IIR)
# ============================================================================
#
# y[n] = alpha * (y[n-1] + x[n] - x[n-1])
# Removes DC offset and low-frequency components.
#
# Structure layout:
#   value: int32        - Current filtered value (16.16 FP) (offset 0)
#   alpha: int32        - Filter coefficient (16.16 FP) (offset 4)
#   prev_input: int32   - Previous input sample (offset 8)
#   initialized: int32  - Has received first sample (offset 12)
# Total: 16 bytes

HPF_VALUE_OFFSET: int32 = 0
HPF_ALPHA_OFFSET: int32 = 4
HPF_PREV_INPUT_OFFSET: int32 = 8
HPF_INIT_OFFSET: int32 = 12
HPF_STRUCT_SIZE: int32 = 16

def hpf_create(cutoff_ratio: int32) -> Ptr[int32]:
    """Create a high-pass filter.

    Args:
        cutoff_ratio: Cutoff frequency / sample frequency (16.16 FP)
                      Range 0 to 0.5 (0 to 32768 in FP)
                      Higher = more filtering of low frequencies

    Returns:
        Pointer to filter structure
    """
    hpf: Ptr[int32] = cast[Ptr[int32]](alloc(HPF_STRUCT_SIZE))
    if cast[uint32](hpf) == 0:
        return cast[Ptr[int32]](0)

    # alpha = 1 / (1 + 2*pi*cutoff_ratio) ~= 1 - 6*cutoff_ratio
    alpha: int32 = FILTER_FP_ONE - cutoff_ratio * 6
    if alpha < 0:
        alpha = 0

    hpf[0] = 0      # value
    hpf[1] = alpha  # alpha
    hpf[2] = 0      # prev_input
    hpf[3] = 0      # not initialized

    return hpf

def hpf_destroy(hpf: Ptr[int32]):
    """Destroy high-pass filter."""
    if cast[uint32](hpf) != 0:
        free(cast[Ptr[uint8]](hpf))

def hpf_reset(hpf: Ptr[int32]):
    """Reset high-pass filter."""
    hpf[0] = 0  # value
    hpf[2] = 0  # prev_input
    hpf[3] = 0  # not initialized

def hpf_update(hpf: Ptr[int32], sample: int32) -> int32:
    """Update high-pass filter with new sample.

    Args:
        hpf: Pointer to filter structure
        sample: New input sample

    Returns:
        High-pass filtered output
    """
    alpha: int32 = hpf[1]

    if hpf[3] == 0:
        # First sample
        hpf[2] = sample
        hpf[3] = 1
        return 0

    # y[n] = alpha * (y[n-1] + x[n] - x[n-1])
    prev_output_fp: int32 = hpf[0]
    prev_input: int32 = hpf[2]
    diff: int32 = sample - prev_input

    # Calculate in fixed-point
    new_output_fp: int32 = (alpha >> 8) * ((prev_output_fp >> 8) + (diff << 8))

    hpf[0] = new_output_fp
    hpf[2] = sample

    return new_output_fp >> FILTER_FP_SHIFT

def hpf_get_value(hpf: Ptr[int32]) -> int32:
    """Get current high-pass filter output."""
    return hpf[0] >> FILTER_FP_SHIFT

# ============================================================================
# Median Filter
# ============================================================================
#
# Non-linear filter excellent for removing impulse noise (spikes).
# Preserves edges better than linear filters.
#
# Structure layout:
#   buffer: Ptr[int32]  - Circular buffer of samples (offset 0)
#   sorted: Ptr[int32]  - Sorted copy for median finding (offset 4)
#   index: int32        - Current write index (offset 8)
#   count: int32        - Number of samples added (offset 12)
#   size: int32         - Window size (must be odd) (offset 16)
# Total: 20 bytes

MED_BUFFER_OFFSET: int32 = 0
MED_SORTED_OFFSET: int32 = 4
MED_INDEX_OFFSET: int32 = 8
MED_COUNT_OFFSET: int32 = 12
MED_SIZE_OFFSET: int32 = 16
MED_STRUCT_SIZE: int32 = 20

def median_create(window_size: int32) -> Ptr[int32]:
    """Create a median filter.

    Args:
        window_size: Number of samples (must be odd, 3 to FILTER_MAX_MEDIAN)

    Returns:
        Pointer to filter structure, or null on failure
    """
    # Force odd window size
    if (window_size & 1) == 0:
        window_size = window_size + 1
    if window_size < 3:
        window_size = 3
    if window_size > FILTER_MAX_MEDIAN:
        window_size = FILTER_MAX_MEDIAN

    # Allocate structure
    med: Ptr[int32] = cast[Ptr[int32]](alloc(MED_STRUCT_SIZE))
    if cast[uint32](med) == 0:
        return cast[Ptr[int32]](0)

    # Allocate buffers
    buffer: Ptr[int32] = cast[Ptr[int32]](alloc(window_size * 4))
    if cast[uint32](buffer) == 0:
        free(cast[Ptr[uint8]](med))
        return cast[Ptr[int32]](0)

    sorted_buf: Ptr[int32] = cast[Ptr[int32]](alloc(window_size * 4))
    if cast[uint32](sorted_buf) == 0:
        free(cast[Ptr[uint8]](buffer))
        free(cast[Ptr[uint8]](med))
        return cast[Ptr[int32]](0)

    # Initialize buffers
    i: int32 = 0
    while i < window_size:
        buffer[i] = 0
        sorted_buf[i] = 0
        i = i + 1

    med[0] = cast[int32](buffer)
    med[1] = cast[int32](sorted_buf)
    med[2] = 0           # index
    med[3] = 0           # count
    med[4] = window_size # size

    return med

def median_destroy(med: Ptr[int32]):
    """Destroy median filter and free memory."""
    if cast[uint32](med) == 0:
        return

    buffer: Ptr[int32] = cast[Ptr[int32]](med[0])
    if cast[uint32](buffer) != 0:
        free(cast[Ptr[uint8]](buffer))

    sorted_buf: Ptr[int32] = cast[Ptr[int32]](med[1])
    if cast[uint32](sorted_buf) != 0:
        free(cast[Ptr[uint8]](sorted_buf))

    free(cast[Ptr[uint8]](med))

def median_reset(med: Ptr[int32]):
    """Reset median filter."""
    buffer: Ptr[int32] = cast[Ptr[int32]](med[0])
    sorted_buf: Ptr[int32] = cast[Ptr[int32]](med[1])
    size: int32 = med[4]

    i: int32 = 0
    while i < size:
        buffer[i] = 0
        sorted_buf[i] = 0
        i = i + 1

    med[2] = 0  # index
    med[3] = 0  # count

def _median_insertion_sort(arr: Ptr[int32], n: int32):
    """Sort array using insertion sort (efficient for small n)."""
    i: int32 = 1
    while i < n:
        key: int32 = arr[i]
        j: int32 = i - 1
        while j >= 0 and arr[j] > key:
            arr[j + 1] = arr[j]
            j = j - 1
        arr[j + 1] = key
        i = i + 1

def median_update(med: Ptr[int32], sample: int32) -> int32:
    """Add a new sample and return the median.

    Args:
        med: Pointer to filter structure
        sample: New input sample

    Returns:
        Median of samples in window
    """
    buffer: Ptr[int32] = cast[Ptr[int32]](med[0])
    sorted_buf: Ptr[int32] = cast[Ptr[int32]](med[1])
    size: int32 = med[4]
    index: int32 = med[2]
    count: int32 = med[3]

    # Add sample to circular buffer
    buffer[index] = sample

    # Update count
    if count < size:
        count = count + 1
        med[3] = count

    # Advance index
    index = index + 1
    if index >= size:
        index = 0
    med[2] = index

    # Copy to sorted buffer and sort
    i: int32 = 0
    while i < count:
        sorted_buf[i] = buffer[i]
        i = i + 1

    _median_insertion_sort(sorted_buf, count)

    # Return median (middle element)
    return sorted_buf[count / 2]

def median_get_value(med: Ptr[int32]) -> int32:
    """Get current median without adding a sample."""
    sorted_buf: Ptr[int32] = cast[Ptr[int32]](med[1])
    count: int32 = med[3]

    if count == 0:
        return 0

    return sorted_buf[count / 2]

# ============================================================================
# Simple 1D Kalman Filter
# ============================================================================
#
# Simplified Kalman filter for single variable estimation.
# Good for sensor fusion with known noise characteristics.
#
# Structure layout:
#   estimate: int32     - Current estimate (16.16 FP) (offset 0)
#   error_est: int32    - Estimate error covariance (16.16 FP) (offset 4)
#   error_meas: int32   - Measurement error (16.16 FP) (offset 8)
#   q: int32            - Process noise (16.16 FP) (offset 12)
#   initialized: int32  - Has received first sample (offset 16)
# Total: 20 bytes

KF_ESTIMATE_OFFSET: int32 = 0
KF_ERROR_EST_OFFSET: int32 = 4
KF_ERROR_MEAS_OFFSET: int32 = 8
KF_Q_OFFSET: int32 = 12
KF_INIT_OFFSET: int32 = 16
KF_STRUCT_SIZE: int32 = 20

def kalman_create(meas_error: int32, process_noise: int32) -> Ptr[int32]:
    """Create a 1D Kalman filter.

    Args:
        meas_error: Measurement error/noise variance (16.16 FP)
        process_noise: Process noise variance (16.16 FP)
                       Higher = faster response, more noise
                       Lower = slower response, smoother output

    Returns:
        Pointer to filter structure, or null on failure
    """
    kf: Ptr[int32] = cast[Ptr[int32]](alloc(KF_STRUCT_SIZE))
    if cast[uint32](kf) == 0:
        return cast[Ptr[int32]](0)

    kf[0] = 0                # estimate
    kf[1] = FILTER_FP_ONE    # error_est (initial uncertainty)
    kf[2] = meas_error       # error_meas
    kf[3] = process_noise    # q
    kf[4] = 0                # not initialized

    return kf

def kalman_destroy(kf: Ptr[int32]):
    """Destroy Kalman filter."""
    if cast[uint32](kf) != 0:
        free(cast[Ptr[uint8]](kf))

def kalman_reset(kf: Ptr[int32]):
    """Reset Kalman filter."""
    kf[0] = 0                # estimate
    kf[1] = FILTER_FP_ONE    # error_est
    kf[4] = 0                # not initialized

def kalman_update(kf: Ptr[int32], measurement: int32) -> int32:
    """Update Kalman filter with new measurement.

    Args:
        kf: Pointer to filter structure
        measurement: New measurement

    Returns:
        Filtered estimate
    """
    if kf[4] == 0:
        # First measurement
        kf[0] = measurement << FILTER_FP_SHIFT
        kf[4] = 1
        return measurement

    # Prediction step
    # estimate stays the same (assuming no model)
    # error_est = error_est + q
    error_est: int32 = kf[1] + kf[3]

    # Update step
    # kalman_gain = error_est / (error_est + error_meas)
    error_meas: int32 = kf[2]
    total_error: int32 = error_est + error_meas

    # Avoid division by zero
    if total_error < 256:
        total_error = 256

    # Kalman gain (fixed-point division)
    kalman_gain: int32 = (error_est << 8) / (total_error >> 8)

    # estimate = estimate + gain * (measurement - estimate)
    estimate_fp: int32 = kf[0]
    meas_fp: int32 = measurement << FILTER_FP_SHIFT
    innovation: int32 = meas_fp - estimate_fp

    # Apply gain to innovation
    correction: int32 = (kalman_gain >> 8) * (innovation >> 8)
    new_estimate: int32 = estimate_fp + correction

    # error_est = (1 - gain) * error_est
    new_error: int32 = ((FILTER_FP_ONE - kalman_gain) >> 8) * (error_est >> 8)

    kf[0] = new_estimate
    kf[1] = new_error

    return new_estimate >> FILTER_FP_SHIFT

def kalman_get_value(kf: Ptr[int32]) -> int32:
    """Get current Kalman estimate."""
    return kf[0] >> FILTER_FP_SHIFT

def kalman_get_uncertainty(kf: Ptr[int32]) -> int32:
    """Get current estimate uncertainty (error covariance)."""
    return kf[1]

def kalman_set_process_noise(kf: Ptr[int32], q: int32):
    """Set process noise (affects filter responsiveness)."""
    kf[3] = q

def kalman_set_meas_error(kf: Ptr[int32], r: int32):
    """Set measurement error (affects noise rejection)."""
    kf[2] = r

# ============================================================================
# Debounce Filter
# ============================================================================
#
# Digital input debounce for buttons and switches.
# Requires stable input for N consecutive samples before changing state.
#
# Structure layout:
#   state: int32        - Current debounced state (0 or 1) (offset 0)
#   counter: int32      - Consecutive samples in same state (offset 4)
#   threshold: int32    - Samples needed for state change (offset 8)
#   raw: int32          - Last raw input (offset 12)
# Total: 16 bytes

DB_STATE_OFFSET: int32 = 0
DB_COUNTER_OFFSET: int32 = 4
DB_THRESHOLD_OFFSET: int32 = 8
DB_RAW_OFFSET: int32 = 12
DB_STRUCT_SIZE: int32 = 16

def debounce_create(threshold: int32) -> Ptr[int32]:
    """Create a debounce filter.

    Args:
        threshold: Number of consecutive samples needed for state change
                   Higher = more filtering, slower response

    Returns:
        Pointer to filter structure, or null on failure
    """
    if threshold < 1:
        threshold = 1

    db: Ptr[int32] = cast[Ptr[int32]](alloc(DB_STRUCT_SIZE))
    if cast[uint32](db) == 0:
        return cast[Ptr[int32]](0)

    db[0] = 0          # state
    db[1] = 0          # counter
    db[2] = threshold  # threshold
    db[3] = 0          # raw

    return db

def debounce_create_ms(debounce_ms: int32, sample_period_ms: int32) -> Ptr[int32]:
    """Create a debounce filter from time parameters.

    Args:
        debounce_ms: Debounce time in milliseconds
        sample_period_ms: Sample period in milliseconds

    Returns:
        Pointer to filter structure
    """
    threshold: int32 = 1
    if sample_period_ms > 0:
        threshold = debounce_ms / sample_period_ms
        if threshold < 1:
            threshold = 1

    return debounce_create(threshold)

def debounce_destroy(db: Ptr[int32]):
    """Destroy debounce filter."""
    if cast[uint32](db) != 0:
        free(cast[Ptr[uint8]](db))

def debounce_reset(db: Ptr[int32]):
    """Reset debounce filter."""
    db[0] = 0  # state
    db[1] = 0  # counter
    db[3] = 0  # raw

def debounce_update(db: Ptr[int32], input: int32) -> int32:
    """Update debounce filter with new input.

    Args:
        db: Pointer to filter structure
        input: Raw input (0 or non-zero)

    Returns:
        Debounced state (0 or 1)
    """
    # Normalize input to 0 or 1
    raw: int32 = 0
    if input != 0:
        raw = 1

    db[3] = raw
    state: int32 = db[0]
    threshold: int32 = db[2]

    if raw == state:
        # Input matches current state, reset counter
        db[1] = 0
    else:
        # Input differs from state, increment counter
        counter: int32 = db[1] + 1
        db[1] = counter

        if counter >= threshold:
            # State change confirmed
            db[0] = raw
            db[1] = 0
            return raw

    return state

def debounce_get_state(db: Ptr[int32]) -> int32:
    """Get current debounced state."""
    return db[0]

def debounce_get_raw(db: Ptr[int32]) -> int32:
    """Get last raw input value."""
    return db[3]

def debounce_rising_edge(db: Ptr[int32], input: int32) -> bool:
    """Check for rising edge (0->1 transition).

    Args:
        db: Pointer to filter structure
        input: Raw input

    Returns:
        True if rising edge detected this sample
    """
    prev_state: int32 = db[0]
    new_state: int32 = debounce_update(db, input)

    return prev_state == 0 and new_state == 1

def debounce_falling_edge(db: Ptr[int32], input: int32) -> bool:
    """Check for falling edge (1->0 transition).

    Args:
        db: Pointer to filter structure
        input: Raw input

    Returns:
        True if falling edge detected this sample
    """
    prev_state: int32 = db[0]
    new_state: int32 = debounce_update(db, input)

    return prev_state == 1 and new_state == 0

# ============================================================================
# Slew Rate Limiter
# ============================================================================
#
# Limits how fast a signal can change per sample.
# Useful for smooth control outputs.
#
# Structure layout:
#   value: int32        - Current output value (offset 0)
#   max_rise: int32     - Maximum increase per sample (offset 4)
#   max_fall: int32     - Maximum decrease per sample (offset 8)
#   initialized: int32  - Has received first sample (offset 12)
# Total: 16 bytes

SRL_VALUE_OFFSET: int32 = 0
SRL_MAX_RISE_OFFSET: int32 = 4
SRL_MAX_FALL_OFFSET: int32 = 8
SRL_INIT_OFFSET: int32 = 12
SRL_STRUCT_SIZE: int32 = 16

def slew_create(max_rise: int32, max_fall: int32) -> Ptr[int32]:
    """Create a slew rate limiter.

    Args:
        max_rise: Maximum increase per sample (positive)
        max_fall: Maximum decrease per sample (positive)

    Returns:
        Pointer to filter structure
    """
    srl: Ptr[int32] = cast[Ptr[int32]](alloc(SRL_STRUCT_SIZE))
    if cast[uint32](srl) == 0:
        return cast[Ptr[int32]](0)

    if max_rise < 0:
        max_rise = -max_rise
    if max_fall < 0:
        max_fall = -max_fall

    srl[0] = 0          # value
    srl[1] = max_rise   # max_rise
    srl[2] = max_fall   # max_fall
    srl[3] = 0          # not initialized

    return srl

def slew_create_symmetric(max_rate: int32) -> Ptr[int32]:
    """Create a slew rate limiter with symmetric limits."""
    return slew_create(max_rate, max_rate)

def slew_destroy(srl: Ptr[int32]):
    """Destroy slew rate limiter."""
    if cast[uint32](srl) != 0:
        free(cast[Ptr[uint8]](srl))

def slew_reset(srl: Ptr[int32]):
    """Reset slew rate limiter."""
    srl[0] = 0
    srl[3] = 0

def slew_update(srl: Ptr[int32], target: int32) -> int32:
    """Update slew rate limiter.

    Args:
        srl: Pointer to filter structure
        target: Target value to approach

    Returns:
        Rate-limited output value
    """
    if srl[3] == 0:
        # First sample
        srl[0] = target
        srl[3] = 1
        return target

    current: int32 = srl[0]
    max_rise: int32 = srl[1]
    max_fall: int32 = srl[2]

    diff: int32 = target - current

    if diff > max_rise:
        current = current + max_rise
    elif diff < -max_fall:
        current = current - max_fall
    else:
        current = target

    srl[0] = current
    return current

def slew_get_value(srl: Ptr[int32]) -> int32:
    """Get current output value."""
    return srl[0]

def slew_set_rates(srl: Ptr[int32], max_rise: int32, max_fall: int32):
    """Set slew rate limits."""
    if max_rise < 0:
        max_rise = -max_rise
    if max_fall < 0:
        max_fall = -max_fall
    srl[1] = max_rise
    srl[2] = max_fall

# ============================================================================
# Hysteresis Filter
# ============================================================================
#
# Prevents output oscillation near threshold.
# Output only changes when input crosses threshold by hysteresis amount.
#
# Structure layout:
#   state: int32        - Current output state (0 or 1) (offset 0)
#   threshold: int32    - Center threshold (offset 4)
#   hysteresis: int32   - Hysteresis band width (offset 8)
# Total: 12 bytes

HYS_STATE_OFFSET: int32 = 0
HYS_THRESHOLD_OFFSET: int32 = 4
HYS_HYSTERESIS_OFFSET: int32 = 8
HYS_STRUCT_SIZE: int32 = 12

def hysteresis_create(threshold: int32, hysteresis: int32) -> Ptr[int32]:
    """Create a hysteresis filter.

    Args:
        threshold: Center threshold value
        hysteresis: Hysteresis band (total width)

    Returns:
        Pointer to filter structure
    """
    hys: Ptr[int32] = cast[Ptr[int32]](alloc(HYS_STRUCT_SIZE))
    if cast[uint32](hys) == 0:
        return cast[Ptr[int32]](0)

    if hysteresis < 0:
        hysteresis = -hysteresis

    hys[0] = 0          # state
    hys[1] = threshold  # threshold
    hys[2] = hysteresis # hysteresis

    return hys

def hysteresis_destroy(hys: Ptr[int32]):
    """Destroy hysteresis filter."""
    if cast[uint32](hys) != 0:
        free(cast[Ptr[uint8]](hys))

def hysteresis_reset(hys: Ptr[int32]):
    """Reset hysteresis filter."""
    hys[0] = 0

def hysteresis_update(hys: Ptr[int32], input: int32) -> int32:
    """Update hysteresis filter.

    Args:
        hys: Pointer to filter structure
        input: Input value

    Returns:
        Output state (0 or 1)
    """
    state: int32 = hys[0]
    threshold: int32 = hys[1]
    half_hys: int32 = hys[2] / 2

    if state == 0:
        # Currently low, need to exceed upper threshold to go high
        if input > threshold + half_hys:
            hys[0] = 1
            return 1
    else:
        # Currently high, need to go below lower threshold to go low
        if input < threshold - half_hys:
            hys[0] = 0
            return 0

    return state

def hysteresis_get_state(hys: Ptr[int32]) -> int32:
    """Get current output state."""
    return hys[0]

def hysteresis_set_params(hys: Ptr[int32], threshold: int32, hysteresis: int32):
    """Set threshold and hysteresis values."""
    if hysteresis < 0:
        hysteresis = -hysteresis
    hys[1] = threshold
    hys[2] = hysteresis

# ============================================================================
# Example Usage
# ============================================================================
#
# # Moving average for ADC smoothing
# adc_filter: Ptr[int32] = ma_create(8)  # 8-sample window
# while True:
#     raw: int32 = adc_read(0)
#     smooth: int32 = ma_update(adc_filter, raw)
#
# # EMA for temperature with 1-second time constant
# temp_filter: Ptr[int32] = ema_create_tc(1000, 100)  # 1s TC, 100ms sample
# while True:
#     temp: int32 = read_temperature()
#     filtered_temp: int32 = ema_update(temp_filter, temp)
#
# # Median filter for removing sensor spikes
# spike_filter: Ptr[int32] = median_create(5)  # 5-sample median
# while True:
#     sensor: int32 = read_sensor()
#     clean: int32 = median_update(spike_filter, sensor)
#
# # Kalman filter for sensor fusion
# kf: Ptr[int32] = kalman_create(6554, 655)  # R=0.1, Q=0.01 in FP
# while True:
#     measurement: int32 = read_sensor()
#     estimate: int32 = kalman_update(kf, measurement)
#
# # Button debounce (50ms at 10ms sample rate)
# button: Ptr[int32] = debounce_create_ms(50, 10)
# while True:
#     raw_btn: int32 = gpio_read(0, 0)
#     if debounce_rising_edge(button, raw_btn):
#         handle_button_press()
#
# # Slew rate limiter for motor control
# motor_slew: Ptr[int32] = slew_create(10, 5)  # Rise 10/sample, fall 5/sample
# while True:
#     target_speed: int32 = get_target()
#     safe_speed: int32 = slew_update(motor_slew, target_speed)
#     set_motor(safe_speed)
