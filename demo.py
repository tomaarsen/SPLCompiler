import os
import subprocess
import tempfile
from pathlib import Path
from pprint import pprint

from compiler import Parser, Scanner, Typer
from compiler.generator import GeneratorYielder
from tests.test_util import open_file

program = open_file("data/exp_main.spl")

scanner = Scanner(program)
tokens = scanner.scan()

parser = Parser(program)
tree = parser.parse(tokens)

typer = Typer(program)
annotree = typer.type(tree)

print(tree)
pprint(tree)

generator = GeneratorYielder()
ssm_code = "\n".join(str(line) for line in generator.visit(tree))
print(ssm_code)

tempfile_path = Path("ssm", "temp.ssm")
with open(tempfile_path, "w") as f:
    f.write(ssm_code)
out = subprocess.check_output(
    ["java", "-jar", "ssm.jar", "--cli", "--file", tempfile_path.name],
    # ["java", "-jar", "ssm.jar", "--file", tempfile_path.name], cwd="ssm"
    cwd="ssm",
)
print(out.decode())
print("(0 is False, -1 is True)")
# 0 is False
# -1 is True
