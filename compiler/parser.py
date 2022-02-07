from typing import List

from pprint import pprint

from compiler.token import Token
from compiler.tree import Tree, BracketTree
from compiler.type import Type
from compiler.error import ErrorRaiser, BracketMismatchError


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
                    bt = BracketTree(token, None)
                    queue.append(bt)

                case Type.RCB | Type.RRB | Type.RSB:  # })]
                    # Verify that the last opened bracket is the same type of bracket
                    # that we now intend to close
                    if len(queue) == 1:
                        # Raise mismatch error: Closing bracket without open bracket
                        BracketMismatchError(
                            self.og_program, token.line_no, token.span, token.type
                        )
                        continue

                    if queue[-1].open.type != right_to_left[token.type]:
                        # Raise mismatch error: Closing a different type of bracket that was opened

                        # FIXED BUG: In the situation of "{(}", this detects the mismatch between ( and },
                        # but raises the issue for } (wrong closing bracket).
                        # Then, { and ( *both* remain unclosed in the queue, and an error is thrown
                        # for them later. So, we get 3 errors instead of just one.
                        # But, the current behaviour is correct for "{)}" (additional closing).
                        # It's only "broken" for additional opening brackets.
                        if len(queue) > 2 and queue[-2].open.type == right_to_left[token.type]:
                            # If the opening bracket before the last one *is* correct,
                            # then we assume that the last open bracket was a mistake.
                            # Note: This only works 1 deep, the issue persists with e.g.
                            # "{((}".
                            wrong_open = queue.pop().open
                            BracketMismatchError(
                                self.og_program,
                                wrong_open.line_no,
                                wrong_open.span,
                                wrong_open.type,
                            )
                        else:
                            # Otherwise, report the closing bracket as being false
                            BracketMismatchError(
                                self.og_program, token.line_no, token.span, token.type
                            )

                    if queue[-1].open.type == right_to_left[token.type]:
                        # If all is well, grab the last opened bracket from the queue,
                        # add this token as a closing tag, and add it the BracketTree
                        # as a child to the Tree higher in the queue
                        bt = queue.pop()
                        bt.close = token
                        queue[-1].add_child(bt)

                case _:
                    queue[-1].add_child(token)

        # If queue is not empty, then there's an opening bracket that we did not close
        for bt in queue[1:]:
            open_bracket = bt.open
            BracketMismatchError(
                self.og_program,
                open_bracket.line_no,
                open_bracket.span,
                open_bracket.type,
            )

        # pprint(root)

        # TODO: Potentially make errors more specific, depended on where in the code the error is raised?
        ErrorRaiser.raise_all()

        return root
