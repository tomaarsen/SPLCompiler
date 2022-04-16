from pprint import pprint

from compiler import Parser, Scanner, Typer
from tests.test_util import open_file

# program = open_file("data/given/valid/SumProduct.spl")
program = open_file("data/given/valid/bool.spl")
# program = """
# foo(a, b, c) :: Int (b, a) c -> a {
#     return (b, a);
# }

#  """

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
# TODO:
# program = """
#     f(x) {
#         return g(x);
#     }
# """

# Is this allowed?
# program = """
#     var y = 12;

#     f(x) {
#         var y = y + 1;
#         return x;
#     }
# """

# program = """
# fib(n) {
#     if (n == 0){
#         return 0;
#     }

#     if (n <= 2){
#         return 1;
#     }

#     return fib(n - 1) + fib(n - 2);
# }

# var x = 1 : 2 : 3 : 4 : [];
#     """


# program = """
# addOne(a) {
#     if (a > 5){
#         return a;
#     } else {
#         a = a + 1;
#     }
# }
# """
# '''
# program = """
# addOne(a) {
#     if (a > 5){
#         return a;
#     } else {
#         a = a + 1;
#         return a;
#     }
#     print(a);
# }

# main(){
#     print(addOne(4));
# }
"""
# '''
# program = """
# var id = get_index();

# get_index() {
#     return 12;
# }
# """

program = """


f(x) :: Int -> Int{
    var x = 1;
}

"""

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
