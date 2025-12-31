#!/usr/bin/env python3
"""
Compiler Unit Tests

Tests for lexer, parser, and codegen components.
"""

import sys
import os

# Change to project root directory for imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(project_root)
sys.path.insert(0, project_root)

from compiler.lexer import tokenize, TokenType
from compiler.parser import parse, parse_with_errors, ParseError
from compiler.ast_nodes import *
from compiler.codegen_arm import ARMCodeGen


def test_lexer_basic():
    """Test basic token recognition."""
    tokens = tokenize("def foo() -> int32:")
    types = [t.type for t in tokens]
    assert TokenType.DEF in types
    assert TokenType.IDENT in types
    assert TokenType.ARROW in types
    print("PASS: test_lexer_basic")


def test_lexer_numbers():
    """Test number tokenization."""
    tokens = tokenize("42 100")
    numbers = [t for t in tokens if t.type == TokenType.NUMBER]
    assert len(numbers) == 2
    assert numbers[0].value == 42
    print("PASS: test_lexer_numbers")


def test_lexer_strings():
    """Test string literal tokenization."""
    tokens = tokenize('"hello"')
    strings = [t for t in tokens if t.type == TokenType.STRING]
    assert len(strings) == 1
    assert strings[0].value == "hello"
    print("PASS: test_lexer_strings")


def test_parser_function():
    """Test function parsing."""
    code = """
def add(a: int32, b: int32) -> int32:
    return a + b
"""
    program = parse(code)
    assert len(program.declarations) == 1
    func = program.declarations[0]
    assert isinstance(func, FunctionDef)
    assert func.name == "add"
    print("PASS: test_parser_function")


def test_parser_import():
    """Test import statement parsing."""
    code = "from lib.io import print_str"
    program = parse(code)
    assert len(program.imports) == 1
    assert program.imports[0].module == "lib.io"
    print("PASS: test_parser_import")


def test_parser_class():
    """Test class parsing."""
    code = """
class Point:
    x: int32
    y: int32
"""
    program = parse(code)
    assert len(program.declarations) == 1
    cls = program.declarations[0]
    assert isinstance(cls, ClassDef)
    assert cls.name == "Point"
    print("PASS: test_parser_class")


def test_parser_error_recovery():
    """Test parser error recovery."""
    code = """
def good() -> int32:
    return 1

invalid syntax here

def good2() -> int32:
    return 2
"""
    program, errors = parse_with_errors(code)
    assert len(errors) >= 1
    print(f"PASS: test_parser_error_recovery ({len(errors)} error(s))")


def test_codegen_simple():
    """Test simple function codegen."""
    code = """
def answer() -> int32:
    return 42
"""
    program = parse(code)
    codegen = ARMCodeGen()
    asm = codegen.gen_program(program)
    assert "answer:" in asm
    print("PASS: test_codegen_simple")


def test_codegen_arithmetic():
    """Test arithmetic expression codegen."""
    code = """
def calc(a: int32, b: int32) -> int32:
    return a + b
"""
    program = parse(code)
    codegen = ARMCodeGen()
    asm = codegen.gen_program(program)
    assert "calc:" in asm
    assert "add" in asm.lower()
    print("PASS: test_codegen_arithmetic")


def run_all_tests():
    """Run all compiler unit tests."""
    tests = [
        test_lexer_basic,
        test_lexer_numbers,
        test_lexer_strings,
        test_parser_function,
        test_parser_import,
        test_parser_class,
        test_parser_error_recovery,
        test_codegen_simple,
        test_codegen_arithmetic,
    ]

    passed = 0
    failed = 0

    print("=" * 50)
    print("Pynux Compiler Unit Tests")
    print("=" * 50)

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAIL: {test.__name__}: {e}")
            failed += 1

    print()
    print("=" * 50)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 50)

    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
