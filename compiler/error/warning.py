from dataclasses import dataclass
from typing import List

from compiler.error.communicator import Communicator, WarningRaiser
from compiler.tree.tree import StmtNode
from compiler.util import Colors, Span


@dataclass
class Warning:
    program: str

    def __post_init__(self) -> None:
        WarningRaiser.WARNINGS.append(self)

    def create_message(
        self, span: Span, before: str, after: str = "", n_after=1
    ) -> str:
        return Communicator.create_message(
            self.program, span, "Warning", before, after, 1, n_after, Colors.YELLOW
        )


@dataclass
class DeadCodeRemovalWarning(Warning):
    after_stmt: StmtNode
    removed: List[StmtNode]

    def __str__(self) -> str:
        span_limited = self.removed[0].span
        for statement in self.removed[1:4]:
            span_limited &= statement.span

        span_all = self.removed[0].span
        for statement in self.removed[1:]:
            span_all &= statement.span
        before = f"Removed unreachable code on {span_all.lines_str}, after {str(self.after_stmt)!r} on {self.after_stmt.span.lines_str}."

        # If the limited span contains all lines:
        if span_limited == span_all:
            return self.create_message(span_limited, before)
        # Else: do not show after line with an arrow
        return self.create_message(span_limited, before, n_after=0)
