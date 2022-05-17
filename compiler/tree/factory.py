from dataclasses import dataclass, field
from typing import List

from compiler.token import Token
from compiler.type import Type
from compiler.util import Span

from compiler.tree.tree import (  # isort:skip
    BoolTypeNode,
    CharTypeNode,
    CommaListNode,
    FieldNode,
    FunCallNode,
    FunDeclNode,
    FunTypeNode,
    IfElseNode,
    IntTypeNode,
    ListAbbrNode,
    ListNode,
    Node,
    Op1Node,
    Op2Node,
    PolymorphicTypeNode,
    ReturnNode,
    SPLNode,
    StmtAssNode,
    StmtNode,
    TupleNode,
    VarDeclNode,
    VariableNode,
    VoidTypeNode,
    WhileNode,
)


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

    @property
    def span(self):
        if len(self.c) == 0:
            return Span(0, (0, 0))
        if len(self.c) == 1:
            return self.c[0].span
        return self.c[0].span & self.c[-1].span

    def build(self):
        raise NotImplementedError()


class VarDeclFactory(NodeFactory):
    def build(self):
        assert len(self.c) == 5  # nosec

        return VarDeclNode(self.c[0], self.c[1], self.c[3], span=self.span)


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

        # Reset the cache of polymorphic variables that should be shared within this function
        TypeFactory.reset_poly_cache()
        return FunDeclNode(func, args, fun_type, var_decl, stmt, span=self.span)


class FieldFactory(NodeFactory):
    def build(self):
        return FieldNode(self.c, span=self.span)


class CommaFactory(NodeFactory):
    def build(self):
        items = [self.c[0]] + [_id for comma, _id in self.c[1:]]
        span = items[0].span & items[-1].span
        return CommaListNode(items, span=span)


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
            return Op2Node(
                left=None, operator=self.c[0], right=self.c[1], span=self.span
            )
        if len(self.c) == 3:
            op2 = self.c[2]
            inner = Op2Node(
                left=None, operator=self.c[0], right=self.c[1], span=self.span
            )
            op2.assign_left(inner)
            return op2
        raise Exception()


class ColonFactory(NodeFactory):
    def build(self):
        match self.c:
            case [_ as basic]:
                return basic
            case [_ as left, Token(type=Type.COLON) as operator, _ as right]:
                return Op2Node(left, operator, right, span=self.span)
        raise Exception()


class UnaryFactory(NodeFactory):
    def build(self):
        match self.c:
            # ( ( '!' | '-' ) Unary )
            case [_ as operator, _ as operand]:
                return Op1Node(operator, operand, span=self.span)
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
                _id = VariableNode(_id, field, span=_id.span & field.span)
                return StmtAssNode(_id, exp, span=self.span)
            case [
                Token(type=Type.ID) as _id,
                Token(type=Type.EQ),
                _ as exp,
                Token(type=Type.SEMICOLON),
            ]:
                _id = VariableNode(_id, span=_id.span)
                return StmtAssNode(_id, exp, span=self.span)
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
                return TupleNode(self.c[1], self.c[3], span=self.span)
            # Bracket ( exp )
            case [Token(type=Type.LRB), _, Token(type=Type.RRB)]:
                return self.c[1]
            # Empty list [ ]
            case [Token(type=Type.LSB), Token(type=Type.RSB)]:
                return ListNode(None, span=self.span)
            case [Token(type=Type.ID) as _id, FieldNode() as field]:
                return VariableNode(_id, field, span=self.span)
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
                return FunCallNode(func, args, span=self.span)
            case [
                Token(type=Type.ID) as func,
                Token(type=Type.LRB),
                Token(type=Type.RRB),
            ]:
                return FunCallNode(func, None, span=self.span)
        raise Exception()


class IfElseFactory(NodeFactory):
    def build(self):
        # 'if' '(' Exp ')' '{' Stmt* '}' [ 'else' '{' Stmt* '}' ]
        cond = self.c[2]
        body = []
        for i in range(5, len(self.c)):
            node = self.c[i]
            if isinstance(node, StmtNode):
                body.append(node)
            else:
                break
        else_body = []
        match self.c[i + 1 :]:
            case [
                Token(type=Type.ELSE),
                Token(type=Type.LCB),
                *else_body,
                Token(type=Type.RCB),
            ]:
                pass

        return IfElseNode(cond, body, else_body, span=self.span)


class WhileFactory(NodeFactory):
    def build(self):
        cond = self.c[2]
        body = []
        for node in self.c[5:]:
            if isinstance(node, StmtNode):
                body.append(node)
            else:
                break
        return WhileNode(cond, body, span=self.span)


class TypeFactory(NodeFactory):

    POLY_CACHE = {}

    def build(self):
        match self.c:
            case [Token()]:
                # Fill the POLY_CACHE with a mapping to poly types,
                # make a new Polymorphic type node if no cached poly node exists for this token
                return TypeFactory.POLY_CACHE.setdefault(
                    self.c[0].text, PolymorphicTypeNode(self.c[0], span=self.span)
                )
            case [IntTypeNode() | BoolTypeNode() | CharTypeNode()]:
                return self.c[0]
            case [Token(type=Type.LSB), _ as _type, Token(type=Type.RSB)]:
                return ListNode(_type, span=self.span)
            case [
                Token(type=Type.LRB),
                _ as left,
                Token(type=Type.COMMA),
                _ as right,
                Token(type=Type.RRB),
            ]:
                return TupleNode(left, right, span=self.span)
        raise Exception()

    @classmethod
    def reset_poly_cache(cls):
        cls.POLY_CACHE = {}


class BasicTypeFactory(NodeFactory):
    def build(self):
        assert len(self.c) == 1  # nosec
        match self.c[0]:
            case Token(type=Type.INT):
                return IntTypeNode(span=self.span)
            case Token(type=Type.BOOL):
                return BoolTypeNode(span=self.span)
            case Token(type=Type.CHAR):
                return CharTypeNode(span=self.span)
        raise Exception()


class SPLFactory(NodeFactory):
    def build(self):
        if len(self.c) == 1 and isinstance(self.c[0], SPLNode):
            return self.c[0]
        return SPLNode(self.c, span=self.span)


class FunTypeFactory(NodeFactory):
    def build(self):
        match self.c:
            case [*types, Token(type=Type.ARROW), _ as ret_type]:
                return FunTypeNode(types, ret_type, span=self.span)
        raise Exception()


class RetTypeFactory(NodeFactory):
    def build(self):
        match self.c:
            case [Token(type=Type.VOID)]:
                return VoidTypeNode(span=self.span)
            case [_]:
                return self.c[0]
        raise Exception()


class StmtFactory(NodeFactory):
    def build(self):
        return StmtNode(self.c[0], span=self.span)


class SingleFactory(NodeFactory):
    def build(self):
        assert len(self.c) == 1  # nosec
        return self.c[0]


class ReturnFactory(NodeFactory):
    def build(self):
        match self.c:
            case [Token(type=Type.RETURN), _ as body, Token(type=Type.SEMICOLON)]:
                return ReturnNode(body, span=self.span)
            case [Token(type=Type.RETURN), Token(type=Type.SEMICOLON)]:
                return ReturnNode(None, span=self.span)
        raise Exception()


class ListAbbrFactory(NodeFactory):
    def build(self):
        match self.c:
            case [
                Token(type=Type.LSB),
                _ as lower,
                Token(type=Type.DDOT),
                _ as upper,
                Token(type=Type.RSB),
            ]:
                return ListAbbrNode(lower, upper, span=self.span)
        raise Exception()


class DefaultFactory(NodeFactory):
    def build(self):
        if len(self.c) == 1:
            return self.c[0]
        return self.c
