from typing import List

from compiler.token import Token
from compiler.tree import Tree
from compiler.type import Type


class Parser:
    def __init__(self) -> None:
        pass

    def parse(self, tokens: List[Token]) -> Tree:
        pass

        for token in tokens:
            match token:
                case Type.LRB:
                    ...
