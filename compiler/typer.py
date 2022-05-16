import copy
from collections import defaultdict
from pprint import pprint
from typing import Dict, List, Tuple

from compiler.error.communicator import Communicator
from compiler.error.error import UnrecoverableError
from compiler.token import Token
from compiler.tree.visitor import NodeTransformer
from compiler.type import Type
from compiler.util import Span

from compiler.error.typer_error import (  # isort:skip
    BinaryUnifyErrorFactory,
    FieldUnifyErrorFactory,
    FunCallUnifyErrorFactory,
    FunctionRedefinitionError,
    FunctionSignatureTypeError,
    IfConditionUnifyErrorFactory,
    PolymorphicTypeCheckError,
    RedefinitionOfVariableError,
    TyperException,
    UnaryUnifyErrorFactory,
    UnificationError,
    UsageOfUndefinedFunctionError,
    VariableAssignmentUnifyErrorFactory,
    VariableDeclarationUnifyErrorFactory,
    VariableError,
    DefaultUnifyErrorFactory,
    ReturnUnifyErrorFactory,
    VoidAssignmentError,
    VoidFunCallArgError,
    VoidOp2Error,
    VoidReturnError,
    VoidTupleError,
    WhileConditionUnifyErrorFactory,
    WrongNumberOfArgumentsCallError,
    DuplicateArgumentsDeclError,
    WrongNumberOfArgumentsDeclError,
)

from compiler.tree.tree import (  # isort:skip
    BoolTypeNode,
    CharTypeNode,
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
                [PolymorphicTypeNode.fresh()],
                VoidTypeNode(),
            ),
            "isEmpty": FunTypeNode(
                [ListNode(PolymorphicTypeNode.fresh())], BoolTypeNode()
            ),
        }
        trans = self.type_node(tree, var_context, fun_context, ft)
        self.apply_trans(tree, trans)
        # TODO: ErrorRaiser.ERRORS = ErrorRaiser.ERRORS[:5]

        # Make sure that all function calls have been taken care of by function declarations
        for fun_name, fun_calls in self.fun_calls.items():
            # The function with name, fun_name, can be called multiple times
            for fun_call in fun_calls:
                fun_call_node = fun_call[0]
                UsageOfUndefinedFunctionError(self.program, fun_call_node)

        Communicator.communicate(TyperException)
        return tree

    def type_node(
        self,
        tree: Node,
        var_context: Dict[str, TypeNode],
        fun_context: Dict[str, TypeNode],
        exp_type: TypeNode,
        error_factory: UnificationError = DefaultUnifyErrorFactory,
    ) -> Node:
        match tree:

            case Token(type=Type.DIGIT):
                # If tree is e.g. `12`:
                return self.unify(exp_type, IntTypeNode(span=tree.span), error_factory)

            case Token(type=Type.TRUE) | Token(type=Type.FALSE):
                return self.unify(exp_type, BoolTypeNode(span=tree.span), error_factory)

            case Token(type=Type.CHARACTER):
                return self.unify(exp_type, CharTypeNode(span=tree.span), error_factory)

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
                declarations = [
                    decl for decl in tree.body if isinstance(decl, VarDeclNode)
                ] + [decl for decl in tree.body if isinstance(decl, FunDeclNode)]
                for expression in declarations:
                    trans = self.type_node(
                        expression, var_context, fun_context, get_fresh_type()
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformations += trans
                return transformations

            case FunDeclNode():
                # Remember the current function for more precise error messaging
                self.current_function = tree
                # fresh_types = [get_fresh_type() for _ in tree.args.items]
                # context.extend(list(zip(tree.args.items, fresh_types)))
                if tree.type:
                    original_tree_type = copy.copy(tree.type.types)
                else:
                    original_tree_type = None

                original_context = var_context.copy()

                if tree.id.text in fun_context:
                    FunctionRedefinitionError(self.program, tree)
                    return []

                fresh_types = []
                args = set()
                if tree.args:
                    for token in tree.args.items:
                        if token.text in args:
                            DuplicateArgumentsDeclError(self.program, token, tree)
                            return []

                        fresh = PolymorphicTypeNode.fresh()
                        var_context[token.text] = fresh
                        fresh_types.append(fresh)
                        args.add(token.text)

                ret_type = PolymorphicTypeNode.fresh()
                fun_context[tree.id.text] = FunTypeNode(
                    fresh_types,
                    ret_type,
                    span=Span(tree.id.span.start_ln, (-1, -1))
                    if tree.type == None
                    else tree.type.span,
                )

                transformations = []
                for var_decl in tree.var_decl:
                    trans = self.type_node(
                        var_decl,
                        var_context,
                        fun_context,
                        PolymorphicTypeNode.fresh(),
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
                    # If we crash here, we know that the inferred type does not equal the type as provided by the programmer
                    transformations += self.unify(
                        tree.type,
                        inferred_type,
                        FunctionSignatureTypeError(tree, inferred_type),
                    )

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
                    ) in self.fun_calls[tree.id.text]:
                        transformations += self.type_node(
                            fc_tree,
                            var_context | fc_var_context,
                            fun_context | fc_fun_context,
                            fc_exp_type,
                        )
                    del self.fun_calls[tree.id.text]

                # If the programmer has specified a type signature:
                if original_tree_type:
                    # Loop over the original types specified by the programmer, and the inferred types
                    # Check that there are no inconsistencies,
                    seen = {}
                    for og, inf in zip(original_tree_type, inferred_type.types):
                        if not isinstance(og, PolymorphicTypeNode) or not isinstance(
                            inf, PolymorphicTypeNode
                        ):
                            continue

                        if inf.id in seen:
                            if seen[inf.id] != og.id:
                                PolymorphicTypeCheckError(
                                    self.program,
                                    tree,
                                    original_tree_type,
                                    inferred_type.types,
                                )
                                return []
                        else:
                            seen[inf.id] = og.id

                # Place in tree
                tree.type = inferred_type

                # We are now out of the function, so no need to remember it
                self.current_function = None
                return transformations

            case StmtNode():
                # Pass expected type down, except with FunCall, as we don't want
                # FunCall to influence the return value of the function.
                if isinstance(tree.stmt, FunCallNode):
                    exp_type = PolymorphicTypeNode.fresh()
                return self.type_node(tree.stmt, var_context, fun_context, exp_type)

            case ReturnNode():
                if tree.exp:
                    trans = self.type_node(
                        tree.exp,
                        var_context,
                        fun_context,
                        exp_type,
                        ReturnUnifyErrorFactory(tree),
                    )

                    # We cannot return a variable of type Void
                    if any(VoidTypeNode() in x[1] for x in trans):
                        VoidReturnError(self.program, tree)
                        return []

                    return trans

                trans = self.unify(
                    exp_type,
                    VoidTypeNode(span=tree.span),
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
                )
                # context = self.apply_trans_context(trans, context)

                assignment_exp_type = PolymorphicTypeNode.fresh()
                trans += self.type_node(
                    tree.id, var_context, fun_context, assignment_exp_type
                )

                # We cannot make an assignment of type void
                if any(VoidTypeNode() in x[1] for x in trans):
                    VoidAssignmentError(self.program, tree)
                    return []

                trans += self.unify(
                    self.apply_trans(expr_exp_type, trans),
                    self.apply_trans(assignment_exp_type, trans),
                    VariableAssignmentUnifyErrorFactory(tree),
                )

                # TODO: We dont use exp_type. Does that matter?
                # trans += self.unify(exp_type, VoidTypeNode(None))

                return trans

            case TupleNode():
                # TODO: Should we return these if they occur in trans?
                left_fresh = PolymorphicTypeNode.fresh()
                right_fresh = PolymorphicTypeNode.fresh()

                # Left side recursion
                trans = self.type_node(tree.left, var_context, fun_context, left_fresh)
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)

                # Right side recursion
                trans += self.type_node(
                    tree.right, var_context, fun_context, right_fresh
                )

                # Left nor the right side of the tuple can be Void
                if any(VoidTypeNode() in x[1] for x in trans):
                    VoidTupleError(self.program, tree)
                    return []

                # Unification with expected type
                trans += self.unify(
                    self.apply_trans(exp_type, trans),
                    self.apply_trans(
                        TupleNode(left_fresh, right_fresh, span=tree.span), trans
                    ),
                    error_factory,
                )

                return trans

            case ListNode():
                if tree.body:
                    # body_exp_type = PolymorphicTypeNode.fresh()
                    # trans = self.type_node(tree.body, context, body_exp_type)
                    # return self.unify(exp_type, ListNode(self.apply_trans(body_exp_type, trans)))
                    # breakpoint()

                    # We only get here if the parser fails
                    UnrecoverableError(
                        f"Error while typing the body of a list node on line [{tree.body.span.start_ln}]."
                    )
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
                        left_exp_type = IntTypeNode(span=tree.left.span)
                        right_exp_type = left_exp_type
                        output_exp_type = left_exp_type

                    case (Type.LEQ | Type.GEQ | Type.LT | Type.GT):
                        left_exp_type = IntTypeNode(span=tree.left.span)
                        right_exp_type = left_exp_type
                        output_exp_type = BoolTypeNode(span=tree.span)

                    case (Type.OR | Type.AND):
                        left_exp_type = BoolTypeNode(span=tree.left.span)
                        right_exp_type = left_exp_type
                        output_exp_type = left_exp_type

                    case (Type.DEQUALS | Type.NEQ):
                        left_exp_type = PolymorphicTypeNode.fresh()
                        right_exp_type = left_exp_type
                        output_exp_type = BoolTypeNode(span=tree.span)
                    case _:
                        UnrecoverableError(
                            f"The binary operator {tree.operator.type} is not supported by the typer of this compiler."
                        )

                trans = self.type_node(
                    tree.left,
                    var_context,
                    fun_context,
                    left_exp_type,
                    BinaryUnifyErrorFactory(tree),
                )
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)
                trans += self.type_node(
                    tree.right,
                    var_context,
                    fun_context,
                    self.apply_trans(right_exp_type, trans),
                    BinaryUnifyErrorFactory(tree),
                )

                # Void cannot be used in a binary operation
                if any(VoidTypeNode() in x[1] for x in trans):
                    VoidOp2Error(self.program, tree)
                    return []

                trans += self.unify(
                    self.apply_trans(exp_type, trans),
                    self.apply_trans(output_exp_type, trans),
                    BinaryUnifyErrorFactory(tree),
                )
                return trans

            case Op1Node():
                if tree.operator.type == Type.NOT:
                    operand_exp_type = BoolTypeNode(span=tree.operand.span)
                    output_exp_type = BoolTypeNode(span=tree.span)
                elif tree.operator.type == Type.MINUS:
                    operand_exp_type = IntTypeNode(span=tree.operand.span)
                    output_exp_type = IntTypeNode(span=tree.span)

                trans = self.type_node(
                    tree.operand,
                    var_context,
                    fun_context,
                    operand_exp_type,
                    UnaryUnifyErrorFactory(tree),
                )
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)

                # Void cannot be used in an unary operation, but we don't need to verify this,
                # as the above self.type_node call already ensured that the operand is not Void.

                trans += self.unify(
                    self.apply_trans(exp_type, trans),
                    self.apply_trans(output_exp_type, trans),
                    UnaryUnifyErrorFactory(tree),
                )
                return trans

            case VarDeclNode():

                if tree.id.text in var_context:
                    RedefinitionOfVariableError(self.program, tree)
                    return []

                match tree.type:
                    case Token(type=Type.VAR):
                        expr_exp_type = PolymorphicTypeNode.fresh()
                    case Node():
                        expr_exp_type = tree.type
                    case None:
                        expr_exp_type = PolymorphicTypeNode.fresh()
                    case _:
                        UnrecoverableError(
                            f"The variable declaration type {tree.type} is not allowed."
                        )
                trans = self.type_node(
                    tree.exp,
                    var_context,
                    fun_context,
                    expr_exp_type,
                    VariableDeclarationUnifyErrorFactory(tree),
                )

                # We cannot make an assignment of type void
                if any(VoidTypeNode() in x[1] for x in trans):
                    VoidAssignmentError(self.program, tree)
                    return []

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
                        expression, var_context, fun_context, original_sigma
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformation_then += trans

                sigma_else = self.apply_trans(original_sigma, transformation_then)

                transformation_else = []
                for expression in else_branch:
                    trans = self.type_node(
                        expression, var_context, fun_context, sigma_else
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
                    BoolTypeNode(span=condition.span),
                    IfConditionUnifyErrorFactory(tree),
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
                        expression, var_context, fun_context, exp_type
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
                    BoolTypeNode(span=condition.span),
                    WhileConditionUnifyErrorFactory(tree),
                )

                return trans_condition

            case FunCallNode():

                if tree.func.text in fun_context:
                    fun_type = fun_context[tree.func.text]
                    # The transformations that we want to return
                    return_trans = []
                    # The transformations that we only want to locally apply here
                    local_trans = []

                    len_call_args = len(tree.args.items) if tree.args else 0
                    if len_call_args != len(fun_type.types):
                        WrongNumberOfArgumentsCallError(
                            self.program,
                            tree,
                            len(fun_type.types),
                            len_call_args,
                        )
                        return []

                    if tree.args:
                        # Track if there is a (Void) error at some point for any of the arguments
                        error = False
                        for call_arg, decl_arg_type in zip(
                            tree.args.items, fun_type.types
                        ):
                            # Get the type of the argument
                            fresh = PolymorphicTypeNode.fresh()
                            trans = self.type_node(
                                call_arg, var_context, fun_context, fresh
                            )
                            call_arg_type = self.apply_trans(fresh, trans)
                            # TODO: Should we also return fresh -> other
                            return_trans += trans

                            # local_trans += self.unify(decl_arg_type, call_arg_type)

                            trans = self.unify(
                                decl_arg_type,
                                call_arg_type,
                                FunCallUnifyErrorFactory(tree),
                                left_to_right=True,
                            )
                            # We cannot use Void as a function call parameter
                            if any(VoidTypeNode() in x[1] for x in trans):
                                VoidFunCallArgError(self.program, call_arg)
                                error = True
                                continue

                            for left, right, left_to_right in trans:
                                if left_to_right:
                                    local_trans += [(left, right)]
                                else:
                                    return_trans += [(left, right)]

                        # Return nothing if there was an error.
                        # This prevents (unnecessary, useless) stacking errors
                        if error:
                            return []

                    # Get the return type using both transformation types
                    ret_type = self.apply_trans(
                        copy.deepcopy(fun_type.ret_type), return_trans + local_trans
                    )
                    tree.type = self.apply_trans(
                        copy.deepcopy(fun_type), return_trans + local_trans
                    )
                    return_trans += self.unify(exp_type, ret_type, error_factory)

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
                        (tree, var_context.copy(), fun_context.copy(), exp_type)
                    )
                    return []

            case VariableNode():
                # transformation is of type: Dict[str, TypeNode]
                if not tree.field:
                    return self.type_node(tree.id, var_context, fun_context, exp_type)

                if tree.id.text not in var_context:
                    VariableError(self.program, tree.id)
                    return []

                variable_type = var_context[tree.id.text]
                trans = []
                for field in tree.field.fields:
                    match field.type:
                        case Type.FST | Type.SND:
                            left = PolymorphicTypeNode.fresh()
                            right = PolymorphicTypeNode.fresh()
                            var_exp_type = TupleNode(
                                left=left,
                                right=right,
                            )
                            sub = self.unify(
                                var_exp_type,
                                variable_type,
                                FieldUnifyErrorFactory(tree),
                            )
                            var_context = self.apply_trans_context(sub, var_context)
                            fun_context = self.apply_trans_context(sub, fun_context)
                            trans += sub

                            # For next iteration
                            picked = left if field.type == Type.FST else right
                            variable_type = self.apply_trans(picked, sub)

                        case Type.HD | Type.TL:
                            element = PolymorphicTypeNode.fresh()
                            var_exp_type = ListNode(element)
                            sub = self.unify(
                                var_exp_type,
                                variable_type,
                                FieldUnifyErrorFactory(tree),
                            )
                            var_context = self.apply_trans_context(sub, var_context)
                            fun_context = self.apply_trans_context(sub, fun_context)
                            trans += sub

                            # For next iteration
                            picked = var_exp_type if field.type == Type.TL else element
                            variable_type = self.apply_trans(picked, sub)

                        case _:
                            UnrecoverableError(
                                f"The field {field.type} is not supported."
                            )

                trans += self.unify(exp_type, variable_type)
                # context = self.apply_trans_context(trans, context)
                # breakpoint()
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

    # Type_one is considered to be the expected type
    def unify(
        self,
        type_one: TypeNode,
        type_two: TypeNode,
        error_factory: UnificationError = None,
        left_to_right: bool = False,
    ) -> List[Tuple[str, TypeNode]]:
        # Return a list of tuples, each tuple is a substitution from left to right

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
            return self.unify(
                type_one.body, type_two.body, error_factory, left_to_right=left_to_right
            )

        if isinstance(type_one, TupleNode) and isinstance(type_two, TupleNode):
            before = self.unify(
                type_one.left, type_two.left, error_factory, left_to_right=left_to_right
            )
            type_one = self.apply_trans(type_one, before)
            type_two = self.apply_trans(type_two, before)

            after = self.unify(
                type_one.right,
                type_two.right,
                error_factory,
                left_to_right=left_to_right,
            )
            type_one = self.apply_trans(type_one, after)
            type_two = self.apply_trans(type_two, after)
            return before + after

        if isinstance(type_one, FunTypeNode) and isinstance(type_two, FunTypeNode):
            if len(type_one.types) != len(type_two.types):
                WrongNumberOfArgumentsDeclError(
                    self.program,
                    self.current_function,
                    len(type_two.types),
                    len(type_one.types),
                )
                return []

            # print("Before")
            # print(type_one)
            # print(type_two)
            # print()

            transformations = []
            for i in range(len(type_one.types)):
                _type_one = type_one.types[i]
                _type_two = type_two.types[i]
                trans = self.unify(
                    _type_one, _type_two, error_factory, left_to_right=left_to_right
                )
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
                type_one.ret_type,
                type_two.ret_type,
                error_factory,
                left_to_right=left_to_right,
            )
            # breakpoint()
            type_one = self.apply_trans(type_one, trans)
            type_two = self.apply_trans(type_two, trans)
            transformations += trans
            return transformations

        if not isinstance(error_factory, UnificationError):
            error_factory = DefaultUnifyErrorFactory()

        error_factory.build(
            type_one=type_one,
            type_two=type_two,
            program=self.program,
            function=self.current_function,
        )
        return []


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
