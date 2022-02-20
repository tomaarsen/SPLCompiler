from __future__ import annotations

# TODO: Clean all this logging up, move it somewhere else
import logging
import re
import stat
from abc import abstractclassmethod, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from lib2to3.pgen2 import grammar
from os.path import abspath
from typing import Callable, List

from grammar_parser import NT, Optional, Or, Plus, Star

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
class Parser:
    tokens: List[Token]

    def __post_init__(self):
        # Pointer used with `self.tokens`
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
