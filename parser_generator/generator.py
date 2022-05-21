import re
from dataclasses import dataclass, field
from os.path import abspath

from parser_generator.type_vars import NT, L, T
from tests.test_util import open_file


class Quantifier:
    def __init__(self, *symbols: tuple) -> None:
        self.symbols = list(symbols)

    def add(self, arg: str) -> None:
        self.symbols.append(arg)


class Or(Quantifier):
    def __repr__(self) -> str:
        return f"Or({self.symbols})"


class Star(Quantifier):
    def __repr__(self) -> str:
        return f"Star({self.symbols})"


class Plus(Quantifier):
    def __repr__(self) -> str:
        return f"Plus({self.symbols})"


class Opt(Quantifier):
    def __repr__(self) -> str:
        return f"Opt({self.symbols})"


@dataclass
class GrammarGenerator:
    grammar_str: str = None
    grammar_file: str = None
    terminal_mapping: dict[T, L] = field(repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        if not self.grammar_file and not self.grammar_str:
            from compiler.error.error import UnrecoverableError

            UnrecoverableError("Must provide either grammar_str or grammar_file.")

        # If there is a grammar file provided:
        if self.grammar_file:
            self.grammar_str = open_file(abspath(self.grammar_file))

        # Convert string to structured data
        self.parsed_grammar = self._grammar_from_string()

    # Getter method
    def get_parsed_grammar(self) -> dict[NT, list[Quantifier | NT | L]]:
        return self.parsed_grammar

    # Converts self.grammar_str into a dict with keys = Non Terminals, and values = the parsed production
    def _parse_non_terminals(self) -> dict[str, str]:
        # Match Non Terminals as the left hand side of '::='
        pattern = re.compile(r"(?P<Non_Terminal>\w*'?)\s*::= ", flags=re.X)
        matches = pattern.finditer(self.grammar_str)
        prev_match = None
        Non_Terminals = {}
        for match in matches:
            if match is None or match.lastgroup is None:
                from compiler.error.error import UnrecoverableError

                UnrecoverableError("Unmatchable match when parsing non terminals.")

            if prev_match is None:
                prev_match = match

            # Get the production rule
            production = self.grammar_str[prev_match.span()[1] : match.span()[0]]
            # Remove consecutive whitespace
            production = re.sub(r"\s+", " ", production)

            # Get non terminals
            Non_Terminals[prev_match[1]] = production
            prev_match = match

        Non_Terminals[prev_match[1]] = self.grammar_str[prev_match.span()[1] :]
        return Non_Terminals

    # Number of helper functions for _parse_grammar
    @staticmethod
    def _has_star(symbol: str) -> bool:
        return symbol[-1] == "*"

    @staticmethod
    def _has_plus(symbol: str) -> bool:
        return symbol[-1] == "+"

    @staticmethod
    def _is_terminal(symbol: str) -> bool:
        return symbol[0] == "'"

    @staticmethod
    def _peek(production: list[str], i: int) -> str | None:
        if len(production) - 1 >= i:
            return production[i]
        return None

    def _is_non_terminal(self, symbol: str) -> bool:
        return symbol in self.non_terminals or (
            symbol[-1] in "+*" and symbol[:-1] in self.non_terminals
        )

    def _apply_terminal_mapping(self, symbol: str) -> L | NT:
        # Remove any possible plus or star
        if symbol[-1] == "+" or symbol[-1] == "*":
            symbol = symbol[:-1]
        # Remove any possible quotes of terminals
        if symbol[0] == "'":
            symbol = symbol[1:-1]

        # Check if we have a terminal or non-terminal:
        if symbol in self.terminal_mapping:
            return self.terminal_mapping[symbol]
        return symbol

    # Converts result of _parse_non_terminals() into a predefined datastructure
    def _parse_grammar(
        self,
        production: str,
        rule=None,
        i=0,
        prev_is_or=False,
    ) -> list[Quantifier | NT | L]:
        if rule is None:
            rule = []

        # Recursive base case
        if i >= len(production):
            return rule

        symbol = production[i]
        is_star = self._has_star(symbol)
        is_plus = self._has_plus(symbol)

        match symbol:
            # Terminals and Non-Terminals
            case s if self._is_terminal(s) or self._is_non_terminal(s):
                temp_symbol = self._apply_terminal_mapping(symbol)
                if is_star:
                    temp_symbol = Star(self._apply_terminal_mapping(symbol))
                elif is_plus:
                    temp_symbol = Plus(self._apply_terminal_mapping(symbol))

                if prev_is_or:
                    rule[-1].add([temp_symbol])
                    prev_is_or = False
                else:
                    rule.append(temp_symbol)
            # Or
            case "|":
                if not isinstance(rule[-1], Or):
                    # Create new OR object
                    rule[-1] = Or([rule[-1]])
                prev_is_or = True
            # Opening of a sequence
            case "[" | "(":
                # Ignore for now, and combine later
                rule.append(symbol)
                prev_is_or = False
            # Closing a Optional sequence
            case "]":
                # Get the last index of opening bracket, in case of nested brackets
                start_index = len(rule) - 1 - rule[::-1].index("[")
                # Create empty Opt object, to which we can add symbols to.
                rule[start_index] = Opt()
                for optional in rule[start_index + 1 :]:
                    rule[start_index].add(optional)
                del rule[start_index + 1 :]
            # Closing a sequence
            case ")" | ")*" | ")+":
                # Get the last index of opening bracket, in case of nested brackets
                start_index = len(rule) - rule[::-1].index("(") - 1

                # Sequence that needs to be combined
                to_combine = rule[start_index + 1 :]
                # Remove the sequence including the '('
                del rule[start_index:]

                # Add the combined sequence, depending on the type.
                if is_star:
                    star = Star()
                    for s in to_combine:
                        star.add(s)
                    to_combine = [star]
                elif is_plus:
                    plus = Plus()
                    for p in to_combine:
                        plus.add(p)
                    to_combine = [plus]

                # Previous is Or
                if start_index != 0 and isinstance(rule[start_index - 1], Or):
                    if len(to_combine) == 1:
                        to_combine = to_combine[0]
                    rule[start_index - 1].add(to_combine)
                    return self._parse_grammar(
                        production,
                        rule,
                        i + 1,
                        prev_is_or,
                    )
                elif self._peek(production, i + 1) == "|":
                    to_combine = [Or(to_combine)]

                # We need to add to_combine, which is either a plus, star or a list
                if len(to_combine) == 1:
                    to_combine = to_combine[0]
                rule.append(to_combine)

        return self._parse_grammar(
            production,
            rule,
            i + 1,
            prev_is_or,
        )

    def _grammar_from_string(self) -> dict[NT, list[Quantifier | NT | L]]:
        # Get the grammar as a dict from key non-terminal to value production
        grammar = self._parse_non_terminals()
        # From the grammar, construct an Enum of non-terminals
        self.non_terminals = list(grammar.keys())
        # Start a new dict as the basis of the new data structure
        structured_grammar = {}
        # For each rule:
        for non_terminal, segment in grammar.items():
            # Remove any leading or trailing whitespace, and split on spaces
            segment = segment.strip().split(" ")
            # Transform the rule to a dict with key non_terminal and value list of annotated productions
            structured_grammar[non_terminal] = self._parse_grammar(segment)
        return {
            self._apply_terminal_mapping(key): value
            for key, value in structured_grammar.items()
        }
