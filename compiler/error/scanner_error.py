from compiler.error.error import CompilerError, CompilerException


class ScannerException(CompilerException):
    pass


class scanner_error(CompilerError):
    def create_error(self, before: str):
        return super().create_error(before, class_name="scanner_error")


class UnmatchableTokenError(scanner_error):
    def __str__(self) -> str:
        return self.create_error(
            f"Unexpected lack of token match on {self.span.lines_str}."
        )


class UnexpectedCharacterError(scanner_error):
    def __str__(self) -> str:
        multiple_unexpected_chars = self.span.multiline
        return self.create_error(
            f"Unexpected character{'s' if multiple_unexpected_chars else ''} {self.error_chars!r} on {self.span.lines_str}."
        )


class DanglingMultiLineCommentError(scanner_error):
    def __str__(self) -> str:
        return self.create_error(
            f"Found dangling multiline comment on {self.span.lines_str}."
        )


class LonelyQuoteError(scanner_error):
    def __str__(self) -> str:
        return self.create_error(f"Found lonely quote on {self.span.lines_str}.")


class EmptyQuoteError(scanner_error):
    def __str__(self) -> str:
        return self.create_error(f"Found empty quote on {self.span.lines_str}.")
