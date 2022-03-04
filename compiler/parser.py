from pprint import pprint
from typing import List

from pyparsing import ParseBaseException

from compiler.grammar import ALLOW_EMPTY, Grammar
from compiler.token import Token
from compiler.tree import Tree
from compiler.type import Type
from compiler.util import Span, span_between_inclusive

from compiler.error import (  # isort:skip
    ClosedWrongBracketError,
    ErrorRaiser,
    OpenedWrongBracketError,
    ParseError,
    ParserException,
    UnclosedBracketError,
    UnopenedBracketError,
)


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
        tokens = self.match_parentheses(tokens)
        # At this stage we should no longer have bracket errors
        ErrorRaiser.raise_all(ParserException)

        grammar = Grammar(tokens)
        tree = grammar.parse()
        # If the tokens wered parsed in full, just return
        if grammar.done:
            return tree

        # Otherwise, we look at the most likely errors
        # Remove everything that didn't reach the end, and then take the last potential error
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
            error_tokens_span = span_between_inclusive(
                error_tokens[0].span, error_tokens[-1].span
            )
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
