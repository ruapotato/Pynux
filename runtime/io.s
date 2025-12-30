@ Pynux I/O Library - ARM Assembly
@ UART output for mps2-an385

    .syntax unified
    .cpu cortex-m3
    .thumb

@ UART0 base address for MPS2-AN385 (CMSDK APB UART)
    .equ UART0_BASE, 0x40004000
    .equ UART0_DATA, 0x40004000
    .equ UART0_STATE, 0x40004004
    .equ UART0_CTRL, 0x40004008
    .equ UART0_BAUDDIV, 0x40004010

@ UART Control bits
    .equ UART_CTRL_TX_EN, 0x01
    .equ UART_CTRL_RX_EN, 0x02

    .section .text

@ void uart_init()
@ Initialize UART (enable TX)
    .global uart_init
    .type uart_init, %function
uart_init:
    ldr r0, =UART0_CTRL
    movs r1, #UART_CTRL_TX_EN
    str r1, [r0]
    bx lr
    .size uart_init, . - uart_init

@ void uart_putc(char c)
@ Write a single character to UART
    .global uart_putc
    .type uart_putc, %function
uart_putc:
    ldr r1, =UART0_DATA
    strb r0, [r1]
    bx lr
    .size uart_putc, . - uart_putc

@ void print_str(const char* s)
@ Print a null-terminated string
    .global print_str
    .type print_str, %function
print_str:
    push {r4, lr}
    mov r4, r0
.print_loop:
    ldrb r0, [r4]
    cmp r0, #0
    beq .print_done
    bl uart_putc
    adds r4, r4, #1
    b .print_loop
.print_done:
    pop {r4}
    pop {pc}
    .size print_str, . - print_str

@ void print_int(int32 n)
@ Print an integer in decimal
    .global print_int
    .type print_int, %function
print_int:
    push {r4, r5, r6, lr}
    mov r4, r0

    @ Handle negative
    cmp r4, #0
    bge .positive
    movs r0, #'-'
    bl uart_putc
    rsb r4, r4, #0

.positive:
    @ Count digits and build string on stack
    mov r5, sp
    movs r6, #0        @ digit count

.count_loop:
    mov r0, r4         @ numerator (the number)
    movs r1, #10       @ denominator
    bl __aeabi_uidivmod
    mov r4, r0         @ quotient
    adds r1, r1, #'0'  @ remainder + '0'
    push {r1}
    adds r6, r6, #1
    cmp r4, #0
    bne .count_loop

    @ Print digits (they're in reverse order on stack)
.print_digits:
    cmp r6, #0
    beq .print_int_done
    pop {r0}
    bl uart_putc
    subs r6, r6, #1
    b .print_digits

.print_int_done:
    pop {r4, r5, r6}
    pop {pc}
    .size print_int, . - print_int

@ void print_hex(uint32 n)
@ Print an integer in hexadecimal
    .global print_hex
    .type print_hex, %function
print_hex:
    push {r4, r5, lr}
    mov r4, r0

    @ Print "0x" prefix
    movs r0, #'0'
    bl uart_putc
    movs r0, #'x'
    bl uart_putc

    @ Print 8 hex digits
    movs r5, #8

.hex_loop:
    @ Get top nibble
    lsr r0, r4, #28
    cmp r0, #10
    blt .hex_digit
    adds r0, r0, #('a' - 10)
    b .hex_print
.hex_digit:
    adds r0, r0, #'0'
.hex_print:
    bl uart_putc
    lsl r4, r4, #4
    subs r5, r5, #1
    bne .hex_loop

    pop {r4, r5}
    pop {pc}
    .size print_hex, . - print_hex

@ void print_newline()
    .global print_newline
    .type print_newline, %function
print_newline:
    push {lr}
    movs r0, #'\n'
    bl uart_putc
    pop {pc}
    .size print_newline, . - print_newline

@ Simple division helper (needed for print_int)
@ unsigned __aeabi_uidivmod(unsigned numerator, unsigned denominator)
@ Returns quotient in r0, remainder in r1
    .global __aeabi_uidivmod
    .type __aeabi_uidivmod, %function
__aeabi_uidivmod:
    @ Simple restoring division
    push {r4}
    mov r4, r1         @ divisor
    movs r1, #0        @ quotient
    movs r2, #1        @ bit position

    @ Find highest bit of divisor that's <= numerator
.find_bit:
    cmp r4, r0
    bhi .divide
    cmp r4, #0x80000000
    bhs .divide
    lsl r4, r4, #1
    lsl r2, r2, #1
    b .find_bit

.divide:
    cmp r2, #0
    beq .div_done
    cmp r0, r4
    blo .div_next
    sub r0, r0, r4
    orr r1, r1, r2
.div_next:
    lsr r4, r4, #1
    lsr r2, r2, #1
    b .divide

.div_done:
    @ r0 = remainder, r1 = quotient
    mov r2, r0         @ save remainder
    mov r0, r1         @ quotient to r0
    mov r1, r2         @ remainder to r1
    pop {r4}
    bx lr
    .size __aeabi_uidivmod, . - __aeabi_uidivmod

@ Signed division
    .global __aeabi_idiv
    .type __aeabi_idiv, %function
__aeabi_idiv:
    push {r4, lr}
    movs r4, #0        @ sign flag

    cmp r0, #0
    bge .idiv_pos_num
    rsb r0, r0, #0
    eor r4, r4, #1
.idiv_pos_num:
    cmp r1, #0
    bge .idiv_pos_den
    rsb r1, r1, #0
    eor r4, r4, #1
.idiv_pos_den:

    bl __aeabi_uidivmod

    cmp r4, #0
    beq .idiv_done
    rsb r0, r0, #0
.idiv_done:
    pop {r4}
    pop {pc}
    .size __aeabi_idiv, . - __aeabi_idiv

@ Signed division with modulo
@ Returns quotient in r0, remainder in r1
    .global __aeabi_idivmod
    .type __aeabi_idivmod, %function
__aeabi_idivmod:
    push {r4, r5, lr}
    mov r4, r0         @ save original numerator sign
    mov r5, r1         @ save original denominator

    cmp r0, #0
    bge .idivmod_pos_num
    rsb r0, r0, #0     @ make numerator positive
.idivmod_pos_num:
    cmp r1, #0
    bge .idivmod_pos_den
    rsb r1, r1, #0     @ make denominator positive
.idivmod_pos_den:

    bl __aeabi_uidivmod  @ unsigned divide

    @ Adjust quotient sign
    cmp r4, #0
    bge .idivmod_check_den
    cmp r5, #0
    bge .idivmod_neg_quot
    b .idivmod_check_rem  @ both negative, quotient positive
.idivmod_check_den:
    cmp r5, #0
    bge .idivmod_check_rem  @ both positive, quotient positive
.idivmod_neg_quot:
    rsb r0, r0, #0     @ negate quotient

.idivmod_check_rem:
    @ Remainder has sign of numerator
    cmp r4, #0
    bge .idivmod_done
    rsb r1, r1, #0     @ negate remainder

.idivmod_done:
    pop {r4, r5}
    pop {pc}
    .size __aeabi_idivmod, . - __aeabi_idivmod

@ char uart_getc()
@ Read a character from UART (blocking)
    .global uart_getc
    .type uart_getc, %function
uart_getc:
    ldr r1, =UART0_STATE
.uart_getc_wait:
    ldr r0, [r1]
    tst r0, #0x02        @ RX buffer full bit
    beq .uart_getc_wait
    ldr r1, =UART0_DATA
    ldrb r0, [r1]
    bx lr
    .size uart_getc, . - uart_getc

@ bool uart_available()
@ Check if character available in RX buffer
    .global uart_available
    .type uart_available, %function
uart_available:
    ldr r1, =UART0_STATE
    ldr r0, [r1]
    and r0, r0, #0x02    @ RX buffer full bit
    lsr r0, r0, #1       @ Shift to bit 0
    bx lr
    .size uart_available, . - uart_available

@ void __pynux_assert_fail()
@ Called when assertion fails (no message)
    .global __pynux_assert_fail
    .type __pynux_assert_fail, %function
__pynux_assert_fail:
    push {lr}
    ldr r0, =.assert_msg
    bl print_str
.assert_halt:
    b .assert_halt  @ Infinite loop on assertion failure
    .size __pynux_assert_fail, . - __pynux_assert_fail

@ void __pynux_assert_fail_msg(const char* msg)
@ Called when assertion fails with message
    .global __pynux_assert_fail_msg
    .type __pynux_assert_fail_msg, %function
__pynux_assert_fail_msg:
    push {r4, lr}
    mov r4, r0
    ldr r0, =.assert_msg
    bl print_str
    mov r0, r4
    bl print_str
    ldr r0, =.newline
    bl print_str
.assert_halt_msg:
    b .assert_halt_msg
    .size __pynux_assert_fail_msg, . - __pynux_assert_fail_msg

@ int __pynux_pow(int base, int exp)
@ Integer power function
    .global __pynux_pow
    .type __pynux_pow, %function
__pynux_pow:
    push {r4, r5, lr}
    mov r4, r0         @ base
    mov r5, r1         @ exp
    movs r0, #1        @ result = 1
.pow_loop:
    cmp r5, #0
    beq .pow_done
    mul r0, r0, r4     @ result *= base
    subs r5, r5, #1    @ exp--
    b .pow_loop
.pow_done:
    pop {r4, r5, pc}
    .size __pynux_pow, . - __pynux_pow

@ Simple malloc - bump allocator from heap
    .global malloc
    .type malloc, %function
malloc:
    ldr r1, =_heap_ptr
    ldr r2, [r1]       @ current heap pointer
    add r3, r2, r0     @ new heap pointer
    add r3, r3, #3
    bic r3, r3, #3     @ align to 4 bytes
    str r3, [r1]       @ save new heap pointer
    mov r0, r2         @ return old pointer
    bx lr
    .size malloc, . - malloc

    .section .rodata
.assert_msg:
    .asciz "Assertion failed: "
    .align 2
.newline:
    .asciz "\n"
    .align 2

    .section .data
_heap_ptr:
    .long _heap_start

    .section .bss
    .global _heap_start
_heap_start:
    .space 4096        @ 4KB heap

@ End of io.s
