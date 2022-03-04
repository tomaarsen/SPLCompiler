import re

import pytest

from compiler.error import CompilerException, ParserException
from compiler.parser import Parser
from compiler.scanner import Scanner
from compiler.tree import Tree
from tests.test_util import open_file


def test_bracket_parser(list_program: str):
    # Ensure that we can scan and parse this program without Exceptions
    scanner = Scanner(list_program)
    tokens = scanner.scan()

    parser = Parser(list_program)
    parser.parse(tokens)


def test_bracket_parser_mutation(list_program: str):
    # Perform mutation testing by removing 1 bracket
    bracket_pattern = re.compile(r"\{|\}|\[|\]|\(|\)")
    for bracket in bracket_pattern.finditer(list_program):
        mutation = list_program[: bracket.start()] + list_program[bracket.end() :]

        # Scanning must still be possible
        scanner = Scanner(mutation)
        tokens = scanner.scan()

        # Parsing must throw a CompilerException
        # TODO: This must become a ParserException
        parser = Parser(mutation)
        try:
            parser.parse(tokens)
            assert False
        except CompilerException:
            assert True


def test_parser(valid_file: str):
    # Ensure that we can scan and parse this program without Exceptions
    program: str = open_file(valid_file)

    scanner = Scanner(program)
    tokens = scanner.scan()

    parser = Parser(program)
    tree = parser.parse(tokens)
    assert tree


def test_print(valid_file: str):
    # Ensure that
    # 1. the pretty print results in the same AST as the original program
    # 2. the pretty print gives the same tokens as for the original program
    program: str = open_file(valid_file)
    scanner = Scanner(program)
    tokens = scanner.scan()
    parser = Parser(program)
    original_tree = parser.parse(tokens)

    program_pprint = str(original_tree)
    scanner_pprint = Scanner(program_pprint)
    tokens_pprint = scanner_pprint.scan()

    parser_print = Parser(program_pprint)
    pretty_print_tree = parser_print.parse(tokens_pprint)

    assert str(tokens) == str(tokens_pprint) and str(original_tree) == str(
        pretty_print_tree
    )


def test_empty():
    scanner = Scanner("")
    tokens = scanner.scan()

    parser = Parser("")
    tree = parser.parse(tokens)
    assert tree == Tree(c=[])


def test_parser_error(parser_error: str):
    program: str = open_file(parser_error)

    scanner = Scanner(program)
    tokens = scanner.scan()

    parser = Parser(program)
    with pytest.raises(ParserException) as excinfo:
        parser.parse(tokens)

    assert "ParseError" in str(excinfo.value)


def test_ClosedWrongBracketError():
    program: str = open_file("data/custom/parserError/ClosedWrongBracketError.spl")

    scanner = Scanner(program)
    tokens = scanner.scan()

    parser = Parser(program)
    with pytest.raises(ParserException) as excinfo:
        parser.parse(tokens)
    assert (
        "ClosedWrongBracketError" in str(excinfo.value)
        and "')'" in str(excinfo.value)
        and "-> 2. " in str(excinfo.value)
    )


def test_UnopenedBracketError():
    program: str = open_file("data/custom/parserError/UnopenedBracketError.spl")

    scanner = Scanner(program)
    tokens = scanner.scan()

    parser = Parser(program)

    with pytest.raises(ParserException) as excinfo:
        parser.parse(tokens)
        print(excinfo)
    assert (
        "UnopenedBracketError" in str(excinfo.value)
        and "'}'" in str(excinfo.value)
        and "-> 3. " in str(excinfo.value)
    )


def test_OpenedWrongBracketError():
    program: str = open_file("data/custom/parserError/OpenedWrongBracketError.spl")

    scanner = Scanner(program)
    tokens = scanner.scan()

    parser = Parser(program)

    with pytest.raises(ParserException) as excinfo:
        parser.parse(tokens)
    assert (
        "OpenedWrongBracketError" in str(excinfo.value)
        and "'('" in str(excinfo.value)
        and "-> 2." in str(excinfo.value)
    )


def test_UnclosedBracketError():
    program: str = open_file("data/custom/parserError/UnclosedBracketError.spl")

    scanner = Scanner(program)
    tokens = scanner.scan()

    parser = Parser(program)

    with pytest.raises(ParserException) as excinfo:
        parser.parse(tokens)
    assert (
        "UnclosedBracketError" in str(excinfo.value)
        and "'{'" in str(excinfo.value)
        and "-> 1. " in str(excinfo.value)
    )


# Put pprint in parser again and verify that ASt is the same
# One test for each Error
