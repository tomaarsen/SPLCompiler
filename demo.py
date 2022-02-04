
from pprint import pprint
from compiler import Scanner, Parser

# with open("data/given/valid/bool.spl", "r", encoding="utf8") as f:
with open("data/commented.spl", "r", encoding="utf8") as f:
    program = f.read()

scanner = Scanner(program)
tokens = scanner.scan()
# pprint(tokens)

parser = Parser()
parser.parse(tokens)
