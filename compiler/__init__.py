import sys

from compiler.generation.generator import Generator
from compiler.parser.parser import Parser
from compiler.scanner.scanner import Scanner
from compiler.token import Token
from compiler.type import Type
from compiler.typer.typer import Typer

# Default is 1000
sys.setrecursionlimit(5000)
