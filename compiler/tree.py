from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from compiler.token import Token


@dataclass
class Tree:
    # children: List[Tree] = field(kw_only=True, default_factory=list)

    # def add_child(self, child: Tree):
    #     self.children.append(child)
    pass


@dataclass
class SPLTree:
    decl: List[DeclTree]


@dataclass
class TokenTree(Tree):
    token: Token


class BasicTypeTree(TokenTree):
    pass


class IDTree(TokenTree):
    pass


@dataclass
class TypeTupleTree(Tree):
    left: Token
    type_fst: TypeTree
    comma: Token
    type_snd: TypeTree
    right: Token


@dataclass
class TypeSingleTree(Tree):
    left: Token
    tok_type: TypeTree
    right: Token


TypeTree = Union[BasicTypeTree, TypeTupleTree, TypeSingleTree, IDTree]


@dataclass
class VarDeclTree(Tree):
    var_type: Token | TypeTree
    var_id: IDTree
    eq: Token
    exp: None  # TODO
    semi: Token


@dataclass
class IntTree(Tree):
    # minus: Optional[Token]
    digit: Token


@dataclass
class BracketTree(Tree):
    open: Token
    close: Token


@dataclass
class FunDeclTree(Tree):
    # FunDecl   = id '(' [ FArgs ] ')' [ '::' FunType ] '{' VarDecl* Stmt+ '}'
    fun_id: List[Tree]

    left_round: Token
    fargs: FArgsTree
    right_round: Token

    double_colon: Optional[Token]
    fun_type: FunTypeTree

    left_curly: Token
    body_decl: List[VarDeclTree]
    body_stmt: List[StmtTree]
    right_curly: Token


@dataclass
class FArgsTree(Tree):
    arg_id: IDTree
    comma: Optional[Token] = None
    fargs: Optional[FArgsTree] = None


@dataclass
class FunTypeTree(Tree):
    ftypes: FTypesTree
    arrow: Optional[Token]
    ret_type: RetTypeTree


@dataclass
class FTypesTree(Tree):
    types: List[TypeTree]


@dataclass
class RetTypeTree(Tree):
    ret_type: TypeTree | Token


@dataclass
class IfStmtTree(Tree):
    # Stmt = 'if' '(' Exp ')' '{' Stmt* '}'
    if_keyword: Token

    left_round: Token
    exp: None  # TODO
    right_round: Token

    left_curly_if: Token
    statements_if: StmtTree
    right_curly_if: Token


@dataclass
class IfElseStmtTree(IfStmtTree):
    # Stmt = 'if' '(' Exp ')' '{' Stmt* '}' [ 'else' '{' Stmt* '}' ]
    else_keyword: Token

    left_curly_else: Token
    statements_else: StmtTree
    right_curly_else: Token


@dataclass
class WhileStmtTree(Tree):
    # Stmt = 'while' '(' Exp ')' '{' Stmt* '}'
    while_keyword: Token

    left_round: Token
    exp: None  # TODO
    right_round: Token

    left_curly: Token
    statements: StmtTree
    right_curly: Token


@dataclass
class AssignmentStmtTree(Tree):
    # Stmt = id Field '=' Exp ';'
    var_id: IDTree
    field: FieldTree
    eq: Token
    exp: None  # TODO
    semicolon: Token


@dataclass
class FunCallStmtTree(Tree):
    fun_call: FunCallTree
    semicolon: Token


@dataclass
class ReturnStmtTree(Tree):
    return_keyword: Token
    exp: Optional[None]  # TODO
    semicolon: Token


@dataclass
class FieldTree(Tree):
    command: Token
    field: Optional[FieldTree]


@dataclass
class FunCallTree(Tree):
    fun_id: Token
    left_round: Token
    act_args: ActArgsTree
    right_round: Token


@dataclass
class ActArgsTree(Tree):
    exp: None
    comma: Optional[Token]
    act_args: Optional[ActArgsTree]


@dataclass
class TupleExpTree(Tree):
    # '(' Exp ',' Exp ')'
    left: Token
    exp_one: ExpTree
    comma: Token
    exp_two: ExpTree
    right: Token


@dataclass
class NestedExpTree(Tree):
    # '(' Exp ')'
    left: Token
    exp: ExpTree
    right: Token


@dataclass
class Op1ExpTree(Tree):
    op: Token
    exp: ExpTree


@dataclass
class EmptyListExpTree(Tree):
    left: Token
    right: Token


@dataclass
class IDExpTree(Tree):
    _id: Token
    field: Optional[FieldTree]


@dataclass
class Op2ExpTree(Tree):
    exp_one: ExpTree
    op: Token
    exp_two: ExpTree


ExpTree = (
    TupleExpTree
    | NestedExpTree
    | Op1ExpTree
    | FunCallTree
    | IntTree
    | Token
    | IDExpTree
)

StmtTree = (
    IfStmtTree
    | IfElseStmtTree
    | WhileStmtTree
    | AssignmentStmtTree
    | FunCallStmtTree
    | ReturnStmtTree
)

DeclTree = VarDeclTree | FunDeclTree
