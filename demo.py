from pprint import pprint

from compiler import Parser, Scanner, Typer
from tests.test_util import open_file

program = open_file("data/given/valid/list.spl")
# program = open_file("data/typer_test.spl")
# program = """
# foo(a, b, c) :: Int (b, a) c -> a {
#     return (b, a);
# }

# """

# program = """

#     [Int] x = [Int];
# """


# program = """
#     g() {
#         return f(1);
#     }
#     f() {
#         return x;
#     }
#     f() {
#         return;
#     }

#     f(a) {
#         return a;
#     }
#
#
# """

# # TODO:
# program = """
# f() {
#     return;
# }

# main() {
#     var x = f();
# }
# """

scanner = Scanner(program)
tokens = scanner.scan()

parser = Parser(program)
tree = parser.parse(tokens)

typer = Typer(program)
annotree = typer.type(tree)

# pprint(tree)
print(tree)
# print(typer.i)

# breakpoint()
