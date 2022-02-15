from pprint import pprint

from compiler import Parser, Scanner

with open("data/given/valid/bool.spl", "r", encoding="utf8") as f:
    # with open("data/bracketed.spl", "r", encoding="utf8") as f:
    # with open("data/given/invalid/unbalanced_parenthesis2.spl", "r", encoding="utf8") as f:
    program = f.read()

program = """
// At the moment, the only valid Expression is an integer
func (a, b) {
    while (a < 5) {
        a = a + 1;
    }

    if (a != b) {
        return b;
    }
}
"""

program = """
var a = 4 / 1 + 2 * 3 == 5 > 3;
"""


scanner = Scanner(program)
tokens = scanner.scan()
# pprint(tokens)

parser = Parser(program)
parser.parse(tokens)
