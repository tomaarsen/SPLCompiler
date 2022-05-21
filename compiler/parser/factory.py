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
    ForNode,
    FunCallNode,
    FunDeclNode,
    FunTypeNode,
    IfElseNode,
    IndexNode,
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
    children: List[Node | Token] = field(kw_only=True, default_factory=list)

    def __len__(self):
        return len(self.children)

    def __bool__(self) -> bool:
        return True

    @property
    def span(self):
        if len(self.children) == 0:
            return Span(0, (0, 0))
        if len(self.children) == 1:
            return self.children[0].span
        return self.children[0].span & self.children[-1].span

    def build(self, children):
        self.children = children


class VarDeclFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        assert len(children) == 5  # nosec

        return VarDeclNode(children[0], children[1], children[3], span=self.span)


class FunDeclFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        func = children[0]
        args = None
        fun_type = None
        var_decl = []
        stmt = []
        for child in children:
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
    def build(self, children):
        super().build(children)
        return FieldNode(children, span=self.span)


class IndexFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
            case [
                Token(type=Type.LSB),
                _ as exp,
                Token(type=Type.RSB),
            ]:
                return IndexNode(exp, span=self.span)
        raise Exception()


class CommaFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        items = [children[0]] + [_id for comma, _id in children[1:]]
        span = items[0].span & items[-1].span
        return CommaListNode(items, span=span)


class ExpFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        if len(children) == 2:
            node = children[1]
            node.assign_left(children[0])
            return node
        elif len(children) == 1:
            return children[0]
        raise Exception()


class ExpPrimeFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        if len(children) == 2:
            return Op2Node(
                left=None, operator=children[0], right=children[1], span=self.span
            )
        if len(children) == 3:
            op2 = children[2]
            inner = Op2Node(
                left=None, operator=children[0], right=children[1], span=self.span
            )
            op2.assign_left(inner)
            return op2
        raise Exception()


class ColonFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
            case [_ as basic]:
                return basic
            case [_ as left, Token(type=Type.COLON) as operator, _ as right]:
                return Op2Node(left, operator, right, span=self.span)
        raise Exception()


class UnaryFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
            # ( ( '!' | '-' ) Unary )
            case [_ as operator, _ as operand]:
                return Op1Node(operator, operand, span=self.span)
            # Basic
            case [_ as basic]:
                return basic
        raise Exception()


class StmtAssFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
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
    def build(self, children):
        super().build(children)
        match children:
            # Tuple ( left , right )
            case [
                Token(type=Type.LRB),
                _,
                Token(type=Type.COMMA),
                _,
                Token(type=Type.RRB),
            ]:
                return TupleNode(children[1], children[3], span=self.span)
            # Bracket ( exp )
            case [Token(type=Type.LRB), _, Token(type=Type.RRB)]:
                return children[1]
            # Empty list [ ]
            case [Token(type=Type.LSB), Token(type=Type.RSB)]:
                return ListNode(None, span=self.span)
            case [Token(type=Type.ID) as _id, FieldNode() as field]:
                return VariableNode(_id, field, span=self.span)
            case [_]:
                return children[0]
        raise Exception()


class FunCallFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
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
    def build(self, children):
        super().build(children)
        # 'if' '(' Exp ')' '{' Stmt* '}' [ 'else' '{' Stmt* '}' ]
        cond = children[2]
        body = []
        for i in range(5, len(children)):
            node = children[i]
            if isinstance(node, StmtNode):
                body.append(node)
            else:
                break
        else_body = []
        match children[i + 1 :]:
            case [
                Token(type=Type.ELSE),
                Token(type=Type.LCB),
                *else_body,
                Token(type=Type.RCB),
            ]:
                pass

        return IfElseNode(cond, body, else_body, span=self.span)


class WhileFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        cond = children[2]
        body = []
        for node in children[5:]:
            if isinstance(node, StmtNode):
                body.append(node)
            else:
                break
        return WhileNode(cond, body, span=self.span)


class ForFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
            case [
                Token(type=Type.FOR),
                Token(type=Type.ID) as _id,
                Token(type=Type.IN),
                _ as loop,
                Token(type=Type.LCB),
                *stmt,
                Token(type=Type.RCB),
            ]:
                return ForNode(_id, loop, stmt, span=self.span)
        raise Exception()


class TypeFactory(NodeFactory):

    POLY_CACHE = {}

    def build(self, children):
        super().build(children)
        match children:
            case [Token()]:
                # Fill the POLY_CACHE with a mapping to poly types,
                # make a new Polymorphic type node if no cached poly node exists for this token
                return TypeFactory.POLY_CACHE.setdefault(
                    children[0].text, PolymorphicTypeNode(children[0], span=self.span)
                )
            case [IntTypeNode() | BoolTypeNode() | CharTypeNode()]:
                return children[0]
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
    def build(self, children):
        super().build(children)
        assert len(children) == 1  # nosec
        match children[0]:
            case Token(type=Type.INT):
                return IntTypeNode(span=self.span)
            case Token(type=Type.BOOL):
                return BoolTypeNode(span=self.span)
            case Token(type=Type.CHAR):
                return CharTypeNode(span=self.span)
        raise Exception()


class SPLFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        return SPLNode(children, span=self.span)


class FunTypeFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
            case [*types, Token(type=Type.ARROW), _ as ret_type]:
                return FunTypeNode(types, ret_type, span=self.span)
        raise Exception()


class RetTypeFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
            case [Token(type=Type.VOID)]:
                return VoidTypeNode(span=self.span)
            case [_]:
                return children[0]
        raise Exception()


class StmtFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        return StmtNode(children[0], span=self.span)


class SingleFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        assert len(children) == 1  # nosec
        return children[0]


class ReturnFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
            case [Token(type=Type.RETURN), _ as body, Token(type=Type.SEMICOLON)]:
                return ReturnNode(body, span=self.span)
            case [Token(type=Type.RETURN), Token(type=Type.SEMICOLON)]:
                return ReturnNode(None, span=self.span)
        raise Exception()


class ListAbbrFactory(NodeFactory):
    def build(self, children):
        super().build(children)
        match children:
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
    def build(self, children):
        super().build(children)
        if len(children) == 1:
            return children[0]
        return children
