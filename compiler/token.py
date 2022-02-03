from typing import List

from compiler.type import Type

from dataclasses import dataclass

@dataclass
class Token:
    text: str
    type: Type
    line_no: int

    def __init__(self, text: str, tok_type: Type, line_no: int) -> None:
        self.text = text
        self.line_no = line_no

        if isinstance(tok_type, Type):
            self.type = tok_type
        else:
            self.type = Type.to_type(tok_type)
