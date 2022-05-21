from enum import Enum, auto


class Type(Enum):
    id = auto()
    operator = auto()
    equals = "="
    space = " "
    semicolon = ";"
    digit = auto()
