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
    IfElseNode,
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
                    trans = self.type_node(expression, context, get_fresh_type())
                    context = self.apply_trans_context(trans, context)
                    transformations += trans
                return transformations

            case FunDeclNode():
                # fresh_types = [get_fresh_type() for _ in tree.args.items]
                # context.extend(list(zip(tree.args.items, fresh_types)))
                context_copy = context.copy()
                if tree.type:
                    if len(tree.args.items) != len(tree.type.types):
                        raise Exception("Wrong number of arguments")

                    for token, _type in zip(tree.args.items, tree.type.types):
                        context_copy[token.text] = _type

                    ret_type = tree.type.ret_type
                    context_copy[tree.id.text] = tree.type

                else:
                    fresh_types = []
                    for token in tree.args.items:
                        if token.text in context_copy:
                            raise Exception("Redefined variable")
                        ft = get_fresh_type()
                        context_copy[token.text] = ft
                        fresh_types.append(ft)

                    ret_type = get_fresh_type()
                    context_copy[tree.id.text] = FunTypeNode(fresh_types, ret_type)

                transformations = []
                for stmt in tree.stmt:
                    trans = self.type_node(stmt, context_copy, ret_type)
                    context_copy = self.apply_trans_context(trans, context_copy)
                    transformations += trans

                # Place in tree
                tree.type = context_copy[tree.id.text]

                transformations += self.unify(
                    self.apply_trans(exp_type, transformations), tree.type
                )

                # Place in global context
                context[tree.id.text] = context_copy[tree.id.text]

                return transformations

            case StmtNode():
                return self.type_node(tree.stmt, context, exp_type)

            case ReturnNode():
                trans = self.type_node(tree.exp, context, exp_type)
                # breakpoint()
                return trans

            case TupleNode():
                left_fresh = PolymorphicTypeNode.fresh()
                right_fresh = PolymorphicTypeNode.fresh()

                # Left side recursion
                trans = self.type_node(tree.left, context, left_fresh)
                context = self.apply_trans_context(trans, context)

                # Right side recursion
                trans += self.type_node(tree.right, context, right_fresh)

                # Unification with expected type
                trans += self.unify(
                    self.apply_trans(exp_type, trans),
                    self.apply_trans(TupleNode(left_fresh, right_fresh), trans),
                )

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

            case VarDeclNode():

                if tree.id.text in context:
                    raise Exception("Redefinition of global variable is not allowed")

                match tree.type:
                    case Token(type=Type.VAR):
                        expr_exp_type = PolymorphicTypeNode.fresh()
                    case Node():
                        expr_exp_type = tree.type
                    case None:
                        expr_exp_type = PolymorphicTypeNode.fresh()
                    case _:
                        raise Exception("Incorrect VarDecl type")

                trans = self.type_node(tree.exp, context, expr_exp_type)

                # Place in global context
                context[tree.id.text] = expr_exp_type
                context = self.apply_trans_context(trans, context)

                # Place in tree
                tree.type = context[tree.id.text]

                return trans

            case IfElseNode():
                condition = tree.cond
                then_branch = tree.body
                else_branch = tree.else_body

                original_sigma = exp_type
                original_context = context.copy()

                transformation_then = []
                for expression in then_branch:
                    trans = self.type_node(expression, context, original_sigma)
                    context = self.apply_trans_context(trans, context)
                    transformation_then += trans

                context_else = context
                sigma_else = self.apply_trans(original_sigma, transformation_then)

                transformation_else = []
                for expression in else_branch:
                    trans = self.type_node(expression, context, sigma_else)
                    context_else = self.apply_trans_context(trans, context_else)
                    transformation_else += trans

                trans_context = self.apply_trans_context(
                    transformation_then + transformation_else, original_context
                )
                trans_condition = self.type_node(
                    condition, trans_context, BoolTypeNode(None)
                )
                return transformation_then + transformation_else + trans_condition

        # breakpoint()
        raise Exception("Node had no handler")

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
