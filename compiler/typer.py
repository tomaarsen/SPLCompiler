import string
from enum import Enum, auto
from pprint import pprint
from typing import Any, List, Tuple, Type

from compiler.tree import FunDeclNode, Node, SPLNode, VarDeclNode

VAR_TYPES = {
    "int",
    "bool",
    "char",
}
VARS_ADDED = 0

VarType = str


def get_fresh_type() -> VarType:
    global VARS_ADDED
    type_name = ""
    vars_added = VARS_ADDED
    while vars_added >= 0:
        type_name += string.ascii_lowercase[VARS_ADDED]
        vars_added -= 26
    VARS_ADDED += 1
    VAR_TYPES.add(type_name)
    return type_name


class Typer:
    def __init__(self) -> None:
        pass

    def type(self, tree: Node) -> Node:
        ft = get_fresh_type()
        return self.M([], tree, ft)

    # def apply_sub_context(self, context: List[Tuple[Any, Any]], substitution: List[Tuple[Any, Any]]) -> List[Tuple[Any, Any]]:
    #     for left_sub, right_sub in substitution:
    #         for i, left_context, right_context in enumerate(context):
    #             if left_context == left_sub:
    #                 context[i] = (right_sub, right_context)
    #             if right_context == left_sub:
    #                 context[i] = (right_sub, right_context)

    def M(self, context: List[Tuple[Any, Any]], expression, _type):
        match expression:
            case SPLNode():
                # TODO: Prevent IndexError
                expr1 = expression.body[0]
                expr2 = expression.body[1:]
                fresh_type = get_fresh_type()
                mapping = (fresh_type, _type)
                sub = self.M(context, expr1, mapping)
                return sub + self.M(
                    self.unify(context, sub), expr2, self.unify(fresh_type, sub)
                )

            case FunDeclNode():
                args = [token.text for token in expression.args.items]
                mapping = [(arg, get_fresh_type()) for arg in args]
                fresh_return_type = get_fresh_type()
                sub = self.M(
                    context + mapping,
                    expression.var_decl + expression.stmt,
                    fresh_return_type,
                )
                return sub + self.unify(self.unify(_type, sub), [])

            case VarDeclNode():

                alpha = get_fresh_type()
                sub = self.M(
                    context + (expression.id.text, alpha), expression.exp, alpha
                )

    def unify(self, type_one, type_two) -> List[Tuple[Any, Any]]:
        # Goal: Return a list of tuples, each tuple is a substitution from left to right
        if type_one == type_two:
            return []

        breakpoint()
