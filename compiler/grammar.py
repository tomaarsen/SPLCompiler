from dataclasses import dataclass
from enum import Enum, auto
from typing import List

from compiler.token import Token
from compiler.type import Type


class Non_Terminal(Enum):
    SPL = auto()
    Decl = auto()
    VarDecl = auto()
    FunDecl = auto()
    RetType = auto()
    FunType = auto()
    FTypes = auto()
    Type = auto()
    BasicType = auto()
    FArgs = auto()
    Stmt = auto()
    Exp = auto()
    Eq = auto()
    Eq_Prime = auto()
    Leq = auto()
    Leq_Prime = auto()
    Sum = auto()
    Sum_Prime = auto()
    Fact = auto()
    Fact_Prime = auto()
    Colon = auto()
    Basic = auto()
    Field = auto()
    FunCall = auto()
    ActArgs = auto()
    Op2 = auto()
    Op1 = auto()
    int = auto()
    id = auto()


class Or:
    def __init__(self, *argv) -> None:
        self.symbols = list(argv)


class Star:
    def __init__(self, *argv) -> None:
        self.symbols = list(argv)


class Plus:
    def __init__(self, *argv) -> None:
        self.symbols = list(argv)


class Optional:
    def __init__(self, *argv) -> None:
        self.symbols = list(argv)


# https://stackoverflow.com/questions/2358045/how-can-i-implement-a-tree-in-python
class NewTree(object):
    "Generic tree node."

    def __init__(self, name, children=None):
        self.name = name
        self.children = []
        if children is not None:
            for child in self.children:
                self.add_child(child)

    def __repr__(self):
        return self.name

    def __len__(self):
        sum = 1
        if self.children is not None:
            for child in self.children:
                sum += len(child)
        return sum

    def add_child(self, node):
        # assert isinstance(node, NewTree)
        self.children.append(node)


@dataclass
class NewParserMatcher:
    tokens: List[Token]

    def __post_init__(self):
        self.grammar = {
            Non_Terminal.SPL: [Star([Non_Terminal.Decl])],
            Non_Terminal.Decl: [Or([Non_Terminal.VarDecl], [Non_Terminal.FunDecl])],
            Non_Terminal.VarDecl: [
                Or([Type.VAR], [Non_Terminal.Type]),
                Non_Terminal.id,
                Type.EQ,
                Non_Terminal.Exp,
                Type.SEMICOLON,
            ],
            Non_Terminal.FunDecl: [
                Non_Terminal.id,
                Type.LRB,
                Optional([Non_Terminal.FArgs]),
                Type.RRB,
                Optional([Type.DOUBLE_COLON], [Non_Terminal.FunType]),
                Type.RCB,
                Star([Non_Terminal.VarDecl]),
                Plus([Non_Terminal.Stmt]),
            ],
            Non_Terminal.RetType: [Or([Non_Terminal.Type], [Type.VOID])],
            Non_Terminal.FunType: [
                Optional([Non_Terminal.FTypes]),
                Type.ARROW,
                Non_Terminal.RetType,
            ],
            Non_Terminal.FTypes: [Non_Terminal.Type, Or([Non_Terminal.FTypes])],
            Non_Terminal.Type: [
                Or(
                    [Non_Terminal.BasicType],
                    [
                        Type.LRB,
                        Non_Terminal.Type,
                        Type.COMMA,
                        Non_Terminal.Type,
                        Type.RRB,
                    ],
                    [Type.LSB, Non_Terminal.Type, Type.RSB],
                    [Non_Terminal.id],
                )
            ],
            Non_Terminal.BasicType: [Type.INT, Type.BOOL, Type.CHAR],
            Non_Terminal.FArgs: [
                Type.ID,
                Optional([Type.COMMA, Non_Terminal.FArgs]),
            ],
            Non_Terminal.Stmt: [
                Or(
                    [
                        Type.IF,
                        Type.LRB,
                        Non_Terminal.Exp,
                        Type.RRB,
                        Type.LCB,
                        Star([Non_Terminal.Stmt]),
                        Type.RCB,
                        Optional(
                            [
                                Type.ELSE,
                                Type.LCB,
                                Star([Non_Terminal.Stmt]),
                                Type.LCB,
                            ]
                        ),
                    ],
                    [
                        Type.WHILE,
                        Type.LRB,
                        Non_Terminal.Exp,
                        Type.LCB,
                        Star([Non_Terminal.Stmt]),
                        Type.LCB,
                    ],
                    [
                        Type.ID,
                        Non_Terminal.Field,
                        Type.EQ,
                        Non_Terminal.Exp,
                        Type.SEMICOLON,
                    ],
                    [Non_Terminal.FunCall, Type.SEMICOLON],
                    [Type.RETURN, Optional(Non_Terminal.Exp), Type.SEMICOLON],
                )
            ],
            Non_Terminal.Exp: [Non_Terminal.Eq],
            Non_Terminal.Eq: [Non_Terminal.Leq, Optional([Non_Terminal.Eq_Prime])],
            Non_Terminal.Eq_Prime: [
                Or([Type.EQ], [Type.NEQ]),
                Non_Terminal.Leq,
                Optional([Non_Terminal.Eq_Prime]),
            ],
            Non_Terminal.Leq: [
                Non_Terminal.Sum,
                Optional([Non_Terminal.Leq_Prime]),
            ],
            Non_Terminal.Leq_Prime: [
                Or([Type.LT], [Type.GT], [Type.LEQ], [Type.GEQ]),
                Non_Terminal.Sum,
                Optional([Non_Terminal.Leq_Prime]),
            ],
            Non_Terminal.Sum: [
                Non_Terminal.Fact,
                Optional([Non_Terminal.Sum_Prime]),
            ],
            Non_Terminal.Sum_Prime: [
                Or([Type.PLUS], [Type.MINUS], [Type.OR]),
                Non_Terminal.Fact,
                Optional([Non_Terminal.Sum_Prime]),
            ],
            Non_Terminal.Fact: [
                Non_Terminal.Colon,
                Optional([Non_Terminal.Fact_Prime]),
            ],
            Non_Terminal.Fact_Prime: [
                Or([Type.STAR], [Type.SLASH], [Type.PERCENT], [Type.AND]),
                Non_Terminal.Colon,
                Optional([Non_Terminal.Fact_Prime]),
            ],
            Non_Terminal.Colon: [
                Or(
                    [Non_Terminal.Basic],
                    [Non_Terminal.Basic, Type.COLON, Non_Terminal.Colon],
                )
            ],
            Non_Terminal.Basic: [
                Or(
                    [Type.LRB, Non_Terminal.Exp, Type.RRB],
                    [
                        Type.LRB,
                        Non_Terminal.Exp,
                        Type.COMMA,
                        Non_Terminal.Exp,
                        Type.RRB,
                    ],
                    [Type.INT],
                    [Type.CHAR],
                    [Type.FALSE],
                    [Type.TRUE],
                    [Non_Terminal.FunCall],
                    [Type.LSB, Type.RSB],
                    [Type.ID],
                )
            ],
        }

    # def repeat(self, t) -> List[Tree]:
    #     accumulated = []
    #     while tree := func():
    #         accumulated.append(tree)
    #     return accumulated

    # def parse(self, input: Non_Terminal, i):

    #     expected = self.grammar[input]

    #     for symbol in expected:
    #         got = []
    #         match symbol:
    #             case Or():
    #                 for OR in symbol.symbols:
    #                     longest_or = []
    #                     for or_symbol in OR:
    #                         longest_or.append(parse(or_symbol))
    #                     return max(longest_or)

    #             case Star():
    #                 for STAR in symbol.symbols:
    #                     parse_star(STAR)

    #             case Plus():
    #                 for PLUS in symbol.symbols:
    #                     for plus_symbol in PLUS:
    #                         match(plus_symbol)
    #                         parse_star(plus_symbol)

    #             case Optional():
    #                 pass

    #             case Type():
    #                 print("type", symbol)
    #             # Is single symbol:
    #             case _:
    #                 pass

    #     return []
