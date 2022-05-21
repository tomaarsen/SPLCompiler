import re
from typing import List

from example_parser.token import Token


class Scanner:
    def __init__(self, program: str) -> None:
        self.og_program = program
        self.preprocessed = None

        self.pattern = re.compile(
            r"""
                (?P<ID>[a-c])|
                (?P<DIGIT>[0-9]+)|
                (?P<LRB>\()|
                (?P<RRB>\))|
                (?P<DOLLAR>\$)|
                (?P<ASSIGN>\<\-)|
                (?P<PLUS>\+)|
                (?P<MINUS>\-)|
                (?P<STAR>\*)|
                (?P<SEMICOLON>;)|
                (?P<NEWLINE>\n)|
                (?P<CARRIAGE>\r)|
                (?P<SPACE>[\ \r\t\f\v\n])|
                (?P<ERROR>.)
            """,
            flags=re.X,
        )

    def scan(self) -> list[Token]:
        tokens = []
        matches = self.pattern.finditer(self.og_program)
        for match in matches:
            if match is None or match.lastgroup is None:
                raise Exception("Error while scanning tokens.")

            match match.lastgroup:
                case "SPACE":
                    continue
                case "ERROR":
                    raise Exception(f"{match.group()!r} is not supported.")

            tokens.append(Token(match[0], match.lastgroup))
        return tokens
