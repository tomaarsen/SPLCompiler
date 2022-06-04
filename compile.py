from compiler import Generator, Parser, Scanner, Typer
from compiler.typer.typer import Typer
from tests.test_util import open_file

# Load a program string,
program = open_file("data/given/valid/bool.spl")
# or define a program manually
program = r"""
main(){

}
"""

# Perform scanning on the input program
scanner = Scanner(program)
tokens = scanner.scan()

# Perform parsing on the scanned tokens
parser = Parser(program)
tree = parser.parse(tokens)

# Perform typing on the AST
typer = Typer(program)
typer.type(tree)

# Print out the typed tree
print("=" * 25)
print("Program:")
print("=" * 25)
print(tree)

# Generate the SSM Code
generator = Generator(tree)
ssm_code = generator.generate()

# Execute the SSM Code
out = generator.run(ssm_code, gui=False)

# Print out the final output
print("=" * 25)
print("Program execution output:")
print("=" * 25)
print(out)
