from enum import Enum, auto


class Type(Enum):
    LRB = auto()
    RRB = auto()
    LCB = auto()
    RCB = auto()
    LSB = auto()
    RSB = auto()
    # COMMENT = auto()
    COMMENT_OPEN = auto()
    COMMENT_CLOSE = auto()
    SEMICOLON = auto()
    DOUBLE_COLON = auto()
    ARROW = auto()
    COMMA = auto()
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()
    POWER = auto()
    PERCENT = auto()
    DEQUALS = auto()
    LEQ = auto()
    GEQ = auto()
    LT = auto()
    GT = auto()
    NEQ = auto()
    EQ = auto()
    AND = auto()
    OR = auto()
    COLON = auto()
    NOT = auto()
    QUOTE = auto()
    QUOTE_EMPTY_ERROR = auto()
    QUOTE_LONELY_ERROR = auto()
    HD = auto()
    TL = auto()
    FST = auto()
    SND = auto()
    IF = auto()
    ELSE = auto()
    WHILE = auto()
    RETURN = auto()
    VOID = auto()
    INT = auto()
    BOOL = auto()
    CHAR = auto()
    FALSE = auto()
    TRUE = auto()
    VAR = auto()
    ID = auto()
    DIGIT = auto()
    CHARACTER = auto()
    SPACE = auto()
    ERROR = auto()

    def to_type(type_str: str):
        return Type[type_str]

    def __str__(self) -> str:
        match self.name:
            case "LRB":
                return "left round bracket"
            case "RRB":
                return "right round bracket"
            case "LCB":
                return "left curly bracket"
            case "RCB":
                return "right curly bracket"
            case "LSB":
                return "left square bracket"
            case "RSB":
                return "right square bracket"
            case _:
                return self.name
