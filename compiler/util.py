from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from compiler.type import Type


@dataclass
class Span:
    ln: Tuple[int, int]
    col: Tuple[int, int]

    @property
    def start_ln(self) -> int:
        return self.ln[0]

    @property
    def end_ln(self) -> int:
        return self.ln[1]

    @property
    def start_col(self) -> int:
        return self.col[0]

    @property
    def end_col(self) -> int:
        return self.col[1]

    @property
    def multiline(self) -> bool:
        return self.start_ln != self.end_ln

    def __init__(self, line_no: int | Tuple[int, int], span: Tuple[int, int]) -> None:
        if isinstance(line_no, int):
            self.ln = (line_no, line_no)
        else:
            self.ln = line_no
        self.col = span

    def __and__(self, other: Span) -> Span:
        # Determine the correct columns based on the starting line
        if self.start_ln < other.start_ln:
            col = (self.start_col, other.end_col)
        elif self.start_ln > other.start_ln:
            col = (other.start_col, self.end_col)
        else:
            col = (
                min(self.start_col, other.start_col),
                max(self.end_col, other.end_col),
            )

        return Span(
            line_no=(
                min(self.start_ln, other.start_ln),
                max(self.end_ln, other.end_ln),
            ),
            span=col,
        )


# This only considers binary operators
operator_precedence = {
    Type.OR: 15,
    Type.AND: 14,
    Type.DEQUALS: 10,
    Type.NEQ: 10,
    Type.LT: 9,
    Type.GT: 9,
    Type.LEQ: 9,
    Type.GEQ: 9,
    Type.COLON: 7,
    Type.PLUS: 6,
    Type.MINUS: 6,
    Type.STAR: 5,
    Type.SLASH: 5,
    Type.PERCENT: 5,
}

right_associative = (Type.COLON,)
