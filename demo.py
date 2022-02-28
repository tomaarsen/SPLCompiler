from pprint import pprint

from compiler.parser import Parser
from compiler.scanner import Scanner
from tests.test_util import open_file

program = open_file("data/given/valid/2D.spl")

scanner = Scanner(program)
tokens = scanner.scan()
# pprint(tokens)

parser = Parser(program)
tree = parser.parse(tokens)

print(tree)
