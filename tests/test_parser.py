import re
from compiler.error import CompilerException
from compiler.parser import Parser
from compiler.scanner import Scanner


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
