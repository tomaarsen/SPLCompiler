from compiler.parser.parser import Parser
from compiler.scanner.scanner import Scanner
from compiler.tree.tree import Node
from compiler.typer.typer import Typer
from tests.test_util import open_file


def type_tree(filename: str) -> Node:
    program: str = open_file(filename)

    scanner = Scanner(program)
    tokens = scanner.scan()

    parser = Parser(program)
    tree = parser.parse(tokens)

    typer = Typer(program)
    typer.type(tree)
    return tree
