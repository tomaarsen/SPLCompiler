from typing import Callable, List

from pprint import pprint

from compiler.token import BracketToken, Token
from compiler.tree import (
    ActArgsTree,
    AssignmentStmtTree,
    FArgsTree,
    FTypesTree,
    FieldTree,
    FunCallStmtTree,
    FunCallTree,
    FunDeclTree,
    FunTypeTree,
    IfElseStmtTree,
    IfStmtTree,
    IntTree,
    RetTypeTree,
    ReturnStmtTree,
    SPLTree,
    TempExpTree,
    TokenTree,
    Tree,
    TypeSingleTree,
    TypeTupleTree,
    VarDeclTree,
    WhileStmtTree,
)
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
        # TODO: Surely we can make these Bracket mismatch errors more specific?
        # E.g. "No corresponding closing bracket for ... on line ...",
        #      "No corresponding opening bracket for ... on line ..."
        # TODO: Update grammar to add space after "var"

        tokens = self.match_parentheses(tokens)
        # TODO: Potentially make errors more specific, depended on where in the code the error is raised?
        # At this stage we should no longer have bracket errors
        ErrorRaiser.raise_all()
        # pprint(tokens)

        pm = ParserMatcher(tokens)
        tree = pm.match_SPL()
        pprint(tree)
        print(pm.i, len(tokens))
        print(pm.suggestions)
        # breakpoint()

        return

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
                        open_bracket_token = BracketToken.from_token(open_token)
                        close_bracket_token = BracketToken.from_token(token)

                        close_bracket_token.open = open_bracket_token
                        open_bracket_token.close = close_bracket_token

                        tokens[i] = close_bracket_token
                        tokens[tokens.index(open_token)] = open_bracket_token

        # If queue is not empty, then there's an opening bracket that we did not close
        for token in queue:
            BracketMismatchError(
                self.og_program,
                token.line_no,
                token.span,
                token.type,
            )

        return tokens

    def parenthesize_expression(self, tokens: List[Token]) -> List[Token]:
        """Use Knuth's Operator Precedence alternative solution"""
        # TODO: && and ||
        # https://en.wikipedia.org/wiki/Order_of_operations#Programming_languages
        # TODO: Make helper so we don't have to type `Token("(", Type.LRB)`
        resolved_tokens = [
            Token("(", Type.LRB),
            Token("(", Type.LRB),
            Token("(", Type.LRB),
            Token("(", Type.LRB),
        ]
        for i, token in enumerate(tokens):
            match token.type:
                case Type.LRB:
                    resolved_tokens += [
                        token,
                        Token("(", Type.LRB),
                        Token("(", Type.LRB),
                        Token("(", Type.LRB),
                    ]
                case Type.RRB:
                    resolved_tokens += [
                        Token(")", Type.RRB),
                        Token(")", Type.RRB),
                        Token(")", Type.RRB),
                        token,
                    ]
                case Type.POWER:
                    resolved_tokens += [
                        Token(")", Type.RRB),
                        token,
                        Token("(", Type.LRB),
                    ]
                case Type.STAR | Type.SLASH | Type.PERCENT:
                    resolved_tokens += [
                        Token(")", Type.RRB),
                        Token(")", Type.RRB),
                        token,
                        Token("(", Type.LRB),
                        Token("(", Type.LRB),
                    ]
                case Type.PLUS | Type.MINUS:
                    # TODO: Figure out if i == 0 helps or hurts
                    if i == 0 or last_type in (
                        Type.LRB,
                        Type.POWER,
                        Type.STAR,
                        Type.SLASH,
                        Type.PLUS,
                        Type.MINUS,
                    ):
                        resolved_tokens.append(token)
                    else:
                        resolved_tokens += [
                            Token(")", Type.RRB),
                            Token(")", Type.RRB),
                            Token(")", Type.RRB),
                            token,
                            Token("(", Type.LRB),
                            Token("(", Type.LRB),
                            Token("(", Type.LRB),
                        ]
                case _:
                    resolved_tokens.append(token)
            last_type = token.type
        resolved_tokens += [
            Token(")", Type.RRB),
            Token(")", Type.RRB),
            Token(")", Type.RRB),
            Token(")", Type.RRB),
        ]
        return resolved_tokens


# TODO: Clean all this logging up, move it somewhere else
import logging

# logger = logging.basicConfig(level=logging.NOTSET)
logger = logging.basicConfig(level=logging.CRITICAL)
logger = logging.getLogger(__name__)


def log(level=logging.DEBUG):
    def _decorator(fn):
        def _decorated(*arg, **kwargs):
            logger.log(level, f"Calling {fn.__name__!r}: {arg[1:]} with i={arg[0].i}")
            ret = fn(*arg, **kwargs)
            logger.log(
                level,
                f"Called {fn.__name__!r}: {arg[1:]} with i={arg[0].i} got return value: {ret}",
            )
            return ret

        return _decorated

    return _decorator


class ParserMatcher:
    def __init__(self, tokens: List[Token]) -> None:
        self.tokens = tokens
        self.i = 0

        self.suggestions = set()

    # TODO: Place in report: (' ' | \t)* is implied between all tokens, except when a minimum
    # number of these tokens is requested.
    # TODO: Ensure that all tokens are absorbed (i.e. self.i == self.tokens (give or take))
    # TODO: Add a @reset decorator: Reset self.i if None is returned

    # Step 1: Verify if this production matches
    # Step 2: Return the corresponding Tree

    @property
    def current(self) -> Token:
        if self.i < len(self.tokens):
            return self.tokens[self.i]
        return Token(" ", Type.SPACE)  # TODO: To avoid some errors, e.g. in match

    @property
    def onwards(self) -> List[Token]:
        return self.tokens[self.i :]

    def repeat(self, func: Callable) -> List[Tree]:
        accumulated = []
        while tree := func():
            accumulated.append(tree)
        return accumulated

    def add(self, value: str) -> True:
        self.suggestions.add(value)
        return True
    
    def remove(self, value: str) -> True:
        self.suggestions.remove(value)
        return True

    @log()
    def match(self, *tok_types: Type) -> bool:
        if self.current.type in tok_types:
            try:
                return self.current
            finally:
                self.i += 1
        return None

    def reset(self, initial) -> None:
        self.i = initial

    @log()
    def match_SPL(self) -> Tree:
        """
        SPL = Decl*
        """
        return SPLTree(self.repeat(self.match_Decl))

    @log()
    def match_Decl(self) -> Tree:
        """
        Decl = VarDecl | FunDecl
        """
        if tree := (self.match_VarDecl() or self.match_FunDecl()):
            return tree
        return None

    @log()
    def match_VarDecl(self) -> Tree:
        """
        VarDecl = ('var' | Type) ' '+ id '=' Exp ';'
        """
        initial = self.i

        # Step 1: Verify if this production matches
        if (
            (var_type := (self.match(Type.VAR) or self.match_Type()))
            and (var_id := self.match_id())
            and (eq := self.match(Type.EQ))
            and (exp := self.match_Exp())
            and self.add(f"VarDecl")
            and (semi := self.match(Type.SEMICOLON))
            and self.remove("VarDecl")
        ):
            return VarDeclTree(var_type, var_id, eq, exp, semi)

        self.reset(initial)
        return None

    @log()
    def match_FunDecl(self) -> Tree:
        """
        FunDecl = id '(' [ FArgs ] ')' [ '::' FunType ] '{' VarDecl* Stmt+ '}'
        """
        initial = self.i

        if (
            (fun_id := self.match(Type.ID))
            and (left_round := self.match(Type.LRB))
            and ((fargs := self.match_FArgs()) or True)
            and (right_round := self.match(Type.RRB))
            and (
                (
                    (dcolon := self.match(Type.DOUBLE_COLON))
                    and (fun_type := self.match_FunType())
                )
                or True
            )
            and (left_curly := self.match(Type.LCB))
            and ((body_decl := self.repeat(self.match_VarDecl)) or True)
            and (body_stmt := self.repeat(self.match_Stmt))
            and (right_curly := self.match(Type.RCB))
        ):
            if dcolon and not fun_type:
                # TODO BUG: If we *do* have ::, but no FunType!
                raise Exception
            return FunDeclTree(
                fun_id,
                left_round,
                fargs,
                right_round,
                dcolon,
                fun_type if dcolon else None,
                left_curly,
                body_decl,
                body_stmt,
                right_curly,
            )

        self.reset(initial)
        return None

    @log()
    def match_FArgs(self) -> Tree:
        """
        FArgs = id [ ',' FArgs ]
        """
        initial = self.i

        if arg_id := self.match_id():
            if (comma := self.match(Type.COMMA)) and (fargs := self.match_FArgs()):
                return FArgsTree(arg_id, comma, fargs)
            return FArgsTree(arg_id)

        self.reset(initial)
        return None

    @log()
    def match_FunType(self) -> Tree:
        """
        FunType = [ FTypes ] '->' RetType
        """
        initial = self.i

        ftypes = self.match_FTypes()
        if (arrow := self.match(Type.ARROW)) and (ret_type := self.match_RetType()):
            return FunTypeTree(ftypes, arrow, ret_type)

        self.reset(initial)
        return None

    @log()
    def match_FTypes(self) -> Tree:
        """
        FTypes = Type [ FTypes ]

        Actually, I've gone for:
        FTypes = Type+
        """
        initial = self.i

        if trees := self.repeat(self.match_Type()):
            return FTypesTree(trees)

        self.reset(initial)
        return None

    @log()
    def match_RetType(self) -> Tree:
        """
        RetType = Type | 'Void'

        TODO: Reorder for efficiency?
        """
        initial = self.i

        if ret_type := (self.match_Type() or self.match(Type.VOID)):
            return RetTypeTree(ret_type)

        self.reset(initial)
        return None

    @log()
    def match_Stmt(self) -> Tree:
        """
        Stmt = 'if' '(' Exp ')' '{' Stmt* '}' [ 'else' '{' Stmt* '}' ]
             | 'while' '(' Exp ')' '{' Stmt* '}'
             | id Field '=' Exp ';'
             | FunCall ';'
             | 'return' [ Exp ] ';'
        """
        initial = self.i

        if (
            (if_keyword := self.match(Type.IF))
            and self.add("IfExp")
            and (left_round := self.match(Type.LRB))
            and (exp := self.match_Exp())
            and (right_round := self.match(Type.RRB))
            and self.remove("IfExp")
            and self.add("IfStmt")
            and (left_curly_if := self.match(Type.LCB))
            and ((statements_if := self.repeat(self.match_Stmt)) or True)
            and (right_curly_if := self.match(Type.RCB))
            and self.remove("IfStmt")
        ):
            # 'if' '(' Exp ')' '{' Stmt* '}' [ 'else' '{' Stmt* '}' ]
            if (
                (else_keyword := self.match(Type.ELSE))
                and self.add("IfElseStmt")
                and (left_curly_else := self.match(Type.LCB))
                and ((statements_else := self.repeat(self.match_Stmt)) or True)
                and (right_curly_else := self.match(Type.RCB))
                and self.remove("IfElseStmt")
            ):
                return IfElseStmtTree(
                    if_keyword,
                    left_round,
                    exp,
                    right_round,
                    left_curly_if,
                    statements_if,
                    right_curly_if,
                    else_keyword,
                    left_curly_else,
                    statements_else,
                    right_curly_else,
                )
            # 'if' '(' Exp ')' '{' Stmt* '}'
            return IfStmtTree(
                if_keyword,
                left_round,
                exp,
                right_round,
                left_curly_if,
                statements_if,
                right_curly_if,
            )

        # print(1, self.current)
        if (
            (while_keyword := self.match(Type.WHILE))
            and self.add("WhileExp")
            and (left_round := self.match(Type.LRB))
            and (exp := self.match_Exp())
            and (right_round := self.match(Type.RRB))
            # and self.remove("WhileExp")
            # and self.add("WhileStmt")
            and (left_curly := self.match(Type.LCB))
            and ((statements := self.repeat(self.match_Stmt)) or True)
            and (right_curly := self.match(Type.RCB))
            # and self.remove("WhileStmt")
        ):
            # 'while' '(' Exp ')' '{' Stmt* '}'
            print("Returning While Statement Tree")
            return WhileStmtTree(
                while_keyword,
                left_round,
                exp,
                right_round,
                left_curly,
                statements,
                right_curly,
            )
        # print(2, self.current)
        # breakpoint()

        if (
            (var_id := self.match(Type.ID))
            and ((field := self.match_Field()) or True)
            and (eq := self.match(Type.EQ))
            and self.add("AssignmentExp")
            and (exp := self.match_Exp())
            # and self.remove("AssignmentExp")
            and self.add("AssignmentSemicolon")
            and (semicolon := self.match(Type.SEMICOLON))
            # and self.remove("AssignmentSemicolon")
        ):
            # id Field '=' Exp ';'
            return AssignmentStmtTree(var_id, field, eq, exp, semicolon)

        if (fun_call := self.match_FunCall()) and (
            semicolon := self.match(Type.SEMICOLON)
        ):
            # FunCall ';'
            return FunCallStmtTree(fun_call, semicolon)

        if (
            (return_keyword := self.match(Type.RETURN))
            and ((exp := self.match_Exp()) or True)
            and (semicolon := self.match(Type.SEMICOLON))
        ):
            # 'return' [ Exp ] ';'
            return ReturnStmtTree(return_keyword, exp, semicolon)

        if "WhileExp" in self.suggestions:
            breakpoint()
            return Tree()

        self.reset(initial)
        return None

    @log()
    def match_Field(self) -> Tree:
        """
        Field = [ ( '.' 'hd' | '.' 'tl' | '.' 'fst' | '.' 'snd' ) Field ]

        TODO: Maybe just a list? E.g.
        Field = ( '.' 'hd' | '.' 'tl' | '.' 'fst' | '.' 'snd' )*
        """
        initial = self.i

        if (command := self.match(Type.HD, Type.TL, Type.FST, Type.SND)) and (
            (field := self.match_Field()) or True
        ):
            return FieldTree(command, field)

        self.reset(initial)
        return None

    @log()
    def match_FunCall(self) -> Tree:
        """
        FunCall = id '(' [ ActArgs ] ')'
        """
        initial = self.i

        if (
            fun_id := self.match_id()
            and (left_round := self.match(Type.LRB))
            and ((act_args := self.match_ActArgs()) or True)
            and (right_round := self.match(Type.RRB))
        ):
            return FunCallTree(fun_id, left_round, act_args, right_round)

        self.reset(initial)
        return None

    @log()
    def match_ActArgs(self) -> Tree:
        """
        ActArgs = Exp [ ',' ActArgs ]
        """
        initial = self.i

        if (exp := self.match_Exp()) and (
            ((comma := self.match(Type.COMMA)) and (act_args := self.match_ActArgs()))
            or True
        ):
            return ActArgsTree(exp, comma, act_args if comma else None)

        self.reset(initial)
        return None

    @log()
    def match_Type(self) -> Tree:
        """
        Type = BasicType
             | '(' Type ',' Type ')'
             | '[' Type ']'
             | id
        
        TODO: Why does Type match 'id'?
        """
        initial = self.i
        # Step 1: Verify if this production matches
        if tree := self.match_BasicType():
            return tree

        if (
            (left := self.match(Type.LRB))
            and (type_fst := self.match_Type())
            and (comma := self.match(Type.COMMA))
            and (type_snd := self.match_Type())
            and (right := self.match(Type.RRB))
        ):
            return TypeTupleTree(left, type_fst, comma, type_snd, right)

        if (
            (left := self.match(Type.LSB))
            and (tok_type := self.match_Type())
            and (right := self.match(Type.RSB))
        ):
            return TypeSingleTree(left, tok_type, right)

        if tree := self.match_id():
            return tree

        self.reset(initial)
        return None

    @log()
    def match_BasicType(self) -> Tree:
        """
        BasicType = 'Int'
                  | 'Bool'
                  | 'Char'
        """
        # Step 1: Verify if this production matches
        if token := self.match(Type.INT, Type.BOOL, Type.CHAR):
            # Step 2: Return the corresponding Tree
            return TokenTree(token)
        return None

    @log()
    def match_Exp(self) -> Tree:
        """
        Exp       = (
                  '(' Exp ',' Exp ')'
                  | '(' Exp ')'
                  | Op1 Exp
                  | FunCall

                  | int
                  | char
                  | 'False' | 'True'
                  | '[]'
                  | id Field
                  ) Exp'
        Exp'      = [ Op2 Exp ]

        Exp = id Field
            | Exp Op2 Exp
            | Op1 Exp
            | int
            | char
            | 'False' | 'True'
            | '(' Exp ')'
            | FunCall
            | '[]'
            | '(' Exp ',' Exp ')'
        """
        initial = self.i

        # if (token := self.match(Type.LRB) ...)

        tokens = []
        while token := self.match(
            Type.ID,
            Type.HD,
            Type.FST,
            Type.SND,
            Type.TL,
            Type.NOT,
            Type.MINUS,
            Type.PLUS,
            Type.STAR,
            Type.SLASH,
            Type.PERCENT,
            Type.DEQUALS,
            Type.LT,
            Type.GT,
            Type.LEQ,
            Type.GEQ,
            Type.NEQ,
            Type.AND,
            Type.OR,
            Type.COLON,
            Type.DIGIT,
            Type.QUOTE,
            Type.FALSE,
            Type.TRUE,
            # Type.LRB,
            # Type.RRB,
            Type.COMMA,
            Type.LSB,
            Type.RSB,
        ):
            tokens.append(token)

        if tokens:
            return TempExpTree(tokens)

        self.reset(initial)
        return None

    @log()
    def match_Op2(self) -> Tree:
        """
        Op2 = '+'  | '-' | '*' | '/'  | '%'
            | '==' | '<' | '>' | '<=' | '>=' | '!='
            | '&&' | '||' | ':'
        """
        # Step 1: Verify if this production matches
        if token := self.match(
            Type.PLUS,
            Type.MINUS,
            Type.STAR,
            Type.SLASH,
            Type.PERCENT,
            Type.DEQUALS,
            Type.LT,
            Type.GT,
            Type.LEQ,
            Type.GEQ,
            Type.NEQ,
            Type.AND,
            Type.OR,
            Type.COLON,
        ):
            # Step 2: Return the corresponding Tree
            return TokenTree(token)

        return None

    @log()
    def match_Op1(self) -> Tree:
        """
        Op1 = '!'  | '-'
        """
        if (token := self.match(Type.NOT, Type.MINUS)):
            return TokenTree(token)
        return None

    @log()
    def match_int(self) -> Tree:
        """
        int = digit+
        """
        # Step 1: Verify if this production matches
        initial = self.i

        # minus = self.match(Type.MINUS)
        if digit := self.match(Type.DIGIT):
            return IntTree(digit)

        self.reset(initial)
        return None

    @log()
    def match_id(self) -> Tree:
        # Step 1: Verify if this production matches
        if match := self.match(Type.ID):
            # Step 2: Return the corresponding Tree
            return TokenTree(match)
        return None
