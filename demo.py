from pprint import pprint
from compiler import Scanner, Parser

with open("data/given/valid/bool.spl", "r", encoding="utf8") as f:
# with open("data/bracketed.spl", "r", encoding="utf8") as f:
# with open("data/given/invalid/unbalanced_parenthesis2.spl", "r", encoding="utf8") as f:
    program = f.read()

program = """
// At the moment, the only valid Expression is an integer
func (a, b) {
    while (a < 5) {
        a = a + 1
        b = b + 1;
        c = b + 1;
        d = b + 1;
    }

    if (a != b) {
        return b;
    }
}
"""


scanner = Scanner(program)
tokens = scanner.scan()
# pprint(tokens)

parser = Parser(program)
parser.parse(tokens)
