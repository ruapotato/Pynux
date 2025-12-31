# Pynux OS GDB Register Commands
# ARM Cortex-M register inspection and decoding

# -----------------------------------------------------------------------------
# ARM Register Display
# -----------------------------------------------------------------------------

define arm-regs
    echo === ARM Core Registers ===\n
    printf "R0:  0x%08x    R1:  0x%08x    R2:  0x%08x    R3:  0x%08x\n", $r0, $r1, $r2, $r3
    printf "R4:  0x%08x    R5:  0x%08x    R6:  0x%08x    R7:  0x%08x\n", $r4, $r5, $r6, $r7
    printf "R8:  0x%08x    R9:  0x%08x    R10: 0x%08x    R11: 0x%08x\n", $r8, $r9, $r10, $r11
    printf "R12: 0x%08x    SP:  0x%08x    LR:  0x%08x    PC:  0x%08x\n", $r12, $sp, $lr, $pc
    echo \n
    arm-cpsr
end
document arm-regs
Print all ARM core registers in a formatted display.
Shows R0-R12, SP, LR, PC, and decodes CPSR/xPSR.
end

# -----------------------------------------------------------------------------
# CPSR/xPSR Decoding
# -----------------------------------------------------------------------------

define arm-cpsr
    echo === Program Status Register ===\n
    set $psr = $cpsr
    printf "xPSR: 0x%08x\n", $psr
    echo \n
    echo Flags:\n

    # Negative flag
    if ($psr & 0x80000000)
        printf "  N (Negative): 1 - Result was negative\n"
    else
        printf "  N (Negative): 0 - Result was positive or zero\n"
    end

    # Zero flag
    if ($psr & 0x40000000)
        printf "  Z (Zero):     1 - Result was zero\n"
    else
        printf "  Z (Zero):     0 - Result was non-zero\n"
    end

    # Carry flag
    if ($psr & 0x20000000)
        printf "  C (Carry):    1 - Carry/borrow occurred\n"
    else
        printf "  C (Carry):    0 - No carry/borrow\n"
    end

    # Overflow flag
    if ($psr & 0x10000000)
        printf "  V (Overflow): 1 - Overflow occurred\n"
    else
        printf "  V (Overflow): 0 - No overflow\n"
    end

    # Thumb state
    if ($psr & 0x01000000)
        printf "  T (Thumb):    1 - Thumb state\n"
    else
        printf "  T (Thumb):    0 - ARM state\n"
    end

    echo \n

    # Exception number (Cortex-M)
    set $exception = $psr & 0x1FF
    printf "Exception number: %d ", $exception
    if $exception == 0
        printf "(Thread mode)\n"
    else
        if $exception == 1
            printf "(Reset)\n"
        else
            if $exception == 2
                printf "(NMI)\n"
            else
                if $exception == 3
                    printf "(HardFault)\n"
                else
                    if $exception == 4
                        printf "(MemManage)\n"
                    else
                        if $exception == 5
                            printf "(BusFault)\n"
                        else
                            if $exception == 6
                                printf "(UsageFault)\n"
                            else
                                if $exception == 11
                                    printf "(SVCall)\n"
                                else
                                    if $exception == 12
                                        printf "(Debug Monitor)\n"
                                    else
                                        if $exception == 14
                                            printf "(PendSV)\n"
                                        else
                                            if $exception == 15
                                                printf "(SysTick)\n"
                                            else
                                                if $exception >= 16
                                                    printf "(IRQ %d)\n", $exception - 16
                                                else
                                                    printf "(Reserved)\n"
                                                end
                                            end
                                        end
                                    end
                                end
                            end
                        end
                    end
                end
            end
        end
    end
end
document arm-cpsr
Decode and display the CPSR/xPSR flags.
Shows condition flags (N, Z, C, V), execution state, and exception number.
end

# -----------------------------------------------------------------------------
# Stack Display
# -----------------------------------------------------------------------------

define arm-stack
    if $argc == 0
        set $count = 16
    else
        set $count = $arg0
    end

    echo === Stack Contents ===\n
    printf "SP: 0x%08x\n\n", $sp

    set $i = 0
    while $i < $count
        set $addr = $sp + ($i * 4)
        set $val = *(unsigned int*)$addr
        printf "SP+%02d [0x%08x]: 0x%08x", $i * 4, $addr, $val

        # Try to identify special values
        if $val == 0xDEADBEEF
            printf " (DEADBEEF marker)"
        end
        if $val == 0xCAFEBABE
            printf " (CAFEBABE marker)"
        end
        if ($val >= 0x08000000) && ($val < 0x08100000)
            printf " (Flash address)"
        end
        if ($val >= 0x20000000) && ($val < 0x20020000)
            printf " (SRAM address)"
        end
        if ($val >= 0x40000000) && ($val < 0x50000000)
            printf " (Peripheral address)"
        end
        if ($val & 0xFFFFFFF0) == 0xFFFFFFF0
            printf " (EXC_RETURN: "
            if $val == 0xFFFFFFF1
                printf "Handler, MSP)"
            end
            if $val == 0xFFFFFFF9
                printf "Thread, MSP)"
            end
            if $val == 0xFFFFFFFD
                printf "Thread, PSP)"
            end
        end

        printf "\n"
        set $i = $i + 1
    end
end
document arm-stack
Show stack contents with annotations.
Usage: arm-stack [count]
Default: 16 words
Annotates special values like EXC_RETURN, memory regions, etc.
end

define arm-stack-frame
    echo === Exception Stack Frame ===\n
    printf "SP: 0x%08x\n\n", $sp
    printf "R0:     0x%08x (SP+0x00)\n", *(unsigned int*)($sp + 0x00)
    printf "R1:     0x%08x (SP+0x04)\n", *(unsigned int*)($sp + 0x04)
    printf "R2:     0x%08x (SP+0x08)\n", *(unsigned int*)($sp + 0x08)
    printf "R3:     0x%08x (SP+0x0C)\n", *(unsigned int*)($sp + 0x0C)
    printf "R12:    0x%08x (SP+0x10)\n", *(unsigned int*)($sp + 0x10)
    printf "LR:     0x%08x (SP+0x14)\n", *(unsigned int*)($sp + 0x14)
    printf "PC:     0x%08x (SP+0x18)\n", *(unsigned int*)($sp + 0x18)
    printf "xPSR:   0x%08x (SP+0x1C)\n", *(unsigned int*)($sp + 0x1C)
end
document arm-stack-frame
Display the Cortex-M exception stack frame.
Shows the 8 registers automatically pushed on exception entry.
end

# -----------------------------------------------------------------------------
# Fault Register Decoding
# -----------------------------------------------------------------------------

# Cortex-M fault register addresses
set $SCB_BASE = 0xE000ED00
set $CFSR = 0xE000ED28
set $HFSR = 0xE000ED2C
set $DFSR = 0xE000ED30
set $MMFAR = 0xE000ED34
set $BFAR = 0xE000ED38
set $AFSR = 0xE000ED3C

define arm-fault
    echo === Fault Status Registers ===\n\n

    # Configurable Fault Status Register
    set $cfsr_val = *(unsigned int*)$CFSR
    printf "CFSR:  0x%08x\n", $cfsr_val

    # Memory Management Fault Status (bits 7:0)
    set $mmfsr = $cfsr_val & 0xFF
    if $mmfsr != 0
        printf "  MemManage Fault (MMFSR = 0x%02x):\n", $mmfsr
        if $mmfsr & 0x01
            printf "    IACCVIOL: Instruction access violation\n"
        end
        if $mmfsr & 0x02
            printf "    DACCVIOL: Data access violation\n"
        end
        if $mmfsr & 0x08
            printf "    MUNSTKERR: Unstacking error\n"
        end
        if $mmfsr & 0x10
            printf "    MSTKERR: Stacking error\n"
        end
        if $mmfsr & 0x20
            printf "    MLSPERR: FP lazy state preservation error\n"
        end
        if $mmfsr & 0x80
            printf "    MMARVALID: MMFAR valid\n"
            printf "    MMFAR: 0x%08x\n", *(unsigned int*)$MMFAR
        end
    else
        printf "  MemManage: No fault\n"
    end

    # Bus Fault Status (bits 15:8)
    set $bfsr = ($cfsr_val >> 8) & 0xFF
    if $bfsr != 0
        printf "  Bus Fault (BFSR = 0x%02x):\n", $bfsr
        if $bfsr & 0x01
            printf "    IBUSERR: Instruction bus error\n"
        end
        if $bfsr & 0x02
            printf "    PRECISERR: Precise data bus error\n"
        end
        if $bfsr & 0x04
            printf "    IMPRECISERR: Imprecise data bus error\n"
        end
        if $bfsr & 0x08
            printf "    UNSTKERR: Unstacking error\n"
        end
        if $bfsr & 0x10
            printf "    STKERR: Stacking error\n"
        end
        if $bfsr & 0x20
            printf "    LSPERR: FP lazy state preservation error\n"
        end
        if $bfsr & 0x80
            printf "    BFARVALID: BFAR valid\n"
            printf "    BFAR: 0x%08x\n", *(unsigned int*)$BFAR
        end
    else
        printf "  Bus Fault: No fault\n"
    end

    # Usage Fault Status (bits 31:16)
    set $ufsr = ($cfsr_val >> 16) & 0xFFFF
    if $ufsr != 0
        printf "  Usage Fault (UFSR = 0x%04x):\n", $ufsr
        if $ufsr & 0x0001
            printf "    UNDEFINSTR: Undefined instruction\n"
        end
        if $ufsr & 0x0002
            printf "    INVSTATE: Invalid state (Thumb bit)\n"
        end
        if $ufsr & 0x0004
            printf "    INVPC: Invalid PC load\n"
        end
        if $ufsr & 0x0008
            printf "    NOCP: No coprocessor\n"
        end
        if $ufsr & 0x0010
            printf "    STKOF: Stack overflow\n"
        end
        if $ufsr & 0x0100
            printf "    UNALIGNED: Unaligned access\n"
        end
        if $ufsr & 0x0200
            printf "    DIVBYZERO: Divide by zero\n"
        end
    else
        printf "  Usage Fault: No fault\n"
    end

    echo \n

    # Hard Fault Status Register
    set $hfsr_val = *(unsigned int*)$HFSR
    printf "HFSR:  0x%08x\n", $hfsr_val
    if $hfsr_val != 0
        if $hfsr_val & 0x00000002
            printf "  VECTTBL: Vector table read fault\n"
        end
        if $hfsr_val & 0x40000000
            printf "  FORCED: Forced HardFault (escalated from configurable fault)\n"
        end
        if $hfsr_val & 0x80000000
            printf "  DEBUGEVT: Debug event\n"
        end
    else
        printf "  No HardFault\n"
    end

    echo \n

    # Debug Fault Status Register
    set $dfsr_val = *(unsigned int*)$DFSR
    printf "DFSR:  0x%08x\n", $dfsr_val
    if $dfsr_val != 0
        if $dfsr_val & 0x01
            printf "  HALTED: Halt request\n"
        end
        if $dfsr_val & 0x02
            printf "  BKPT: Breakpoint\n"
        end
        if $dfsr_val & 0x04
            printf "  DWTTRAP: DWT match\n"
        end
        if $dfsr_val & 0x08
            printf "  VCATCH: Vector catch\n"
        end
        if $dfsr_val & 0x10
            printf "  EXTERNAL: External debug request\n"
        end
    end
end
document arm-fault
Decode and display ARM Cortex-M fault status registers.
Shows CFSR (MemManage, Bus, Usage faults), HFSR, DFSR.
Displays fault addresses from MMFAR and BFAR when valid.
end

define arm-fault-clear
    echo Clearing fault status registers...\n
    set *(unsigned int*)$CFSR = 0xFFFFFFFF
    set *(unsigned int*)$HFSR = 0xFFFFFFFF
    set *(unsigned int*)$DFSR = 0x1F
    echo Done.\n
end
document arm-fault-clear
Clear all fault status registers.
end

# -----------------------------------------------------------------------------
# NVIC Display
# -----------------------------------------------------------------------------

set $NVIC_BASE = 0xE000E100
set $NVIC_ISER = 0xE000E100
set $NVIC_ICER = 0xE000E180
set $NVIC_ISPR = 0xE000E200
set $NVIC_ICPR = 0xE000E280
set $NVIC_IABR = 0xE000E300
set $NVIC_IPR = 0xE000E400

define arm-nvic
    echo === NVIC Status ===\n\n

    printf "Enabled Interrupts (ISER):\n"
    set $i = 0
    while $i < 8
        set $iser = *(unsigned int*)($NVIC_ISER + $i * 4)
        if $iser != 0
            printf "  ISER[%d]: 0x%08x (IRQs %d-%d)\n", $i, $iser, $i * 32, ($i + 1) * 32 - 1
            set $j = 0
            while $j < 32
                if $iser & (1 << $j)
                    printf "    IRQ %d enabled\n", $i * 32 + $j
                end
                set $j = $j + 1
            end
        end
        set $i = $i + 1
    end

    printf "\nPending Interrupts (ISPR):\n"
    set $i = 0
    set $any_pending = 0
    while $i < 8
        set $ispr = *(unsigned int*)($NVIC_ISPR + $i * 4)
        if $ispr != 0
            set $any_pending = 1
            printf "  ISPR[%d]: 0x%08x\n", $i, $ispr
            set $j = 0
            while $j < 32
                if $ispr & (1 << $j)
                    printf "    IRQ %d pending\n", $i * 32 + $j
                end
                set $j = $j + 1
            end
        end
        set $i = $i + 1
    end
    if $any_pending == 0
        printf "  No interrupts pending\n"
    end

    printf "\nActive Interrupts (IABR):\n"
    set $i = 0
    set $any_active = 0
    while $i < 8
        set $iabr = *(unsigned int*)($NVIC_IABR + $i * 4)
        if $iabr != 0
            set $any_active = 1
            printf "  IABR[%d]: 0x%08x\n", $i, $iabr
            set $j = 0
            while $j < 32
                if $iabr & (1 << $j)
                    printf "    IRQ %d active\n", $i * 32 + $j
                end
                set $j = $j + 1
            end
        end
        set $i = $i + 1
    end
    if $any_active == 0
        printf "  No interrupts active\n"
    end
end
document arm-nvic
Display NVIC interrupt controller status.
Shows enabled, pending, and active interrupts.
end

define arm-nvic-priority
    if $argc == 0
        echo Usage: arm-nvic-priority <irq_number>\n
        echo Shows priority of the specified IRQ.\n
    else
        set $irq = $arg0
        set $prio_reg = $NVIC_IPR + ($irq / 4) * 4
        set $prio_shift = ($irq % 4) * 8
        set $prio = (*(unsigned int*)$prio_reg >> $prio_shift) & 0xFF
        printf "IRQ %d priority: %d (0x%02x)\n", $irq, $prio >> 4, $prio
    end
end
document arm-nvic-priority
Show priority of a specific interrupt.
Usage: arm-nvic-priority <irq_number>
end

# -----------------------------------------------------------------------------
# SysTick Display
# -----------------------------------------------------------------------------

set $SYST_CSR = 0xE000E010
set $SYST_RVR = 0xE000E014
set $SYST_CVR = 0xE000E018
set $SYST_CALIB = 0xE000E01C

define arm-systick
    echo === SysTick Status ===\n\n

    set $csr = *(unsigned int*)$SYST_CSR
    set $rvr = *(unsigned int*)$SYST_RVR
    set $cvr = *(unsigned int*)$SYST_CVR
    set $calib = *(unsigned int*)$SYST_CALIB

    printf "CSR (Control): 0x%08x\n", $csr
    printf "  ENABLE:    %d\n", $csr & 1
    printf "  TICKINT:   %d (interrupt %s)\n", ($csr >> 1) & 1, ($csr & 2) ? "enabled" : "disabled"
    printf "  CLKSOURCE: %d (%s)\n", ($csr >> 2) & 1, (($csr >> 2) & 1) ? "processor clock" : "external clock"
    printf "  COUNTFLAG: %d\n", ($csr >> 16) & 1

    printf "\nRVR (Reload):  0x%08x (%u)\n", $rvr & 0x00FFFFFF, $rvr & 0x00FFFFFF
    printf "CVR (Current): 0x%08x (%u)\n", $cvr & 0x00FFFFFF, $cvr & 0x00FFFFFF

    if $rvr != 0
        set $percent = (($rvr - $cvr) * 100) / $rvr
        printf "Progress:      %d%%\n", $percent
    end

    printf "\nCALIB:         0x%08x\n", $calib
    printf "  TENMS:     %u\n", $calib & 0x00FFFFFF
    printf "  SKEW:      %d\n", ($calib >> 30) & 1
    printf "  NOREF:     %d\n", ($calib >> 31) & 1
end
document arm-systick
Display SysTick timer status.
Shows control register, reload value, current value, and calibration.
end
