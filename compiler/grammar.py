from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from compiler.grammar_parser import GRAMMAR, NT, Opt, Or, Plus, Star
from compiler.token import Token
from compiler.tree import Tree
from compiler.type import Type

# Allow a non-terminal of this type to be raised as
# an exception, but only if the production was at least partially matched
ALLOW_NONEMPTY = (
    NT.Return,
    NT.IfElse,
    NT.While,
    NT.StmtAss,
)

# Allow a non-terminal of this type to be raised as
# an exception, even if none of the production was matched
ALLOW_EMPTY = (
    NT.VarDecl,
    NT.FunDecl,
    NT.RetType,
    NT.FunType,
    # NT.Type,
    # NT.BasicType,
    NT.FArgs,
    NT.Stmt,
    NT.ActArgs,
    # NT.Exp,
)

# Combination of the two, i.e. this type can be raised as an exception
ALLOW = (*ALLOW_NONEMPTY, *ALLOW_EMPTY)


@dataclass
class ParseErrorSpan:
    nt: NT
    start: int
    end: int
    active: bool = field(repr=False)
    remaining: List = field(repr=False, init=False, default_factory=list)


@dataclass
class Grammar:
    tokens: List[Token]

    def __post_init__(self):
        # Pointer used with `self.tokens`
        self.i = 0
        self.grammar = GRAMMAR

        self.potential_errors: List[ParseErrorSpan] = []

    @property
    def current(self) -> Token:
        if self.i < len(self.tokens):
            return self.tokens[self.i]
        return Token(" ", Type.SPACE)  # TODO: To avoid some errors, e.g. in match

    @property
    def onwards(self) -> List[Token]:
        return self.tokens[self.i :]

    @property
    def done(self) -> bool:
        return self.i == len(self.tokens)

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

    def match_type(self, *tok_types: Type) -> bool:
        if self.current.type in tok_types:
            try:
                return self.current
            finally:
                self.i += 1
        return None

    def reset(self, initial) -> None:
        self.i = initial

    def parse(self, production=None, non_terminal: Opt[NT] = None) -> Tree:
        initial = self.i

        if production is None:
            production = [NT.SPL]

        tree = Tree()
        for i, segment in enumerate(production):
            for error in self.potential_errors:
                if error.active:
                    if error.end < self.i:
                        error.end = self.i
                    if error.nt == non_terminal:
                        error.remaining = production[i:]

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

                case Opt():
                    if match := self.parse(segment.symbols):
                        tree.add_child(match)

                case Type():
                    if match := self.match_type(segment):
                        tree.add_child(match)
                    else:
                        self.reset(initial)
                        return None

                case NT():
                    if segment in ALLOW:
                        error = ParseErrorSpan(segment, self.i, self.i, active=True)
                        self.potential_errors.append(error)

                    if match := self.parse(self.grammar[segment], non_terminal=segment):
                        tree.add_child(match)
                        if segment in ALLOW:
                            error.active = False
                    else:
                        if segment in ALLOW:
                            error.active = False
                        self.reset(initial)
                        return None

                # Is single symbol:
                case _:
                    raise Exception(segment)

        # If the tree only has one child, return the child instead
        if len(tree) == 1:
            return tree[0]

        return tree
