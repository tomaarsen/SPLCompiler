import re
from typing import List

from icecream import ic

from compiler.token import Token


class Scanner:
    def __init__(self) -> None:
        self.pattern = re.compile(
            r"""
                (?P<LRB>\()| # lb = Left Right Bracket
                (?P<RRB>\))| # rb = Right Right Bracket
                (?P<LCB>\{)| # lcb = Left Curly Bracket
                (?P<RCB>\})| # rcb = Right Curly Bracket
                (?P<LSB>\[)| # lsb = Left Square Bracket
                (?P<RSB>\])| # rsb = Right Square Bracket
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
                (?P<WHILE>\bwhile\b)|
                (?P<RETURN>\breturn\b)|
                (?P<VOID>\bVoid\b)|
                (?P<INT>\bInt\b)|
                (?P<BOOL>\bBool\b)|
                (?P<CHAR>\bChar\b)|
                (?P<FALSE>\bFalse\b)|
                (?P<TRUE>\bTrue\b)|
                (?P<ID>[a-zA-Z]\w*)|
                (?P<DIGIT>\d+)|
                (?P<SPACE>[\ \r\t\f\v\n])|
                (?P<ERROR>.)
            """,
            flags=re.X,
        )

    def scan(self, lines: List[str]):
        tokens = []
        errors = []
        for line_no, line in enumerate(lines, start=1):
            line_tokens, line_errors = self.scan_line(line, line_no)
            tokens.extend(line_tokens)
            errors.extend(line_errors)
        if errors:
            raise Exception("\n".join(errors))
        return tokens

    def scan_line(self, line: str, line_no) -> List[Token]:
        tokens = []
        errors = []
        matches = self.pattern.finditer(line)
        for match in matches:
            if match is None or match.lastgroup is None:
                raise Exception(f"Unexpected lack of token match on line {line_no}.")
            
            if match.lastgroup == "SPACE":
                continue

            if match.lastgroup == "ERROR":
                # TODO: Make better Exception class
                exc = "\n" + line.replace('\t', ' ') + f"{' ' * match.start()}{'^' * (match.end() - match.start())}\nThere was an error with token {match[0]!r} on line {line_no}."
                errors.append(exc)
            tokens.append(Token(match[0], match.lastgroup, line_no))
        return tokens, errors
