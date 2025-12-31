@ RP2040 Startup Code for Pynux
@
@ Boot sequence:
@   1. ROM bootloader loads boot2 (256 bytes) from flash
@   2. boot2 configures XIP flash and jumps to _reset
@   3. _reset initializes clocks, RAM, and calls kernel_main
@
@ Clock configuration:
@   - XOSC: 12MHz crystal
@   - PLL_SYS: 125MHz (12MHz * 125 / 6 / 2)
@   - System clock: 125MHz

    .syntax unified
    .cpu cortex-m0plus
    .thumb

@ ============================================================================
@ Boot2 Stage - Configure QSPI flash for XIP
@ ============================================================================
@ This is a minimal boot2 that works with most QSPI flash chips.
@ For production, use the official pico-sdk boot2 for your specific flash.

    .section .boot2, "ax"
    .align 2

boot2_entry:
    @ Disable XIP to configure SSI
    ldr r3, =0x18000000         @ XIP_SSI_BASE
    movs r0, #0
    str r0, [r3, #8]            @ SSIENR = 0 (disable)

    @ Configure SSI for standard SPI mode
    movs r0, #0                 @ Standard SPI frame format
    str r0, [r3, #4]            @ CTRLR0

    @ Set baud rate divider (conservative: divide by 4)
    movs r0, #4
    str r0, [r3, #0x14]         @ BAUDR

    @ Enable SSI
    movs r0, #1
    str r0, [r3, #8]            @ SSIENR = 1

    @ Jump to main code
    ldr r0, =_reset
    bx r0

    @ Pad to 252 bytes, then add CRC placeholder
    .align 2
    .space 252 - (. - boot2_entry)

    @ CRC32 placeholder (calculated by build system)
    .word 0x00000000

@ ============================================================================
@ Vector Table
@ ============================================================================

    .section .vectors, "ax"
    .align 8

    .global _vectors
_vectors:
    .word __stack_top           @ Initial stack pointer
    .word _reset                @ Reset handler
    .word _nmi_handler          @ NMI
    .word _hardfault_handler    @ HardFault
    .word 0                     @ Reserved (MemManage - not on M0+)
    .word 0                     @ Reserved (BusFault - not on M0+)
    .word 0                     @ Reserved (UsageFault - not on M0+)
    .word 0                     @ Reserved
    .word 0                     @ Reserved
    .word 0                     @ Reserved
    .word 0                     @ Reserved
    .word _svc_handler          @ SVCall
    .word 0                     @ Reserved (Debug Monitor - not on M0+)
    .word 0                     @ Reserved
    .word _pendsv_handler       @ PendSV
    .word _systick_handler      @ SysTick

    @ RP2040 IRQ handlers (32 IRQs)
    .word _irq0_handler         @ TIMER_IRQ_0
    .word _irq1_handler         @ TIMER_IRQ_1
    .word _irq2_handler         @ TIMER_IRQ_2
    .word _irq3_handler         @ TIMER_IRQ_3
    .word _irq4_handler         @ PWM_IRQ_WRAP
    .word _irq5_handler         @ USBCTRL_IRQ
    .word _irq6_handler         @ XIP_IRQ
    .word _irq7_handler         @ PIO0_IRQ_0
    .word _irq8_handler         @ PIO0_IRQ_1
    .word _irq9_handler         @ PIO1_IRQ_0
    .word _irq10_handler        @ PIO1_IRQ_1
    .word _irq11_handler        @ DMA_IRQ_0
    .word _irq12_handler        @ DMA_IRQ_1
    .word _irq13_handler        @ IO_IRQ_BANK0
    .word _irq14_handler        @ IO_IRQ_QSPI
    .word _irq15_handler        @ SIO_IRQ_PROC0
    .word _irq16_handler        @ SIO_IRQ_PROC1
    .word _irq17_handler        @ CLOCKS_IRQ
    .word _irq18_handler        @ SPI0_IRQ
    .word _irq19_handler        @ SPI1_IRQ
    .word _irq20_handler        @ UART0_IRQ
    .word _irq21_handler        @ UART1_IRQ
    .word _irq22_handler        @ ADC_IRQ_FIFO
    .word _irq23_handler        @ I2C0_IRQ
    .word _irq24_handler        @ I2C1_IRQ
    .word _irq25_handler        @ RTC_IRQ
    .word _default_handler      @ Reserved
    .word _default_handler      @ Reserved
    .word _default_handler      @ Reserved
    .word _default_handler      @ Reserved
    .word _default_handler      @ Reserved
    .word _default_handler      @ Reserved

@ ============================================================================
@ Reset Handler
@ ============================================================================

    .section .text
    .align 2
    .global _reset
    .thumb_func
_reset:
    @ Disable interrupts during init
    cpsid i

    @ Set stack pointer (redundant but safe)
    ldr r0, =__stack_top
    mov sp, r0

    @ Reset all peripherals except QSPI (already configured)
    bl rp2040_reset_peripherals

    @ Configure clocks to 125MHz
    bl rp2040_clock_init

    @ Zero BSS section
    ldr r0, =__bss_start
    ldr r1, =__bss_end
    movs r2, #0
bss_loop:
    cmp r0, r1
    bge bss_done
    stm r0!, {r2}
    b bss_loop
bss_done:

    @ Copy .data from flash to RAM
    ldr r0, =__data_start
    ldr r1, =__data_end
    ldr r2, =__data_load
data_loop:
    cmp r0, r1
    bge data_done
    ldm r2!, {r3}
    stm r0!, {r3}
    b data_loop
data_done:

    @ Initialize UART for debug output
    bl rp2040_uart_init

    @ Enable interrupts
    cpsie i

    @ Call kernel main
    bl kernel_main

    @ Halt if kernel returns
halt:
    wfi
    b halt

@ ============================================================================
@ Clock Initialization - Configure for 125MHz
@ ============================================================================

    .align 2
    .thumb_func
rp2040_clock_init:
    push {lr}

    @ === Start XOSC (12MHz crystal) ===
    ldr r3, =0x40024000         @ XOSC_BASE

    @ Set crystal frequency range (1-15MHz)
    ldr r0, =0xAA0              @ FREQ_RANGE = 1_15MHZ
    str r0, [r3, #0x00]         @ CTRL

    @ Set startup delay (~1ms at ring oscillator speed)
    ldr r0, =47                 @ STARTUP_DELAY
    str r0, [r3, #0x0C]         @ STARTUP

    @ Enable XOSC
    ldr r0, [r3, #0x00]
    ldr r1, =0xFAB000           @ ENABLE magic value
    orrs r0, r1
    str r0, [r3, #0x00]

    @ Wait for XOSC to stabilize
xosc_wait:
    ldr r0, [r3, #0x04]         @ STATUS
    lsrs r0, r0, #31            @ Check STABLE bit
    beq xosc_wait

    @ === Configure PLL_SYS for 125MHz ===
    @ Formula: (XOSC * FBDIV) / (POSTDIV1 * POSTDIV2)
    @ 125MHz = (12MHz * 125) / (6 * 2) = 1500 / 12 = 125

    ldr r3, =0x40028000         @ PLL_SYS_BASE

    @ Reset PLL
    ldr r4, =0x4000C000         @ RESETS_BASE
    ldr r0, [r4, #0x00]         @ RESET register
    ldr r1, =(1 << 12)          @ PLL_SYS reset bit
    orrs r0, r1
    str r0, [r4, #0x00]

    @ Unreset PLL
    bics r0, r1
    str r0, [r4, #0x00]

    @ Wait for PLL to come out of reset
pll_reset_wait:
    ldr r0, [r4, #0x08]         @ RESET_DONE
    tst r0, r1
    beq pll_reset_wait

    @ Configure PLL
    @ CS = 1 (reference = XOSC)
    movs r0, #1
    str r0, [r3, #0x00]         @ CS

    @ FBDIV = 125
    movs r0, #125
    str r0, [r3, #0x08]         @ FBDIV_INT

    @ Power on PLL (clear PD and VCOPD)
    ldr r0, [r3, #0x04]         @ PWR
    ldr r1, =0x21               @ PD | VCOPD
    bics r0, r1
    str r0, [r3, #0x04]

    @ Wait for PLL to lock
pll_lock_wait:
    ldr r0, [r3, #0x00]         @ CS
    lsrs r0, r0, #31            @ Check LOCK bit
    beq pll_lock_wait

    @ Configure post dividers: POSTDIV1=6, POSTDIV2=2
    ldr r0, =(6 << 16) | (2 << 12)
    str r0, [r3, #0x0C]         @ PRIM

    @ Enable post divider (clear POSTDIVPD)
    ldr r0, [r3, #0x04]
    ldr r1, =0x08               @ POSTDIVPD
    bics r0, r1
    str r0, [r3, #0x04]

    @ === Switch system clock to PLL ===
    ldr r3, =0x40008000         @ CLOCKS_BASE

    @ CLK_SYS: source = PLL_SYS (via CLKSRC_CLK_SYS_AUX)
    @ First set aux source to PLL_SYS
    movs r0, #0                 @ CLKSRC_PLL_SYS = 0
    str r0, [r3, #0x3C + 4]     @ CLK_SYS_CTRL offset, AUXSRC field

    @ Then switch to aux source
    ldr r0, [r3, #0x3C]         @ CLK_SYS_CTRL
    movs r1, #1                 @ SRC = 1 (aux)
    orrs r0, r1
    str r0, [r3, #0x3C]

    @ CLK_PERI: enable with PLL_SYS source for UART
    ldr r0, =(1 << 11)          @ ENABLE bit
    str r0, [r3, #0x48]         @ CLK_PERI_CTRL

    pop {pc}

@ ============================================================================
@ Reset Peripherals
@ ============================================================================

    .align 2
    .thumb_func
rp2040_reset_peripherals:
    push {lr}

    ldr r3, =0x4000C000         @ RESETS_BASE

    @ Reset most peripherals (not QSPI, PLL, PADS)
    ldr r0, =0x01FFFFFF         @ All reset bits
    ldr r1, =(1 << 6)           @ Keep IO_QSPI out of reset
    bics r0, r1
    str r0, [r3, #0x00]         @ RESET

    @ Unreset required peripherals
    @ UART0, GPIO, PADS_BANK0, IO_BANK0
    ldr r1, =(1 << 22) | (1 << 5) | (1 << 8) | (1 << 9)
    ldr r0, [r3, #0x00]
    bics r0, r1
    str r0, [r3, #0x00]

    @ Wait for unreset
unreset_wait:
    ldr r0, [r3, #0x08]         @ RESET_DONE
    tst r0, r1
    bne unreset_done
    b unreset_wait
unreset_done:

    pop {pc}

@ ============================================================================
@ UART Initialization (UART0 on GPIO0/1 at 115200 baud)
@ ============================================================================

    .align 2
    .thumb_func
    .global rp2040_uart_init
rp2040_uart_init:
    push {lr}

    @ Configure GPIO0 (TX) and GPIO1 (RX) for UART
    ldr r3, =0x40014000         @ IO_BANK0_BASE

    @ GPIO0: function 2 (UART0 TX)
    movs r0, #2
    str r0, [r3, #0x04]         @ GPIO0_CTRL

    @ GPIO1: function 2 (UART0 RX)
    str r0, [r3, #0x0C]         @ GPIO1_CTRL

    @ Configure UART0
    ldr r3, =0x40034000         @ UART0_BASE

    @ Disable UART during configuration
    movs r0, #0
    str r0, [r3, #0x30]         @ UARTCR

    @ Set baud rate for 115200 at 125MHz peripheral clock
    @ BAUDDIV = 125000000 / (16 * 115200) = 67.816
    @ IBRD = 67, FBRD = 52 (0.816 * 64 = 52.2)
    movs r0, #67
    str r0, [r3, #0x24]         @ UARTIBRD

    movs r0, #52
    str r0, [r3, #0x28]         @ UARTFBRD

    @ 8N1: 8 data bits, no parity, 1 stop bit, enable FIFOs
    movs r0, #(3 << 5) | (1 << 4)   @ WLEN=8, FEN=1
    str r0, [r3, #0x2C]         @ UARTLCR_H

    @ Enable UART, TX, RX
    movs r0, #(1 << 0) | (1 << 8) | (1 << 9)  @ UARTEN, TXE, RXE
    str r0, [r3, #0x30]         @ UARTCR

    pop {pc}

@ ============================================================================
@ UART I/O Functions
@ ============================================================================

    .align 2
    .global uart_putc
    .thumb_func
uart_putc:
    @ r0 = character to send
    ldr r1, =0x40034000         @ UART0_BASE
uart_putc_wait:
    ldr r2, [r1, #0x18]         @ UARTFR
    lsrs r2, r2, #6             @ Check TXFF bit
    bcs uart_putc_wait          @ Wait if FIFO full
    str r0, [r1, #0x00]         @ UARTDR
    bx lr

    .align 2
    .global uart_getc
    .thumb_func
uart_getc:
    ldr r1, =0x40034000         @ UART0_BASE
uart_getc_wait:
    ldr r2, [r1, #0x18]         @ UARTFR
    lsrs r2, r2, #5             @ Check RXFE bit
    bcs uart_getc_wait          @ Wait if FIFO empty
    ldr r0, [r1, #0x00]         @ UARTDR
    uxtb r0, r0                 @ Mask to 8 bits
    bx lr

    .align 2
    .global uart_tx_ready
    .thumb_func
uart_tx_ready:
    ldr r1, =0x40034000
    ldr r0, [r1, #0x18]         @ UARTFR
    lsrs r0, r0, #6             @ TXFF bit
    eors r0, r0, #1             @ Invert: 1 if ready
    bx lr

    .align 2
    .global uart_rx_ready
    .thumb_func
uart_rx_ready:
    ldr r1, =0x40034000
    ldr r0, [r1, #0x18]         @ UARTFR
    lsrs r0, r0, #5             @ RXFE bit
    eors r0, r0, #1             @ Invert: 1 if data available
    bx lr

@ ============================================================================
@ Exception Handlers
@ ============================================================================

    .align 2
    .global _nmi_handler
    .thumb_func
_nmi_handler:
    b .

    .align 2
    .global _hardfault_handler
    .thumb_func
_hardfault_handler:
    @ Could add debug output here
    b .

    .align 2
    .weak _svc_handler
    .thumb_func
_svc_handler:
    bx lr

    .align 2
    .weak _pendsv_handler
    .thumb_func
_pendsv_handler:
    bx lr

    .align 2
    .global _systick_handler
    .thumb_func
_systick_handler:
    push {lr}
    bl timer_tick
    pop {pc}

    @ Default handler for unused IRQs
    .align 2
    .thumb_func
_default_handler:
    bx lr

    @ Weak aliases for all IRQ handlers
    .weak _irq0_handler
    .set _irq0_handler, _default_handler
    .weak _irq1_handler
    .set _irq1_handler, _default_handler
    .weak _irq2_handler
    .set _irq2_handler, _default_handler
    .weak _irq3_handler
    .set _irq3_handler, _default_handler
    .weak _irq4_handler
    .set _irq4_handler, _default_handler
    .weak _irq5_handler
    .set _irq5_handler, _default_handler
    .weak _irq6_handler
    .set _irq6_handler, _default_handler
    .weak _irq7_handler
    .set _irq7_handler, _default_handler
    .weak _irq8_handler
    .set _irq8_handler, _default_handler
    .weak _irq9_handler
    .set _irq9_handler, _default_handler
    .weak _irq10_handler
    .set _irq10_handler, _default_handler
    .weak _irq11_handler
    .set _irq11_handler, _default_handler
    .weak _irq12_handler
    .set _irq12_handler, _default_handler
    .weak _irq13_handler
    .set _irq13_handler, _default_handler
    .weak _irq14_handler
    .set _irq14_handler, _default_handler
    .weak _irq15_handler
    .set _irq15_handler, _default_handler
    .weak _irq16_handler
    .set _irq16_handler, _default_handler
    .weak _irq17_handler
    .set _irq17_handler, _default_handler
    .weak _irq18_handler
    .set _irq18_handler, _default_handler
    .weak _irq19_handler
    .set _irq19_handler, _default_handler
    .weak _irq20_handler
    .set _irq20_handler, _default_handler
    .weak _irq21_handler
    .set _irq21_handler, _default_handler
    .weak _irq22_handler
    .set _irq22_handler, _default_handler
    .weak _irq23_handler
    .set _irq23_handler, _default_handler
    .weak _irq24_handler
    .set _irq24_handler, _default_handler
    .weak _irq25_handler
    .set _irq25_handler, _default_handler

@ ============================================================================
@ Symbols for C code
@ ============================================================================

    .global __aeabi_unwind_cpp_pr0
__aeabi_unwind_cpp_pr0:
    bx lr

    .end
