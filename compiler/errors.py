import re
import sys

from dataclasses import dataclass
from typing import Tuple

# TODO: Print lines before and after?


class Colors:
    RED = "\033[31m"
    ENDC = "\033[m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


class CompilerError:

    ERRORS = []

    # TODO: Properly concat similar errors
    @staticmethod
    def __combine_errors():
        # Check if we have any consecutive UnexpectedCharacterError
        # First sort on line_no, and then on start of the error (span[0]) in line
        # If error object has no span attribute, then sort it on top
        CompilerError.ERRORS.sort(
            key=lambda error: (error.line_no, error.span[0])
            if hasattr(error, "span")
            else (error.line_no, -1)
        )

        length = len(CompilerError.ERRORS)
        i = 0
        while i < length - 1:
            if (
                isinstance(CompilerError.ERRORS[i], UnexpectedCharacterError)
                and isinstance(CompilerError.ERRORS[i + 1], UnexpectedCharacterError)
                and CompilerError.ERRORS[i].span[1]
                == CompilerError.ERRORS[i + 1].span[0]
            ):
                CompilerError.ERRORS[i + 1] = UnexpectedCharacterError(
                    CompilerError.ERRORS[i].line,
                    CompilerError.ERRORS[i].line_no,
                    (
                        CompilerError.ERRORS[i].span[0],
                        CompilerError.ERRORS[i + 1].span[1],
                    ),
                )
                del CompilerError.ERRORS[i]
                length -= 1
                i -= 1
            i += 1

    @staticmethod
    def raise_all():
        CompilerError.__combine_errors()
        errors = "".join(["\n\n" + str(error) for error in CompilerError.ERRORS[:10]])

        if errors:
            sys.tracebacklimit = -1
            if len(CompilerError.ERRORS) > 10:
                omitting_multiple_errors = len(CompilerError.ERRORS) - 10 > 1
                errors += f"\n\nShowing 10 errors, omitting {len(CompilerError.ERRORS)-10} error{'s' if omitting_multiple_errors else ''}..."
            CompilerError.ERRORS.clear()
            raise Exception(errors)


class QueueableError:
    def queue(self):
        CompilerError.ERRORS.append(self)


@dataclass
class UnexpectedCharacterError(QueueableError):
    line: str
    line_no: int
    span: Tuple[int, int]

    def __str__(self) -> str:
        multiple_unexpected_chars = (self.span[1] - self.span[0]) > 1
        return (
            f"Unexpected character{'s' if multiple_unexpected_chars else ''} {self.line[self.span[0]:self.span[1]]!r} on line {self.line_no}.\n"
            f"  {self.line_no}. {self.line[:self.span[0]]}{Colors.RED}{self.line[self.span[0]:self.span[1]]}{Colors.ENDC}{self.line[self.span[1]:]}"
        )


@dataclass
class MissingSemicolonError(QueueableError):
    line: str
    line_no: int

    def __str__(self) -> str:
        return (
            f"Missing a semicolon on line: {self.line_no}."
            f"  {self.line_no}. {self.line}"
        )


@dataclass
class UnmatchableTokenError(QueueableError):
    line: str
    line_no: int

    def __str__(self) -> str:
        return (
            f"Unexpected lack of token match on line: {self.line_no}.\n"
            f"  {self.line_no}. {self.line}"
        )


@dataclass
class DanglingMultiLineCommentError(QueueableError):
    line: str
    line_no: int
    match: re.Match

    def __str__(self) -> str:
        return (
            f"Found dangling multiline comment on line: {self.line_no}.\n"
            f"  {self.line_no}. {self.line[:self.match.start()]}{Colors.RED}{self.line[self.match.start():self.match.end()]}{Colors.ENDC}{self.line[self.match.end():]}"
        )


@dataclass
class LonelyQuoteError(QueueableError):
    line: str
    line_no: int
    match: re.Match

    def __str__(self) -> str:
        return (
            f"Found lonely quote on line: {self.line_no}.\n"
            f"  {self.line_no}. {self.line[:self.match.start()]}{Colors.RED}{self.line[self.match.start():self.match.end()]}{Colors.ENDC}{self.line[self.match.end():]}"
        )


if __name__ == "__main__":
    # Example usage:
    MissingSemicolonError("  var head = prog.hd", 95).queue()
    # UnexpectedCharacterError("        depth = depth - 1;", 58, None).queue()
    MissingSemicolonError("    current = get_current();", 100).queue()
    # UnexpectedCharacterError("    program_pos = pro.gram_pos + 1;", 64, None).queue()
    MissingSemicolonError("        current.hd = (current.hd - 1) % 256;", 106).queue()
    CompilerError.raise_all()
