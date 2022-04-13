from dataclasses import dataclass
from tokenize import Token
from typing import Tuple

from compiler.error.error import CompilerError, CompilerException, ErrorRaiser
from compiler.tree.tree import FunDeclNode, ReturnNode, TypeNode
from compiler.util import Span


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
@dataclass
class returnUnifyErrorFactory(UnificationError):
    token: ReturnNode

    @staticmethod
    def capitalize_first_char(string: str):
        return string[0].upper() + string[1:]

    @property
    def is_inferred(self):
        return (
            self.token.span.start_col == self.token.span.end_col
            and self.token.span.ln[0] == self.token.span.ln[1]
        )

    def __str__(self) -> str:
        # Lines on which the function is defined on
        lines = f"[{self.function.span.ln[0]}-{self.function.span.ln[1]}]"
        # Did we insert the return type?
        return_type_one = (
            f"return type `{self.type_one}` on line [{self.type_one.span.start_ln}]"
            if self.type_one.span.start_col != self.type_one.span.end_col
            else f"inferred return type `{self.type_one}`"
        )
        return_type_two = (
            f"return type `{self.type_two}` on line [{self.type_two.span.start_ln}]"
            if self.type_two.span.start_col != self.type_two.span.end_col
            else f"inferred return type `{self.type_two}`"
        )
        # Create the error message
        before = f"Expected {return_type_one} for function `{self.function.id.text}`, but got {return_type_two}."
        after = (
            f"Error occurred in function `{self.function.id.text}` defined on lines {lines}.\n"
            f"{returnUnifyErrorFactory.capitalize_first_char(return_type_one)} cannot be matched with {return_type_two}."
        )

        # Highlight the function name if the return type is inferred, else highlight the return.
        if self.is_inferred:
            span = Span(
                line_no=(self.function.span.start_ln, self.function.span.start_ln),
                span=self.function.span.col,
            )
        else:
            span = self.token.span

        return CompilerError(self.program, span).create_error(before, after)
