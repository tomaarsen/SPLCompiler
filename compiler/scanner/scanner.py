import re
from typing import List

from compiler.error.communicator import Communicator
from compiler.token import Token
from compiler.type import Type
from compiler.util import Span

from compiler.error.scanner_error import (  # isort:skip
    DanglingMultiLineCommentError,
    EmptyQuoteError,
    LonelyQuoteError,
    ScannerException,
    UnexpectedCharacterError,
    UnmatchableTokenError,
    ScannerException,
)


class Scanner:
    def __init__(self, program: str) -> None:
        # TODO: Potential extension: " for characters too
        # TODO: Potential extension: While else
        # TODO: '\*'

        self.og_program = program
        self.preprocessed = None

        self.pattern = re.compile(
            r"""
                (?P<LRB>\()| # lb = Left Round Bracket
                (?P<RRB>\))| # rb = Right Round Bracket
                (?P<LCB>\{)| # lcb = Left Curly Bracket
                (?P<RCB>\})| # rcb = Right Curly Bracket
                (?P<LSB>\[)| # lsb = Left Square Bracket
                (?P<RSB>\])| # rsb = Right Square Bracket
                # (?P<COMMENT>\/\/)|
                (?P<COMMENT_OPEN>\/\*)|
                (?P<COMMENT_CLOSE>\*\/)|
                (?P<SEMICOLON>\;)|
                (?P<DOUBLE_COLON>\:\:)|
                (?P<ARROW>\-\>)|
                (?P<DDOT>\.\.)|
                (?P<COMMA>\,)|
                (?P<PLUS>\+)|
                (?P<MINUS>\-)|
                (?P<STAR>\*)|
                (?P<SLASH>\/)|
                (?P<POWER>\^)|
                (?P<PERCENT>\%)|
                (?P<DEQUALS>\=\=)|
                (?P<LEQ>\<\=)|
                (?P<GEQ>\>\=)|
                (?P<LT>\<)|
                (?P<GT>\>)|
                (?P<NEQ>\!\=)|
                (?P<EQ>\=)|
                (?P<AND>\&\&)|
                (?P<OR>\|\|)|
                (?P<COLON>\:)|
                (?P<NOT>\!)|
                # Dot only occurs with hd, tl, fst or snd:
                (?P<HD>\.hd)| # Head
                (?P<TL>\.tl)| # Tail
                (?P<FST>\.fst)| # First
                (?P<SND>\.snd)| # Second
                (?P<IF>\bif\b)|
                (?P<ELSE>\belse\b)|
                (?P<WHILE>\bwhile\b)|
                (?P<FOR>\bfor\b)|
                (?P<IN>\bin\b)|
                (?P<RETURN>\breturn\b)|
                (?P<VOID>\bVoid\b)|
                (?P<INT>\bInt\b)|
                (?P<BOOL>\bBool\b)|
                (?P<CHAR>\bChar\b)|
                (?P<FALSE>\bFalse\b)|
                (?P<TRUE>\bTrue\b)|
                (?P<VAR>\bvar\b)|
                (?P<CONTINUE>)\bcontinue\b|
                (?P<BREAK>)\bbreak\b|
                (?P<ID>\b[a-zA-Z]\w*)|
                (?P<DIGIT>\d+\b)|
                (?P<STRING>)\"(?:[ -~]*?)\"|
                (?P<STRING_LONELY_ERROR>)\"|
                (?P<CHARACTER_SLASH_ERROR>\'\\\')|
                (?P<CHARACTER>)\'(?:\\a|\\b|\\n|\\r|\\t|\\\\|[ -~])\'|
                (?P<QUOTE_EMPTY_ERROR>\'\')|
                (?P<QUOTE_LONELY_ERROR>\')|
                (?P<SPACE>[\ \r\t\f\v\n])|
                (?P<ERROR>.)
            """,
            flags=re.X,
        )

    def scan(self) -> List[Token]:
        """Extract the list of tokens from the program passed to `Scanner(program)`.

        Alternatively, Scanner errors may be raised if relevant, i.e. on illegal tokens.

        Returns:
            List[Token]: A list of Token instances
        """
        # Remove comments first
        self.preprocessed = self.remove_comments(self.og_program)
        lines = self.preprocessed.splitlines()

        # Extract the tokens from the lines line by line
        tokens = [
            token
            for line_no, line in enumerate(lines, start=1)
            for token in self.scan_line(line, line_no)
        ]

        # Raise all errors, if any, that may have accumulated during `scan_line`.
        Communicator.communicate(ScannerException)
        return tokens

    def scan_line(self, line: str, line_no) -> List[Token]:
        tokens = []
        matches = self.pattern.finditer(line)
        for match in matches:
            if match is None or match.lastgroup is None:
                UnmatchableTokenError(self.og_program, line_no)

            span = Span(line_no, match.span())
            match match.lastgroup:
                case "SPACE":
                    continue
                case "ERROR":
                    UnexpectedCharacterError(self.og_program, span)
                case ("COMMENT_OPEN" | "COMMENT_CLOSE"):
                    DanglingMultiLineCommentError(self.og_program, span)
                case "QUOTE_LONELY_ERROR":
                    LonelyQuoteError(self.og_program, span)
                case "QUOTE_EMPTY_ERROR":
                    EmptyQuoteError(self.og_program, span)
                case "STRING_LONELY_ERROR":
                    LonelyQuoteError(self.og_program, span)
                case "CHARACTER_SLASH_ERROR":
                    # TODO
                    raise Exception("Cannot use '\\'")

            tokens.append(Token(match[0], match.lastgroup, span))
        return tokens

    def remove_comments(self, program: str) -> str:
        """Replace all commented out code in the program with spaces.

        Find all occurrences of comment start (/*, //) and comment end (*/, \n) tokens,
        and iterate over them. For every token, track if we now start, end, or continue to be
        in a comment. When the comment ends, we track the spans of the comment, and then replace
        all non-newline tokens with spaces.

        We replace with spaces to preserve the location information of the uncommented code.

        Args:
            program (str): The input program as a string.

        Returns:
            str: The program with comments replaced by spaces.
        """
        poi_pattern = re.compile(r"//|/\*|\*/|\n")
        comment_spans = []
        start_line = -1
        start_star = -1
        for match in poi_pattern.finditer(program):
            match match.group(0):
                case "//":
                    if start_line == start_star == -1:
                        start_line = match.start()

                case "/*":
                    if start_line == start_star == -1:
                        start_star = match.start()

                case "*/":
                    if start_star >= 0:
                        comment_spans.append((start_star, match.end()))
                        start_star = -1

                case "\n":
                    if start_line >= 0:
                        comment_spans.append((start_line, match.start()))
                        start_line = -1

        # To close off the final line comment in a program that does not end with a newline
        if start_line >= 0:
            comment_spans.append((start_line, len(program)))

        # Replace spans with spaces
        for start, end in comment_spans[::-1]:
            separator = re.sub("[^\r\n]", " ", program[start:end])
            program = program[:start] + separator + program[end:]

        return program
