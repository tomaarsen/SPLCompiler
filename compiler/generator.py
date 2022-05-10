from dataclasses import dataclass, field
from enum import Enum, auto
from pprint import pprint
from typing import Tuple

from compiler.token import Token
from compiler.tree.visitor import Variable, YieldVisitor
from compiler.type import Type

from compiler.tree.tree import (  # isort:skip
    BoolTypeNode,
    CharTypeNode,
    CommaListNode,
    FieldNode,
    FunCallNode,
    FunDeclNode,
    FunTypeNode,
    IfElseNode,
    IntTypeNode,
    ListNode,
    Node,
    Op1Node,
    Op2Node,
    PolymorphicTypeNode,
    ReturnNode,
    SPLNode,
    StmtAssNode,
    StmtNode,
    VarDeclNode,
    VariableNode,
    VoidTypeNode,
    WhileNode,
)


class Instruction(Enum):
    LDC = auto()  # Load Constant
    LDS = auto()  # Load from Stack
    LDMS = auto()  # Load Multiple from Stack
    STS = auto()  # Store into Stack
    STMS = auto()  # Store Multiple into Stack
    LDSA = auto()  # Load Stack Address
    LDL = auto()  # Load Local
    LDML = auto()  # Load Multiple Local
    STL = auto()  # Store Local
    STML = auto()  # Store Multiple Local
    LDLA = auto()  # Load Local Address
    LDA = auto()  # Load via Address
    LDMA = auto()  # Load Multiple via Address
    LDAA = auto()  # Load Address of Address
    STA = auto()  # Store via Address
    STMA = auto()  # Store Multiple via Address
    LDR = auto()  # Load Register
    LDRR = auto()  # Load Register from Register
    STR = auto()  # Store Register
    SWP = auto()  # Swap values
    SWPR = auto()  # Swap Register
    SWPRR = auto()  # Swap 2 Registers
    AJS = auto()  # Adjust Stack

    ADD = auto()  # Addition
    MUL = auto()  # Multiplication
    SUB = auto()  # Subtraction
    DIV = auto()  # Division
    MOD = auto()  # Modulo
    AND = auto()  # Bitwise AND
    OR = auto()  # Bitwise OR
    XOR = auto()  # Bitwise XOR
    EQ = auto()  # Equality
    NE = auto()  # Non-equality
    LT = auto()  # Less than
    LE = auto()  # Less or equal
    GT = auto()  # Greater than
    GE = auto()  # Greater or equal
    NEG = auto()  # Negation
    NOT = auto()  # Bitwise complement

    BSR = auto()  # Branch to Subroutine
    BRA = auto()  # Branch Always
    BRF = auto()  # Branch on False
    BRT = auto()  # Branch on True
    JSR = auto()  # Jump to Subroutine
    RET = auto()  # Return from Subroutine

    LINK = auto()  # Reserve memory for locals
    UNLINK = auto()  # Free memory for locals
    NOP = auto()  # No operation
    HALT = auto()  # Halt execution
    TRAP = auto()  # Trap to environment function, involves a systemcall:
    """
     0: Pop the topmost element from the stack and print it as an integer.
     1: Pop the topmost element from the stack and print it as a unicode character.
    10: Ask the user for an integer input and push it on the stack.
    11: Ask the user for a unicode character input and push it on the stack.
    12: Ask the user for a sequence of unicode characters input and push the characters on the stack terminated by a null-character.
    20: Pop a null-terminated file name from the stack, open the file for reading and push a file pointer on the stack.
    21: Pop a null-terminated file name from the stack, open the file for writing and push a file pointer on the stack.
    22: Pop a file pointer from the stack, read a character from the file pointed to by the file pointer and push the character on the stack.
    23: Pop a character and a file pointer from the stack, write the character to the file pointed to by the file pointer.
    24: Pop a file pointer from the stack and close the corresponding file.
    """
    ANNOTE = auto()  # Annotate, color used in the GUI

    LDH = auto()  # Load from Heap
    LDMH = auto()  # Load Multiple from Heap
    STH = auto()  # Store into Heap
    STMH = auto()  # Store Multiple into Heap

    def __str__(self) -> str:
        return self.name.lower()


@dataclass
class Line:
    label: str
    instruction: Tuple[str]
    comment: str

    def __init__(
        self, *instruction: Tuple[Instruction | str], label: str = "", comment: str = ""
    ) -> None:
        self.label = label
        self.instruction = instruction
        self.comment = comment

    def __repr__(self) -> str:
        label = f"\n{self.label}:\t" if self.label else "\t"
        instruction = " ".join(str(instruction) for instruction in self.instruction)
        comment = f"\t\t\t; {self.comment}" if self.comment else ""
        return label + instruction + comment


STD_LIB = """
_print_Bool:
	link 0
    ldl -2
	brt _print_Bool_Then

_print_Bool_Else:
	ldc 70			; 'F'
	trap 1			; print('F')
	ldc 97			; 'a'
	trap 1			; print('a')
	ldc 108			; 'l'
	trap 1			; print('l')
	ldc 115			; 's'
	trap 1			; print('s')
	ldc 101			; 'e'
	trap 1			; print('e')
	bra _print_Bool_End

_print_Bool_Then:
	ldc 84			; 'T'
	trap 1			; print('T')
	ldc 114			; 'r'
	trap 1			; print('r')
	ldc 117			; 'u'
	trap 1			; print('u')
	ldc 101			; 'e'
	trap 1			; print('e')

_print_Bool_End:
	unlink
	ret			; return;
"""


class Generator:
    def __init__(self, tree: SPLNode) -> None:
        self.generator_yielder = GeneratorYielder()
        # self.tree = self.add_std_lib(tree)
        self.tree = tree

    def generate(self) -> str:
        ssm_code = "\n".join(
            str(line) for line in self.generator_yielder.visit(self.tree)
        )  # + STD_LIB
        return ssm_code


class GeneratorYielder(YieldVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.variables = {
            "global": {},
            "arguments": {},
            "local": {},
        }
        self.if_else_counter = 0
        self.while_counter = 0
        self.functions = []

    def visit_SPLNode(self, node: SPLNode, *args, **kwargs):
        # yield Line(Instruction.BRA, "main")

        # fun_decls = {}
        # for node in node.body:
        #     match node:
        #         case FunDeclNode():
        #             fun_decls[node.id.text] = node

        #         case VarDeclNode():
        #             yield from self.visit(node, *args, **kwargs)

        var_decls = [node for node in node.body if isinstance(node, VarDeclNode)]

        yield Line(Instruction.LINK, len(var_decls))
        yield Line(Instruction.LDR, "MP")
        yield Line(Instruction.STR, "R5", comment="Globals Pointer (GP)")
        for var_decl in var_decls:
            yield from self.visit(var_decl, *args, **kwargs)
        yield Line(Instruction.STML, 1, len(var_decls))

        fun_decls = {
            node.id.text: node for node in node.body if isinstance(node, FunDeclNode)
        }
        yield from self.visit(fun_decls["main"], *args, **kwargs)
        yield Line(Instruction.HALT)

        while self.functions:
            function = self.functions.pop()
            name = function["name"]
            fun_type = function["type"]
            # TODO: Make print implementations
            if name == "print":
                continue
            fun_decl = fun_decls[name]
            yield from self.visit(fun_decl, *args, fun_type=fun_type, **kwargs)

    def visit_FunDeclNode(self, node: FunDeclNode, *args, fun_type=None, **kwargs):
        # Mark a label from this point onwards
        label = node.id.text + (
            "".join("_" + str(t) for t in fun_type.types) if fun_type else ""
        )
        # print(f"Defining {label}")
        yield Line(label=label)
        # Link to conveniently move MP and SP
        yield Line(Instruction.LINK, len(node.var_decl))
        # Set the function arguments, this is the order that they are above the MP
        if node.args:
            self.variables["arguments"] = {
                token: arg_type
                for token, arg_type in zip(node.args.items, fun_type.types)
            }

        # Place the local variables on the stack
        for var_decl in node.var_decl:
            yield from self.visit(var_decl, *args, in_func=True, **kwargs)

        # pprint(self.variables)

        # Store them locally
        if node.var_decl:
            yield Line(Instruction.STML, 1, len(node.var_decl))

        for stmt in node.stmt:
            yield from self.visit(stmt, *args, in_main=node.id.text == "main", **kwargs)

        # Remove the function and local arguments again
        self.variables["arguments"].clear()
        self.variables["local"].clear()

    def visit_VarDeclNode(self, node: VarDeclNode, *args, in_func=False, **kwargs):
        # No need to pass the in_func any deeper
        exp_type = Variable(None)
        yield from self.visit(node.exp, *args, exp_type=exp_type, **kwargs)

        if in_func:
            # Local variable definition
            self.variables["local"][node.id] = exp_type.var

        else:
            # Global variable definition
            yield Line(Instruction.STH, comment=str(node))
            self.variables["global"][node.id] = exp_type.var

    def visit_FunCallNode(self, node: FunCallNode, *args, exp_type=None, **kwargs):
        # First handle the function call arguments
        self.functions.append({"name": node.func.text, "type": node.type})

        arg_types = []
        if node.args:
            for arg in node.args.items:
                arg_type = Variable(None)
                yield from self.visit(arg, *args, exp_type=arg_type, **kwargs)
                arg_types.append(arg_type.var)

        if node.func.text == "print":
            # Naively determine type of whats being printed
            match arg_types[0]:
                case CharTypeNode():
                    # Print as a character
                    yield Line(Instruction.TRAP, 1, comment=str(node))

                case IntTypeNode():
                    # Print as integer
                    yield Line(Instruction.TRAP, 0, comment=str(node))

                case BoolTypeNode():
                    # Print as integer
                    # yield Line(Instruction.TRAP, 0, comment=str(node))
                    yield Line(Instruction.BSR, "_print_Bool")

                case _:
                    # breakpoint()
                    raise NotImplementedError(
                        f"Printing {arg_types[0]} hasn't been implemented yet"
                    )

            # No need to clean up the stack here, as TRAP already eats
            # up the one element that is being printed
        # TODO: isEmpty
        else:
            # Branch to the function that is being called
            label = node.func.text + "".join("_" + str(t) for t in node.type.types)
            yield Line(Instruction.BSR, label, comment=str(node))

            # Clean up the stack that still has the function call arguments on it
            if node.args:
                yield Line(Instruction.AJS, -len(node.args.items))

            # Place the function return back on the stack
            yield Line(Instruction.LDR, "RR")

            # Set the return value as the expression type, if requested higher
            # on the tree
            if exp_type:
                exp_type.set(node.type.ret_type)

    def visit_IfElseNode(self, node: IfElseNode, *args, **kwargs):
        then_label = f"Then{self.if_else_counter}"
        else_label = f"Else{self.if_else_counter}"
        end_label = f"IfEnd{self.if_else_counter}"
        self.if_else_counter += 1
        # Condition
        yield from self.visit(node.cond)
        if node.else_body:
            # Jump over the else body, if the condition is true
            yield Line(Instruction.BRT, then_label)
            # Execute the else branch
            yield Line(label=else_label)
            for stmt in node.else_body:
                yield from self.visit(stmt)
            # Jump over body
            yield Line(Instruction.BRA, end_label)
        else:
            # Jump over then branch, if there is no else branch to execute
            yield Line(Instruction.BRF, end_label)

        yield Line(label=then_label)
        for stmt in node.body:
            yield from self.visit(stmt)
        yield Line(label=end_label)

    def visit_WhileNode(self, node: WhileNode, *args, **kwargs):
        condition_label = f"WhileCond{self.while_counter}"
        body_label = f"WhileBody{self.while_counter}"
        end_label = f"WhileEnd{self.while_counter}"
        self.while_counter += 1

        # Condition
        yield Line(label=condition_label)
        yield from self.visit(node.cond)
        # Jump over while body if condition is false
        yield Line(Instruction.BRF, end_label)
        # While body
        yield Line(label=body_label)
        for stmt in node.body:
            yield from self.visit(stmt)
        # Jump back to condition
        yield Line(Instruction.BRA, condition_label)
        yield Line(label=end_label)

    def visit_StmtAssNode(self, node: StmtAssNode, *args, **kwargs):
        yield from self.visit(node.exp, *args, **kwargs)

        if node.id.id in self.variables["local"]:
            # Local variables are positive relative to MP, starting from 1
            index = self.variables["local"].index(node.id.id)
            offset = index + 1
            yield Line(Instruction.STL, offset, comment=str(node))

        elif node.id.id in self.variables["arguments"]:
            # Index 0 means we need to get the first argument, so the furthest away one
            # The last argument is at -2
            index = self.variables["arguments"].index(node.id.id)
            offset = index - 1 - len(self.variables["arguments"])
            # Load the function argument using the offset from MP
            yield Line(Instruction.STL, offset, comment=str(node))

        elif node.id.id in self.variables["global"]:
            # Global variables are positive relative to Global Pointer (GP), starting from 1
            index = list(self.variables["global"]).index(node.id.id)
            offset = index + 1

            # Load heap address, and then store the value there
            yield Line(Instruction.LDR, "R5", comment="Load Global Pointer (GP)")
            yield Line(Instruction.LDA, offset, comment="Load Heap address")
            yield Line(Instruction.STA, 0, comment=str(node))

        else:
            # TODO: Implement a backup error saying that there is no such variable,
            # should never occur.
            raise Exception(f"Variable {node.id.id.text!r} does not exist")

    def visit_FieldNode(self, node: FieldNode, *args, **kwargs):
        # TODO
        yield from []

    def visit_FunTypeNode(self, node: FunTypeNode, *args, **kwargs):
        yield from []

    def visit_ReturnNode(self, node: ReturnNode, *args, in_main=False, **kwargs):
        # Recurse into children
        if node.exp:
            yield from self.visit(node.exp, *args, **kwargs)

        # Store return value in RR register, if something was returned
        if node.exp:
            yield Line(Instruction.STR, "RR")
        # Delete local variables
        yield Line(Instruction.UNLINK)
        # Actually return, but only if we're not in main
        if not in_main:
            yield Line(Instruction.RET, comment=str(node))

    def visit_IntTypeNode(self, node: IntTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_CharTypeNode(self, node: CharTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_BoolTypeNode(self, node: BoolTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_VoidTypeNode(self, node: VoidTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_PolymorphicTypeNode(self, node: PolymorphicTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_VariableNode(self, node: VariableNode, *args, **kwargs):
        # TODO
        yield from []

    def visit_ListNode(self, node: ListNode, *args, **kwargs):
        # TODO: Note the distinction between if node.exp exists (then it's a type)
        # and if it doesn't (then it's an empty list)
        yield from []

    def visit_Op2Node(self, node: Op2Node, *args, exp_type=Variable(None), **kwargs):
        # First recurse into both children
        left_exp_type = Variable(None)
        yield from self.visit(node.left, *args, exp_type=left_exp_type, **kwargs)
        yield from self.visit(node.right, *args, **kwargs)

        match node.operator:
            # Boolean operations
            case Token(type=Type.AND):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.AND, comment=str(node))
            case Token(type=Type.OR):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.OR, comment=str(node))

            # Arithmetic operations
            case Token(type=Type.PLUS):
                exp_type.set(IntTypeNode())
                yield Line(Instruction.ADD, comment=str(node))
            case Token(type=Type.MINUS):
                exp_type.set(IntTypeNode())
                yield Line(Instruction.SUB, comment=str(node))
            case Token(type=Type.STAR):
                exp_type.set(IntTypeNode())
                yield Line(Instruction.MUL, comment=str(node))
            case Token(type=Type.SLASH):
                exp_type.set(IntTypeNode())
                yield Line(Instruction.DIV, comment=str(node))
            case Token(type=Type.PERCENT):
                exp_type.set(IntTypeNode())
                yield Line(Instruction.MOD, comment=str(node))

            # Equality
            case Token(type=Type.DEQUALS):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.EQ, comment=str(node))
            case Token(type=Type.NEQ):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.NE, comment=str(node))

            # Arithmetic Equality
            case Token(type=Type.LT):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.LT, comment=str(node))
            case Token(type=Type.GT):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.GT, comment=str(node))
            case Token(type=Type.LEQ):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.LE, comment=str(node))
            case Token(type=Type.GEQ):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.GE, comment=str(node))

            case _:
                raise NotImplementedError(repr(node.operator))

    def visit_Op1Node(self, node: Op1Node, *args, exp_type=Variable(None), **kwargs):
        # First recurse into the child
        yield from self.visit(node.operand, *args, **kwargs)

        match node.operator:
            case Token(type=Type.NOT):
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.NOT, comment=str(node))

            case Token(type=Type.MINUS):
                exp_type.set(IntTypeNode())
                yield Line(Instruction.NEG, comment=str(node))

            case _:
                raise NotImplementedError(repr(node.operator))

    def visit_Token(self, node: Token, *args, exp_type=Variable(None), **kwargs):
        match node:
            case Token(type=Type.TRUE):
                # True is encoded as -1
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.LDC, -1, comment=str(node))

            case Token(type=Type.FALSE):
                # True is encoded as 0
                exp_type.set(BoolTypeNode())
                yield Line(Instruction.LDC, 0, comment=str(node))

            case Token(type=Type.ID):
                # TODO: Implement global variables
                if node in self.variables["local"]:
                    # Local variables are positive relative to MP, starting from 1
                    index = list(self.variables["local"]).index(node)
                    offset = index + 1
                    exp_type.set(self.variables["local"][node])
                    yield Line(Instruction.LDL, offset, comment=str(node))

                elif node in self.variables["arguments"]:
                    # Index 0 means we need to get the first argument, so the furthest away one
                    # The last argument is at -2
                    index = list(self.variables["arguments"]).index(node)
                    offset = index - 1 - len(self.variables["arguments"])
                    # Load the function argument using the offset from MP
                    exp_type.set(self.variables["arguments"][node])
                    yield Line(Instruction.LDL, offset, comment=str(node))

                elif node in self.variables["global"]:
                    # Global variables are positive relative to Global Pointer (GP), starting from 1
                    index = list(self.variables["global"]).index(node)
                    offset = index + 1

                    exp_type.set(self.variables["global"][node])
                    yield Line(
                        Instruction.LDR, "R5", comment="Load Global Pointer (GP)"
                    )
                    yield Line(Instruction.LDA, offset, comment="Load Heap address")
                    yield Line(Instruction.LDH, 0, comment="Load Heap value")

                else:
                    # TODO: Implement a backup error saying that there is no such variable,
                    # should never occur.
                    raise Exception(f"Variable {node.text!r} does not exist")

            case Token(type=Type.DIGIT):
                # TODO: Disallow overflow somewhere?
                exp_type.set(IntTypeNode())
                yield Line(Instruction.LDC, int(node.text), comment=str(node))

            case Token(type=Type.CHARACTER):
                # Get the character range. Can be larger than length 1 if '\\n' etc.
                character = node.text[1:-1]
                # Remove duplicate escaping, i.e. '\\n' -> '\n'
                character = character.encode().decode("unicode_escape")
                exp_type.set(CharTypeNode())
                yield Line(Instruction.LDC, ord(character), comment=str(node))

            case _:
                raise NotImplementedError(repr(node))
