/* STM32F405/F407 Linker Script
 *
 * Memory Map (STM32F405RG / STM32F407VG):
 *   Flash: 0x08000000 - 0x080FFFFF (1MB)
 *   SRAM1: 0x20000000 - 0x2001FFFF (128KB)
 *   SRAM2: 0x2001C000 - 0x2001FFFF (16KB, overlaps end of SRAM1)
 *   CCM:   0x10000000 - 0x1000FFFF (64KB, core coupled memory)
 *
 * Flash Layout for Dual-Bank Firmware Update:
 *   0x08000000 - 0x08003FFF  Bootloader (16KB - Sector 0)
 *   0x08004000 - 0x0807FFFF  Bank 0 - Application (496KB)
 *   0x08080000 - 0x080FBFFF  Bank 1 - Update slot (496KB)
 *   0x080FC000 - 0x080FFFFF  Config/metadata (16KB - last sector)
 *
 * Note: This targets F405/F407. For F401 (256KB flash, 64KB RAM),
 *       modify the MEMORY section accordingly.
 */

MEMORY
{
    /* Bootloader region (16KB - Sector 0) */
    BOOTLOADER (rx) : ORIGIN = 0x08000000, LENGTH = 16K

    /* Bank 0 - Primary application */
    BANK0 (rx)      : ORIGIN = 0x08004000, LENGTH = 496K

    /* Bank 1 - Secondary/update slot */
    BANK1 (rx)      : ORIGIN = 0x08080000, LENGTH = 496K

    /* Configuration and metadata */
    CONFIG (rx)     : ORIGIN = 0x080FC000, LENGTH = 16K

    /* For backward compatibility, FLASH points to Bank 0 */
    FLASH (rx)      : ORIGIN = 0x08004000, LENGTH = 496K

    /* Main SRAM (SRAM1 + SRAM2 contiguous) */
    RAM (rwx)       : ORIGIN = 0x20000000, LENGTH = 128K

    /* Core Coupled Memory - fast, no DMA access */
    CCM (rwx)       : ORIGIN = 0x10000000, LENGTH = 64K

    /* Backup SRAM (4KB, battery-backed) */
    BKPSRAM (rwx)   : ORIGIN = 0x40024000, LENGTH = 4K
}

ENTRY(_reset)

SECTIONS
{
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

    /* Vector table at start of application flash */
    .vectors : {
        . = ALIGN(4);
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

        /* ARM exception unwinding (optional) */
        *(.ARM.extab*)
        *(.ARM.exidx*)

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

    /* Stack - 8KB at end of main RAM */
    .stack (NOLOAD) : {
        . = ALIGN(8);
        __stack_start = .;
        . = . + 8K;
        __stack_end = .;
        __stack_top = .;
    } > RAM

    /* CCM can be used for fast variables */
    .ccm (NOLOAD) : {
        . = ALIGN(4);
        __ccm_start = .;
        *(.ccm*)
        . = ALIGN(4);
        __ccm_end = .;
    } > CCM

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

/* STM32F4 Peripheral Base Addresses */

/* AHB1 Peripherals */
PROVIDE(GPIOA_BASE      = 0x40020000);
PROVIDE(GPIOB_BASE      = 0x40020400);
PROVIDE(GPIOC_BASE      = 0x40020800);
PROVIDE(GPIOD_BASE      = 0x40020C00);
PROVIDE(GPIOE_BASE      = 0x40021000);
PROVIDE(GPIOF_BASE      = 0x40021400);
PROVIDE(GPIOG_BASE      = 0x40021800);
PROVIDE(GPIOH_BASE      = 0x40021C00);
PROVIDE(GPIOI_BASE      = 0x40022000);
PROVIDE(CRC_BASE        = 0x40023000);
PROVIDE(RCC_BASE        = 0x40023800);
PROVIDE(FLASH_BASE      = 0x40023C00);
PROVIDE(DMA1_BASE       = 0x40026000);
PROVIDE(DMA2_BASE       = 0x40026400);
PROVIDE(ETH_BASE        = 0x40028000);
PROVIDE(USB_OTG_HS_BASE = 0x40040000);

/* AHB2 Peripherals */
PROVIDE(USB_OTG_FS_BASE = 0x50000000);
PROVIDE(DCMI_BASE       = 0x50050000);
PROVIDE(RNG_BASE        = 0x50060800);

/* APB1 Peripherals */
PROVIDE(TIM2_BASE       = 0x40000000);
PROVIDE(TIM3_BASE       = 0x40000400);
PROVIDE(TIM4_BASE       = 0x40000800);
PROVIDE(TIM5_BASE       = 0x40000C00);
PROVIDE(TIM6_BASE       = 0x40001000);
PROVIDE(TIM7_BASE       = 0x40001400);
PROVIDE(TIM12_BASE      = 0x40001800);
PROVIDE(TIM13_BASE      = 0x40001C00);
PROVIDE(TIM14_BASE      = 0x40002000);
PROVIDE(RTC_BASE        = 0x40002800);
PROVIDE(WWDG_BASE       = 0x40002C00);
PROVIDE(IWDG_BASE       = 0x40003000);
PROVIDE(SPI2_BASE       = 0x40003800);
PROVIDE(SPI3_BASE       = 0x40003C00);
PROVIDE(USART2_BASE     = 0x40004400);
PROVIDE(USART3_BASE     = 0x40004800);
PROVIDE(UART4_BASE      = 0x40004C00);
PROVIDE(UART5_BASE      = 0x40005000);
PROVIDE(I2C1_BASE       = 0x40005400);
PROVIDE(I2C2_BASE       = 0x40005800);
PROVIDE(I2C3_BASE       = 0x40005C00);
PROVIDE(CAN1_BASE       = 0x40006400);
PROVIDE(CAN2_BASE       = 0x40006800);
PROVIDE(PWR_BASE        = 0x40007000);
PROVIDE(DAC_BASE        = 0x40007400);

/* APB2 Peripherals */
PROVIDE(TIM1_BASE       = 0x40010000);
PROVIDE(TIM8_BASE       = 0x40010400);
PROVIDE(USART1_BASE     = 0x40011000);
PROVIDE(USART6_BASE     = 0x40011400);
PROVIDE(ADC_BASE        = 0x40012000);
PROVIDE(SDIO_BASE       = 0x40012C00);
PROVIDE(SPI1_BASE       = 0x40013000);
PROVIDE(SYSCFG_BASE     = 0x40013800);
PROVIDE(EXTI_BASE       = 0x40013C00);
PROVIDE(TIM9_BASE       = 0x40014000);
PROVIDE(TIM10_BASE      = 0x40014400);
PROVIDE(TIM11_BASE      = 0x40014800);

/* Cortex-M4 Internal Peripherals */
PROVIDE(SCB_BASE        = 0xE000ED00);
PROVIDE(SYSTICK_BASE    = 0xE000E010);
PROVIDE(NVIC_BASE       = 0xE000E100);
PROVIDE(FPU_BASE        = 0xE000EF30);
PROVIDE(MPU_BASE        = 0xE000ED90);

/* Bootloader Memory Layout Symbols */
PROVIDE(__bootloader_base = 0x08000000);
PROVIDE(__bootloader_size = 16K);
PROVIDE(__bank0_base     = 0x08004000);
PROVIDE(__bank0_size     = 496K);
PROVIDE(__bank1_base     = 0x08080000);
PROVIDE(__bank1_size     = 496K);
PROVIDE(__config_base    = 0x080FC000);
PROVIDE(__config_size    = 16K);
PROVIDE(__bkpsram_base   = 0x40024000);
PROVIDE(__bkpsram_size   = 4K);

/* Application Header Offset (after vector table) */
PROVIDE(__app_header_offset = 0x100);

/* Flash Sector Layout (for erase operations)
 * Sector 0:  16KB  0x08000000 - 0x08003FFF (Bootloader)
 * Sector 1:  16KB  0x08004000 - 0x08007FFF
 * Sector 2:  16KB  0x08008000 - 0x0800BFFF
 * Sector 3:  16KB  0x0800C000 - 0x0800FFFF
 * Sector 4:  64KB  0x08010000 - 0x0801FFFF
 * Sector 5: 128KB  0x08020000 - 0x0803FFFF
 * Sector 6: 128KB  0x08040000 - 0x0805FFFF
 * Sector 7: 128KB  0x08060000 - 0x0807FFFF (End of Bank 0)
 * Sector 8: 128KB  0x08080000 - 0x0809FFFF (Start of Bank 1)
 * Sector 9: 128KB  0x080A0000 - 0x080BFFFF
 * Sector10: 128KB  0x080C0000 - 0x080DFFFF
 * Sector11: 128KB  0x080E0000 - 0x080FFFFF (End of Bank 1 + Config)
 */
