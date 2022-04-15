from dataclasses import dataclass
from typing import List

from compiler.error.error import CompilerError, CompilerException
from compiler.grammar_parser import NT
from compiler.token import Token
from compiler.type import Type


class ParserException(CompilerException):
    pass


@dataclass
class BracketMismatchError(CompilerError):
    bracket: Type

    def __str__(self) -> str:
        return self.create_error(
            f"Bracket mismatch with {str(self.bracket)} on {self.lines}"
        )


class UnclosedBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on {self.lines} was never closed."
        )


class UnopenedBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on {self.lines} was never opened."
        )


class ClosedWrongBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on {self.lines} closes the wrong type of bracket."
        )


class OpenedWrongBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on {self.lines} opens the wrong type of bracket."
        )


@dataclass
class ParseError(CompilerError):
    nt: NT
    expected: List
    got: Token

    def __str__(self) -> str:
        after = ""
        if isinstance(self.expected[0], Type):
            after = f"Expected {self.expected[0].article_str()}"
            if self.got:
                after += f", but got {self.got.text!r} instead"
            after += f" on line {self.span.end_ln} column {self.span.end_col}."

        return self.create_error(
            f"Syntax error detected when expecting {self.str_nt} on {self.lines}",
            after=after if after else "",
        )
