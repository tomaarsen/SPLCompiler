from dataclasses import dataclass
from typing import List

from compiler.error.error import CompilerError, CompilerException
from compiler.token import Token
from compiler.type import Type


class ParserException(CompilerException):
    pass


@dataclass
class BracketMismatchError(CompilerError):
    bracket: Type

    def create_error(self, before):
        return super().create_error(before, class_name="BracketError")


class UnclosedBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on {self.span.lines_str} was never closed."
        )


class UnopenedBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on {self.span.lines_str} was never opened."
        )


class ClosedWrongBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on {self.span.lines_str} closes the wrong type of bracket."
        )


class OpenedWrongBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on {self.span.lines_str} opens the wrong type of bracket."
        )


@dataclass
class ParseError(CompilerError):
    nt: str
    expected: List
    got: Token

    def __str__(self) -> str:
        after = ""
        if isinstance(self.expected[0], Type):
            after = f"Expected {self.expected[0].article_str()}"
            if self.got:
                after += f", but got {self.got.text!r} instead"
            after += f" on {self.span.lines_str} column {self.span.end_col}."

        return self.create_error(
            f"Expected {self.str_nt} on {self.span.lines_str}.",
            after,
            class_name="SyntaxError",
        )
