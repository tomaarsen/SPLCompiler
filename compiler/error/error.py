import sys
from dataclasses import dataclass, field
from typing import Tuple

from compiler.grammar_parser import NT
from compiler.util import Span


class Colors:
    RED = "\033[31m"
    ENDC = "\033[m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"


# Python exceptions to differentiate the stage in which errors are thrown
class CompilerException(Exception):
    pass


class ErrorRaiser:
    ERRORS = []

    @staticmethod
    def __combine_errors__() -> None:
        from compiler.error.scanner_error import UnexpectedCharacterError

        # Check if we have any consecutive UnexpectedCharacterError
        # First sort on line_no, and then on start of the error in the line
        # If error object has no span attribute, then sort it on top
        ErrorRaiser.ERRORS.sort(
            key=lambda error: (error.span.start_ln, error.span.start_col)
            if isinstance(error, CompilerError)
            else (0, 0)
        )

        length = len(ErrorRaiser.ERRORS)
        i = 0
        while i < length - 1:
            # Ensure that consecutive objects are the (1) same error, (2) have same line_no and (3) are next to eachothers
            current_error = ErrorRaiser.ERRORS[i]
            next_error = ErrorRaiser.ERRORS[i + 1]
            if (
                isinstance(current_error, UnexpectedCharacterError)
                and isinstance(next_error, UnexpectedCharacterError)
                and current_error.span.start_ln == next_error.span.start_ln
                and current_error.span.end_col == next_error.span.start_col
            ):

                # Reuse current_error to prevent additional call to __post_init__ on object creation
                next_error.span = Span(
                    line_no=(current_error.span.start_ln, current_error.span.end_ln),
                    span=(current_error.span.start_col, next_error.span.end_col),
                )
                del ErrorRaiser.ERRORS[i]
                length -= 1
            else:
                i += 1

    @staticmethod
    def raise_all(stage_of_exception: CompilerException) -> None:
        ErrorRaiser.__combine_errors__()
        errors = "".join(["\n\n" + str(error) for error in ErrorRaiser.ERRORS[:10]])
        if errors:
            sys.tracebacklimit = -1
            if len(ErrorRaiser.ERRORS) > 10:
                omitting_multiple_errors = len(ErrorRaiser.ERRORS) - 10 > 1
                errors += f"\n\nShowing 10 errors, omitting {len(ErrorRaiser.ERRORS)-10} error{'s' if omitting_multiple_errors else ''}..."
            ErrorRaiser.ERRORS.clear()
            raise stage_of_exception(errors)


@dataclass
class CompilerError:
    program: str
    # From (line, col) to (line, col)
    span: Span
    n_before: int = field(init=False, default=1)
    n_after: int = field(init=False, default=1)

    # Call __post_init__ using dataclass, to automatically add errors to the list
    def __post_init__(self) -> None:
        ErrorRaiser.ERRORS.append(self)

    @property
    def lines(self) -> Tuple[int]:
        if self.span.multiline:
            return f"lines [{self.span.start_ln}-{self.span.end_ln}]"
        return f"line [{self.span.start_ln}]"

    @property
    def length(self) -> int:
        return self.span.end_col - self.span.start_col

    # Give the characters that caused the error to be thrown
    @property
    def error_chars(self) -> str:
        error_line = self.program.splitlines()[self.span.start_ln - 1]
        return error_line[self.span.start_col : self.span.end_col]

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
                # First line
                if i == self.span.start_ln:
                    # Do not color outside of span on first line
                    final_line += f"   {i}. {line[:self.span.start_col]}"

                    # If we have more than 1 line, color the remaining line
                    if self.span.multiline:
                        final_line += (
                            f"{Colors.RED}{line[self.span.start_col:]}{Colors.ENDC}"
                        )
                    # If there is one line, color up until the correct col
                    else:
                        final_line += f"{Colors.RED}{line[self.span.start_col:self.span.end_col]}{Colors.ENDC}"
                        final_line += line[self.span.end_col :]

                # Color lines (if any) that are in between the first and last line
                elif i > self.span.start_ln and i < self.span.end_ln:
                    final_line += f"   {i}. {Colors.RED}{line}{Colors.ENDC}"
                # The last line, of a multiline
                else:
                    final_line += (
                        f"   {i}. {Colors.RED}{line[:self.span.end_col]}{Colors.ENDC}"
                    )
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

    @property
    def str_nt(self) -> str:
        match self.nt:
            case NT.Return:
                return "a return statement"
            case NT.IfElse:
                return "an if-else statement"
            case NT.While:
                return "a while loop"
            case NT.StmtAss:
                return "an assignment"
            case NT.VarDecl:
                return "a variable declaration"
            case NT.FunDecl:
                return "a function declaration"
            case NT.RetType:
                return "a return type"
            case NT.FunType:
                return "a function type"
            case NT.FArgs:
                return "function arguments"
            case NT.Stmt:
                return "a statement"
            case NT.ActArgs:
                return "a function-call"
            case _:
                return ""


# General compiler errors from which we cannot recover
@dataclass
class CompilerStringError:
    error_message: str
    stage: CompilerException

    # Add the error to the list, and immediately raise it
    def __post_init__(self) -> None:
        ErrorRaiser.ERRORS.append(self)
        ErrorRaiser.raise_all(self.stage)


class UnrecoverableError(CompilerError):
    def __str__(self) -> str:
        return self.error_message