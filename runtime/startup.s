@ Pynux ARM Cortex-M3 Startup Code
@ Target: QEMU mps2-an385
@
@ ============================================================================
@ BOOT SEQUENCE OVERVIEW
@ ============================================================================
@
@ The Cortex-M3 boot sequence is:
@   1. Hardware loads SP from vector table offset 0x00
@   2. Hardware loads PC from vector table offset 0x04 (reset handler)
@   3. Reset handler executes (this code)
@
@ This startup code performs:
@   1. Stack initialization (redundant but safe)
@   2. BSS section zeroing (uninitialized data)
@   3. Data section copy (initialized data from flash to RAM)
@   4. Early hardware initialization (clocks, watchdog)
@   5. Boot reason detection
@   6. Firmware validation (CRC check)
@   7. UART initialization for debug output
@   8. Jump to main()
@
@ ============================================================================
@ MEMORY MAP (mps2-an385)
@ ============================================================================
@
@   0x00000000 - 0x003FFFFF  Flash (4MB)
@   0x20000000 - 0x203FFFFF  SRAM (4MB)
@   0x40000000 - 0x5FFFFFFF  Peripherals
@   0xE0000000 - 0xE00FFFFF  Private peripheral bus (NVIC, SysTick, etc.)
@
@ Stack grows downward from _stack_top (typically end of SRAM)
@
@ ============================================================================
@ LINKER SYMBOLS (provided by linker script)
@ ============================================================================
@
@   _stack_top   - Top of stack (initial SP value)
@   _bss_start   - Start of BSS section in RAM
@   _bss_end     - End of BSS section in RAM
@   _data_load   - Load address of data section (in flash)
@   _data_start  - Start of data section in RAM
@   _data_end    - End of data section in RAM
@   _heap_start  - Start of heap
@   _heap_end    - End of heap
@
@ ============================================================================

    .syntax unified
    .cpu cortex-m3
    .thumb

@ ============================================================================
@ FIRMWARE HEADER (placed after vector table at 0x100)
@ ============================================================================
@
@ The firmware header allows the bootloader to validate and identify firmware.
@ Format (64 bytes):
@   Offset  Size  Field
@   0x00    4     Magic number (0x50594E58 = "PYNX")
@   0x04    4     CRC32 of firmware (excluding header)
@   0x08    4     Firmware size in bytes
@   0x0C    4     Version (major.minor.patch packed as 0xMMmmPPPP)
@   0x10    16    Build date string (null-terminated)
@   0x20    16    Version string (null-terminated)
@   0x30    4     Entry point address
@   0x34    4     Load address
@   0x38    4     Flags (FW_FLAG_*)
@   0x3C    4     Header CRC32
@
@ ============================================================================

@ Vector table
    .section .vectors, "a"
    .global _vectors
_vectors:
    .word _stack_top       @ 0x00: Initial stack pointer
    .word _reset           @ 0x04: Reset handler
    .word _nmi             @ 0x08: NMI handler
    .word _hardfault       @ 0x0C: Hard fault handler
    .word _memfault        @ 0x10: Memory fault handler
    .word _busfault        @ 0x14: Bus fault handler
    .word _usagefault      @ 0x18: Usage fault handler
    .word 0                @ 0x1C: Reserved
    .word 0                @ 0x20: Reserved
    .word 0                @ 0x24: Reserved
    .word 0                @ 0x28: Reserved
    .word _svc             @ 0x2C: SVC handler
    .word _debugmon        @ 0x30: Debug monitor handler
    .word 0                @ 0x34: Reserved
    .word _pendsv          @ 0x38: PendSV handler
    .word _systick         @ 0x3C: SysTick handler
    @ External interrupts (IRQ 0-239) would follow here
    @ For mps2-an385, we have up to 32 external interrupts
    .space 128             @ Reserve space for 32 IRQ vectors (32 * 4 = 128)

@ Firmware header at fixed offset 0x100 (256 bytes from start)
    .section .fw_header, "a"
    .global _fw_header
_fw_header:
    .word 0x50594E58       @ Magic "PYNX"
    .word 0x00000000       @ CRC32 (filled by build tool)
    .word 0x00000000       @ Firmware size (filled by build tool)
    .word 0x00000100       @ Version 0.1.0
    .ascii "Dec 30 2025\0\0\0\0\0"  @ Build date (16 bytes)
    .ascii "0.1.0\0\0\0\0\0\0\0\0\0\0\0"  @ Version string (16 bytes)
    .word _reset           @ Entry point
    .word 0x00000000       @ Load address
    .word 0x00000008       @ Flags (FW_FLAG_DEBUG)
    .word 0x00000000       @ Header CRC (filled by build tool)

@ ============================================================================
@ BOOT REASON CODES (for kernel/boot.py)
@ ============================================================================
@
@ BOOT_COLD     = 0  - Power-on reset
@ BOOT_WARM     = 1  - Software reset
@ BOOT_WATCHDOG = 2  - Watchdog timeout
@ BOOT_UPDATE   = 3  - Reset after firmware update
@ BOOT_FAULT    = 4  - Hard fault recovery
@ BOOT_BROWNOUT = 5  - Low voltage reset
@ BOOT_EXTERNAL = 6  - External reset pin
@
@ The boot reason is detected by reading the RCC_CSR register flags.
@ These flags persist across reset and must be cleared after reading.
@
@ ============================================================================

@ Text section
    .section .text
    .thumb_func
    .global _reset
    .type _reset, %function
_reset:
    @ ========================================================================
    @ STEP 1: Stack Initialization
    @ ========================================================================
    @ Hardware already loaded SP from vector table, but we set it explicitly
    @ for safety (e.g., if jumping here from bootloader or debugger)
    ldr r0, =_stack_top
    mov sp, r0

    @ Ensure we're in Thread mode with MSP
    @ (Should already be the case after reset)
    mrs r0, CONTROL
    bic r0, r0, #0x03      @ Clear SPSEL and nPRIV bits
    msr CONTROL, r0
    isb                    @ Instruction barrier after CONTROL write

    @ ========================================================================
    @ STEP 2: Early Hardware Initialization
    @ ========================================================================
    @ Disable interrupts during initialization
    cpsid i

    @ Configure fault handlers (enable UsageFault, BusFault, MemManage)
    ldr r0, =0xE000ED24    @ SHCSR (System Handler Control and State)
    ldr r1, [r0]
    orr r1, r1, #0x70000   @ Enable UsageFault, BusFault, MemManage
    str r1, [r0]

    @ Set priority grouping (all bits for preemption priority)
    ldr r0, =0xE000ED0C    @ AIRCR
    ldr r1, =0x05FA0300    @ VECTKEY | PRIGROUP=3
    str r1, [r0]
    dsb
    isb

    @ ========================================================================
    @ STEP 3: BSS Section Zeroing
    @ ========================================================================
    @ Zero all uninitialized global/static variables
    ldr r0, =_bss_start
    ldr r1, =_bss_end
    movs r2, #0
.zero_bss:
    cmp r0, r1
    bge .bss_done
    str r2, [r0]
    adds r0, r0, #4
    b .zero_bss
.bss_done:

    @ ========================================================================
    @ STEP 4: Data Section Copy (Flash -> RAM)
    @ ========================================================================
    @ Copy initialized data from flash (LMA) to RAM (VMA)
    ldr r0, =_data_load    @ Source (in flash)
    ldr r1, =_data_start   @ Destination (in RAM)
    ldr r2, =_data_end
.copy_data:
    cmp r1, r2
    bge .data_done
    ldr r3, [r0]
    str r3, [r1]
    adds r0, r0, #4
    adds r1, r1, #4
    b .copy_data
.data_done:

    @ Memory barrier after data initialization
    dsb
    isb

    @ ========================================================================
    @ STEP 5: FPU Initialization (if present - Cortex-M4F/M7)
    @ ========================================================================
    @ Cortex-M3 does not have FPU, skip this section
    @ For M4F/M7, would enable CP10/CP11 in CPACR

    @ ========================================================================
    @ STEP 6: Clock Configuration
    @ ========================================================================
    @ For QEMU mps2-an385, clocks are pre-configured
    @ Real hardware would configure PLL, flash wait states, etc.
    @ bl clock_init

    @ ========================================================================
    @ STEP 7: Watchdog Configuration
    @ ========================================================================
    @ Optionally start watchdog early for boot protection
    @ bl watchdog_init

    @ ========================================================================
    @ STEP 8: UART Initialization (for debug output)
    @ ========================================================================
    bl uart_init

    @ ========================================================================
    @ STEP 9: Boot Initialization (kernel/boot.py)
    @ ========================================================================
    @ Detect boot reason, validate firmware CRC
    bl boot_init

    @ ========================================================================
    @ STEP 10: Enable Interrupts
    @ ========================================================================
    cpsie i

    @ ========================================================================
    @ STEP 11: Call main()
    @ ========================================================================
    bl main

    @ ========================================================================
    @ STEP 12: Post-main Handling
    @ ========================================================================
    @ If main returns, disable interrupts and halt
    cpsid i
.halt_loop:
    wfi                    @ Wait for interrupt (low power)
    b .halt_loop

    .size _reset, . - _reset

@ Default exception handlers (infinite loop)
    .thumb_func
    .weak _nmi
    .type _nmi, %function
_nmi:
    b .
    .size _nmi, . - _nmi

    .thumb_func
    .weak _hardfault
    .type _hardfault, %function
_hardfault:
    b .
    .size _hardfault, . - _hardfault

    .thumb_func
    .weak _memfault
    .type _memfault, %function
_memfault:
    b .
    .size _memfault, . - _memfault

    .thumb_func
    .weak _busfault
    .type _busfault, %function
_busfault:
    b .
    .size _busfault, . - _busfault

    .thumb_func
    .weak _usagefault
    .type _usagefault, %function
_usagefault:
    b .
    .size _usagefault, . - _usagefault

    .thumb_func
    .weak _svc
    .type _svc, %function
_svc:
    b .
    .size _svc, . - _svc

    .thumb_func
    .weak _debugmon
    .type _debugmon, %function
_debugmon:
    b .
    .size _debugmon, . - _debugmon

    .thumb_func
    .weak _pendsv
    .type _pendsv, %function
_pendsv:
    b .
    .size _pendsv, . - _pendsv

    .thumb_func
    .global _systick
    .type _systick, %function
_systick:
    @ SysTick interrupt handler - increment kernel timer
    push {lr}
    bl timer_tick
    pop {pc}
    .size _systick, . - _systick

@ End of startup.s
