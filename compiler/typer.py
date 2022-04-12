import string
from collections import defaultdict
from enum import Enum, auto
from pprint import pprint
from typing import Any, Dict, List, Tuple

from compiler.error import ErrorRaiser, TypeError, TyperException
from compiler.token import Token
from compiler.tree.visitor import NodeTransformer
from compiler.type import Type
from compiler.util import Span

from compiler.tree.tree import (  # isort:skip
    BoolTypeNode,
    CharTypeNode,
    FieldNode,
    FunCallNode,
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
    StmtAssNode,
    StmtNode,
    TupleNode,
    TypeNode,
    VarDeclNode,
    VariableNode,
    VoidTypeNode,
    WhileNode,
)


def get_fresh_type() -> TypeNode:
    return PolymorphicTypeNode.fresh()


class Typer:
    def __init__(self, program: str) -> None:
        self.i = 0
        self.fun_calls = defaultdict(list)
        self.program = program

    def type(self, tree: Node):
        ft = get_fresh_type()
        context = {
            "print": FunTypeNode(
                [PolymorphicTypeNode.fresh()], VoidTypeNode(None, span=None), span=None
            ),
            "isEmpty": FunTypeNode(
                [ListNode(PolymorphicTypeNode.fresh(), span=None)],
                BoolTypeNode(None, span=None),
                span=None,
            ),
        }
        trans = self.type_node(tree, context, ft)
        self.apply_trans(tree, trans)
        ErrorRaiser.raise_all(TyperException)
        return tree

    def type_node(
        self, tree: Node, context: Dict[str, TypeNode], exp_type: TypeNode
    ) -> Node:
        match tree:

            case Token(type=Type.DIGIT):
                # If tree is e.g. `12`:
                return self.unify(exp_type, IntTypeNode(None, span=tree.span))

            case Token(type=Type.TRUE) | Token(type=Type.FALSE):
                return self.unify(exp_type, BoolTypeNode(None, span=tree.span))

            case Token(type=Type.CHARACTER):
                return self.unify(exp_type, CharTypeNode(None, span=tree.span))

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
                # TODO: Check if tree.text in context
                if tree.text not in context:
                    raise Exception(f"Unknown variable {tree.text}")

                context_type = context[tree.text]
                return self.unify(exp_type, context_type)

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

                original_context = context.copy()

                arg_context = {}
                arg_trans = []

                # # If this function was already called, and thus is context, use those values
                # if tree.id.text in context:
                #     fun_type = context[tree.id.text]

                #     if len(tree.args.items) != len(fun_type.types):
                #         raise Exception("Wrong number of arguments")

                #     for token, var_type in zip(tree.args.items, fun_type.types):
                #         arg_context[token.text] = var_type

                if tree.type:
                    if tree.args:
                        if len(tree.args.items) != len(tree.type.types):
                            raise Exception("Wrong number of arguments")

                        for token, var_type in zip(tree.args.items, tree.type.types):
                            if token.text in arg_context:
                                arg_trans += self.unify(
                                    arg_context[token.text], var_type
                                )
                            arg_context[token.text] = self.apply_trans(
                                var_type, arg_trans
                            )

                    context[tree.id.text] = tree.type

                if not arg_context:
                    fresh_types = []
                    if tree.args:
                        for token in tree.args.items:
                            # if token.text in context:
                            #     raise Exception("Redefined variable")
                            ft = get_fresh_type()
                            arg_context[token.text] = ft
                            fresh_types.append(ft)

                    ret_type = get_fresh_type()
                    context[tree.id.text] = FunTypeNode(
                        fresh_types,
                        ret_type,
                        span=Span(tree.id.span.start_ln, (-1, -1)),
                    )

                for key, value in arg_context.items():
                    context[key] = value

                # transformations = arg_trans
                for var_decl in tree.var_decl:
                    trans = self.type_node(
                        var_decl, context, PolymorphicTypeNode.fresh()
                    )
                    context = self.apply_trans_context(trans, context)
                    # transformations += trans

                for stmt in tree.stmt:
                    # print(context[tree.id.text].ret_type)
                    trans = self.type_node(
                        stmt, context, context[tree.id.text].ret_type
                    )
                    context = self.apply_trans_context(trans, context)
                    # transformations += trans

                # Place in tree
                tree.type = context[tree.id.text]

                # transformations += self.unify(
                #     self.apply_trans(exp_type, transformations), tree.type
                # )
                trans = self.unify(exp_type, tree.type)

                # breakpoint()

                # Place in global context
                # context[tree.id.text] = context_copy[tree.id.text]

                # Reset function arguments
                for token in list(context.keys()):
                    if token in original_context:
                        context[token] = original_context[token]
                    elif token != tree.id.text:
                        del context[token]

                if tree.id.text in self.fun_calls:
                    for fc_tree, fc_context, fc_exp_type in self.fun_calls[
                        tree.id.text
                    ]:
                        trans += self.type_node(
                            fc_tree, context | fc_context, fc_exp_type
                        )
                    del self.fun_calls[tree.id.text]

                return trans

            case StmtNode():
                return self.type_node(tree.stmt, context, exp_type)

            case ReturnNode():
                if tree.exp:
                    trans = self.type_node(tree.exp, context, exp_type)
                    return trans

                trans = self.unify(exp_type, VoidTypeNode(None, span=tree.span))
                return trans

            case StmtAssNode():
                expr_exp_type = PolymorphicTypeNode.fresh()
                trans = self.type_node(tree.exp, context, expr_exp_type)
                # context = self.apply_trans_context(trans, context)

                assignment_exp_type = PolymorphicTypeNode.fresh()
                trans += self.type_node(tree.id, context, assignment_exp_type)
                # breakpoint()
                # context = self.apply_trans_context(trans, context)

                trans += self.unify(
                    self.apply_trans(expr_exp_type, trans),
                    self.apply_trans(assignment_exp_type, trans),
                )

                # TODO: We dont use exp_type. Does that matter?
                # trans += self.unify(exp_type, VoidTypeNode(None))

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
                    self.apply_trans(
                        TupleNode(left_fresh, right_fresh, span=tree.span), trans
                    ),
                )

                return trans

            case ListNode():
                if tree.body:
                    # body_exp_type = PolymorphicTypeNode.fresh()
                    # trans = self.type_node(tree.body, context, body_exp_type)
                    # return self.unify(exp_type, ListNode(self.apply_trans(body_exp_type, trans)))
                    # breakpoint()
                    raise Exception("List body should not be filled at this stage")
                else:
                    return self.unify(
                        exp_type, ListNode(PolymorphicTypeNode.fresh(), span=tree.span)
                    )

            case Op2Node():
                if tree.operator.type == Type.COLON:
                    left_exp_type = PolymorphicTypeNode.fresh()
                    right_exp_type = ListNode(left_exp_type, span=tree.right.span)
                    output_exp_type = right_exp_type

                elif tree.operator.type in (
                    Type.PLUS,
                    Type.MINUS,
                    Type.STAR,
                    Type.SLASH,
                    Type.PERCENT,
                ):
                    left_exp_type = IntTypeNode(None, span=tree.left.span)
                    right_exp_type = left_exp_type
                    output_exp_type = left_exp_type

                elif tree.operator.type in (
                    Type.LEQ,
                    Type.GEQ,
                    Type.LT,
                    Type.GT,
                ):
                    left_exp_type = IntTypeNode(None, span=tree.left.span)
                    right_exp_type = left_exp_type
                    output_exp_type = BoolTypeNode(None, span=tree.span)

                elif tree.operator.type in (Type.OR, Type.AND):
                    left_exp_type = BoolTypeNode(None, span=tree.left.span)
                    right_exp_type = left_exp_type
                    output_exp_type = left_exp_type

                elif tree.operator.type in (Type.DEQUALS, Type.NEQ):
                    left_exp_type = PolymorphicTypeNode.fresh()
                    right_exp_type = left_exp_type
                    output_exp_type = BoolTypeNode(None, span=tree.span)

                else:
                    raise Exception("Incorrect Op2Node")

                trans = self.type_node(tree.left, context, left_exp_type)
                context = self.apply_trans_context(trans, context)
                trans += self.type_node(
                    tree.right, context, self.apply_trans(right_exp_type, trans)
                )
                trans += self.unify(
                    self.apply_trans(exp_type, trans),
                    self.apply_trans(output_exp_type, trans),
                )
                return trans

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
                    condition, trans_context, BoolTypeNode(None, span=condition.span)
                )
                return transformation_then + transformation_else + trans_condition

            case WhileNode():
                condition = tree.cond
                body = tree.body

                original_context = context.copy()

                transformation_body = []
                for expression in body:
                    trans = self.type_node(expression, context, exp_type)
                    context = self.apply_trans_context(trans, context)
                    transformation_body += trans

                trans_context = self.apply_trans_context(
                    transformation_body, original_context
                )
                trans_condition = self.type_node(
                    condition, trans_context, BoolTypeNode(None, span=condition.span)
                )

                return trans_condition

            case FunCallNode():
                # self.i += 1
                # print(self.i, end="\r")
                # return self.type_node(tree, context, PolymorphicTypeNode.fresh())

                # """
                if tree.func.text in context:
                    # print(tree.func.text)
                    # breakpoint()
                    fun_type = context[tree.func.text]
                    if len(tree.args.items) != len(fun_type.types):
                        raise Exception("Wrong number of arguments")

                    # The transformations that we want to return
                    return_trans = []
                    # The transformations that we only want to locally apply here
                    local_trans = []
                    for call_arg, decl_arg_type in zip(tree.args.items, fun_type.types):
                        # Get the type of the argument
                        fresh = PolymorphicTypeNode.fresh()
                        trans = self.type_node(call_arg, context, fresh)
                        call_arg_type = self.apply_trans(fresh, trans)
                        # TODO: Should we also return fresh -> other
                        return_trans += trans

                        # local_trans += self.unify(decl_arg_type, call_arg_type)
                        trans = self.unify(
                            decl_arg_type, call_arg_type, left_to_right=True
                        )
                        # return_trans += [t for t in trans if t[0] == fresh]
                        # local_trans += [t for t in trans if t[0] != fresh]
                        # local_trans += trans
                        for left, right, left_to_right in trans:
                            if left_to_right:
                                local_trans += [(left, right)]
                            else:
                                return_trans += [(left, right)]

                    # Get the return type using both transformation types
                    ret_type = self.apply_trans(
                        fun_type.ret_type, return_trans + local_trans
                    )
                    return_trans += self.unify(exp_type, ret_type)

                    # print("FunCall stats:")
                    # pprint(context)
                    # pprint(return_trans)
                    # pprint(local_trans)
                    # pprint(self.apply_trans_context(return_trans, context))
                    # breakpoint()
                    return return_trans

                else:
                    self.fun_calls[tree.func.text].append(
                        (tree, context.copy(), exp_type)
                    )
                    return []

                """
                else:
                    fun_types = []
                    for arg in tree.args.items:
                        if arg.text in context:
                            fun_types.append(context[arg.text])
                        else:
                            raise Exception(f"Unknown Variable {arg_context.text!r}")

                #     ret_type = PolymorphicTypeNode.fresh()
                #     fun_type = FunTypeNode(fun_types, ret_type)

                #     # context[tree.func.text] = fun_type

                #     trans = self.unify(exp_type, ret_type)

                    return trans
                # """
                pass

            case VariableNode():
                # transformation is of type: Dict[str, TypeNode]
                if not tree.field:
                    return self.type_node(tree.id, context, exp_type)

                # breakpoint()
                if tree.id.text not in context:
                    raise Exception("Undefined variable")

                variable_type = context[tree.id.text]
                # trans = []
                for field in tree.field.fields:
                    match field.type:
                        case Type.FST | Type.SND:
                            left = PolymorphicTypeNode.fresh()
                            right = PolymorphicTypeNode.fresh()
                            var_exp_type = TupleNode(left=left, right=right)
                            trans = self.unify(variable_type, var_exp_type)
                            context = self.apply_trans_context(trans, context)

                            # For next iteration
                            picked = left if field.type == Type.FST else right
                            variable_type = self.apply_trans(picked, trans)

                        case Type.HD | Type.TL:
                            element = PolymorphicTypeNode.fresh()
                            var_exp_type = ListNode(element)
                            trans = self.unify(variable_type, var_exp_type)
                            context = self.apply_trans_context(trans, context)

                            # For next iteration
                            picked = var_exp_type if field.type == Type.TL else element
                            variable_type = self.apply_trans(picked, trans)

                        case _:
                            raise Exception("Unreachable compiler code")

                trans = self.unify(exp_type, variable_type)
                # context = self.apply_trans_context(trans, context)
                # breakpoint()
                return trans

        raise Exception(f"Node had no handler\n\n{tree}")

    def apply_trans(
        self, node: TypeNode, trans: List[Tuple[PolymorphicTypeNode, TypeNode]]
    ) -> TypeNode:
        sub_transformer = SubstitutionTransformer()
        return sub_transformer.visit(node, trans)

    def apply_trans_context(
        self,
        trans: List[Tuple[PolymorphicTypeNode, TypeNode]],
        context: Dict[str, TypeNode],
    ) -> Dict[str, TypeNode]:

        if trans:
            for var_name, var_type in context.items():
                context[var_name] = self.apply_trans(var_type, trans)

        return context

    def unify(
        self, type_one: TypeNode, type_two: TypeNode, left_to_right: bool = False
    ) -> List[Tuple[str, TypeNode]]:
        # Goal: Return a list of tuples, each tuple is a substitution from left to right
        if isinstance(type_one, IntTypeNode) and isinstance(type_two, IntTypeNode):
            return []

        if isinstance(type_one, BoolTypeNode) and isinstance(type_two, BoolTypeNode):
            return []

        if isinstance(type_one, CharTypeNode) and isinstance(type_two, CharTypeNode):
            return []

        if isinstance(type_one, VoidTypeNode) and isinstance(type_two, VoidTypeNode):
            return []

        if type_one == type_two:
            return []

        # If left is very general, e.g. "a", and right is specific, e.g. "Int", then map "a" to "Int"
        # TODO: Fail case
        if isinstance(type_one, PolymorphicTypeNode):
            if left_to_right:
                return [(type_one, type_two, True)]
            return [(type_one, type_two)]

        if isinstance(type_two, PolymorphicTypeNode):
            # If we only want to update left based on right, then we just want to return [] here
            # if left_to_right:
            #     return []

            if left_to_right:
                return [(type_two, type_one, False)]
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

            trans = []
            for _type_one, _type_two in zip(type_one.types, type_two.types):
                trans += self.unify(_type_one, _type_two)
            trans += self.unify(type_one.ret_type, type_two.ret_type)
            return trans

        print(type_one.span)
        print(type_two.span)
        raise Exception("Failed to unify", type_one, "and", type_two)


class SubstitutionTransformer(NodeTransformer):
    def visit_PolymorphicTypeNode(
        self,
        node: PolymorphicTypeNode,
        trans: List[Tuple[PolymorphicTypeNode, TypeNode]],
    ) -> Node:
        for left_sub, right_sub in trans:
            if node == left_sub:
                return right_sub
        return node
