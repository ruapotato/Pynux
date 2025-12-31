#!/usr/bin/env python3
"""
Pynux QEMU Test Runner

Runs Pynux tests in QEMU and parses test output from UART.
Provides pass/fail reporting and CI integration via exit codes.

Usage:
    python tests/qemu_runner.py [--timeout=30] [--verbose] [test_pattern]

Options:
    --timeout=N     Timeout in seconds (default: 30)
    --verbose       Show all QEMU output
    --no-color      Disable colored output
    --help          Show this help message

Exit codes:
    0 - All tests passed
    1 - Some tests failed
    2 - Test execution error (timeout, crash, etc.)
"""

import argparse
import glob
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional


class TestStatus(Enum):
    """Test result status."""
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"
    RUNNING = "running"


@dataclass
class TestResult:
    """Result of a single test."""
    name: str
    status: TestStatus
    message: str = ""
    duration_ms: float = 0.0


@dataclass
class TestSuite:
    """Collection of test results."""
    name: str
    results: list = field(default_factory=list)
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    start_time: float = 0.0
    end_time: float = 0.0

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.skipped

    @property
    def duration_ms(self) -> float:
        return (self.end_time - self.start_time) * 1000


class Colors:
    """ANSI color codes for terminal output."""
    RESET = "\033[0m"
    BOLD = "\033[1m"
    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"

    @classmethod
    def disable(cls):
        """Disable all colors."""
        cls.RESET = ""
        cls.BOLD = ""
        cls.RED = ""
        cls.GREEN = ""
        cls.YELLOW = ""
        cls.BLUE = ""
        cls.CYAN = ""


class TestOutputParser:
    """Parse test output from UART."""

    # Test output markers
    TEST_PATTERN = re.compile(r"^\[TEST\]\s+(.+)$")
    PASS_PATTERN = re.compile(r"^\[PASS\]\s+(.+)$")
    FAIL_PATTERN = re.compile(r"^\[FAIL\]\s+(.+?)(?::\s*(.*))?$")
    SKIP_PATTERN = re.compile(r"^\[SKIP\]\s+(.+?)(?::\s*(.*))?$")
    SUMMARY_PATTERN = re.compile(
        r"^\[SUMMARY\]\s+(\d+)\s+passed,\s+(\d+)\s+failed,\s+(\d+)\s+skipped"
    )
    # Alternative summary format (from existing test_framework.py)
    ALT_PASS_PATTERN = re.compile(r"^Passed:\s+(\d+)")
    ALT_FAIL_PATTERN = re.compile(r"^Failed:\s+(\d+)")
    ALT_SKIP_PATTERN = re.compile(r"^Skipped:\s+(\d+)")
    ALL_PASSED_PATTERN = re.compile(r"^All tests passed")
    SOME_FAILED_PATTERN = re.compile(r"^Some tests failed")

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.suite = TestSuite(name="pynux")
        self.current_test: Optional[str] = None
        self.test_start_time: float = 0.0
        self.summary_found = False

    def parse_line(self, line: str) -> Optional[TestResult]:
        """Parse a single line of test output.

        Returns TestResult if line indicates test completion, None otherwise.
        """
        line = line.strip()
        if not line:
            return None

        # Check for test start
        match = self.TEST_PATTERN.match(line)
        if match:
            self.current_test = match.group(1)
            self.test_start_time = time.time()
            if self.verbose:
                print(f"{Colors.CYAN}[TEST]{Colors.RESET} {self.current_test}")
            return None

        # Check for pass
        match = self.PASS_PATTERN.match(line)
        if match:
            name = match.group(1)
            duration = (time.time() - self.test_start_time) * 1000 if self.test_start_time else 0
            result = TestResult(name=name, status=TestStatus.PASS, duration_ms=duration)
            self.suite.results.append(result)
            self.suite.passed += 1
            self.current_test = None
            print(f"{Colors.GREEN}[PASS]{Colors.RESET} {name}")
            return result

        # Check for fail
        match = self.FAIL_PATTERN.match(line)
        if match:
            name = match.group(1)
            message = match.group(2) or ""
            duration = (time.time() - self.test_start_time) * 1000 if self.test_start_time else 0
            result = TestResult(name=name, status=TestStatus.FAIL, message=message, duration_ms=duration)
            self.suite.results.append(result)
            self.suite.failed += 1
            self.current_test = None
            msg_part = f": {message}" if message else ""
            print(f"{Colors.RED}[FAIL]{Colors.RESET} {name}{msg_part}")
            return result

        # Check for skip
        match = self.SKIP_PATTERN.match(line)
        if match:
            name = match.group(1)
            reason = match.group(2) or ""
            result = TestResult(name=name, status=TestStatus.SKIP, message=reason)
            self.suite.results.append(result)
            self.suite.skipped += 1
            self.current_test = None
            reason_part = f": {reason}" if reason else ""
            print(f"{Colors.YELLOW}[SKIP]{Colors.RESET} {name}{reason_part}")
            return result

        # Check for summary line
        match = self.SUMMARY_PATTERN.match(line)
        if match:
            self.summary_found = True
            # Update counts from summary (authoritative)
            self.suite.passed = int(match.group(1))
            self.suite.failed = int(match.group(2))
            self.suite.skipped = int(match.group(3))
            return None

        # Check for alternative summary formats
        match = self.ALT_PASS_PATTERN.match(line)
        if match:
            self.suite.passed = int(match.group(1))
            return None

        match = self.ALT_FAIL_PATTERN.match(line)
        if match:
            self.suite.failed = int(match.group(1))
            return None

        match = self.ALT_SKIP_PATTERN.match(line)
        if match:
            self.suite.skipped = int(match.group(1))
            return None

        if self.ALL_PASSED_PATTERN.match(line) or self.SOME_FAILED_PATTERN.match(line):
            self.summary_found = True
            return None

        # Verbose mode: print other output
        if self.verbose:
            print(f"  {line}")

        return None

    def parse_output(self, output: str) -> TestSuite:
        """Parse complete test output."""
        self.suite.start_time = time.time()
        for line in output.split('\n'):
            self.parse_line(line)
        self.suite.end_time = time.time()
        return self.suite


class QEMURunner:
    """Run tests in QEMU and capture output."""

    # Default QEMU settings for MPS2-AN385
    QEMU_CMD = "qemu-system-arm"
    QEMU_MACHINE = "mps2-an385"
    QEMU_CPU = "cortex-m3"
    QEMU_MEMORY = "16M"

    def __init__(self, kernel_path: str, timeout: int = 30, verbose: bool = False):
        self.kernel_path = kernel_path
        self.timeout = timeout
        self.verbose = verbose
        self.output_lines: list = []

    def _build_qemu_command(self) -> list:
        """Build QEMU command line."""
        return [
            self.QEMU_CMD,
            "-machine", self.QEMU_MACHINE,
            "-cpu", self.QEMU_CPU,
            "-m", self.QEMU_MEMORY,
            "-nographic",
            "-no-reboot",
            "-serial", "mon:stdio",
            "-kernel", self.kernel_path,
        ]

    def run(self) -> tuple[str, int]:
        """Run QEMU and capture output.

        Returns:
            Tuple of (output_text, return_code)
        """
        cmd = self._build_qemu_command()

        if self.verbose:
            print(f"{Colors.CYAN}Running:{Colors.RESET} {' '.join(cmd)}")
            print()

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.PIPE,
                text=True,
            )

            output_lines = []
            start_time = time.time()
            test_complete = False

            while True:
                # Check timeout
                elapsed = time.time() - start_time
                if elapsed > self.timeout:
                    process.kill()
                    output_lines.append("\n[ERROR] Test timed out")
                    break

                # Try to read a line (with small timeout)
                try:
                    line = process.stdout.readline()
                    if not line:
                        # Process ended
                        break

                    output_lines.append(line)

                    # Check for test completion markers
                    stripped = line.strip()
                    if "[SUMMARY]" in stripped:
                        test_complete = True
                    elif "All tests passed" in stripped or "Some tests failed" in stripped:
                        test_complete = True
                    elif stripped == "=== Test Results ===" or "Test Results" in stripped:
                        # Wait a bit for summary
                        pass

                    # If tests are complete, give a short grace period then exit
                    if test_complete:
                        # Read any remaining output briefly
                        try:
                            remaining, _ = process.communicate(timeout=1.0)
                            if remaining:
                                output_lines.append(remaining)
                        except subprocess.TimeoutExpired:
                            pass
                        process.kill()
                        break

                except Exception:
                    break

            # Clean up process
            try:
                process.kill()
                process.wait(timeout=1.0)
            except Exception:
                pass

            output = ''.join(output_lines)
            return output, 0

        except FileNotFoundError:
            return f"Error: QEMU not found: {self.QEMU_CMD}", 2
        except subprocess.SubprocessError as e:
            return f"Error running QEMU: {e}", 2
        except Exception as e:
            return f"Unexpected error: {e}", 2


class TestDiscovery:
    """Discover test files in the tests directory."""

    def __init__(self, tests_dir: str):
        self.tests_dir = Path(tests_dir)

    def discover(self, pattern: str = "test_*.py") -> list[Path]:
        """Discover test files matching pattern.

        Args:
            pattern: Glob pattern for test files

        Returns:
            List of test file paths
        """
        test_files = []

        # Search for test files
        for test_file in sorted(self.tests_dir.glob(pattern)):
            # Skip framework and runner files
            if test_file.name in ("framework.py", "qemu_runner.py", "test_all.py",
                                  "test_compiler.py", "test_integration.py"):
                continue

            # Skip files that start with shebang (host Python scripts)
            try:
                with open(test_file, 'r') as f:
                    first_line = f.readline().strip()
                    if first_line.startswith("#!/"):
                        continue
            except Exception:
                continue

            test_files.append(test_file)

        return test_files

    def filter_by_pattern(self, files: list[Path], pattern: str) -> list[Path]:
        """Filter test files by name pattern.

        Args:
            files: List of test file paths
            pattern: Pattern to match (e.g., "timer" matches "test_timer.py")

        Returns:
            Filtered list of test files
        """
        if not pattern:
            return files

        filtered = []
        for f in files:
            name = f.stem  # e.g., "test_timer"
            if pattern in name or pattern in f.name:
                filtered.append(f)

        return filtered


def print_summary(suite: TestSuite):
    """Print test summary."""
    print()
    print(f"{Colors.BOLD}{'=' * 50}{Colors.RESET}")
    print(f"{Colors.BOLD}Test Summary{Colors.RESET}")
    print(f"{'=' * 50}")

    if suite.passed > 0:
        print(f"  {Colors.GREEN}Passed:{Colors.RESET}  {suite.passed}")
    if suite.failed > 0:
        print(f"  {Colors.RED}Failed:{Colors.RESET}  {suite.failed}")
    if suite.skipped > 0:
        print(f"  {Colors.YELLOW}Skipped:{Colors.RESET} {suite.skipped}")

    print(f"  Total:   {suite.total}")
    print(f"  Time:    {suite.duration_ms:.0f}ms")
    print()

    if suite.failed == 0:
        print(f"{Colors.GREEN}{Colors.BOLD}All tests passed!{Colors.RESET}")
    else:
        print(f"{Colors.RED}{Colors.BOLD}Some tests failed.{Colors.RESET}")

        # List failed tests
        print()
        print(f"{Colors.RED}Failed tests:{Colors.RESET}")
        for result in suite.results:
            if result.status == TestStatus.FAIL:
                msg = f": {result.message}" if result.message else ""
                print(f"  - {result.name}{msg}")

    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Pynux QEMU Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument(
        "test_pattern",
        nargs="?",
        default="",
        help="Pattern to filter tests (e.g., 'timer' for test_timer.py)"
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=30,
        help="Timeout in seconds (default: 30)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show all QEMU output"
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output"
    )
    parser.add_argument(
        "--kernel",
        default="build/pynux.elf",
        help="Path to kernel ELF file (default: build/pynux.elf)"
    )
    parser.add_argument(
        "--list", "-l",
        action="store_true",
        dest="list_tests",
        help="List available tests without running"
    )

    args = parser.parse_args()

    # Handle colors
    if args.no_color or not sys.stdout.isatty():
        Colors.disable()

    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Check kernel exists
    kernel_path = project_root / args.kernel
    if not kernel_path.exists():
        print(f"{Colors.RED}Error:{Colors.RESET} Kernel not found: {kernel_path}")
        print("Run './build.sh' first to build the kernel.")
        return 2

    # Discover tests
    discovery = TestDiscovery(script_dir)
    test_files = discovery.discover()
    test_files = discovery.filter_by_pattern(test_files, args.test_pattern)

    if args.list_tests:
        print(f"{Colors.BOLD}Available tests:{Colors.RESET}")
        for tf in test_files:
            print(f"  - {tf.name}")
        return 0

    if not test_files:
        if args.test_pattern:
            print(f"{Colors.YELLOW}Warning:{Colors.RESET} No tests matching '{args.test_pattern}'")
        else:
            print(f"{Colors.YELLOW}Warning:{Colors.RESET} No test files found")
        return 0

    # Print header
    print()
    print(f"{Colors.BOLD}Pynux QEMU Test Runner{Colors.RESET}")
    print(f"{'=' * 50}")
    print(f"  Kernel:  {kernel_path}")
    print(f"  Timeout: {args.timeout}s")
    print(f"  Tests:   {len(test_files)} file(s)")
    print(f"{'=' * 50}")
    print()

    # Run QEMU with tests
    runner = QEMURunner(
        kernel_path=str(kernel_path),
        timeout=args.timeout,
        verbose=args.verbose
    )

    print(f"{Colors.CYAN}Running tests in QEMU...{Colors.RESET}")
    print()

    output, return_code = runner.run()

    if return_code != 0:
        print(f"{Colors.RED}Error:{Colors.RESET} QEMU execution failed")
        print(output)
        return 2

    # Parse output
    parser_obj = TestOutputParser(verbose=args.verbose)
    suite = parser_obj.parse_output(output)

    # Print summary
    print_summary(suite)

    # Return appropriate exit code
    if suite.failed > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
