@ STM32F405/F407 Startup Code for Pynux
@
@ Clock configuration:
@   - HSE: 8MHz external crystal (common on dev boards)
@   - PLL: 168MHz (HSE * 336 / 8 / 2)
@   - AHB: 168MHz
@   - APB1: 42MHz (max)
@   - APB2: 84MHz (max)
@
@ Flash configuration:
@   - 5 wait states for 168MHz operation
@   - Prefetch and caches enabled

    .syntax unified
    .cpu cortex-m4
    .fpu softvfp
    .thumb

@ ============================================================================
@ RCC Register Offsets
@ ============================================================================

.equ RCC_BASE,          0x40023800
.equ RCC_CR,            0x00
.equ RCC_PLLCFGR,       0x04
.equ RCC_CFGR,          0x08
.equ RCC_CIR,           0x0C
.equ RCC_AHB1ENR,       0x30
.equ RCC_APB1ENR,       0x40
.equ RCC_APB2ENR,       0x44

@ RCC_CR bits
.equ RCC_CR_HSEON,      (1 << 16)
.equ RCC_CR_HSERDY,     (1 << 17)
.equ RCC_CR_PLLON,      (1 << 24)
.equ RCC_CR_PLLRDY,     (1 << 25)

@ RCC_CFGR bits
.equ RCC_CFGR_SW_PLL,   0x02
.equ RCC_CFGR_SWS_PLL,  0x08
.equ RCC_CFGR_PPRE1_DIV4, (5 << 10)   @ APB1 = AHB/4
.equ RCC_CFGR_PPRE2_DIV2, (4 << 13)   @ APB2 = AHB/2

@ Flash register
.equ FLASH_BASE,        0x40023C00
.equ FLASH_ACR,         0x00
.equ FLASH_ACR_LATENCY_5WS, 5
.equ FLASH_ACR_PRFTEN,  (1 << 8)
.equ FLASH_ACR_ICEN,    (1 << 9)
.equ FLASH_ACR_DCEN,    (1 << 10)

@ GPIO
.equ GPIOA_BASE,        0x40020000
.equ GPIO_MODER,        0x00
.equ GPIO_AFRL,         0x20
.equ GPIO_AFRH,         0x24

@ USART1
.equ USART1_BASE,       0x40011000
.equ USART_SR,          0x00
.equ USART_DR,          0x04
.equ USART_BRR,         0x08
.equ USART_CR1,         0x0C

@ ============================================================================
@ Vector Table
@ ============================================================================

    .section .vectors, "ax"
    .align 2

    .global _vectors
_vectors:
    .word __stack_top           @ Initial stack pointer
    .word _reset                @ Reset handler
    .word _nmi_handler          @ NMI
    .word _hardfault_handler    @ HardFault
    .word _memmanage_handler    @ MemManage
    .word _busfault_handler     @ BusFault
    .word _usagefault_handler   @ UsageFault
    .word 0                     @ Reserved
    .word 0                     @ Reserved
    .word 0                     @ Reserved
    .word 0                     @ Reserved
    .word _svc_handler          @ SVCall
    .word _debugmon_handler     @ Debug Monitor
    .word 0                     @ Reserved
    .word _pendsv_handler       @ PendSV
    .word _systick_handler      @ SysTick

    @ STM32F4 IRQ handlers (82 interrupts)
    .word _wwdg_handler         @ 0: Window Watchdog
    .word _pvd_handler          @ 1: PVD through EXTI
    .word _tamp_stamp_handler   @ 2: Tamper and TimeStamp
    .word _rtc_wkup_handler     @ 3: RTC Wakeup
    .word _flash_handler        @ 4: Flash
    .word _rcc_handler          @ 5: RCC
    .word _exti0_handler        @ 6: EXTI Line 0
    .word _exti1_handler        @ 7: EXTI Line 1
    .word _exti2_handler        @ 8: EXTI Line 2
    .word _exti3_handler        @ 9: EXTI Line 3
    .word _exti4_handler        @ 10: EXTI Line 4
    .word _dma1_stream0_handler @ 11: DMA1 Stream 0
    .word _dma1_stream1_handler @ 12: DMA1 Stream 1
    .word _dma1_stream2_handler @ 13: DMA1 Stream 2
    .word _dma1_stream3_handler @ 14: DMA1 Stream 3
    .word _dma1_stream4_handler @ 15: DMA1 Stream 4
    .word _dma1_stream5_handler @ 16: DMA1 Stream 5
    .word _dma1_stream6_handler @ 17: DMA1 Stream 6
    .word _adc_handler          @ 18: ADC1, ADC2, ADC3
    .word _can1_tx_handler      @ 19: CAN1 TX
    .word _can1_rx0_handler     @ 20: CAN1 RX0
    .word _can1_rx1_handler     @ 21: CAN1 RX1
    .word _can1_sce_handler     @ 22: CAN1 SCE
    .word _exti9_5_handler      @ 23: EXTI Lines 5-9
    .word _tim1_brk_handler     @ 24: TIM1 Break
    .word _tim1_up_handler      @ 25: TIM1 Update
    .word _tim1_trg_handler     @ 26: TIM1 Trigger
    .word _tim1_cc_handler      @ 27: TIM1 Capture Compare
    .word _tim2_handler         @ 28: TIM2
    .word _tim3_handler         @ 29: TIM3
    .word _tim4_handler         @ 30: TIM4
    .word _i2c1_ev_handler      @ 31: I2C1 Event
    .word _i2c1_er_handler      @ 32: I2C1 Error
    .word _i2c2_ev_handler      @ 33: I2C2 Event
    .word _i2c2_er_handler      @ 34: I2C2 Error
    .word _spi1_handler         @ 35: SPI1
    .word _spi2_handler         @ 36: SPI2
    .word _usart1_handler       @ 37: USART1
    .word _usart2_handler       @ 38: USART2
    .word _usart3_handler       @ 39: USART3
    .word _exti15_10_handler    @ 40: EXTI Lines 10-15
    .word _rtc_alarm_handler    @ 41: RTC Alarm
    .word _otg_fs_wkup_handler  @ 42: USB OTG FS Wakeup
    .word _tim8_brk_handler     @ 43: TIM8 Break
    .word _tim8_up_handler      @ 44: TIM8 Update
    .word _tim8_trg_handler     @ 45: TIM8 Trigger
    .word _tim8_cc_handler      @ 46: TIM8 Capture Compare
    .word _dma1_stream7_handler @ 47: DMA1 Stream 7
    .word _fsmc_handler         @ 48: FSMC
    .word _sdio_handler         @ 49: SDIO
    .word _tim5_handler         @ 50: TIM5
    .word _spi3_handler         @ 51: SPI3
    .word _uart4_handler        @ 52: UART4
    .word _uart5_handler        @ 53: UART5
    .word _tim6_dac_handler     @ 54: TIM6 and DAC
    .word _tim7_handler         @ 55: TIM7
    .word _dma2_stream0_handler @ 56: DMA2 Stream 0
    .word _dma2_stream1_handler @ 57: DMA2 Stream 1
    .word _dma2_stream2_handler @ 58: DMA2 Stream 2
    .word _dma2_stream3_handler @ 59: DMA2 Stream 3
    .word _dma2_stream4_handler @ 60: DMA2 Stream 4
    .word _eth_handler          @ 61: Ethernet
    .word _eth_wkup_handler     @ 62: Ethernet Wakeup
    .word _can2_tx_handler      @ 63: CAN2 TX
    .word _can2_rx0_handler     @ 64: CAN2 RX0
    .word _can2_rx1_handler     @ 65: CAN2 RX1
    .word _can2_sce_handler     @ 66: CAN2 SCE
    .word _otg_fs_handler       @ 67: USB OTG FS
    .word _dma2_stream5_handler @ 68: DMA2 Stream 5
    .word _dma2_stream6_handler @ 69: DMA2 Stream 6
    .word _dma2_stream7_handler @ 70: DMA2 Stream 7
    .word _usart6_handler       @ 71: USART6
    .word _i2c3_ev_handler      @ 72: I2C3 Event
    .word _i2c3_er_handler      @ 73: I2C3 Error
    .word _otg_hs_ep1_out_handler @ 74: USB OTG HS EP1 Out
    .word _otg_hs_ep1_in_handler  @ 75: USB OTG HS EP1 In
    .word _otg_hs_wkup_handler  @ 76: USB OTG HS Wakeup
    .word _otg_hs_handler       @ 77: USB OTG HS
    .word _dcmi_handler         @ 78: DCMI
    .word _cryp_handler         @ 79: CRYP
    .word _hash_rng_handler     @ 80: HASH and RNG
    .word _fpu_handler          @ 81: FPU

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

    @ Set stack pointer
    ldr r0, =__stack_top
    mov sp, r0

    @ Enable FPU (Cortex-M4 with FPU)
    @ Set CP10 and CP11 to full access
    ldr r0, =0xE000ED88         @ CPACR
    ldr r1, [r0]
    orr r1, r1, #(0xF << 20)    @ CP10, CP11 full access
    str r1, [r0]
    dsb
    isb

    @ Configure flash wait states BEFORE increasing clock
    bl stm32f4_flash_init

    @ Configure clocks to 168MHz
    bl stm32f4_clock_init

    @ Zero BSS section
    ldr r0, =__bss_start
    ldr r1, =__bss_end
    movs r2, #0
bss_loop:
    cmp r0, r1
    bge bss_done
    str r2, [r0], #4
    b bss_loop
bss_done:

    @ Copy .data from flash to RAM
    ldr r0, =__data_start
    ldr r1, =__data_end
    ldr r2, =__data_load
data_loop:
    cmp r0, r1
    bge data_done
    ldr r3, [r2], #4
    str r3, [r0], #4
    b data_loop
data_done:

    @ Initialize UART for debug output
    bl stm32f4_uart_init

    @ Configure SysTick for 1ms ticks
    bl stm32f4_systick_init

    @ Enable fault handlers
    ldr r0, =0xE000ED24         @ SCB->SHCSR
    ldr r1, [r0]
    orr r1, #(1 << 16)          @ MEMFAULTENA
    orr r1, #(1 << 17)          @ BUSFAULTENA
    orr r1, #(1 << 18)          @ USGFAULTENA
    str r1, [r0]

    @ Enable interrupts
    cpsie i

    @ Call kernel main
    bl kernel_main

    @ Halt if kernel returns
halt:
    wfi
    b halt

@ ============================================================================
@ Flash Configuration
@ ============================================================================

    .align 2
    .thumb_func
stm32f4_flash_init:
    ldr r0, =FLASH_BASE

    @ Set 5 wait states, enable prefetch and caches
    ldr r1, =(FLASH_ACR_LATENCY_5WS | FLASH_ACR_PRFTEN | FLASH_ACR_ICEN | FLASH_ACR_DCEN)
    str r1, [r0, #FLASH_ACR]

    bx lr

@ ============================================================================
@ Clock Configuration - 168MHz from 8MHz HSE
@ ============================================================================

    .align 2
    .thumb_func
stm32f4_clock_init:
    push {lr}

    ldr r4, =RCC_BASE

    @ Enable HSE (external 8MHz crystal)
    ldr r0, [r4, #RCC_CR]
    orr r0, #RCC_CR_HSEON
    str r0, [r4, #RCC_CR]

    @ Wait for HSE ready
hse_wait:
    ldr r0, [r4, #RCC_CR]
    tst r0, #RCC_CR_HSERDY
    beq hse_wait

    @ Configure PLL
    @ PLL_M = 8 (HSE/8 = 1MHz to PLL input)
    @ PLL_N = 336 (1MHz * 336 = 336MHz VCO)
    @ PLL_P = 2 (336MHz / 2 = 168MHz system clock)
    @ PLL_Q = 7 (336MHz / 7 = 48MHz for USB)
    @ Source = HSE

    ldr r0, =(8 << 0)           @ PLLM = 8
    orr r0, #(336 << 6)         @ PLLN = 336
    orr r0, #(0 << 16)          @ PLLP = 2 (00 = /2)
    orr r0, #(1 << 22)          @ PLLSRC = HSE
    orr r0, #(7 << 24)          @ PLLQ = 7
    str r0, [r4, #RCC_PLLCFGR]

    @ Enable PLL
    ldr r0, [r4, #RCC_CR]
    orr r0, #RCC_CR_PLLON
    str r0, [r4, #RCC_CR]

    @ Wait for PLL ready
pll_wait:
    ldr r0, [r4, #RCC_CR]
    tst r0, #RCC_CR_PLLRDY
    beq pll_wait

    @ Configure bus dividers and switch to PLL
    @ AHB = SYSCLK (168MHz)
    @ APB1 = AHB/4 (42MHz, max for APB1)
    @ APB2 = AHB/2 (84MHz, max for APB2)
    ldr r0, =(RCC_CFGR_SW_PLL | RCC_CFGR_PPRE1_DIV4 | RCC_CFGR_PPRE2_DIV2)
    str r0, [r4, #RCC_CFGR]

    @ Wait for PLL as system clock
pll_switch_wait:
    ldr r0, [r4, #RCC_CFGR]
    and r0, #0x0C               @ SWS bits
    cmp r0, #RCC_CFGR_SWS_PLL
    bne pll_switch_wait

    pop {pc}

@ ============================================================================
@ SysTick Configuration - 1ms ticks at 168MHz
@ ============================================================================

    .align 2
    .thumb_func
stm32f4_systick_init:
    @ SysTick reload = 168000 - 1 for 1ms at 168MHz
    ldr r0, =0xE000E010         @ SysTick base
    ldr r1, =(168000 - 1)
    str r1, [r0, #4]            @ LOAD

    movs r1, #0
    str r1, [r0, #8]            @ VAL (clear current)

    movs r1, #7                 @ CLKSOURCE=1, TICKINT=1, ENABLE=1
    str r1, [r0, #0]            @ CTRL

    bx lr

@ ============================================================================
@ UART1 Initialization (PA9=TX, PA10=RX at 115200 baud)
@ ============================================================================

    .align 2
    .thumb_func
    .global stm32f4_uart_init
stm32f4_uart_init:
    push {lr}

    @ Enable GPIOA and USART1 clocks
    ldr r4, =RCC_BASE
    ldr r0, [r4, #RCC_AHB1ENR]
    orr r0, #(1 << 0)           @ GPIOAEN
    str r0, [r4, #RCC_AHB1ENR]

    ldr r0, [r4, #RCC_APB2ENR]
    orr r0, #(1 << 4)           @ USART1EN
    str r0, [r4, #RCC_APB2ENR]

    @ Configure PA9, PA10 as alternate function (AF7 = USART1)
    ldr r4, =GPIOA_BASE

    @ MODER: PA9, PA10 = alternate function (10)
    ldr r0, [r4, #GPIO_MODER]
    bic r0, #(3 << 18)          @ Clear PA9
    bic r0, #(3 << 20)          @ Clear PA10
    orr r0, #(2 << 18)          @ PA9 = AF
    orr r0, #(2 << 20)          @ PA10 = AF
    str r0, [r4, #GPIO_MODER]

    @ AFRH: PA9, PA10 = AF7
    ldr r0, [r4, #GPIO_AFRH]
    bic r0, #(0xF << 4)         @ Clear PA9 AF
    bic r0, #(0xF << 8)         @ Clear PA10 AF
    orr r0, #(7 << 4)           @ PA9 = AF7
    orr r0, #(7 << 8)           @ PA10 = AF7
    str r0, [r4, #GPIO_AFRH]

    @ Configure USART1
    ldr r4, =USART1_BASE

    @ Disable USART during configuration
    movs r0, #0
    str r0, [r4, #USART_CR1]

    @ Set baud rate for 115200 at 84MHz APB2 clock
    @ BRR = 84000000 / 115200 = 729.16
    @ Mantissa = 729 = 0x2D9, Fraction = 0.16 * 16 = 2.6 ≈ 3
    @ BRR = (729 << 4) | 3 = 0x2D93
    ldr r0, =0x2D9
    lsl r0, #4
    orr r0, #3
    str r0, [r4, #USART_BRR]

    @ Enable USART, TX, RX
    ldr r0, =(1 << 13) | (1 << 3) | (1 << 2)  @ UE, TE, RE
    str r0, [r4, #USART_CR1]

    pop {pc}

@ ============================================================================
@ UART I/O Functions
@ ============================================================================

    .align 2
    .global uart_putc
    .thumb_func
uart_putc:
    @ r0 = character to send
    ldr r1, =USART1_BASE
uart_putc_wait:
    ldr r2, [r1, #USART_SR]
    tst r2, #(1 << 7)           @ TXE bit
    beq uart_putc_wait
    str r0, [r1, #USART_DR]
    bx lr

    .align 2
    .global uart_getc
    .thumb_func
uart_getc:
    ldr r1, =USART1_BASE
uart_getc_wait:
    ldr r2, [r1, #USART_SR]
    tst r2, #(1 << 5)           @ RXNE bit
    beq uart_getc_wait
    ldr r0, [r1, #USART_DR]
    and r0, #0xFF
    bx lr

    .align 2
    .global uart_tx_ready
    .thumb_func
uart_tx_ready:
    ldr r1, =USART1_BASE
    ldr r0, [r1, #USART_SR]
    ubfx r0, r0, #7, #1         @ TXE bit
    bx lr

    .align 2
    .global uart_rx_ready
    .thumb_func
uart_rx_ready:
    ldr r1, =USART1_BASE
    ldr r0, [r1, #USART_SR]
    ubfx r0, r0, #5, #1         @ RXNE bit
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
    b .

    .align 2
    .global _memmanage_handler
    .thumb_func
_memmanage_handler:
    b .

    .align 2
    .global _busfault_handler
    .thumb_func
_busfault_handler:
    b .

    .align 2
    .global _usagefault_handler
    .thumb_func
_usagefault_handler:
    b .

    .align 2
    .weak _svc_handler
    .thumb_func
_svc_handler:
    bx lr

    .align 2
    .weak _debugmon_handler
    .thumb_func
_debugmon_handler:
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

@ Default handler for all other IRQs
    .align 2
    .thumb_func
_default_handler:
    bx lr

@ Weak aliases for all IRQ handlers
.macro def_irq_handler handler_name
    .weak \handler_name
    .set \handler_name, _default_handler
.endm

    def_irq_handler _wwdg_handler
    def_irq_handler _pvd_handler
    def_irq_handler _tamp_stamp_handler
    def_irq_handler _rtc_wkup_handler
    def_irq_handler _flash_handler
    def_irq_handler _rcc_handler
    def_irq_handler _exti0_handler
    def_irq_handler _exti1_handler
    def_irq_handler _exti2_handler
    def_irq_handler _exti3_handler
    def_irq_handler _exti4_handler
    def_irq_handler _dma1_stream0_handler
    def_irq_handler _dma1_stream1_handler
    def_irq_handler _dma1_stream2_handler
    def_irq_handler _dma1_stream3_handler
    def_irq_handler _dma1_stream4_handler
    def_irq_handler _dma1_stream5_handler
    def_irq_handler _dma1_stream6_handler
    def_irq_handler _adc_handler
    def_irq_handler _can1_tx_handler
    def_irq_handler _can1_rx0_handler
    def_irq_handler _can1_rx1_handler
    def_irq_handler _can1_sce_handler
    def_irq_handler _exti9_5_handler
    def_irq_handler _tim1_brk_handler
    def_irq_handler _tim1_up_handler
    def_irq_handler _tim1_trg_handler
    def_irq_handler _tim1_cc_handler
    def_irq_handler _tim2_handler
    def_irq_handler _tim3_handler
    def_irq_handler _tim4_handler
    def_irq_handler _i2c1_ev_handler
    def_irq_handler _i2c1_er_handler
    def_irq_handler _i2c2_ev_handler
    def_irq_handler _i2c2_er_handler
    def_irq_handler _spi1_handler
    def_irq_handler _spi2_handler
    def_irq_handler _usart1_handler
    def_irq_handler _usart2_handler
    def_irq_handler _usart3_handler
    def_irq_handler _exti15_10_handler
    def_irq_handler _rtc_alarm_handler
    def_irq_handler _otg_fs_wkup_handler
    def_irq_handler _tim8_brk_handler
    def_irq_handler _tim8_up_handler
    def_irq_handler _tim8_trg_handler
    def_irq_handler _tim8_cc_handler
    def_irq_handler _dma1_stream7_handler
    def_irq_handler _fsmc_handler
    def_irq_handler _sdio_handler
    def_irq_handler _tim5_handler
    def_irq_handler _spi3_handler
    def_irq_handler _uart4_handler
    def_irq_handler _uart5_handler
    def_irq_handler _tim6_dac_handler
    def_irq_handler _tim7_handler
    def_irq_handler _dma2_stream0_handler
    def_irq_handler _dma2_stream1_handler
    def_irq_handler _dma2_stream2_handler
    def_irq_handler _dma2_stream3_handler
    def_irq_handler _dma2_stream4_handler
    def_irq_handler _eth_handler
    def_irq_handler _eth_wkup_handler
    def_irq_handler _can2_tx_handler
    def_irq_handler _can2_rx0_handler
    def_irq_handler _can2_rx1_handler
    def_irq_handler _can2_sce_handler
    def_irq_handler _otg_fs_handler
    def_irq_handler _dma2_stream5_handler
    def_irq_handler _dma2_stream6_handler
    def_irq_handler _dma2_stream7_handler
    def_irq_handler _usart6_handler
    def_irq_handler _i2c3_ev_handler
    def_irq_handler _i2c3_er_handler
    def_irq_handler _otg_hs_ep1_out_handler
    def_irq_handler _otg_hs_ep1_in_handler
    def_irq_handler _otg_hs_wkup_handler
    def_irq_handler _otg_hs_handler
    def_irq_handler _dcmi_handler
    def_irq_handler _cryp_handler
    def_irq_handler _hash_rng_handler
    def_irq_handler _fpu_handler

    .end
