import os
import re
from dataclasses import dataclass, field
from enum import Enum, auto
from os.path import abspath

from compiler.type import Type
from tests.test_util import open_file


class NT(Enum):
    pass


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
class GrammarParser:
    grammar_str: str = None
    grammar_file: str = None
    terminal_mapping: dict[str, Type] = field(
        default_factory=lambda: {
            "(": Type.LRB,
            ")": Type.RRB,
            "{": Type.LCB,
            "}": Type.RCB,
            "[": Type.LSB,
            "]": Type.RSB,
            ";": Type.SEMICOLON,
            "::": Type.DOUBLE_COLON,
            "->": Type.ARROW,
            ",": Type.COMMA,
            "+": Type.PLUS,
            "-": Type.MINUS,
            "*": Type.STAR,
            "/": Type.SLASH,
            "^": Type.POWER,
            "%": Type.PERCENT,
            "==": Type.DEQUALS,
            "<=": Type.LEQ,
            ">=": Type.GEQ,
            "<": Type.LT,
            ">": Type.GT,
            "!=": Type.NEQ,
            "=": Type.EQ,
            "&&": Type.AND,
            "||": Type.OR,
            ":": Type.COLON,
            "!": Type.NOT,
            ".hd": Type.HD,
            ".tl": Type.TL,
            ".fst": Type.FST,
            ".snd": Type.SND,
            "if": Type.IF,
            "else": Type.ELSE,
            "while": Type.WHILE,
            "return": Type.RETURN,
            "Void": Type.VOID,
            "Int": Type.INT,
            "Bool": Type.BOOL,
            "Char": Type.CHAR,
            "False": Type.FALSE,
            "True": Type.TRUE,
            "var": Type.VAR,
            "id": Type.ID,
            "int": Type.DIGIT,
            "char": Type.CHARACTER,
            " ": Type.SPACE,
        },
        init=False,
        repr=False,
    )

    def __post_init__(self) -> None:
        if not self.grammar_file and not self.grammar_str:
            raise Exception("Must provide either grammar_str or grammar_file.")

        # If there is a grammar file provided:
        if self.grammar_file:
            self.grammar_str = open_file(abspath(self.grammar_file))

        # Convert string to structured data
        self.parsed_grammar = self._grammar_from_string()

    # Getter method
    def get_parsed_grammar(self) -> dict[NT, list[Quantifier | NT | Type]]:
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
                raise Exception("Unmatchable")

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

    @staticmethod
    def _is_non_terminal(symbol: str) -> bool:
        return symbol in NT.__members__ or symbol[:-1] in NT.__members__

    def _apply_terminal_mapping(self, symbol: str) -> Type | NT:
        # Remove any possible plus or star
        if symbol[-1] == "+" or symbol[-1] == "*":
            symbol = symbol[:-1]
        # Remove any possible quotes of terminals
        if symbol[0] == "'":
            symbol = symbol[1:-1]

        # Check if we have a terminal or non-terminal:
        if symbol in self.terminal_mapping:
            return self.terminal_mapping[symbol]
        global NT
        return NT[symbol]

    # Converts result of _parse_non_terminals() into a predefined datastructure
    def _parse_grammar(
        self,
        production: str,
        rule=None,
        i=0,
        prev_is_or=False,
    ) -> list[Quantifier | NT | Type]:
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

    def _grammar_from_string(self) -> dict[NT, list[Quantifier | NT | Type]]:
        # Get the grammar as a dict from key non-terminal to value production
        grammar = self._parse_non_terminals()
        # From the grammar, construct an Enum of non-terminals
        global NT
        NT = Enum("NT", {k: auto() for k, _ in grammar.items()}, module=__name__)
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


GRAMMAR = GrammarParser(
    grammar_file=os.path.join(os.path.dirname(__file__), "grammar.txt")
).get_parsed_grammar()
