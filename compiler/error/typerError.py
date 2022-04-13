from dataclasses import dataclass
from typing import Tuple

from compiler.error.error import CompilerError, CompilerException, ErrorRaiser
from compiler.token import Token
from compiler.tree.tree import FunDeclNode, ReturnNode, TypeNode
from compiler.util import Span


class TyperException(CompilerException):
    pass


# Failed to unify two types, the error is raised immediately
class UnificationError:
    type_one = None
    type_two = None
    program = ""
    function = None

    def build_and_raise(
        self,
        type_one: TypeNode,
        type_two: TypeNode,
        program: str,
        function: FunDeclNode,
    ):
        self.type_one = type_one
        self.type_two = type_two
        self.program = program
        self.function = function
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

    # Should only be called after build method has been used
    def __str__(self) -> str:
        # Lines on which the function is defined on
        lines = f"[{self.function.span.ln[0]}-{self.function.span.ln[1]}]"
        # Did we insert the return type?
        return_type_one = (
            f"return type '{self.type_one}' defined on line [{self.type_one.span.start_ln}]"
            if self.type_one.span.start_col != self.type_one.span.end_col
            else f"inferred return type '{self.type_one}'"
        )
        return_type_two = (
            f"return type '{self.type_two}' defined on line [{self.type_two.span.start_ln}]"
            if self.type_two.span.start_col != self.type_two.span.end_col
            else f"inferred return type '{self.type_two}'"
        )
        # Create the error message
        before = f"Expected {return_type_one} for function '{self.function.id.text}', but got {return_type_two}."
        after = (
            f"Error occurred in function '{self.function.id.text}' defined on lines {lines}.\n"
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


# Errors that occur within the type_node function of the Typer
# These errors are raised immediately
@dataclass
class TypeNodeError:
    program: str

    def __post_init__(self):
        ErrorRaiser.ERRORS.append(self)


@dataclass
class VariableError(TypeNodeError):
    token: Token

    def __str__(self) -> str:
        before = f"Unknown variable {self.token.text!r} found on line {self.token.span.start_ln}."
        return CompilerError(self.program, self.token.span).create_error(before)


@dataclass
class FunctionRedefinitionError(TypeNodeError):
    token: FunDeclNode

    def __str__(self) -> str:
        before = (
            f"The function {self.token.id.text!r} cannot be defined more than once."
        )

        span = Span(
            line_no=(self.token.span.start_ln, self.token.span.start_ln),
            span=self.token.span.col,
        )
        return CompilerError(self.program, span).create_error(before)


class WrongNumberOfArgumentsError(TypeNodeError):
    token: FunDeclNode
    expected_num_args: int
    given_num_args: int

    def __str__(self) -> str:
        before = f""
        return CompilerError(self.program, span).create_error(before)
