from pprint import pprint

from compiler import Parser, Scanner, Typer
from tests.test_util import open_file

program = open_file("data/bool_typed.spl")

scanner = Scanner(program)
tokens = scanner.scan()

parser = Parser(program)
tree = parser.parse(tokens)

typer = Typer()
annotree = typer.type(tree)

pprint(annotree)
print(tree)
