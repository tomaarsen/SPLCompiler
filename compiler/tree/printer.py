from enum import Enum, auto
from typing import Iterator

from compiler.token import Token
from compiler.tree.visitor import NodeYielder
from compiler.type import Type
from compiler.util import operator_precedence, right_associative

from compiler.tree.tree import (  # isort:skip
    BoolTypeNode,
    CharTypeNode,
    CommaListNode,
    ForNode,
    FunCallNode,
    FunDeclNode,
    FunTypeNode,
    IfElseNode,
    IndexNode,
    IntTypeNode,
    ListNode,
    Node,
    Op1Node,
    Op2Node,
    PolymorphicTypeNode,
    ReturnNode,
    StmtAssNode,
    StmtNode,
    TupleNode,
    VarDeclNode,
    VoidTypeNode,
    WhileNode,
    ListAbbrNode,
)

LEFT_ATTACHED_TOKENS = {
    Type.LRB,  # (
    Type.LSB,  # [
    Type.NOT,  # !
    Type.DDOT,  # ..
    Type.STRING,  # Useful for printing strings without additional spaces
    Type.COLON,
}

RIGHT_ATTACHED_TOKENS = {
    Type.COLON,
    Type.RRB,  # )
    Type.RSB,  # ]
    Type.COMMA,
    Type.SEMICOLON,
    Type.HD,
    Type.TL,
    Type.FST,
    Type.SND,
    Type.DDOT,  # ..
}


class PrintingInfo(Enum):
    NOSPACE = auto()
    SPACE = auto()
    NEWLINE = auto()
    # INDENT = auto()
    # UNINDENT = auto()


INDENT = " " * 4


class Printer(NodeYielder):
    def __init__(self) -> None:
        super().__init__()
        self.program = []

    def print(self, tree: Node) -> str:
        # Traverse the tree, collecting Tokens and printing information
        depth = 0
        program = ""
        for token in self.visit(tree):
            if token == PrintingInfo.NEWLINE:
                program += "\n"
            elif token == PrintingInfo.SPACE:
                last_token = token
            elif token == PrintingInfo.NOSPACE:
                while program and program[-1] == " ":
                    program = program[:-1]
            else:
                # Modify depth before this token
                if token.type == Type.RCB:  # }
                    depth -= 1

                # Ensure indentation is correct
                if program and program[-1] == "\n":
                    program += INDENT * depth

                # Modify depth after this token
                if token.type == Type.LCB:  # {
                    depth += 1

                # Remove the last space if this is a tightly bound character, e.g. ';'
                # OR if `token` is the `(` after an `id` (i.e. a function call)
                if (
                    program
                    and program[-1] == " "
                    and last_token != PrintingInfo.SPACE
                    and (
                        token.type in RIGHT_ATTACHED_TOKENS
                        or (
                            last_token
                            and last_token.type == Type.ID
                            and token.type == Type.LRB
                        )
                    )
                ):
                    program = program[:-1]

                # Print this token
                program += token.text

                # Print space that follows this token if applicable
                if token.type not in LEFT_ATTACHED_TOKENS:
                    program += " "

                # Print a newline if applicable
                if token.type in {Type.RCB, Type.LCB, Type.SEMICOLON}:
                    program += "\n"

                last_token = token

        return program.strip()

    def visit_FunDeclNode(self, node: FunDeclNode, **kwargs) -> Iterator[Token]:
        yield node.id
        yield Token("(", Type.LRB)
        if node.args:
            yield from self.visit(node.args)
        yield Token(")", Type.RRB)
        if node.type:
            yield Token("::", Type.DOUBLE_COLON)
            yield from self.visit(node.type)
        yield Token("{", Type.LCB)
        for var_decl in node.var_decl:
            yield from self.visit(var_decl)
        for stmt in node.stmt:
            yield from self.visit(stmt)
        yield Token("}", Type.RCB)
        yield PrintingInfo.NEWLINE

    def visit_VarDeclNode(self, node: VarDeclNode, **kwargs) -> Iterator[Token]:
        yield from self.visit(node.type)
        yield from self.visit(node.id)
        yield Token("=", Type.EQ)
        yield from self.visit(node.exp)
        yield Token(";", Type.SEMICOLON)

    def visit_IntTypeNode(self, node: IntTypeNode, **kwargs) -> Iterator[Token]:
        yield Token("Int", Type.INT)

    def visit_CharTypeNode(self, node: CharTypeNode, **kwargs) -> Iterator[Token]:
        yield Token("Char", Type.CHAR)

    def visit_BoolTypeNode(self, node: BoolTypeNode, **kwargs) -> Iterator[Token]:
        yield Token("Bool", Type.BOOL)

    def visit_VoidTypeNode(self, node: VoidTypeNode, **kwargs) -> Iterator[Token]:
        yield Token("Void", Type.VOID)

    def visit_PolymorphicTypeNode(
        self, node: PolymorphicTypeNode, **kwargs
    ) -> Iterator[Token]:
        yield node.token

    def visit_IndexNode(self, node: IndexNode, **kwargs) -> Iterator[Token]:
        yield PrintingInfo.NOSPACE
        yield Token("[", Type.LSB)
        yield from self.visit(node.exp)
        yield Token("]", Type.RSB)

    def visit_ListNode(self, node: ListNode, **kwargs) -> Iterator[Token]:
        yield Token("[", Type.LSB)
        if node.body:
            yield from self.visit(node.body)
        yield Token("]", Type.RSB)

    def visit_Op2Node(
        self, node: Op2Node, previous_precedence: int = None, first=True, **kwargs
    ) -> Iterator[Token]:

        # Custom printing for strings
        if isinstance(node.left, Token) and node.left.type == Type.CHARACTER:
            if first:
                yield Token('"', Type.STRING)
            yield Token(node.left.text[1:-1], Type.STRING)
            if not isinstance(node.right, ListNode):
                yield from self.visit(node.right, first=False, **kwargs)
            if first:
                # As opposed to STRING, STRING_LONELY_ERROR is not left attached
                # which allows a space after the string is over
                yield Token('"', Type.STRING_LONELY_ERROR)

        # Special bracket handling for right associative operators
        elif node.operator.type in right_associative:
            # We want brackets on the left side whenever that left side is another Op2Node,
            # rather than a Token
            brackets = not isinstance(node.left, Token)
            if brackets:
                yield Token("(", Type.LRB)
            yield from self.visit(node.left)
            if brackets:
                yield Token(")", Type.RRB)
            yield node.operator
            yield from self.visit(node.right)

        else:
            precedence = operator_precedence[node.operator.type]
            if previous_precedence and (precedence > previous_precedence):
                yield Token("(", Type.LRB)
                yield from self.visit(node.left, previous_precedence=precedence)
                yield node.operator
                yield from self.visit(node.right, previous_precedence=precedence)
                yield Token(")", Type.RRB)
            else:
                yield from self.visit(node.left, previous_precedence=precedence)
                yield node.operator
                yield from self.visit(node.right, previous_precedence=precedence)

    def visit_Op1Node(self, node: Op1Node, **kwargs) -> Iterator[Token]:
        if isinstance(node.operand, Op2Node):
            yield node.operator
            yield PrintingInfo.NOSPACE
            yield Token("(", Type.LRB)
            yield from self.visit(node.operand)
            yield Token(")", Type.RRB)
        else:
            yield node.operator
            yield PrintingInfo.NOSPACE
            yield from self.visit(node.operand)

    def visit_TupleNode(self, node: TupleNode, **kwargs) -> Iterator[Token]:
        yield Token("(", Type.LRB)
        yield from self.visit(node.left)
        yield Token(",", Type.COMMA)
        yield from self.visit(node.right)
        yield Token(")", Type.RRB)

    def visit_ReturnNode(self, node: ReturnNode, **kwargs) -> Iterator[Token]:
        yield Token("return", Type.RETURN)
        if node.exp:
            yield from self.visit(node.exp)
        yield Token(";", Type.SEMICOLON)

    def visit_StmtNode(self, node: StmtNode, **kwargs) -> Iterator[Token]:
        yield from self.visit(node.stmt)
        match node.stmt:
            case FunCallNode() | Token(type=Type.CONTINUE) | Token(type=Type.BREAK):
                yield Token(";", Type.SEMICOLON)

    def visit_FunTypeNode(self, node: FunTypeNode, **kwargs) -> Iterator[Token]:
        for _type in node.types:
            yield from self.visit(_type)
            yield PrintingInfo.SPACE
        yield Token("->", Type.ARROW)
        yield from self.visit(node.ret_type)

    def visit_StmtAssNode(self, node: StmtAssNode, **kwargs) -> Iterator[Token]:
        yield from self.visit(node.id)
        yield Token("=", Type.EQ)
        yield from self.visit(node.exp)
        yield Token(";", Type.SEMICOLON)

    def visit_WhileNode(self, node: WhileNode, **kwargs) -> Iterator[Token]:
        yield Token("while", Type.WHILE)
        yield Token("(", Type.LRB)
        yield from self.visit(node.cond)
        yield Token(")", Type.RRB)
        yield Token("{", Type.LCB)
        for stmt in node.body:
            yield from self.visit(stmt)
        yield Token("}", Type.RCB)

    def visit_ForNode(self, node: ForNode, **kwargs) -> Iterator[Token]:
        yield Token("for", Type.FOR)
        yield from self.visit(node.id)
        yield Token("in", Type.IN)
        yield from self.visit(node.loop)
        yield Token("{", Type.LCB)
        for stmt in node.body:
            yield from self.visit(stmt)
        yield Token("}", Type.RCB)

    def visit_IfElseNode(self, node: IfElseNode, **kwargs) -> Iterator[Token]:
        yield Token("if", Type.IF)
        yield Token("(", Type.LRB)
        yield from self.visit(node.cond)
        yield Token(")", Type.RRB)
        yield Token("{", Type.LCB)
        for stmt in node.body:
            yield from self.visit(stmt)
        yield Token("}", Type.RCB)
        if node.else_body:
            yield Token("else", Type.ELSE)
            yield Token("{", Type.LCB)
            for stmt in node.else_body:
                yield from self.visit(stmt)
            yield Token("}", Type.RCB)

    def visit_FunCallNode(self, node: FunCallNode, **kwargs) -> Iterator[Token]:
        yield node.func
        yield Token("(", Type.LRB)
        if node.args:
            yield from self.visit(node.args)
        yield Token(")", Type.RRB)

    def visit_CommaListNode(self, node: CommaListNode, **kwargs) -> Iterator[Token]:
        yield from self.visit(node.items[0])
        for token in node.items[1:]:
            yield Token(",", Type.COMMA)
            # yield PrintingInfo.SPACE
            yield from self.visit(token)

    def visit_ListAbbrNode(self, node: ListAbbrNode, **kwargs) -> Iterator[Token]:
        yield Token("[", Type.LSB)
        yield from self.visit(node.left)
        yield Token("..", Type.DDOT)
        yield from self.visit(node.right)
        yield Token("]", Type.RSB)

    def visit_Token(self, node: Token, **kwargs) -> Iterator[Token]:
        yield node
