from __future__ import annotations

from dataclasses import dataclass, field
from platform import node
from pprint import pprint
from typing import List, Optional

from compiler.grammar_parser import NT
from compiler.token import Token
from compiler.type import Type

# Optional TODO: Type.MINUS *sometimes* left attaches (e.g. -12)
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


"""
@dataclass
class Tree:
    nt: NT
    c: List[Tree | Token] = field(kw_only=True, default_factory=list)

    def add_child(self, child: Tree) -> None:
        # print(f"Placing {child} in tree of type {self.nt}")
        # breakpoint()
        self.c.append(child)

    def add_children(self, children: List[Tree]) -> None:
        # print(f"Placing {children} in tree of type {self.nt}")
        # breakpoint()
        self.c.extend(children)

    def __iter__(self):
        return self.c

    def __len__(self):
        return len(self.c)

    def __getitem__(self, index: int) -> Tree | Token:
        return self.c[index]

    def __bool__(self) -> bool:
        return True

    def __str__(self) -> str:
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
"""


@dataclass
class NodeFactory:
    c: List[Node | Token] = field(kw_only=True, default_factory=list)

    def __len__(self):
        return len(self.c)

    def __bool__(self) -> bool:
        return True

    def add_children(self, children: List[Node] | Node) -> None:
        try:
            self.c.extend(children)
        except TypeError:
            self.c.append(children)

    def build(self):
        raise NotImplementedError()


class VarDeclFactory(NodeFactory):
    def build(self):
        assert len(self.c) == 5  # nosec

        return VarDeclNode(self.c[0], self.c[1], self.c[3])


class FunDeclFactory(NodeFactory):
    def build(self):
        func = self.c[0]
        args = None
        fun_type = None
        var_decl = []
        stmt = []
        for child in self.c:
            match child:
                case CommaListNode():
                    args = child

                case FunTypeNode():
                    fun_type = child

                case VarDeclNode():
                    var_decl.append(child)

                case StmtNode():
                    stmt.append(child)

        return FunDeclNode(func, args, fun_type, var_decl, stmt)


class FieldFactory(NodeFactory):
    def build(self):
        return FieldNode(self.c)


class CommaFactory(NodeFactory):
    def build(self):
        return CommaListNode([self.c[0]] + [_id for comma, _id in self.c[1:]])


class ExpFactory(NodeFactory):
    def build(self):
        if len(self.c) == 2:
            node = self.c[1]
            node.assign_left(self.c[0])
            return node
        elif len(self.c) == 1:
            return self.c[0]
        raise Exception()


class ExpPrimeFactory(NodeFactory):
    def build(self):
        if len(self.c) == 2:
            return Op2Node(left=None, operator=self.c[0], right=self.c[1])
        if len(self.c) == 3:
            op2 = self.c[2]
            inner = Op2Node(left=None, operator=self.c[0], right=self.c[1])
            op2.assign_left(inner)
            return op2
        raise Exception()


class ColonFactory(NodeFactory):
    def build(self):
        match self.c:
            case [_ as basic]:
                return basic
            case [_ as left, Token(type=Type.COLON) as operator, _ as right]:
                return Op2Node(left, operator, right)
        raise Exception()


class UnaryFactory(NodeFactory):
    def build(self):
        match self.c:
            # ( ( '!' | '-' ) Unary )
            case [_ as operator, _ as operand]:
                return Op1Node(operator, operand)
            # Basic
            case [_ as basic]:
                return basic
        raise Exception()


class StmtAssFactory(NodeFactory):
    def build(self):
        match self.c:
            case [
                Token(type=Type.ID) as _id,
                _ as field,
                Token(type=Type.EQ),
                _ as exp,
                Token(type=Type.SEMICOLON),
            ]:
                _id = VariableNode(_id, field)
                return StmtAssNode(_id, exp)
            case [
                Token(type=Type.ID) as _id,
                Token(type=Type.EQ),
                _ as exp,
                Token(type=Type.SEMICOLON),
            ]:
                _id = VariableNode(_id)
                return StmtAssNode(_id, exp)
        raise Exception()


class BasicFactory(NodeFactory):
    def build(self):
        match self.c:
            # Tuple ( left , right )
            case [
                Token(type=Type.LRB),
                _,
                Token(type=Type.COMMA),
                _,
                Token(type=Type.RRB),
            ]:
                return TupleNode(self.c[1], self.c[3])
            # Bracket ( exp )
            case [Token(type=Type.LRB), _, Token(type=Type.RRB)]:
                return self.c[1]
            # Empty list [ ]
            case [Token(type=Type.LSB), Token(type=Type.RSB)]:
                return ListNode(None)
            case [Token(type=Type.ID) as _id, FieldNode() as field]:
                return VariableNode(_id, field)
            case [_]:
                return self.c[0]
        raise Exception()


class FunCallFactory(NodeFactory):
    def build(self):
        match self.c:
            case [
                Token(type=Type.ID) as func,
                Token(type=Type.LRB),
                _ as args,
                Token(type=Type.RRB),
            ]:
                return FunCallNode(func, args)
            case [
                Token(type=Type.ID) as func,
                Token(type=Type.LRB),
                Token(type=Type.RRB),
            ]:
                return FunCallNode(func, None)
        raise Exception()


class IfElseFactory(NodeFactory):
    def build(self):
        # 'if' '(' Exp ')' '{' Stmt* '}' [ 'else' '{' Stmt* '}' ]
        cond = self.c[2]
        # Only if index 5 is indeed a Stmt, and not '}'
        body = self.c[5] if isinstance(self.c[5], Node) else None
        # Only if 4 from the last is "else", then there must be an else statmenet
        else_body = (
            self.c[-2]
            if isinstance(self.c[-4], Token) and self.c[-4].type == Type.ELSE
            else None
        )
        return IfElseNode(cond, body, else_body)


class WhileFactory(NodeFactory):
    def build(self):
        cond = self.c[2]
        # Only if index 5 is indeed a Stmt, and not '}'
        body = self.c[5] if isinstance(self.c[5], Node) else None
        return WhileNode(cond, body)


class TypeFactory(NodeFactory):
    def build(self):
        match self.c:
            case [_ as _type]:
                return _type
            case [Token(type=Type.LSB), _ as _type, Token(type=Type.RSB)]:
                return ListNode(_type)
            case [
                Token(type=Type.LRB),
                _ as left,
                Token(type=Type.COMMA),
                _ as right,
                Token(type=Type.RRB),
            ]:
                return TupleNode(left, right)
        raise Exception()


class SPLFactory(NodeFactory):
    def build(self):
        # breakpoint()
        # print("SPLFactory", self.c)
        if len(self.c) == 1 and isinstance(self.c[0], SPLNode):
            return self.c[0]
        return SPLNode(self.c)


class FunTypeFactory(NodeFactory):
    def build(self):
        match self.c:
            case [*obj, Token(type=Type.ARROW), _ as ret_type]:
                return FunTypeNode(self.c[:-2], ret_type)
        raise Exception()


class StmtFactory(NodeFactory):
    def build(self):
        return StmtNode(self.c[0])


class SingleFactory(NodeFactory):
    def build(self):
        assert len(self.c) == 1  # nosec
        return self.c[0]


class ReturnFactory(NodeFactory):
    def build(self):
        match self.c:
            case [Token(type=Type.RETURN), _ as body, Token(type=Type.SEMICOLON)]:
                return ReturnNode(body)
            case [Token(type=Type.RETURN), Token(type=Type.SEMICOLON)]:
                return ReturnNode(None)
        raise Exception()


class DefaultFactory(NodeFactory):
    def build(self):
        # print(self.c)
        # breakpoint()
        if len(self.c) == 1:
            return self.c[0]
        return self.c


# class ExpHandler:
#     def add_children(*args, **kwargs):

#         return Op2Node(left, op, right)


class Node:
    # def add_children(*args, **kwargs):
    #     raise NotImplementedError()
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
    body: Optional[StmtNode]
    else_body: Optional[StmtNode]


@dataclass
class WhileNode(Node):
    cond: Node
    body: Optional[StmtNode]


@dataclass
class StmtAssNode(Node):
    id: Token
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
    exp: Node


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
