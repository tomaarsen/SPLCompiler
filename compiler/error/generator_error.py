from dataclasses import dataclass

from compiler.error.error import CompilerError, CompilerException


class GeneratorException(CompilerException):
    pass


class GeneratorError(CompilerError):
    def create_error(self, before: str, after=""):
        return super().create_error(before, class_name="GeneratorError", after=after)


@dataclass
class OverFlowError(GeneratorError):
    integer_value: int

    def __str__(self) -> str:
        return self.create_error(
            f"The value {self.integer_value} does not fit into SSM memory."
        )
