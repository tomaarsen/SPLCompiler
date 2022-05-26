from compiler.generation.generator import Generator
from compiler.parser.parser import Parser
from compiler.scanner.scanner import Scanner
from compiler.typer.typer import Typer
from tests.test_util import open_file


def execute(program: str) -> str:
    scanner = Scanner(program)
    tokens = scanner.scan()

    parser = Parser(program)
    tree = parser.parse(tokens)

    typer = Typer(program)
    typer.type(tree)

    generator = Generator(tree)
    ssm_code = generator.generate()
    output = generator.run(ssm_code)
    return output


def execute_file(filename: str) -> str:
    program: str = open_file(filename)
    return execute(program)
