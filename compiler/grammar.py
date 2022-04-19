from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List, Optional

from compiler.grammar_parser import GRAMMAR, NT, Opt, Or, Plus, Star
from compiler.token import Token
from compiler.type import Type

from compiler.tree.factory import (  # isort:skip
    BasicFactory,
    BasicTypeFactory,
    ColonFactory,
    CommaFactory,
    DefaultFactory,
    ExpFactory,
    ExpPrimeFactory,
    FieldFactory,
    FunCallFactory,
    FunDeclFactory,
    FunTypeFactory,
    RetTypeFactory,
    IfElseFactory,
    Node,
    ReturnFactory,
    SPLFactory,
    StmtAssFactory,
    StmtFactory,
    TypeFactory,
    UnaryFactory,
    VarDeclFactory,
    WhileFactory,
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
    NT.FArgs,
    NT.Stmt,
    NT.ActArgs,
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

    def repeat(self, func: Callable) -> List[Node]:
        accumulated = []
        while tree := func():
            accumulated.append(tree)
        # if len(accumulated) == 1:
        #     return accumulated[0]
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

    def parse(self, production=None, nt: Optional[NT] = None) -> Node:
        initial = self.i

        if production is None:
            production = [NT.SPL]

        trees_dict = {
            NT.SPL: SPLFactory(),
            NT.VarDecl: VarDeclFactory(),
            NT.FunDecl: FunDeclFactory(),
            NT.RetType: RetTypeFactory(),
            NT.FunType: FunTypeFactory(),
            NT.Type: TypeFactory(),
            NT.BasicType: BasicTypeFactory(),
            NT.FArgs: CommaFactory(),
            NT.Stmt: StmtFactory(),
            NT.StmtAss: StmtAssFactory(),
            NT.IfElse: IfElseFactory(),
            NT.While: WhileFactory(),
            NT.Return: ReturnFactory(),
            NT.Exp: ExpFactory(),
            NT["Or'"]: ExpPrimeFactory(),
            NT.And: ExpFactory(),
            NT["And'"]: ExpPrimeFactory(),
            NT.Eq: ExpFactory(),
            NT["Eq'"]: ExpPrimeFactory(),
            NT.Leq: ExpFactory(),
            NT["Leq'"]: ExpPrimeFactory(),
            NT.Sum: ExpFactory(),
            NT["Sum'"]: ExpPrimeFactory(),
            NT.Fact: ExpFactory(),
            NT["Fact'"]: ExpPrimeFactory(),
            NT.Colon: ColonFactory(),
            NT.Unary: UnaryFactory(),
            NT.Basic: BasicFactory(),
            NT.Field: FieldFactory(),
            NT.FunCall: FunCallFactory(),
            NT.ActArgs: CommaFactory(),
        }

        tree = trees_dict.get(nt, DefaultFactory())
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
                        result = self.parse(alternative)
                        if result is not None:
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
                    match = self.parse(segment.symbols)
                    if match is not None:
                        tree.add_children(match)

                case Type():
                    match = self.match_type(segment)
                    if match is not None:
                        tree.add_children(match)
                    else:
                        self.reset(initial)
                        return None

                case NT():
                    if segment in ALLOW:
                        error = ParseErrorSpan(segment, self.i, self.i, active=True)
                        self.potential_errors.append(error)

                    match = self.parse(self.grammar[segment], nt=segment)
                    if match is not None:
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

        tree = tree.build()

        return tree
