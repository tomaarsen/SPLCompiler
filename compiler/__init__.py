import sys

from compiler.parser import Parser
from compiler.scanner import Scanner
from compiler.token import Token
from compiler.type import Type

# Default is 1000
sys.setrecursionlimit(5000)
