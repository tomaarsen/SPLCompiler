import re
from typing import List

from icecream import ic

from compiler.token import Token
from compiler.exceptions import CompilerError, UnexpectedCharacterError


class Scanner:
    def __init__(self) -> None:
        # TODO:
        # Comments must be removed first!
        # 'var'
        # Potential extension: " for characters too

        self.pattern = re.compile(
            r"""
                (?P<LRB>\()| # lb = Left Right Bracket
                (?P<RRB>\))| # rb = Right Right Bracket
                (?P<LCB>\{)| # lcb = Left Curly Bracket
                (?P<RCB>\})| # rcb = Right Curly Bracket
                (?P<LSB>\[)| # lsb = Left Square Bracket
                (?P<RSB>\])| # rsb = Right Square Bracket
                # (?P<COMMENT>\/\/)|
                # (?P<COMMENT_OPEN>\/\*)|
                # (?P<COMMENT_CLOSE>\*\/)|
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
                (?P<QUOTE>\'.\')|
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
                (?P<QUOTE_ERROR>\')|
                (?P<ERROR>.)
            """,
            flags=re.X,
        )

    def scan(self, program: str):
        # Scan each line individually
        # TODO: Remove comments first
        program = self.remove_comments(program)

        # TODO: Verify that removing the \n with split() doesn't cause issues
        lines = program.split("\n")

        tokens = [
            token
            for line_no, line in enumerate(lines, start=1)
            for token in self.scan_line(line, line_no)
        ]
        # Raise all errors, if any, that may have accumulated during `scan_line`.
        CompilerError.raise_all()
        return tokens

    def scan_line(self, line: str, line_no) -> List[Token]:
        tokens = []
        matches = self.pattern.finditer(line)
        for match in matches:
            if match is None or match.lastgroup is None:
                # TODO: Perhaps create a QueueableError subclass for this
                raise Exception(f"Unexpected lack of token match on line {line_no}.")

            if match.lastgroup == "SPACE":
                continue

            # TODO: Errors can only be one character long. What if there are multiple
            # wrong characters in a row, e.g. `0a`. Can we combine exceptions in that
            # case?
            if match.lastgroup == "ERROR":
                UnexpectedCharacterError(line, line_no, match).queue()

            # TODO: Handle QUOTE_ERROR

            tokens.append(Token(match[0], match.lastgroup, line_no))
        return tokens

    def remove_comments(self, program: str):
        poi_pattern = re.compile(r"//|/\*|\*/|\n")
        comment_spans = []
        line_comment = False
        star_comment = False
        start = 0
        for match in poi_pattern.finditer(program):
            match match.group(0):
                case "//":
                    if not star_comment:
                        line_comment = True
                        start = match.start()
                case "/*":
                    if not line_comment:
                        star_comment = True
                        start = match.start()
                case "*/":
                    if star_comment:
                        star_comment = False
                        comment_spans.append((start, match.end()))
                case "\n":
                    if line_comment:
                        line_comment = False
                        comment_spans.append((start, match.start()))

        for start, end in comment_spans[::-1]:
            program = program[:start] + "\n" * program[start:end].count("\n") + program[end:]

        return program
