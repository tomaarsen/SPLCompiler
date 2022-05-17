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
    var a = 1;
    var b = [a..5];
    var c = [a..(a + 3) / 2];
    //var d = ['a'..12];
    print(b);
    print("\n");
    print(c);
    return;
}
"""

scanner = Scanner(program)
tokens = scanner.scan()

parser = Parser(program)
tree = parser.parse(tokens)

typer = Typer(program)
annotree = typer.type(tree)

print(tree)
# '''
# pprint(tree)

generator = Generator(tree)
ssm_code = generator.generate()
print(ssm_code)

tempfile_path = Path("ssm", "temp.ssm")
with open(tempfile_path, "w") as f:
    f.write(ssm_code)
out = subprocess.check_output(
    ["java", "-jar", "ssm.jar", "--cli", "--file", tempfile_path.name],
    # ["java", "-jar", "ssm.jar", "--file", tempfile_path.name],
    cwd="ssm",
)
print(out.decode())
# print("(0 is False, -1 is True)")
# 0 is False
# -1 is True

# TODO: Disallow people making print or isEmpty as functions
