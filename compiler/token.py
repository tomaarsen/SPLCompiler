from typing import List, Tuple

from compiler.type import Type

from dataclasses import dataclass


@dataclass
class Token:
    text: str
    type: Type
    line_no: int
    span: Tuple[int, int]

    def __post_init__(self):
        if not isinstance(self.type, Type):
            self.type = Type.to_type(self.type)
