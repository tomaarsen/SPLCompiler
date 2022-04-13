from pprint import pprint

from compiler import Parser, Scanner, Typer
from tests.test_util import open_file

# program = open_file("data/given/valid/SumProduct.spl")
program = open_file("data/typer_test.spl")

scanner = Scanner(program)
tokens = scanner.scan()

parser = Parser(program)
tree = parser.parse(tokens)

typer = Typer(program)
annotree = typer.type(tree)

# pprint(tree)
print(tree)
# print(typer.i)

# breakpoint()
