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

@ int __pynux_strlen(const char* s)
@ Get string length
    .global __pynux_strlen
    .type __pynux_strlen, %function
__pynux_strlen:
    mov r1, r0         @ save string pointer
    movs r0, #0        @ length = 0
.strlen_loop:
    ldrb r2, [r1]
    cmp r2, #0
    beq .strlen_done
    adds r0, r0, #1
    adds r1, r1, #1
    b .strlen_loop
.strlen_done:
    bx lr
    .size __pynux_strlen, . - __pynux_strlen

@ char* __pynux_read_line(char* buf)
@ Read line from UART into buffer (expects buffer address in r0)
@ Returns when newline received, null-terminates the string
    .global __pynux_read_line
    .type __pynux_read_line, %function
__pynux_read_line:
    push {r4, r5, lr}
    mov r4, r0         @ buffer pointer
    mov r5, r0         @ save start
.read_line_loop:
    bl uart_getc       @ get character
    cmp r0, #'\r'      @ carriage return?
    beq .read_line_done
    cmp r0, #'\n'      @ newline?
    beq .read_line_done
    cmp r0, #8         @ backspace?
    beq .read_line_back
    cmp r0, #127       @ DEL?
    beq .read_line_back
    strb r0, [r4]      @ store character
    adds r4, r4, #1
    bl uart_putc       @ echo character
    b .read_line_loop
.read_line_back:
    cmp r4, r5         @ at start?
    beq .read_line_loop
    subs r4, r4, #1
    movs r0, #8        @ backspace
    bl uart_putc
    movs r0, #' '      @ space
    bl uart_putc
    movs r0, #8        @ backspace
    bl uart_putc
    b .read_line_loop
.read_line_done:
    movs r0, #0
    strb r0, [r4]      @ null terminate
    movs r0, #'\n'
    bl uart_putc       @ echo newline
    mov r0, r5         @ return buffer start
    pop {r4, r5, pc}
    .size __pynux_read_line, . - __pynux_read_line

@ bool __pynux_in(int needle, void* haystack)
@ Check if needle is in haystack (string char check or list membership)
@ For strings: r0 = char, r1 = string pointer, returns 1 if char in string
    .global __pynux_in
    .type __pynux_in, %function
__pynux_in:
    @ Assume string search for now (char in string)
    push {r4, lr}
    mov r4, r0         @ save needle (char value)
.in_loop:
    ldrb r0, [r1]      @ load character from haystack
    cmp r0, #0         @ end of string?
    beq .in_not_found
    cmp r0, r4         @ found?
    beq .in_found
    adds r1, r1, #1
    b .in_loop
.in_found:
    movs r0, #1
    pop {r4, pc}
.in_not_found:
    movs r0, #0
    pop {r4, pc}
    .size __pynux_in, . - __pynux_in

@ char* __pynux_strcat(char* dest, const char* src)
@ Concatenate src to dest, return dest
@ Note: caller must ensure dest has enough space
    .global __pynux_strcat
    .type __pynux_strcat, %function
__pynux_strcat:
    push {r4, r5, lr}
    mov r4, r0         @ save dest
    mov r5, r1         @ save src
    @ Find end of dest
.strcat_find_end:
    ldrb r2, [r0]
    cmp r2, #0
    beq .strcat_copy
    adds r0, r0, #1
    b .strcat_find_end
.strcat_copy:
    ldrb r2, [r5]
    strb r2, [r0]
    cmp r2, #0
    beq .strcat_done
    adds r0, r0, #1
    adds r5, r5, #1
    b .strcat_copy
.strcat_done:
    mov r0, r4         @ return dest
    pop {r4, r5, pc}
    .size __pynux_strcat, . - __pynux_strcat

@ char* __pynux_strcpy(char* dest, const char* src)
@ Copy src to dest, return dest
    .global __pynux_strcpy
    .type __pynux_strcpy, %function
__pynux_strcpy:
    push {r4, lr}
    mov r4, r0         @ save dest
.strcpy_loop:
    ldrb r2, [r1]
    strb r2, [r0]
    cmp r2, #0
    beq .strcpy_done
    adds r0, r0, #1
    adds r1, r1, #1
    b .strcpy_loop
.strcpy_done:
    mov r0, r4         @ return dest
    pop {r4, pc}
    .size __pynux_strcpy, . - __pynux_strcpy

@ int __pynux_strcmp(const char* s1, const char* s2)
@ Compare two strings, return 0 if equal
    .global __pynux_strcmp
    .type __pynux_strcmp, %function
__pynux_strcmp:
.strcmp_loop:
    ldrb r2, [r0]
    ldrb r3, [r1]
    cmp r2, r3
    bne .strcmp_diff
    cmp r2, #0         @ both null?
    beq .strcmp_equal
    adds r0, r0, #1
    adds r1, r1, #1
    b .strcmp_loop
.strcmp_equal:
    movs r0, #0
    bx lr
.strcmp_diff:
    subs r0, r2, r3
    bx lr
    .size __pynux_strcmp, . - __pynux_strcmp

@ void* __pynux_memcpy(void* dest, const void* src, int n)
@ Copy n bytes from src to dest
    .global __pynux_memcpy
    .type __pynux_memcpy, %function
__pynux_memcpy:
    push {r4, lr}
    mov r4, r0         @ save dest
.memcpy_loop:
    cmp r2, #0
    beq .memcpy_done
    ldrb r3, [r1]
    strb r3, [r0]
    adds r0, r0, #1
    adds r1, r1, #1
    subs r2, r2, #1
    b .memcpy_loop
.memcpy_done:
    mov r0, r4
    pop {r4, pc}
    .size __pynux_memcpy, . - __pynux_memcpy

@ void* __pynux_memset(void* dest, int c, int n)
@ Set n bytes to value c
    .global __pynux_memset
    .type __pynux_memset, %function
__pynux_memset:
    push {r4, lr}
    mov r4, r0         @ save dest
.memset_loop:
    cmp r2, #0
    beq .memset_done
    strb r1, [r0]
    adds r0, r0, #1
    subs r2, r2, #1
    b .memset_loop
.memset_done:
    mov r0, r4
    pop {r4, pc}
    .size __pynux_memset, . - __pynux_memset

@ ============================================================================
@ String Methods
@ ============================================================================

@ char* __pynux_str_upper(const char* s)
@ Convert string to uppercase, returns new string
    .global __pynux_str_upper
    .type __pynux_str_upper, %function
__pynux_str_upper:
    push {r4, r5, r6, r7, lr}
    mov r4, r0         @ source string
    @ Get length
    bl __pynux_strlen
    mov r5, r0         @ length
    add r0, r5, #1
    bl malloc
    mov r6, r0         @ destination (working pointer)
    mov r7, r0         @ save original destination for return

.upper_loop:
    ldrb r0, [r4]
    cmp r0, #0
    beq .upper_done
    @ Check if lowercase letter (a-z = 97-122)
    cmp r0, #97
    blt .upper_store
    cmp r0, #122
    bgt .upper_store
    sub r0, r0, #32    @ Convert to uppercase
.upper_store:
    strb r0, [r6]
    adds r4, r4, #1
    adds r6, r6, #1
    b .upper_loop
.upper_done:
    movs r0, #0
    strb r0, [r6]      @ Null terminate
    mov r0, r7         @ Return start of new string
    pop {r4, r5, r6, r7, pc}
    .size __pynux_str_upper, . - __pynux_str_upper

@ char* __pynux_str_lower(const char* s)
@ Convert string to lowercase, returns new string
    .global __pynux_str_lower
    .type __pynux_str_lower, %function
__pynux_str_lower:
    push {r4, r5, r6, r7, lr}
    mov r4, r0         @ source string
    bl __pynux_strlen
    mov r5, r0
    add r0, r5, #1
    bl malloc
    mov r6, r0         @ destination (working pointer)
    mov r7, r0         @ save original destination for return

.lower_loop:
    ldrb r0, [r4]
    cmp r0, #0
    beq .lower_done
    @ Check if uppercase letter (A-Z = 65-90)
    cmp r0, #65
    blt .lower_store
    cmp r0, #90
    bgt .lower_store
    add r0, r0, #32    @ Convert to lowercase
.lower_store:
    strb r0, [r6]
    adds r4, r4, #1
    adds r6, r6, #1
    b .lower_loop
.lower_done:
    movs r0, #0
    strb r0, [r6]      @ Null terminate
    mov r0, r7         @ Return start of new string
    pop {r4, r5, r6, r7, pc}
    .size __pynux_str_lower, . - __pynux_str_lower

@ char* __pynux_str_strip(const char* s)
@ Remove leading and trailing whitespace, returns new string
    .global __pynux_str_strip
    .type __pynux_str_strip, %function
__pynux_str_strip:
    push {r4, r5, r6, r7, lr}
    mov r4, r0         @ source

    @ Find first non-whitespace
.strip_start:
    ldrb r0, [r4]
    cmp r0, #0
    beq .strip_empty
    cmp r0, #' '
    beq .strip_skip
    cmp r0, #'\t'
    beq .strip_skip
    cmp r0, #'\n'
    beq .strip_skip
    cmp r0, #'\r'
    beq .strip_skip
    b .strip_find_end
.strip_skip:
    adds r4, r4, #1
    b .strip_start

.strip_find_end:
    mov r5, r4         @ start of content
    @ Find end of string
    mov r0, r4
    bl __pynux_strlen
    add r6, r4, r0     @ end pointer
    @ Move back over trailing whitespace
.strip_end:
    subs r6, r6, #1
    cmp r6, r5
    blt .strip_empty
    ldrb r0, [r6]
    cmp r0, #' '
    beq .strip_end
    cmp r0, #'\t'
    beq .strip_end
    cmp r0, #'\n'
    beq .strip_end
    cmp r0, #'\r'
    beq .strip_end

    @ Calculate length and allocate
    sub r7, r6, r5
    add r7, r7, #1     @ length
    add r0, r7, #1     @ +1 for null
    bl malloc
    mov r6, r0         @ destination
    @ Copy
.strip_copy:
    ldrb r0, [r5]
    strb r0, [r6]
    adds r5, r5, #1
    adds r6, r6, #1
    subs r7, r7, #1
    bne .strip_copy
    movs r0, #0
    strb r0, [r6]      @ null terminate
    sub r0, r6, r7     @ This gives us back the start
    @ Actually we need to fix this - let's recalculate
    sub r6, r6, #1
.strip_back:
    ldrb r1, [r6]
    cmp r1, #0
    beq .strip_return
    subs r6, r6, #1
    b .strip_back
.strip_return:
    add r0, r6, #1
    pop {r4, r5, r6, r7, pc}

.strip_empty:
    movs r0, #1
    bl malloc
    movs r1, #0
    strb r1, [r0]
    pop {r4, r5, r6, r7, pc}
    .size __pynux_str_strip, . - __pynux_str_strip

@ bool __pynux_str_startswith(const char* s, const char* prefix)
@ Check if string starts with prefix
    .global __pynux_str_startswith
    .type __pynux_str_startswith, %function
__pynux_str_startswith:
    push {r4, r5, lr}
    mov r4, r0         @ string
    mov r5, r1         @ prefix
.startswith_loop:
    ldrb r0, [r5]
    cmp r0, #0
    beq .startswith_yes   @ End of prefix, matched!
    ldrb r1, [r4]
    cmp r0, r1
    bne .startswith_no
    adds r4, r4, #1
    adds r5, r5, #1
    b .startswith_loop
.startswith_yes:
    movs r0, #1
    pop {r4, r5, pc}
.startswith_no:
    movs r0, #0
    pop {r4, r5, pc}
    .size __pynux_str_startswith, . - __pynux_str_startswith

@ bool __pynux_str_endswith(const char* s, const char* suffix)
@ Check if string ends with suffix
    .global __pynux_str_endswith
    .type __pynux_str_endswith, %function
__pynux_str_endswith:
    push {r4, r5, r6, r7, lr}
    mov r4, r0         @ string
    mov r5, r1         @ suffix
    @ Get lengths
    bl __pynux_strlen
    mov r6, r0         @ string length
    mov r0, r5
    bl __pynux_strlen
    mov r7, r0         @ suffix length
    @ Check if suffix is longer than string
    cmp r7, r6
    bgt .endswith_no
    @ Compare from end
    add r4, r4, r6
    sub r4, r4, r7     @ Position in string to compare
.endswith_loop:
    ldrb r0, [r5]
    cmp r0, #0
    beq .endswith_yes
    ldrb r1, [r4]
    cmp r0, r1
    bne .endswith_no
    adds r4, r4, #1
    adds r5, r5, #1
    b .endswith_loop
.endswith_yes:
    movs r0, #1
    pop {r4, r5, r6, r7, pc}
.endswith_no:
    movs r0, #0
    pop {r4, r5, r6, r7, pc}
    .size __pynux_str_endswith, . - __pynux_str_endswith

@ int __pynux_str_find(const char* s, const char* sub)
@ Find first occurrence of substring, returns index or -1
    .global __pynux_str_find
    .type __pynux_str_find, %function
__pynux_str_find:
    push {r4, r5, r6, r7, lr}
    mov r4, r0         @ string
    mov r5, r1         @ substring
    movs r6, #0        @ index
.find_outer:
    ldrb r0, [r4]
    cmp r0, #0
    beq .find_notfound
    @ Try to match substring here
    mov r7, r4
    push {r5}
.find_inner:
    ldrb r0, [r5]
    cmp r0, #0
    beq .find_found    @ End of substring, found!
    ldrb r1, [r7]
    cmp r1, #0
    beq .find_inner_fail
    cmp r0, r1
    bne .find_inner_fail
    adds r5, r5, #1
    adds r7, r7, #1
    b .find_inner
.find_inner_fail:
    pop {r5}
    adds r4, r4, #1
    adds r6, r6, #1
    b .find_outer
.find_found:
    pop {r5}
    mov r0, r6
    pop {r4, r5, r6, r7, pc}
.find_notfound:
    mov r0, #-1
    pop {r4, r5, r6, r7, pc}
    .size __pynux_str_find, . - __pynux_str_find

@ bool __pynux_str_isdigit(const char* s)
@ Check if all characters are digits
    .global __pynux_str_isdigit
    .type __pynux_str_isdigit, %function
__pynux_str_isdigit:
    push {r4, lr}
    mov r4, r0
    ldrb r0, [r4]
    cmp r0, #0
    beq .isdigit_empty
.isdigit_loop:
    ldrb r0, [r4]
    cmp r0, #0
    beq .isdigit_yes
    cmp r0, #'0'
    blt .isdigit_no
    cmp r0, #'9'
    bgt .isdigit_no
    adds r4, r4, #1
    b .isdigit_loop
.isdigit_yes:
    movs r0, #1
    pop {r4, pc}
.isdigit_no:
.isdigit_empty:
    movs r0, #0
    pop {r4, pc}
    .size __pynux_str_isdigit, . - __pynux_str_isdigit

@ bool __pynux_str_isalpha(const char* s)
@ Check if all characters are alphabetic
    .global __pynux_str_isalpha
    .type __pynux_str_isalpha, %function
__pynux_str_isalpha:
    push {r4, lr}
    mov r4, r0
    ldrb r0, [r4]
    cmp r0, #0
    beq .isalpha_empty
.isalpha_loop:
    ldrb r0, [r4]
    cmp r0, #0
    beq .isalpha_yes
    @ Check A-Z (65-90)
    cmp r0, #65
    blt .isalpha_check_lower
    cmp r0, #90
    ble .isalpha_next
.isalpha_check_lower:
    @ Check a-z (97-122)
    cmp r0, #97
    blt .isalpha_no
    cmp r0, #122
    bgt .isalpha_no
.isalpha_next:
    adds r4, r4, #1
    b .isalpha_loop
.isalpha_yes:
    movs r0, #1
    pop {r4, pc}
.isalpha_no:
.isalpha_empty:
    movs r0, #0
    pop {r4, pc}
    .size __pynux_str_isalpha, . - __pynux_str_isalpha

@ Exception handling stubs
    .global __pynux_raise
    .type __pynux_raise, %function
__pynux_raise:
    push {lr}
    ldr r0, =.raise_msg
    bl print_str
.raise_halt:
    b .raise_halt
    .size __pynux_raise, . - __pynux_raise

    .global __pynux_reraise
    .type __pynux_reraise, %function
__pynux_reraise:
    b __pynux_raise
    .size __pynux_reraise, . - __pynux_reraise

@ ============================================================================
@ Generator Support
@ ============================================================================

@ void* __pynux_generator_next(void* gen)
@ Get next value from generator, returns 0 if exhausted
    .global __pynux_generator_next
    .type __pynux_generator_next, %function
__pynux_generator_next:
    push {lr}
    @ Check if generator is exhausted
    ldr r1, =__generator_state
    ldr r1, [r1]
    cmp r1, #2          @ 2 = exhausted
    beq .gen_exhausted
    @ Resume generator - for now just return the yielded value
    ldr r0, =__generator_value
    ldr r0, [r0]
    pop {pc}
.gen_exhausted:
    movs r0, #0
    pop {pc}
    .size __pynux_generator_next, . - __pynux_generator_next

@ ============================================================================
@ Context Manager Support
@ ============================================================================

@ void* __pynux_context_enter(void* ctx)
@ Call context manager __enter__ method
    .global __pynux_context_enter
    .type __pynux_context_enter, %function
__pynux_context_enter:
    @ Simple implementation: just return the context manager itself
    @ A real implementation would call obj.__enter__()
    bx lr
    .size __pynux_context_enter, . - __pynux_context_enter

@ void __pynux_context_exit(void* ctx)
@ Call context manager __exit__ method
    .global __pynux_context_exit
    .type __pynux_context_exit, %function
__pynux_context_exit:
    @ Simple implementation: no-op
    @ A real implementation would call obj.__exit__(None, None, None)
    bx lr
    .size __pynux_context_exit, . - __pynux_context_exit

@ Dictionary functions
@ int32 __pynux_dict_get_int(dict* d, int32 key)
@ Dict layout: [count, key0, val0, key1, val1, ...]
@ Returns value for integer key, or 0 if not found
    .global __pynux_dict_get_int
    .type __pynux_dict_get_int, %function
__pynux_dict_get_int:
    push {r4, r5, r6, lr}
    mov r4, r0          @ r4 = dict pointer
    mov r5, r1          @ r5 = key to find
    ldr r6, [r4]        @ r6 = count
    add r4, r4, #4      @ r4 = &pairs[0]
.dict_int_loop:
    cmp r6, #0
    beq .dict_int_notfound
    ldr r0, [r4]        @ r0 = current key
    cmp r0, r5
    beq .dict_int_found
    add r4, r4, #8      @ next pair
    sub r6, r6, #1
    b .dict_int_loop
.dict_int_found:
    ldr r0, [r4, #4]    @ return value
    pop {r4, r5, r6, pc}
.dict_int_notfound:
    movs r0, #0         @ return 0 if not found
    pop {r4, r5, r6, pc}
    .size __pynux_dict_get_int, . - __pynux_dict_get_int

@ int32 __pynux_dict_get_str(dict* d, char* key)
@ Returns value for string key, or 0 if not found
    .global __pynux_dict_get_str
    .type __pynux_dict_get_str, %function
__pynux_dict_get_str:
    push {r4, r5, r6, r7, lr}
    mov r4, r0          @ r4 = dict pointer
    mov r5, r1          @ r5 = key to find
    ldr r6, [r4]        @ r6 = count
    add r4, r4, #4      @ r4 = &pairs[0]
.dict_str_loop:
    cmp r6, #0
    beq .dict_str_notfound
    ldr r0, [r4]        @ r0 = current key (string ptr)
    mov r1, r5          @ r1 = search key
    bl __pynux_strcmp
    cmp r0, #0
    beq .dict_str_found
    add r4, r4, #8      @ next pair
    sub r6, r6, #1
    b .dict_str_loop
.dict_str_found:
    ldr r0, [r4, #4]    @ return value
    pop {r4, r5, r6, r7, pc}
.dict_str_notfound:
    movs r0, #0         @ return 0 if not found
    pop {r4, r5, r6, r7, pc}
    .size __pynux_dict_get_str, . - __pynux_dict_get_str

@ void __pynux_dict_set_int(dict* d, int32 key, int32 value)
@ Sets value for integer key (if key exists, updates; otherwise adds at end)
    .global __pynux_dict_set_int
    .type __pynux_dict_set_int, %function
__pynux_dict_set_int:
    push {r4, r5, r6, r7, lr}
    mov r4, r0          @ r4 = dict pointer
    mov r5, r1          @ r5 = key
    mov r7, r2          @ r7 = value
    ldr r6, [r4]        @ r6 = count
    add r0, r4, #4      @ r0 = &pairs[0]
.dict_set_int_loop:
    cmp r6, #0
    beq .dict_set_int_add
    ldr r1, [r0]        @ r1 = current key
    cmp r1, r5
    beq .dict_set_int_update
    add r0, r0, #8      @ next pair
    sub r6, r6, #1
    b .dict_set_int_loop
.dict_set_int_update:
    str r7, [r0, #4]    @ update value
    pop {r4, r5, r6, r7, pc}
.dict_set_int_add:
    @ Add new key-value pair at end
    ldr r6, [r4]        @ get count again
    add r0, r4, #4      @ base of pairs
    lsl r1, r6, #3      @ offset = count * 8
    add r0, r0, r1      @ r0 = &pairs[count]
    str r5, [r0]        @ store key
    str r7, [r0, #4]    @ store value
    add r6, r6, #1      @ increment count
    str r6, [r4]
    pop {r4, r5, r6, r7, pc}
    .size __pynux_dict_set_int, . - __pynux_dict_set_int

@ Slicing functions
@ char* __pynux_slice(char* str, int32 start, int32 end, int32 step)
@ Returns a new string containing the slice [start:end:step]
@ If end == -1, uses strlen as end
    .global __pynux_slice
    .type __pynux_slice, %function
__pynux_slice:
    push {r4, r5, r6, r7, lr}
    sub sp, sp, #12     @ Reserve space for locals
    mov r4, r0          @ r4 = source string
    mov r5, r1          @ r5 = start
    mov r6, r2          @ r6 = end
    str r3, [sp, #0]    @ step on stack

    @ Get string length
    bl __pynux_strlen
    mov r7, r0          @ r7 = strlen

    @ Handle negative start
    cmp r5, #0
    bge .slice_start_ok
    add r5, r5, r7      @ start += len
    cmp r5, #0
    bge .slice_start_ok
    movs r5, #0         @ clamp to 0
.slice_start_ok:

    @ Handle end == -1 (means "to end")
    cmp r6, #-1
    bne .slice_check_neg_end
    mov r6, r7          @ end = len
    b .slice_end_ok
.slice_check_neg_end:
    @ Handle negative end
    cmp r6, #0
    bge .slice_clamp_end
    add r6, r6, r7      @ end += len
.slice_clamp_end:
    @ Clamp end to length
    cmp r6, r7
    ble .slice_end_ok
    mov r6, r7
.slice_end_ok:

    @ Calculate result length: (end - start + step - 1) / step
    @ For step=1: just end - start
    ldr r3, [sp, #0]    @ get step
    cmp r3, #1
    bne .slice_calc_len_step
    sub r0, r6, r5      @ len = end - start
    b .slice_len_done
.slice_calc_len_step:
    sub r0, r6, r5      @ end - start
    add r0, r0, r3      @ + step
    sub r0, r0, #1      @ - 1
    @ divide by step (assume step > 0)
    mov r1, r3
    bl __aeabi_idiv
.slice_len_done:
    cmp r0, #0
    bgt .slice_has_len
    movs r0, #0         @ empty string
    b .slice_return_empty
.slice_has_len:
    str r0, [sp, #4]    @ save result length

    @ Allocate result string
    add r0, r0, #1      @ +1 for null terminator
    bl malloc
    str r0, [sp, #8]    @ save result ptr

    @ Copy characters
    ldr r0, [sp, #8]    @ dest
    mov r1, r4          @ source
    add r1, r1, r5      @ source + start
    ldr r2, [sp, #4]    @ length
    ldr r3, [sp, #0]    @ step

.slice_copy_loop:
    cmp r2, #0
    beq .slice_copy_done
    ldrb r7, [r1]       @ load char from source
    strb r7, [r0]       @ store to dest
    add r0, r0, #1      @ dest++
    add r1, r1, r3      @ source += step
    sub r2, r2, #1      @ length--
    b .slice_copy_loop

.slice_copy_done:
    movs r7, #0
    strb r7, [r0]       @ null terminate
    ldr r0, [sp, #8]    @ return result ptr
    add sp, sp, #12
    pop {r4, r5, r6, r7, pc}

.slice_return_empty:
    @ Allocate empty string
    movs r0, #1
    bl malloc
    movs r1, #0
    strb r1, [r0]       @ empty null-terminated string
    add sp, sp, #12
    pop {r4, r5, r6, r7, pc}
    .size __pynux_slice, . - __pynux_slice

    .section .rodata
.raise_msg:
    .asciz "Exception raised\n"
    .align 2
.assert_msg:
    .asciz "Assertion failed: "
    .align 2
.newline:
    .asciz "\n"
    .align 2

    .section .data
_heap_ptr:
    .long _heap_start

@ Generator state storage
    .global __generator_state
__generator_state:
    .long 0            @ 0 = not started, 1 = yielded, 2 = exhausted

    .global __generator_value
__generator_value:
    .long 0            @ Last yielded value

    .section .bss
    .global _heap_start
_heap_start:
    .space 4096        @ 4KB heap

@ End of io.s
