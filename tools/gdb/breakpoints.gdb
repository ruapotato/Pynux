# Pynux OS GDB Breakpoint Helpers
# Predefined breakpoints for common debugging scenarios

# -----------------------------------------------------------------------------
# Fault Breakpoints
# -----------------------------------------------------------------------------

define break-fault
    echo Setting breakpoints on all fault handlers...\n

    # Cortex-M fault handlers (common names)
    break HardFault_Handler
    break MemManage_Handler
    break BusFault_Handler
    break UsageFault_Handler
    break NMI_Handler

    # Alternative naming conventions
    catch signal SIGSEGV
    catch signal SIGBUS
    catch signal SIGFPE

    echo Fault breakpoints set.\n
    info breakpoints
end
document break-fault
Set breakpoints on all fault handlers.
Breaks on HardFault, MemManage, BusFault, UsageFault, and NMI.
end

define break-hardfault
    echo Setting breakpoint on HardFault...\n
    break HardFault_Handler
    echo HardFault breakpoint set.\n
end
document break-hardfault
Set breakpoint on HardFault handler.
end

define break-memmanage
    echo Setting breakpoint on MemManage fault...\n
    break MemManage_Handler
    echo MemManage breakpoint set.\n
end
document break-memmanage
Set breakpoint on MemManage fault handler.
end

define break-busfault
    echo Setting breakpoint on BusFault...\n
    break BusFault_Handler
    echo BusFault breakpoint set.\n
end
document break-busfault
Set breakpoint on BusFault handler.
end

define break-usagefault
    echo Setting breakpoint on UsageFault...\n
    break UsageFault_Handler
    echo UsageFault breakpoint set.\n
end
document break-usagefault
Set breakpoint on UsageFault handler.
end

# -----------------------------------------------------------------------------
# Memory Allocation Breakpoints
# -----------------------------------------------------------------------------

define break-malloc-fail
    echo Setting breakpoint on allocation failures...\n

    # Common allocation failure points
    break malloc if $r0 == 0
    break calloc if $r0 == 0
    break realloc if $r0 == 0

    # Pynux specific allocators
    break pynux_alloc if $r0 == 0
    break heap_alloc if $r0 == 0

    echo Allocation failure breakpoints set.\n
    echo Note: Breaks when allocation returns NULL.\n
end
document break-malloc-fail
Set breakpoints on memory allocation failures.
Breaks when malloc, calloc, realloc, or Pynux allocators return NULL.
end

define break-malloc
    echo Setting breakpoint on all malloc calls...\n
    break malloc
    break calloc
    break realloc
    break free
    echo Allocation breakpoints set.\n
end
document break-malloc
Set breakpoints on all memory allocation functions.
Useful for tracking memory usage.
end

define break-heap-corrupt
    echo Setting watchpoint for heap corruption...\n

    # These symbols depend on your heap implementation
    # Adjust addresses based on actual heap layout
    watch *(unsigned int*)(&_heap_start)
    watch *(unsigned int*)(&_heap_end - 4)

    echo Heap boundary watchpoints set.\n
end
document break-heap-corrupt
Set watchpoints on heap boundaries.
Helps detect heap corruption.
end

# -----------------------------------------------------------------------------
# Assertion Breakpoints
# -----------------------------------------------------------------------------

define break-assert
    echo Setting breakpoints on assertions...\n

    # Common assertion failure functions
    break __assert_fail
    break __assert_func
    break assert_failed
    break pynux_assert_fail
    break panic

    echo Assertion breakpoints set.\n
end
document break-assert
Set breakpoints on assertion failures.
Breaks on __assert_fail, __assert_func, assert_failed, panic.
end

define break-panic
    echo Setting breakpoint on kernel panic...\n
    break panic
    break kernel_panic
    break pynux_panic
    echo Panic breakpoints set.\n
end
document break-panic
Set breakpoints on kernel panic functions.
end

# -----------------------------------------------------------------------------
# Interrupt Breakpoints
# -----------------------------------------------------------------------------

define break-irq
    if $argc == 0
        echo Usage: break-irq <irq_name>\n
        echo Example: break-irq USART1_IRQHandler\n
    else
        printf "Setting breakpoint on IRQ handler: %s\n", "$arg0"
        break $arg0
    end
end
document break-irq
Set breakpoint on a specific IRQ handler.
Usage: break-irq <handler_name>
Example: break-irq USART1_IRQHandler
end

define break-systick
    echo Setting breakpoint on SysTick...\n
    break SysTick_Handler
    echo SysTick breakpoint set.\n
end
document break-systick
Set breakpoint on SysTick timer interrupt.
end

define break-pendsv
    echo Setting breakpoint on PendSV...\n
    break PendSV_Handler
    echo PendSV breakpoint set.\n
end
document break-pendsv
Set breakpoint on PendSV handler.
Often used for context switching.
end

define break-svc
    echo Setting breakpoint on SVC...\n
    break SVC_Handler
    echo SVC breakpoint set.\n
end
document break-svc
Set breakpoint on SVC (Supervisor Call) handler.
end

# -----------------------------------------------------------------------------
# Scheduler Breakpoints
# -----------------------------------------------------------------------------

define break-context-switch
    echo Setting breakpoints on context switch...\n
    break context_switch
    break switch_context
    break schedule
    break PendSV_Handler
    echo Context switch breakpoints set.\n
end
document break-context-switch
Set breakpoints on context switch points.
end

define break-scheduler
    echo Setting breakpoints on scheduler...\n
    break schedule
    break scheduler_run
    break scheduler_tick
    break task_switch
    echo Scheduler breakpoints set.\n
end
document break-scheduler
Set breakpoints on scheduler functions.
end

# -----------------------------------------------------------------------------
# Driver Breakpoints
# -----------------------------------------------------------------------------

define break-uart
    echo Setting breakpoints on UART...\n
    break USART1_IRQHandler
    break USART2_IRQHandler
    break USART3_IRQHandler
    break uart_init
    break uart_send
    break uart_receive
    echo UART breakpoints set.\n
end
document break-uart
Set breakpoints on UART/USART handlers and functions.
end

define break-spi
    echo Setting breakpoints on SPI...\n
    break SPI1_IRQHandler
    break SPI2_IRQHandler
    break spi_init
    break spi_transfer
    echo SPI breakpoints set.\n
end
document break-spi
Set breakpoints on SPI handlers and functions.
end

define break-i2c
    echo Setting breakpoints on I2C...\n
    break I2C1_EV_IRQHandler
    break I2C1_ER_IRQHandler
    break I2C2_EV_IRQHandler
    break I2C2_ER_IRQHandler
    break i2c_init
    break i2c_read
    break i2c_write
    echo I2C breakpoints set.\n
end
document break-i2c
Set breakpoints on I2C handlers and functions.
end

# -----------------------------------------------------------------------------
# Watchpoints
# -----------------------------------------------------------------------------

define watch-var
    if $argc == 0
        echo Usage: watch-var <variable>\n
        echo Sets a watchpoint that triggers on any write to the variable.\n
    else
        printf "Setting watchpoint on: %s\n", "$arg0"
        watch $arg0
    end
end
document watch-var
Set a watchpoint on a variable.
Usage: watch-var <variable>
Triggers on any write to the variable.
end

define watch-read
    if $argc == 0
        echo Usage: watch-read <variable>\n
        echo Sets a watchpoint that triggers on read access.\n
    else
        printf "Setting read watchpoint on: %s\n", "$arg0"
        rwatch $arg0
    end
end
document watch-read
Set a read watchpoint on a variable.
Usage: watch-read <variable>
Triggers on any read from the variable.
end

define watch-access
    if $argc == 0
        echo Usage: watch-access <variable>\n
        echo Sets a watchpoint that triggers on any access.\n
    else
        printf "Setting access watchpoint on: %s\n", "$arg0"
        awatch $arg0
    end
end
document watch-access
Set an access watchpoint on a variable.
Usage: watch-access <variable>
Triggers on any read or write.
end

# -----------------------------------------------------------------------------
# Conditional Breakpoints
# -----------------------------------------------------------------------------

define break-pid
    if $argc == 0
        echo Usage: break-pid <pid>\n
        echo Breaks when current process matches PID.\n
    else
        printf "Setting breakpoint for PID %d\n", $arg0
        break schedule if current_process->pid == $arg0
    end
end
document break-pid
Set conditional breakpoint for a specific process.
Usage: break-pid <pid>
Breaks when scheduler switches to that process.
end

# -----------------------------------------------------------------------------
# Breakpoint Management
# -----------------------------------------------------------------------------

define break-clear-all
    echo Deleting all breakpoints and watchpoints...\n
    delete
    echo Done.\n
end
document break-clear-all
Delete all breakpoints and watchpoints.
end

define break-disable-all
    echo Disabling all breakpoints...\n
    disable
    echo Done.\n
end
document break-disable-all
Disable all breakpoints without deleting them.
end

define break-enable-all
    echo Enabling all breakpoints...\n
    enable
    echo Done.\n
end
document break-enable-all
Enable all breakpoints.
end

define break-list
    echo === Active Breakpoints ===\n
    info breakpoints
    echo \n=== Watchpoints ===\n
    info watchpoints
end
document break-list
List all breakpoints and watchpoints.
end
