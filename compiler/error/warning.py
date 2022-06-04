from dataclasses import dataclass
from typing import List

from compiler.error.communicator import Communicator, WarningRaiser
from compiler.util import Colors, Span

from compiler.tree.tree import (  # isort:skip
    FieldNode,
    FunCallNode,
    FunDeclNode,
    IfElseNode,
    ReturnNode,
    StmtAssNode,
    StmtNode,
    VarDeclNode,
    WhileNode,
)


@dataclass
class Warning:
    program: str

    def __post_init__(self) -> None:
        WarningRaiser.WARNINGS.append(self)

    def create_message(
        self, span: Span, before: str, after: str = "", n_after=1
    ) -> str:
        return Communicator.create_message(
            self.program, span, "Warning", before, after, 1, n_after, Colors.YELLOW
        )


@dataclass
class DeadCodeRemovalWarning(Warning):
    after_stmt: StmtNode
    removed: List[StmtNode]

    def __str__(self) -> str:
        span_limited = self.removed[0].span
        for statement in self.removed[1:4]:
            span_limited &= statement.span

        span_all = self.removed[0].span
        for statement in self.removed[1:]:
            span_all &= statement.span
        before = f"Removed unreachable code on {span_all.lines_str}, after {self.str_stmt(self.after_stmt)} on {self.after_stmt.span.lines_str}."
        # If the limited span contains all lines:
        if span_limited == span_all:
            return self.create_message(span_limited, before)
        # Else: do not show after line with an arrow
        return self.create_message(span_limited, before, n_after=0)

    def str_stmt(self, stmt: StmtNode) -> str:
        match stmt.stmt:
            case FunCallNode():
                return f"a function call to {stmt.stmt.func.text!r}"
            case IfElseNode():
                return f"an if-else statement"
            case WhileNode():
                return f"a while statement"
            case StmtAssNode():
                return f"an assignment to {stmt.stmt.id!r}"
            case StmtNode():
                return self.str_stmt(stmt.stmt.stmt)
            case ReturnNode():
                return f"a return"
            case VarDeclNode():
                return f"the variable declaration of {stmt.stmt.id!r}"
            case _:
                return "a statement"


@dataclass
class InsertedReturnWarning(Warning):
    function: FunDeclNode

    def __str__(self) -> str:
        before = f"Added an empty return statement at the end of function {str(self.function.id)!r}."
        return self.create_message(self.function.id.span, before)


@dataclass
class NoMainFunctionWarning(Warning):
    def __str__(self) -> str:
        before = "No main function found. The given program will not execute."
        return self.create_message(Span(-1, (0, -1)), before)


@dataclass
class MainCallWarning(Warning):
    function: FunCallNode

    def __str__(self) -> str:
        before = "The function 'main' should not be called."
        return self.create_message(self.function.span, before)
