from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from compiler.grammar_parser import GRAMMAR, NT, Opt, Or, Plus, Star
from compiler.token import Token
from compiler.type import Type

from compiler.tree import (  # isort:skip
    BasicFactory,
    BasicTypeFactory,
    DefaultFactory,
    ExpFactory,
    ExpPrimeFactory,
    FunDeclFactory,
    NodeFactory,
    Op2Node,
    SPLFactory,
    Tree,
    TypeFactory,
    VarDeclFactory,
)

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

    def parse(
        self, production=None, tree: NodeFactory = None, nt: Optional[NT] = None
    ) -> Tree:
        initial = self.i

        if production is None:
            production = [NT.SPL]

        trees_dict = {
            NT.SPL: SPLFactory(),
            NT.Exp: ExpFactory(),
            NT["Eq'"]: ExpPrimeFactory(),
            NT.Sum: ExpFactory(),
            NT["Sum'"]: ExpPrimeFactory(),
            NT.Fact: ExpFactory(),
            NT["Fact'"]: ExpPrimeFactory(),
            NT.Leq: ExpFactory(),
            NT["Leq'"]: ExpPrimeFactory(),
            NT.Unary: ExpFactory(),
            NT.Colon: ExpFactory(),  # TODO: Fix this
            NT.Basic: BasicFactory(),
            NT.VarDecl: VarDeclFactory(),
            NT.FunDecl: FunDeclFactory(),
            NT.Type: TypeFactory(),
            NT.BasicType: BasicTypeFactory(),
        }

        # print(nt, production)
        # if nt:
        # tree = trees_dict[nt]
        tree = trees_dict.get(nt, DefaultFactory())
        # else:
        #     tree = Tree(nt)

        # tree = trees_dict[nt]
        for i, segment in enumerate(production):
            for error in self.potential_errors:
                if error.active:
                    if error.end < self.i:
                        error.end = self.i
                    if error.nt == nt:
                        error.remaining = production[i:]

            match segment:
                case Or():
                    for alternative in segment.symbols:
                        if result := self.parse(alternative):
                            tree.add_children(result)
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
                        tree.add_children(match)

                case Type():
                    if match := self.match_type(segment):
                        tree.add_children(match)
                    else:
                        self.reset(initial)
                        return None

                case NT():
                    if segment in ALLOW:
                        error = ParseErrorSpan(segment, self.i, self.i, active=True)
                        self.potential_errors.append(error)

                    if match := self.parse(self.grammar[segment], nt=segment):
                        tree.add_children(match)
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

        # print(production)
        # print(tree)

        # tree = tree.build()
        if isinstance(tree, NodeFactory):
            tree = tree.build()

        # If the tree only has one child, return the child instead
        elif len(tree) == 1:
            return tree[0]

        return tree
