"""
Pynux ARM Thumb-2 Code Generator

Generates ARM assembly for Cortex-M (Thumb-2 instruction set).
Target: QEMU mps2-an385 (Cortex-M3)

AAPCS calling convention:
- r0-r3: arguments (first 4) and return value (r0)
- r4-r11: callee-saved
- r12 (ip): scratch
- r13 (sp): stack pointer
- r14 (lr): link register
- r15 (pc): program counter

VFP (soft-float for Cortex-M3):
- Uses software floating point calls (__aeabi_fadd, etc.)
"""

from dataclasses import dataclass, field
from typing import Optional

from .ast_nodes import *


@dataclass
class LocalVar:
    """A local variable on the stack."""
    name: str
    offset: int  # Offset from frame pointer (negative)
    size: int = 4  # Size in bytes
    var_type: Optional[Type] = None


@dataclass
class StructInfo:
    """Information about a struct/class."""
    name: str
    fields: list[tuple[str, Type, int]]  # (name, type, offset)
    total_size: int


@dataclass
class LoopContext:
    """Track loop labels for break/continue."""
    start_label: str
    end_label: str
    continue_label: str  # Usually same as start, but could be different


@dataclass
class FunctionContext:
    """Context for generating a function."""
    name: str
    locals: dict[str, LocalVar] = field(default_factory=dict)
    globals: set[str] = field(default_factory=set)
    stack_size: int = 0
    label_counter: int = 0
    loop_stack: list[LoopContext] = field(default_factory=list)
    defer_stack: list[Stmt] = field(default_factory=list)

    def alloc_local(self, name: str, size: int = 4, var_type: Type = None) -> LocalVar:
        """Allocate a local variable on the stack."""
        self.stack_size += size
        # Align to 4 bytes
        self.stack_size = (self.stack_size + 3) & ~3
        var = LocalVar(name, -self.stack_size, size, var_type)
        self.locals[name] = var
        return var

    def mark_global(self, name: str) -> None:
        """Mark a variable as global (not local)."""
        self.globals.add(name)

    def is_global(self, name: str) -> bool:
        """Check if a variable is marked as global."""
        return name in self.globals

    def new_label(self, prefix: str = "L") -> str:
        """Generate a unique label."""
        self.label_counter += 1
        return f".{prefix}_{self.name}_{self.label_counter}"

    def push_loop(self, start: str, end: str, cont: str = None) -> None:
        """Push a loop context for break/continue."""
        self.loop_stack.append(LoopContext(start, end, cont or start))

    def pop_loop(self) -> None:
        """Pop a loop context."""
        self.loop_stack.pop()

    def current_loop(self) -> Optional[LoopContext]:
        """Get current loop context."""
        return self.loop_stack[-1] if self.loop_stack else None


class CodeGenError(Exception):
    """Error during code generation."""
    pass


class ARMCodeGen:
    """Generates ARM Thumb-2 assembly."""

    def __init__(self):
        self.output: list[str] = []
        self.data_section: list[str] = []
        self.bss_section: list[str] = []
        self.string_literals: dict[str, str] = {}
        self.string_counter = 0
        self.ctx: Optional[FunctionContext] = None
        self.extern_funcs: set[str] = set()
        self.global_arrays: set[str] = set()  # Track global array names
        self.array_element_sizes: dict[str, int] = {}  # Array name -> element size
        self.structs: dict[str, StructInfo] = {}  # Struct/class definitions
        self.global_var_types: dict[str, Type] = {}  # Global variable types

    def emit(self, line: str) -> None:
        """Emit a line of assembly."""
        self.output.append(line)

    def emit_data(self, line: str) -> None:
        """Emit a line to the data section."""
        self.data_section.append(line)

    def emit_bss(self, line: str) -> None:
        """Emit a line to the BSS section."""
        self.bss_section.append(line)

    def add_string(self, s: str) -> str:
        """Add a string literal and return its label."""
        if s in self.string_literals:
            return self.string_literals[s]
        self.string_counter += 1
        label = f".str_{self.string_counter}"
        self.string_literals[s] = label
        return label

    def get_type_size(self, t: Type | None) -> int:
        """Get size of a type in bytes."""
        if t is None:
            return 4

        # Handle array types: Array[size, element_type]
        if isinstance(t, ArrayType):
            return t.size * self.get_type_size(t.element_type)

        # Handle pointer types
        if isinstance(t, PointerType):
            return 4  # Pointers are always 4 bytes on ARM

        # Handle tuple types
        if isinstance(t, TupleType):
            return sum(self.get_type_size(et) for et in t.element_types)

        # Handle struct types
        name = t.name if isinstance(t, Type) else str(t)
        if name in self.structs:
            return self.structs[name].total_size

        sizes = {
            "int8": 1, "uint8": 1, "char": 1, "bool": 1,
            "int16": 2, "uint16": 2,
            "int32": 4, "uint32": 4, "int": 4,
            "int64": 8, "uint64": 8,
            "float32": 4, "float64": 8, "float": 4,
        }
        return sizes.get(name, 4)  # Default to 4 bytes (pointer size)

    def is_float_type(self, t: Type | None) -> bool:
        """Check if type is floating point."""
        if t is None:
            return False
        name = t.name if isinstance(t, Type) else str(t)
        return name in ("float32", "float64", "float")

    # -------------------------------------------------------------------------
    # Expression generation
    # -------------------------------------------------------------------------

    def gen_expr(self, expr: Expr) -> None:
        """Generate code for an expression, result in r0."""
        match expr:
            case IntLiteral(value=v):
                if -256 <= v <= 255:
                    self.emit(f"    movs r0, #{v}")
                elif v >= 0 and v <= 65535:
                    self.emit(f"    movw r0, #{v}")
                else:
                    self.emit(f"    ldr r0, ={v}")

            case FloatLiteral(value=v):
                # Store float as 32-bit IEEE 754 integer representation
                import struct
                bits = struct.unpack('<I', struct.pack('<f', v))[0]
                self.emit(f"    ldr r0, ={bits}  @ float {v}")

            case BoolLiteral(value=v):
                self.emit(f"    movs r0, #{1 if v else 0}")

            case CharLiteral(value=v):
                self.emit(f"    movs r0, #{ord(v)}")

            case StringLiteral(value=v):
                label = self.add_string(v)
                self.emit(f"    ldr r0, ={label}")

            case FStringLiteral(value=v):
                # F-string: parse and emit parts
                self.gen_fstring(v)

            case NoneLiteral():
                self.emit("    movs r0, #0")

            case Identifier(name=name):
                if name in self.ctx.locals:
                    var = self.ctx.locals[name]
                    self.emit(f"    ldr r0, [r7, #{var.offset}]")
                elif name in self.global_arrays:
                    # Global array - just load address, don't dereference
                    self.emit(f"    ldr r0, ={name}")
                else:
                    # Global scalar variable
                    self.emit(f"    ldr r0, ={name}")
                    self.emit(f"    ldr r0, [r0]")

            case BinaryExpr(op=op, left=left, right=right):
                self.gen_binary(op, left, right)

            case UnaryExpr(op=op, operand=operand):
                self.gen_unary(op, operand)

            case CallExpr(func=func, args=args):
                self.gen_call(func, args)

            case MethodCallExpr(obj=obj, method=method, args=args):
                # Handle string methods specially
                string_methods = {
                    'upper': '__pynux_str_upper',
                    'lower': '__pynux_str_lower',
                    'strip': '__pynux_str_strip',
                    'lstrip': '__pynux_str_lstrip',
                    'rstrip': '__pynux_str_rstrip',
                    'startswith': '__pynux_str_startswith',
                    'endswith': '__pynux_str_endswith',
                    'find': '__pynux_str_find',
                    'replace': '__pynux_str_replace',
                    'split': '__pynux_str_split',
                    'join': '__pynux_str_join',
                    'isdigit': '__pynux_str_isdigit',
                    'isalpha': '__pynux_str_isalpha',
                }
                if method in string_methods:
                    # Call runtime function with obj as first arg
                    all_args = [obj] + args
                    self.gen_call(Identifier(string_methods[method]), all_args)
                else:
                    # Generic method call - treat as function with obj as first arg
                    all_args = [obj] + args
                    self.gen_call(Identifier(method), all_args)

            case IndexExpr(obj=obj, index=index):
                # Array indexing: obj[index]
                # Support negative indexing like Python (arr[-1] = last element)
                self.gen_expr(index)
                self.emit("    push {r0}")  # Save index
                self.gen_expr(obj)
                self.emit("    pop {r1}")   # r1 = index, r0 = array base

                # Determine element size and array length
                elem_size = 4  # Default to word
                array_len = None
                if isinstance(obj, Identifier):
                    elem_size = self.array_element_sizes.get(obj.name, 4)
                    # Get array length if known
                    var_type = self.global_var_types.get(obj.name)
                    if var_type is None and obj.name in self.ctx.locals:
                        var_type = self.ctx.locals[obj.name].var_type
                    if isinstance(var_type, ArrayType):
                        array_len = var_type.size

                # Handle negative indices: if index < 0, add length
                neg_label = self.ctx.new_label("negidx")
                done_label = self.ctx.new_label("idxdone")
                self.emit("    cmp r1, #0")
                self.emit(f"    bge {done_label}")
                # Negative index - add array length
                if array_len is not None:
                    self.emit(f"    add r1, r1, #{array_len}")
                else:
                    # For dynamic arrays/strings, call strlen
                    self.emit("    push {r0, r1}")
                    self.emit("    bl __pynux_strlen")
                    self.emit("    pop {r1}")  # Just pop the old r1
                    self.emit("    pop {r2}")  # Get array base back
                    self.emit("    add r1, r1, r0")  # index += length
                    self.emit("    mov r0, r2")  # Restore array base
                self.emit(f"{done_label}:")

                # Scale index by element size
                if elem_size == 4:
                    self.emit("    lsl r1, r1, #2")
                elif elem_size == 2:
                    self.emit("    lsl r1, r1, #1")
                # For elem_size == 1, no shift needed

                self.emit("    add r0, r0, r1")

                # Use appropriate load instruction
                if elem_size == 1:
                    self.emit("    ldrb r0, [r0]")
                elif elem_size == 2:
                    self.emit("    ldrh r0, [r0]")
                else:
                    self.emit("    ldr r0, [r0]")

            case SliceExpr(obj=obj, start=start, end=end, step=step):
                self.gen_slice(obj, start, end, step)

            case MemberExpr(obj=obj, member=member):
                self.gen_member_access(obj, member)

            case ListLiteral(elements=elements):
                self.gen_list_literal(elements)

            case DictLiteral(pairs=pairs):
                self.gen_dict_literal(pairs)

            case TupleLiteral(elements=elements):
                self.gen_tuple_literal(elements)

            case ListComprehension(element=element, var=var, iterable=iterable, condition=cond):
                self.gen_list_comprehension(element, var, iterable, cond)

            case ConditionalExpr(condition=cond, then_expr=then_e, else_expr=else_e):
                else_label = self.ctx.new_label("else")
                end_label = self.ctx.new_label("endif")
                self.gen_expr(cond)
                self.emit("    cmp r0, #0")
                self.emit(f"    beq {else_label}")
                self.gen_expr(then_e)
                self.emit(f"    b {end_label}")
                self.emit(f"{else_label}:")
                self.gen_expr(else_e)
                self.emit(f"{end_label}:")

            case LambdaExpr():
                raise CodeGenError("Lambda expressions not yet supported in ARM codegen")

            case SizeOfExpr(target_type=t):
                size = self.get_type_size(t)
                self.emit(f"    movs r0, #{size}")

            case CastExpr(target_type=t, expr=e):
                self.gen_expr(e)
                # Handle float<->int conversions
                # For now, just pass through (soft-float would need runtime calls)

            case AsmExpr(code=code):
                self.emit(f"    {code}")

            case _:
                raise CodeGenError(f"Unsupported expression: {type(expr).__name__}")

    def gen_fstring(self, fstr: str) -> None:
        """Generate code for f-string interpolation."""
        # Parse f-string and emit print calls for each part
        # Format: f"Hello {name}, you are {age} years old"
        # Results in: print "Hello ", print name, print ", you are ", print age, print " years old"

        # For now, we'll build a result on the heap or just print directly
        # Simple approach: just print each segment
        parts = []
        i = 0
        current = ""
        while i < len(fstr):
            if fstr[i] == '{' and i + 1 < len(fstr) and fstr[i+1] != '{':
                if current:
                    parts.append(('str', current))
                    current = ""
                # Find matching }
                j = i + 1
                while j < len(fstr) and fstr[j] != '}':
                    j += 1
                expr_str = fstr[i+1:j]
                parts.append(('expr', expr_str))
                i = j + 1
            elif fstr[i] == '{' and i + 1 < len(fstr) and fstr[i+1] == '{':
                current += '{'
                i += 2
            elif fstr[i] == '}' and i + 1 < len(fstr) and fstr[i+1] == '}':
                current += '}'
                i += 2
            else:
                current += fstr[i]
                i += 1
        if current:
            parts.append(('str', current))

        # For returning result, we'd need string concatenation
        # For now, emit a combined string label (simplified)
        combined = self.add_string(fstr)  # Simplified - just use raw string
        self.emit(f"    ldr r0, ={combined}")

    def gen_binary(self, op: BinOp, left: Expr, right: Expr) -> None:
        """Generate code for binary operation."""
        # Evaluate right first, push, then left
        self.gen_expr(right)
        self.emit("    push {r0}")
        self.gen_expr(left)
        self.emit("    pop {r1}")  # r0 = left, r1 = right

        match op:
            case BinOp.ADD:
                self.emit("    add r0, r0, r1")
            case BinOp.SUB:
                self.emit("    sub r0, r0, r1")
            case BinOp.MUL:
                self.emit("    mul r0, r0, r1")
            case BinOp.DIV | BinOp.IDIV:
                self.emit("    bl __aeabi_idiv")
            case BinOp.MOD:
                self.emit("    bl __aeabi_idivmod")
                self.emit("    mov r0, r1")  # Remainder in r1
            case BinOp.POW:
                # Power function - call runtime
                self.emit("    bl __pynux_pow")
            case BinOp.BIT_AND:
                self.emit("    and r0, r0, r1")
            case BinOp.BIT_OR:
                self.emit("    orr r0, r0, r1")
            case BinOp.BIT_XOR:
                self.emit("    eor r0, r0, r1")
            case BinOp.SHL:
                self.emit("    lsl r0, r0, r1")
            case BinOp.SHR:
                self.emit("    lsr r0, r0, r1")
            case BinOp.EQ:
                self.emit("    cmp r0, r1")
                self.emit("    ite eq")
                self.emit("    moveq r0, #1")
                self.emit("    movne r0, #0")
            case BinOp.NEQ:
                self.emit("    cmp r0, r1")
                self.emit("    ite ne")
                self.emit("    movne r0, #1")
                self.emit("    moveq r0, #0")
            case BinOp.LT:
                self.emit("    cmp r0, r1")
                self.emit("    ite lt")
                self.emit("    movlt r0, #1")
                self.emit("    movge r0, #0")
            case BinOp.LTE:
                self.emit("    cmp r0, r1")
                self.emit("    ite le")
                self.emit("    movle r0, #1")
                self.emit("    movgt r0, #0")
            case BinOp.GT:
                self.emit("    cmp r0, r1")
                self.emit("    ite gt")
                self.emit("    movgt r0, #1")
                self.emit("    movle r0, #0")
            case BinOp.GTE:
                self.emit("    cmp r0, r1")
                self.emit("    ite ge")
                self.emit("    movge r0, #1")
                self.emit("    movlt r0, #0")
            case BinOp.AND:
                # Logical AND using branches to avoid nested IT blocks
                label = self.ctx.new_label("and")
                self.emit("    cmp r0, #0")
                self.emit(f"    beq {label}_false")
                self.emit("    cmp r1, #0")
                self.emit(f"    beq {label}_false")
                self.emit("    movs r0, #1")
                self.emit(f"    b {label}_done")
                self.emit(f"{label}_false:")
                self.emit("    movs r0, #0")
                self.emit(f"{label}_done:")
            case BinOp.OR:
                # Logical OR using branches
                label = self.ctx.new_label("or")
                self.emit("    cmp r0, #0")
                self.emit(f"    bne {label}_true")
                self.emit("    cmp r1, #0")
                self.emit(f"    bne {label}_true")
                self.emit("    movs r0, #0")
                self.emit(f"    b {label}_done")
                self.emit(f"{label}_true:")
                self.emit("    movs r0, #1")
                self.emit(f"{label}_done:")
            case BinOp.IN:
                # 'in' operator - call runtime helper
                self.emit("    bl __pynux_in")
            case BinOp.NOT_IN:
                self.emit("    bl __pynux_in")
                self.emit("    eor r0, r0, #1")  # Invert result
            case BinOp.IS:
                # Identity comparison (pointer equality)
                self.emit("    cmp r0, r1")
                self.emit("    ite eq")
                self.emit("    moveq r0, #1")
                self.emit("    movne r0, #0")
            case BinOp.IS_NOT:
                self.emit("    cmp r0, r1")
                self.emit("    ite ne")
                self.emit("    movne r0, #1")
                self.emit("    moveq r0, #0")
            case _:
                raise CodeGenError(f"Unsupported binary op: {op}")

    def gen_unary(self, op: UnaryOp, operand: Expr) -> None:
        """Generate code for unary operation."""
        # Handle ADDR specially - don't evaluate operand first!
        if op == UnaryOp.ADDR:
            # Address-of - need lvalue handling
            if isinstance(operand, Identifier):
                if operand.name in self.ctx.locals:
                    var = self.ctx.locals[operand.name]
                    self.emit(f"    add r0, r7, #{var.offset}")
                else:
                    # Global variable - address is just the symbol
                    self.emit(f"    ldr r0, ={operand.name}")
            elif isinstance(operand, IndexExpr):
                # &arr[i] - array element address
                self.gen_expr(operand.index)

                # Determine element size
                elem_size = 4  # Default to word
                if isinstance(operand.obj, Identifier):
                    elem_size = self.array_element_sizes.get(operand.obj.name, 4)

                # Scale index by element size
                if elem_size == 4:
                    self.emit("    lsl r0, r0, #2")
                elif elem_size == 2:
                    self.emit("    lsl r0, r0, #1")
                # For elem_size == 1, no shift needed

                self.emit("    push {r0}")
                self.gen_expr(operand.obj)
                self.emit("    pop {r1}")
                self.emit("    add r0, r0, r1")
            elif isinstance(operand, MemberExpr):
                # &obj.field - address of struct field
                self.gen_member_addr(operand.obj, operand.member)
            else:
                raise CodeGenError(f"Cannot take address of non-lvalue: {type(operand).__name__}")
            return

        # For other unary ops, evaluate operand first
        self.gen_expr(operand)

        match op:
            case UnaryOp.NEG:
                self.emit("    rsb r0, r0, #0")  # r0 = 0 - r0
            case UnaryOp.NOT:
                self.emit("    cmp r0, #0")
                self.emit("    ite eq")
                self.emit("    moveq r0, #1")
                self.emit("    movne r0, #0")
            case UnaryOp.BIT_NOT:
                self.emit("    mvn r0, r0")
            case UnaryOp.DEREF:
                self.emit("    ldr r0, [r0]")
            case _:
                raise CodeGenError(f"Unsupported unary op: {op}")

    def gen_call(self, func: Expr, args: list[Expr]) -> None:
        """Generate function call."""
        # Get function name
        if isinstance(func, Identifier):
            func_name = func.name
        else:
            raise CodeGenError("Indirect function calls not yet supported")

        # Handle built-in functions specially
        if func_name == "print":
            self.gen_builtin_print(args)
            return
        elif func_name == "len":
            self.gen_builtin_len(args)
            return
        elif func_name == "abs":
            self.gen_builtin_abs(args)
            return
        elif func_name == "min":
            self.gen_builtin_min(args)
            return
        elif func_name == "max":
            self.gen_builtin_max(args)
            return
        elif func_name == "ord":
            self.gen_builtin_ord(args)
            return
        elif func_name == "chr":
            self.gen_builtin_chr(args)
            return
        elif func_name == "input":
            self.gen_builtin_input(args)
            return

        # Save caller-saved registers if needed
        if len(args) > 4:
            raise CodeGenError("More than 4 arguments not yet supported")

        # Push args in reverse order, then pop to r0-r3
        for arg in reversed(args):
            self.gen_expr(arg)
            self.emit("    push {r0}")

        for i in range(len(args)):
            self.emit(f"    pop {{r{i}}}")

        self.emit(f"    bl {func_name}")

    def gen_builtin_print(self, args: list[Expr]) -> None:
        """Generate print() built-in - auto-detects type and prints."""
        for i, arg in enumerate(args):
            if i > 0:
                # Print space separator between args
                self.emit("    movs r0, #' '")
                self.emit("    bl uart_putc")

            # Determine type and call appropriate print function
            if isinstance(arg, StringLiteral):
                label = self.add_string(arg.value)
                self.emit(f"    ldr r0, ={label}")
                self.emit("    bl print_str")
            elif isinstance(arg, IntLiteral):
                self.gen_expr(arg)
                self.emit("    bl print_int")
            elif isinstance(arg, BoolLiteral):
                if arg.value:
                    label = self.add_string("True")
                else:
                    label = self.add_string("False")
                self.emit(f"    ldr r0, ={label}")
                self.emit("    bl print_str")
            elif isinstance(arg, CharLiteral):
                self.emit(f"    movs r0, #{ord(arg.value)}")
                self.emit("    bl uart_putc")
            elif isinstance(arg, FStringLiteral):
                # F-string: parse and print each part
                self.gen_fstring_print(arg.value)
            else:
                # For other expressions, evaluate and print as int
                # In the future we could add type inference
                self.gen_expr(arg)
                self.emit("    bl print_int")

        # Print newline at end
        self.emit("    movs r0, #'\\n'")
        self.emit("    bl uart_putc")

    def gen_fstring_print(self, fstr: str) -> None:
        """Generate code for printing f-string interpolation."""
        i = 0
        while i < len(fstr):
            if fstr[i] == '{' and i + 1 < len(fstr) and fstr[i+1] != '{':
                # Find matching }
                j = i + 1
                while j < len(fstr) and fstr[j] != '}':
                    j += 1
                expr_str = fstr[i+1:j]
                # For now, parse and evaluate as identifier
                # This is simplified - full implementation would use parser
                if expr_str.isidentifier():
                    if expr_str in self.ctx.locals:
                        var = self.ctx.locals[expr_str]
                        self.emit(f"    ldr r0, [r7, #{var.offset}]")
                    else:
                        self.emit(f"    ldr r0, ={expr_str}")
                        self.emit("    ldr r0, [r0]")
                    self.emit("    bl print_int")
                i = j + 1
            elif fstr[i] == '{' and i + 1 < len(fstr) and fstr[i+1] == '{':
                self.emit("    movs r0, #'{'")
                self.emit("    bl uart_putc")
                i += 2
            elif fstr[i] == '}' and i + 1 < len(fstr) and fstr[i+1] == '}':
                self.emit("    movs r0, #'}'")
                self.emit("    bl uart_putc")
                i += 2
            else:
                # Collect consecutive literal characters
                start = i
                while i < len(fstr) and fstr[i] != '{' and fstr[i] != '}':
                    i += 1
                if start < i:
                    substr = fstr[start:i]
                    label = self.add_string(substr)
                    self.emit(f"    ldr r0, ={label}")
                    self.emit("    bl print_str")

    def gen_builtin_len(self, args: list[Expr]) -> None:
        """Generate len() built-in - returns length of string or array."""
        if len(args) != 1:
            raise CodeGenError("len() takes exactly 1 argument")

        arg = args[0]

        # For string literals, we know the length at compile time
        if isinstance(arg, StringLiteral):
            self.emit(f"    movs r0, #{len(arg.value)}")
            return

        # For identifiers, check if it's an array or string
        if isinstance(arg, Identifier):
            if arg.name in self.global_arrays:
                # Get array size from type
                var_type = self.global_var_types.get(arg.name)
                if isinstance(var_type, ArrayType):
                    self.emit(f"    movs r0, #{var_type.size}")
                    return

        # For runtime strings, call strlen
        self.gen_expr(arg)
        self.emit("    bl __pynux_strlen")

    def gen_builtin_abs(self, args: list[Expr]) -> None:
        """Generate abs() built-in."""
        if len(args) != 1:
            raise CodeGenError("abs() takes exactly 1 argument")
        self.gen_expr(args[0])
        # if negative, negate
        self.emit("    cmp r0, #0")
        self.emit("    it lt")
        self.emit("    rsblt r0, r0, #0")

    def gen_builtin_min(self, args: list[Expr]) -> None:
        """Generate min() built-in."""
        if len(args) < 2:
            raise CodeGenError("min() takes at least 2 arguments")
        # Start with first arg
        self.gen_expr(args[0])
        for arg in args[1:]:
            self.emit("    push {r0}")
            self.gen_expr(arg)
            self.emit("    pop {r1}")
            # r1 = current min, r0 = new value
            self.emit("    cmp r0, r1")
            self.emit("    it ge")
            self.emit("    movge r0, r1")

    def gen_builtin_max(self, args: list[Expr]) -> None:
        """Generate max() built-in."""
        if len(args) < 2:
            raise CodeGenError("max() takes at least 2 arguments")
        # Start with first arg
        self.gen_expr(args[0])
        for arg in args[1:]:
            self.emit("    push {r0}")
            self.gen_expr(arg)
            self.emit("    pop {r1}")
            # r1 = current max, r0 = new value
            self.emit("    cmp r0, r1")
            self.emit("    it le")
            self.emit("    movle r0, r1")

    def gen_builtin_ord(self, args: list[Expr]) -> None:
        """Generate ord() built-in - get ASCII value of character."""
        if len(args) != 1:
            raise CodeGenError("ord() takes exactly 1 argument")
        arg = args[0]
        if isinstance(arg, CharLiteral):
            self.emit(f"    movs r0, #{ord(arg.value)}")
        elif isinstance(arg, StringLiteral) and len(arg.value) == 1:
            self.emit(f"    movs r0, #{ord(arg.value[0])}")
        else:
            # Get first character of string/expression
            self.gen_expr(arg)
            self.emit("    ldrb r0, [r0]")

    def gen_builtin_chr(self, args: list[Expr]) -> None:
        """Generate chr() built-in - convert int to character."""
        if len(args) != 1:
            raise CodeGenError("chr() takes exactly 1 argument")
        self.gen_expr(args[0])
        # Result is already in r0 as the character value

    def gen_builtin_input(self, args: list[Expr]) -> None:
        """Generate input() built-in - read line from UART."""
        # Print prompt if provided
        if args:
            self.gen_expr(args[0])
            self.emit("    bl print_str")

        # Allocate buffer on heap (128 bytes)
        self.emit("    movs r0, #128")
        self.emit("    bl malloc")
        self.emit("    push {r0}")  # Save buffer address

        # Read line into buffer
        self.emit("    bl __pynux_read_line")

        self.emit("    pop {r0}")  # Return buffer address

    def gen_member_access(self, obj: Expr, member: str) -> None:
        """Generate struct field access."""
        # Get object address
        if isinstance(obj, Identifier):
            if obj.name in self.ctx.locals:
                var = self.ctx.locals[obj.name]
                self.emit(f"    add r0, r7, #{var.offset}")
                var_type = var.var_type
            else:
                self.emit(f"    ldr r0, ={obj.name}")
                var_type = self.global_var_types.get(obj.name)
        else:
            self.gen_expr(obj)
            var_type = None

        # Get struct info and field offset
        if var_type and hasattr(var_type, 'name') and var_type.name in self.structs:
            struct = self.structs[var_type.name]
            for fname, ftype, offset in struct.fields:
                if fname == member:
                    if offset != 0:
                        self.emit(f"    add r0, r0, #{offset}")
                    size = self.get_type_size(ftype)
                    if size == 1:
                        self.emit("    ldrb r0, [r0]")
                    elif size == 2:
                        self.emit("    ldrh r0, [r0]")
                    else:
                        self.emit("    ldr r0, [r0]")
                    return

        # Fallback - just emit a TODO for now
        self.emit(f"    @ access member {member}")
        self.emit("    ldr r0, [r0]")

    def gen_member_addr(self, obj: Expr, member: str) -> None:
        """Generate address of struct field."""
        if isinstance(obj, Identifier):
            if obj.name in self.ctx.locals:
                var = self.ctx.locals[obj.name]
                self.emit(f"    add r0, r7, #{var.offset}")
                var_type = var.var_type
            else:
                self.emit(f"    ldr r0, ={obj.name}")
                var_type = self.global_var_types.get(obj.name)
        else:
            self.gen_expr(obj)
            var_type = None

        # Add field offset
        if var_type and hasattr(var_type, 'name') and var_type.name in self.structs:
            struct = self.structs[var_type.name]
            for fname, ftype, offset in struct.fields:
                if fname == member:
                    if offset != 0:
                        self.emit(f"    add r0, r0, #{offset}")
                    return

    def gen_slice(self, obj: Expr, start: Optional[Expr], end: Optional[Expr],
                  step: Optional[Expr]) -> None:
        """Generate array/string slice."""
        # Slicing creates a new view/copy - needs runtime support
        # For now, emit a runtime call
        self.gen_expr(obj)
        self.emit("    push {r0}")

        if start:
            self.gen_expr(start)
        else:
            self.emit("    movs r0, #0")
        self.emit("    push {r0}")

        if end:
            self.gen_expr(end)
        else:
            self.emit("    movs r0, #-1")  # -1 means "to end"
        self.emit("    push {r0}")

        if step:
            self.gen_expr(step)
        else:
            self.emit("    movs r0, #1")

        self.emit("    pop {r2}")  # end
        self.emit("    pop {r1}")  # start
        self.emit("    pop {r0}")  # obj
        self.emit("    push {r3}")  # save step in r3 temporarily
        self.emit("    mov r3, r0")  # step is already in r0
        self.emit("    pop {r3}")
        self.emit("    bl __pynux_slice")

    def gen_list_literal(self, elements: list[Expr]) -> None:
        """Generate list literal [a, b, c]."""
        # Allocate space for list header + elements
        n = len(elements)
        self.emit(f"    movs r0, #{(n + 2) * 4}")  # header + length + elements
        self.emit("    bl malloc")
        self.emit("    push {r0}")  # Save list pointer

        # Store length
        self.emit(f"    movs r1, #{n}")
        self.emit("    str r1, [r0]")

        # Store capacity
        self.emit(f"    movs r1, #{n}")
        self.emit("    str r1, [r0, #4]")

        # Store elements
        for i, elem in enumerate(elements):
            self.emit("    ldr r0, [sp]")  # Get list pointer
            self.emit(f"    add r0, r0, #{(i + 2) * 4}")
            self.emit("    push {r0}")
            self.gen_expr(elem)
            self.emit("    pop {r1}")
            self.emit("    str r0, [r1]")

        self.emit("    pop {r0}")  # Return list pointer

    def gen_dict_literal(self, pairs: list[tuple[Expr, Expr]]) -> None:
        """Generate dict literal {k: v, ...}."""
        # Simple implementation: allocate array of key-value pairs
        n = len(pairs)
        self.emit(f"    movs r0, #{(n * 2 + 1) * 4}")  # count + pairs
        self.emit("    bl malloc")
        self.emit("    push {r0}")

        # Store count
        self.emit(f"    movs r1, #{n}")
        self.emit("    str r1, [r0]")

        # Store pairs
        for i, (key, val) in enumerate(pairs):
            # Key
            self.emit("    ldr r0, [sp]")
            self.emit(f"    add r0, r0, #{(i * 2 + 1) * 4}")
            self.emit("    push {r0}")
            self.gen_expr(key)
            self.emit("    pop {r1}")
            self.emit("    str r0, [r1]")

            # Value
            self.emit("    ldr r0, [sp]")
            self.emit(f"    add r0, r0, #{(i * 2 + 2) * 4}")
            self.emit("    push {r0}")
            self.gen_expr(val)
            self.emit("    pop {r1}")
            self.emit("    str r0, [r1]")

        self.emit("    pop {r0}")

    def gen_tuple_literal(self, elements: list[Expr]) -> None:
        """Generate tuple literal (a, b, c)."""
        # Tuples are just contiguous memory with elements
        n = len(elements)
        self.emit(f"    movs r0, #{n * 4}")
        self.emit("    bl malloc")
        self.emit("    push {r0}")

        for i, elem in enumerate(elements):
            self.emit("    ldr r0, [sp]")
            self.emit(f"    add r0, r0, #{i * 4}")
            self.emit("    push {r0}")
            self.gen_expr(elem)
            self.emit("    pop {r1}")
            self.emit("    str r0, [r1]")

        self.emit("    pop {r0}")

    def gen_list_comprehension(self, element: Expr, var: str, iterable: Expr, condition: Optional[Expr]) -> None:
        """Generate list comprehension: [expr for var in iterable if cond]."""
        # This is complex - we need to:
        # 1. Allocate initial list on heap
        # 2. Iterate over iterable
        # 3. For each item, optionally check condition
        # 4. Evaluate element expression and append to list

        # For simplicity, support range() iterables for now
        if not isinstance(iterable, CallExpr) or not isinstance(iterable.func, Identifier):
            raise CodeGenError("List comprehensions only support range() for now")

        if iterable.func.name != "range":
            raise CodeGenError("List comprehensions only support range() for now")

        # Parse range args
        range_args = iterable.args
        if len(range_args) == 1:
            start_val, end_val, step_val = 0, None, 1
            end_expr = range_args[0]
        elif len(range_args) == 2:
            start_val, step_val = None, 1
            start_expr, end_expr = range_args[0], range_args[1]
        else:
            start_expr, end_expr, step_expr = range_args[0], range_args[1], range_args[2]
            start_val, step_val = None, None

        # Allocate list with estimated size (we'll use max 256 elements)
        self.emit("    movs r0, #264")  # 8 bytes header + 256 elements max
        self.emit("    bl malloc")
        self.emit("    push {r0}")  # Save list pointer

        # Initialize length = 0
        self.emit("    movs r1, #0")
        self.emit("    str r1, [r0]")

        # Allocate loop variable
        loop_var = self.ctx.alloc_local(var)

        # Get range parameters
        if len(range_args) == 1:
            self.emit("    movs r0, #0")
            self.emit(f"    str r0, [r7, #{loop_var.offset}]")
        else:
            self.gen_expr(range_args[0])
            self.emit(f"    str r0, [r7, #{loop_var.offset}]")

        end_var = self.ctx.alloc_local(f"_end_{var}")
        if len(range_args) >= 1:
            self.gen_expr(end_expr)
            self.emit(f"    str r0, [r7, #{end_var.offset}]")

        # Loop
        start_label = self.ctx.new_label("listcomp")
        end_label = self.ctx.new_label("endlistcomp")
        continue_label = self.ctx.new_label("listcompcont")

        self.emit(f"{start_label}:")
        self.emit(f"    ldr r0, [r7, #{loop_var.offset}]")
        self.emit(f"    ldr r1, [r7, #{end_var.offset}]")
        self.emit("    cmp r0, r1")
        self.emit(f"    bge {end_label}")

        # Check condition if present
        if condition:
            self.gen_expr(condition)
            self.emit("    cmp r0, #0")
            self.emit(f"    beq {continue_label}")

        # Evaluate element expression
        self.gen_expr(element)
        self.emit("    push {r0}")  # Save element value

        # Append to list: list[len] = value, len++
        self.emit("    ldr r0, [sp, #4]")  # Get list pointer (below saved element)
        self.emit("    ldr r1, [r0]")       # Get current length
        self.emit("    add r2, r0, #8")     # Data starts at offset 8
        self.emit("    lsl r3, r1, #2")     # Offset = len * 4
        self.emit("    add r2, r2, r3")     # Data address
        self.emit("    pop {r3}")           # Get saved element
        self.emit("    str r3, [r2]")       # Store element
        self.emit("    add r1, r1, #1")     # len++
        self.emit("    str r1, [r0]")       # Store new length

        self.emit(f"{continue_label}:")
        # Increment loop variable
        self.emit(f"    ldr r0, [r7, #{loop_var.offset}]")
        self.emit("    add r0, r0, #1")
        self.emit(f"    str r0, [r7, #{loop_var.offset}]")
        self.emit(f"    b {start_label}")

        self.emit(f"{end_label}:")
        self.emit("    pop {r0}")  # Return list pointer

    # -------------------------------------------------------------------------
    # Statement generation
    # -------------------------------------------------------------------------

    def gen_stmt(self, stmt: Stmt) -> None:
        """Generate code for a statement."""
        match stmt:
            case ExprStmt(expr=expr):
                self.gen_expr(expr)

            case VarDecl(name=name, var_type=var_type, value=value):
                size = self.get_type_size(var_type)
                var = self.ctx.alloc_local(name, size, var_type)

                # Track array element sizes for local arrays
                if isinstance(var_type, ArrayType):
                    elem_size = self.get_type_size(var_type.element_type)
                    self.array_element_sizes[name] = elem_size

                if value is not None:
                    self.gen_expr(value)
                    self.emit(f"    str r0, [r7, #{var.offset}]")

            case Assignment(target=target, value=value, op=op):
                self.gen_assignment(target, value, op)

            case ReturnStmt(value=value):
                # Execute deferred statements in reverse order
                for deferred in reversed(self.ctx.defer_stack):
                    self.gen_stmt(deferred)

                if value is not None:
                    self.gen_expr(value)
                # Epilogue - must pop both r7 and pc (we pushed r7 and lr)
                self.emit("    mov sp, r7")
                self.emit("    pop {r7, pc}")

            case IfStmt(condition=cond, then_body=then_body, elif_branches=elifs, else_body=else_body):
                self.gen_if(cond, then_body, elifs, else_body)

            case WhileStmt(condition=cond, body=body):
                self.gen_while(cond, body)

            case ForStmt(var=var, iterable=iterable, body=body):
                self.gen_for(var, iterable, body)

            case ForUnpackStmt(vars=vars, iterable=iterable, body=body):
                self.gen_for_unpack(vars, iterable, body)

            case BreakStmt():
                loop = self.ctx.current_loop()
                if loop:
                    self.emit(f"    b {loop.end_label}")
                else:
                    raise CodeGenError("break outside of loop")

            case ContinueStmt():
                loop = self.ctx.current_loop()
                if loop:
                    self.emit(f"    b {loop.continue_label}")
                else:
                    raise CodeGenError("continue outside of loop")

            case PassStmt():
                self.emit("    @ pass")

            case GlobalStmt(names=names):
                # Mark variables as global in the current context
                for name in names:
                    self.ctx.mark_global(name)

            case DeferStmt(stmt=deferred_stmt):
                # Add to defer stack - will be executed on return
                self.ctx.defer_stack.append(deferred_stmt)

            case AssertStmt(condition=cond, message=msg):
                self.gen_assert(cond, msg)

            case MatchStmt(expr=expr, arms=arms):
                self.gen_match(expr, arms)

            case TupleUnpackAssign(targets=targets, value=value):
                self.gen_tuple_unpack_assign(targets, value)

            case TryStmt(try_body=try_body, handlers=handlers, else_body=else_body, finally_body=finally_body):
                self.gen_try_stmt(try_body, handlers, else_body, finally_body)

            case RaiseStmt(exception=exc):
                self.gen_raise(exc)

            case _:
                raise CodeGenError(f"Unsupported statement: {type(stmt).__name__}")

    def gen_assignment(self, target: Expr, value: Expr, op: Optional[str]) -> None:
        """Generate assignment statement."""
        self.gen_expr(value)

        if op is not None:
            # Compound assignment
            self.emit("    push {r0}")
            if isinstance(target, Identifier):
                var = self.ctx.locals.get(target.name)
                if var:
                    self.emit(f"    ldr r0, [r7, #{var.offset}]")
                else:
                    self.emit(f"    ldr r0, ={target.name}")
                    self.emit("    ldr r0, [r0]")
            elif isinstance(target, IndexExpr):
                self.gen_expr(target)  # Load current value
            elif isinstance(target, MemberExpr):
                self.gen_member_access(target.obj, target.member)

            self.emit("    pop {r1}")
            match op:
                case '+': self.emit("    add r0, r0, r1")
                case '-': self.emit("    sub r0, r0, r1")
                case '*': self.emit("    mul r0, r0, r1")
                case '/':
                    self.emit("    mov r1, r0")
                    self.emit("    bl __aeabi_idiv")
                case '%':
                    self.emit("    mov r1, r0")
                    self.emit("    bl __aeabi_idivmod")
                    self.emit("    mov r0, r1")
                case '&': self.emit("    and r0, r0, r1")
                case '|': self.emit("    orr r0, r0, r1")
                case '^': self.emit("    eor r0, r0, r1")
                case '<<': self.emit("    lsl r0, r0, r1")
                case '>>': self.emit("    lsr r0, r0, r1")

        # Store result
        if isinstance(target, Identifier):
            var = self.ctx.locals.get(target.name)
            if var:
                self.emit(f"    str r0, [r7, #{var.offset}]")
            else:
                # Global
                self.emit(f"    ldr r1, ={target.name}")
                self.emit("    str r0, [r1]")
        elif isinstance(target, IndexExpr):
            self.gen_index_store(target, "r0")
        elif isinstance(target, MemberExpr):
            self.gen_member_store(target, "r0")

    def gen_index_store(self, target: IndexExpr, value_reg: str) -> None:
        """Generate store to array index."""
        self.emit(f"    push {{{value_reg}}}")  # Save value
        self.gen_expr(target.index)

        # Determine element size
        elem_size = 4  # Default to word
        if isinstance(target.obj, Identifier):
            elem_size = self.array_element_sizes.get(target.obj.name, 4)

        # Scale index by element size
        if elem_size == 4:
            self.emit("    lsl r0, r0, #2")
        elif elem_size == 2:
            self.emit("    lsl r0, r0, #1")
        # For elem_size == 1, no shift needed

        self.emit("    push {r0}")  # Save offset
        self.gen_expr(target.obj)
        self.emit("    pop {r1}")   # offset
        self.emit("    pop {r2}")   # value
        self.emit("    add r0, r0, r1")

        # Use appropriate store instruction
        if elem_size == 1:
            self.emit("    strb r2, [r0]")
        elif elem_size == 2:
            self.emit("    strh r2, [r0]")
        else:
            self.emit("    str r2, [r0]")

    def gen_member_store(self, target: MemberExpr, value_reg: str) -> None:
        """Generate store to struct member."""
        self.emit(f"    push {{{value_reg}}}")
        self.gen_member_addr(target.obj, target.member)
        self.emit("    pop {r1}")
        self.emit("    str r1, [r0]")

    def gen_if(self, cond: Expr, then_body: list[Stmt],
               elifs: list[tuple[Expr, list[Stmt]]],
               else_body: Optional[list[Stmt]]) -> None:
        """Generate if statement."""
        else_label = self.ctx.new_label("else")
        end_label = self.ctx.new_label("endif")

        self.gen_expr(cond)
        self.emit("    cmp r0, #0")
        if elifs or else_body:
            self.emit(f"    beq {else_label}")
        else:
            self.emit(f"    beq {end_label}")

        for s in then_body:
            self.gen_stmt(s)
        self.emit(f"    b {end_label}")

        if elifs:
            for i, (elif_cond, elif_body) in enumerate(elifs):
                self.emit(f"{else_label}:")
                else_label = self.ctx.new_label("else")
                self.gen_expr(elif_cond)
                self.emit("    cmp r0, #0")
                if i < len(elifs) - 1 or else_body:
                    self.emit(f"    beq {else_label}")
                else:
                    self.emit(f"    beq {end_label}")
                for s in elif_body:
                    self.gen_stmt(s)
                self.emit(f"    b {end_label}")

        if else_body:
            self.emit(f"{else_label}:")
            for s in else_body:
                self.gen_stmt(s)

        self.emit(f"{end_label}:")

    def gen_while(self, cond: Expr, body: list[Stmt]) -> None:
        """Generate while loop."""
        start_label = self.ctx.new_label("while")
        end_label = self.ctx.new_label("endwhile")

        self.ctx.push_loop(start_label, end_label)

        self.emit(f"{start_label}:")
        self.gen_expr(cond)
        self.emit("    cmp r0, #0")
        self.emit(f"    beq {end_label}")

        for s in body:
            self.gen_stmt(s)

        self.emit(f"    b {start_label}")
        self.emit(f"{end_label}:")

        self.ctx.pop_loop()

    def gen_for(self, var: str, iterable: Expr, body: list[Stmt]) -> None:
        """Generate for loop."""
        # Handle range() specially
        if isinstance(iterable, CallExpr):
            if isinstance(iterable.func, Identifier) and iterable.func.name == "range":
                self.gen_for_range(var, iterable.args, body)
                return

        # Generic iterable - needs runtime support
        raise CodeGenError("For loops only support range() for now")

    def gen_for_range(self, var: str, range_args: list[Expr], body: list[Stmt]) -> None:
        """Generate for loop over range."""
        loop_var = self.ctx.alloc_local(var)

        # Parse range args: range(end) or range(start, end) or range(start, end, step)
        if len(range_args) == 1:
            start = IntLiteral(0)
            end = range_args[0]
            step = IntLiteral(1)
        elif len(range_args) == 2:
            start = range_args[0]
            end = range_args[1]
            step = IntLiteral(1)
        else:
            start = range_args[0]
            end = range_args[1]
            step = range_args[2]

        start_label = self.ctx.new_label("for")
        end_label = self.ctx.new_label("endfor")
        continue_label = self.ctx.new_label("forcont")

        self.ctx.push_loop(start_label, end_label, continue_label)

        # Initialize loop variable
        self.gen_expr(start)
        self.emit(f"    str r0, [r7, #{loop_var.offset}]")

        # Save end value
        end_var = self.ctx.alloc_local(f"_end_{var}")
        self.gen_expr(end)
        self.emit(f"    str r0, [r7, #{end_var.offset}]")

        # Save step value
        step_var = self.ctx.alloc_local(f"_step_{var}")
        self.gen_expr(step)
        self.emit(f"    str r0, [r7, #{step_var.offset}]")

        # Loop start
        self.emit(f"{start_label}:")
        self.emit(f"    ldr r0, [r7, #{loop_var.offset}]")
        self.emit(f"    ldr r1, [r7, #{end_var.offset}]")
        self.emit("    cmp r0, r1")
        self.emit(f"    bge {end_label}")

        # Body
        for s in body:
            self.gen_stmt(s)

        # Continue label for continue statements
        self.emit(f"{continue_label}:")

        # Increment by step
        self.emit(f"    ldr r0, [r7, #{loop_var.offset}]")
        self.emit(f"    ldr r1, [r7, #{step_var.offset}]")
        self.emit("    add r0, r0, r1")
        self.emit(f"    str r0, [r7, #{loop_var.offset}]")
        self.emit(f"    b {start_label}")

        self.emit(f"{end_label}:")

        self.ctx.pop_loop()

    def gen_for_unpack(self, vars: list[str], iterable: Expr, body: list[Stmt]) -> None:
        """Generate for loop with tuple unpacking."""
        # Allocate loop variables
        loop_vars = [self.ctx.alloc_local(v) for v in vars]

        # Generate iteration over iterable
        # This needs runtime support for iteration protocol
        idx_var = self.ctx.alloc_local(f"_idx")
        len_var = self.ctx.alloc_local(f"_len")
        iter_var = self.ctx.alloc_local(f"_iter")

        start_label = self.ctx.new_label("forunpack")
        end_label = self.ctx.new_label("endforunpack")
        continue_label = self.ctx.new_label("forunpackcont")

        self.ctx.push_loop(start_label, end_label, continue_label)

        # Get iterable
        self.gen_expr(iterable)
        self.emit(f"    str r0, [r7, #{iter_var.offset}]")

        # Get length
        self.emit("    ldr r0, [r0]")  # Assume length at offset 0
        self.emit(f"    str r0, [r7, #{len_var.offset}]")

        # Initialize index
        self.emit("    movs r0, #0")
        self.emit(f"    str r0, [r7, #{idx_var.offset}]")

        # Loop start
        self.emit(f"{start_label}:")
        self.emit(f"    ldr r0, [r7, #{idx_var.offset}]")
        self.emit(f"    ldr r1, [r7, #{len_var.offset}]")
        self.emit("    cmp r0, r1")
        self.emit(f"    bge {end_label}")

        # Unpack tuple element - get tuple at index
        self.emit(f"    ldr r0, [r7, #{iter_var.offset}]")
        self.emit(f"    ldr r1, [r7, #{idx_var.offset}]")
        self.emit("    lsl r1, r1, #2")
        self.emit("    add r0, r0, r1")
        self.emit("    add r0, r0, #8")  # Skip header
        self.emit("    ldr r0, [r0]")  # Load tuple pointer

        # Unpack into variables
        for i, var in enumerate(loop_vars):
            if i > 0:
                self.emit(f"    ldr r0, [r7, #{iter_var.offset}]")
                self.emit(f"    ldr r1, [r7, #{idx_var.offset}]")
                self.emit("    lsl r1, r1, #2")
                self.emit("    add r0, r0, r1")
                self.emit("    add r0, r0, #8")
                self.emit("    ldr r0, [r0]")
            self.emit(f"    ldr r1, [r0, #{i * 4}]")
            self.emit(f"    str r1, [r7, #{var.offset}]")

        # Body
        for s in body:
            self.gen_stmt(s)

        # Continue label
        self.emit(f"{continue_label}:")

        # Increment index
        self.emit(f"    ldr r0, [r7, #{idx_var.offset}]")
        self.emit("    add r0, r0, #1")
        self.emit(f"    str r0, [r7, #{idx_var.offset}]")
        self.emit(f"    b {start_label}")

        self.emit(f"{end_label}:")

        self.ctx.pop_loop()

    def gen_assert(self, cond: Expr, msg: Optional[Expr]) -> None:
        """Generate assert statement."""
        ok_label = self.ctx.new_label("assert_ok")

        self.gen_expr(cond)
        self.emit("    cmp r0, #0")
        self.emit(f"    bne {ok_label}")

        # Assertion failed
        if msg:
            self.gen_expr(msg)
            self.emit("    bl __pynux_assert_fail_msg")
        else:
            self.emit("    bl __pynux_assert_fail")

        self.emit(f"{ok_label}:")

    def gen_match(self, expr: Expr, arms: list[MatchArm]) -> None:
        """Generate match statement."""
        end_label = self.ctx.new_label("endmatch")

        # Evaluate match expression
        self.gen_expr(expr)
        self.emit("    push {r0}")  # Save match value

        for i, arm in enumerate(arms):
            next_arm = self.ctx.new_label("matcharm")

            pattern = arm.pattern

            if pattern.name == "_":
                # Wildcard - always matches
                self.emit("    pop {r0}")  # Consume saved value
                for s in arm.body:
                    self.gen_stmt(s)
                self.emit(f"    b {end_label}")
            else:
                # Check if pattern matches
                self.emit("    ldr r0, [sp]")  # Peek saved value

                # For enum variants, check discriminant
                # For now, assume integer comparison
                self.emit(f"    @ match pattern {pattern.name}")

                # If pattern has bindings, extract them
                for j, binding in enumerate(pattern.bindings):
                    bind_var = self.ctx.alloc_local(binding)
                    # Extract from tuple/struct at offset
                    self.emit("    ldr r0, [sp]")
                    self.emit(f"    ldr r1, [r0, #{(j + 1) * 4}]")
                    self.emit(f"    str r1, [r7, #{bind_var.offset}]")

                # Execute arm body
                for s in arm.body:
                    self.gen_stmt(s)

                self.emit(f"    add sp, sp, #4")  # Pop saved value
                self.emit(f"    b {end_label}")

            self.emit(f"{next_arm}:")

        # Clean up stack if no arm matched (shouldn't happen with _)
        self.emit("    add sp, sp, #4")

        self.emit(f"{end_label}:")

    def gen_tuple_unpack_assign(self, targets: list[str], value: Expr) -> None:
        """Generate tuple unpacking assignment: a, b = expr."""
        # Evaluate the right-hand side
        self.gen_expr(value)
        self.emit("    push {r0}")  # Save tuple/value pointer

        # For tuple literal on RHS: evaluate and store directly
        if isinstance(value, TupleLiteral):
            # Values are on the heap, indexed
            for i, target in enumerate(targets):
                self.emit("    ldr r0, [sp]")
                self.emit(f"    ldr r0, [r0, #{i * 4}]")
                if target in self.ctx.locals:
                    var = self.ctx.locals[target]
                    self.emit(f"    str r0, [r7, #{var.offset}]")
                else:
                    # Allocate new local
                    var = self.ctx.alloc_local(target)
                    self.emit(f"    str r0, [r7, #{var.offset}]")
        else:
            # For other expressions (function returns, etc.)
            # Assume the result is a pointer to contiguous values
            for i, target in enumerate(targets):
                self.emit("    ldr r0, [sp]")
                if i > 0:
                    self.emit(f"    add r0, r0, #{i * 4}")
                self.emit("    ldr r0, [r0]")
                if target in self.ctx.locals:
                    var = self.ctx.locals[target]
                    self.emit(f"    str r0, [r7, #{var.offset}]")
                else:
                    var = self.ctx.alloc_local(target)
                    self.emit(f"    str r0, [r7, #{var.offset}]")

        self.emit("    pop {r0}")  # Clean up

    def gen_try_stmt(self, try_body: list, handlers: list, else_body: list, finally_body: list) -> None:
        """Generate try/except/finally statement."""
        # Simple implementation: try/except is just conditional execution
        # In a real system, we'd need setjmp/longjmp or similar

        # For now, we use a simple error flag approach
        # Set error flag to 0, run try block
        # If any function sets error flag, jump to handler

        error_var = self.ctx.alloc_local("_error_flag")
        handler_label = self.ctx.new_label("except")
        else_label = self.ctx.new_label("else")
        finally_label = self.ctx.new_label("finally")
        end_label = self.ctx.new_label("endtry")

        # Initialize error flag to 0
        self.emit("    movs r0, #0")
        self.emit(f"    str r0, [r7, #{error_var.offset}]")

        # Execute try body
        for s in try_body:
            self.gen_stmt(s)

        # Check if error occurred
        self.emit(f"    ldr r0, [r7, #{error_var.offset}]")
        self.emit("    cmp r0, #0")
        self.emit(f"    bne {handler_label}")

        # No error - run else block if present
        if else_body:
            for s in else_body:
                self.gen_stmt(s)
        self.emit(f"    b {finally_label}")

        # Exception handlers
        self.emit(f"{handler_label}:")
        for handler in handlers:
            # For now, just run the handler body
            # (proper exception matching would need type checking)
            if handler.name:
                # Create variable for exception
                exc_var = self.ctx.alloc_local(handler.name)
                self.emit(f"    ldr r0, [r7, #{error_var.offset}]")
                self.emit(f"    str r0, [r7, #{exc_var.offset}]")
            for s in handler.body:
                self.gen_stmt(s)
            # Clear error flag after handling
            self.emit("    movs r0, #0")
            self.emit(f"    str r0, [r7, #{error_var.offset}]")
            break  # Only run first matching handler

        # Finally block (always runs)
        self.emit(f"{finally_label}:")
        for s in finally_body:
            self.gen_stmt(s)

        self.emit(f"{end_label}:")

    def gen_raise(self, exc: Optional[Expr]) -> None:
        """Generate raise statement."""
        if exc:
            self.gen_expr(exc)
            # Store exception and halt
            self.emit("    bl __pynux_raise")
        else:
            # Re-raise current exception
            self.emit("    bl __pynux_reraise")

    # -------------------------------------------------------------------------
    # Declaration generation
    # -------------------------------------------------------------------------

    def gen_function(self, func: FunctionDef) -> None:
        """Generate code for a function."""
        self.ctx = FunctionContext(func.name)

        # Create locals for parameters
        for i, param in enumerate(func.params):
            var = self.ctx.alloc_local(param.name, 4, param.param_type)

        self.emit("")
        self.emit(f"    .global {func.name}")
        self.emit(f"    .type {func.name}, %function")
        self.emit(f"{func.name}:")
        self.emit("    push {r7, lr}")
        self.emit("    mov r7, sp")

        # Reserve space for locals (will be adjusted later)
        stack_reserve_idx = len(self.output)
        self.emit("    @ STACK_RESERVE")

        # Store parameters to stack
        for i, param in enumerate(func.params):
            if i < 4:
                var = self.ctx.locals[param.name]
                self.emit(f"    str r{i}, [r7, #{var.offset}]")

        # Generate body
        for stmt in func.body:
            self.gen_stmt(stmt)

        # Default return 0
        if not func.body or not isinstance(func.body[-1], ReturnStmt):
            # Execute deferred statements
            for deferred in reversed(self.ctx.defer_stack):
                self.gen_stmt(deferred)
            self.emit("    movs r0, #0")
            self.emit("    mov sp, r7")
            self.emit("    pop {r7, pc}")

        # Fix up stack reservation
        stack_size = (self.ctx.stack_size + 7) & ~7  # Align to 8
        if stack_size > 0:
            self.output[stack_reserve_idx] = f"    sub sp, sp, #{stack_size}"
        else:
            self.output[stack_reserve_idx] = "    @ no locals"

        self.emit(f"    .size {func.name}, . - {func.name}")
        # Add literal pool after each function
        self.emit("    .ltorg")

    def gen_class(self, cls: ClassDef) -> None:
        """Generate code for a class definition."""
        # Calculate field offsets
        fields = []
        offset = 0
        for field in cls.fields:
            size = self.get_type_size(field.field_type)
            fields.append((field.name, field.field_type, offset))
            offset += size
            # Align to 4 bytes
            offset = (offset + 3) & ~3

        self.structs[cls.name] = StructInfo(cls.name, fields, offset)

        # Generate methods
        for method in cls.methods:
            # Rename method to include class name
            method_name = f"{cls.name}_{method.name}"
            # Add 'self' as first parameter if not already there
            if not method.params or method.params[0].name != "self":
                self_param = Parameter("self", Type(cls.name))
                method.params.insert(0, self_param)

            # Save original name and generate
            orig_name = method.name
            method.name = method_name
            self.gen_function(method)
            method.name = orig_name

    def gen_extern(self, decl: ExternDecl) -> None:
        """Generate extern function reference."""
        self.extern_funcs.add(decl.name)

    def gen_program(self, program: Program) -> str:
        """Generate code for entire program."""
        # Header
        self.emit("@ Pynux generated ARM Thumb-2 assembly")
        self.emit("@ Target: Cortex-M3 (mps2-an385)")
        self.emit("")
        self.emit("    .syntax unified")
        self.emit("    .cpu cortex-m3")
        self.emit("    .thumb")
        self.emit("")

        # Text section
        self.emit("    .section .text")
        self.emit("")

        # First pass: collect global variable info and class definitions
        global_vars: list[VarDecl] = []
        for decl in program.declarations:
            if isinstance(decl, VarDecl):
                global_vars.append(decl)
                self.global_var_types[decl.name] = decl.var_type
                # Track if this is an array
                if isinstance(decl.var_type, ArrayType):
                    self.global_arrays.add(decl.name)
                    elem_size = self.get_type_size(decl.var_type.element_type)
                    self.array_element_sizes[decl.name] = elem_size
            elif isinstance(decl, ClassDef):
                # Pre-register class for field offset calculation
                self.gen_class(decl)

        # Second pass: generate functions
        for decl in program.declarations:
            match decl:
                case FunctionDef():
                    self.gen_function(decl)
                case ExternDecl():
                    self.gen_extern(decl)
                case ClassDef():
                    pass  # Already processed
                case EnumDef():
                    pass  # Enums don't need codegen
                case VarDecl():
                    pass  # Already collected

        # Data section for global variables
        if global_vars:
            self.emit("")
            self.emit("    .section .data")
            for var in global_vars:
                self.emit(f"    .global {var.name}")
                self.emit(f"{var.name}:")
                size = self.get_type_size(var.var_type)
                if var.value is not None:
                    # Handle constant initialization
                    if isinstance(var.value, IntLiteral):
                        if size == 1:
                            self.emit(f"    .byte {var.value.value}")
                        elif size == 2:
                            self.emit(f"    .short {var.value.value}")
                        else:
                            self.emit(f"    .long {var.value.value}")
                    elif isinstance(var.value, BoolLiteral):
                        self.emit(f"    .long {1 if var.value.value else 0}")
                    elif isinstance(var.value, FloatLiteral):
                        import struct
                        bits = struct.unpack('<I', struct.pack('<f', var.value.value))[0]
                        self.emit(f"    .long {bits}  @ float {var.value.value}")
                    else:
                        # Default to zero
                        self.emit(f"    .space {size}")
                else:
                    self.emit(f"    .space {size}")
                self.emit("    .align 2")

        # Data section with string literals
        if self.string_literals:
            self.emit("")
            self.emit("    .section .rodata")
            for s, label in self.string_literals.items():
                self.emit(f"{label}:")
                # Escape the string for assembly
                escaped = s.replace("\\", "\\\\").replace('"', '\\"')
                escaped = escaped.replace("\n", "\\n").replace("\t", "\\t")
                escaped = escaped.replace("\r", "\\r").replace("\0", "\\0")
                # Replace any other non-printable characters with octal escapes
                result = []
                for c in escaped:
                    if ord(c) < 32 and c not in '\n\t\r':
                        result.append(f"\\{ord(c):03o}")
                    else:
                        result.append(c)
                escaped = "".join(result)
                self.emit(f'    .asciz "{escaped}"')
                self.emit("    .align 2")

        return "\n".join(self.output) + "\n"


def generate(program: Program) -> str:
    """Generate ARM assembly from AST."""
    codegen = ARMCodeGen()
    return codegen.gen_program(program)


if __name__ == "__main__":
    from .parser import parse

    code = '''
def main() -> int32:
    x: int32 = 42
    if x > 0:
        x = x + 1
    return x
'''
    program = parse(code)
    asm = generate(program)
    print(asm)
