from dataclasses import dataclass
from typing import Tuple

from compiler.error.error import CompilerError, CompilerException, ErrorRaiser
from compiler.tree.tree import FunDeclNode, TypeNode


class TyperException(CompilerException):
    pass


# Failed to unify two types, the error is raised immediately
@dataclass
class UnificationError:
    type_one: TypeNode
    type_two: TypeNode
    program: str
    function: FunDeclNode

    def __post_init__(self) -> None:
        # class Span:
        # ln: Tuple[int, int]
        # col: Tuple[int, int]
        ErrorRaiser.ERRORS.append(self)
        ErrorRaiser.raise_all(TyperException)


class defaultUnifyErrorFactory(UnificationError):
    # TODO: improve this
    def __str__(self) -> str:
        # breakpoint()
        return f"Failed to match type {str(self.type_one)} with expected type {str(self.type_two)}."


# Cannot unify the return types
class returnUnifyErrorFactory(UnificationError):
    def __str__(self) -> str:
        lines = f"[{self.function.span.col[0]}-{self.function.span.col[1]}]"
        message = f"Failed to match return type {str(self.type_one)} with expected return type {str(self.type_two)}.\n\
        Error occurred in function {self.function.id.text} defined on lines {lines}"
        # CompilerError()
        # breakpoint()


class TypeError(UnificationError):
    # If span = ln = 0 and col=0 --> inserted by us

    @staticmethod
    def lines(span) -> Tuple[int]:
        if span.multiline:
            return f"on lines [{span.start_ln}-{span.end_ln}]"
        return f"on line [{span.start_ln}]"

    def __str__(self) -> str:
        compilerError = CompilerError(
            program=self.program,
            span=self.type_one.span if self.type_two is None else self.type_two.span,
        )
        str_type_one = (
            "an inserted Void" if self.type_one is None else str(self.type_one)
        )
        str_type_two = (
            "an inserted Void" if self.type_two is None else str(self.type_two)
        )
        line_type_one = "" if self.type_one is None else self.lines(self.type_one.span)
        line_type_two = "" if self.type_two is None else self.lines(self.type_two.span)

        return compilerError.create_error(
            before=f"Type error: failed to unify {str_type_one} {line_type_one} with {str_type_two} {line_type_two}."
        )
