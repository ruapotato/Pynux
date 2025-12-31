/* RP2040 (Raspberry Pi Pico) Linker Script
 *
 * Memory Map:
 *   Flash (XIP): 0x10000000 - 0x101FFFFF (2MB)
 *   SRAM:        0x20000000 - 0x20041FFF (264KB)
 *
 * Boot sequence:
 *   1. Boot ROM loads boot2 (256 bytes) from flash
 *   2. boot2 configures XIP and jumps to bootloader
 *   3. Bootloader validates firmware and jumps to app
 *
 * Flash Layout for Dual-Bank Firmware Update:
 *   0x10000000 - 0x100000FF  boot2 (256 bytes)
 *   0x10000100 - 0x10003FFF  Bootloader (16KB - 256)
 *   0x10004000 - 0x1010FFFF  Bank 0 - Application (1MB + 48KB)
 *   0x10110000 - 0x101FBFFF  Bank 1 - Update slot (944KB)
 *   0x101FC000 - 0x101FFFFF  Config/metadata (16KB)
 */

MEMORY
{
    /* First 256 bytes reserved for boot2 stage */
    BOOT2 (rx)       : ORIGIN = 0x10000000, LENGTH = 256

    /* Bootloader region (16KB - 256 bytes for boot2) */
    BOOTLOADER (rx)  : ORIGIN = 0x10000100, LENGTH = 16K - 256

    /* Bank 0 - Primary application */
    BANK0 (rx)       : ORIGIN = 0x10004000, LENGTH = 1M + 48K

    /* Bank 1 - Secondary/update slot */
    BANK1 (rx)       : ORIGIN = 0x10110000, LENGTH = 944K

    /* Configuration and metadata */
    CONFIG (rx)      : ORIGIN = 0x101FC000, LENGTH = 16K

    /* For backward compatibility, FLASH points to Bank 0 */
    FLASH (rx)       : ORIGIN = 0x10004000, LENGTH = 1M + 48K

    /* SRAM banks 0-3 (striped) + SRAM4 + SRAM5 */
    RAM (rwx)        : ORIGIN = 0x20000000, LENGTH = 264K
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

    /* Bootloader section */
    .bootloader : {
        . = ALIGN(4);
        __bootloader_start = .;
        KEEP(*(.bootloader.vectors))
        KEEP(*(.bootloader.text))
        KEEP(*(.bootloader.rodata))
        . = ALIGN(4);
        __bootloader_end = .;
    } > BOOTLOADER

    /* Vector table must be at start of application flash */
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

/* Bootloader Memory Layout Symbols */
PROVIDE(__bootloader_base = 0x10000100);
PROVIDE(__bootloader_size = 16K - 256);
PROVIDE(__bank0_base     = 0x10004000);
PROVIDE(__bank0_size     = 1M + 48K);
PROVIDE(__bank1_base     = 0x10110000);
PROVIDE(__bank1_size     = 944K);
PROVIDE(__config_base    = 0x101FC000);
PROVIDE(__config_size    = 16K);

/* Application Header Offset (after vector table) */
PROVIDE(__app_header_offset = 0x100);
