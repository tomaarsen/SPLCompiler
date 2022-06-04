from ast import NodeVisitor
from dataclasses import dataclass
from typing import List

from compiler.token import Token
from compiler.tree.visitor import Boolean, NodeTransformer
from compiler.type import Type
from compiler.util import Span

from compiler.error.typer_error import (  # isort:skip
    GlobalFunctionCallError,
    IllegalContinueBreakError,
)
from compiler.error.warning import (  # isort:skip
    DeadCodeRemovalWarning,
    InsertedReturnWarning,
    MainCallWarning,
)

from compiler.tree.tree import (  # isort:skip
    ForNode,
    FunCallNode,
    FunDeclNode,
    IfElseNode,
    ListNode,
    Op2Node,
    ReturnNode,
    StmtNode,
    WhileNode,
)


@dataclass
class AnalyzeTransformer(NodeTransformer):
    program: str
    """
    Perform two steps:
    1. Delete unreachable dead code after a return statement.
    2. Insert an ReturnNode after every function that does not end every branch with a return.
    3. Give a warning if the main function is called.

    Additionally, verify that all uses of `continue` and `break` occur inside of a for or while loop.

    Lastly, expand Strings into Op2Nodes of characters being added together
    """

    def traverse_statements(
        self, stmts: List[StmtNode], reachable: Boolean, **kwargs
    ) -> None:
        for i, stmt in enumerate(stmts, start=1):
            self.visit_children(stmt, reachable=reachable, **kwargs)
            if not reachable:
                if stmts[i:]:
                    DeadCodeRemovalWarning(self.program, stmts[i - 1], stmts[i:])
                    del stmts[i:]
                break

    def visit_FunCallNode(self, node: FunCallNode, **kwargs) -> FunCallNode:
        if isinstance(node.func, Token) and node.func.text == "main":
            MainCallWarning(self.program, node)
        return node

    def visit_FunDeclNode(self, node: FunDeclNode, **kwargs) -> FunDeclNode:
        reachable = Boolean(True)

        for var_decl in node.var_decl:
            self.visit_children(var_decl, None, **kwargs)

        self.traverse_statements(node.stmt, reachable, **kwargs)

        # If the end of the function body is reachable, then we add an empty (void) return
        if reachable:
            # print(f"Adding Return at the end of {node.id.text!r}")
            col = max(node.span.end_col - 1, 0)
            span = Span(node.span.end_ln, (col, col))
            node.stmt.append(StmtNode(ReturnNode(None, span=span), span=span))
            InsertedReturnWarning(self.program, node)

        # Traverse to the other children too, but not for reachability analysis
        self.visit(node.id, reachable, **kwargs)
        if node.args:
            self.visit(node.args, reachable, **kwargs)
        if node.type:
            self.visit(node.type, reachable, **kwargs)

        return node

    def visit_IfElseNode(
        self, node: IfElseNode, reachable: Boolean, **kwargs
    ) -> StmtNode:
        # Traverse to condition too, but not for reachability analysis
        self.visit(node.cond, reachable, **kwargs)
        if reachable:
            # Traverse the "then" branch to see if that side is reachable
            self.traverse_statements(node.body, reachable, **kwargs)
            left_reachable = reachable.var

            # Reset reachability to true, as we know the if-else can be reached,
            # so the else can be reached too.
            reachable.set(True)
            self.traverse_statements(node.else_body, reachable, **kwargs)
            right_reachable = reachable.var

            # Only if both sides end with a return (and thus have reachable=False at the end),
            # then we get reachable=False for this if-else
            reachable.set(left_reachable or right_reachable)
        return node

    def visit_ForNode(self, node: ForNode, reachable: Boolean, **kwargs) -> ForNode:
        # Code after a for loop is always assumed to be reachable,
        # as we assume that the loop can be empty from the get-go.
        # So, we only traverse statements to potentially delete dead code after a return statement.
        kwargs["in_loop"] = True
        self.visit(node.id, reachable, **kwargs)
        self.visit(node.loop, reachable, **kwargs)
        self.traverse_statements(node.body, reachable, **kwargs)
        reachable.set(True)
        return node

    def visit_WhileNode(
        self, node: WhileNode, reachable: Boolean, **kwargs
    ) -> WhileNode:
        # Code after a while statement is always assumed to be reachable,
        # as we assume that the condition can be False from the get-go.
        # So, we only traverse statements to potentially delete dead code after a return statement.
        kwargs["in_loop"] = True
        self.visit(
            node.cond, reachable, **kwargs
        )  # Traverse to condition too, but not for reachability analysis
        self.traverse_statements(node.body, reachable, **kwargs)
        reachable.set(True)
        return node

    def visit_ReturnNode(
        self, node: ReturnNode, reachable: Boolean, **kwargs
    ) -> ReturnNode:
        # Code directly after this Return statement is *not* reachable
        # TODO: This line might not be needed
        self.visit_children(node, reachable=reachable, **kwargs)

        reachable.set(False)
        return node

    def visit_Token(
        self, node: Token, reachable: Boolean = None, in_loop=False, **kwargs
    ) -> Token:
        if node.type in (Type.CONTINUE, Type.BREAK) and not in_loop:
            IllegalContinueBreakError(self.program, node)
        if node.type == Type.STRING:
            # Strip off " at the start and end
            string = node.text[1:-1]
            # Remove duplicate escaping, i.e. '\\n' -> '\n'
            string = string.encode().decode("unicode_escape")
            right = ListNode(None, span=node.span)
            for char in string[::-1]:
                left = Token(f"'{char}'", Type.CHARACTER, span=node.span)
                right = Op2Node(left, Token(":", Type.COLON, span=node.span), right)
            return right
        return node


@dataclass
class GlobalVisitor(NodeVisitor):
    program: str
    """
    Perform one step: Ensure that globals are constants
    1. For all variable declarations that are made *outside* of functions,
       throw an error if that global calls a function.

    NOTE: Globals are only defined on lines that follow *after* the declaration
    """

    def visit_FunCallNode(self, node: FunCallNode, *args, **kwargs):
        # Every SPL program is a list of function and global variable declarations.
        # If we disallow visiting into functions, then every occurrence of a function
        # call will be in the declaration of a global variable - which we want to avoid:
        GlobalFunctionCallError(self.program, node)

    def visit_FunDeclNode(self, node: FunDeclNode, *args, **kwargs):
        # Don't visit deeper into functions
        return
