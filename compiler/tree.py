from __future__ import annotations

from dataclasses import dataclass, field
from compiler.token import Token
from typing import List, Optional


@dataclass
class Tree:
    children: List[Tree] = field(kw_only=True, default_factory=list)

    def add_child(self, child: Tree):
        self.children.append(child)


@dataclass()
class TokenTree(Tree):
    token: Token


@dataclass
class BracketTree(Tree):
    open: Token
    close: Token


@dataclass
class FuncDeclTree(Tree):
    # FunDecl   = id '(' [ FArgs ] ')' [ '::' FunType ] '{' VarDecl* Stmt+ '}'
    _id: List[Tree]
    args: List[BracketTree]
    arg_types: List[Tree]
    body: List[BracketTree]

    double_colon: Optional[Token]
    arrow: Optional[Token]
