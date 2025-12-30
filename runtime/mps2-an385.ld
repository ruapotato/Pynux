/* Pynux Linker Script for QEMU mps2-an385 (Cortex-M3) */

/* Memory layout for MPS2-AN385 */
MEMORY
{
    FLASH (rx)  : ORIGIN = 0x00000000, LENGTH = 4M
    RAM   (rwx) : ORIGIN = 0x20000000, LENGTH = 4M
}

/* Stack size */
_stack_size = 0x2000;  /* 8KB stack */

SECTIONS
{
    /* Vector table at start of flash */
    .vectors :
    {
        KEEP(*(.vectors))
    } > FLASH

    /* Code section */
    .text :
    {
        *(.text)
        *(.text*)
        *(.rodata)
        *(.rodata*)
        . = ALIGN(4);
    } > FLASH

    /* ARM exception handling */
    .ARM.extab :
    {
        *(.ARM.extab*)
    } > FLASH

    .ARM.exidx :
    {
        *(.ARM.exidx*)
    } > FLASH

    /* Initialized data - stored in flash, copied to RAM */
    _data_load = LOADADDR(.data);

    .data :
    {
        _data_start = .;
        *(.data)
        *(.data*)
        . = ALIGN(4);
        _data_end = .;
    } > RAM AT > FLASH

    /* Uninitialized data (BSS) */
    .bss :
    {
        _bss_start = .;
        *(.bss)
        *(.bss*)
        *(COMMON)
        . = ALIGN(4);
        _bss_end = .;
    } > RAM

    /* Stack at end of RAM */
    .stack (NOLOAD) :
    {
        . = ALIGN(8);
        _stack_bottom = .;
        . = . + _stack_size;
        . = ALIGN(8);
        _stack_top = .;
    } > RAM

    /* Heap after BSS */
    .heap (NOLOAD) :
    {
        _heap_start = .;
        . = ORIGIN(RAM) + LENGTH(RAM) - _stack_size;
        _heap_end = .;
    } > RAM
}

/* Entry point */
ENTRY(_reset)
