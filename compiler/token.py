from __future__ import annotations

from dataclasses import dataclass, field

from compiler.type import Type
from compiler.util import Span


@dataclass
class Token:
    text: str
    type: Type = field(repr=False)
    span: Span = field(repr=False, default_factory=lambda: Span(-1, (0, -1)))

    def __post_init__(self) -> None:
        if not isinstance(self.type, Type):
            self.type = Type.to_type(self.type)

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Token):
            return False
        return self.text == __o.text and self.type == __o.type

    def __hash__(self) -> int:
        return hash(self.text)

    def __str__(self) -> str:
        return self.text
