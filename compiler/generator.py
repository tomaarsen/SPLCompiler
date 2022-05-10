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
    IfElseNode,
    Node,
    Op1Node,
    Op2Node,
    ReturnNode,
    SPLNode,
    StmtAssNode,
    StmtNode,
    VarDeclNode,
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


class GeneratorYielder(YieldVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.variables = {
            "global": [],
            "arguments": [],
            "local": [],
        }
        self.if_else_counter = 0
        self.while_counter = 0

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

        # Place the local variables on the stack
        for var_decl in node.var_decl:
            yield from self.visit(var_decl, *args, in_func=True, **kwargs)

        # Store them locally
        if node.var_decl:
            yield Line(Instruction.STML, 1, len(node.var_decl))

        for stmt in node.stmt:
            yield from self.visit(stmt, *args, in_main=node.id.text == "main", **kwargs)

        # Remove the function and local arguments again
        self.variables["arguments"].clear()
        self.variables["local"].clear()

    def visit_VarDeclNode(self, node: VarDeclNode, *args, in_func=False, **kwargs):
        if in_func:
            # Local variable definition
            # No need to pass the in_func any deeper
            yield from self.visit(node.exp, *args, **kwargs)

            self.variables["local"].append(node.id)

        else:
            # Global variable definition
            # TODO
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
            pass

        else:
            # TODO: Implement a backup error saying that there is no such variable,
            # should never occur.
            raise Exception(f"Variable {node.id.id.text!r} does not exist")

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
            yield Line(Instruction.RET, comment=str(node))

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
            # Boolean operations
            case Token(type=Type.AND):
                yield Line(Instruction.AND, comment=str(node))
            case Token(type=Type.OR):
                yield Line(Instruction.OR, comment=str(node))

            # Arithmetic operations
            case Token(type=Type.PLUS):
                yield Line(Instruction.ADD, comment=str(node))
            case Token(type=Type.MINUS):
                yield Line(Instruction.SUB, comment=str(node))
            case Token(type=Type.STAR):
                yield Line(Instruction.MUL, comment=str(node))
            case Token(type=Type.SLASH):
                yield Line(Instruction.DIV, comment=str(node))
            case Token(type=Type.PERCENT):
                yield Line(Instruction.MOD, comment=str(node))

            # Equality
            case Token(type=Type.DEQUALS):
                yield Line(Instruction.EQ, comment=str(node))
            case Token(type=Type.NEQ):
                yield Line(Instruction.NE, comment=str(node))
            case Token(type=Type.LT):
                yield Line(Instruction.LT, comment=str(node))
            case Token(type=Type.GT):
                yield Line(Instruction.GT, comment=str(node))
            case Token(type=Type.LEQ):
                yield Line(Instruction.LE, comment=str(node))
            case Token(type=Type.GEQ):
                yield Line(Instruction.GE, comment=str(node))

            case _:
                raise NotImplementedError(repr(node.operator))

    def visit_Op1Node(self, node: Op1Node, *args, **kwargs):
        # First recurse into the child
        yield from self.visit(node.operand, *args, **kwargs)

        match node.operator:
            case Token(type=Type.NOT):
                yield Line(Instruction.NOT, comment=str(node))
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
                # TODO: Implement global variables
                if node in self.variables["local"]:
                    # Local variables are positive relative to MP, starting from 1
                    index = self.variables["local"].index(node)
                    offset = index + 1
                    yield Line(Instruction.LDL, offset, comment=str(node))

                elif node in self.variables["arguments"]:
                    # Index 0 means we need to get the first argument, so the furthest away one
                    # The last argument is at -2
                    index = self.variables["arguments"].index(node)
                    offset = index - 1 - len(self.variables["arguments"])
                    # Load the function argument using the offset from MP
                    yield Line(Instruction.LDL, offset, comment=str(node))

                elif node in self.variables["global"]:
                    pass
                else:
                    # TODO: Implement a backup error saying that there is no such variable,
                    # should never occur.
                    raise Exception(f"Variable {node.text!r} does not exist")

            case Token(type=Type.DIGIT):
                # TODO: Disallow overflow somewhere?
                yield Line(Instruction.LDC, int(node.text), comment=str(node))

            case _:
                raise NotImplementedError(repr(node))
