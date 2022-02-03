import re
import sys

from dataclasses import dataclass

# TODO: Print lines before and after?


class Colors:
    RED = "\033[31m"
    ENDC = "\033[m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


class CompilerError:

    ERRORS = []

    @staticmethod
    def raise_all():
        errors = "".join(["\n\n" + str(error) for error in CompilerError.ERRORS])

        if errors:
            sys.tracebacklimit = -1
            raise Exception(errors)


class QueueableError:
    def queue(self):
        CompilerError.ERRORS.append(self)


@dataclass
class UnexpectedCharacterError(QueueableError):
    line: str
    line_no: int
    match: re.Match

    def __str__(self) -> str:
        return (
            f"Unknown character {self.match.group(0)!r} on line {self.line_no}.\n"
            f"  {self.line_no}. {self.line[:self.match.start()]}{Colors.RED}{self.line[self.match.start():self.match.end()]}{Colors.ENDC}{self.line[self.match.end():]}"
        )


@dataclass
class ForgetSemicolonError(QueueableError):
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
            f"Unexpected lack of token match on line: {self.line_no}."
            f"  {self.line_no}. {self.line}"
        )


if __name__ == "__main__":
    # Example usage:
    ForgetSemicolonError("  var head = prog.hd", 95).queue()
    UnexpectedCharacterError("        depth = depth - 1;", 58, None).queue()
    ForgetSemicolonError("    current = get_current();", 100).queue()
    UnexpectedCharacterError("    program_pos = pro.gram_pos + 1;", 64, None).queue()
    ForgetSemicolonError("        current.hd = (current.hd - 1) % 256;", 106).queue()
    CompilerError.raise_all()
