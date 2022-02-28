from __future__ import annotations

# TODO: Clean all this logging up, move it somewhere else
import logging
import os
from dataclasses import dataclass
from pprint import pprint
from typing import Callable, List

from compiler.grammar_parser import GrammarParser

"""
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
"""

from compiler.token import Token
from compiler.tree import Tree
from compiler.type import Type

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
class Grammar:
    tokens: List[Token]

    def __post_init__(self):
        # Pointer used with `self.tokens`
        self.i = 0
        gp = GrammarParser(
            grammar_file=os.path.join(os.path.dirname(__file__), "grammar.txt")
        )
        self.grammar = gp.get_parsed_grammar()

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
    def parse(self, production=None, fix_level: int = 0):
        """
        Goal: (Not yet implemented)

        If `NT.Decl: [Or([NT.VarDecl], [NT.FunDecl])]` fails, then we must retry this rule
        but with some fixing enabled.
        """
        from compiler.grammar_parser import NT, Optional, Or, Plus, Star

        def fail(production, fix_level: int):
            if production == [NT.SPL] and fix_level <= 5:
                return self.parse(production, fix_level=fix_level + 1)
            return None

        initial = self.i
        # root = False

        if production is None:
            # print("Setting root = True")
            production = [NT.SPL]
            # root = True

        tree = Tree()
        for segment in production:
            match segment:
                case Or():
                    for alternative in segment.symbols:
                        if result := self.parse(alternative, fix_level=fix_level):
                            tree.add_child(result)
                            break
                        self.reset(initial)
                    else:
                        # If no alternative resulted in anything
                        return fail(production, fix_level)

                case Star():
                    tree.add_children(
                        self.repeat(
                            lambda: self.parse(segment.symbols, fix_level=fix_level)
                        )
                    )

                case Plus():
                    if trees := self.repeat(
                        lambda: self.parse(segment.symbols, fix_level=fix_level)
                    ):
                        tree.add_children(trees)
                    else:
                        self.reset(initial)
                        return fail(production, fix_level)

                case Optional():
                    if match := self.parse(segment.symbols, fix_level=fix_level):
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
                        return fail(production, fix_level)

                case NT():
                    if match := self.parse(self.grammar[segment], fix_level=fix_level):
                        tree.add_child(match)
                    else:
                        self.reset(initial)
                        return fail(production, fix_level)

                # Is single symbol:
                case _:
                    # This shouldn't occur, right?
                    raise Exception(segment)

        # If the tree only has one child, return the child instead
        if len(tree) == 1:
            return tree[0]

        return tree
