import string
from enum import Enum, auto
from pprint import pprint
from typing import Any, Dict, List, Tuple

from compiler.token import Token
from compiler.type import Type

from compiler.tree import (  # isort:skip
    BoolTypeNode,
    CharTypeNode,
    FunDeclNode,
    FunTypeNode,
    IntTypeNode,
    ListNode,
    Node,
    Op2Node,
    PolymorphicTypeNode,
    ReturnNode,
    SPLNode,
    StmtNode,
    TupleNode,
    TypeNode,
    VarDeclNode,
)


def get_fresh_type() -> TypeNode:
    return PolymorphicTypeNode.fresh()


class Typer:
    def __init__(self) -> None:
        pass

    def type(self, tree: Node):
        ft = get_fresh_type()
        return self.type_node(tree, {}, ft)

    def type_node(
        self, tree: Node, context: Dict[str, TypeNode], exp_type: TypeNode
    ) -> Node:
        match tree:

            case Token(type=Type.DIGIT):
                # If tree is e.g. `12`:
                return self.unify(exp_type, IntTypeNode(None))

            case Token(type=Type.ID):
                # If tree is e.g. `a`:
                # 1: Look up the environment type for that variable, which is a type scheme (e.g. (Int, b) or something)
                # 2: Introduce new fresh variables
                # 3: Substitute alpha with the fresh variables in tau. New version of tau where all variables that
                #    were universally qualified by our `tree` variable are replaced by a fresh variable.

                # Maybe this is done to remove recursion?
                # context(x) = forall alpha-> . tau
                # tau[alpha-> |-> beta->]

                # Note: This is a simplified version, no replacement with fresh variables
                context_type = context[tree.text]
                return self.unify(context_type, exp_type)

            case SPLNode():
                transformations = []
                for expression in tree.body:
                    trans = self.type_node(expression, {**context}, get_fresh_type())
                    context = self.apply_trans_context(trans, context)
                    transformations += trans
                return transformations

            case FunDeclNode():
                # fresh_types = [get_fresh_type() for _ in tree.args.items]
                # context.extend(list(zip(tree.args.items, fresh_types)))
                if tree.type:
                    if len(tree.args.items) != len(tree.type.types):
                        raise Exception("Wrong number of arguments")

                    for token, _type in zip(tree.args.items, tree.type.types):
                        context[token.text] = _type

                    ret_type = tree.type.ret_type
                    context[tree.id.text] = tree.type

                else:
                    fresh_types = []
                    for token in tree.args.items:
                        if token.text in context:
                            raise Exception("Redefined variable")
                        ft = get_fresh_type()
                        context[token.text] = ft
                        fresh_types.append(ft)

                    ret_type = get_fresh_type()
                    context[tree.id.text] = FunTypeNode(fresh_types, ret_type)

                # TODO: Fill return type
                transformations = []
                for stmt in tree.stmt:
                    trans = self.type_node(stmt, {**context}, ret_type)
                    context = self.apply_trans_context(trans, context)
                    transformations += trans

                tree.type = context[tree.id.text]

                transformations += self.unify(
                    self.apply_trans(exp_type, transformations), tree.type
                )

                return transformations

            case StmtNode():
                return self.type_node(tree.stmt, {**context}, exp_type)

            case ReturnNode():
                trans = self.type_node(tree.exp, {**context}, exp_type)
                # breakpoint()
                return trans

            case Op2Node():
                if tree.operator.type == Type.COLON:
                    left_exp_type = PolymorphicTypeNode.fresh()
                    right_exp_type = ListNode(left_exp_type)
                    output_exp_type = right_exp_type

                elif tree.operator.type in (
                    Type.PLUS,
                    Type.MINUS,
                    Type.STAR,
                    Type.SLASH,
                    Type.PERCENT,
                ):
                    left_exp_type = IntTypeNode(None)
                    right_exp_type = left_exp_type
                    output_exp_type = left_exp_type

                elif tree.operator.type in (
                    Type.LEQ,
                    Type.GEQ,
                    Type.LT,
                    Type.GT,
                ):
                    left_exp_type = IntTypeNode(None)
                    right_exp_type = left_exp_type
                    output_exp_type = BoolTypeNode(None)

                elif tree.operator.type in (Type.OR, Type.AND):
                    left_exp_type = BoolTypeNode(None)
                    right_exp_type = left_exp_type
                    output_exp_type = left_exp_type

                elif tree.operator.type in (Type.DEQUALS, Type.NEQ):
                    left_exp_type = PolymorphicTypeNode.fresh()
                    right_exp_type = left_exp_type
                    output_exp_type = BoolTypeNode(None)

                else:
                    raise Exception("Incorrect Op2Node")

                trans_left = self.type_node(tree.left, context, left_exp_type)
                context = self.apply_trans_context(trans_left, context)
                trans_right = self.type_node(tree.right, context, right_exp_type)
                trans_op = self.unify(
                    self.apply_trans(exp_type, trans_right), output_exp_type
                )
                return trans_left + trans_right + trans_op

        raise Exception("Node had no handler")
        # breakpoint()

    def apply_trans(
        self, node: TypeNode, trans: List[Tuple[PolymorphicTypeNode, TypeNode]]
    ) -> TypeNode:
        for left_sub, right_sub in trans:
            match node:
                case FunTypeNode():
                    node.types = [self.apply_trans(node, trans) for node in node.types]
                    node.ret_type = self.apply_trans(node.ret_type, trans)
                case ListNode():
                    node.body = self.apply_trans(node.body, trans)
                case TupleNode():
                    node.left = self.apply_trans(node.left, trans)
                    node.right = self.apply_trans(node.right, trans)
                case IntTypeNode():
                    if isinstance(left_sub, IntTypeNode):
                        return right_sub
                case CharTypeNode():
                    if isinstance(left_sub, CharTypeNode):
                        return right_sub
                case BoolTypeNode():
                    if isinstance(left_sub, BoolTypeNode):
                        return right_sub
                case PolymorphicTypeNode():
                    if left_sub == node:
                        return right_sub
        return node

    def apply_trans_context(
        self,
        trans: List[Tuple[PolymorphicTypeNode, TypeNode]],
        context: Dict[str, TypeNode],
    ) -> Dict[str, TypeNode]:
        # print(trans, context)

        if trans:
            for var_name, var_type in context.items():
                context[var_name] = self.apply_trans(var_type, trans)

        # print(context)
        return context

    def unify(
        self, type_one: TypeNode, type_two: TypeNode
    ) -> List[Tuple[str, TypeNode]]:
        # Goal: Return a list of tuples, each tuple is a substitution from left to right
        if isinstance(type_one, IntTypeNode) and isinstance(type_two, IntTypeNode):
            return []

        if isinstance(type_one, BoolTypeNode) and isinstance(type_two, BoolTypeNode):
            return []

        if isinstance(type_one, CharTypeNode) and isinstance(type_two, CharTypeNode):
            return []

        if type_one == type_two:
            return []

        # If left is very general, e.g. "a", and right is specific, e.g. "Int", then map "a" to "Int"
        # TODO: Fail case
        if isinstance(type_one, PolymorphicTypeNode):
            return [(type_one, type_two)]

        if isinstance(type_two, PolymorphicTypeNode):
            return [(type_two, type_one)]

        if isinstance(type_one, ListNode) and isinstance(type_two, ListNode):
            return self.unify(type_one.body, type_two.body)

        if isinstance(type_one, TupleNode) and isinstance(type_two, TupleNode):
            before = self.unify(type_one.left, type_two.left)
            after = self.unify(type_one.right, type_two.right)
            return before + after

        if isinstance(type_one, FunTypeNode) and isinstance(type_two, FunTypeNode):
            if len(type_one.types) != len(type_two.types):
                raise Exception("Different number of arguments")

            transformations = []
            for _type_one, _type_two in zip(type_one.types, type_two.types):
                transformations.append(self.unify(_type_one, _type_two))
            transformations.append(self.unify(type_one.ret_type, type_two.ret_type))
            return [t for t in transformations if t]

        raise Exception("Failed to unify", type_one, "and", type_two)
