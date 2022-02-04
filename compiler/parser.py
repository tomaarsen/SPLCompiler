from typing import List

from pprint import pprint

from compiler.token import Token
from compiler.tree import Tree, BracketTree
from compiler.type import Type


class Parser:
    def __init__(self) -> None:
        pass

    def parse(self, tokens: List[Token]) -> Tree:
        pass
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
                
                case Type.LCB | Type.LRB | Type.LSB: # {([
                    # bracket_queue[token.type].put(token)
                    bt = BracketTree(token, None)
                    queue.append(bt)

                case Type.RCB | Type.RRB | Type.RSB: # })]
                    # Verify that the last opened bracket is the same type of bracket
                    # that we now intend to close
                    if len(queue) == 1:
                        # TODO: Raise: Closing bracket without open bracket
                        pass
                    if queue[-1].open.type == right_to_left[token.type]:
                        # If all is well, grab the last opened bracket from the queue,
                        # add this token as a closing tag, and add it the BracketTree
                        # as a child to the Tree higher in the queue
                        bt = queue.pop()
                        bt.close = token
                        queue[-1].add_child(bt)
                    else:
                        # TODO: Raise mismatch error: Closing a different type of bracket that was opened
                        pass

                case _:
                    queue[-1].add_child(token)

        # TODO: If bracket_queue.values() queues not empty, then there's an opening bracket
        # without a closing one
        pprint(root)
        return root
