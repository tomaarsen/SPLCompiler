from dataclasses import dataclass
from typing import List

from compiler.error.error import ErrorRaiser
from compiler.error.typer_error import GlobalFunctionCallError
from compiler.grammar import ALLOW_EMPTY, Grammar
from compiler.grammar_parser import NT
from compiler.token import Token
from compiler.tree.visitor import Boolean, NodeTransformer, NodeVisitor
from compiler.type import Type
from compiler.util import Span

from compiler.tree.tree import (  # isort:skip
    FunCallNode,
    FunDeclNode,
    IfElseNode,
    Node,
    PolymorphicTypeNode,
    ReturnNode,
    SPLNode,
    StmtNode,
    VarDeclNode,
    WhileNode,
)

from compiler.error.parser_error import (  # isort:skip
    ClosedWrongBracketError,
    OpenedWrongBracketError,
    ParseError,
    ParserException,
    UnclosedBracketError,
    UnopenedBracketError,
)


class Parser:
    def __init__(self, program: str) -> None:
        self.og_program = program

        # Reset the Polymorphic IDs as we are now dealing with a new parser
        PolymorphicTypeNode.reset()

    def parse(self, tokens: List[Token]) -> SPLNode:
        """
        Conceptual algorithm (bottom-up):
        Step 1: Group tokens that must co-occur, that define scopes
                With other words, '(' and ')', '{' and '}', '[' and ']'.
                This leads to an "unfinished" AST.
        (optional)
        Step 1.1: Verify contents of these groups: Between '[' and ']' may only
                be nothing or `Type`.
        """
        tokens = self.match_parentheses(tokens)
        # At this stage we should no longer have bracket errors
        ErrorRaiser.raise_all(ParserException)

        grammar = Grammar(tokens)
        tree = grammar.parse(nt=NT.SPL)
        # If the tokens were not parsed in full, look at the most likely errors
        # Remove everything that didn't reach the end, and then take the last potential error
        if not grammar.done:
            max_end = max(error.end for error in grammar.potential_errors)
            potential_errors = [
                error
                for error in grammar.potential_errors
                if error.end == max_end
                and (error.end > error.start or error.nt in ALLOW_EMPTY)
            ]
            # Extract the ParseErrorSpan instance
            error = potential_errors[-1]
            # The tokens that were matched before the error occurred
            error_tokens = tokens[error.start : error.end]
            # The partial production that failed to match
            expected = error.remaining
            # What we got instead of being able to match the partial production
            got = tokens[error.end]

            # Track whether the received token and the expected token are on the same line
            sameline = False
            # Get a span of the error tokens, if possible
            if error_tokens:
                error_tokens_span = error_tokens[0].span and error_tokens[-1].span
                if got.span.start_ln == error_tokens_span.end_ln:
                    sameline = True
            else:
                error_tokens_span = Span(
                    got.span.start_ln, (got.span.start_col, got.span.start_col)
                )

            ParseError(
                self.og_program,
                error_tokens_span,
                error.nt,
                expected,
                got if sameline else None,
            )

            ErrorRaiser.raise_all(ParserException)

            return tree

        # If there were no issues, then we convert this parse tree into a more abstract variant
        # TODO: Prune tree to remove statements after `return`, and throw warning if there are any
        transformer = ReturnTransformer()
        transformer.visit(tree)

        # Ensure that global variable declarations do not call functions
        transformer = GlobalVisitor(self.og_program)
        transformer.visit(tree)

        return tree

    def match_parentheses(self, tokens: List[Token]) -> None:
        right_to_left = {
            Type.RCB: Type.LCB,
            Type.RRB: Type.LRB,
            Type.RSB: Type.LSB,
        }

        queue = []
        for token in tokens:
            match token.type:
                case Type.LCB | Type.LRB | Type.LSB:  # {([
                    queue.append(token)

                case Type.RCB | Type.RRB | Type.RSB:  # })]
                    # Verify that the last opened bracket is the same type of bracket
                    # that we now intend to close
                    if len(queue) == 0:
                        # Raise mismatch error: Closing bracket without open bracket
                        UnopenedBracketError(self.og_program, token.span, token.type)
                        continue

                    if queue[-1].type != right_to_left[token.type]:
                        # Raise mismatch error: Closing a different type of bracket that was opened

                        # FIXED BUG: In the situation of "{(}", this detects the mismatch between ( and },
                        # but raises the issue for } (wrong closing bracket).
                        # Then, { and ( *both* remain unclosed in the queue, and an error is thrown
                        # for them later. So, we get 3 errors instead of just one.
                        # But, the current behaviour is correct for "{)}" (additional closing).
                        # It's only "broken" for additional opening brackets.
                        if (
                            len(queue) > 1
                            and queue[-2].type == right_to_left[token.type]
                        ):
                            # If the opening bracket before the last one *is* correct,
                            # then we assume that the last open bracket was a mistake.
                            # Note: This only works 1 deep, the issue persists with e.g.
                            # "{((}".
                            wrong_open = queue.pop()
                            OpenedWrongBracketError(
                                self.og_program,
                                wrong_open.span,
                                wrong_open.type,
                            )
                        else:
                            # Otherwise, report the closing bracket as being false
                            ClosedWrongBracketError(
                                self.og_program,
                                token.span,
                                token.type,
                            )

                    if queue[-1].type == right_to_left[token.type]:
                        # If all is well, grab the last opened bracket from the queue,
                        # add this token as a closing tag, and add it the BracketTree
                        # as a child to the Tree higher in the queue
                        open_token = queue.pop()
                        # Replace `token` with one that knows its Open
                        # Replace `open_token` with one that knows its Close
                        # open_bracket_token = BracketToken.from_token(open_token)
                        # close_bracket_token = BracketToken.from_token(token)

                        # close_bracket_token.open = open_bracket_token
                        # open_bracket_token.close = close_bracket_token

                        # tokens[i] = close_bracket_token
                        # tokens[tokens.index(open_token)] = open_bracket_token

        # If queue is not empty, then there's an opening bracket that we did not close
        for token in queue:
            UnclosedBracketError(
                self.og_program,
                token.span,
                token.type,
            )

        return tokens


class ReturnTransformer(NodeTransformer):
    """
    Perform two steps:
    1. Delete unreachable dead code after a return statement.
    2. Insert an ReturnNode after every function that does not end every branch with a return.
    """

    def traverse_statements(self, stmts: List[StmtNode], reachable: Boolean) -> None:
        for i, stmt in enumerate(stmts, start=1):
            self.visit_children(stmt, reachable=reachable)
            if not reachable:
                if stmts[i:]:
                    # TODO: This is where we delete unreachable code, add a warning.
                    # print(f"Deleting dead code: {stmts[i:]}")
                    del stmts[i:]
                break

    def visit_FunDeclNode(self, node: FunDeclNode, **kwargs) -> FunDeclNode:
        reachable = Boolean(True)

        self.traverse_statements(node.stmt, reachable)

        # If the end of the function body is reachable, then we add an empty (void) return
        if reachable:
            # print(f"Adding Return at the end of {node.id.text!r}")
            col = max(node.span.end_col - 1, 0)
            span = Span(node.span.end_ln, (col, col))
            node.stmt.append(StmtNode(ReturnNode(None, span=span), span=span))

        return node

    def visit_IfElseNode(
        self, node: IfElseNode, reachable: Boolean, **kwargs
    ) -> StmtNode:
        if reachable:
            # Traverse the "then" branch to see if that side is reachable
            self.traverse_statements(node.body, reachable)
            left_reachable = reachable.boolean

            # Reset reachability to true, as we know the if-else can be reached,
            # so the else can be reached too.
            reachable.set(True)
            self.traverse_statements(node.else_body, reachable)
            right_reachable = reachable.boolean

            # Only if both sides end with a return (and thus have reachable=False at the end),
            # then we get reachable=False for this if-else
            reachable.set(left_reachable or right_reachable)
        return node

    def visit_WhileNode(
        self, node: WhileNode, reachable: Boolean, **kwargs
    ) -> WhileNode:
        # Code after a while statement is always assumed to be reachable,
        # as we assume that the condition can be False from the get-go.
        # So, we only traverse statements to potentially delete dead code after a return statement.
        self.traverse_statements(node.body, reachable)
        reachable.set(True)
        return node

    def visit_ReturnNode(
        self, node: ReturnNode, reachable: Boolean, **kwargs
    ) -> ReturnNode:
        # Code directly after this Return statement is *not* reachable
        # TODO: This line might not be needed
        self.visit_children(node, reachable=reachable)

        reachable.set(False)
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
