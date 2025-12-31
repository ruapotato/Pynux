# Pynux OS GDB Memory Commands
# Memory inspection and peripheral debugging

# -----------------------------------------------------------------------------
# Memory Dump
# -----------------------------------------------------------------------------

define mem-dump
    if $argc < 2
        echo Usage: mem-dump <address> <length>\n
        echo Example: mem-dump 0x20000000 256\n
    else
        set $addr = $arg0
        set $len = $arg1
        set $rows = ($len + 15) / 16
        set $row = 0

        echo \n
        while $row < $rows
            set $offset = $row * 16
            if $offset < $len
                printf "%08x: ", $addr + $offset

                # Print hex bytes
                set $col = 0
                while $col < 16
                    if ($offset + $col) < $len
                        set $byte = *(unsigned char*)($addr + $offset + $col)
                        printf "%02x ", $byte
                    else
                        printf "   "
                    end
                    if $col == 7
                        printf " "
                    end
                    set $col = $col + 1
                end

                printf " |"

                # Print ASCII
                set $col = 0
                while $col < 16
                    if ($offset + $col) < $len
                        set $byte = *(unsigned char*)($addr + $offset + $col)
                        if $byte >= 0x20 && $byte < 0x7f
                            printf "%c", $byte
                        else
                            printf "."
                        end
                    end
                    set $col = $col + 1
                end

                printf "|\n"
            end
            set $row = $row + 1
        end
        echo \n
    end
end
document mem-dump
Dump memory in hex and ASCII format.
Usage: mem-dump <address> <length>
Example: mem-dump 0x20000000 256
end

# -----------------------------------------------------------------------------
# Memory Regions
# -----------------------------------------------------------------------------

define mem-regions
    echo === Memory Regions (Typical Cortex-M) ===\n\n

    printf "Region          Start        End          Size         Description\n"
    printf "--------------- ------------ ------------ ------------ -----------\n"
    printf "Code            0x00000000   0x1FFFFFFF   512 MB       Flash, ROM\n"
    printf "SRAM            0x20000000   0x3FFFFFFF   512 MB       On-chip SRAM\n"
    printf "Peripheral      0x40000000   0x5FFFFFFF   512 MB       On-chip peripherals\n"
    printf "RAM             0x60000000   0x7FFFFFFF   512 MB       External RAM\n"
    printf "RAM             0x80000000   0x9FFFFFFF   512 MB       External RAM\n"
    printf "Device          0xA0000000   0xBFFFFFFF   512 MB       External device\n"
    printf "Device          0xC0000000   0xDFFFFFFF   512 MB       External device\n"
    printf "System          0xE0000000   0xFFFFFFFF   512 MB       PPB, Vendor\n"

    echo \n=== System Region Details ===\n\n
    printf "ITM             0xE0000000   0xE0000FFF   4 KB\n"
    printf "DWT             0xE0001000   0xE0001FFF   4 KB\n"
    printf "FPB             0xE0002000   0xE0002FFF   4 KB\n"
    printf "SCS (NVIC/SCB)  0xE000E000   0xE000EFFF   4 KB\n"
    printf "TPIU            0xE0040000   0xE0040FFF   4 KB\n"
    printf "ETM             0xE0041000   0xE0041FFF   4 KB\n"
    printf "ROM Table       0xE00FF000   0xE00FFFFF   4 KB\n"
end
document mem-regions
Display standard Cortex-M memory map.
Shows code, SRAM, peripheral, and system regions.
end

define mem-info
    echo === Memory Access Test ===\n

    if $argc == 0
        echo Usage: mem-info <address>\n
        echo Tests if memory at address is accessible and shows value.\n
    else
        set $addr = $arg0
        printf "Address: 0x%08x\n", $addr

        # Determine region
        if $addr < 0x20000000
            printf "Region: Code (Flash/ROM)\n"
        else
            if $addr < 0x40000000
                printf "Region: SRAM\n"
            else
                if $addr < 0x60000000
                    printf "Region: Peripheral\n"
                else
                    if $addr < 0xE0000000
                        printf "Region: External Memory/Device\n"
                    else
                        printf "Region: System (PPB)\n"
                    end
                end
            end
        end

        printf "Value (word):  0x%08x\n", *(unsigned int*)$addr
        printf "Value (hword): 0x%04x\n", *(unsigned short*)$addr
        printf "Value (byte):  0x%02x\n", *(unsigned char*)$addr
    end
end
document mem-info
Test memory access and show region information.
Usage: mem-info <address>
end

# -----------------------------------------------------------------------------
# Peripheral Register Dump
# -----------------------------------------------------------------------------

define periph-dump
    if $argc == 0
        echo Usage: periph-dump <base_address> [num_regs]\n
        echo Example: periph-dump 0x40021000 16\n
        echo \nDumps peripheral registers starting at base address.\n
    else
        set $base = $arg0
        if $argc >= 2
            set $count = $arg1
        else
            set $count = 16
        end

        printf "\n=== Peripheral Registers at 0x%08x ===\n\n", $base
        printf "Offset     Address      Value\n"
        printf "---------- ------------ ----------\n"

        set $i = 0
        while $i < $count
            set $addr = $base + ($i * 4)
            set $val = *(unsigned int*)$addr
            printf "0x%03x      0x%08x   0x%08x\n", $i * 4, $addr, $val
            set $i = $i + 1
        end
        echo \n
    end
end
document periph-dump
Dump peripheral registers.
Usage: periph-dump <base_address> [num_regs]
Default: 16 registers
end

# -----------------------------------------------------------------------------
# Common Peripheral Bases
# -----------------------------------------------------------------------------

define periph-rcc
    echo === RCC Registers (STM32) ===\n
    periph-dump 0x40021000 16
end
document periph-rcc
Dump RCC (Reset and Clock Control) registers.
Assumes STM32 peripheral layout.
end

define periph-gpio
    if $argc == 0
        echo Usage: periph-gpio <port>\n
        echo   port: A=0, B=1, C=2, D=3, E=4, F=5, G=6\n
        echo Example: periph-gpio 0\n
    else
        set $port = $arg0
        set $base = 0x40010800 + ($port * 0x400)
        printf "=== GPIO Port %c Registers ===\n", 'A' + $port
        periph-dump $base 8
    end
end
document periph-gpio
Dump GPIO port registers.
Usage: periph-gpio <port_number>
Port: A=0, B=1, C=2, etc.
end

define periph-usart
    if $argc == 0
        echo Usage: periph-usart <number>\n
        echo Example: periph-usart 1\n
    else
        set $num = $arg0
        if $num == 1
            set $base = 0x40013800
        else
            set $base = 0x40004400 + (($num - 2) * 0x400)
        end
        printf "=== USART%d Registers ===\n", $num
        periph-dump $base 8
    end
end
document periph-usart
Dump USART registers.
Usage: periph-usart <number>
Example: periph-usart 1
end

# -----------------------------------------------------------------------------
# Memory Search
# -----------------------------------------------------------------------------

define mem-find
    if $argc < 3
        echo Usage: mem-find <start> <end> <pattern>\n
        echo Example: mem-find 0x20000000 0x20010000 0xDEADBEEF\n
    else
        set $start = $arg0
        set $end = $arg1
        set $pattern = $arg2

        printf "Searching for 0x%08x in range 0x%08x - 0x%08x\n", $pattern, $start, $end

        set $addr = $start
        set $found = 0
        while $addr < $end
            set $val = *(unsigned int*)$addr
            if $val == $pattern
                printf "Found at 0x%08x\n", $addr
                set $found = $found + 1
            end
            set $addr = $addr + 4
        end

        printf "Total matches: %d\n", $found
    end
end
document mem-find
Search memory for a 32-bit pattern.
Usage: mem-find <start> <end> <pattern>
Example: mem-find 0x20000000 0x20010000 0xDEADBEEF
end

# -----------------------------------------------------------------------------
# Memory Fill
# -----------------------------------------------------------------------------

define mem-fill
    if $argc < 3
        echo Usage: mem-fill <start> <length> <pattern>\n
        echo Example: mem-fill 0x20000000 256 0xDEADBEEF\n
    else
        set $start = $arg0
        set $len = $arg1
        set $pattern = $arg2

        printf "Filling 0x%08x - 0x%08x with 0x%08x\n", $start, $start + $len, $pattern

        set $addr = $start
        set $end = $start + $len
        while $addr < $end
            set *(unsigned int*)$addr = $pattern
            set $addr = $addr + 4
        end

        echo Done.\n
    end
end
document mem-fill
Fill memory with a pattern.
Usage: mem-fill <start> <length> <pattern>
Example: mem-fill 0x20000000 256 0xDEADBEEF
end

# -----------------------------------------------------------------------------
# Memory Compare
# -----------------------------------------------------------------------------

define mem-cmp
    if $argc < 3
        echo Usage: mem-cmp <addr1> <addr2> <length>\n
        echo Compare two memory regions.\n
    else
        set $addr1 = $arg0
        set $addr2 = $arg1
        set $len = $arg2

        printf "Comparing 0x%08x and 0x%08x (%d bytes)\n", $addr1, $addr2, $len

        set $i = 0
        set $diffs = 0
        while $i < $len
            set $val1 = *(unsigned char*)($addr1 + $i)
            set $val2 = *(unsigned char*)($addr2 + $i)
            if $val1 != $val2
                if $diffs < 10
                    printf "Diff at offset 0x%x: 0x%02x != 0x%02x\n", $i, $val1, $val2
                end
                set $diffs = $diffs + 1
            end
            set $i = $i + 1
        end

        if $diffs == 0
            printf "Memory regions are identical.\n"
        else
            printf "Total differences: %d\n", $diffs
        end
    end
end
document mem-cmp
Compare two memory regions.
Usage: mem-cmp <addr1> <addr2> <length>
Shows first 10 differences if any.
end

# -----------------------------------------------------------------------------
# Flash Operations
# -----------------------------------------------------------------------------

define flash-info
    echo === Flash Memory Info ===\n
    printf "Flash base:     0x08000000\n"
    printf "Option bytes:   0x1FFFF800\n"
    printf "System memory:  0x1FFFF000\n"

    echo \nFlash Control Register:\n
    set $flash_cr = *(unsigned int*)0x40022010
    printf "FLASH_CR: 0x%08x\n", $flash_cr

    set $flash_sr = *(unsigned int*)0x4002200C
    printf "FLASH_SR: 0x%08x\n", $flash_sr
    if $flash_sr & 0x01
        printf "  BSY: Flash busy\n"
    end
    if $flash_sr & 0x04
        printf "  PGERR: Programming error\n"
    end
    if $flash_sr & 0x10
        printf "  WRPRTERR: Write protection error\n"
    end
end
document flash-info
Display Flash memory controller status.
Shows control and status registers.
end
