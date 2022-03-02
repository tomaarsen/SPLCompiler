from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from compiler.token import Token
from compiler.type import Type

# TODO: Type.MINUS *sometimes* left attaches (e.g. -12)
LEFT_ATTACHED_TOKENS = {
    Type.LRB,  # (
    Type.LSB,  # [
    Type.NOT,  # !
}

RIGHT_ATTACHED_TOKENS = {
    Type.RRB,  # )
    Type.RSB,  # ]
    Type.COMMA,
    Type.SEMICOLON,
    Type.HD,
    Type.TL,
    Type.FST,
    Type.SND,
}

SPACES_PER_INDENT = 4


@dataclass
class Tree:
    c: List[Tree | Token] = field(kw_only=True, default_factory=list)

    def add_child(self, child: Tree) -> None:
        self.c.append(child)

    def add_children(self, children: List[Tree]) -> None:
        self.c.extend(children)

    def __len__(self):
        return len(self.c)

    def __getitem__(self, index: int) -> Tree | Token:
        return self.c[index]

    def __bool__(self) -> bool:
        return True

    def __str__(self):
        depth = 0
        program = ""
        last_token = None

        for token in self.yield_tokens():
            # Modify depth before this token
            if token.type == Type.RCB:  # }
                depth -= 1

            # Ensure indentation is correct
            if program and program[-1] == "\n":
                program += " " * (SPACES_PER_INDENT * depth)

            # Modify depth after this token
            if token.type == Type.LCB:  # {
                depth += 1

            # Remove the last space if this is a tightly bound character, e.g. ';'
            # OR if `token` is the `(` after an `id` (i.e. a function call)
            if (
                program
                and program[-1] == " "
                and (
                    token.type in RIGHT_ATTACHED_TOKENS
                    or (
                        last_token
                        and last_token.type == Type.ID
                        and token.type == Type.LRB
                    )
                )
            ):
                program = program[:-1]

            # Print this token
            program += token.text

            # Print space that follows this token if applicable
            if token.type not in LEFT_ATTACHED_TOKENS:
                program += " "

            # Print a newline if applicable
            if token.type in {Type.RCB, Type.LCB, Type.SEMICOLON}:
                program += "\n"

            last_token = token

        return program.strip()

    def yield_tokens(self) -> str:
        for child in self.c:
            match child:
                case Token():
                    yield child

                case Tree():
                    yield from child.yield_tokens()
