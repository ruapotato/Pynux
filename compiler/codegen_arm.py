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
class UnionInfo:
    """Information about a union (all fields at offset 0)."""
    name: str
    fields: list[tuple[str, Type]]  # (name, type) - all at offset 0
    total_size: int  # Size of largest field


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
    is_interrupt: bool = False  # True for @interrupt functions

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
        self.defined_funcs: set[str] = set()  # Track user-defined function names
        self.global_arrays: set[str] = set()  # Track global array names
        self.array_element_sizes: dict[str, int] = {}  # Array name -> element size
        self.structs: dict[str, StructInfo] = {}  # Struct/class definitions
        self.unions: dict[str, 'UnionInfo'] = {}  # Union definitions
        self.global_var_types: dict[str, Type] = {}  # Global variable types
        self.class_bases: dict[str, str] = {}  # Class name -> parent class name
        self.properties: dict[str, str] = {}  # "Class.prop" -> method name
        self.pending_lambdas: list[tuple[str, list[str], Expr]] = []  # Deferred lambda generation
        self.packed_structs: set[str] = set()  # Structs with @packed decorator
        self.interrupt_funcs: dict[str, int] = {}  # Function name -> interrupt vector

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

        # Handle function pointer types
        if isinstance(t, FunctionPointerType):
            return 4  # Function pointers are 4 bytes on ARM

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

    def get_expr_type(self, expr) -> Type | None:
        """Get the result type of an expression."""
        if isinstance(expr, Identifier):
            if expr.name in self.ctx.locals:
                return self.ctx.locals[expr.name].var_type
            return self.global_var_types.get(expr.name)
        elif isinstance(expr, IndexExpr):
            # For arr[i], result type is element type of arr
            obj_type = self.get_expr_type(expr.obj)
            if isinstance(obj_type, ArrayType):
                return obj_type.element_type
            elif isinstance(obj_type, PointerType):
                return obj_type.base_type
            return None
        elif isinstance(expr, MemberExpr):
            # For obj.field, look up field type
            obj_type = self.get_expr_type(expr.obj)
            if obj_type and hasattr(obj_type, 'name') and obj_type.name in self.structs:
                struct_info = self.structs[obj_type.name]
                for field_name, field_type, _ in struct_info.fields:
                    if field_name == expr.member:
                        return field_type
            return None
        return None

    def emit_stack_alloc(self, size: int) -> None:
        """Emit code to allocate stack space, handling large values."""
        if size == 0:
            self.emit("    @ no locals")
        elif size <= 508:
            # Small values can use direct SUB
            self.emit(f"    sub sp, sp, #{size}")
        elif size <= 4095:
            # Medium values: use SUB.W with 12-bit immediate
            self.emit(f"    sub.w sp, sp, #{size}")
        else:
            # Large values: load into register first
            self.emit(f"    ldr r12, ={size}")
            self.emit("    sub sp, sp, r12")

    def emit_stack_dealloc(self, size: int) -> None:
        """Emit code to deallocate stack space, handling large values."""
        if size == 0:
            return
        elif size <= 508:
            self.emit(f"    add sp, sp, #{size}")
        elif size <= 4095:
            self.emit(f"    add.w sp, sp, #{size}")
        else:
            self.emit(f"    ldr r12, ={size}")
            self.emit("    add sp, sp, r12")

    def emit_load_local(self, reg: str, offset: int) -> None:
        """Emit code to load from a local variable, handling large offsets."""
        if -255 <= offset <= 4095:
            self.emit(f"    ldr {reg}, [r7, #{offset}]")
        else:
            # Large negative offset - need to compute address
            self.emit(f"    ldr r12, ={-offset}")
            self.emit(f"    sub r12, r7, r12")
            self.emit(f"    ldr {reg}, [r12]")

    def emit_store_local(self, reg: str, offset: int) -> None:
        """Emit code to store to a local variable, handling large offsets."""
        if -255 <= offset <= 4095:
            self.emit(f"    str {reg}, [r7, #{offset}]")
        else:
            # Large negative offset - need to compute address
            # Save the value temporarily
            self.emit(f"    mov r11, {reg}")
            self.emit(f"    ldr r12, ={-offset}")
            self.emit(f"    sub r12, r7, r12")
            self.emit(f"    str r11, [r12]")

    def emit_add_local_addr(self, reg: str, offset: int) -> None:
        """Emit code to compute address of local variable into reg."""
        if -255 <= offset <= 255:
            if offset >= 0:
                self.emit(f"    add {reg}, r7, #{offset}")
            else:
                self.emit(f"    sub {reg}, r7, #{-offset}")
        else:
            self.emit(f"    ldr r12, ={-offset}")
            self.emit(f"    sub {reg}, r7, r12")

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
                    # Local arrays: compute address, don't load value
                    if isinstance(var.var_type, ArrayType):
                        self.emit_add_local_addr("r0", var.offset)
                    else:
                        self.emit_load_local("r0", var.offset)
                elif name in self.global_arrays:
                    # Global array - just load address, don't dereference
                    self.emit(f"    ldr r0, ={name}")
                elif name in self.defined_funcs or name in self.extern_funcs:
                    # Function reference - load address (for function pointers)
                    self.emit(f"    ldr r0, ={name}")
                else:
                    # Global scalar variable
                    self.emit(f"    ldr r0, ={name}")
                    self.emit(f"    ldr r0, [r0]")

            case BinaryExpr(op=op, left=left, right=right):
                self.gen_binary(op, left, right)

            case UnaryExpr(op=op, operand=operand):
                self.gen_unary(op, operand)

            case CallExpr(func=func, args=args, kwargs=kwargs):
                self.gen_call(func, args, kwargs)

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
                    'count': 'str_count',
                    'index': 'str_index',
                }

                # Handle list/array methods inline
                if method in ('append', 'pop', 'insert', 'remove', 'clear'):
                    self.gen_list_method(obj, method, args)
                elif method in ('keys', 'values', 'items', 'get'):
                    self.gen_dict_method(obj, method, args)
                elif method in string_methods:
                    # Call runtime function with obj as first arg
                    all_args = [obj] + args
                    self.gen_call(Identifier(string_methods[method]), all_args)
                elif isinstance(obj, Identifier) and obj.name in self.structs:
                    # Static method call: ClassName.method(args)
                    class_name = obj.name
                    func_name = f"{class_name}_{method}"
                    self.gen_call(Identifier(func_name), args)
                else:
                    # Generic method call - look up object's type for class prefix
                    all_args = [obj] + args
                    class_name = None
                    if isinstance(obj, Identifier):
                        # Try to get type from locals first
                        if obj.name in self.ctx.locals:
                            var_type = self.ctx.locals[obj.name].var_type
                            if var_type is not None:
                                type_name = getattr(var_type, 'name', str(var_type))
                                if type_name in self.structs:
                                    class_name = type_name
                        # Try global types
                        elif obj.name in self.global_var_types:
                            var_type = self.global_var_types[obj.name]
                            if var_type is not None:
                                type_name = getattr(var_type, 'name', str(var_type))
                                if type_name in self.structs:
                                    class_name = type_name

                    if class_name:
                        func_name = f"{class_name}_{method}"
                        self.gen_call(Identifier(func_name), all_args)
                    else:
                        self.gen_call(Identifier(method), all_args)

            case IndexExpr(obj=obj, index=index):
                # Check if this is dictionary access
                var_type = None
                if isinstance(obj, Identifier):
                    var_type = self.global_var_types.get(obj.name)
                    if var_type is None and obj.name in self.ctx.locals:
                        var_type = self.ctx.locals[obj.name].var_type

                if isinstance(var_type, DictType):
                    # Dictionary access: d[key]
                    self.gen_expr(index)
                    self.emit("    push {r0}")  # Save key
                    self.gen_expr(obj)
                    self.emit("    pop {r1}")   # r1 = key, r0 = dict ptr
                    # Determine key type and call appropriate lookup
                    key_is_str = isinstance(index, StringLiteral)
                    if hasattr(var_type.key_type, 'name') and var_type.key_type.name == 'str':
                        key_is_str = True
                    if key_is_str:
                        self.emit("    bl __pynux_dict_get_str")
                    else:
                        self.emit("    bl __pynux_dict_get_int")
                else:
                    # Array/string indexing: obj[index]
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
                        # Check for string type - characters are 1 byte
                        if var_type is not None:
                            type_name = getattr(var_type, 'name', str(var_type))
                            if type_name == 'str':
                                elem_size = 1
                            # Handle Ptr[T] types - get element size from base type
                            elif isinstance(var_type, PointerType):
                                elem_size = self.get_type_size(var_type.base_type)
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
                    if elem_size == 1:
                        pass  # No scaling needed
                    elif elem_size == 2:
                        self.emit("    lsl r1, r1, #1")
                    elif elem_size == 4:
                        self.emit("    lsl r1, r1, #2")
                    elif elem_size == 8:
                        self.emit("    lsl r1, r1, #3")
                    elif elem_size == 16:
                        self.emit("    lsl r1, r1, #4")
                    elif elem_size == 32:
                        self.emit("    lsl r1, r1, #5")
                    elif elem_size == 64:
                        self.emit("    lsl r1, r1, #6")
                    else:
                        # General case: multiply by element size
                        self.emit(f"    ldr r2, ={elem_size}")
                        self.emit("    mul r1, r1, r2")

                    self.emit("    add r0, r0, r1")

                    # Check if element type is an array (nested array access)
                    # If so, don't load - just return the address
                    is_nested_array = False
                    if isinstance(var_type, ArrayType) and isinstance(var_type.element_type, ArrayType):
                        is_nested_array = True

                    if is_nested_array:
                        pass  # Just return address, don't load
                    elif elem_size == 1:
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

            case StructInitExpr(struct_name=name, fields=init_fields):
                self.gen_struct_init(name, init_fields)

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

            case LambdaExpr(params=params, body=body):
                # Generate lambda as anonymous function
                self.gen_lambda(params, body)

            case SizeOfExpr(target_type=t):
                size = self.get_type_size(t)
                self.emit(f"    movs r0, #{size}")

            case CastExpr(target_type=t, expr=e):
                self.gen_expr(e)
                # Handle float<->int conversions
                # For now, just pass through (soft-float would need runtime calls)

            case AsmExpr(code=code):
                # Handle multi-line asm blocks - strip common indent and emit each line
                import textwrap
                code = textwrap.dedent(code).strip()
                for line in code.split('\n'):
                    line = line.rstrip()
                    if line:
                        self.emit(f"    {line}")

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

                # Determine element size by getting the type of operand.obj
                elem_size = 4  # Default to word
                obj_type = self.get_expr_type(operand.obj)
                if isinstance(obj_type, ArrayType):
                    elem_size = self.get_type_size(obj_type.element_type)
                elif isinstance(obj_type, PointerType):
                    elem_size = self.get_type_size(obj_type.base_type)
                elif isinstance(operand.obj, Identifier):
                    # Fallback for simple identifiers
                    elem_size = self.array_element_sizes.get(operand.obj.name, 4)

                # Scale index by element size
                if elem_size == 1:
                    pass  # No scaling needed
                elif elem_size == 2:
                    self.emit("    lsl r0, r0, #1")
                elif elem_size == 4:
                    self.emit("    lsl r0, r0, #2")
                elif elem_size == 8:
                    self.emit("    lsl r0, r0, #3")
                elif elem_size == 16:
                    self.emit("    lsl r0, r0, #4")
                elif elem_size == 32:
                    self.emit("    lsl r0, r0, #5")
                else:
                    self.emit(f"    ldr r2, ={elem_size}")
                    self.emit("    mul r0, r0, r2")

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

    def gen_call(self, func: Expr, args: list[Expr], kwargs: dict = None) -> None:
        """Generate function call."""
        if kwargs is None:
            kwargs = {}

        # Handle method calls on class names (static/class methods)
        if isinstance(func, MemberExpr):
            if isinstance(func.obj, Identifier):
                class_name = func.obj.name
                method_name = func.member
                # Check if this is a known class
                if class_name in self.structs:
                    # Generate call to Class_method with AAPCS calling convention
                    full_name = f"{class_name}_{method_name}"
                    num_stack_args = max(0, len(args) - 4)

                    if num_stack_args > 0:
                        for arg in reversed(args[4:]):
                            self.gen_expr(arg)
                            self.emit("    push {r0}")

                    first_four = args[:4]
                    for arg in reversed(first_four):
                        self.gen_expr(arg)
                        self.emit("    push {r0}")
                    for i in range(len(first_four)):
                        self.emit(f"    pop {{r{i}}}")

                    self.emit(f"    bl {full_name}")

                    if num_stack_args > 0:
                        stack_cleanup = num_stack_args * 4
                        self.emit(f"    add sp, sp, #{stack_cleanup}")
                    return
            raise CodeGenError(f"Unsupported member call: {func}")

        # Get function name or handle indirect call
        if isinstance(func, Identifier):
            func_name = func.name
        else:
            # Indirect function call through function pointer
            self.gen_indirect_call(func, args)
            return

        # Check if this is a class instantiation (constructor call)
        if func_name in self.structs:
            struct = self.structs[func_name]
            # Allocate memory for the struct on the stack (for now)
            # Return a pointer to the struct
            # For simplicity, we'll just allocate a local struct and return its address
            self.emit(f"    @ Allocate {func_name} instance ({struct.total_size} bytes)")
            self.emit_stack_alloc(struct.total_size)
            self.emit("    mov r0, sp")
            # Initialize to zero
            if struct.total_size <= 16:
                self.emit("    movs r1, #0")
                for i in range(0, struct.total_size, 4):
                    self.emit(f"    str r1, [sp, #{i}]")
            return

        # Handle built-in functions specially
        if func_name == "print":
            self.gen_builtin_print(args, kwargs)
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
        # Memory barrier builtins for hardware synchronization
        elif func_name == "dmb":
            # Data Memory Barrier - ensures all memory accesses complete
            self.emit("    dmb")
            self.emit("    movs r0, #0")
            return
        elif func_name == "dsb":
            # Data Synchronization Barrier - ensures all memory accesses complete before continuing
            self.emit("    dsb")
            self.emit("    movs r0, #0")
            return
        elif func_name == "isb":
            # Instruction Synchronization Barrier - flushes pipeline
            self.emit("    isb")
            self.emit("    movs r0, #0")
            return
        elif func_name == "wfi":
            # Wait For Interrupt - low power wait
            self.emit("    wfi")
            self.emit("    movs r0, #0")
            return
        elif func_name == "wfe":
            # Wait For Event
            self.emit("    wfe")
            self.emit("    movs r0, #0")
            return
        elif func_name == "sev":
            # Send Event
            self.emit("    sev")
            self.emit("    movs r0, #0")
            return

        # Atomic operations using LDREX/STREX (Cortex-M3+)
        elif func_name == "atomic_load":
            # atomic_load(ptr) -> value
            # Uses LDREX for exclusive load
            if len(args) != 1:
                raise CodeGenError("atomic_load takes 1 argument")
            self.gen_expr(args[0])  # ptr in r0
            self.emit("    ldrex r0, [r0]")
            return

        elif func_name == "atomic_store":
            # atomic_store(ptr, value) -> success (0 = success)
            # Uses STREX for exclusive store
            if len(args) != 2:
                raise CodeGenError("atomic_store takes 2 arguments")
            self.gen_expr(args[0])  # ptr
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # value
            self.emit("    mov r1, r0")  # value in r1
            self.emit("    pop {r2}")    # ptr in r2
            self.emit("    strex r0, r1, [r2]")  # r0 = 0 on success
            return

        elif func_name == "atomic_add":
            # atomic_add(ptr, val) -> old_value
            # LDREX, ADD, STREX loop
            if len(args) != 2:
                raise CodeGenError("atomic_add takes 2 arguments")
            label = self.ctx.new_label("atomic_add")
            self.gen_expr(args[0])  # ptr
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # val
            self.emit("    mov r1, r0")  # val in r1
            self.emit("    pop {r2}")    # ptr in r2
            self.emit(f"{label}:")
            self.emit("    ldrex r0, [r2]")      # old value
            self.emit("    add r3, r0, r1")      # new value
            self.emit("    strex r4, r3, [r2]")  # try store
            self.emit(f"    cbnz r4, {label}")   # retry if failed
            return

        elif func_name == "atomic_sub":
            # atomic_sub(ptr, val) -> old_value
            if len(args) != 2:
                raise CodeGenError("atomic_sub takes 2 arguments")
            label = self.ctx.new_label("atomic_sub")
            self.gen_expr(args[0])  # ptr
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # val
            self.emit("    mov r1, r0")  # val in r1
            self.emit("    pop {r2}")    # ptr in r2
            self.emit(f"{label}:")
            self.emit("    ldrex r0, [r2]")      # old value
            self.emit("    sub r3, r0, r1")      # new value
            self.emit("    strex r4, r3, [r2]")  # try store
            self.emit(f"    cbnz r4, {label}")   # retry if failed
            return

        elif func_name == "atomic_cmpxchg":
            # atomic_cmpxchg(ptr, expected, desired) -> old_value
            # Compare-and-swap: if *ptr == expected, *ptr = desired
            if len(args) != 3:
                raise CodeGenError("atomic_cmpxchg takes 3 arguments")
            label = self.ctx.new_label("atomic_cmpxchg")
            label_done = self.ctx.new_label("atomic_cmpxchg_done")
            self.gen_expr(args[0])  # ptr
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # expected
            self.emit("    push {r0}")
            self.gen_expr(args[2])  # desired
            self.emit("    mov r3, r0")  # desired in r3
            self.emit("    pop {r1}")    # expected in r1
            self.emit("    pop {r2}")    # ptr in r2
            self.emit(f"{label}:")
            self.emit("    ldrex r0, [r2]")      # old value
            self.emit("    cmp r0, r1")          # compare with expected
            self.emit(f"    bne {label_done}")   # if not equal, return old value
            self.emit("    strex r4, r3, [r2]")  # try store desired
            self.emit(f"    cbnz r4, {label}")   # retry if failed
            self.emit(f"{label_done}:")
            return

        elif func_name == "atomic_or":
            # atomic_or(ptr, val) -> old_value
            if len(args) != 2:
                raise CodeGenError("atomic_or takes 2 arguments")
            label = self.ctx.new_label("atomic_or")
            self.gen_expr(args[0])  # ptr
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # val
            self.emit("    mov r1, r0")
            self.emit("    pop {r2}")
            self.emit(f"{label}:")
            self.emit("    ldrex r0, [r2]")
            self.emit("    orr r3, r0, r1")
            self.emit("    strex r4, r3, [r2]")
            self.emit(f"    cbnz r4, {label}")
            return

        elif func_name == "atomic_and":
            # atomic_and(ptr, val) -> old_value
            if len(args) != 2:
                raise CodeGenError("atomic_and takes 2 arguments")
            label = self.ctx.new_label("atomic_and")
            self.gen_expr(args[0])  # ptr
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # val
            self.emit("    mov r1, r0")
            self.emit("    pop {r2}")
            self.emit(f"{label}:")
            self.emit("    ldrex r0, [r2]")
            self.emit("    and r3, r0, r1")
            self.emit("    strex r4, r3, [r2]")
            self.emit(f"    cbnz r4, {label}")
            return

        elif func_name == "atomic_xor":
            # atomic_xor(ptr, val) -> old_value
            if len(args) != 2:
                raise CodeGenError("atomic_xor takes 2 arguments")
            label = self.ctx.new_label("atomic_xor")
            self.gen_expr(args[0])  # ptr
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # val
            self.emit("    mov r1, r0")
            self.emit("    pop {r2}")
            self.emit(f"{label}:")
            self.emit("    ldrex r0, [r2]")
            self.emit("    eor r3, r0, r1")
            self.emit("    strex r4, r3, [r2]")
            self.emit(f"    cbnz r4, {label}")
            return

        elif func_name == "critical_enter":
            # critical_enter() -> old_primask
            # Disable interrupts and return previous state
            self.emit("    mrs r0, primask")  # save old state
            self.emit("    cpsid i")          # disable interrupts
            return

        elif func_name == "critical_exit":
            # critical_exit(old_primask)
            # Restore interrupt state
            if len(args) != 1:
                raise CodeGenError("critical_exit takes 1 argument")
            self.gen_expr(args[0])  # old primask
            self.emit("    msr primask, r0")  # restore state
            self.emit("    movs r0, #0")
            return

        elif func_name == "clrex":
            # clrex() - Clear exclusive monitor
            self.emit("    clrex")
            self.emit("    movs r0, #0")
            return

        # Bit manipulation builtins for register/hardware access
        elif func_name == "bit_set":
            # bit_set(val, bit) -> val with bit set
            if len(args) != 2:
                raise CodeGenError("bit_set takes 2 arguments")
            self.gen_expr(args[0])  # val
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # bit position
            self.emit("    movs r1, #1")
            self.emit("    lsl r1, r1, r0")  # r1 = 1 << bit
            self.emit("    pop {r0}")
            self.emit("    orr r0, r0, r1")
            return

        elif func_name == "bit_clear":
            # bit_clear(val, bit) -> val with bit cleared
            if len(args) != 2:
                raise CodeGenError("bit_clear takes 2 arguments")
            self.gen_expr(args[0])  # val
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # bit position
            self.emit("    movs r1, #1")
            self.emit("    lsl r1, r1, r0")  # r1 = 1 << bit
            self.emit("    pop {r0}")
            self.emit("    bic r0, r0, r1")
            return

        elif func_name == "bit_test":
            # bit_test(val, bit) -> 1 if set, 0 if clear
            if len(args) != 2:
                raise CodeGenError("bit_test takes 2 arguments")
            self.gen_expr(args[0])  # val
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # bit position
            self.emit("    movs r1, #1")
            self.emit("    lsl r1, r1, r0")  # r1 = 1 << bit
            self.emit("    pop {r0}")
            self.emit("    tst r0, r1")
            self.emit("    ite ne")
            self.emit("    movne r0, #1")
            self.emit("    moveq r0, #0")
            return

        elif func_name == "bit_toggle":
            # bit_toggle(val, bit) -> val with bit toggled
            if len(args) != 2:
                raise CodeGenError("bit_toggle takes 2 arguments")
            self.gen_expr(args[0])  # val
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # bit position
            self.emit("    movs r1, #1")
            self.emit("    lsl r1, r1, r0")  # r1 = 1 << bit
            self.emit("    pop {r0}")
            self.emit("    eor r0, r0, r1")
            return

        elif func_name == "bits_get":
            # bits_get(val, start, width) -> extracted bits
            # Uses UBFX (Unsigned Bit Field Extract) on Cortex-M3+
            if len(args) != 3:
                raise CodeGenError("bits_get takes 3 arguments (val, start, width)")
            self.gen_expr(args[0])  # val
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # start bit
            self.emit("    push {r0}")
            self.gen_expr(args[2])  # width
            self.emit("    mov r2, r0")      # width in r2
            self.emit("    pop {r1}")        # start in r1
            self.emit("    pop {r0}")        # val in r0
            # Use shift and mask (UBFX would require immediate args)
            self.emit("    lsr r0, r0, r1")  # shift right by start
            self.emit("    movs r3, #1")
            self.emit("    lsl r3, r3, r2")  # r3 = 1 << width
            self.emit("    subs r3, r3, #1") # r3 = mask
            self.emit("    and r0, r0, r3")
            return

        elif func_name == "bits_set":
            # bits_set(val, field, start, width) -> val with field inserted
            # Clears bits at [start:start+width] and inserts field value
            if len(args) != 4:
                raise CodeGenError("bits_set takes 4 arguments (val, field, start, width)")
            self.gen_expr(args[0])  # val
            self.emit("    push {r0}")
            self.gen_expr(args[1])  # field value to insert
            self.emit("    push {r0}")
            self.gen_expr(args[2])  # start bit
            self.emit("    push {r0}")
            self.gen_expr(args[3])  # width
            self.emit("    mov r3, r0")      # width in r3
            self.emit("    pop {r2}")        # start in r2
            self.emit("    pop {r1}")        # field in r1
            self.emit("    pop {r0}")        # val in r0
            # Create mask for the field
            self.emit("    push {r4, r5}")
            self.emit("    movs r4, #1")
            self.emit("    lsl r4, r4, r3")  # r4 = 1 << width
            self.emit("    subs r4, r4, #1") # r4 = width mask
            self.emit("    and r1, r1, r4")  # mask field value
            self.emit("    lsl r4, r4, r2")  # shift mask to position
            self.emit("    bic r0, r0, r4")  # clear bits in val
            self.emit("    lsl r1, r1, r2")  # shift field to position
            self.emit("    orr r0, r0, r1")  # insert field
            self.emit("    pop {r4, r5}")
            return

        elif func_name == "clz":
            # clz(val) -> count of leading zeros (Cortex-M3+)
            if len(args) != 1:
                raise CodeGenError("clz takes 1 argument")
            self.gen_expr(args[0])
            self.emit("    clz r0, r0")
            return

        elif func_name == "rbit":
            # rbit(val) -> bit-reversed value (Cortex-M3+)
            if len(args) != 1:
                raise CodeGenError("rbit takes 1 argument")
            self.gen_expr(args[0])
            self.emit("    rbit r0, r0")
            return

        elif func_name == "rev":
            # rev(val) -> byte-reversed value (big-endian swap)
            if len(args) != 1:
                raise CodeGenError("rev takes 1 argument")
            self.gen_expr(args[0])
            self.emit("    rev r0, r0")
            return

        elif func_name == "rev16":
            # rev16(val) -> halfword byte swap
            if len(args) != 1:
                raise CodeGenError("rev16 takes 1 argument")
            self.gen_expr(args[0])
            self.emit("    rev16 r0, r0")
            return

        # Python builtins for iteration and reduction
        elif func_name == "sum":
            # sum(iterable) -> total
            # For arrays: sum elements, for range: use formula
            self.gen_builtin_sum(args)
            return

        elif func_name == "any":
            # any(iterable) -> True if any element is truthy
            self.gen_builtin_any(args)
            return

        elif func_name == "all":
            # all(iterable) -> True if all elements are truthy
            self.gen_builtin_all(args)
            return

        elif func_name == "reversed":
            # reversed(list) -> reversed list (in-place for now)
            self.gen_builtin_reversed(args)
            return

        elif func_name == "sorted":
            # sorted(array) -> sorted array (in-place)
            self.gen_builtin_sorted(args)
            return

        # Math builtins - dispatch to lib/math.py functions
        elif func_name == "sqrt":
            # Integer square root
            self.gen_expr(args[0])
            self.emit("    bl isqrt")
            return

        elif func_name == "abs":
            # Absolute value
            self.gen_expr(args[0])
            self.emit("    bl abs_int")
            return

        elif func_name == "pow":
            # Integer power: pow(base, exp)
            self.gen_expr(args[1])
            self.emit("    push {r0}")
            self.gen_expr(args[0])
            self.emit("    pop {r1}")
            self.emit("    bl pow_int")
            return

        elif func_name == "min":
            # min of two integers
            self.gen_expr(args[1])
            self.emit("    push {r0}")
            self.gen_expr(args[0])
            self.emit("    pop {r1}")
            self.emit("    bl min_int")
            return

        elif func_name == "max":
            # max of two integers
            self.gen_expr(args[1])
            self.emit("    push {r0}")
            self.gen_expr(args[0])
            self.emit("    pop {r1}")
            self.emit("    bl max_int")
            return

        elif func_name == "clamp":
            # clamp(x, lo, hi)
            self.gen_expr(args[2])
            self.emit("    push {r0}")
            self.gen_expr(args[1])
            self.emit("    push {r0}")
            self.gen_expr(args[0])
            self.emit("    pop {r1}")
            self.emit("    pop {r2}")
            self.emit("    bl clamp")
            return

        elif func_name == "sign":
            # sign(x) -> -1, 0, or 1
            self.gen_expr(args[0])
            self.emit("    bl sign")
            return

        elif func_name == "gcd":
            # Greatest common divisor
            self.gen_expr(args[1])
            self.emit("    push {r0}")
            self.gen_expr(args[0])
            self.emit("    pop {r1}")
            self.emit("    bl gcd")
            return

        elif func_name == "lcm":
            # Least common multiple
            self.gen_expr(args[1])
            self.emit("    push {r0}")
            self.gen_expr(args[0])
            self.emit("    pop {r1}")
            self.emit("    bl lcm")
            return

        elif func_name == "sin":
            # Sine in degrees (returns 16.16 fixed-point)
            self.gen_expr(args[0])
            self.emit("    bl sin_deg")
            return

        elif func_name == "cos":
            # Cosine in degrees (returns 16.16 fixed-point)
            self.gen_expr(args[0])
            self.emit("    bl cos_deg")
            return

        elif func_name == "tan":
            # Tangent in degrees (returns 16.16 fixed-point)
            self.gen_expr(args[0])
            self.emit("    bl tan_deg")
            return

        elif func_name == "rand":
            # Random integer (0 to INT_MAX)
            self.emit("    bl rand")
            return

        elif func_name == "randint":
            # Random integer in range [lo, hi]
            self.gen_expr(args[1])
            self.emit("    push {r0}")
            self.gen_expr(args[0])
            self.emit("    pop {r1}")
            self.emit("    bl rand_range")
            return

        elif func_name == "srand":
            # Set random seed
            self.gen_expr(args[0])
            self.emit("    bl srand")
            return

        elif func_name == "distance":
            # Distance between two points
            self.gen_expr(args[3])
            self.emit("    push {r0}")
            self.gen_expr(args[2])
            self.emit("    push {r0}")
            self.gen_expr(args[1])
            self.emit("    push {r0}")
            self.gen_expr(args[0])
            self.emit("    pop {r1}")
            self.emit("    pop {r2}")
            self.emit("    pop {r3}")
            self.emit("    bl distance")
            return

        # Check if this is an indirect call through a local variable (function pointer)
        is_indirect = func_name in self.ctx.locals

        # ARM AAPCS: r0-r3 for first 4 args, rest on stack
        num_stack_args = max(0, len(args) - 4)

        if num_stack_args > 0:
            # Push arguments 5+ onto stack in reverse order (rightmost first)
            for arg in reversed(args[4:]):
                self.gen_expr(arg)
                self.emit("    push {r0}")

        # Push first 4 args in reverse order, then pop to r0-r3
        first_four = args[:4]
        for arg in reversed(first_four):
            self.gen_expr(arg)
            self.emit("    push {r0}")

        for i in range(len(first_four)):
            self.emit(f"    pop {{r{i}}}")

        if is_indirect:
            # Load function pointer from local variable and call indirectly
            var = self.ctx.locals[func_name]
            self.emit_load_local("r4", var.offset)
            self.emit("    blx r4")
        else:
            self.emit(f"    bl {func_name}")

        # Clean up stack args after call
        if num_stack_args > 0:
            stack_cleanup = num_stack_args * 4
            if stack_cleanup <= 508:
                self.emit(f"    add sp, sp, #{stack_cleanup}")
            else:
                self.emit(f"    add.w sp, sp, #{stack_cleanup}")

    def gen_indirect_call(self, func_expr: Expr, args: list[Expr]) -> None:
        """Generate an indirect function call through a function pointer."""
        # AAPCS calling convention: first 4 args in r0-r3, rest on stack
        num_args = len(args)
        num_stack_args = max(0, num_args - 4)

        # Push arguments beyond the first 4 onto stack (in reverse order)
        if num_stack_args > 0:
            for arg in reversed(args[4:]):
                self.gen_expr(arg)
                self.emit("    push {r0}")

        # Evaluate arguments r0-r3 and save them
        first_four = args[:4]
        for arg in reversed(first_four):
            self.gen_expr(arg)
            self.emit("    push {r0}")

        # Now evaluate the function pointer expression
        # We need to save r4 since we'll use it for the function pointer
        self.emit("    push {r4}")
        self.gen_expr(func_expr)
        self.emit("    mov r4, r0")  # r4 = function pointer

        # Pop arguments into r0-r3
        for i in range(len(first_four)):
            self.emit(f"    pop {{r{i}}}")

        # Call through function pointer using blx
        self.emit("    blx r4")

        # Restore r4
        self.emit("    push {r0}")  # Save return value
        self.emit("    ldr r4, [sp, #4]")  # Get old r4 from stack
        self.emit("    add sp, sp, #4")  # Remove old r4
        self.emit("    pop {r0}")  # Restore return value

        # Clean up stack arguments
        if num_stack_args > 0:
            stack_cleanup = num_stack_args * 4
            if stack_cleanup <= 508:
                self.emit(f"    add sp, sp, #{stack_cleanup}")
            else:
                self.emit(f"    add.w sp, sp, #{stack_cleanup}")

    def gen_builtin_print(self, args: list[Expr], kwargs: dict = None) -> None:
        """Generate print() built-in - auto-detects type and prints."""
        if kwargs is None:
            kwargs = {}

        # Get sep and end parameters (default: sep=" ", end="\n")
        sep = " "
        end = "\n"
        if 'sep' in kwargs:
            if isinstance(kwargs['sep'], StringLiteral):
                sep = kwargs['sep'].value
        if 'end' in kwargs:
            if isinstance(kwargs['end'], StringLiteral):
                end = kwargs['end'].value

        for i, arg in enumerate(args):
            if i > 0 and sep:
                # Print separator between args
                if len(sep) == 1:
                    self.emit(f"    movs r0, #{ord(sep)}")
                    self.emit("    bl uart_putc")
                else:
                    label = self.add_string(sep)
                    self.emit(f"    ldr r0, ={label}")
                    self.emit("    bl print_str")

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

        # Print end string
        if end:
            if len(end) == 1:
                self.emit(f"    movs r0, #{ord(end)}")
                self.emit("    bl uart_putc")
            else:
                label = self.add_string(end)
                self.emit(f"    ldr r0, ={label}")
                self.emit("    bl print_str")

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
                        self.emit_load_local("r0", var.offset)
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

    def gen_builtin_sum(self, args: list[Expr]) -> None:
        """Generate sum() built-in - sum elements of array."""
        if len(args) < 1:
            raise CodeGenError("sum() takes at least 1 argument")

        arg = args[0]

        # Check if it's an array we know the size of
        if isinstance(arg, Identifier):
            var_type = None
            if arg.name in self.ctx.locals:
                var_type = self.ctx.locals[arg.name].var_type
            else:
                var_type = self.global_var_types.get(arg.name)

            if isinstance(var_type, ArrayType):
                size = var_type.size
                elem_size = self.get_type_size(var_type.element_type)

                # Generate loop to sum elements
                self.gen_expr(arg)  # Get array address in r0
                self.emit("    mov r4, r0")  # r4 = array base
                self.emit("    movs r5, #0")  # r5 = sum
                self.emit(f"    movs r6, #{size}")  # r6 = count

                loop_label = self.ctx.new_label("sum_loop")
                done_label = self.ctx.new_label("sum_done")

                self.emit(f"{loop_label}:")
                self.emit("    cmp r6, #0")
                self.emit(f"    beq {done_label}")

                # Load element based on size
                if elem_size == 1:
                    self.emit("    ldrb r0, [r4]")
                elif elem_size == 2:
                    self.emit("    ldrh r0, [r4]")
                else:
                    self.emit("    ldr r0, [r4]")

                self.emit("    add r5, r5, r0")
                self.emit(f"    add r4, r4, #{elem_size}")
                self.emit("    sub r6, r6, #1")
                self.emit(f"    b {loop_label}")

                self.emit(f"{done_label}:")
                self.emit("    mov r0, r5")
                return

        raise CodeGenError("sum() requires an array with known size")

    def gen_builtin_any(self, args: list[Expr]) -> None:
        """Generate any() built-in - True if any element is truthy."""
        if len(args) != 1:
            raise CodeGenError("any() takes exactly 1 argument")

        arg = args[0]

        if isinstance(arg, Identifier):
            var_type = None
            if arg.name in self.ctx.locals:
                var_type = self.ctx.locals[arg.name].var_type
            else:
                var_type = self.global_var_types.get(arg.name)

            if isinstance(var_type, ArrayType):
                size = var_type.size
                elem_size = self.get_type_size(var_type.element_type)

                self.gen_expr(arg)
                self.emit("    mov r4, r0")  # r4 = array base
                self.emit(f"    movs r6, #{size}")  # r6 = count

                loop_label = self.ctx.new_label("any_loop")
                found_label = self.ctx.new_label("any_found")
                done_label = self.ctx.new_label("any_done")

                self.emit(f"{loop_label}:")
                self.emit("    cmp r6, #0")
                self.emit(f"    beq {done_label}")

                if elem_size == 1:
                    self.emit("    ldrb r0, [r4]")
                elif elem_size == 2:
                    self.emit("    ldrh r0, [r4]")
                else:
                    self.emit("    ldr r0, [r4]")

                self.emit("    cmp r0, #0")
                self.emit(f"    bne {found_label}")
                self.emit(f"    add r4, r4, #{elem_size}")
                self.emit("    sub r6, r6, #1")
                self.emit(f"    b {loop_label}")

                self.emit(f"{found_label}:")
                self.emit("    movs r0, #1")
                self.emit(f"    b {done_label}_end")

                self.emit(f"{done_label}:")
                self.emit("    movs r0, #0")
                self.emit(f"{done_label}_end:")
                return

        raise CodeGenError("any() requires an array with known size")

    def gen_builtin_all(self, args: list[Expr]) -> None:
        """Generate all() built-in - True if all elements are truthy."""
        if len(args) != 1:
            raise CodeGenError("all() takes exactly 1 argument")

        arg = args[0]

        if isinstance(arg, Identifier):
            var_type = None
            if arg.name in self.ctx.locals:
                var_type = self.ctx.locals[arg.name].var_type
            else:
                var_type = self.global_var_types.get(arg.name)

            if isinstance(var_type, ArrayType):
                size = var_type.size
                elem_size = self.get_type_size(var_type.element_type)

                self.gen_expr(arg)
                self.emit("    mov r4, r0")  # r4 = array base
                self.emit(f"    movs r6, #{size}")  # r6 = count

                loop_label = self.ctx.new_label("all_loop")
                false_label = self.ctx.new_label("all_false")
                done_label = self.ctx.new_label("all_done")

                self.emit(f"{loop_label}:")
                self.emit("    cmp r6, #0")
                self.emit(f"    beq {done_label}")

                if elem_size == 1:
                    self.emit("    ldrb r0, [r4]")
                elif elem_size == 2:
                    self.emit("    ldrh r0, [r4]")
                else:
                    self.emit("    ldr r0, [r4]")

                self.emit("    cmp r0, #0")
                self.emit(f"    beq {false_label}")
                self.emit(f"    add r4, r4, #{elem_size}")
                self.emit("    sub r6, r6, #1")
                self.emit(f"    b {loop_label}")

                self.emit(f"{false_label}:")
                self.emit("    movs r0, #0")
                self.emit(f"    b {done_label}_end")

                self.emit(f"{done_label}:")
                self.emit("    movs r0, #1")
                self.emit(f"{done_label}_end:")
                return

        raise CodeGenError("all() requires an array with known size")

    def gen_builtin_reversed(self, args: list[Expr]) -> None:
        """Generate reversed() - returns pointer to reversed array (in-place)."""
        if len(args) != 1:
            raise CodeGenError("reversed() takes exactly 1 argument")

        arg = args[0]

        if isinstance(arg, Identifier):
            var_type = None
            if arg.name in self.ctx.locals:
                var_type = self.ctx.locals[arg.name].var_type
            else:
                var_type = self.global_var_types.get(arg.name)

            if isinstance(var_type, ArrayType):
                size = var_type.size
                elem_size = self.get_type_size(var_type.element_type)

                self.gen_expr(arg)
                self.emit("    mov r4, r0")  # r4 = start pointer
                self.emit(f"    add r5, r4, #{(size - 1) * elem_size}")  # r5 = end pointer

                loop_label = self.ctx.new_label("rev_loop")
                done_label = self.ctx.new_label("rev_done")

                self.emit(f"{loop_label}:")
                self.emit("    cmp r4, r5")
                self.emit(f"    bge {done_label}")

                # Swap elements at r4 and r5
                if elem_size == 1:
                    self.emit("    ldrb r0, [r4]")
                    self.emit("    ldrb r1, [r5]")
                    self.emit("    strb r1, [r4]")
                    self.emit("    strb r0, [r5]")
                elif elem_size == 2:
                    self.emit("    ldrh r0, [r4]")
                    self.emit("    ldrh r1, [r5]")
                    self.emit("    strh r1, [r4]")
                    self.emit("    strh r0, [r5]")
                else:
                    self.emit("    ldr r0, [r4]")
                    self.emit("    ldr r1, [r5]")
                    self.emit("    str r1, [r4]")
                    self.emit("    str r0, [r5]")

                self.emit(f"    add r4, r4, #{elem_size}")
                self.emit(f"    sub r5, r5, #{elem_size}")
                self.emit(f"    b {loop_label}")

                self.emit(f"{done_label}:")
                self.gen_expr(arg)  # Return original array pointer
                return

        raise CodeGenError("reversed() requires an array with known size")

    def gen_builtin_sorted(self, args: list[Expr]) -> None:
        """Generate sorted() - sorts array in-place using insertion sort."""
        if len(args) != 1:
            raise CodeGenError("sorted() takes exactly 1 argument")

        arg = args[0]

        if isinstance(arg, Identifier):
            var_type = None
            if arg.name in self.ctx.locals:
                var_type = self.ctx.locals[arg.name].var_type
            else:
                var_type = self.global_var_types.get(arg.name)

            if isinstance(var_type, ArrayType):
                size = var_type.size
                elem_size = self.get_type_size(var_type.element_type)

                # Only support int32 arrays for now
                if elem_size != 4:
                    self.emit("    @ Warning: sorted() only supports int32 arrays")
                    self.gen_expr(arg)
                    return

                self.gen_expr(arg)
                self.emit("    mov r4, r0")  # r4 = array base
                self.emit(f"    movs r5, #{size}")  # r5 = length

                # Insertion sort
                outer_label = self.ctx.new_label("sort_outer")
                inner_label = self.ctx.new_label("sort_inner")
                inner_done = self.ctx.new_label("sort_inner_done")
                done_label = self.ctx.new_label("sort_done")

                self.emit("    movs r6, #1")  # i = 1
                self.emit(f"{outer_label}:")
                self.emit("    cmp r6, r5")
                self.emit(f"    bge {done_label}")

                # key = arr[i]
                self.emit("    lsl r0, r6, #2")
                self.emit("    ldr r7, [r4, r0]")  # r7 = key

                # j = i - 1
                self.emit("    sub r8, r6, #1")

                self.emit(f"{inner_label}:")
                self.emit("    cmp r8, #0")
                self.emit(f"    blt {inner_done}")

                # if arr[j] <= key, done
                self.emit("    lsl r0, r8, #2")
                self.emit("    ldr r1, [r4, r0]")  # arr[j]
                self.emit("    cmp r1, r7")
                self.emit(f"    ble {inner_done}")

                # arr[j+1] = arr[j]
                self.emit("    add r2, r8, #1")
                self.emit("    lsl r2, r2, #2")
                self.emit("    str r1, [r4, r2]")

                # j--
                self.emit("    sub r8, r8, #1")
                self.emit(f"    b {inner_label}")

                self.emit(f"{inner_done}:")
                # arr[j+1] = key
                self.emit("    add r0, r8, #1")
                self.emit("    lsl r0, r0, #2")
                self.emit("    str r7, [r4, r0]")

                # i++
                self.emit("    add r6, r6, #1")
                self.emit(f"    b {outer_label}")

                self.emit(f"{done_label}:")
                self.gen_expr(arg)  # Return array pointer
                return

        raise CodeGenError("sorted() requires an array with known size")

    def gen_list_method(self, obj: Expr, method: str, args: list[Expr]) -> None:
        """Generate code for list/array methods like append, pop, etc."""
        var_type = None
        if isinstance(obj, Identifier):
            if obj.name in self.ctx.locals:
                var_type = self.ctx.locals[obj.name].var_type
            else:
                var_type = self.global_var_types.get(obj.name)

        # Check if this is a dynamic list (Array[4, int32] is the list struct)
        is_dynamic_list = (isinstance(var_type, ArrayType) and
                          var_type.size == 4 and
                          hasattr(var_type.element_type, 'name') and
                          var_type.element_type.name == 'int32')

        if method == "append":
            if is_dynamic_list:
                # Dynamic list: call list_push(lst, &val)
                if args:
                    self.gen_expr(args[0])
                    self.emit("    push {r0}")  # Push value onto stack
                    self.emit("    mov r1, sp")  # r1 = address of value
                    self.gen_expr(obj)          # r0 = list pointer
                    self.emit("    bl list_push")
                    self.emit("    add sp, sp, #4")
                return
            self.emit("    @ Warning: append() requires dynamic list")
            self.emit("    movs r0, #0")
            return

        elif method == "pop":
            if is_dynamic_list:
                # Dynamic list: call list_pop
                self.gen_expr(obj)
                self.emit("    bl list_pop")
                # Dereference returned pointer to get value
                self.emit("    cmp r0, #0")
                self.emit("    it ne")
                self.emit("    ldrne r0, [r0]")
                return
            # For static arrays with index argument
            if args and isinstance(var_type, ArrayType):
                self.gen_expr(args[0])  # index in r0
                elem_size = self.get_type_size(var_type.element_type)

                if elem_size == 4:
                    self.emit("    lsl r0, r0, #2")
                elif elem_size == 2:
                    self.emit("    lsl r0, r0, #1")
                elif elem_size != 1:
                    self.emit(f"    ldr r1, ={elem_size}")
                    self.emit("    mul r0, r0, r1")

                self.emit("    push {r0}")
                self.gen_expr(obj)
                self.emit("    pop {r1}")
                self.emit("    add r0, r0, r1")

                if elem_size == 1:
                    self.emit("    ldrb r0, [r0]")
                elif elem_size == 2:
                    self.emit("    ldrh r0, [r0]")
                else:
                    self.emit("    ldr r0, [r0]")
                return

        elif method == "insert":
            if is_dynamic_list and len(args) >= 2:
                # list_insert(lst, index, &elem)
                self.gen_expr(args[1])  # value
                self.emit("    push {r0}")
                self.gen_expr(args[0])  # index
                self.emit("    push {r0}")
                self.gen_expr(obj)      # list
                self.emit("    pop {r1}")   # r1 = index
                self.emit("    add r2, sp, #0")  # r2 = address of value
                self.emit("    bl list_insert")
                self.emit("    add sp, sp, #4")
                return

        elif method == "remove":
            if is_dynamic_list and args:
                # list_remove(lst, index)
                self.gen_expr(args[0])  # index
                self.emit("    push {r0}")
                self.gen_expr(obj)
                self.emit("    pop {r1}")
                self.emit("    bl list_remove")
                return

        elif method == "clear":
            if is_dynamic_list:
                self.gen_expr(obj)
                self.emit("    bl list_clear")
                return
            # Static array: zero out
            if isinstance(var_type, ArrayType):
                size = var_type.size
                elem_size = self.get_type_size(var_type.element_type)
                total_bytes = size * elem_size

                self.gen_expr(obj)
                self.emit("    movs r1, #0")
                self.emit(f"    ldr r2, ={total_bytes}")
                self.emit("    bl memset")
                self.emit("    movs r0, #0")
                return

        elif method == "reverse":
            if is_dynamic_list:
                self.gen_expr(obj)
                self.emit("    bl list_reverse")
                return

        elif method == "len" or method == "__len__":
            if is_dynamic_list:
                # Return lst[1] (length field)
                self.gen_expr(obj)
                self.emit("    ldr r0, [r0, #4]")
                return

        # Fallback
        self.emit(f"    @ Warning: list.{method}() not fully implemented")
        self.emit("    movs r0, #0")

    def gen_dict_method(self, obj: Expr, method: str, args: list[Expr]) -> None:
        """Generate code for dict methods like get, keys, values, items."""
        var_type = None
        if isinstance(obj, Identifier):
            if obj.name in self.ctx.locals:
                var_type = self.ctx.locals[obj.name].var_type
            else:
                var_type = self.global_var_types.get(obj.name)

        if method == "get":
            # dict.get(key, default=None)
            if len(args) >= 1:
                # For now, just do regular dict access
                # A proper implementation would return default on missing key
                self.gen_expr(args[0])  # key
                self.emit("    push {r0}")
                self.gen_expr(obj)
                self.emit("    pop {r1}")
                # Determine key type
                if isinstance(var_type, DictType):
                    if hasattr(var_type.key_type, 'name') and var_type.key_type.name == 'str':
                        self.emit("    bl __pynux_dict_get_str")
                    else:
                        self.emit("    bl __pynux_dict_get_int")
                else:
                    self.emit("    bl __pynux_dict_get_int")
                return

        # For keys(), values(), items() - these need iterator support
        # For now, emit stub
        self.emit(f"    @ Warning: dict.{method}() requires iterator support")
        self.emit("    movs r0, #0")

    def gen_member_access(self, obj: Expr, member: str) -> None:
        """Generate struct field access."""
        # Get object address and type
        var_type = None
        if isinstance(obj, Identifier):
            if obj.name in self.ctx.locals:
                var = self.ctx.locals[obj.name]
                var_type = var.var_type
            else:
                var_type = self.global_var_types.get(obj.name)

        # Check if this is a property access
        if var_type and hasattr(var_type, 'name'):
            class_name = var_type.name
            prop_key = f"{class_name}.{member}"
            if prop_key in self.properties:
                # This is a property - call the getter method
                # First get the object pointer for 'self' parameter
                if isinstance(obj, Identifier):
                    if obj.name in self.ctx.locals:
                        var = self.ctx.locals[obj.name]
                        # Load the pointer to the struct instance
                        self.emit_load_local("r0", var.offset)
                    else:
                        self.emit(f"    ldr r0, ={obj.name}")
                else:
                    self.gen_expr(obj)
                # Call the property getter
                method_name = self.properties[prop_key]
                self.emit(f"    bl {method_name}")
                return

        # Get object address for field access - if the local is a class instance,
        # it stores a pointer that we need to dereference
        if isinstance(obj, Identifier):
            if obj.name in self.ctx.locals:
                var = self.ctx.locals[obj.name]
                if var_type and hasattr(var_type, 'name') and var_type.name in self.structs:
                    # Load pointer to struct instance
                    self.emit_load_local("r0", var.offset)
                else:
                    self.emit(f"    add r0, r7, #{var.offset}")
            else:
                self.emit(f"    ldr r0, ={obj.name}")
        else:
            self.gen_expr(obj)

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
        var_type = None
        if isinstance(obj, Identifier):
            if obj.name in self.ctx.locals:
                var = self.ctx.locals[obj.name]
                var_type = var.var_type
                # If the variable holds a pointer to a struct (class instance),
                # load the pointer first, then add offset
                if var_type and hasattr(var_type, 'name') and var_type.name in self.structs:
                    # Load the pointer value from local variable
                    self.emit_load_local("r0", var.offset)
                else:
                    self.emit(f"    add r0, r7, #{var.offset}")
            else:
                self.emit(f"    ldr r0, ={obj.name}")
                var_type = self.global_var_types.get(obj.name)
        else:
            self.gen_expr(obj)

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
        # Slicing creates a new string/list copy
        # Args: r0=obj, r1=start, r2=end, r3=step

        # Evaluate step first and save
        if step:
            self.gen_expr(step)
        else:
            self.emit("    movs r0, #1")
        self.emit("    push {r0}")  # save step

        # Evaluate end and save
        if end:
            self.gen_expr(end)
        else:
            self.emit("    mov r0, #-1")  # -1 means "to end"
        self.emit("    push {r0}")  # save end

        # Evaluate start and save
        if start:
            self.gen_expr(start)
        else:
            self.emit("    movs r0, #0")
        self.emit("    push {r0}")  # save start

        # Evaluate obj
        self.gen_expr(obj)

        # Now set up args: r0=obj (already), r1=start, r2=end, r3=step
        self.emit("    pop {r1}")  # start
        self.emit("    pop {r2}")  # end
        self.emit("    pop {r3}")  # step
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

    def gen_struct_init(self, struct_name: str, init_fields: dict[str, Expr]) -> None:
        """Generate struct initialization: Point{x=10, y=20}."""
        if struct_name not in self.structs:
            # Check if it's a union
            if struct_name in self.unions:
                self.gen_union_init(struct_name, init_fields)
                return
            raise CodeGenError(f"Unknown struct: {struct_name}")

        struct = self.structs[struct_name]

        # Allocate memory for struct
        self.emit(f"    @ Struct init: {struct_name}")
        self.emit(f"    movs r0, #{struct.total_size}")
        self.emit("    bl malloc")
        self.emit("    push {r0}")

        # Initialize to zero first
        if struct.total_size <= 32:
            self.emit("    movs r1, #0")
            for i in range(0, struct.total_size, 4):
                self.emit("    ldr r2, [sp]")
                self.emit(f"    str r1, [r2, #{i}]")

        # Set specified fields
        for field_name, field_val in init_fields.items():
            # Find field offset
            field_offset = None
            for fname, ftype, foffset in struct.fields:
                if fname == field_name:
                    field_offset = foffset
                    break

            if field_offset is None:
                raise CodeGenError(f"Unknown field {field_name} in {struct_name}")

            # Generate value
            self.gen_expr(field_val)
            self.emit("    ldr r1, [sp]")  # Get struct pointer
            self.emit(f"    str r0, [r1, #{field_offset}]")

        self.emit("    pop {r0}")  # Return struct pointer

    def gen_union_init(self, union_name: str, init_fields: dict[str, Expr]) -> None:
        """Generate union initialization."""
        union = self.unions[union_name]

        # Allocate memory for union (size of largest field)
        self.emit(f"    @ Union init: {union_name}")
        self.emit(f"    movs r0, #{union.total_size}")
        self.emit("    bl malloc")
        self.emit("    push {r0}")

        # Initialize to zero
        if union.total_size <= 32:
            self.emit("    movs r1, #0")
            for i in range(0, union.total_size, 4):
                self.emit("    ldr r2, [sp]")
                self.emit(f"    str r1, [r2, #{i}]")

        # Set the field (all fields are at offset 0 in a union)
        for field_name, field_val in init_fields.items():
            # Verify field exists
            found = False
            for fname, ftype in union.fields:
                if fname == field_name:
                    found = True
                    break
            if not found:
                raise CodeGenError(f"Unknown field {field_name} in union {union_name}")

            self.gen_expr(field_val)
            self.emit("    ldr r1, [sp]")
            self.emit("    str r0, [r1]")  # All union fields at offset 0

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
            self.emit_store_local("r0", loop_var.offset)
        else:
            self.gen_expr(range_args[0])
            self.emit_store_local("r0", loop_var.offset)

        end_var = self.ctx.alloc_local(f"_end_{var}")
        if len(range_args) >= 1:
            self.gen_expr(end_expr)
            self.emit_store_local("r0", end_var.offset)

        # Loop
        start_label = self.ctx.new_label("listcomp")
        end_label = self.ctx.new_label("endlistcomp")
        continue_label = self.ctx.new_label("listcompcont")

        self.emit(f"{start_label}:")
        self.emit_load_local("r0", loop_var.offset)
        self.emit_load_local("r1", end_var.offset)
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
        self.emit_load_local("r0", loop_var.offset)
        self.emit("    add r0, r0, #1")
        self.emit_store_local("r0", loop_var.offset)
        self.emit(f"    b {start_label}")

        self.emit(f"{end_label}:")
        self.emit("    pop {r0}")  # Get list pointer
        self.emit("    add r0, r0, #8")  # Skip header, return pointer to elements

    def gen_lambda(self, params: list[str], body: Expr) -> None:
        """Generate lambda expression as anonymous function (deferred)."""
        # Generate unique function name
        lambda_name = f"__lambda_{self.string_counter}"
        self.string_counter += 1

        # Store lambda for deferred generation
        self.pending_lambdas.append((lambda_name, params, body))

        # Just load the lambda function address - it will be generated later
        self.emit(f"    ldr r0, ={lambda_name}")

    def gen_pending_lambdas(self) -> None:
        """Generate all deferred lambda functions."""
        for lambda_name, params, body in self.pending_lambdas:
            # Save current context
            saved_ctx = self.ctx

            # Create new context for lambda
            self.ctx = FunctionContext(lambda_name)

            # Emit lambda function
            self.emit("")
            self.emit(f"    .global {lambda_name}")
            self.emit(f"    .type {lambda_name}, %function")
            self.emit(f"{lambda_name}:")
            self.emit("    push {r7, lr}")
            self.emit("    mov r7, sp")

            # Reserve space for locals (will be fixed up)
            stack_reserve_idx = len(self.output)
            self.emit("    sub sp, sp, #0  @ placeholder")

            # Store parameters as locals
            for i, param in enumerate(params):
                var = self.ctx.alloc_local(param)
                if i < 4:
                    self.emit(f"    str r{i}, [r7, #{var.offset}]")

            # Generate body expression
            self.gen_expr(body)

            # Return - result is in r0
            self.emit("    mov sp, r7")
            self.emit("    pop {r7, pc}")

            # Fix up stack reservation
            stack_size = (self.ctx.stack_size + 7) & ~7
            if stack_size == 0:
                self.output[stack_reserve_idx] = "    @ no locals"
            elif stack_size <= 508:
                self.output[stack_reserve_idx] = f"    sub sp, sp, #{stack_size}"
            elif stack_size <= 4095:
                self.output[stack_reserve_idx] = f"    sub.w sp, sp, #{stack_size}"
            else:
                self.output[stack_reserve_idx] = f"    ldr r12, ={stack_size}\n    sub sp, sp, r12"

            self.emit(f"    .size {lambda_name}, . - {lambda_name}")
            self.emit("    .ltorg")

            # Restore context
            self.ctx = saved_ctx

        # Clear pending lambdas
        self.pending_lambdas.clear()

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
                    self.emit_store_local("r0", var.offset)

            case Assignment(target=target, value=value, op=op):
                self.gen_assignment(target, value, op)

            case ReturnStmt(value=value):
                # Execute deferred statements in reverse order
                for deferred in reversed(self.ctx.defer_stack):
                    self.gen_stmt(deferred)

                if value is not None:
                    self.gen_expr(value)
                # Epilogue - must pop registers we pushed
                self.emit("    mov sp, r7")
                if self.ctx.is_interrupt:
                    self.emit("    pop {r0-r3, r7, r12, pc}")
                else:
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

            case YieldStmt(value=value):
                self.gen_yield(value)

            case WithStmt(items=items, body=body):
                self.gen_with(items, body)

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
                    self.emit_load_local("r0", var.offset)
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
                self.emit_store_local("r0", var.offset)
            elif target.name in self.global_var_types:
                # Known global variable
                self.emit(f"    ldr r1, ={target.name}")
                self.emit("    str r0, [r1]")
            else:
                # First assignment to new local variable - create it
                var = self.ctx.alloc_local(target.name)
                self.emit_store_local("r0", var.offset)
        elif isinstance(target, IndexExpr):
            self.gen_index_store(target, "r0")
        elif isinstance(target, MemberExpr):
            self.gen_member_store(target, "r0")

    def gen_index_store(self, target: IndexExpr, value_reg: str) -> None:
        """Generate store to array index."""
        self.emit(f"    push {{{value_reg}}}")  # Save value
        self.gen_expr(target.index)

        # Determine element size by getting the type of target.obj
        elem_size = 4  # Default to word
        obj_type = self.get_expr_type(target.obj)
        if isinstance(obj_type, ArrayType):
            elem_size = self.get_type_size(obj_type.element_type)
        elif isinstance(obj_type, PointerType):
            elem_size = self.get_type_size(obj_type.base_type)
        elif isinstance(target.obj, Identifier):
            # Fallback for simple identifiers
            elem_size = self.array_element_sizes.get(target.obj.name, 4)

        # Scale index by element size
        if elem_size == 1:
            pass  # No scaling needed
        elif elem_size == 2:
            self.emit("    lsl r0, r0, #1")
        elif elem_size == 4:
            self.emit("    lsl r0, r0, #2")
        elif elem_size == 8:
            self.emit("    lsl r0, r0, #3")
        elif elem_size == 16:
            self.emit("    lsl r0, r0, #4")
        elif elem_size == 32:
            self.emit("    lsl r0, r0, #5")
        else:
            self.emit(f"    ldr r3, ={elem_size}")
            self.emit("    mul r0, r0, r3")

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
                # Add literal pool dump every 10 elif branches to prevent
                # "offset out of range" errors in large if-elif chains
                if i > 0 and i % 10 == 0:
                    self.emit("    .ltorg")
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
        self.emit_store_local("r0", loop_var.offset)

        # Save end value
        end_var = self.ctx.alloc_local(f"_end_{var}")
        self.gen_expr(end)
        self.emit_store_local("r0", end_var.offset)

        # Save step value
        step_var = self.ctx.alloc_local(f"_step_{var}")
        self.gen_expr(step)
        self.emit_store_local("r0", step_var.offset)

        # Loop start
        self.emit(f"{start_label}:")
        self.emit_load_local("r0", loop_var.offset)
        self.emit_load_local("r1", end_var.offset)
        self.emit("    cmp r0, r1")
        self.emit(f"    bge {end_label}")

        # Body
        for s in body:
            self.gen_stmt(s)

        # Continue label for continue statements
        self.emit(f"{continue_label}:")

        # Increment by step
        self.emit_load_local("r0", loop_var.offset)
        self.emit_load_local("r1", step_var.offset)
        self.emit("    add r0, r0, r1")
        self.emit_store_local("r0", loop_var.offset)
        self.emit(f"    b {start_label}")

        self.emit(f"{end_label}:")

        self.ctx.pop_loop()

    def gen_for_unpack(self, vars: list[str], iterable: Expr, body: list[Stmt]) -> None:
        """Generate for loop with tuple unpacking."""
        # Handle enumerate() specially: for i, x in enumerate(list)
        if isinstance(iterable, CallExpr):
            if isinstance(iterable.func, Identifier):
                if iterable.func.name == "enumerate":
                    self.gen_for_enumerate(vars, iterable.args, body)
                    return
                elif iterable.func.name == "zip":
                    self.gen_for_zip(vars, iterable.args, body)
                    return

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
        self.emit_store_local("r0", iter_var.offset)

        # Get length
        self.emit("    ldr r0, [r0]")  # Assume length at offset 0
        self.emit_store_local("r0", len_var.offset)

        # Initialize index
        self.emit("    movs r0, #0")
        self.emit_store_local("r0", idx_var.offset)

        # Loop start
        self.emit(f"{start_label}:")
        self.emit_load_local("r0", idx_var.offset)
        self.emit_load_local("r1", len_var.offset)
        self.emit("    cmp r0, r1")
        self.emit(f"    bge {end_label}")

        # Unpack tuple element - get tuple at index
        self.emit_load_local("r0", iter_var.offset)
        self.emit_load_local("r1", idx_var.offset)
        self.emit("    lsl r1, r1, #2")
        self.emit("    add r0, r0, r1")
        self.emit("    add r0, r0, #8")  # Skip header
        self.emit("    ldr r0, [r0]")  # Load tuple pointer

        # Unpack into variables
        for i, var in enumerate(loop_vars):
            if i > 0:
                self.emit_load_local("r0", iter_var.offset)
                self.emit_load_local("r1", idx_var.offset)
                self.emit("    lsl r1, r1, #2")
                self.emit("    add r0, r0, r1")
                self.emit("    add r0, r0, #8")
                self.emit("    ldr r0, [r0]")
            self.emit(f"    ldr r1, [r0, #{i * 4}]")
            self.emit_store_local("r1", var.offset)

        # Body
        for s in body:
            self.gen_stmt(s)

        # Continue label
        self.emit(f"{continue_label}:")

        # Increment index
        self.emit_load_local("r0", idx_var.offset)
        self.emit("    add r0, r0, #1")
        self.emit_store_local("r0", idx_var.offset)
        self.emit(f"    b {start_label}")

        self.emit(f"{end_label}:")

        self.ctx.pop_loop()

    def gen_for_enumerate(self, vars: list[str], args: list[Expr], body: list[Stmt]) -> None:
        """Generate for loop with enumerate: for i, x in enumerate(list)."""
        if len(vars) != 2:
            raise CodeGenError("enumerate() requires exactly 2 loop variables")

        idx_name, val_name = vars
        idx_var = self.ctx.alloc_local(idx_name)
        val_var = self.ctx.alloc_local(val_name)

        # Get the iterable and optional start value
        iterable_expr = args[0]
        start_val = args[1] if len(args) > 1 else IntLiteral(0)

        # Allocate internal variables
        iter_var = self.ctx.alloc_local(f"_enum_iter")
        len_var = self.ctx.alloc_local(f"_enum_len")
        internal_idx = self.ctx.alloc_local(f"_enum_idx")

        start_label = self.ctx.new_label("enumfor")
        end_label = self.ctx.new_label("endenumfor")
        continue_label = self.ctx.new_label("enumforcont")

        self.ctx.push_loop(start_label, end_label, continue_label)

        # Evaluate iterable (list pointer)
        self.gen_expr(iterable_expr)
        self.emit_store_local("r0", iter_var.offset)

        # Get list length (at offset 4 in list struct: [data, len, cap, elem_size])
        self.emit("    ldr r0, [r0, #4]")
        self.emit_store_local("r0", len_var.offset)

        # Initialize internal index to 0
        self.emit("    movs r0, #0")
        self.emit_store_local("r0", internal_idx.offset)

        # Initialize user index to start value
        self.gen_expr(start_val)
        self.emit_store_local("r0", idx_var.offset)

        # Loop start
        self.emit(f"{start_label}:")
        self.emit_load_local("r0", internal_idx.offset)
        self.emit_load_local("r1", len_var.offset)
        self.emit("    cmp r0, r1")
        self.emit(f"    bge {end_label}")

        # Load current element: data[idx * elem_size]
        # Assuming int32 list (elem_size = 4)
        self.emit_load_local("r0", iter_var.offset)
        self.emit("    ldr r2, [r0]")  # data pointer
        self.emit_load_local("r1", internal_idx.offset)
        self.emit("    lsl r1, r1, #2")  # * 4
        self.emit("    ldr r0, [r2, r1]")
        self.emit_store_local("r0", val_var.offset)

        # Body
        for s in body:
            self.gen_stmt(s)

        # Continue label
        self.emit(f"{continue_label}:")

        # Increment both indices
        self.emit_load_local("r0", internal_idx.offset)
        self.emit("    add r0, r0, #1")
        self.emit_store_local("r0", internal_idx.offset)

        self.emit_load_local("r0", idx_var.offset)
        self.emit("    add r0, r0, #1")
        self.emit_store_local("r0", idx_var.offset)

        self.emit(f"    b {start_label}")

        self.emit(f"{end_label}:")
        self.ctx.pop_loop()

    def gen_for_zip(self, vars: list[str], args: list[Expr], body: list[Stmt]) -> None:
        """Generate for loop with zip: for a, b in zip(list1, list2)."""
        if len(vars) != len(args):
            raise CodeGenError(f"zip() with {len(args)} lists requires {len(args)} loop variables")

        # Allocate loop variables
        loop_vars = [self.ctx.alloc_local(v) for v in vars]

        # Allocate internal variables for each list
        iter_vars = [self.ctx.alloc_local(f"_zip_iter{i}") for i in range(len(args))]
        len_vars = [self.ctx.alloc_local(f"_zip_len{i}") for i in range(len(args))]
        idx_var = self.ctx.alloc_local("_zip_idx")
        min_len_var = self.ctx.alloc_local("_zip_minlen")

        start_label = self.ctx.new_label("zipfor")
        end_label = self.ctx.new_label("endzipfor")
        continue_label = self.ctx.new_label("zipforcont")

        self.ctx.push_loop(start_label, end_label, continue_label)

        # Evaluate each iterable and get its length
        for i, arg in enumerate(args):
            self.gen_expr(arg)
            self.emit_store_local("r0", iter_vars[i].offset)
            # Get list length
            self.emit("    ldr r0, [r0, #4]")
            self.emit_store_local("r0", len_vars[i].offset)

        # Find minimum length
        self.emit_load_local("r0", len_vars[0].offset)
        for i in range(1, len(args)):
            self.emit_load_local("r1", len_vars[i].offset)
            self.emit("    cmp r0, r1")
            self.emit("    it gt")
            self.emit("    movgt r0, r1")
        self.emit_store_local("r0", min_len_var.offset)

        # Initialize index to 0
        self.emit("    movs r0, #0")
        self.emit_store_local("r0", idx_var.offset)

        # Loop start
        self.emit(f"{start_label}:")
        self.emit_load_local("r0", idx_var.offset)
        self.emit_load_local("r1", min_len_var.offset)
        self.emit("    cmp r0, r1")
        self.emit(f"    bge {end_label}")

        # Load element from each list
        for i in range(len(args)):
            self.emit_load_local("r0", iter_vars[i].offset)
            self.emit("    ldr r2, [r0]")  # data pointer
            self.emit_load_local("r1", idx_var.offset)
            self.emit("    lsl r1, r1, #2")  # * 4
            self.emit("    ldr r0, [r2, r1]")
            self.emit_store_local("r0", loop_vars[i].offset)

        # Body
        for s in body:
            self.gen_stmt(s)

        # Continue label
        self.emit(f"{continue_label}:")

        # Increment index
        self.emit_load_local("r0", idx_var.offset)
        self.emit("    add r0, r0, #1")
        self.emit_store_local("r0", idx_var.offset)
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
                    self.emit_store_local("r1", bind_var.offset)

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
                    self.emit_store_local("r0", var.offset)
                else:
                    # Allocate new local
                    var = self.ctx.alloc_local(target)
                    self.emit_store_local("r0", var.offset)
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
                    self.emit_store_local("r0", var.offset)
                else:
                    var = self.ctx.alloc_local(target)
                    self.emit_store_local("r0", var.offset)

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
        self.emit_store_local("r0", error_var.offset)

        # Execute try body
        for s in try_body:
            self.gen_stmt(s)

        # Check if error occurred
        self.emit_load_local("r0", error_var.offset)
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
                self.emit_load_local("r0", error_var.offset)
                self.emit_store_local("r0", exc_var.offset)
            for s in handler.body:
                self.gen_stmt(s)
            # Clear error flag after handling
            self.emit("    movs r0, #0")
            self.emit_store_local("r0", error_var.offset)
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

    def gen_yield(self, value: Optional[Expr]) -> None:
        """Generate yield statement for generators."""
        # Simple implementation: generators are not true coroutines
        # Instead, we store the yielded value in a generator state object
        # and return to the caller

        if value:
            self.gen_expr(value)
        else:
            self.emit("    movs r0, #0")

        # Store value in generator state
        self.emit("    @ yield value in r0")
        # For now, just store in a global generator state
        # A proper implementation would use a state machine
        self.emit("    ldr r1, =__generator_value")
        self.emit("    str r0, [r1]")

        # Set generator state to "yielded"
        self.emit("    ldr r1, =__generator_state")
        self.emit("    movs r0, #1")  # 1 = yielded
        self.emit("    str r0, [r1]")

        # Return to caller (generator will be resumed later)
        self.emit("    mov sp, r7")
        self.emit("    pop {r7, pc}")

    def gen_with(self, items: list, body: list) -> None:
        """Generate with statement for context managers."""
        # For each context manager:
        # 1. Evaluate the expression
        # 2. Call __enter__ method
        # 3. Store result in variable (if 'as' clause present)
        # 4. Execute body
        # 5. Call __exit__ method (even if exception)

        exit_info = []  # Store (context_manager_type, item) for __exit__ calls

        for item in items:
            # Evaluate context expression and determine type
            class_name = None
            if isinstance(item.context, CallExpr):
                # Constructor call like File("name")
                if isinstance(item.context.func, Identifier):
                    if item.context.func.name in self.structs:
                        class_name = item.context.func.name
            elif isinstance(item.context, Identifier):
                # Variable reference
                if item.context.name in self.ctx.locals:
                    var_type = self.ctx.locals[item.context.name].var_type
                    if var_type is not None:
                        type_name = getattr(var_type, 'name', str(var_type))
                        if type_name in self.structs:
                            class_name = type_name

            self.gen_expr(item.context)
            self.emit("    push {r0}")  # Save context manager

            # Call __enter__ method
            self.emit("    @ with: call __enter__")
            if class_name:
                enter_func = f"{class_name}___enter__"
                self.emit(f"    bl {enter_func}")
            else:
                # Fallback to generic runtime function
                self.emit("    ldr r0, [sp]")
                self.emit("    bl __pynux_context_enter")

            # Store result in variable if 'as' clause
            if item.var:
                var = self.ctx.alloc_local(item.var)
                self.emit_store_local("r0", var.offset)

            exit_info.append((class_name, item))

        # Execute body
        for s in body:
            self.gen_stmt(s)

        # Call __exit__ for each context manager (in reverse order)
        for class_name, item in reversed(exit_info):
            self.emit("    @ with: call __exit__")
            self.emit("    pop {r0}")  # Get context manager
            if class_name:
                exit_func = f"{class_name}___exit__"
                self.emit(f"    bl {exit_func}")
            else:
                self.emit("    bl __pynux_context_exit")

    # -------------------------------------------------------------------------
    # Declaration generation
    # -------------------------------------------------------------------------

    def gen_function(self, func: FunctionDef) -> None:
        """Generate code for a function."""
        self.ctx = FunctionContext(func.name)
        self.defined_funcs.add(func.name)

        # Check for @interrupt decorator
        is_interrupt = "interrupt" in func.decorators
        self.ctx.is_interrupt = is_interrupt

        # Create locals for parameters
        for i, param in enumerate(func.params):
            var = self.ctx.alloc_local(param.name, 4, param.param_type)

        self.emit("")
        self.emit(f"    .global {func.name}")
        if is_interrupt:
            self.emit(f"    .type {func.name}, %function")
            self.emit(f"    @ Interrupt handler - save all caller-saved registers")
            self.emit(f"{func.name}:")
            self.emit("    push {r0-r3, r7, r12, lr}")
            self.emit("    mov r7, sp")
        else:
            self.emit(f"    .type {func.name}, %function")
            self.emit(f"{func.name}:")
            self.emit("    push {r7, lr}")
            self.emit("    mov r7, sp")

        # Reserve space for locals (will be adjusted later)
        stack_reserve_idx = len(self.output)
        self.emit("    @ STACK_RESERVE")

        # Store parameters to stack
        # First 4 args come in r0-r3, rest are on stack above saved frame
        for i, param in enumerate(func.params):
            var = self.ctx.locals[param.name]
            if i < 4:
                self.emit_store_local(f"r{i}", var.offset)
            else:
                # Stack args: [r7+8] = arg5, [r7+12] = arg6, etc.
                stack_offset = 8 + (i - 4) * 4
                self.emit(f"    ldr r0, [r7, #{stack_offset}]")
                self.emit_store_local("r0", var.offset)

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
            if is_interrupt:
                self.emit("    pop {r0-r3, r7, r12, pc}")
            else:
                self.emit("    pop {r7, pc}")

        # Fix up stack reservation
        stack_size = (self.ctx.stack_size + 7) & ~7  # Align to 8
        if stack_size == 0:
            self.output[stack_reserve_idx] = "    @ no locals"
        elif stack_size <= 508:
            self.output[stack_reserve_idx] = f"    sub sp, sp, #{stack_size}"
        elif stack_size <= 4095:
            # Use wide encoding for medium values
            self.output[stack_reserve_idx] = f"    sub.w sp, sp, #{stack_size}"
        else:
            # Large stack: need to load value first
            self.output[stack_reserve_idx] = f"    ldr r12, ={stack_size}\n    sub sp, sp, r12"

        self.emit(f"    .size {func.name}, . - {func.name}")
        # Add literal pool after each function
        self.emit("    .ltorg")

    def gen_class(self, cls: ClassDef) -> None:
        """Generate code for a class definition."""
        # Handle class inheritance - inherit fields from parent classes
        fields = []
        offset = 0

        # First, copy fields from parent classes
        for base_name in cls.bases:
            if base_name in self.structs:
                parent = self.structs[base_name]
                for field_name, field_type, field_offset in parent.fields:
                    fields.append((field_name, field_type, offset + field_offset))
                offset += parent.total_size
                # Align to 4 bytes
                offset = (offset + 3) & ~3

        # Then add this class's own fields
        for field in cls.fields:
            size = self.get_type_size(field.field_type)
            fields.append((field.name, field.field_type, offset))
            offset += size
            # Align to 4 bytes
            offset = (offset + 3) & ~3

        self.structs[cls.name] = StructInfo(cls.name, fields, offset)

        # Store parent class for method resolution
        if cls.bases:
            self.class_bases[cls.name] = cls.bases[0]  # Single inheritance for now

        # Generate methods
        for method in cls.methods:
            # Check for decorators
            is_static = "staticmethod" in method.decorators
            is_classmethod = "classmethod" in method.decorators
            is_property = "property" in method.decorators

            # Rename method to include class name
            method_name = f"{cls.name}_{method.name}"

            # Handle self/cls parameter based on decorator
            if is_static:
                # Static method - no self parameter
                pass
            elif is_classmethod:
                # Class method - 'cls' as first parameter
                if not method.params or method.params[0].name != "cls":
                    cls_param = Parameter("cls", Type(cls.name))
                    method.params.insert(0, cls_param)
            else:
                # Regular method - 'self' as first parameter
                if not method.params or method.params[0].name != "self":
                    self_param = Parameter("self", Type(cls.name))
                    method.params.insert(0, self_param)

            # For @property, also generate getter name without underscore
            if is_property:
                # Store property info for later access
                self.properties[f"{cls.name}.{method.name}"] = method_name

            # Save original name and generate
            orig_name = method.name
            method.name = method_name
            self.gen_function(method)
            method.name = orig_name

    def gen_union(self, union_def: UnionDef) -> None:
        """Register a union definition - all fields share same memory at offset 0."""
        # Find the largest field size
        max_size = 0
        fields = []

        for field_name, field_type in union_def.fields:
            size = self.get_type_size(field_type)
            if size > max_size:
                max_size = size
            fields.append((field_name, field_type))

        # Align to 4 bytes
        max_size = (max_size + 3) & ~3

        self.unions[union_def.name] = UnionInfo(union_def.name, fields, max_size)

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
                # Check for @packed decorator
                if 'packed' in decl.decorators:
                    self.packed_structs.add(decl.name)
                self.gen_class(decl)
            elif isinstance(decl, UnionDef):
                # Register union
                self.gen_union(decl)

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
                case UnionDef():
                    pass  # Already processed
                case VarDecl():
                    pass  # Already collected

        # Generate any pending lambda functions
        self.gen_pending_lambdas()

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
                    elif isinstance(var.value, CastExpr):
                        # Handle cast of integer literal (e.g., cast[Ptr[...]](0xE000E010))
                        if isinstance(var.value.expr, IntLiteral):
                            self.emit(f"    .long {var.value.expr.value}")
                        else:
                            self.emit(f"    .space {size}")
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
