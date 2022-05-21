import re
from doctest import UnexpectedException
from typing import List

from compiler.util import Span
from prolog_test_compiler.token import Token


class Scanner:
    def __init__(self, program: str) -> None:
        self.og_program = program
        self.preprocessed = None

        self.pattern = re.compile(
            r"""
                (?P<id>[a|b])|
                (?P<digit>[0-9])|
                (?P<operator>[+|-|*])|
                (?P<semicolon>;)|
                (?P<equals>\=)|
                (?P<space>[\ \r\t\f\v\n])|
                (?P<error>.)
            """,
            flags=re.X,
        )

    def scan(self) -> list[Token]:
        lines = self.og_program.splitlines()

        tokens = [
            token
            for line_no, line in enumerate(lines, start=1)
            for token in self.scan_line(line, line_no)
        ]

        return tokens

    def scan_line(self, line: str, line_no) -> List[Token]:
        tokens = []
        matches = self.pattern.finditer(line)
        for match in matches:
            if match is None or match.lastgroup is None:
                raise Exception("Error while scanning tokens.")

            match match.lastgroup:
                case "space":
                    continue
                case "error":
                    raise Exception(f"{match} is not supported.")

            tokens.append(Token(match[0], match.lastgroup))
        return tokens
