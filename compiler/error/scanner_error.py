from compiler.error.error import CompilerError, CompilerException


class ScannerException(CompilerException):
    pass


class UnmatchableTokenError(CompilerError):
    def __str__(self) -> str:
        return self.create_error(f"Unexpected lack of token match on {self.lines}.")


class UnexpectedCharacterError(CompilerError):
    def __str__(self) -> str:
        multiple_unexpected_chars = self.length > 1
        return self.create_error(
            f"Unexpected character{'s' if multiple_unexpected_chars else ''} {self.error_chars!r} on {self.lines}."
        )


class DanglingMultiLineCommentError(CompilerError):
    def __str__(self) -> str:
        return self.create_error(f"Found dangling multiline comment on {self.lines}.")


class LonelyQuoteError(CompilerError):
    def __str__(self) -> str:
        return self.create_error(f"Found lonely quote on {self.lines}.")


class EmptyQuoteError(CompilerError):
    def __str__(self) -> str:
        return self.create_error(f"Found empty quote on {self.lines}.")
