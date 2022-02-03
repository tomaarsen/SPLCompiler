import re
import sys

from dataclasses import dataclass

# TODO: Consider printing lines with color rather than using ^^ on a line below
#       Then we could also print lines before and after?

class CompilerError(Exception):

    ERRORS = []

    def __init__(self) -> None:
        super().__init__()
        sys.tracebacklimit = -1

    @staticmethod
    def raise_all():
        errors = "".join(["\n\n" + str(error) for error in CompilerError.ERRORS])

        if errors:
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
        # TODO: Improve this, use line and ^^
        return f"Unknown character {self.match.group(0) if self.match else '?'!r} on line: {self.line_no}."


@dataclass
class ForgetSemicolonError(QueueableError):
    line: str
    line_no: int

    def __str__(self) -> str:
        # TODO: Improve this, use line and ^^
        return f"Seems like you forgot a semicolon on line: {self.line_no}."


if __name__ == "__main__":
    # Example usage:
    ForgetSemicolonError("  var head = prog.hd", 95).queue()
    UnexpectedCharacterError("        depth = depth - 1;", 58, None).queue()
    ForgetSemicolonError("    current = get_current();", 100).queue()
    UnexpectedCharacterError("    program_pos = pro.gram_pos + 1;", 64, None).queue()
    ForgetSemicolonError("        current.hd = (current.hd - 1) % 256;", 106).queue()
    CompilerError.raise_all()
