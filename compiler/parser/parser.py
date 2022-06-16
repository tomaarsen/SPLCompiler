import os
from typing import List

from compiler.error.communicator import Communicator
from compiler.parser.analyze import AnalyzeTransformer
from compiler.parser.factory import DefaultFactory
from compiler.token import Token
from compiler.type import Type
from compiler.util import Span
from parser_generator.grammar import Grammar

from compiler.error.warning import (  # isort:skip
    NoMainFunctionWarning,
)

from compiler.tree.tree import (  # isort:skip
    FunDeclNode,
    PolymorphicTypeNode,
    SPLNode,
)
from compiler.parser.factory import (  # isort:skip
    BasicFactory,
    BasicTypeFactory,
    ColonFactory,
    CommaFactory,
    DefaultFactory,
    ExpFactory,
    ExpPrimeFactory,
    FieldFactory,
    ForFactory,
    FunCallFactory,
    FunDeclFactory,
    FunTypeFactory,
    IndexFactory,
    ListAbbrFactory,
    RetTypeFactory,
    IfElseFactory,
    ReturnFactory,
    SPLFactory,
    StmtAssFactory,
    StmtFactory,
    TypeFactory,
    UnaryFactory,
    VarDeclFactory,
    WhileFactory,
)
from compiler.error.parser_error import (  # isort:skip
    ClosedWrongBracketError,
    OpenedWrongBracketError,
    ParseError,
    ParserException,
    UnclosedBracketError,
    UnopenedBracketError,
)


# Allow a non-terminal of this type to be raised as
# an exception, but only if the production was at least partially matched
ALLOW_ERROR_NONEMPTY = (
    "Return",
    "IfElse",
    "While",
    "For",
    "StmtAss",
    "ListAbbr",
)

# Allow a non-terminal of this type to be raised as
# an exception, even if none of the production was matched
ALLOW_ERROR_EMPTY = (
    "VarDecl",
    "FunDecl",
    "RetType",
    "FunType",
    "FArgs",
    "Stmt",
    "ActArgs",
)


class Parser:
    def __init__(self, program: str) -> None:
        self.og_program = program

        # Reset the Polymorphic IDs as we are now dealing with a new parser
        PolymorphicTypeNode.reset()

    def parse(self, tokens: List[Token]) -> SPLNode:
        """Given a list of Tokens from the scanner, apply the grammar from `grammar.txt`
        to produce an Abstract Syntax Tree.

        Args:
            tokens (List[Token]): A list of tokens, produced by `Scanner(program).scan()`

        Returns:
            SPLNode: The root of the AST.
        """
        tokens = self.match_parentheses(tokens)
        # At this stage we should no longer have bracket errors
        Communicator.communicate(ParserException)

        # Set up grammar using parser generator
        terminal_mapping = {
            "(": Type.LRB,
            ")": Type.RRB,
            "{": Type.LCB,
            "}": Type.RCB,
            "[": Type.LSB,
            "]": Type.RSB,
            ";": Type.SEMICOLON,
            "::": Type.DOUBLE_COLON,
            "->": Type.ARROW,
            ",": Type.COMMA,
            "..": Type.DDOT,
            "+": Type.PLUS,
            "-": Type.MINUS,
            "*": Type.STAR,
            "/": Type.SLASH,
            "^": Type.POWER,
            "%": Type.PERCENT,
            "==": Type.DEQUALS,
            "<=": Type.LEQ,
            ">=": Type.GEQ,
            "<": Type.LT,
            ">": Type.GT,
            "!=": Type.NEQ,
            "=": Type.EQ,
            "&&": Type.AND,
            "||": Type.OR,
            ":": Type.COLON,
            "!": Type.NOT,
            ".hd": Type.HD,
            ".tl": Type.TL,
            ".fst": Type.FST,
            ".snd": Type.SND,
            "if": Type.IF,
            "else": Type.ELSE,
            "while": Type.WHILE,
            "for": Type.FOR,
            "in": Type.IN,
            "return": Type.RETURN,
            "Void": Type.VOID,
            "Int": Type.INT,
            "Bool": Type.BOOL,
            "Char": Type.CHAR,
            "False": Type.FALSE,
            "True": Type.TRUE,
            "var": Type.VAR,
            "id": Type.ID,
            "int": Type.DIGIT,
            "char": Type.CHARACTER,
            "continue": Type.CONTINUE,
            "string": Type.STRING,
            "break": Type.BREAK,
            " ": Type.SPACE,
        }
        # Get mappings of non-terminals to functions to generate nodes
        non_terminal_factory_mapping = {
            "SPL": SPLFactory().build,
            "VarDecl": VarDeclFactory().build,
            "FunDecl": FunDeclFactory().build,
            "RetType": RetTypeFactory().build,
            "FunType": FunTypeFactory().build,
            "Type": TypeFactory().build,
            "BasicType": BasicTypeFactory().build,
            "FArgs": CommaFactory().build,
            "Stmt": StmtFactory().build,
            "StmtAss": StmtAssFactory().build,
            "IfElse": IfElseFactory().build,
            "While": WhileFactory().build,
            "For": ForFactory().build,
            "Return": ReturnFactory().build,
            "Exp": ExpFactory().build,
            "Or'": ExpPrimeFactory().build,
            "And": ExpFactory().build,
            "And'": ExpPrimeFactory().build,
            "Eq": ExpFactory().build,
            "Eq'": ExpPrimeFactory().build,
            "Leq": ExpFactory().build,
            "Leq'": ExpPrimeFactory().build,
            "Sum": ExpFactory().build,
            "Sum'": ExpPrimeFactory().build,
            "Fact": ExpFactory().build,
            "Fact'": ExpPrimeFactory().build,
            "Colon": ColonFactory().build,
            "Unary": UnaryFactory().build,
            "Basic": BasicFactory().build,
            "Field": FieldFactory().build,
            "Index": IndexFactory().build,
            "ListAbbr": ListAbbrFactory().build,
            "FunCall": FunCallFactory().build,
            "ActArgs": CommaFactory().build,
        }
        default_factory = DefaultFactory().build
        error_non_terminals = (*ALLOW_ERROR_NONEMPTY, *ALLOW_ERROR_EMPTY)
        grammar_file = os.path.join(os.path.dirname(__file__), "grammar.txt")
        grammar = Grammar(
            "",
            grammar_file,
            terminal_mapping,
            start_non_terminal="SPL",
            non_terminal_factory_mapping=non_terminal_factory_mapping,
            non_terminal_default_factory=default_factory,
            error_non_terminals=error_non_terminals,
        )
        output = grammar.parse(tokens)
        tree = output["tree"]
        done = output["done"]
        potential_errors = output["potential_errors"]
        # If the tokens were not parsed in full, look at the most likely errors
        # Remove everything that didn't reach the end, and then take the last potential error
        if not done:
            max_end = max(error.end for error in potential_errors)
            potential_errors = [
                error
                for error in potential_errors
                if error.end == max_end
                and (error.end > error.start or error.nt in ALLOW_ERROR_EMPTY)
            ]
            # Extract the ParseErrorSpan instance
            error = potential_errors[-1]
            # The tokens that were matched before the error occurred
            error_tokens = tokens[error.start : error.end]
            # The partial production that failed to match
            expected = error.remaining
            # What we got instead of being able to match the partial production
            got = tokens[error.end] if error.end < len(tokens) else None

            # Track whether the received token and the expected token are on the same line
            sameline = False
            # Get a span of the error tokens, if possible
            if error_tokens:
                error_tokens_span = error_tokens[0].span & error_tokens[-1].span
                if got and got.span.start_ln == error_tokens_span.end_ln:
                    sameline = True
            elif got:
                error_tokens_span = Span(
                    got.span.start_ln, (got.span.start_col, got.span.start_col)
                )
            else:
                error_tokens_span = Span(
                    tokens[-1].span.start_ln,
                    (tokens[-1].span.start_col, tokens[-1].span.start_col),
                )

            ParseError(
                self.og_program,
                error_tokens_span,
                error.nt,
                expected,
                got if sameline else None,
            )

            Communicator.communicate(ParserException)

            return tree

        # Prune tree to remove statements after `return`, and throw warning if there are any
        transformer = AnalyzeTransformer(self.og_program)
        transformer.visit(tree)

        # Ensure that there is a main function, else give a warning
        self.check_main_function(tree.body)

        Communicator.communicate(ParserException)

        return tree

    def check_main_function(self, body: List[FunDeclNode]) -> None:
        """Verify that at least 1 main function is declared.

        NoMainFunctionWarning in initialized if a function declaration named 'main' cannot be found.

        Args:
            body (List[FunDeclNode]): A list containing all function declarations.
        """

        for decl in body:
            if decl.id.text == "main":
                return
        # At this point we have not found a main function
        NoMainFunctionWarning(self.og_program)

    def match_parentheses(self, tokens: List[Token]) -> None:
        """Perform an analysis to throw detailed bracket exceptions.

        Including UnopenedBracketError, OpenedWrongBracketError, ClosedWrongBracketError,
        and UnclosedBracketError.

        Args:
            tokens (List[Token]): The scanned tokens after the scanner.
        """
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
                        queue.pop()

        # If queue is not empty, then there's an opening bracket that we did not close
        for token in queue:
            UnclosedBracketError(
                self.og_program,
                token.span,
                token.type,
            )

        return tokens
