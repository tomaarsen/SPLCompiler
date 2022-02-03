

from compiler import Scanner

with open("data/bool.spl", "r", encoding="utf8") as f:
    lines = f.readlines()

scanner = Scanner()
tokens = scanner.scan(lines=lines)
print(tokens)

# from compiler import Type

# print(Type.to_type("ID"))