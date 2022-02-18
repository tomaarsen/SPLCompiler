from __future__ import annotations

import re
import stat
from abc import abstractclassmethod, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum, auto
from lib2to3.pgen2 import grammar
from os.path import abspath
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


# TODO Make all members of symbol either NT | Type | Quantifier
@dataclass
class Quantifier:
    symbols: List[NT | Type | Quantifier]

    def __init__(self, *symbols) -> None:
        self.symbols = list(symbols)

    def add(self, arg):
        self.symbols.append(arg)


class Or(Quantifier):
    # def __init__(self, *argv) -> None:
    # self.symbols = list(argv)
    def __repr__(self):
        return f"Or({self.symbols})"


class Star(Quantifier):
    def __repr__(self):
        return f"Star({self.symbols})"


class Plus(Quantifier):
    def __repr__(self):
        return f"Plus({self.symbols})"


class Optional(Quantifier):
    def __repr__(self):
        return f"Optional({self.symbols})"


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
class Parser:
    tokens: List[Token]
    grammar_file: str = None
    grammar_str: str = None
    dynamic_non_literals = None

    def __post_init__(self):
        # Pointer used with `self.tokens`
        self.i = 0
        # if there is a grammar file provided:
        if self.grammar_file:
            with open(abspath(self.grammar_file)) as file:
                data = file.read()
                self.grammar_str = data
        self.parsed_grammar = self._grammar_from_string()

        return

    # Converts self.grammar_str into a dict with keys = Non Terminals, and value = the corresponding production
    def _parse_non_terminals(self) -> dict:
        pattern = re.compile(r"(?P<Non_Terminal>\w*'?)\s*::= ", flags=re.X)
        matches = pattern.finditer(self.grammar_str)
        prev_match = None
        Non_Terminals = {}
        for match in matches:
            if match is None or match.lastgroup is None:
                raise Exception("Unmatchable")

            if prev_match is None:
                prev_match = match

            # Get the production rule
            production = self.grammar_str[prev_match.span()[1] : match.span()[0]]
            # Remove consecutive whitespace
            production = re.sub(r"\s+", " ", production)

            # Get non terminals.
            Non_Terminals[prev_match[1]] = production
            prev_match = match
        Non_Terminals[prev_match[1]] = self.grammar_str[prev_match.span()[1] :]
        return Non_Terminals

    # Number of helper functions for _parse_grammar
    @staticmethod
    def _has_star(symbol: str):
        return symbol[-1] == "*"

    @staticmethod
    def _has_plus(symbol: str):
        return symbol[-1] == "+"

    @staticmethod
    def _is_terminal(symbol: str):
        return symbol[0] == "'"

    def _is_non_terminal(self, symbol: str):
        return (
            symbol in self.dynamic_non_literals.__members__
            or symbol[:-1] in self.dynamic_non_literals.__members__
        )

    # Converts result of _parse_non_terminals() into a predefined datastructure
    def _parse_grammar(
        self,
        non_terminal: str,
        production: str,
        rule=defaultdict(list),
        i=0,
        prev_is_or=False,
    ) -> list:
        # Recursive base case
        if i >= len(production):
            return rule

        symbol = production[i]
        is_star = self._has_star(symbol)
        is_plus = self._has_plus(symbol)

        match symbol:
            # Terminals and Non-Terminals
            case s if self._is_terminal(s) or self._is_non_terminal(s):
                temp_symbol = symbol
                if is_star:
                    temp_symbol = Star(symbol[:-1])
                elif is_plus:
                    temp_symbol = Plus(symbol[:-1])

                if prev_is_or:
                    rule[non_terminal][-1].add(temp_symbol)
                    prev_is_or = False
                else:
                    rule[non_terminal].append(temp_symbol)
            # Or
            case "|":
                if not isinstance(rule[non_terminal][-1], Or):
                    # Create new OR object
                    rule[non_terminal][-1] = Or(rule[non_terminal][-1])
                prev_is_or = True
            # Opening of a sequence
            case "[" | "(":
                # Ignore for now, and combine later
                rule[non_terminal].append(symbol)
                prev_is_or = False
            # Closing a Optional sequence
            case "]":
                # Get the last index of opening bracket, in case of nested brackets
                start_index = (
                    len(rule[non_terminal]) - 1 - rule[non_terminal][::-1].index("[")
                )
                # Create empty Optional object, to which we can add symbols to.
                rule[non_terminal][start_index] = Optional()
                for optional in rule[non_terminal][start_index + 1 :]:
                    rule[non_terminal][start_index].add(optional)
                del rule[non_terminal][start_index + 1 :]
            # Closing a sequence
            case ")" | ")*" | ")+":
                # Get the last index of opening bracket, in case of nested brackets
                start_index = (
                    len(rule[non_terminal]) - rule[non_terminal][::-1].index("(") - 1
                )

                # Sequence that needs to be combined
                to_combine = rule[non_terminal][start_index + 1 :]

                # Add the combined sequence, depending on the type.
                if is_star:
                    rule[non_terminal][start_index] = Star(to_combine)
                elif is_plus:
                    rule[non_terminal][start_index] = Plus(to_combine)
                else:
                    rule[non_terminal][start_index] = to_combine

                # Remove the combined sequence
                del rule[non_terminal][start_index + 1 :]

                # If the element(s) before this sequence was an or, add to it
                if isinstance(rule[non_terminal][start_index - 1], Or):
                    rule[non_terminal][start_index - 1].add(
                        rule[non_terminal][start_index]
                    )
                    del rule[non_terminal][start_index]
            case _:
                # Ignore unrecognized symbols
                pass

        return self._parse_grammar(
            non_terminal,
            production,
            rule,
            i + 1,
            prev_is_or,
        )

    def _grammar_from_string(self):
        # Get the grammar as a dict from key non-terminal to value production
        grammar = self._parse_non_terminals()
        # From the grammar, construct an Enum of non-terminals
        self.dynamic_non_literals = Enum("NT", {k: auto() for k, _ in grammar.items()})
        # Start a new dict as the basis of the new data structure.
        structured_grammar = {}
        # For each grammar rule
        for non_terminal, segment in grammar.items():
            # Remove any leading or trailing whitespace, and split on space
            segment = segment.strip().split(" ")
            # Transform the rule to a dict of key non_terminal and value list of annotated productions
            structured_grammar = self._parse_grammar(non_terminal, segment)
            print(non_terminal, "::=", structured_grammar[non_terminal])
        self.structured_grammar = structured_grammar

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
