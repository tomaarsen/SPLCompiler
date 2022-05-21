from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List

from example_parser.token import Token
from example_parser.type import Type
from parser_generator.grammar import Grammar


class Node:
    pass


@dataclass
class SentenceNode(Node):
    stmts: List[StatementNode]


@dataclass
class ExpressionNode(Node):
    left: Node | Token
    operator: Token
    right: Node | Token

    def assign_left(self, new_left):
        if self.left:
            self.left.assign_left(new_left)
        else:
            self.left = new_left


@dataclass
class StatementNode(Node):
    id: Token
    expr: ExpressionNode


def default_factory(children: List[Token]):
    if len(children) != 1:
        return children
    return children[0]


def sentence_factory(children: List[Token]):
    return SentenceNode([child[0] for child in children])


def statement_factory(children: List[Token]):
    return StatementNode(children[0], children[4])


def expression_factory(children: List[Token]):
    if len(children) == 1:
        return children[0]
    elif len(children) == 2:
        children[1].assign_left(children[0])
        return children[1]
    raise Exception()


def expression_prime_factory(children: List[Token]):
    if len(children) == 2:
        return ExpressionNode(None, children[0], children[1])
    elif len(children) == 3:
        left = ExpressionNode(None, children[0], children[1])
        children[2].assign_left(left)
        return children[2]
    elif not children:
        return children
    raise Exception()


class Parser:
    def __init__(self) -> None:
        filename = os.path.join(os.path.dirname(__file__), "grammar.txt")
        terminal_mapping = {
            "id": Type.ID,
            "digit": Type.DIGIT,
            "+": Type.PLUS,
            "-": Type.MINUS,
            "*": Type.STAR,
            ";": Type.SEMICOLON,
            "<-": Type.ASSIGN,
            "(": Type.LRB,
            ")": Type.RRB,
            "$": Type.DOLLAR,
            "\\n": Type.NEWLINE,
            "\\r": Type.CARRIAGE,
        }

        non_terminal_factory_mapping = {
            "sentence": sentence_factory,
            "statement": statement_factory,
            "expression": expression_factory,
            "expression'": expression_prime_factory,
        }
        start_non_terminal = "sentence"
        error_non_terminals = ("statement", "expression")
        self.grammar = Grammar(
            "",
            filename,
            terminal_mapping=terminal_mapping,
            start_non_terminal=start_non_terminal,
            non_terminal_factory_mapping=non_terminal_factory_mapping,
            non_terminal_default_factory=default_factory,
            error_non_terminals=error_non_terminals,
        )

    def parse(self, tokens: List[Token]):
        output = self.grammar.parse(tokens)
        return output["tree"]
