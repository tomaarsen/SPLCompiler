from __future__ import annotations

from dataclasses import dataclass, field

from example_parser.type import Type


@dataclass
class Token:
    text: str
    type: Type = field(repr=False)

    def __post_init__(self) -> None:
        if not isinstance(self.type, Type):
            self.type = Type.to_type(self.type)

    def match(self, other_type: Type) -> bool:
        return self.type == other_type

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, Token):
            return False
        return self.text == __o.text and self.type == __o.type

    def __str__(self) -> str:
        return self.text
