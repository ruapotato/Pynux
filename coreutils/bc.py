# bc - basic calculator
# Simple expression evaluator

from lib.io import print_str, print_int, print_newline, uart_putc, uart_getc
from lib.string import isdigit, isspace

# Simple recursive descent parser for expressions
# Supports: + - * / () and integers

expr_input: Ptr[char]
expr_pos: int32 = 0

def expr_peek() -> char:
    return expr_input[expr_pos]

def expr_next() -> char:
    c: char = expr_input[expr_pos]
    expr_pos = expr_pos + 1
    return c

def expr_skip_space():
    while isspace(expr_peek()):
        expr_next()

def parse_number() -> int32:
    expr_skip_space()
    result: int32 = 0
    neg: bool = False

    if expr_peek() == '-':
        neg = True
        expr_next()

    while isdigit(expr_peek()):
        result = result * 10 + (cast[int32](expr_next()) - cast[int32]('0'))

    if neg:
        return -result
    return result

def parse_factor() -> int32:
    expr_skip_space()
    if expr_peek() == '(':
        expr_next()  # consume '('
        result: int32 = parse_expr()
        expr_skip_space()
        if expr_peek() == ')':
            expr_next()  # consume ')'
        return result
    return parse_number()

def parse_term() -> int32:
    left: int32 = parse_factor()
    expr_skip_space()

    while expr_peek() == '*' or expr_peek() == '/':
        op: char = expr_next()
        right: int32 = parse_factor()
        if op == '*':
            left = left * right
        else:
            if right != 0:
                left = left / right
        expr_skip_space()

    return left

def parse_expr() -> int32:
    left: int32 = parse_term()
    expr_skip_space()

    while expr_peek() == '+' or expr_peek() == '-':
        op: char = expr_next()
        right: int32 = parse_term()
        if op == '+':
            left = left + right
        else:
            left = left - right
        expr_skip_space()

    return left

def evaluate(input: Ptr[char]) -> int32:
    global expr_input, expr_pos
    expr_input = input
    expr_pos = 0
    return parse_expr()

def bc_repl():
    line: Array[256, char]

    print_str("bc - basic calculator\n")
    print_str("Enter expressions, 'quit' to exit\n")

    while True:
        print_str("> ")
        pos: int32 = 0

        while True:
            c: char = uart_getc()
            if c == '\r' or c == '\n':
                line[pos] = '\0'
                print_newline()
                break
            if c == '\x04':  # Ctrl+D
                return
            if pos < 255:
                line[pos] = c
                pos = pos + 1
                uart_putc(c)

        # Check for quit
        if line[0] == 'q':
            break

        if pos > 0:
            result: int32 = evaluate(&line[0])
            print_int(result)
            print_newline()

def main() -> int32:
    bc_repl()
    return 0
