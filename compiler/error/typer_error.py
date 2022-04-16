from dataclasses import dataclass

from compiler.error.error import CompilerError, CompilerException, ErrorRaiser
from compiler.token import Token
from compiler.util import Span

from compiler.tree.tree import (  # isort:skip
    FunCallNode,
    FunDeclNode,
    IfElseNode,
    Op1Node,
    Op2Node,
    ReturnNode,
    TypeNode,
    VarDeclNode,
    VariableNode,
    WhileNode,
)


class TyperException(CompilerException):
    pass


# Failed to unify two types
class UnificationError:
    type_one = None
    type_two = None
    program = ""
    function = None

    def build(
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


# This class should be avoided at all cost, since the error is very generic.
class DefaultUnifyErrorFactory(UnificationError):
    def __str__(self) -> str:
        # Error occurred outside of a function
        if self.function == None:
            return f"Failed to match type {str(self.type_two)!r} with expected type {str(self.type_one)!r}."

        before = f"Failed to match type {str(self.type_two)!r} with expected type {str(self.type_one)!r} in function {self.function.id.text!r}."
        span = Span(
            line_no=(self.function.span.start_ln, self.function.span.start_ln),
            span=self.function.span.col,
        )
        return CompilerError(self.program, span).create_error(before)


@dataclass
class UnaryUnifyErrorFactory(UnificationError):
    unary_op: Op1Node

    def __str__(self) -> str:
        span = self.unary_op.operand.span & self.unary_op.operator.span
        compiler_error = CompilerError(self.program, span)
        before = f"Cannot match type {str(self.type_two)!r} with expected type {str(self.type_one)!r} for unary operation {str(self.unary_op.operator)!r} on {compiler_error.lines}."
        return compiler_error.create_error(before)


@dataclass
class BinaryUnifyErrorFactory(UnificationError):
    binary_op: Op2Node

    def __str__(self) -> str:
        compiler_error = CompilerError(self.program, self.binary_op.span)
        before = f"Cannot match type {str(self.type_two)!r} with expected type {str(self.type_one)!r} for binary operation {str(self.binary_op.operator)!r} on {compiler_error.lines}."

        return compiler_error.create_error(before)


@dataclass
class VariableDeclarationUnifyErrorFactory(UnificationError):
    var_decl: VarDeclNode

    def __str__(self) -> str:
        compiler_error = CompilerError(self.program, self.var_decl.span)
        before = f"Cannot match type {str(self.type_two)!r} with expected type {str(self.type_one)!r} for variable declaration on {compiler_error.lines}."

        return compiler_error.create_error(before)


@dataclass
class IfConditionUnifyErrorFactory(UnificationError):
    if_else: IfElseNode

    def __str__(self) -> str:
        compiler_error = CompilerError(self.program, self.if_else.cond.span)
        before = f"Cannot match type {str(self.type_two)!r} with expected type {str(self.type_one)!r} for if-statement condition on {compiler_error.lines}."

        return compiler_error.create_error(before)


@dataclass
class WhileConditionUnifyErrorFactory(UnificationError):
    while_: WhileNode

    def __str__(self) -> str:
        compiler_error = CompilerError(self.program, self.while_.cond.span)
        before = f"Cannot match type {str(self.type_two)!r} with expected type {str(self.type_one)!r} for while condition on {compiler_error.lines}."

        return compiler_error.create_error(before)


@dataclass
class FunCallUnifyErrorFactory(UnificationError):
    fun_call: FunCallNode

    def __str__(self) -> str:
        compiler_error = CompilerError(self.program, self.fun_call.args.span)
        before = f"Cannot match type {str(self.type_two)!r} with expected type {str(self.type_one)!r} in the function call to {str(self.fun_call.func)!r} on {compiler_error.lines}."

        return compiler_error.create_error(before)


@dataclass
class FieldUnifyErrorFactory(UnificationError):
    var: VariableNode

    def __str__(self) -> str:
        compiler_error = CompilerError(self.program, self.var.span)
        before = f"Cannot match type {str(self.type_two)!r} with expected type {str(self.type_one)!r} when applying {str(self.var.field)!r} on {compiler_error.lines}."

        return compiler_error.create_error(before)


@dataclass
class ReturnUnifyErrorFactory(UnificationError):
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
            f"inferred return type '{self.type_one}'"
            if not self.type_one.span
            or self.type_one.span.start_col != self.type_one.span.end_col
            else f"return type '{self.type_one}' defined on line [{self.type_one.span.start_ln}]"
        )
        return_type_two = (
            f"inferred return type '{self.type_two}'"
            if not self.type_two.span
            or self.type_two.span.start_col == self.type_two.span.end_col
            else f"return type '{self.type_two}' defined on line [{self.type_two.span.start_ln}]"
        )
        # Create the error message
        before = f"Expected {return_type_one} for function '{self.function.id.text}', but got {return_type_two}."
        after = (
            f"Error occurred in function '{self.function.id.text}' defined on lines {lines}."
            # f"{ReturnUnifyErrorFactory.capitalize_first_char(return_type_one)} cannot be matched with {return_type_two}."
        )

        # Highlight the function name if the return type is inferred, else highlight the return.
        if self.is_inferred:
            after += (
                "\nThe 'Void' type was inferred because of a missing return statement."
            )
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

        return CompilerError(self.program, self.token.id.span).create_error(before)


@dataclass
class DuplicateArgumentsDeclError(TypeNodeError):
    token: Token
    function: FunDeclNode

    def __str__(self) -> str:
        num_of_duplicate = sum(
            [
                1
                for argument in self.function.args.items
                if argument.text == self.token.text
            ]
        )
        before = f"Parameter {self.token.text!r} can only occur once as an argument, but it was given {num_of_duplicate}x in the function {self.function.id.text!r}."
        span = Span(
            line_no=(self.function.span.start_ln, self.function.span.start_ln),
            span=self.function.span.col,
        )
        return CompilerError(self.program, span).create_error(before)


@dataclass
class WrongNumberOfArgumentsCallError(TypeNodeError):
    function: FunCallNode
    num_of_expected: int
    num_of_received: int

    def __str__(self) -> str:
        arg = "arguments" if self.num_of_expected > 1 else "argument"
        before = f"Expected {self.num_of_expected} {arg}, but got {self.num_of_received} when calling the function {self.function.func.text} on line {self.function.span.start_ln}."
        return CompilerError(self.program, self.function.span).create_error(before)


@dataclass
class WrongNumberOfArgumentsDeclError(TypeNodeError):
    function: FunDeclNode
    num_of_args: int
    num_of_type_args: int

    def __str__(self) -> str:
        span = self.function.id.span & self.function.args.span & self.function.type.span
        compiler_error = CompilerError(self.program, span)
        arg_str = (
            f"{self.num_of_type_args} arguments"
            if self.num_of_args > 1
            else f"{self.num_of_args} argument"
        )
        arg_type_str = (
            f"{self.num_of_type_args} arguments"
            if self.num_of_type_args > 1
            else f"{self.num_of_num_of_type_argsargs} argument"
        )
        before = f"The function {str(self.function.id)!r} has {arg_str}, but its type signature expects {arg_type_str} on {compiler_error.lines}."

        return compiler_error.create_error(before)


@dataclass
class RedefinitionOfVariableError(TypeNodeError):
    var_decl: VarDeclNode

    def __str__(self) -> str:
        before = f"Redefinition of the variable {self.var_decl.id.text!r} to {(self.var_decl.exp)!r} is not allowed on line {self.var_decl.span.start_ln}."
        return CompilerError(self.program, self.var_decl.span).create_error(before)


@dataclass
class UsageOfUndefinedFunctionError(TypeNodeError):
    function: FunCallNode

    def __str__(self) -> str:
        before = f"Function call to {self.function.func.text!r} on line {self.function.span.start_ln} is not allowed, because {self.function.func.text!r} is not defined."
        return CompilerError(self.program, self.function.span).create_error(before)


@dataclass
class GlobalFunctionCallError(TypeNodeError):
    function: FunCallNode

    def __str__(self) -> str:
        before = f"Function call to {self.function.func.text!r} on line {self.function.span.start_ln} is not allowed, because the call is made in a global context."
        return CompilerError(self.program, self.function.span).create_error(before)
