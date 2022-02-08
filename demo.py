from pprint import pprint
from compiler import Scanner, Parser

with open("data/given/valid/bool.spl", "r", encoding="utf8") as f:
# with open("data/bracketed.spl", "r", encoding="utf8") as f:
# with open("data/given/invalid/unbalanced_parenthesis2.spl", "r", encoding="utf8") as f:
    program = f.read()

scanner = Scanner(program)
tokens = scanner.scan()
# pprint(tokens)

parser = Parser(program)
parser.parse(tokens)
