# Pynux Test Makefile
#
# Build and run tests for Pynux OS.
#
# Usage:
#     make              # Build kernel and run all tests
#     make build        # Just build the kernel
#     make test         # Run tests (assumes kernel is built)
#     make test-verbose # Run tests with verbose output
#     make test-kernel  # Run only kernel tests
#     make test-hal     # Run only HAL tests
#     make clean        # Clean build artifacts
#
# The actual build is handled by the main build.sh script.
# This Makefile provides convenient test targets.

.PHONY: all build test test-verbose test-kernel test-hal clean help

# Default target
all: test

# Build the kernel for QEMU
build:
	@echo "Building Pynux for QEMU..."
	cd .. && ./build.sh --target=qemu

# Run all tests
test: build
	@echo "Running tests..."
	python3 qemu_runner.py --timeout=60

# Run tests with verbose output
test-verbose: build
	@echo "Running tests (verbose)..."
	python3 qemu_runner.py --timeout=60 --verbose

# Run only kernel tests
test-kernel: build
	@echo "Running kernel tests..."
	python3 qemu_runner.py --timeout=60 kernel

# Run only HAL tests
test-hal: build
	@echo "Running HAL tests..."
	python3 qemu_runner.py --timeout=60 hal

# Run with specific pattern
test-%: build
	@echo "Running $* tests..."
	python3 qemu_runner.py --timeout=60 $*

# Clean build artifacts
clean:
	cd .. && rm -rf build/

# List available tests
list:
	@echo "Available tests:"
	@python3 qemu_runner.py --list

# Help
help:
	@echo "Pynux Test Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  all           Build and run all tests (default)"
	@echo "  build         Build the kernel for QEMU"
	@echo "  test          Run all tests"
	@echo "  test-verbose  Run tests with verbose output"
	@echo "  test-kernel   Run only kernel tests"
	@echo "  test-hal      Run only HAL tests"
	@echo "  test-<name>   Run tests matching <name>"
	@echo "  list          List available tests"
	@echo "  clean         Clean build artifacts"
	@echo "  help          Show this help"
	@echo ""
	@echo "Examples:"
	@echo "  make                    # Build and run all tests"
	@echo "  make test-verbose       # Run with verbose output"
	@echo "  make test-timer         # Run timer tests only"
	@echo "  make test-memory        # Run memory tests only"
