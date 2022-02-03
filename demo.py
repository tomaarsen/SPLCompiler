
from pprint import pprint
from compiler import Scanner

with open("data/commented.spl", "r", encoding="utf8") as f:
    program = f.read()

scanner = Scanner()
tokens = scanner.scan(program)
pprint(tokens)
