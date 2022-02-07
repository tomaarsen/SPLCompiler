import sys

from dataclasses import dataclass, field
from typing import Tuple

from compiler.type import Type


class Colors:
    RED = "\033[31m"
    ENDC = "\033[m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


class ErrorRaiser:

    ERRORS = []

    @staticmethod
    def __combine_errors__():
        # Check if we have any consecutive UnexpectedCharacterError
        # First sort on line_no, and then on start of the error (span[0]) in line
        # If error object has no span attribute, then sort it on top
        ErrorRaiser.ERRORS.sort(
            key=lambda error: (error.line_no, error.span[0])
            if hasattr(error, "span")
            else (error.line_no, -1)
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
            raise Exception(errors)


@dataclass
class CompilerError:
    program: str
    line_no: int
    error: str = field(init=False)
    n_before: int = field(init=False, default=1)
    n_after: int = field(init=False, default=1)

    # Call __post_init__ using dataclass, to automatically add errors to the list
    def __post_init__(self):
        ErrorRaiser.ERRORS.append(self)


# TODO: Check that LineErrors work
@dataclass
class LineError(CompilerError):
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


@dataclass
class RangeError(CompilerError):
    span: Tuple[int, int]

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


class MissingSemicolonError(LineError):
    def __str__(self) -> str:
        return super().create_error(f"Missing a semicolon on line: {self.line_no}.")


class UnmatchableTokenError(LineError):
    def __str__(self) -> str:
        return super().create_error(
            f"Unexpected lack of token match on line: {self.line_no}."
        )


class UnexpectedCharacterError(RangeError):
    def __str__(self) -> str:
        error_line = self.program.splitlines()[self.line_no - 1]
        multiple_unexpected_chars = (self.span[1] - self.span[0]) > 1
        return super().create_error(
            f"Unexpected character{'s' if multiple_unexpected_chars else ''} {error_line[self.span[0]:self.span[1]]!r} on line {self.line_no}."
        )


class DanglingMultiLineCommentError(RangeError):
    def __str__(self) -> str:
        return super().create_error(
            f"Found dangling multiline comment on line: {self.line_no}."
        )


class LonelyQuoteError(RangeError):
    def __str__(self) -> str:
        return super().create_error(f"Found lonely quote on line: {self.line_no}.")


class EmptyQuoteError(RangeError):
    def __str__(self) -> str:
        return super().create_error(f"Found empty quote on line: {self.line_no}.")


@dataclass
class BracketMissMatchError(RangeError):
    bracket: Type

    def __str__(self) -> str:
        return super().create_error(
            f"Bracket miss-match with {str(self.bracket)} on line: {self.line_no}"
        )
