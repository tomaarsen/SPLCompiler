from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, List

from compiler.token import Token
from compiler.tree import Tree
from compiler.type import Type


class NT(Enum):
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
    Unary = auto()
    Basic = auto()
    Field = auto()
    FunCall = auto()
    ActArgs = auto()
    Op2 = auto()
    Op1 = auto()
    int = auto()
    id = auto()


@dataclass
class Quantifier:
    symbols: List[NT | Type | Quantifier]


class Or(Quantifier):
    def __init__(self, *argv) -> None:
        self.symbols = list(argv)


class Star(Quantifier):
    pass


class Plus(Quantifier):
    pass


class Optional(Quantifier):
    pass


# TODO: Clean all this logging up, move it somewhere else
import logging

# logger = logging.basicConfig(level=logging.NOTSET)
logger = logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


def log(level=logging.DEBUG):
    def _decorator(fn):
        def _decorated(*arg, **kwargs):
            logger.log(
                level,
                f"Calling {fn.__name__!r}: {arg[1:]} with i={arg[0].i}: {arg[0].current}",
            )
            ret = fn(*arg, **kwargs)
            logger.log(
                level,
                f"Called {fn.__name__!r}: {arg[1:]} with i={arg[0].i}: {arg[0].current} got return value: {ret}",
            )
            return ret

        return _decorated

    return _decorator


@dataclass
class NewParserMatcher:
    tokens: List[Token]

    def __post_init__(self):
        self.grammar = {
            NT.SPL: [Star([NT.Decl])],
            NT.Decl: [Or([NT.VarDecl], [NT.FunDecl])],
            NT.VarDecl: [
                Or([Type.VAR], [NT.Type]),
                Type.ID,
                Type.EQ,
                NT.Exp,
                Type.SEMICOLON,
            ],
            NT.FunDecl: [
                Type.ID,
                Type.LRB,
                Optional([NT.FArgs]),
                Type.RRB,
                Optional([Type.DOUBLE_COLON, NT.FunType]),
                Type.LCB,
                Star([NT.VarDecl]),
                Plus([NT.Stmt]),
                Type.RCB,
            ],
            NT.RetType: [Or([NT.Type], [Type.VOID])],
            NT.FunType: [
                Star([NT.Type]),
                Type.ARROW,
                NT.RetType,
            ],
            NT.Type: [
                Or(
                    [NT.BasicType],
                    [
                        Type.LRB,
                        NT.Type,
                        Type.COMMA,
                        NT.Type,
                        Type.RRB,
                    ],
                    [Type.LSB, NT.Type, Type.RSB],
                    [Type.ID],
                )
            ],
            NT.BasicType: [Or([Type.INT], [Type.BOOL], [Type.CHAR])],
            NT.FArgs: [
                Type.ID,
                Optional([Type.COMMA, NT.FArgs]),
            ],
            NT.Stmt: [
                Or(
                    [
                        Type.IF,
                        Type.LRB,
                        NT.Exp,
                        Type.RRB,
                        Type.LCB,
                        Star([NT.Stmt]),
                        Type.RCB,
                        Optional(
                            [
                                Type.ELSE,
                                Type.LCB,
                                Star([NT.Stmt]),
                                Type.RCB,
                            ]
                        ),
                    ],
                    [
                        Type.WHILE,
                        Type.LRB,
                        NT.Exp,
                        Type.RRB,
                        Type.LCB,
                        Star([NT.Stmt]),
                        Type.RCB,
                    ],
                    [
                        Type.ID,
                        Optional([NT.Field]),
                        Type.EQ,
                        NT.Exp,
                        Type.SEMICOLON,
                    ],
                    [NT.FunCall, Type.SEMICOLON],
                    [Type.RETURN, Optional([NT.Exp]), Type.SEMICOLON],
                )
            ],
            NT.Exp: [NT.Eq],
            NT.Eq: [NT.Leq, Optional([NT.Eq_Prime])],
            NT.Eq_Prime: [
                Or([Type.DEQUALS], [Type.NEQ]),
                NT.Leq,
                Optional([NT.Eq_Prime]),
            ],
            NT.Leq: [
                NT.Sum,
                Optional([NT.Leq_Prime]),
            ],
            NT.Leq_Prime: [
                Or([Type.LT], [Type.GT], [Type.LEQ], [Type.GEQ]),
                NT.Sum,
                Optional([NT.Leq_Prime]),
            ],
            NT.Sum: [
                NT.Fact,
                Optional([NT.Sum_Prime]),
            ],
            NT.Sum_Prime: [
                Or([Type.PLUS], [Type.MINUS], [Type.OR]),
                NT.Fact,
                Optional([NT.Sum_Prime]),
            ],
            NT.Fact: [
                NT.Colon,
                Optional([NT.Fact_Prime]),
            ],
            NT.Fact_Prime: [
                Or([Type.STAR], [Type.SLASH], [Type.PERCENT], [Type.AND]),
                NT.Colon,
                Optional([NT.Fact_Prime]),
            ],
            NT.Colon: [NT.Unary, Optional([Type.COLON, NT.Colon])],
            NT.Unary: [Or([Or([Type.NOT], [Type.MINUS]), NT.Unary], [NT.Basic])],
            NT.Basic: [
                Or(
                    [
                        Type.LRB,
                        NT.Exp,
                        Optional(
                            [
                                Type.COMMA,
                                NT.Exp,
                            ]
                        ),
                        Type.RRB,
                    ],
                    [Type.DIGIT],
                    [Type.QUOTE],
                    [Type.FALSE],
                    [Type.TRUE],
                    [NT.FunCall],
                    [Type.LSB, Type.RSB],
                    [Type.ID, Optional([NT.Field])],
                )
            ],
            NT.Field: [Plus([Or([Type.HD], [Type.TL], [Type.FST], [Type.SND])])],
            NT.FunCall: [
                Type.ID,
                Type.LRB,
                Optional([NT.ActArgs]),
                Type.RRB,
            ],
            NT.ActArgs: [NT.Exp, Optional([Type.COMMA, NT.ActArgs])],
        }

        # Pointer on `self.tokens`
        self.i = 0

    @property
    def current(self) -> Token:
        if self.i < len(self.tokens):
            return self.tokens[self.i]
        return Token(" ", Type.SPACE)  # TODO: To avoid some errors, e.g. in match

    @property
    def onwards(self) -> List[Token]:
        return self.tokens[self.i :]

    def repeat(self, func: Callable) -> List[Tree]:
        accumulated = []
        while tree := func():
            accumulated.append(tree)
        return accumulated

    def add(self, value: str) -> True:
        self.suggestions.add(value)
        return True

    def remove(self, value: str) -> True:
        self.suggestions.remove(value)
        return True

    @log()
    def match_type(self, *tok_types: Type) -> bool:
        if self.current.type in tok_types:
            try:
                return self.current
            finally:
                self.i += 1
        return None

    def reset(self, initial) -> None:
        self.i = initial

    # @log()
    def parse(self, production=None):
        """
        Goal: (Not yet implemented)

        If `NT.Decl: [Or([NT.VarDecl], [NT.FunDecl])]` fails, then we must retry this rule
        but with some fixing enabled.
        """
        initial = self.i

        if production is None:
            production = [NT.SPL]

        tree = Tree()
        for segment in production:
            match segment:
                case Or():
                    for alternative in segment.symbols:
                        if result := self.parse(alternative):
                            tree.add_child(result)
                            break
                        self.reset(initial)
                    else:
                        # If no alternative resulted in anything
                        return None

                case Star():
                    tree.add_children(self.repeat(lambda: self.parse(segment.symbols)))

                case Plus():
                    if trees := self.repeat(lambda: self.parse(segment.symbols)):
                        tree.add_children(trees)
                    else:
                        self.reset(initial)
                        return None

                case Optional():
                    if match := self.parse(segment.symbols):
                        tree.add_child(match)

                case Type():
                    if match := self.match_type(segment):
                        tree.add_child(match)
                    else:
                        """
                        Alternative 1:
                            Grammar: a b c d e f
                            Program: a b e f
                            Solution: Insert tokens in program.

                            We can look-ahead to see if the current token matches an upcoming production segment.
                            (But we can only look inside of this production, and not outside of it)
                            Technically, as easy as not returning `return None`, and just continuing as if
                            the production segment was matched.

                            To match: Exp
                            Program: `+4;`
                            Not a single token can be matched.

                        Alternative 2:
                            Grammar: a b e f
                            Program: a b c d e f
                            Solution: Delete tokens in program.

                            We can look-ahead to see if the current production segment matches an upcoming program token.
                            Technically, as easy as incrementing the pointer `self.i` by some number and retrying `self.match_type(segment)`.
                            Probably less common in practice, and thus less important.
                        """
                        self.reset(initial)
                        return None

                case NT():
                    if match := self.parse(self.grammar[segment]):
                        tree.add_child(match)
                    else:
                        self.reset(initial)
                        return None

                # Is single symbol:
                case _:
                    # This shouldn't occur, right?
                    raise Exception(segment)

        # If the tree only has one child, return the child instead
        if len(tree) == 1:
            return tree[0]

        return tree
