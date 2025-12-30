@ Pynux ARM Cortex-M3 Startup Code
@ Target: QEMU mps2-an385

    .syntax unified
    .cpu cortex-m3
    .thumb

@ Vector table
    .section .vectors, "a"
    .global _vectors
_vectors:
    .word _stack_top       @ Initial stack pointer
    .word _reset           @ Reset handler
    .word _nmi             @ NMI handler
    .word _hardfault       @ Hard fault handler
    .word _memfault        @ Memory fault handler
    .word _busfault        @ Bus fault handler
    .word _usagefault      @ Usage fault handler
    .word 0                @ Reserved
    .word 0                @ Reserved
    .word 0                @ Reserved
    .word 0                @ Reserved
    .word _svc             @ SVC handler
    .word _debugmon        @ Debug monitor handler
    .word 0                @ Reserved
    .word _pendsv          @ PendSV handler
    .word _systick         @ SysTick handler

@ Text section
    .section .text
    .thumb_func
    .global _reset
    .type _reset, %function
_reset:
    @ Set up stack pointer (already done by hardware from vector table)
    ldr r0, =_stack_top
    mov sp, r0

    @ Zero BSS section
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

    @ Copy data section from flash to RAM
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

    @ Initialize UART
    bl uart_init

    @ Call main
    bl main

    @ If main returns, loop forever
    b .

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
    .weak _systick
    .type _systick, %function
_systick:
    b .
    .size _systick, . - _systick

@ End of startup.s
