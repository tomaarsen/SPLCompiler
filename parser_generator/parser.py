from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Tuple

from parser_generator.generator import Opt, Or, Plus, Quantifier, Star
from parser_generator.type_vars import NT, L, N, T


@dataclass
class ParseErrorSpan:
    nt: NT
    start: int
    end: int
    active: bool = field(repr=False)
    remaining: List = field(repr=False, init=False, default_factory=list)


@dataclass
class GrammarParser:
    grammar: Dict[NT, list[Quantifier | NT | T]]
    leaves: List[L]
    non_terminal_factory_mapping: Dict[NT, Callable[[List[N | L]], N]]
    non_terminal_default_factory: Optional[Callable[[List[N | L]], N]] = (None,)
    error_non_terminals: Iterable[NT] = (None,)
    tokens: List[L] = field(repr=False, init=False, default_factory=list)

    def __post_init__(self):
        # Pointer used with `self.tokens`
        self.i = 0
        self.potential_errors: List[ParseErrorSpan] = []

    def set_tokens(self, tokens):
        self.reset(0)
        self.tokens = tokens

    @property
    def current(self) -> L:
        if self.i < len(self.tokens):
            return self.tokens[self.i]
        return None  # TODO: To avoid some errors, e.g. in match

    @property
    def onwards(self) -> List[L]:
        return self.tokens[self.i :]

    @property
    def done(self) -> bool:
        return self.i == len(self.tokens)

    def repeat(self, func: Callable) -> List[N]:
        accumulated = []
        while tree := func():
            accumulated.append(tree)
        return accumulated

    def match_type(self, *tok_types: Tuple[L]) -> bool:
        for tok_type in tok_types:
            if self.current and self.current.match(tok_type):
                try:
                    return self.current
                finally:
                    self.i += 1
        return None

    def reset(self, initial) -> None:
        self.i = initial

    def add_children(self, arguments: List[N], children: List[N] | N) -> None:
        try:
            arguments.extend(children)
        except TypeError:
            arguments.append(children)

    def parse(self, production=None, nt: Optional[NT] = None) -> N:
        """Try to match the production to self.tokens[self.i:].

        Args:
            production (_type_, optional): The production to match. If the production is None, 'nt' will be used as a starting production.
            nt (Optional[NT], optional): Starting non-terminal. Used to determine which node type to use and any possible error type.

        Returns:
            N: The matched tree.
        """
        initial = self.i

        factory = self.non_terminal_factory_mapping.get(
            nt, self.non_terminal_default_factory
        )
        arguments = []
        for i, segment in enumerate(production):
            for error in self.potential_errors:
                if error.active:
                    if error.end < self.i:
                        error.end = self.i
                        if (
                            len(error.remaining) == 1
                            and isinstance(error.remaining[0], Or)
                            and production in error.remaining[0].symbols
                        ):
                            error.remaining = production[i:]
                    if error.nt == nt and (
                        len(production[i:]) < len(error.remaining)
                        or not error.remaining
                    ):
                        error.remaining = production[i:]

            match segment:
                case Or():
                    for alternative in segment.symbols:
                        result = self.parse(alternative)
                        if result is not None:
                            self.add_children(arguments, result)
                            break
                        self.reset(initial)
                    else:
                        # If no alternative resulted in anything
                        return None

                case Star():
                    self.add_children(
                        arguments, self.repeat(lambda: self.parse(segment.symbols))
                    )

                case Plus():
                    if trees := self.repeat(lambda: self.parse(segment.symbols)):
                        self.add_children(arguments, trees)
                    else:
                        self.reset(initial)
                        return None

                case Opt():
                    match = self.parse(segment.symbols)
                    if match is not None:
                        self.add_children(arguments, match)

                case obj if obj in self.leaves:
                    match = self.match_type(segment)
                    if match is not None:
                        self.add_children(arguments, match)
                    else:
                        self.reset(initial)
                        return None

                case _:
                    if segment in self.error_non_terminals:
                        error = ParseErrorSpan(segment, self.i, self.i, active=True)
                        self.potential_errors.append(error)

                    match = self.parse(self.grammar[segment], nt=segment)
                    if segment in self.error_non_terminals:
                        error.active = False
                    if match is not None:
                        self.add_children(arguments, match)
                    else:
                        self.reset(initial)
                        return None

        tree = factory(arguments)
        return tree
