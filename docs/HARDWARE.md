# Hardware Bring-Up Guide

This guide covers deploying Pynux on real hardware targets.

## Supported Targets

| Target | MCU | Status | Notes |
|--------|-----|--------|-------|
| QEMU | Cortex-M3 | Working | Primary development target |
| RP2040 | Cortex-M0+ | Experimental | Raspberry Pi Pico |
| STM32F4 | Cortex-M4 | Experimental | STM32F405/F407 boards |

## Quick Start

### QEMU (Development)

```bash
./build.sh
./build.sh --run
```

### RP2040 (Raspberry Pi Pico)

```bash
# Build
./build.sh --target=rp2040

# Flash (hold BOOTSEL while connecting USB)
./build.sh --target=rp2040 --flash
```

### STM32F4

```bash
# Build
./build.sh --target=stm32f4

# Flash (requires ST-Link or compatible)
./build.sh --target=stm32f4 --flash
```

## Hardware Validation

### First Test: Blinky

The `programs/blinky.py` program validates basic hardware:
- SysTick timer (1ms interrupts)
- GPIO output (LED toggle)
- UART output (status messages)

Expected output on serial (115200 baud):
```
Blinky started on RP2040
Running blinky loop...
Blink #1 at 2s
Blink #2 at 4s
```

LED should toggle every 500ms.

### Second Test: UART Echo

1. Connect serial terminal at 115200 baud
2. Type characters - they should echo back
3. Confirms bidirectional UART

## Pin Mappings

### RP2040 (Raspberry Pi Pico)

| Function | GPIO | Notes |
|----------|------|-------|
| LED | GPIO25 | Onboard green LED |
| UART0 TX | GPIO0 | Default debug UART |
| UART0 RX | GPIO1 | |
| I2C0 SDA | GPIO4 | |
| I2C0 SCL | GPIO5 | |
| SPI0 MISO | GPIO16 | |
| SPI0 CS | GPIO17 | |
| SPI0 SCK | GPIO18 | |
| SPI0 MOSI | GPIO19 | |
| ADC0 | GPIO26 | 12-bit, 3.3V ref |
| ADC1 | GPIO27 | |
| ADC2 | GPIO28 | |
| ADC3 | GPIO29 | VSYS/3 on Pico |
| ADC4 | - | Internal temp sensor |

### STM32F4 (Blue Pill / Nucleo)

| Function | Pin | Notes |
|----------|-----|-------|
| LED | PC13 | Blue Pill (active low) |
| LED | PA5 | Nucleo boards |
| USART1 TX | PA9 | Default debug UART |
| USART1 RX | PA10 | |
| I2C1 SCL | PB6 | Alt: PB8 |
| I2C1 SDA | PB7 | Alt: PB9 |
| SPI1 SCK | PA5 | |
| SPI1 MISO | PA6 | |
| SPI1 MOSI | PA7 | |
| ADC1 CH0 | PA0 | 12-bit, 3.3V ref |
| ADC1 CH16 | - | Internal temp sensor |
| ADC1 CH17 | - | VREFINT (~1.2V) |

## Clock Configuration

### RP2040
- Crystal: 12 MHz XOSC
- PLL: 125 MHz system clock
- USB: 48 MHz from PLL_USB

### STM32F4
- Crystal: 8 MHz HSE
- PLL: 168 MHz SYSCLK
- AHB: 168 MHz
- APB1: 42 MHz (I2C, SPI2, USART2-5, TIM2-7)
- APB2: 84 MHz (SPI1, USART1/6, ADC, TIM1/8)

## Memory Layout

### RP2040
```
0x10000000  Flash (2MB)
  ├─ Boot2 (256 bytes)
  ├─ Vectors
  ├─ .text (code)
  └─ .rodata
0x20000000  SRAM (264KB)
  ├─ .data
  ├─ .bss
  ├─ Heap
  └─ Stack (8KB at end)
```

### STM32F4
```
0x08000000  Flash (1MB)
  ├─ Vectors
  ├─ .text
  └─ .rodata
0x20000000  SRAM (128KB)
  ├─ .data
  ├─ .bss
  ├─ Heap
  └─ Stack (8KB at end)
0x10000000  CCM (64KB)
  └─ Fast data (no DMA)
```

## HAL Drivers

Hardware-specific drivers in `lib/hal/`:

| Driver | RP2040 | STM32F4 |
|--------|--------|---------|
| GPIO | `rp2040_gpio.py` | `stm32f4_gpio.py` |
| UART | `rp2040_uart.py` | `stm32f4_uart.py` |
| I2C | `rp2040_i2c.py` | `stm32f4_i2c.py` |
| SPI | `rp2040_spi.py` | `stm32f4_spi.py` |
| ADC | `rp2040_adc.py` | `stm32f4_adc.py` |

### Usage Example

```python
# RP2040 LED blink
from lib.hal.rp2040_gpio import gpio_init, gpio_set_dir_out, gpio_toggle

gpio_init(25)
gpio_set_dir_out(25)
gpio_toggle(25)

# STM32F4 LED blink
from lib.hal.stm32f4_gpio import gpio_init_output, gpio_toggle, PORT_C

gpio_init_output(PORT_C, 13)
gpio_toggle(PORT_C, 13)
```

## Debugging

### RP2040

- **Picoprobe**: Use another Pico as debugger
- **SWD**: Connect SWDIO (GPIO) and SWCLK
- **openocd**: `openocd -f interface/cmsis-dap.cfg -f target/rp2040.cfg`

### STM32F4

- **ST-Link**: Built into Nucleo, external for Blue Pill
- **openocd**: `openocd -f interface/stlink.cfg -f target/stm32f4x.cfg`
- **GDB**: `arm-none-eabi-gdb build/pynux.elf`

### UART Debugging

Both targets output debug messages on UART at boot:
```
Pynux OS v0.1.0
Clock: 125 MHz
RAM: 264 KB
Heap: 200 KB free
```

## Common Issues

### RP2040

**No output on UART**
- Check GPIO0/1 connections (TX/RX)
- Verify 3.3V logic level
- Try swapping TX/RX

**Boot loop**
- Hold BOOTSEL, connect USB, release
- Flash new firmware

### STM32F4

**No output on UART**
- Check PA9/PA10 connections
- USART1 requires APB2 clock (84 MHz)
- Blue Pill may need USB-Serial adapter

**Flash fails**
- Check ST-Link connection
- Try `st-flash erase` first
- Verify 3.3V supply

**Clock issues**
- Most boards have 8 MHz crystal
- Some use 25 MHz - modify startup

## Porting to New Hardware

1. **Create BSP directory**: `bsp/your_board/`

2. **Linker script** (`your_board.ld`):
   - Define FLASH, RAM regions
   - Set peripheral base addresses

3. **Startup code** (`startup.s`):
   - Vector table
   - Clock/PLL configuration
   - UART init for debug
   - Call `kernel_main`

4. **HAL drivers** (if needed):
   - GPIO if different from existing
   - UART for serial I/O
   - SysTick for timing

5. **Update build.sh**:
   - Add target case
   - Set ASFLAGS for CPU type
   - Point to linker script

Example for new Cortex-M board:
```bash
your_board)
    ASFLAGS="-mcpu=cortex-m4 -mthumb"
    LINKER_SCRIPT="bsp/your_board/your_board.ld"
    STARTUP_FILE="bsp/your_board/startup.s"
    SYSTEM_CLOCK=100000000
    ;;
```

## Performance Notes

| Operation | RP2040 (125MHz) | STM32F4 (168MHz) |
|-----------|-----------------|------------------|
| GPIO toggle | ~8 ns | ~6 ns |
| UART char | ~87 µs @ 115200 | ~87 µs @ 115200 |
| I2C byte | ~10 µs @ 400kHz | ~2.5 µs @ 400kHz |
| SPI byte | ~1 µs @ 10MHz | ~0.7 µs @ 10MHz |
| ADC sample | ~2 µs | ~0.5 µs |
