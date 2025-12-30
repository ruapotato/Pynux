# pwd - print working directory

from lib.io import print_str, print_newline

# Current working directory (shared with shell)
cwd: Array[128, char]
cwd_initialized: bool = False

def pwd_init():
    global cwd_initialized
    cwd[0] = '/'
    cwd[1] = '\0'
    cwd_initialized = True

def pwd_get() -> Ptr[char]:
    if not cwd_initialized:
        pwd_init()
    return &cwd[0]

def pwd_set(path: Ptr[char]):
    global cwd_initialized
    if not cwd_initialized:
        pwd_init()

    i: int32 = 0
    while path[i] != '\0' and i < 127:
        cwd[i] = path[i]
        i = i + 1
    cwd[i] = '\0'

def pwd():
    print_str(pwd_get())
    print_newline()

def main() -> int32:
    pwd()
    return 0
