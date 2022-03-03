from pprint import pprint

from compiler import Parser, Scanner
from tests.test_util import open_file

program = open_file("data/bool_broken.spl")

scanner = Scanner(program)
tokens = scanner.scan()

parser = Parser(program)
tree = parser.parse(tokens)

print(tree)
