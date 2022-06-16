import copy
from collections import defaultdict
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
    IndexTypeError,
    ListAbbrError,
    PolymorphicTypeCheckError,
    RedefinitionOfLoopVariableError,
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
    TypeNode,
    VarDeclNode,
    VariableNode,
    VoidTypeNode,
    WhileNode,
)


class Typer:
    def __init__(self, program: str) -> None:
        self.program = program
        self.i = 0
        self.fun_calls = defaultdict(list)
        # Keeps track of the current function that is checked
        self.current_function = None

        # Create an instance of our transformation application transformer to use in self.apply_trans
        self.sub_transformer = SubstitutionTransformer()

    def type(self, tree: Node) -> Node:
        """Add type information to the parsed AST from `Parser(program).parse(tokens)`.

        Uses the M-algorithm behind the scenes.

        Args:
            tree (Node): The input AST (potentially) without type information.

        Returns:
            Node: The output AST with type information applied.
        """
        # Store variables and functions in a context as a mapping of variable/function names
        # to the TypeNodes
        var_context = {}
        fun_context = {
            "print": FunTypeNode(
                [PolymorphicTypeNode.fresh()],
                VoidTypeNode(),
            ),
            "println": FunTypeNode(
                [PolymorphicTypeNode.fresh()],
                VoidTypeNode(),
            ),
            "isEmpty": FunTypeNode(
                [ListNode(PolymorphicTypeNode.fresh())], BoolTypeNode()
            ),
            "get_Int": FunTypeNode([], IntTypeNode()),
            "get_Chr": FunTypeNode([], CharTypeNode()),
            "get_Str": FunTypeNode([], ListNode(CharTypeNode())),
            "exit": FunTypeNode([], ListNode(VoidTypeNode())),
            "length": FunTypeNode(
                [ListNode(PolymorphicTypeNode.fresh())], IntTypeNode()
            ),
            "ord": FunTypeNode([CharTypeNode()], IntTypeNode()),
            "chr": FunTypeNode([IntTypeNode()], CharTypeNode()),
            "bool": FunTypeNode([PolymorphicTypeNode.fresh()], BoolTypeNode()),
        }
        # Apply the recursive `type_node` function.
        trans = self.type_node(
            tree,
            var_context,
            fun_context,
            PolymorphicTypeNode.fresh(),
            DefaultUnifyErrorFactory,
        )
        # Apply the final transformations on the tree
        self.apply_trans(tree, trans)

        # Make sure that all function calls have been taken care of by function declarations
        for _fun_name, fun_calls in self.fun_calls.items():
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
        error_factory: UnificationError,
    ) -> List[Tuple[PolymorphicTypeNode, TypeNode]]:
        """Our variant of the M-function in the M-algorithm. Recursively adds typing information to `tree`.

        Args:
            tree (Node): A Node in the AST tree.
            var_context (Dict[str, TypeNode]): The variables defined in this context.
            fun_context (Dict[str, TypeNode]): The functions defined.
            exp_type (TypeNode): The expected type for `tree`.
            error_factory (UnificationError): A detailed error factory that allows errors
                that are caused very deep in the tree to use information from a bit higher
                in the tree. For example, if there is an error in an Op2Node (i.e. an expression),
                then we can throw the exception with information that the expression occurs in the
                condition of an if-statement, in a specific function.

        Returns:
            Node: A transformation, i.e. a list of tuples that represent mappings from very general
                PolymorphicTypeNode instances to more specific TypeNode instances, e.g. IntTypeNode.
        """
        match tree:

            case Token(type=Type.CONTINUE) | Token(type=Type.BREAK):
                """`continue` and `break` do not require typing"""
                return []

            case Token(type=Type.DIGIT):
                """If tree is e.g. `12`, then we unify the expected type with an IntTypeNode"""
                return self.unify(exp_type, IntTypeNode(span=tree.span), error_factory)

            case Token(type=Type.TRUE) | Token(type=Type.FALSE):
                """If tree is e.g. `True`, then we unify the expected type with a BoolTypeNode"""
                return self.unify(exp_type, BoolTypeNode(span=tree.span), error_factory)

            case Token(type=Type.CHARACTER):
                """If tree is e.g. `'a'`, then we unify the expected type with a CharTypeNode"""
                return self.unify(exp_type, CharTypeNode(span=tree.span), error_factory)

            case Token(type=Type.ID):
                """
                If tree is a variable, e.g. `a`, then we first verify that the variable was defined,
                and then we unify the expected type with the known type from the variable context.
                """
                if tree.text not in var_context:
                    VariableError(self.program, tree)
                    return []

                context_type = var_context[tree.text]
                return self.unify(exp_type, context_type, error_factory)

            case SPLNode():
                """
                For the root of the AST, we sort the declarations in order to recursively
                type the variable declarations before the function declarations. Then,
                we iteratively type each of the declarations and append together the
                transformations.
                """
                transformations = []
                declarations = [
                    decl for decl in tree.body if isinstance(decl, VarDeclNode)
                ] + [decl for decl in tree.body if isinstance(decl, FunDeclNode)]
                for expression in declarations:
                    trans = self.type_node(
                        expression,
                        var_context,
                        fun_context,
                        PolymorphicTypeNode.fresh(),
                        error_factory,
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformations += trans
                return transformations

            case FunDeclNode():
                # Remember the current function for more precise error messaging
                self.current_function = tree

                # Track the given tree type
                if tree.type:
                    original_tree_type = copy.deepcopy(tree.type.types)
                else:
                    original_tree_type = None

                original_context = var_context.copy()

                if tree.id.text in fun_context:
                    FunctionRedefinitionError(self.program, tree)
                    return []

                # Add the function arguments to the variable context,
                # and ensure no duplicate argument names (e.g. func(a, a) {...})
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

                # Add the function type to the function context
                ret_type = PolymorphicTypeNode.fresh()
                fun_context[tree.id.text] = FunTypeNode(
                    fresh_types,
                    ret_type,
                    span=Span(tree.id.span.start_ln, (-1, -1))
                    if tree.type == None
                    else tree.type.span,
                )

                # Iterate over the variable declarations and type them
                transformations = []
                for var_decl in tree.var_decl:
                    trans = self.type_node(
                        var_decl,
                        var_context,
                        fun_context,
                        PolymorphicTypeNode.fresh(),
                        error_factory,
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformations += trans

                # Iterate over the statements and type them
                for stmt in tree.stmt:
                    trans = self.type_node(
                        stmt,
                        var_context,
                        fun_context,
                        fun_context[tree.id.text].ret_type,
                        error_factory,
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformations += trans

                # Unify the inferred function type with the expected type
                inferred_type = fun_context[tree.id.text]
                transformations += self.unify(exp_type, inferred_type, error_factory)

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

                # If this function was previously called, then type the function call now
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
                            error_factory,
                        )
                    del self.fun_calls[tree.id.text]

                # If the programmer has specified a polymorphic type signature:
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
                """
                Pass expected type down, except with FunCall, as we don't want
                FunCall to influence the return value of the function.
                """
                if isinstance(tree.stmt, FunCallNode):
                    exp_type = PolymorphicTypeNode.fresh()
                return self.type_node(
                    tree.stmt, var_context, fun_context, exp_type, error_factory
                )

            case ReturnNode():
                """
                If we have an expression, then try to type it, and ensure that the returned
                type is not Void. If there is no expression, then try to unify the expected
                type with Void.
                """
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
                """
                Type both the left and right-hand side of the = in the statement assignment.
                Then, unify both of the types. Also, ensure that we are not assigning to Void.
                """
                expr_exp_type = PolymorphicTypeNode.fresh()
                trans = self.type_node(
                    tree.exp, var_context, fun_context, expr_exp_type, error_factory
                )

                assignment_exp_type = PolymorphicTypeNode.fresh()
                trans += self.type_node(
                    tree.id,
                    var_context,
                    fun_context,
                    assignment_exp_type,
                    error_factory,
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

                return trans

            case TupleNode():
                """
                Type the left, type the right, ensure that neither are void, and then unify
                the expected type with Tuple(left_type, right_type).
                """
                left_fresh = PolymorphicTypeNode.fresh()
                right_fresh = PolymorphicTypeNode.fresh()

                # Left side recursion
                trans = self.type_node(
                    tree.left, var_context, fun_context, left_fresh, error_factory
                )
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)

                # Right side recursion
                trans += self.type_node(
                    tree.right, var_context, fun_context, right_fresh, error_factory
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
                """
                Simply unify with a ListNode with a PolymorphicTypeNode as its list element type.
                ListNode only has a body in one context: In a type (i.e. [a] -> [a])
                """
                if tree.body:
                    # We only get here if the parser fails
                    UnrecoverableError(
                        f"Error while typing the body of a list node on line [{tree.body.span.start_ln}]."
                    )
                    return []
                return self.unify(
                    exp_type,
                    ListNode(PolymorphicTypeNode.fresh(), span=tree.span),
                    error_factory,
                )

            case Op2Node():
                """
                Depending on the operator used, set the expected type for left, right and the output.
                For example, for an == we want left and right to be the same Polymorphic type, while
                the output must be BoolTypeNode. Then, type the left and right sides, ensure
                that neither are Void, and unify the output type too.
                """
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
                """
                Depending on the operator, get the expected operand type and the expected output type.
                Then, type the operand followed by the output. We don't need to check for Void here,
                as ! and - already require specific (non-polymorphic) types.
                """
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
                """
                First ensure that the variable was not already declared. Then, determine the expected
                type for the expression, and type it. Ensure that the type is not Void, and then
                store the variable in the variable context.
                """

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
                var_context[tree.id.text] = expr_exp_type
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)
                tree.type = var_context[tree.id.text]

                return trans

            case IfElseNode():
                """
                First type the then branch, then the else branch, then the condition.
                """
                condition = tree.cond
                then_branch = tree.body
                else_branch = tree.else_body

                original_sigma = exp_type
                original_var_context = var_context.copy()
                original_fun_context = fun_context.copy()

                # Type the then-branch
                transformation_then = []
                for expression in then_branch:
                    trans = self.type_node(
                        expression,
                        var_context,
                        fun_context,
                        original_sigma,
                        error_factory,
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformation_then += trans

                sigma_else = self.apply_trans(original_sigma, transformation_then)

                # Type the else-branch
                transformation_else = []
                for expression in else_branch:
                    trans = self.type_node(
                        expression, var_context, fun_context, sigma_else, error_factory
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    transformation_else += trans

                trans_context = self.apply_trans_context(
                    transformation_then + transformation_else, original_var_context
                )

                # Type the condition
                trans_condition = self.type_node(
                    condition,
                    trans_context,
                    original_fun_context,
                    BoolTypeNode(span=condition.span),
                    IfConditionUnifyErrorFactory(tree),
                )
                return transformation_then + transformation_else + trans_condition

            case ForNode():
                """
                Set the expected loop element to be polymorphic, and the expected loop type to be
                the ListNode with that loop element type as its element type. Then, type both the
                loop, the new loop variable, and the loop body.
                Also ensure that the new loop variable was not previously defined.
                """
                # Get expected types for the id and loop, respectively
                loop_element_type = PolymorphicTypeNode.fresh()
                loop_type = ListNode(loop_element_type)

                # Type check the loop
                trans_loop = self.type_node(
                    tree.loop, var_context, fun_context, loop_type, error_factory
                )

                # If the variable already exists, throw an exception
                if tree.id.text in var_context:
                    RedefinitionOfLoopVariableError(self.program, tree)
                    return []

                # Set the id type, and place it in the variable context
                var_context[tree.id.text] = loop_element_type
                var_context = self.apply_trans_context(trans_loop, var_context)
                fun_context = self.apply_trans_context(trans_loop, fun_context)

                # Type check the id
                trans_id = self.type_node(
                    tree.id, var_context, fun_context, loop_element_type, error_factory
                )

                # Update the contexts again
                var_context = self.apply_trans_context(trans_id, var_context)
                fun_context = self.apply_trans_context(trans_id, fun_context)

                trans_body = []
                for expression in tree.body:
                    trans = self.type_node(
                        expression, var_context, fun_context, exp_type, error_factory
                    )
                    var_context = self.apply_trans_context(trans, var_context)
                    fun_context = self.apply_trans_context(trans, fun_context)
                    trans_body += trans

                # Delete the id again from the variable context
                del var_context[tree.id.text]
                return trans_body

            case WhileNode():
                """
                Recursively type the while body, and then the condition.
                """
                condition = tree.cond
                body = tree.body

                original_var_context = var_context.copy()
                original_fun_context = fun_context.copy()

                # Type the while body
                transformation_body = []
                for expression in body:
                    trans = self.type_node(
                        expression, var_context, fun_context, exp_type, error_factory
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

                # Type the condition
                trans_condition = self.type_node(
                    condition,
                    original_var_context,
                    original_fun_context,
                    BoolTypeNode(span=condition.span),
                    WhileConditionUnifyErrorFactory(tree),
                )

                return trans_condition

            case FunCallNode():
                """
                If the function that is being called was already defined, then ensure that the
                right number of arguments were given, and then type and unify the arguments and
                return values. We copy the function type as to not accidentally update it.

                If the function was not yet defined, then store this "state", i.e. the defined variables,
                functions, tree and exp_type in `self.fun_calls`. It can then be typed at the end of
                the function definition, or used to determine that a non-defined function is called.
                """

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
                                call_arg, var_context, fun_context, fresh, error_factory
                            )
                            call_arg_type = self.apply_trans(fresh, trans)
                            return_trans += trans

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

                    return return_trans

                else:
                    self.fun_calls[tree.func.text].append(
                        (tree, var_context.copy(), fun_context.copy(), exp_type)
                    )
                    return []

            case VariableNode():
                """
                A VariableNode may contain a field. If not, then we simply recursively type the variable.
                If it does, then we grab the existing variable, and iterate over the fields. We then
                apply typing based on the exact field that is used. For example, if a.fst is used, then we
                unify a with a Tuple of two polymorphic variables, and we set the left of the two
                polymorphic variables as the new type of a.fst. This method allows for chaining, e.g.
                a.fst.snd.
                """
                if not tree.field:
                    return self.type_node(
                        tree.id, var_context, fun_context, exp_type, error_factory
                    )

                if tree.id.text not in var_context:
                    VariableError(self.program, tree.id)
                    return []

                variable_type = var_context[tree.id.text]
                trans = []
                for field in tree.field.fields:
                    match field:
                        case Token(type=Type.FST) | Token(type=Type.SND):
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

                        case Token(type=Type.HD) | Token(type=Type.TL) | IndexNode():
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
                            if isinstance(field, IndexNode):
                                picked = element
                                trans += self.type_node(
                                    field.exp,
                                    var_context,
                                    fun_context,
                                    IntTypeNode(),
                                    IndexTypeError(field),
                                )
                            else:
                                picked = (
                                    element if field.type == Type.HD else var_exp_type
                                )
                            variable_type = self.apply_trans(picked, sub)

                        case _:
                            UnrecoverableError(
                                f"The field {field.type} is not supported."
                            )

                trans += self.unify(exp_type, variable_type, error_factory)
                return trans

            case ListAbbrNode():
                """
                First, we type the left expression. Then, we verify that the returned type
                is either an Int or a Char. Then, we type the right side, requiring it to be
                the same type as the left side. Lastly, we unify the expected type to a ListNode
                with child type as the element types.
                """
                sub_exp_type = PolymorphicTypeNode.fresh()
                trans = self.type_node(
                    tree.left,
                    var_context,
                    fun_context,
                    sub_exp_type,
                    ListAbbrError(tree.left, is_left=True),
                )
                var_context = self.apply_trans_context(trans, var_context)
                fun_context = self.apply_trans_context(trans, fun_context)
                sub_exp_type = self.apply_trans(sub_exp_type, trans)

                if not isinstance(sub_exp_type, (IntTypeNode, CharTypeNode)):
                    ListAbbrError(tree.left, is_left=True).build(
                        (IntTypeNode(), CharTypeNode()),
                        sub_exp_type,
                        self.program,
                        self.current_function,
                    )
                    sub_exp_type = IntTypeNode()

                trans += self.type_node(
                    tree.right,
                    var_context,
                    fun_context,
                    sub_exp_type,
                    ListAbbrError(tree.right, is_left=False),
                )

                trans += self.unify(exp_type, ListNode(sub_exp_type), error_factory)

                return trans

        UnrecoverableError(f"Node had no handler: {tree!r}")

    def apply_trans(
        self, node: Node, trans: List[Tuple[PolymorphicTypeNode, TypeNode]]
    ) -> Node:
        """Given a Node and transformations, apply the transformations on the Node.

        For example, if `node` contains a PolymorphicTypeNode as one of its descendents, whose instance
        corresponds exactly with an instance in one of the transformations, then that PolymorphicTypeNode
        will be transformed with the new TypeNode. E.g. PolymorphicTypeNode("a") can become IntTypeNode().

        Args:
            node (Node): The Node on which to apply the type transformations.
            trans (List[Tuple[PolymorphicTypeNode, TypeNode]]): A list of transformations to apply.

        Returns:
            Node: `node`, but with the transformations applied.
        """
        return self.sub_transformer.visit(node, trans)

    def apply_trans_context(
        self,
        trans: List[Tuple[PolymorphicTypeNode, TypeNode]],
        context: Dict[str, TypeNode],
    ) -> Dict[str, TypeNode]:
        """Apply the given transformations on the context values. Relies on `self.apply_trans`.

        Args:
            trans (List[Tuple[PolymorphicTypeNode, TypeNode]]): A list of transformations to apply.
            context (Dict[str, TypeNode]): The var_context or fun_context.

        Returns:
            Dict[str, TypeNode]: The updated context.
        """

        if trans:
            for var_name, var_type in context.items():
                context[var_name] = self.apply_trans(var_type, trans)

        return context

    def unify(
        self,
        type_one: TypeNode,
        type_two: TypeNode,
        error_factory: UnificationError,
        left_to_right: bool = False,
    ) -> List[Tuple[PolymorphicTypeNode, TypeNode]]:
        """Try to unify `type_one` with `type_two`.

        Args:
            type_one (TypeNode): The left type. This is generally the expected/desired type.
            type_two (TypeNode): The right type.
            error_factory (UnificationError): A factory with a `build` method that can be called to
                throw an exception, when the two types cannot unify.
            left_to_right (bool, optional): If set to True, then the return type becomes
                List[Tuple[PolymorphicTypeNode, TypeNode, bool]]. The last bool is True whenever
                we are now updating `type_one` to `type_two` and False otherwise, but only if both
                are Polymorphic. Defaults to False.

        Returns:
            List[Tuple[PolymorphicTypeNode, TypeNode]]: Our representation of a list of transformations,
                i.e. a list of tuples representing a mapping of a PolymorphicTypeNode to some other type.
        """

        # Case 1: The types are the same. No transformation needed for unification.
        if type_one == type_two:
            return []

        # Case 2: If left is very general, e.g. "a", and right is specific, e.g. "Int", then map "a" to "Int"
        # NOTE: If type_one in type_two, then we have an error (e.g. we want to go from a -> (a, b), which is recursive)
        # We can abuse this to get a more precise error, but I'm not sure whether that's helpful
        if isinstance(type_one, PolymorphicTypeNode) and type_one not in type_two:
            if left_to_right:
                return [(type_one, type_two, True)]
            return [(type_one, type_two)]

        # Case 3: If right is very general, e.g. "a", and left is specific, e.g. "Int", then map "a" to "Int"
        if isinstance(type_two, PolymorphicTypeNode) and type_two not in type_one:
            if left_to_right:
                return [(type_two, type_one, False)]
            return [(type_two, type_one)]

        # Case 4: If both types are lists, then recursively unify the types of the list.
        if isinstance(type_one, ListNode) and isinstance(type_two, ListNode):
            return self.unify(
                type_one.body, type_two.body, error_factory, left_to_right=left_to_right
            )

        # Case 5: If both types are tuples, then recursively unify first the left side, and then
        # the right side.
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

        # Case 6: If both types are functions, then first check if both sides have the same
        # number of arguments, and then try to unify all arguments, as well as the return type
        if isinstance(type_one, FunTypeNode) and isinstance(type_two, FunTypeNode):
            # Ensure the same number of arguments
            if len(type_one.types) != len(type_two.types):
                WrongNumberOfArgumentsDeclError(
                    self.program,
                    self.current_function,
                    len(type_two.types),
                    len(type_one.types),
                )
                return []

            # Try to unify all arguments
            transformations = []
            for i in range(len(type_one.types)):
                _type_one = type_one.types[i]
                _type_two = type_two.types[i]
                trans = self.unify(
                    _type_one, _type_two, error_factory, left_to_right=left_to_right
                )
                type_one = self.apply_trans(type_one, trans)
                type_two = self.apply_trans(type_two, trans)

                transformations += trans

            # Try to unify the return type
            trans = self.unify(
                type_one.ret_type,
                type_two.ret_type,
                error_factory,
                left_to_right=left_to_right,
            )
            type_one = self.apply_trans(type_one, trans)
            type_two = self.apply_trans(type_two, trans)
            transformations += trans
            return transformations

        # If no (correct) error_factory was provided, then just use a default one that simply
        # states that the two types cannot unify.
        if not isinstance(error_factory, UnificationError):
            error_factory = DefaultUnifyErrorFactory()

        # Use the error factory to produce a detailed and relevant error.
        error_factory.build(
            type_one=type_one,
            type_two=type_two,
            program=self.program,
            function=self.current_function,
        )
        return []


class SubstitutionTransformer(NodeTransformer):
    """Apply a transformation on a tree using a visitor pattern"""

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
