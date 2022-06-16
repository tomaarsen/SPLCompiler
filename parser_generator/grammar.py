from __future__ import annotations

from typing import Callable, Dict, Iterable, List, Optional

from parser_generator.generator import GrammarGenerator
from parser_generator.parser import GrammarParser
from parser_generator.type_vars import NT, L, N, T


class Grammar:
    def __init__(
        self,
        grammar_str: str,
        grammar_file: str,
        terminal_mapping: Dict[T, L],
        start_non_terminal: NT,
        non_terminal_factory_mapping: Dict[NT, Callable[[List[N | L]], N]],
        non_terminal_default_factory: Optional[Callable[[List[N | L]], N]] = None,
        # allow_error_empty: Iterable[NT] = None,
        # allow_error_nonempty: Iterable[NT] = None,
        error_non_terminals: Iterable[NT] = None,
    ) -> Grammar:
        """
        Args:
            grammar_str (str): String depicting a Grammar file, mutually exclusive with
                `grammar_file`.
            grammar_file (str): Filename pointing to a Grammar file, mutually exclusive with
                `grammar_str`.
            terminal_mapping (Dict[T, L]): Mapping of terminals (strings) to leaves (objects).
            start_non_terminal (NT): Non-terminal (string) denoting the start of the grammar.
            non_terminal_factory_mapping (Dict[NT, Callable[[List[N | L]], N]]):
                Mapping of non-terminals (strings) to a function taking a list of nodes and leaves
                as input, that returns a node.
            non_terminal_default_factory (Optional[Callable[[List[N | L]], N]]):
                Default factory function taking a list of nodes and leaves as input, that returns a
                node, that is used when a non-terminal is matched that is not a key in
                `non_terminal_factory_mapping`. Defaults to None.
            error_non_terminals (Iterable[N]): An iterator of non-terminals that can be used to
                raise an exception. Defaults to None.

        Returns:
            GrammarParser: Implements `.parse(tokens)` to parse using the grammar
        """
        self.start_non_terminal = start_non_terminal

        self.grammar = GrammarGenerator(
            grammar_str, grammar_file, terminal_mapping
        ).get_parsed_grammar()

        leaves = list(terminal_mapping.values())
        self.parser = GrammarParser(
            self.grammar,
            leaves,
            non_terminal_factory_mapping,
            non_terminal_default_factory,
            error_non_terminals,
        )

    def parse(self, tokens):
        self.parser.set_tokens(tokens)
        tree = self.parser.parse(
            self.grammar[self.start_non_terminal], self.start_non_terminal
        )

        output = {
            "tree": tree,
            "done": self.parser.done,
            "potential_errors": self.parser.potential_errors,
        }
        return output
