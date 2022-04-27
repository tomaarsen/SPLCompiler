from dataclasses import dataclass, field
from enum import Enum, auto
from pprint import pprint
from typing import Tuple

from compiler.token import Token
from compiler.tree.visitor import YieldVisitor
from compiler.type import Type

from compiler.tree.tree import (  # isort:skip
    FunCallNode,
    FunDeclNode,
    Node,
    Op1Node,
    Op2Node,
    ReturnNode,
    SPLNode,
    StmtNode,
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
    SUB = auto()  # Substitution
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
        comment = f" // {self.comment}" if self.comment else ""
        return label + instruction + comment


class GeneratorYielder(YieldVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.variables = {
            "global": [],
            "arguments": [],
            "local": [],
        }

    def visit_SPLNode(self, node: SPLNode, *args, **kwargs):
        yield Line(Instruction.BRA, "main")
        yield from self.visit_children(node, *args, **kwargs)

    def visit_FunDeclNode(self, node: FunDeclNode, *args, **kwargs):
        # Mark a label from this point onwards
        yield Line(label=node.id)
        # Link to conveniently move MP and SP
        yield Line(Instruction.LINK, len(node.var_decl))
        # Set the function arguments, this is the order that they are above the MP
        if node.args:
            self.variables["arguments"] = node.args.items

        for var_decl in node.var_decl:
            yield from self.visit(var_decl, *args, **kwargs)

        for stmt in node.stmt:
            yield from self.visit(stmt, *args, in_main=node.id.text == "main", **kwargs)

        # Remove the function arguments again
        self.variables["arguments"].clear()

    def visit_VarDeclNode(self, node: Node | Token, *args, **kwargs):
        """
        If in function, then:
        link 1
        recurse into expression
        otherwise:
        TODO
        """
        yield from []

    # def visit_CommaListNode(self, node: Node | Token, *args, **kwargs):
    #     yield from []

    def visit_FunCallNode(self, node: FunCallNode, *args, **kwargs):
        # First handle the function call arguments
        if node.args:
            yield from self.visit(node.args, *args, **kwargs)

        if node.func.text == "print":
            # TODO: Determine type of whats being printed
            # Print as integer
            yield Line(Instruction.TRAP, 0)

            # No need to clean up the stack here, as TRAP already eats
            # up the one element that is being printed
        # TODO: isEmpty
        else:
            # Branch to the function that is being called
            yield Line(Instruction.BSR, node.func.text)

            # Clean up the stack that still has the function call arguments on it
            if node.args:
                yield Line(Instruction.AJS, -len(node.args.items))

            # Place the function return back on the stack
            yield Line(Instruction.LDR, "RR")

    def visit_IfElseNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_WhileNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_StmtAssNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_FieldNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_FunTypeNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    # def visit_StmtNode(self, node: StmtNode, *args, **kwargs):
    #     yield from self.visit_children(node, *args, **kwargs)

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
            yield Line(Instruction.RET)

    def visit_IntTypeNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_CharTypeNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_BoolTypeNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_VoidTypeNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_PolymorphicTypeNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_VariableNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_ListNode(self, node: Node | Token, *args, **kwargs):
        yield from []

    def visit_Op2Node(self, node: Op2Node, *args, **kwargs):
        # First recurse into both children
        yield from self.visit(node.left, *args, **kwargs)
        yield from self.visit(node.right, *args, **kwargs)

        match node.operator:
            case Token(type=Type.AND):
                yield Line(Instruction.AND)
            case Token(type=Type.OR):
                yield Line(Instruction.OR)
            case _:
                raise NotImplementedError(repr(node.operator))

    def visit_Op1Node(self, node: Op1Node, *args, **kwargs):
        # First recurse into the child
        yield from self.visit(node.operand, *args, **kwargs)

        match node.operator:
            case Token(type=Type.NOT):
                yield Line(Instruction.NOT)
            case _:
                raise NotImplementedError(repr(node.operator))

    def visit_Token(self, node: Token, *args, **kwargs):
        match node:
            case Token(type=Type.TRUE):
                # True is encoded as -1
                yield Line(Instruction.LDC, -1)
            case Token(type=Type.FALSE):
                # True is encoded as 0
                yield Line(Instruction.LDC, 0)
            case Token(type=Type.ID):
                # TODO: Implement global and local variables
                # Index 0 means we need to get the first argument, so the furthest away one
                # The last argument is at -2
                index = self.variables["arguments"].index(node)
                offset = index - 1 - len(self.variables["arguments"])
                # Load the function argument using the offset from MP
                yield Line(Instruction.LDL, offset)
            case Token(type=Type.DIGIT):
                # TODO: Disallow overflow somewhere?
                yield Line(Instruction.LDC, int(node.text))
            case _:
                raise NotImplementedError(repr(node))
