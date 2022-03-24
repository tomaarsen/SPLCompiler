from __future__ import annotations

from dataclasses import dataclass, field, fields
from pprint import pprint
from string import ascii_lowercase
from typing import Iterator, List, Optional

from compiler.token import Token
from compiler.type import Type


class Node:
    def __str__(self) -> str:
        from compiler.tree.printer import Printer

        printer = Printer()
        return printer.print(self)

    def iter_fields(self, **kwargs) -> Iterator[Token]:
        # Yield the dataclass field.
        # Throws a TypeError if self is not a dataclass, just ignore if so
        try:
            for _field in fields(self):
                yield _field.name, getattr(self, _field.name)
        except TypeError:
            pass


@dataclass
class CommaListNode(Node):
    items: List[Node]


@dataclass
class FunCallNode(Node):
    func: Token
    args: Optional[CommaListNode]


@dataclass
class IfElseNode(Node):
    cond: Node
    body: List[StmtNode]
    else_body: List[StmtNode]


@dataclass
class WhileNode(Node):
    cond: Node
    body: List[StmtNode]


@dataclass
class StmtAssNode(Node):
    id: VariableNode
    exp: Node


@dataclass
class FieldNode(Node):
    fields: List[Token]


@dataclass
class FunTypeNode(Node):
    types: List[Node]
    ret_type: Node


@dataclass
class StmtNode(Node):
    stmt: Node


@dataclass
class ReturnNode(Node):
    exp: Optional[Node | Token]


@dataclass
class TupleNode(Node):
    left: Node
    right: Node


@dataclass
class SPLNode(Node):
    body: List[Node]


@dataclass
class FunDeclNode(Node):
    id: Token
    args: Optional[CommaListNode]
    type: Optional[FunTypeNode]
    var_decl: List[VarDeclNode]
    stmt: List[StmtNode]


@dataclass
class VarDeclNode(Node):
    type: Token | Node
    id: Token
    exp: Node


@dataclass
class BasicTypeNode(Node):
    token: Token


class IntTypeNode(BasicTypeNode):
    pass


class CharTypeNode(BasicTypeNode):
    pass


class BoolTypeNode(BasicTypeNode):
    pass


@dataclass
class VoidTypeNode(Node):
    token: Token


class PolymorphicTypeNode(Node):
    id = 0
    print_id = 0

    def __init__(self, name=None) -> None:
        self._token = None
        self.id = PolymorphicTypeNode.id
        PolymorphicTypeNode.id += 1

    @property
    def token(self):
        if self._token is None:
            text = ""
            i = self.print_id // 26
            if i:
                text += ascii_lowercase[i]
            text += ascii_lowercase[self.print_id % 26]
            self._token = Token(text, Type.ID)
            PolymorphicTypeNode.print_id += 1

        return self._token

    @classmethod
    def reset(cls):
        cls.id = 0
        cls.print_id = 0

    def __eq__(self, __o: object) -> bool:
        if not isinstance(__o, PolymorphicTypeNode):
            return False

        return self.id == __o.id

    def __repr__(self):
        return f"PolymorphicTypeNode(name={self.token}, id={self.id})"

    @classmethod
    def fresh(cls):
        return cls(None)


@dataclass
class VariableNode(Node):
    id: Token
    field: Optional[FieldNode] = None


@dataclass
class ListNode(Node):
    body: Optional[Node]


@dataclass
class Op2Node(Node):
    left: Node
    operator: Token
    right: Node

    def assign_left(self, value: Token | Node):
        if self.left is None:
            self.left = value
        elif isinstance(self.left, Op2Node):
            self.left.assign_left(value)
        else:
            raise Exception()


@dataclass
class Op1Node(Node):
    operator: Token
    operand: Node


TypeNode = (
    FunTypeNode
    | ListNode
    | TupleNode
    | BasicTypeNode
    | PolymorphicTypeNode
    | VoidTypeNode
)
