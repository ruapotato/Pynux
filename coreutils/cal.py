# cal - display calendar
# Shows a simple month calendar

from lib.io import print_str, print_int, print_newline, uart_putc

def print_padded(n: int32, width: int32):
    if n < 10 and width >= 2:
        uart_putc(' ')
    print_int(n)

def days_in_month(month: int32, year: int32) -> int32:
    if month == 2:
        # Leap year check
        if (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0):
            return 29
        return 28
    if month == 4 or month == 6 or month == 9 or month == 11:
        return 30
    return 31

def day_of_week(day: int32, month: int32, year: int32) -> int32:
    # Zeller's formula (0 = Sunday)
    if month < 3:
        month = month + 12
        year = year - 1
    k: int32 = year % 100
    j: int32 = year / 100
    h: int32 = (day + (13 * (month + 1)) / 5 + k + k / 4 + j / 4 - 2 * j) % 7
    return ((h + 6) % 7)  # Convert to 0=Sunday

def cal(month: int32, year: int32):
    months: Array[12, Ptr[char]]
    months[0] = "    January"
    months[1] = "   February"
    months[2] = "     March"
    months[3] = "     April"
    months[4] = "      May"
    months[5] = "     June"
    months[6] = "     July"
    months[7] = "    August"
    months[8] = "   September"
    months[9] = "    October"
    months[10] = "   November"
    months[11] = "   December"

    # Header
    print_str(months[month - 1])
    uart_putc(' ')
    print_int(year)
    print_newline()
    print_str("Su Mo Tu We Th Fr Sa\n")

    # Find starting day
    start_day: int32 = day_of_week(1, month, year)
    num_days: int32 = days_in_month(month, year)

    # Print leading spaces
    i: int32 = 0
    while i < start_day:
        print_str("   ")
        i = i + 1

    # Print days
    day: int32 = 1
    while day <= num_days:
        print_padded(day, 2)
        uart_putc(' ')
        if (start_day + day) % 7 == 0:
            print_newline()
        day = day + 1

    if (start_day + num_days) % 7 != 0:
        print_newline()

def main() -> int32:
    # Default: January 2025
    cal(1, 2025)
    return 0
