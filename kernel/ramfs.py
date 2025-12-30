# Pynux RAM Filesystem
#
# Simple in-memory filesystem for bare-metal ARM.
# Provides basic file operations.

from lib.memory import alloc, free, memcpy, memset
from lib.string import strcmp, strcpy, strlen, strrchr

# Maximum files and directories
MAX_FILES: int32 = 64
MAX_PATH: int32 = 128
MAX_FILE_SIZE: int32 = 4096
MAX_NAME: int32 = 32

# File types
FTYPE_FREE: int32 = 0
FTYPE_FILE: int32 = 1
FTYPE_DIR: int32 = 2

# File entry structure (in arrays for simplicity)
# Arrays indexed by file descriptor (0-63)
file_types: Array[64, int32]      # FTYPE_*
file_names: Array[64, Array[32, char]]  # Filename
file_parents: Array[64, int32]    # Parent directory fd (-1 for root)
file_sizes: Array[64, int32]      # File size
file_data: Array[64, Ptr[uint8]]  # File data pointer

# Filesystem state
fs_initialized: bool = False
root_fd: int32 = 0

def ramfs_init():
    global fs_initialized, root_fd

    state: int32 = critical_enter()

    # Clear all entries
    i: int32 = 0
    while i < MAX_FILES:
        file_types[i] = FTYPE_FREE
        file_sizes[i] = 0
        file_data[i] = Ptr[uint8](0)
        file_parents[i] = -1
        i = i + 1

    # Create root directory
    file_types[0] = FTYPE_DIR
    file_names[0][0] = '/'
    file_names[0][1] = '\0'
    file_parents[0] = -1
    root_fd = 0

    fs_initialized = True

    critical_exit(state)

# Find a free file entry
def ramfs_alloc_entry() -> int32:
    i: int32 = 1  # Start from 1, 0 is root
    while i < MAX_FILES:
        if file_types[i] == FTYPE_FREE:
            return i
        i = i + 1
    return -1  # No free entry

# Find file by path, returns fd or -1
def ramfs_lookup(path: Ptr[char]) -> int32:
    if path[0] == '\0':
        return -1

    # Handle root
    if path[0] == '/' and path[1] == '\0':
        return root_fd

    # Parse path components
    current_dir: int32 = root_fd
    start: int32 = 0

    if path[0] == '/':
        start = 1

    i: int32 = start
    name_start: int32 = start

    while True:
        if path[i] == '/' or path[i] == '\0':
            # Extract component name
            name_len: int32 = i - name_start
            if name_len > 0:
                # Search for this name in current directory
                found: int32 = -1
                j: int32 = 0
                while j < MAX_FILES:
                    if file_types[j] != FTYPE_FREE and file_parents[j] == current_dir:
                        # Compare names using pointer (workaround for 2D array bug)
                        name_ptr: Ptr[char] = &file_names[j][0]
                        is_match: bool = True
                        k: int32 = 0
                        while k < name_len:
                            if name_ptr[k] != path[name_start + k]:
                                is_match = False
                                break
                            k = k + 1
                        if is_match and name_ptr[name_len] == '\0':
                            found = j
                            break
                    j = j + 1

                if found < 0:
                    return -1  # Not found

                if path[i] == '\0':
                    return found  # Final component
                else:
                    if file_types[found] != FTYPE_DIR:
                        return -1  # Not a directory
                    current_dir = found
                    name_start = i + 1

            if path[i] == '\0':
                break
            name_start = i + 1
        i = i + 1

    return current_dir

# Create file or directory
def ramfs_create(path: Ptr[char], is_dir: bool) -> int32:
    state: int32 = critical_enter()

    # Check if already exists
    if ramfs_lookup(path) >= 0:
        critical_exit(state)
        return -1  # Already exists

    # Find parent directory
    parent_fd: int32 = root_fd
    name_start: int32 = 0

    # Find last slash to get parent path and filename
    last_slash: Ptr[char] = strrchr(path, '/')
    if last_slash != Ptr[char](0):
        # Has directory component
        slash_pos: int32 = cast[int32](last_slash) - cast[int32](path)
        if slash_pos > 0:
            # Extract parent path
            parent_path: Array[128, char]
            i: int32 = 0
            while i < slash_pos:
                parent_path[i] = path[i]
                i = i + 1
            parent_path[i] = '\0'
            parent_fd = ramfs_lookup(&parent_path[0])
            if parent_fd < 0:
                critical_exit(state)
                return -1  # Parent not found
        name_start = slash_pos + 1
    else:
        name_start = 0

    # Allocate entry
    fd: int32 = ramfs_alloc_entry()
    if fd < 0:
        critical_exit(state)
        return -1  # No space

    # Set up entry
    if is_dir:
        file_types[fd] = FTYPE_DIR
    else:
        file_types[fd] = FTYPE_FILE

    # Copy name
    i: int32 = 0
    while path[name_start + i] != '\0' and i < MAX_NAME - 1:
        file_names[fd][i] = path[name_start + i]
        i = i + 1
    file_names[fd][i] = '\0'

    file_parents[fd] = parent_fd
    file_sizes[fd] = 0
    file_data[fd] = Ptr[uint8](0)

    critical_exit(state)
    return fd

# Delete file
def ramfs_delete(path: Ptr[char]) -> int32:
    state: int32 = critical_enter()

    fd: int32 = ramfs_lookup(path)
    if fd < 0:
        critical_exit(state)
        return -1

    if fd == root_fd:
        critical_exit(state)
        return -1  # Can't delete root

    # Check if directory is empty
    if file_types[fd] == FTYPE_DIR:
        i: int32 = 0
        while i < MAX_FILES:
            if file_types[i] != FTYPE_FREE and file_parents[i] == fd:
                critical_exit(state)
                return -1  # Not empty
            i = i + 1

    # Free data if any
    if file_data[fd] != Ptr[uint8](0):
        free(file_data[fd])

    file_types[fd] = FTYPE_FREE

    critical_exit(state)
    return 0

# Read file contents
def ramfs_read(path: Ptr[char], buf: Ptr[uint8], count: int32) -> int32:
    fd: int32 = ramfs_lookup(path)
    if fd < 0:
        return -1

    if file_types[fd] != FTYPE_FILE:
        return -1

    size: int32 = file_sizes[fd]
    if count > size:
        count = size

    if count > 0 and file_data[fd] != Ptr[uint8](0):
        memcpy(buf, file_data[fd], count)

    return count

# Write to file
def ramfs_write(path: Ptr[char], data: Ptr[char]) -> int32:
    state: int32 = critical_enter()

    fd: int32 = ramfs_lookup(path)
    if fd < 0:
        # Create file
        fd = ramfs_create_internal(path)
        if fd < 0:
            critical_exit(state)
            return -1

    if file_types[fd] != FTYPE_FILE:
        critical_exit(state)
        return -1

    # Calculate data length
    length: int32 = strlen(data)
    if length > MAX_FILE_SIZE:
        length = MAX_FILE_SIZE

    # Allocate/reallocate buffer
    if file_data[fd] == Ptr[uint8](0):
        file_data[fd] = alloc(MAX_FILE_SIZE)
    if file_data[fd] == Ptr[uint8](0):
        critical_exit(state)
        return -1

    # Copy data
    memcpy(file_data[fd], cast[Ptr[uint8]](data), length)
    file_sizes[fd] = length

    critical_exit(state)
    return length

# Internal create without critical section (called from within critical section)
def ramfs_create_internal(path: Ptr[char]) -> int32:
    # Check if already exists
    if ramfs_lookup(path) >= 0:
        return -1  # Already exists

    # Find parent directory
    parent_fd: int32 = root_fd
    name_start: int32 = 0

    # Find last slash to get parent path and filename
    last_slash: Ptr[char] = strrchr(path, '/')
    if last_slash != Ptr[char](0):
        # Has directory component
        slash_pos: int32 = cast[int32](last_slash) - cast[int32](path)
        if slash_pos > 0:
            # Extract parent path
            parent_path: Array[128, char]
            i: int32 = 0
            while i < slash_pos:
                parent_path[i] = path[i]
                i = i + 1
            parent_path[i] = '\0'
            parent_fd = ramfs_lookup(&parent_path[0])
            if parent_fd < 0:
                return -1  # Parent not found
        name_start = slash_pos + 1
    else:
        name_start = 0

    # Allocate entry
    fd: int32 = ramfs_alloc_entry()
    if fd < 0:
        return -1  # No space

    # Set up entry as file
    file_types[fd] = FTYPE_FILE

    # Copy name
    i: int32 = 0
    while path[name_start + i] != '\0' and i < MAX_NAME - 1:
        file_names[fd][i] = path[name_start + i]
        i = i + 1
    file_names[fd][i] = '\0'

    file_parents[fd] = parent_fd
    file_sizes[fd] = 0
    file_data[fd] = Ptr[uint8](0)

    return fd

# Append to file
def ramfs_append(path: Ptr[char], data: Ptr[char]) -> int32:
    state: int32 = critical_enter()

    fd: int32 = ramfs_lookup(path)
    if fd < 0:
        critical_exit(state)
        return ramfs_write(path, data)

    if file_types[fd] != FTYPE_FILE:
        critical_exit(state)
        return -1

    length: int32 = strlen(data)
    current_size: int32 = file_sizes[fd]

    if current_size + length > MAX_FILE_SIZE:
        length = MAX_FILE_SIZE - current_size

    if length <= 0:
        critical_exit(state)
        return 0

    if file_data[fd] == Ptr[uint8](0):
        file_data[fd] = alloc(MAX_FILE_SIZE)
    if file_data[fd] == Ptr[uint8](0):
        critical_exit(state)
        return -1

    # Append data
    memcpy(&file_data[fd][current_size], cast[Ptr[uint8]](data), length)
    file_sizes[fd] = current_size + length

    critical_exit(state)
    return length

# Get file size
def ramfs_size(path: Ptr[char]) -> int32:
    fd: int32 = ramfs_lookup(path)
    if fd < 0:
        return -1
    return file_sizes[fd]

# Check if path is directory
def ramfs_isdir(path: Ptr[char]) -> bool:
    fd: int32 = ramfs_lookup(path)
    if fd < 0:
        return False
    return file_types[fd] == FTYPE_DIR

# Check if path exists
def ramfs_exists(path: Ptr[char]) -> bool:
    return ramfs_lookup(path) >= 0

# List directory contents
# Calls callback for each entry: callback(name, is_dir, size)
def ramfs_list(path: Ptr[char], callback: Ptr[void]) -> int32:
    fd: int32 = ramfs_lookup(path)
    if fd < 0:
        return -1

    if file_types[fd] != FTYPE_DIR:
        return -1

    count: int32 = 0
    i: int32 = 0
    while i < MAX_FILES:
        if file_types[i] != FTYPE_FREE and file_parents[i] == fd:
            # Found an entry
            count = count + 1
            # Note: callback would be called here
        i = i + 1

    return count

# Get directory entry by index
def ramfs_readdir(dir_path: Ptr[char], index: int32, name_buf: Ptr[char]) -> int32:
    fd: int32 = ramfs_lookup(dir_path)
    if fd < 0:
        return -1

    if file_types[fd] != FTYPE_DIR:
        return -1

    count: int32 = 0
    i: int32 = 0
    while i < MAX_FILES:
        if file_types[i] != FTYPE_FREE and file_parents[i] == fd:
            if count == index:
                strcpy(name_buf, &file_names[i][0])
                if file_types[i] == FTYPE_DIR:
                    return 1  # Is directory
                else:
                    return 0  # Is file
            count = count + 1
        i = i + 1

    return -1  # Index out of range
