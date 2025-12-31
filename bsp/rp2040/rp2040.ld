/* RP2040 (Raspberry Pi Pico) Linker Script
 *
 * Memory Map:
 *   Flash (XIP): 0x10000000 - 0x101FFFFF (2MB)
 *   SRAM:        0x20000000 - 0x20041FFF (264KB)
 *
 * Boot sequence:
 *   1. Boot ROM loads boot2 (256 bytes) from flash
 *   2. boot2 configures XIP and jumps to main code
 *   3. Vector table at 0x10000100
 */

MEMORY
{
    /* First 256 bytes reserved for boot2 stage */
    BOOT2 (rx)  : ORIGIN = 0x10000000, LENGTH = 256

    /* Main flash after boot2 */
    FLASH (rx)  : ORIGIN = 0x10000100, LENGTH = 2M - 256

    /* SRAM banks 0-3 (striped) + SRAM4 + SRAM5 */
    RAM (rwx)   : ORIGIN = 0x20000000, LENGTH = 264K
}

ENTRY(_reset)

SECTIONS
{
    /* Boot2 stage - copies from flash, configures XIP */
    .boot2 : {
        __boot2_start = .;
        KEEP(*(.boot2))
        __boot2_end = .;
    } > BOOT2

    /* Vector table must be at start of main flash */
    .vectors : {
        . = ALIGN(256);
        __vectors_start = .;
        KEEP(*(.vectors))
        __vectors_end = .;
    } > FLASH

    /* Code */
    .text : {
        . = ALIGN(4);
        __text_start = .;
        *(.text*)
        *(.rodata*)
        . = ALIGN(4);
        __text_end = .;
    } > FLASH

    /* Initialized data - stored in flash, copied to RAM */
    .data : {
        . = ALIGN(4);
        __data_start = .;
        *(.data*)
        . = ALIGN(4);
        __data_end = .;
    } > RAM AT > FLASH

    /* Load address of .data in flash */
    __data_load = LOADADDR(.data);

    /* Uninitialized data - zeroed at startup */
    .bss : {
        . = ALIGN(4);
        __bss_start = .;
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        __bss_end = .;
    } > RAM

    /* Stack - 8KB at end of RAM */
    .stack (NOLOAD) : {
        . = ALIGN(8);
        __stack_start = .;
        . = . + 8K;
        __stack_end = .;
        __stack_top = .;
    } > RAM

    /* Heap - everything between BSS and stack */
    __heap_start = __bss_end;
    __heap_end = __stack_start;
    __heap_size = __heap_end - __heap_start;

    /* Symbols for startup code */
    _etext = __text_end;
    _sdata = __data_start;
    _edata = __data_end;
    _sbss = __bss_start;
    _ebss = __bss_end;
}

/* RP2040 Peripheral Base Addresses */
PROVIDE(XIP_BASE        = 0x10000000);
PROVIDE(XIP_SSI_BASE    = 0x18000000);
PROVIDE(SYSINFO_BASE    = 0x40000000);
PROVIDE(SYSCFG_BASE     = 0x40004000);
PROVIDE(CLOCKS_BASE     = 0x40008000);
PROVIDE(RESETS_BASE     = 0x4000C000);
PROVIDE(PSM_BASE        = 0x40010000);
PROVIDE(IO_BANK0_BASE   = 0x40014000);
PROVIDE(IO_QSPI_BASE    = 0x40018000);
PROVIDE(PADS_BANK0_BASE = 0x4001C000);
PROVIDE(PADS_QSPI_BASE  = 0x40020000);
PROVIDE(XOSC_BASE       = 0x40024000);
PROVIDE(PLL_SYS_BASE    = 0x40028000);
PROVIDE(PLL_USB_BASE    = 0x4002C000);
PROVIDE(BUSCTRL_BASE    = 0x40030000);
PROVIDE(UART0_BASE      = 0x40034000);
PROVIDE(UART1_BASE      = 0x40038000);
PROVIDE(SPI0_BASE       = 0x4003C000);
PROVIDE(SPI1_BASE       = 0x40040000);
PROVIDE(I2C0_BASE       = 0x40044000);
PROVIDE(I2C1_BASE       = 0x40048000);
PROVIDE(ADC_BASE        = 0x4004C000);
PROVIDE(PWM_BASE        = 0x40050000);
PROVIDE(TIMER_BASE      = 0x40054000);
PROVIDE(WATCHDOG_BASE   = 0x40058000);
PROVIDE(RTC_BASE        = 0x4005C000);
PROVIDE(ROSC_BASE       = 0x40060000);
PROVIDE(VREG_BASE       = 0x40064000);
PROVIDE(TBMAN_BASE      = 0x4006C000);
PROVIDE(DMA_BASE        = 0x50000000);
PROVIDE(USB_BASE        = 0x50110000);
PROVIDE(PIO0_BASE       = 0x50200000);
PROVIDE(PIO1_BASE       = 0x50300000);
PROVIDE(SIO_BASE        = 0xD0000000);
PROVIDE(PPB_BASE        = 0xE0000000);
