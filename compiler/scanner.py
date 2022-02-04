from multiprocessing.sharedctypes import Value
import queue
import re
from typing import List

from icecream import ic

from compiler.token import Token
from compiler.errors import (
    ErrorRaiser,
    UnexpectedCharacterError,
    UnmatchableTokenError,
    DanglingMultiLineCommentError,
    LonelyQuoteError,
    EmptyQuoteError,
)


class Scanner:
    def __init__(self, program: str) -> None:
        # TODO: Potential extension: " for characters too

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
                (?P<COMMA>\,)|
                (?P<PLUS>\+)|
                (?P<MINUS>\-)|
                (?P<STAR>\*)|
                (?P<SLASH>\/)|
                (?P<PERCENT>\%)|
                (?P<DEQUALS>\=\=)|
                (?P<LT>\<)|
                (?P<GT>\>)|
                (?P<LEQ>\<\=)|
                (?P<GEQ>\>\=)|
                (?P<NEQ>\!\=)|
                (?P<EQ>\=)|
                (?P<AND>\&\&)|
                (?P<OR>\|\|)|
                (?P<COLON>\:)|
                (?P<NOT>\!)|
                (?P<QUOTE>\'\\?.\')|
                (?P<QUOTE_EMPTY_ERROR>\'\')| # TODO: Verify this
                (?P<QUOTE_LONELY_ERROR>\')|
                # Dot only occurs with hd, tl, fst or snd:
                (?P<HD>\.hd)| # Head
                (?P<TL>\.tl)| # Tail
                (?P<FST>\.fst)| # First
                (?P<SND>\.snd)| # Second
                (?P<IF>\bif\b)|
                (?P<WHILE>\bwhile\b)|
                (?P<RETURN>\breturn\b)|
                (?P<VOID>\bVoid\b)|
                (?P<INT>\bInt\b)|
                (?P<BOOL>\bBool\b)|
                (?P<CHAR>\bChar\b)|
                (?P<FALSE>\bFalse\b)|
                (?P<TRUE>\bTrue\b)|
                (?P<VAR>\bvar\b)|
                (?P<ID>\b[a-zA-Z]\w*)|
                (?P<DIGIT>\d+\b)|
                (?P<SPACE>[\ \r\t\f\v\n])|
                (?P<ERROR>.)
            """,
            flags=re.X,
        )

    def scan(self):
        # Remove comments first
        self.preprocessed = self.remove_comments(self.og_program)

        # TODO: Verify that removing the \n with splitlines() doesn't cause issues
        lines = self.preprocessed.splitlines()

        tokens = [
            token
            for line_no, line in enumerate(lines, start=1)
            for token in self.scan_line(line, line_no)
        ]

        # Raise all errors, if any, that may have accumulated during `scan_line`.
        ErrorRaiser.raise_all()
        return tokens

    def scan_line(self, line: str, line_no) -> List[Token]:
        tokens = []
        matches = self.pattern.finditer(line)
        for match in matches:
            if match is None or match.lastgroup is None:
                UnmatchableTokenError(self.og_program, line_no)

            match match.lastgroup:
                case "SPACE":
                    continue
                case "ERROR":
                    UnexpectedCharacterError(self.og_program, line_no, match.span())
                case ("COMMENT_OPEN" | "COMMENT_CLOSE"):
                    DanglingMultiLineCommentError(
                        self.og_program, line_no, match.span()
                    )
                case "QUOTE_LONELY_ERROR":
                    LonelyQuoteError(self.og_program, line_no, match.span())
                case "QUOTE_EMPTY_ERROR":
                    EmptyQuoteError(self.og_program, line_no, match.span())

            tokens.append(Token(match[0], match.lastgroup, line_no, match.span()))
        return tokens

    def remove_comments(self, program: str):
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

        if start_line >= 0:
            comment_spans.append((start_line, len(program)))

        for start, end in comment_spans[::-1]:
            separator = re.sub("[^\r\n]", " ", program[start:end])
            program = program[:start] + separator + program[end:]

        return program
