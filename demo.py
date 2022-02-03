
from pprint import pprint
from compiler import Scanner

with open("data/bool.spl", "r", encoding="utf8") as f:
    lines = f.readlines()

scanner = Scanner()
tokens = scanner.scan(lines=lines)
pprint(tokens)
