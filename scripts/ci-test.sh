#!/bin/bash
# Pynux CI Test Runner
#
# Builds and runs tests in QEMU, returns exit codes for CI integration.
#
# Usage:
#   ./scripts/ci-test.sh           # Run all tests
#   ./scripts/ci-test.sh --demo    # Run demo verification
#   ./scripts/ci-test.sh --quick   # Quick smoke test (shorter timeout)
#
# Exit codes:
#   0 - All tests passed
#   1 - Some tests failed
#   2 - Build failed
#   3 - QEMU execution failed

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Configuration
TIMEOUT=180
MODE="test"
VERBOSE=false

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
for arg in "$@"; do
    case $arg in
        --demo)
            MODE="demo"
            TIMEOUT=60
            ;;
        --quick)
            TIMEOUT=60
            ;;
        --verbose|-v)
            VERBOSE=true
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --demo     Run demo verification instead of tests"
            echo "  --quick    Quick smoke test (60s timeout)"
            echo "  --verbose  Show all output"
            echo "  --help     Show this help"
            exit 0
            ;;
    esac
done

echo -e "${CYAN}======================================${NC}"
echo -e "${CYAN}  Pynux CI Test Runner${NC}"
echo -e "${CYAN}======================================${NC}"
echo ""

# Step 1: Build
echo -e "${YELLOW}[1/3] Building kernel (mode: $MODE)...${NC}"
rm -rf build/

if [ "$MODE" = "demo" ]; then
    BUILD_OUTPUT=$(./build.sh --demo --target=qemu 2>&1) || {
        echo -e "${RED}Build failed!${NC}"
        echo "$BUILD_OUTPUT"
        exit 2
    }
else
    BUILD_OUTPUT=$(./build.sh --test --target=qemu 2>&1) || {
        echo -e "${RED}Build failed!${NC}"
        echo "$BUILD_OUTPUT"
        exit 2
    }
fi

if [ "$VERBOSE" = true ]; then
    echo "$BUILD_OUTPUT"
fi
echo -e "${GREEN}Build complete.${NC}"
echo ""

# Step 2: Run in QEMU
echo -e "${YELLOW}[2/3] Running in QEMU (timeout: ${TIMEOUT}s)...${NC}"
QEMU_OUTPUT=$(timeout $TIMEOUT qemu-system-arm \
    -M mps2-an385 \
    -cpu cortex-m3 \
    -nographic \
    -kernel build/pynux.elf 2>&1) || true

if [ "$VERBOSE" = true ]; then
    echo "$QEMU_OUTPUT"
fi

# Step 3: Parse results
echo -e "${YELLOW}[3/3] Analyzing results...${NC}"
echo ""

# Check for success marker
if echo "$QEMU_OUTPUT" | grep -q "\[QEMU_EXIT\] SUCCESS"; then
    echo -e "${GREEN}======================================${NC}"

    if [ "$MODE" = "demo" ]; then
        echo -e "${GREEN}  All demos completed successfully!${NC}"
    else
        # Extract test counts
        PASSED=$(echo "$QEMU_OUTPUT" | grep -o "Passed:.*[0-9]*" | tail -1 | grep -o "[0-9]*" || echo "?")
        FAILED=$(echo "$QEMU_OUTPUT" | grep -o "Failed:.*[0-9]*" | tail -1 | grep -o "[0-9]*" || echo "?")
        TOTAL=$(echo "$QEMU_OUTPUT" | grep -o "Total:.*[0-9]*" | tail -1 | grep -o "[0-9]*" || echo "?")

        echo -e "${GREEN}  All tests passed!${NC}"
        echo -e "${GREEN}  Tests: $PASSED passed, $FAILED failed${NC}"
    fi

    echo -e "${GREEN}======================================${NC}"
    exit 0

elif echo "$QEMU_OUTPUT" | grep -q "\[QEMU_EXIT\] FAILURE"; then
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}  Some tests failed!${NC}"

    # Show failed tests
    echo "$QEMU_OUTPUT" | grep -E "^\[FAIL\]" || true

    echo -e "${RED}======================================${NC}"
    exit 1

else
    echo -e "${RED}======================================${NC}"
    echo -e "${RED}  QEMU execution failed or timed out${NC}"
    echo -e "${RED}======================================${NC}"

    # Show last few lines of output
    echo ""
    echo "Last output:"
    echo "$QEMU_OUTPUT" | tail -20

    exit 3
fi
