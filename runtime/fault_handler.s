@ Pynux ARM Cortex-M3 Fault Handlers
@
@ Assembly fault handlers that preserve context and call Python handlers.
@ These are naked functions to ensure the exception stack frame is intact.
@
@ ============================================================================
@ EXCEPTION STACK FRAME
@ ============================================================================
@
@ When an exception occurs, the Cortex-M3 hardware automatically pushes
@ 8 registers onto the active stack (MSP or PSP):
@
@   [SP+0]  = R0
@   [SP+4]  = R1
@   [SP+8]  = R2
@   [SP+12] = R3
@   [SP+16] = R12
@   [SP+20] = LR (return address)
@   [SP+24] = PC (faulting instruction address)
@   [SP+28] = xPSR (program status register)
@
@ The stack pointer used depends on the mode before the exception:
@   - Thread mode with MSP: uses MSP
@   - Thread mode with PSP: uses PSP
@   - Handler mode: always uses MSP
@
@ ============================================================================
@ EXC_RETURN VALUES
@ ============================================================================
@
@ When entering an exception, LR is set to EXC_RETURN which indicates
@ how to return from the exception:
@
@   0xFFFFFFF1 - Return to Handler mode, use MSP
@   0xFFFFFFF9 - Return to Thread mode, use MSP
@   0xFFFFFFFD - Return to Thread mode, use PSP
@
@ Bit 2: 0 = MSP was used, 1 = PSP was used
@ Bit 3: 0 = Return to Handler mode, 1 = Return to Thread mode
@
@ ============================================================================

    .syntax unified
    .cpu cortex-m3
    .thumb

    .section .text

@ ============================================================================
@ HardFault Handler
@ ============================================================================
@
@ Called when a HardFault exception occurs. This can be due to:
@   - Escalated configurable fault (MemManage, BusFault, UsageFault)
@   - Vector table read error
@   - Invalid exception return
@
    .global _hardfault
    .type _hardfault, %function
    .thumb_func
_hardfault:
    @ Save LR (EXC_RETURN) for stack detection
    mov r1, lr

    @ Determine which stack was in use (bit 2 of EXC_RETURN)
    @ 0 = MSP, 1 = PSP
    tst lr, #0x04
    beq .hf_use_msp
    mrs r0, psp            @ Get Process Stack Pointer
    b .hf_call_handler
.hf_use_msp:
    mrs r0, msp            @ Get Main Stack Pointer

.hf_call_handler:
    @ r0 = stack pointer with exception frame
    @ r1 = EXC_RETURN value
    @ Align stack to 8 bytes (AAPCS requirement)
    push {r4-r7, lr}

    @ Call Python handler: hardfault_handler(sp, exc_return)
    bl hardfault_handler

    @ If handler returns (shouldn't happen), infinite loop
    pop {r4-r7, pc}

    .size _hardfault, . - _hardfault

@ ============================================================================
@ MemManage Fault Handler
@ ============================================================================
@
@ Called when a Memory Management fault occurs:
@   - MPU violation
@   - Invalid memory access
@   - Instruction fetch from non-executable region
@
    .global _memfault
    .type _memfault, %function
    .thumb_func
_memfault:
    @ Save LR (EXC_RETURN) for stack detection
    mov r1, lr

    @ Determine which stack was in use
    tst lr, #0x04
    beq .mf_use_msp
    mrs r0, psp
    b .mf_call_handler
.mf_use_msp:
    mrs r0, msp

.mf_call_handler:
    push {r4-r7, lr}

    @ Call Python handler: memmanage_handler(sp, exc_return)
    bl memmanage_handler

    pop {r4-r7, pc}

    .size _memfault, . - _memfault

@ ============================================================================
@ BusFault Handler
@ ============================================================================
@
@ Called when a Bus fault occurs:
@   - Invalid memory access (non-existent address)
@   - Access to peripheral without proper clock/enable
@   - Unaligned access on bus
@
    .global _busfault
    .type _busfault, %function
    .thumb_func
_busfault:
    @ Save LR (EXC_RETURN) for stack detection
    mov r1, lr

    @ Determine which stack was in use
    tst lr, #0x04
    beq .bf_use_msp
    mrs r0, psp
    b .bf_call_handler
.bf_use_msp:
    mrs r0, msp

.bf_call_handler:
    push {r4-r7, lr}

    @ Call Python handler: busfault_handler(sp, exc_return)
    bl busfault_handler

    pop {r4-r7, pc}

    .size _busfault, . - _busfault

@ ============================================================================
@ UsageFault Handler
@ ============================================================================
@
@ Called when a Usage fault occurs:
@   - Undefined instruction
@   - Invalid state (EPSR.T bit cleared)
@   - Divide by zero (if enabled)
@   - Unaligned access (if enabled)
@   - Invalid EXC_RETURN value
@
    .global _usagefault
    .type _usagefault, %function
    .thumb_func
_usagefault:
    @ Save LR (EXC_RETURN) for stack detection
    mov r1, lr

    @ Determine which stack was in use
    tst lr, #0x04
    beq .uf_use_msp
    mrs r0, psp
    b .uf_call_handler
.uf_use_msp:
    mrs r0, msp

.uf_call_handler:
    push {r4-r7, lr}

    @ Call Python handler: usagefault_handler(sp, exc_return)
    bl usagefault_handler

    pop {r4-r7, pc}

    .size _usagefault, . - _usagefault

@ ============================================================================
@ Assembly Barrier and Control Instructions
@ ============================================================================

@ void cpsid_i()
@ Disable interrupts (set PRIMASK)
    .global cpsid_i
    .type cpsid_i, %function
    .thumb_func
cpsid_i:
    cpsid i
    bx lr
    .size cpsid_i, . - cpsid_i

@ void cpsie_i()
@ Enable interrupts (clear PRIMASK)
    .global cpsie_i
    .type cpsie_i, %function
    .thumb_func
cpsie_i:
    cpsie i
    bx lr
    .size cpsie_i, . - cpsie_i

@ void wfi()
@ Wait For Interrupt - low power wait
    .global wfi
    .type wfi, %function
    .thumb_func
wfi:
    wfi
    bx lr
    .size wfi, . - wfi

@ void dsb()
@ Data Synchronization Barrier
    .global dsb
    .type dsb, %function
    .thumb_func
dsb:
    dsb sy
    bx lr
    .size dsb, . - dsb

@ void dmb()
@ Data Memory Barrier
    .global dmb
    .type dmb, %function
    .thumb_func
dmb:
    dmb sy
    bx lr
    .size dmb, . - dmb

@ void isb()
@ Instruction Synchronization Barrier
    .global isb
    .type isb, %function
    .thumb_func
isb:
    isb sy
    bx lr
    .size isb, . - isb

@ ============================================================================
@ Stack Pointer Access
@ ============================================================================

@ uint32 get_msp()
@ Get Main Stack Pointer
    .global get_msp
    .type get_msp, %function
    .thumb_func
get_msp:
    mrs r0, msp
    bx lr
    .size get_msp, . - get_msp

@ uint32 get_psp()
@ Get Process Stack Pointer
    .global get_psp
    .type get_psp, %function
    .thumb_func
get_psp:
    mrs r0, psp
    bx lr
    .size get_psp, . - get_psp

@ void set_msp(uint32 sp)
@ Set Main Stack Pointer
    .global set_msp
    .type set_msp, %function
    .thumb_func
set_msp:
    msr msp, r0
    bx lr
    .size set_msp, . - set_msp

@ void set_psp(uint32 sp)
@ Set Process Stack Pointer
    .global set_psp
    .type set_psp, %function
    .thumb_func
set_psp:
    msr psp, r0
    bx lr
    .size set_psp, . - set_psp

@ ============================================================================
@ Control Register Access
@ ============================================================================

@ uint32 get_control()
@ Get CONTROL register
    .global get_control
    .type get_control, %function
    .thumb_func
get_control:
    mrs r0, control
    bx lr
    .size get_control, . - get_control

@ void set_control(uint32 val)
@ Set CONTROL register
    .global set_control
    .type set_control, %function
    .thumb_func
set_control:
    msr control, r0
    isb                    @ Required after CONTROL write
    bx lr
    .size set_control, . - set_control

@ uint32 get_primask()
@ Get PRIMASK register (interrupt enable state)
    .global get_primask
    .type get_primask, %function
    .thumb_func
get_primask:
    mrs r0, primask
    bx lr
    .size get_primask, . - get_primask

@ void set_primask(uint32 val)
@ Set PRIMASK register
    .global set_primask
    .type set_primask, %function
    .thumb_func
set_primask:
    msr primask, r0
    bx lr
    .size set_primask, . - set_primask

@ uint32 get_basepri()
@ Get BASEPRI register
    .global get_basepri
    .type get_basepri, %function
    .thumb_func
get_basepri:
    mrs r0, basepri
    bx lr
    .size get_basepri, . - get_basepri

@ void set_basepri(uint32 val)
@ Set BASEPRI register
    .global set_basepri
    .type set_basepri, %function
    .thumb_func
set_basepri:
    msr basepri, r0
    bx lr
    .size set_basepri, . - set_basepri

@ uint32 get_faultmask()
@ Get FAULTMASK register
    .global get_faultmask
    .type get_faultmask, %function
    .thumb_func
get_faultmask:
    mrs r0, faultmask
    bx lr
    .size get_faultmask, . - get_faultmask

@ void set_faultmask(uint32 val)
@ Set FAULTMASK register
    .global set_faultmask
    .type set_faultmask, %function
    .thumb_func
set_faultmask:
    msr faultmask, r0
    bx lr
    .size set_faultmask, . - set_faultmask

@ ============================================================================
@ Critical Section Helpers
@ ============================================================================

@ int32 critical_enter()
@ Enter critical section (disable interrupts), return previous state
    .global critical_enter
    .type critical_enter, %function
    .thumb_func
critical_enter:
    mrs r0, primask        @ Save current interrupt state
    cpsid i                @ Disable interrupts
    bx lr
    .size critical_enter, . - critical_enter

@ void critical_exit(int32 state)
@ Exit critical section (restore interrupt state)
    .global critical_exit
    .type critical_exit, %function
    .thumb_func
critical_exit:
    msr primask, r0        @ Restore interrupt state
    bx lr
    .size critical_exit, . - critical_exit

@ ============================================================================
@ Fault Test Functions (for debugging)
@ ============================================================================

@ void trigger_hardfault()
@ Intentionally trigger a HardFault (for testing)
    .global trigger_hardfault
    .type trigger_hardfault, %function
    .thumb_func
trigger_hardfault:
    @ Try to read from invalid address
    ldr r0, =0xFFFFFFFC
    ldr r0, [r0]
    bx lr
    .size trigger_hardfault, . - trigger_hardfault

@ void trigger_usagefault_divzero()
@ Intentionally trigger divide by zero (for testing)
@ Note: Requires DIV_0_TRP bit set in CCR
    .global trigger_usagefault_divzero
    .type trigger_usagefault_divzero, %function
    .thumb_func
trigger_usagefault_divzero:
    movs r0, #1
    movs r1, #0
    udiv r0, r0, r1        @ Divide by zero
    bx lr
    .size trigger_usagefault_divzero, . - trigger_usagefault_divzero

@ void trigger_usagefault_undef()
@ Intentionally trigger undefined instruction (for testing)
    .global trigger_usagefault_undef
    .type trigger_usagefault_undef, %function
    .thumb_func
trigger_usagefault_undef:
    .word 0xFFFFFFFF       @ Undefined instruction
    bx lr
    .size trigger_usagefault_undef, . - trigger_usagefault_undef

@ End of fault_handler.s
