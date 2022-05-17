from enum import Enum, auto


class Type(Enum):
    LRB = "("
    RRB = ")"
    LCB = "{"
    RCB = "}"
    LSB = "["
    RSB = "]"
    COMMENT_OPEN = "/*"
    COMMENT_CLOSE = "*/"
    SEMICOLON = ";"
    DOUBLE_COLON = "::"
    ARROW = "->"
    COMMA = ","
    DDOT = ".."
    PLUS = "+"
    MINUS = "-"
    STAR = "*"
    SLASH = "/"
    POWER = "^"
    PERCENT = "%"
    DEQUALS = "=="
    LEQ = "<="
    GEQ = ">="
    LT = "<"
    GT = ">"
    NEQ = "!="
    EQ = "="
    AND = "&&"
    OR = "||"
    COLON = ":"
    NOT = "!"
    QUOTE_EMPTY_ERROR = "''"
    QUOTE_LONELY_ERROR = "'"
    HD = ".hd"
    TL = ".tl"
    FST = ".fst"
    SND = ".snd"
    IF = "if"
    ELSE = "else"
    WHILE = "while"
    RETURN = "return"
    VOID = "Void"
    INT = "Int"
    BOOL = "Bool"
    CHAR = "Char"
    FALSE = "False"
    TRUE = "True"
    VAR = "var"
    ID = auto()
    DIGIT = auto()
    CHARACTER = auto()
    SPACE = " "
    ERROR = auto()

    def to_type(type_str: str):
        return Type[type_str]

    def __str__(self) -> str:
        match self:
            case Type.ID:
                return "variable"
            case Type.DIGIT:
                return "digit"
            case Type.ERROR:
                return "error"
        return repr(self.value)

    def article_str(self) -> str:
        match self:
            case Type.ERROR | Type.INT | Type.ELSE | Type.IF:
                return f"an {self}"
            case _:
                return f"a {self}"
