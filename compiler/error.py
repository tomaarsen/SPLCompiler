import sys
from dataclasses import dataclass, field
from typing import Any, List, Tuple

from compiler.grammar_parser import NT
from compiler.token import Token
from compiler.type import Type
from compiler.util import Span


class Colors:
    RED = "\033[31m"
    ENDC = "\033[m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


class CompilerException(Exception):
    pass


class ErrorRaiser:

    # TODO: Think about the different stages of errors we have: Scanning Errors, Parsing Errors.
    #       We never see Parsing Errors if we have Scanning errors (very logically), but maybe
    #       we then want to specify what kinds of errors are being shown?
    #       E.g. with `raise ParsingException` or `raise ScanningException` at the end of `raise_all`?

    ERRORS = []

    @staticmethod
    def __combine_errors__():
        # TODO: The new Span changes likely broke this

        # Check if we have any consecutive UnexpectedCharacterError
        # First sort on line_no, and then on start of the error (span[0]) in line
        # If error object has no span attribute, then sort it on top
        ErrorRaiser.ERRORS.sort(
            key=lambda error: (error.span.start_ln, error.span.start_col)
        )

        length = len(ErrorRaiser.ERRORS)
        i = 0
        while i < length - 1:
            # Ensure that consecutive objects are the (1) same error, have (2) same line_no and (3) are next to eachothers
            if (
                isinstance(ErrorRaiser.ERRORS[i], UnexpectedCharacterError)
                and isinstance(ErrorRaiser.ERRORS[i + 1], UnexpectedCharacterError)
                and ErrorRaiser.ERRORS[i].line_no == ErrorRaiser.ERRORS[i + 1].line_no
                and ErrorRaiser.ERRORS[i].span[1] == ErrorRaiser.ERRORS[i + 1].span[0]
            ):

                # Reuse CompilerError.ERRORS[i] to prevent additional call to __post_init__ on object creation
                ErrorRaiser.ERRORS[i + 1].span = (
                    ErrorRaiser.ERRORS[i].span[0],
                    ErrorRaiser.ERRORS[i + 1].span[1],
                )
                del ErrorRaiser.ERRORS[i]
                length -= 1
            else:
                i += 1

    @staticmethod
    def raise_all():
        ErrorRaiser.__combine_errors__()
        errors = "".join(["\n\n" + str(error) for error in ErrorRaiser.ERRORS[:10]])

        if errors:
            sys.tracebacklimit = -1
            if len(ErrorRaiser.ERRORS) > 10:
                omitting_multiple_errors = len(ErrorRaiser.ERRORS) - 10 > 1
                errors += f"\n\nShowing 10 errors, omitting {len(ErrorRaiser.ERRORS)-10} error{'s' if omitting_multiple_errors else ''}..."
            ErrorRaiser.ERRORS.clear()
            raise CompilerException(errors)


@dataclass
class CompilerError:
    program: str
    # error: str = field(init=False)  # TODO: What does this do?
    # (line, col) to (line, col)
    span: Span = field(init=False)
    n_before: int = field(init=False, default=1)
    n_after: int = field(init=False, default=1)

    @property
    def lines(self) -> Tuple[int]:
        if self.span.multiline:
            return f"[{self.span.start_ln}-{self.span.end_ln}]"
        return f"[{self.span.start_ln}]"

    # Call __post_init__ using dataclass, to automatically add errors to the list
    def __post_init__(self):
        ErrorRaiser.ERRORS.append(self)


# TODO: Check that LineErrors work
@dataclass
class LineError(CompilerError):
    def __post_init__(self, line_no: int):
        super().__post_init__()
        self.span = Span(line_no, (0, -1))

    def create_error(self, error_message) -> str:
        lines = self.program.splitlines()
        error_lines = lines[
            max(0, self.line_no - self.n_before - 1) : self.line_no + self.n_after
        ]
        error_lines = [
            f"-> {i}. {line}" if self.line_no == i else f"   {i}. {line}"
            for i, line in enumerate(
                error_lines, start=max(1, self.line_no - self.n_before)
            )
        ]
        return error_message + "\n" + "\n".join(error_lines)

    # @dataclass
    # class RangeError(CompilerError):
    #     span: Tuple[Tuple[int, int], Tuple[int, int]]
    # TODO: Add `def length() -> int` for the length of the span.
    #       Useful for subclasses to determine whether to use "character" or "characters"
    # TODO: Add `def error() -> str` (or something named similarly) to
    #       get the character(s) that contain the error. Useful for subclasses.
    # span: Tuple[Tuple[int, int], Tuple[int, int]] # (line, col) to (line, col)

    """
    def create_error(self, error_message: str) -> str:
        lines = self.program.splitlines()
        error_lines = lines[
            max(0, self.line_no - self.n_before - 1) : self.line_no + self.n_after
        ]
        error_lines = [
            f"-> {i}. {line[:self.span[0]]}"
            f"{Colors.RED}{line[self.span[0]:self.span[1]]}{Colors.ENDC}"
            f"{line[self.span[1]:]}"
            if self.line_no == i
            else f"   {i}. {line}"
            for i, line in enumerate(
                error_lines, start=max(1, self.line_no - self.n_before)
            )
        ]

        return error_message + "\n" + "\n".join(error_lines)
    """


@dataclass
class RangeError(CompilerError):
    span: Span
    # TODO: Add `def length() -> int` for the length of the span.
    #       Useful for subclasses to determine whether to use "character" or "characters"
    # TODO: Add `def error() -> str` (or something named similarly) to
    #       get the character(s) that contain the error. Useful for subclasses.

    def create_error(self, before: str, after: str = "") -> str:
        lines = self.program.splitlines()
        error_lines = lines[
            max(0, self.span.start_ln - self.n_before - 1) : self.span.end_ln
            + self.n_after
        ]
        final_error_lines = []
        for i, line in enumerate(
            error_lines, start=max(1, self.span.start_ln - self.n_before)
        ):
            final_line = ""
            # If this line contains denotated spans:
            if i >= self.span.start_ln and i <= self.span.end_ln:
                # Before:
                final_line = f"-> {i}. {line[:self.span.start_col]}"
                # During the denotated area
                final_line += f"{Colors.RED}{line[self.span.start_col:self.span.end_col]}{Colors.ENDC}"
                # Optionally, after
                final_line += line[self.span.end_col :]
            else:
                final_line += f"   {i}. {line}"
            final_error_lines.append(final_line)

        message = (
            self.__class__.__name__
            + ": "
            + before
            + "\n"
            + "\n".join(final_error_lines)
        )
        if after:
            message += "\n" + after
        return message


class MissingSemicolonError(LineError):
    def __str__(self) -> str:
        return self.create_error(f"Missing a semicolon on line {self.lines}.")


class UnmatchableTokenError(LineError):
    def __str__(self) -> str:
        return self.create_error(
            f"Unexpected lack of token match on line {self.lines}."
        )


class UnexpectedCharacterError(RangeError):
    def __str__(self) -> str:
        error_line = self.program.splitlines()[self.line_no - 1]
        multiple_unexpected_chars = (self.span[1] - self.span[0]) > 1
        return self.create_error(
            f"Unexpected character{'s' if multiple_unexpected_chars else ''} {error_line[self.span[0]:self.span[1]]!r} on line {self.lines}."
        )


class DanglingMultiLineCommentError(RangeError):
    def __str__(self) -> str:
        return self.create_error(
            f"Found dangling multiline comment on line {self.lines}."
        )


class LonelyQuoteError(RangeError):
    def __str__(self) -> str:
        return self.create_error(f"Found lonely quote on line {self.lines}.")


class EmptyQuoteError(RangeError):
    def __str__(self) -> str:
        return self.create_error(f"Found empty quote on line {self.lines}.")


@dataclass
class BracketMismatchError(RangeError):
    bracket: Type

    def __str__(self) -> str:
        return self.create_error(
            f"Bracket mismatch with {str(self.bracket)} on line {self.lines}"
        )


class UnclosedBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on line {self.lines} was never closed."
        )


class UnopenedBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on line {self.lines} was never opened."
        )


class ClosedWrongBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on line {self.lines} closes the wrong type of bracket."
        )


class OpenedWrongBracketError(BracketMismatchError):
    def __str__(self) -> str:
        return self.create_error(
            f"The {str(self.bracket)} bracket on line {self.lines} opens the wrong type of bracket."
        )


@dataclass
class ParseError(RangeError):
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
            f"Syntax error detected when expecting a {self.nt} on line{'s' if self.span.multiline else ''} {self.lines}",
            after=after if after else "",
        )
