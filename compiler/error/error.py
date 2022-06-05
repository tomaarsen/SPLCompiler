from dataclasses import dataclass, field

from compiler.error.communicator import Communicator, ErrorRaiser
from compiler.util import Span


# Python exceptions to differentiate the stage in which errors are thrown
class CompilerException(Exception):
    pass


@dataclass
class CompilerError:
    program: str
    span: Span
    n_before: int = field(init=False, default=1)
    n_after: int = field(init=False, default=1)

    # Call __post_init__ using dataclass, to automatically add errors to the list
    def __post_init__(self) -> None:
        ErrorRaiser.ERRORS.append(self)

    def create_error(
        self, before: str = "", after: str = "", class_name="CompilerError"
    ):
        return Communicator.create_message(
            self.program, self.span, class_name, before, after
        )

    # Give the characters that caused the error to be thrown
    @property
    def error_chars(self) -> str:
        error_line = self.program.splitlines()[self.span.start_ln - 1]
        return error_line[self.span.start_col : self.span.end_col]

    @property
    def str_nt(self) -> str:
        match self.nt:
            case "Return":
                return "a return statement"
            case "IfElse":
                return "an if-else statement"
            case "While":
                return "a while loop"
            case "StmtAss":
                return "an assignment"
            case "VarDecl":
                return "a variable declaration"
            case "FunDecl":
                return "a function declaration"
            case "RetType":
                return "a return type"
            case "FunType":
                return "a function type"
            case "FArgs":
                return "function arguments"
            case "Stmt":
                return "a statement"
            case "ActArgs":
                return "a function-call"
            case "ListAbbr":
                return "a list abbreviation"
            case "For":
                return "a for loop"
            case _:
                raise Exception(
                    f"Attempted to print out {self.nt!r} as extended string, but no such format exists."
                )


class UnrecoverableError(CompilerError):
    def __str__(self) -> str:
        return self.error_message

    # Add the error to the list, and immediately raise it
    def __post_init__(self) -> None:
        ErrorRaiser.ERRORS.append(self)
        Communicator.communicate(self.stage)
