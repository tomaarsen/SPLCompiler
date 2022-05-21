from pprint import pprint

from example_parser.parser import Parser
from example_parser.scanner import Scanner

program = """\
a <- $(1 * 3 + 9);
b <- $(7 * 8 + 11);
c <- $(11);
"""

scanner = Scanner(program)
tokens = scanner.scan()

print(tokens)
parser = Parser()
tree = parser.parse(tokens)

pprint(tree)
