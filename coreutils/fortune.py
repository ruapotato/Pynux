# fortune - print a random fortune

from lib.io import print_str, print_newline

# Simple LCG random number generator
fortune_seed: int32 = 12345

def fortune_rand() -> int32:
    global fortune_seed
    fortune_seed = (fortune_seed * 1103515245 + 12345) & 0x7FFFFFFF
    return fortune_seed

def fortune():
    fortunes: Array[10, Ptr[char]]
    fortunes[0] = "The best way to predict the future is to invent it."
    fortunes[1] = "In theory, there is no difference between theory and practice."
    fortunes[2] = "Simplicity is the ultimate sophistication."
    fortunes[3] = "First, solve the problem. Then, write the code."
    fortunes[4] = "Talk is cheap. Show me the code."
    fortunes[5] = "The only way to go fast is to go well."
    fortunes[6] = "Any fool can write code that a computer can understand."
    fortunes[7] = "Debugging is twice as hard as writing the code."
    fortunes[8] = "It works on my machine."
    fortunes[9] = "There are only two hard things: cache invalidation and naming."

    index: int32 = fortune_rand() % 10
    print_str(fortunes[index])
    print_newline()

def main() -> int32:
    fortune()
    return 0
