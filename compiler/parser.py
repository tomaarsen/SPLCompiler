from pprint import pprint
from typing import Callable, List

from compiler.error import BracketMismatchError, ErrorRaiser
from compiler.token import Token
from compiler.tree import Tree
from compiler.type import Type


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
        # TODO: Surely we can make these Bracket mismatch errors more specific?
        # E.g. "No corresponding closing bracket for ... on line ...",
        #      "No corresponding opening bracket for ... on line ..."
        # TODO: Update grammar to add space after "var"

        tokens = self.match_parentheses(tokens)
        # TODO: Potentially make errors more specific, depended on where in the code the error is raised?
        # At this stage we should no longer have bracket errors
        ErrorRaiser.raise_all()
        # pprint(tokens)

        pm = NewParserMatcher(tokens)
        tree = pm.parse()
        # tree.clean()
        # pprint(tree)
        print(pm.i, len(tokens))

        # TODO: Error if pm.i != len(tokens)

        return tree

    def match_parentheses(self, tokens: List[Token]) -> None:
        right_to_left = {
            Type.RCB: Type.LCB,
            Type.RRB: Type.LRB,
            Type.RSB: Type.LSB,
        }

        queue = []
        for i, token in enumerate(tokens):
            match token.type:
                case Type.LCB | Type.LRB | Type.LSB:  # {([
                    queue.append(token)

                case Type.RCB | Type.RRB | Type.RSB:  # })]
                    # Verify that the last opened bracket is the same type of bracket
                    # that we now intend to close
                    if len(queue) == 0:
                        # Raise mismatch error: Closing bracket without open bracket
                        BracketMismatchError(
                            self.og_program, token.line_no, token.span, token.type
                        )
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
            BracketMismatchError(
                self.og_program,
                token.line_no,
                token.span,
                token.type,
            )

        return tokens
