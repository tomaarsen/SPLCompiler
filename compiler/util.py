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


def span_between_inclusive(span_one: Span, span_two: Span):
    return Span(
        line_no=(span_one.start_ln, span_two.end_ln),
        span=(span_one.start_col, span_two.end_col),
    )
