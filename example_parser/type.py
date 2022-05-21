from enum import Enum, auto


class Type(Enum):
    ID = auto()
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    ASSIGN = "<-"
    SEMICOLON = ";"
    DOLLAR = "$"
    LRB = "("
    RRB = ")"
    NEWLINE = "\n"
    CARRIAGE = "\r"
    DIGIT = auto()

    def to_type(type_str: str):
        return Type[type_str]
