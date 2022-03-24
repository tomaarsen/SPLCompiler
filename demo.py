from pprint import pprint

from compiler import Parser, Scanner, Typer
from tests.test_util import open_file

# program = open_file("data/given/valid/brainfuck.spl")
program = open_file("data/return_types.spl")

scanner = Scanner(program)
tokens = scanner.scan()

parser = Parser(program)
tree = parser.parse(tokens)

typer = Typer()
annotree = typer.type(tree)

# pprint(tree)
print(tree)
# print(typer.i)

# breakpoint()
