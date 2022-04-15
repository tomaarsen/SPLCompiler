from collections import defaultdict
from functools import partial
from pprint import pprint
from typing import Any, Dict, List, Tuple

from compiler.error.error import ErrorRaiser, UnrecoverableError
from compiler.token import Token
from compiler.tree.visitor import Boolean, NodeTransformer
from compiler.type import Type
from compiler.util import Span

from compiler.error.typer_error import (  # isort:skip
    FunctionRedefinitionError,
    TyperException,
    UnificationError,
    VariableError,
    DefaultUnifyErrorFactory,
    ReturnUnifyErrorFactory,
)

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
    Op1Node,
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
        self.program = program
        self.i = 0
        self.fun_calls = defaultdict(list)
        # Keeps track of the current function that is checked
        self.current_function = None

    def type(self, tree: Node):
        ft = get_fresh_type()
        var_context = {}
        fun_context = {
            "print": FunTypeNode(
                [PolymorphicTypeNode.fresh()], VoidTypeNode(None, span=None), span=None
            ),
            "isEmpty": FunTypeNode(
                [ListNode(PolymorphicTypeNode.fresh(), span=None)],
                BoolTypeNode(None, span=None),
                span=None,
            ),
        }
        trans = self.type_node(tree, var_context, fun_context, ft)
        self.apply_trans(tree, trans)
        # TODO: ErrorRaiser.ERRORS = ErrorRaiser.ERRORS[:5]

        # Make sure that all function calls have been taken care of by function declarations
        if len(self.fun_calls):
            raise Exception(
                f"The following functions are used, but have not been defined: {list(self.fun_calls.keys())!r}"
            )

        ErrorRaiser.raise_all(TyperException)
        return tree

    def type_node(
        self,
        tree: Node,
        var_context: Dict[str, TypeNode],
        fun_context: Dict[str, TypeNode],
        exp_type: TypeNode,
        error_factory: UnificationError = DefaultUnifyErrorFactory,
        **kwargs,
    ) -> Node:
        match tree:

            case Token(type=Type.DIGIT):
                # If tree is e.g. `12`:
                return self.unify(
                    exp_type, IntTypeNode(None, span=tree.span), error_factory
                )

            case Token(type=Type.TRUE) | Token(type=Type.FALSE):
                return self.unify(
                    exp_type, BoolTypeNode(None, span=tree.span), error_factory
                )

            case Token(type=Type.CHARACTER):
                return self.unify(
                    exp_type, CharTypeNode(None, span=tree.span), error_factory
                )

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
                if tree.text not in var_context:
                    VariableError(self.program, tree)
                    return []

                context_type = var_context[tree.text]
                return self.unify(exp_type, context_type, error_factory)

            case SPLNode():
                transformations = []
                for expression in tree.body:
                    trans = self.type_node(
                        expression, var_context, fun_context, get_fresh_type(), **kwargs
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformations += trans
                return transformations

            case FunDeclNode():
                self.current_function = tree
                # fresh_types = [get_fresh_type() for _ in tree.args.items]
                # context.extend(list(zip(tree.args.items, fresh_types)))

                original_context = var_context.copy()

                if tree.id.text in fun_context:
                    FunctionRedefinitionError(self.program, tree)
                    return []

                fresh_types = []
                args = set()
                if tree.args:
                    for token in tree.args.items:
                        if token.text in args:
                            # breakpoint()
                            # print(tree.args)
                            raise Exception(
                                f"Function {tree.id.text!r} has multiple function parameters with the same name: {token.text!r}."
                            )
                        fresh = PolymorphicTypeNode.fresh()
                        var_context[token.text] = fresh
                        fresh_types.append(fresh)
                        args.add(token.text)

                ret_type = PolymorphicTypeNode.fresh()
                fun_context[tree.id.text] = FunTypeNode(
                    fresh_types,
                    ret_type,
                    span=Span(tree.id.span.start_ln, (-1, -1)),
                )

                transformations = []
                for var_decl in tree.var_decl:
                    trans = self.type_node(
                        var_decl,
                        var_context,
                        fun_context,
                        PolymorphicTypeNode.fresh(),
                        **kwargs,
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformations += trans

                for stmt in tree.stmt:
                    # print(context[tree.id.text].ret_type)
                    trans = self.type_node(
                        stmt,
                        var_context,
                        fun_context,
                        fun_context[tree.id.text].ret_type,
                        **kwargs,
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    # print("-" * 30)
                    # print(stmt.__class__.__name__)
                    # pprint(var_context)
                    # pprint(fun_context)
                    # breakpoint()
                    transformations += trans

                inferred_type = fun_context[tree.id.text]
                # transformations += self.unify(
                #     self.apply_trans(exp_type, transformations), tree.type
                # )
                transformations += self.unify(exp_type, inferred_type)

                # Compare the inferred type with the developer-supplied type, if any (type checking)
                if tree.type:
                    # TODO: Error
                    # If we crash here, we know that the inferred type does not equal the type as provided by the programmer
                    # breakpoint()
                    transformations += self.unify(tree.type, inferred_type)

                # Reset function arguments
                for token in list(var_context.keys()):
                    if token in original_context:
                        var_context[token] = original_context[token]
                    elif token != tree.id.text:
                        del var_context[token]

                if tree.id.text in self.fun_calls:
                    for (
                        fc_tree,
                        fc_var_context,
                        fc_fun_context,
                        fc_exp_type,
                        fc_kwargs,
                    ) in self.fun_calls[tree.id.text]:
                        transformations += self.type_node(
                            fc_tree,
                            var_context | fc_var_context,
                            fun_context | fc_fun_context,
                            fc_exp_type,
                            **fc_kwargs,
                        )
                    del self.fun_calls[tree.id.text]

                # Place in tree
                tree.type = inferred_type

                return transformations

            case StmtNode():
                # Pass expected type down - this is the expected type of the return here,
                # so all children of tree.stmt should ignore this, except ReturnNode
                return self.type_node(
                    tree.stmt, var_context, fun_context, exp_type, **kwargs
                )

            case ReturnNode():
                if tree.exp:
                    trans = self.type_node(
                        tree.exp,
                        var_context,
                        fun_context,
                        exp_type,
                        ReturnUnifyErrorFactory(tree),
                        return_funcall=True,
                        **kwargs,
                    )
                    return trans

                trans = self.unify(
                    exp_type,
                    VoidTypeNode(None, span=tree.span),
                    ReturnUnifyErrorFactory(tree),
                )
                return trans

            case StmtAssNode():
                expr_exp_type = PolymorphicTypeNode.fresh()
                trans = self.type_node(
                    tree.exp,
                    var_context,
                    fun_context,
                    expr_exp_type,
                    return_funcall=True,
                    **kwargs,
                )
                # context = self.apply_trans_context(trans, context)

                assignment_exp_type = PolymorphicTypeNode.fresh()
                trans += self.type_node(
                    tree.id, var_context, fun_context, assignment_exp_type, **kwargs
                )
                # context = self.apply_trans_context(trans, context)

                trans += self.unify(
                    self.apply_trans(expr_exp_type, trans),
                    self.apply_trans(assignment_exp_type, trans),
                )

                # TODO: We dont use exp_type. Does that matter?
                # trans += self.unify(exp_type, VoidTypeNode(None))

                return trans

            case TupleNode():
                # TODO: Should we return these if they occur in trans?
                left_fresh = PolymorphicTypeNode.fresh()
                right_fresh = PolymorphicTypeNode.fresh()

                # Left side recursion
                trans = self.type_node(
                    tree.left, var_context, fun_context, left_fresh, **kwargs
                )
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)

                # Right side recursion
                trans += self.type_node(
                    tree.right, var_context, fun_context, right_fresh, **kwargs
                )

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

                    # We only get here if the parser fails
                    raise Exception("List body should not be filled at this stage")
                else:
                    return self.unify(
                        exp_type, ListNode(PolymorphicTypeNode.fresh(), span=tree.span)
                    )

            case Op2Node():
                match tree.operator.type:
                    case Type.COLON:
                        left_exp_type = PolymorphicTypeNode.fresh()
                        right_exp_type = ListNode(left_exp_type, span=tree.right.span)
                        output_exp_type = right_exp_type

                    case (
                        Type.PLUS | Type.MINUS | Type.STAR | Type.SLASH | Type.PERCENT
                    ):
                        left_exp_type = IntTypeNode(None, span=tree.left.span)
                        right_exp_type = left_exp_type
                        output_exp_type = left_exp_type

                    case (Type.LEQ | Type.GEQ | Type.LT | Type.GT):
                        left_exp_type = IntTypeNode(None, span=tree.left.span)
                        right_exp_type = left_exp_type
                        output_exp_type = BoolTypeNode(None, span=tree.span)

                    case (Type.OR | Type.AND):
                        left_exp_type = BoolTypeNode(None, span=tree.left.span)
                        right_exp_type = left_exp_type
                        output_exp_type = left_exp_type

                    case (Type.DEQUALS | Type.NEQ):
                        left_exp_type = PolymorphicTypeNode.fresh()
                        right_exp_type = left_exp_type
                        output_exp_type = BoolTypeNode(None, span=tree.span)
                    case _:
                        # Op2 node not yet supported
                        raise Exception("Incorrect Op2Node")

                trans = self.type_node(
                    tree.left, var_context, fun_context, left_exp_type, **kwargs
                )
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)
                trans += self.type_node(
                    tree.right,
                    var_context,
                    fun_context,
                    self.apply_trans(right_exp_type, trans),
                    **kwargs,
                )
                trans += self.unify(
                    self.apply_trans(exp_type, trans),
                    self.apply_trans(output_exp_type, trans),
                )
                return trans

            case Op1Node():
                if tree.operator.type == Type.NOT:
                    operand_exp_type = BoolTypeNode(None, span=tree.operand.span)
                    output_exp_type = BoolTypeNode(None, span=tree.span)
                elif tree.operator.type == Type.MINUS:
                    operand_exp_type = IntTypeNode(None, span=tree.operand.span)
                    output_exp_type = IntTypeNode(None, span=tree.span)

                trans = self.type_node(
                    tree.operand, var_context, fun_context, operand_exp_type, **kwargs
                )
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)
                trans += self.unify(
                    self.apply_trans(exp_type, trans),
                    self.apply_trans(output_exp_type, trans),
                )
                return trans

            case VarDeclNode():

                if tree.id.text in var_context:
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

                trans = self.type_node(
                    tree.exp,
                    var_context,
                    fun_context,
                    expr_exp_type,
                    return_funcall=True,
                    **kwargs,
                )

                # Place in tree & global context
                tree.type = expr_exp_type
                var_context[tree.id.text] = expr_exp_type
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)

                return trans

            case IfElseNode():
                condition = tree.cond
                then_branch = tree.body
                else_branch = tree.else_body

                original_sigma = exp_type
                original_var_context = var_context.copy()
                original_fun_context = fun_context.copy()

                transformation_then = []
                for expression in then_branch:
                    trans = self.type_node(
                        expression, var_context, fun_context, original_sigma, **kwargs
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformation_then += trans

                sigma_else = self.apply_trans(original_sigma, transformation_then)

                transformation_else = []
                for expression in else_branch:
                    trans = self.type_node(
                        expression, var_context, fun_context, sigma_else, **kwargs
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformation_else += trans

                trans_context = self.apply_trans_context(
                    transformation_then + transformation_else, original_var_context
                )
                trans_condition = self.type_node(
                    condition,
                    trans_context,
                    original_fun_context,
                    BoolTypeNode(None, span=condition.span),
                    **kwargs,
                )
                return transformation_then + transformation_else + trans_condition

            case WhileNode():
                condition = tree.cond
                body = tree.body

                original_var_context = var_context.copy()
                original_fun_context = fun_context.copy()

                transformation_body = []
                for expression in body:
                    trans = self.type_node(
                        expression, var_context, fun_context, exp_type, **kwargs
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformation_body += trans

                original_var_context = self.apply_trans_context(
                    transformation_body, original_var_context
                )
                original_fun_context = self.apply_trans_context(
                    transformation_body, original_fun_context
                )
                trans_condition = self.type_node(
                    condition,
                    original_var_context,
                    original_fun_context,
                    BoolTypeNode(None, span=condition.span),
                    **kwargs,
                )

                return trans_condition

            case FunCallNode():
                # self.i += 1
                # print(self.i, end="\r")
                # return self.type_node(tree, context, PolymorphicTypeNode.fresh())

                # """
                if tree.func.text in fun_context:
                    fun_type = fun_context[tree.func.text]
                    # The transformations that we want to return
                    return_trans = []
                    # The transformations that we only want to locally apply here
                    local_trans = []

                    if tree.args:
                        if len(tree.args.items) != len(fun_type.types):
                            raise Exception("Wrong number of arguments")

                        for call_arg, decl_arg_type in zip(
                            tree.args.items, fun_type.types
                        ):
                            # Get the type of the argument
                            fresh = PolymorphicTypeNode.fresh()
                            trans = self.type_node(
                                call_arg, var_context, fun_context, fresh, **kwargs
                            )
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
                    if kwargs.get("return_funcall", False):
                        ret_type = self.apply_trans(
                            fun_type.ret_type, return_trans + local_trans
                        )
                        return_trans += self.unify(exp_type, ret_type)

                    # if tree.args.items[0].text == "l":
                    #     print("FunCall stats:")
                    #     pprint(var_context)
                    #     pprint(fun_context)
                    #     pprint(return_trans)
                    #     pprint(local_trans)
                    #     pprint(self.apply_trans_context(return_trans, var_context))
                    #     pprint(self.apply_trans_context(return_trans, fun_context))
                    #     breakpoint()
                    return return_trans

                else:
                    self.fun_calls[tree.func.text].append(
                        (tree, var_context.copy(), fun_context.copy(), exp_type, kwargs)
                    )
                    return []

            case VariableNode():
                # transformation is of type: Dict[str, TypeNode]
                if not tree.field:
                    return self.type_node(
                        tree.id, var_context, fun_context, exp_type, **kwargs
                    )

                # breakpoint()
                if tree.id.text not in var_context:
                    raise Exception("Undefined variable")

                variable_type = var_context[tree.id.text]
                trans = []
                for field in tree.field.fields:
                    match field.type:
                        case Type.FST | Type.SND:
                            left = PolymorphicTypeNode.fresh()
                            right = PolymorphicTypeNode.fresh()
                            var_exp_type = TupleNode(left=left, right=right, span=None)
                            sub = self.unify(var_exp_type, variable_type)
                            var_context = self.apply_trans_context(sub, var_context)
                            fun_context = self.apply_trans_context(sub, fun_context)
                            trans += sub

                            # For next iteration
                            picked = left if field.type == Type.FST else right
                            variable_type = self.apply_trans(picked, trans)

                        case Type.HD | Type.TL:
                            element = PolymorphicTypeNode.fresh()
                            var_exp_type = ListNode(element, span=None)
                            sub = self.unify(variable_type, var_exp_type)
                            var_context = self.apply_trans_context(trans, var_context)
                            fun_context = self.apply_trans_context(trans, fun_context)
                            trans += sub

                            # For next iteration
                            picked = var_exp_type if field.type == Type.TL else element
                            variable_type = self.apply_trans(picked, trans)

                        case _:
                            raise Exception("Unreachable compiler code")

                trans += self.unify(exp_type, variable_type)
                # context = self.apply_trans_context(trans, context)
                return trans

        UnrecoverableError(f"Node had no handler\n\n{tree}", TyperException)

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
        self,
        type_one: TypeNode,
        type_two: TypeNode,
        error_factory: UnificationError = DefaultUnifyErrorFactory,
        left_to_right: bool = False,
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
        # NOTE: If type_one in type_two, then we have an error (e.g. we want to go from a -> (a, b), which is recursive)
        # We can abuse this to get a more precise error, but I'm not sure whether that's helpful
        if isinstance(type_one, PolymorphicTypeNode) and type_one not in type_two:
            if left_to_right:
                return [(type_one, type_two, True)]
            return [(type_one, type_two)]

        if isinstance(type_two, PolymorphicTypeNode) and type_two not in type_one:
            if left_to_right:
                return [(type_two, type_one, False)]
            return [(type_two, type_one)]

        if isinstance(type_one, ListNode) and isinstance(type_two, ListNode):
            return self.unify(type_one.body, type_two.body, left_to_right=left_to_right)

        if isinstance(type_one, TupleNode) and isinstance(type_two, TupleNode):
            before = self.unify(
                type_one.left, type_two.left, left_to_right=left_to_right
            )
            type_one = self.apply_trans(type_one, before)
            type_two = self.apply_trans(type_two, before)

            after = self.unify(
                type_one.right, type_two.right, left_to_right=left_to_right
            )
            type_one = self.apply_trans(type_one, after)
            type_two = self.apply_trans(type_two, after)
            return before + after

        if isinstance(type_one, FunTypeNode) and isinstance(type_two, FunTypeNode):
            if len(type_one.types) != len(type_two.types):
                raise Exception("Different number of arguments")

            # print("Before")
            # print(type_one)
            # print(type_two)
            # print()

            transformations = []
            for i in range(len(type_one.types)):
                _type_one = type_one.types[i]
                _type_two = type_two.types[i]
                trans = self.unify(_type_one, _type_two, left_to_right=left_to_right)
                # if trans:
                #     print(trans[0][0], "->", trans[0][1])
                type_one = self.apply_trans(type_one, trans)
                type_two = self.apply_trans(type_two, trans)

                # print(f"After index {i}")
                # print(type_one)
                # print(type_two)
                # print()
                transformations += trans

            trans = self.unify(
                type_one.ret_type, type_two.ret_type, left_to_right=left_to_right
            )
            # breakpoint()
            type_one = self.apply_trans(type_one, trans)
            type_two = self.apply_trans(type_two, trans)
            transformations += trans
            return transformations

        error_factory.build_and_raise(
            type_one, type_two, self.program, self.current_function
        )


class SubstitutionTransformer(NodeTransformer):
    def visit_PolymorphicTypeNode(
        self,
        node: PolymorphicTypeNode,
        trans: List[Tuple[PolymorphicTypeNode, TypeNode]],
    ) -> Node:
        for transformation in trans:
            left_sub, right_sub = transformation[:2]
            if node == left_sub:
                node = right_sub
        return node
