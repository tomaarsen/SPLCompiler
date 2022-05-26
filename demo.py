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
    int x = 13;

    for i in [1..5]{
        if (i > 3){
            println("> 3");
            break;
        }
        println(i);
    }

    print('\n');

    while (x > 7){
        x = x - 1;
        if (x < 10){
            println("< 10");
            break;
        }
        println(x);
    }
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
