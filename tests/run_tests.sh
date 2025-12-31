#!/bin/bash
# Pynux Test Runner
#
# Build and run all tests in QEMU.
#
# Usage:
#     ./tests/run_tests.sh [OPTIONS] [test_pattern]
#
# Options:
#     --timeout=N     Test timeout in seconds (default: 30)
#     --verbose       Show verbose output
#     --no-build      Skip the build step
#     --help          Show this help message
#
# Examples:
#     ./tests/run_tests.sh                    # Run all tests
#     ./tests/run_tests.sh --verbose          # Verbose output
#     ./tests/run_tests.sh timer              # Only timer tests
#     ./tests/run_tests.sh --no-build memory  # Skip build, run memory tests

set -e

# Change to project root
cd "$(dirname "$0")/.."

# Parse arguments
TIMEOUT=30
VERBOSE=""
NO_BUILD=0
TEST_PATTERN=""
SHOW_HELP=0

for arg in "$@"; do
    case $arg in
        --timeout=*)
            TIMEOUT="${arg#*=}"
            ;;
        --verbose|-v)
            VERBOSE="--verbose"
            ;;
        --no-build)
            NO_BUILD=1
            ;;
        --help|-h)
            SHOW_HELP=1
            ;;
        -*)
            echo "Unknown option: $arg"
            SHOW_HELP=1
            ;;
        *)
            TEST_PATTERN="$arg"
            ;;
    esac
done

if [ "$SHOW_HELP" -eq 1 ]; then
    echo "Pynux Test Runner"
    echo ""
    echo "Usage: $0 [OPTIONS] [test_pattern]"
    echo ""
    echo "Options:"
    echo "  --timeout=N     Test timeout in seconds (default: 30)"
    echo "  --verbose       Show verbose QEMU output"
    echo "  --no-build      Skip the build step"
    echo "  --help          Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                    # Run all tests"
    echo "  $0 --verbose          # Verbose output"
    echo "  $0 timer              # Only timer tests"
    echo "  $0 --no-build memory  # Skip build, run memory tests"
    exit 0
fi

# Build if needed
if [ "$NO_BUILD" -eq 0 ]; then
    echo "=== Building Pynux for QEMU ==="
    ./build.sh --target=qemu

    if [ $? -ne 0 ]; then
        echo ""
        echo "Build failed!"
        exit 2
    fi
    echo ""
fi

# Check if kernel exists
if [ ! -f "build/pynux.elf" ]; then
    echo "Error: build/pynux.elf not found"
    echo "Run './build.sh' first to build the kernel."
    exit 2
fi

# Run tests
echo "=== Running Tests in QEMU ==="
python3 tests/qemu_runner.py --timeout="$TIMEOUT" $VERBOSE "$TEST_PATTERN"

exit $?
