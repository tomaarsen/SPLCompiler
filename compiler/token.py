from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple

from compiler.type import Type


@dataclass
class Token:
    text: str
    type: Type
    line_no: int = None
    span: Tuple[int, int] = None

    def __post_init__(self):
        if not isinstance(self.type, Type):
            self.type = Type.to_type(self.type)


@dataclass
class BracketToken(Token):
    open: Token = None
    close: Token = None

    @classmethod
    def from_token(cls, token: Token):
        return cls(**token.__dict__)
