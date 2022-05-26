import os
import subprocess
import tempfile
from pathlib import Path
from pprint import pprint

from compiler import Parser, Scanner, Typer
from compiler.generation.generator import Generator
from tests.test_util import open_file

program = open_file("data/global_vars.spl")

program = r"""
main(){
    Var a = "hello\nthere";
    print(a);
}
"""

scanner = Scanner(program)
tokens = scanner.scan()

parser = Parser(program)
tree = parser.parse(tokens)

typer = Typer(program)
annotree = typer.type(tree)

print("=" * 25)
print("Program:")
print("=" * 25)
print(tree)
# '''
# pprint(tree)

generator = Generator(tree)
ssm_code = generator.generate()
# print(ssm_code)
print("=" * 25)
print("Program execution output:")
print("=" * 25)

out = generator.run(ssm_code, gui=False)
print(out)
# print("(0 is False, -1 is True)")
# 0 is False
# -1 is True
# '''
# TODO: Disallow people making print or isEmpty as functions
