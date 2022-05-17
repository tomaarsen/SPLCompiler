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
fun(a, b){
    var c = 12;
    var d = 24;
    for i in [0..5]{
        println(i);
        for j in [1..6]{
            print('\t');
            println(j);
        }
    }
    for i in [0..5]{
        print(i);
    }
    return;
}
main(){
    fun(4, 8);
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

tempfile_path = Path("ssm", "temp.ssm")
with open(tempfile_path, "w") as f:
    f.write(ssm_code)
out = subprocess.check_output(
    ["java", "-jar", "ssm.jar", "--cli", "--file", tempfile_path.name],
    # ["java", "-jar", "ssm.jar", "--guidelay", "1", "--file", tempfile_path.name],
    cwd="ssm",
)
print(out.decode())
# print("(0 is False, -1 is True)")
# 0 is False
# -1 is True
# '''
# TODO: Disallow people making print or isEmpty as functions
