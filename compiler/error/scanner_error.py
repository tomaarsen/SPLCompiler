from compiler.error.error import CompilerError, CompilerException


class ScannerException(CompilerException):
    pass


class ScannerError(CompilerError):
    def create_error(self, before: str):
        return super().create_error(before, class_name="ScannerError")


class UnmatchableTokenError(ScannerError):
    def __str__(self) -> str:
        return self.create_error(
            f"Unexpected lack of token match on {self.span.lines_str}."
        )


class UnexpectedCharacterError(ScannerError):
    def __str__(self) -> str:
        multiple_unexpected_chars = self.span.multiline
        return self.create_error(
            f"Unexpected character{'s' if multiple_unexpected_chars else ''} {self.error_chars!r} on {self.span.lines_str}."
        )


class DanglingMultiLineCommentError(ScannerError):
    def __str__(self) -> str:
        return self.create_error(
            f"Found dangling multiline comment on {self.span.lines_str}."
        )


class LonelyQuoteError(ScannerError):
    def __str__(self) -> str:
        return self.create_error(f"Found lonely quote on {self.span.lines_str}.")


class EmptyQuoteError(ScannerError):
    def __str__(self) -> str:
        return self.create_error(f"Found empty quote on {self.span.lines_str}.")
