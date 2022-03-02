from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Tuple

from compiler.type import Type
from compiler.util import Span


@dataclass
class Token:
    text: str
    type: Type
    span: Span = field(repr=False, default_factory=lambda: Span(-1, (0, -1)))

    def __post_init__(self):
        if not isinstance(self.type, Type):
            self.type = Type.to_type(self.type)
