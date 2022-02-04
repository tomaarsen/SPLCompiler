from typing import List

from pprint import pprint

from compiler.token import Token
from compiler.tree import Tree, BracketTree
from compiler.type import Type
from compiler.errors import ErrorRaiser, BracketMissMatchError


class Parser:
    def __init__(self, program: str) -> None:
        self.og_program = program

    def parse(self, tokens: List[Token]) -> Tree:
        """
        Conceptual algorithm (bottom-up):
        Step 1: Group tokens that must co-occur, that define scopes
                With other words, '(' and ')', '{' and '}', '[' and ']'.
                This leads to an "unfinished" AST.
        (optional)
        Step 1.1: Verify contents of these groups: Between '[' and ']' may only
                be nothing or `Type`.
        """
        # TODO: Store column alongside the current line_no in Token

        right_to_left = {
            Type.RCB: Type.LCB,
            Type.RRB: Type.LRB,
            Type.RSB: Type.LSB,
        }

        root = Tree()
        queue = [root]
        for token in tokens:
            match token.type:

                case Type.LCB | Type.LRB | Type.LSB:  # {([
                    # bracket_queue[token.type].put(token)
                    bt = BracketTree(token, None)
                    queue.append(bt)

                case Type.RCB | Type.RRB | Type.RSB:  # })]
                    # Verify that the last opened bracket is the same type of bracket
                    # that we now intend to close
                    if len(queue) == 1:
                        BracketMissMatchError(
                            self.og_program, token.line_no, token.span, token.type
                        )
                        # TODO: Raise: Closing bracket without open bracket

                    # TODO: @Tom do we mean "elif" instead of "if"?
                    # Seems to fix: *** AttributeError: 'Tree' object has no attribute 'open'
                    elif queue[-1].open.type == right_to_left[token.type]:
                        # If all is well, grab the last opened bracket from the queue,
                        # add this token as a closing tag, and add it the BracketTree
                        # as a child to the Tree higher in the queue
                        bt = queue.pop()
                        bt.close = token
                        queue[-1].add_child(bt)
                    else:
                        BracketMissMatchError(
                            self.og_program, token.line_no, token.span, token.type
                        )
                        # TODO: Raise mismatch error: Closing a different type of bracket that was opened

                case _:
                    queue[-1].add_child(token)

        # TODO: If queue queues not empty, then there's an opening bracket that we did not close
        if len(queue) > 1:
            for bt in queue[1:]:
                open_bracket = bt.open
                BracketMissMatchError(
                    self.og_program,
                    open_bracket.line_no,
                    open_bracket.span,
                    open_bracket.type,
                )
                # throw error here
        # without a closing one
        pprint(root)
        # Test:
        # TODO: Potentially make errors more specific, depended on where in the code the error is raised?
        ErrorRaiser.raise_all()

        return root
