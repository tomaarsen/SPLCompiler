from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

from compiler.token import Token


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
