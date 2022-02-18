import re
from collections import defaultdict


class Or:
    def __init__(self, *argv) -> None:
        self.symbols = list(argv)

    def add(self, arg):
        self.symbols.append(arg)

    def __repr__(self):
        return f"Or({self.symbols})"


class Star:
    def __init__(self, *symbols) -> None:
        self.symbols = list(symbols)

    def add(self, arg):
        self.symbols.append(arg)

    def __repr__(self):
        return f"Star({self.symbols})"


class Plus:
    def __init__(self, symbols) -> None:
        self.symbols = symbols

    def add(self, arg):
        self.symbols.append(arg)

    def __repr__(self):
        return f"Plus({self.symbols})"


class Optional:
    def __init__(self, *symbols) -> None:
        self.symbols = list(symbols)

    def add(self, arg):
        self.symbols.append(arg)

    def __repr__(self):
        return f"Optional({self.symbols})"


grammar = r"""
SPL       ::= Decl*
Decl      ::= VarDecl
            | FunDecl
VarDecl   ::= ( 'var' | Type ) id  '=' Exp ';'
FunDecl   ::= id '(' [ FArgs ] ')' [ '::' FunType ] '{' VarDecl* Stmt+ '}'
RetType   ::= Type
            | 'Void'
FunType   ::= Type* '->' RetType
Type      ::= BasicType
            | ( '(' Type ',' Type ')' )
            | ( '[' Type ']' )
            | id
BasicType ::= 'Int'
            | 'Bool'
            | 'Char'
FArgs     ::= id [ ',' FArgs ]
Stmt      ::= ( 'if' '(' Exp ')' '{' Stmt* '}' [ 'else' '{' Stmt* '}' ] )
            | ( 'while' '(' Exp ')' '{' Stmt* '}' )
            | ( id Field '=' Exp ';' )
            | ( FunCall ';' )
            | ( 'return' [ Exp ] ';' )
Exp       ::= Eq
Eq        ::= Leq [ Eq' ]
Eq'       ::= ( '==' | '!=' ) Leq [ Eq' ]
Leq       ::= Sum [ Leq' ]
Leq'      ::= ( '<' | '>' | '<=' | '>=' ) Sum [ Leq' ]
Sum       ::= Fact [ Sum' ]
Sum'      ::= ( '+' | '-' | '||' ) Fact [ Sum' ]
Fact      ::= Colon [ Fact' ]
Fact'     ::= ( '*' | '/' | '%' | '&&' ) Colon [ Fact' ]
Colon     ::= Unary [ ':' Colon ]
Unary     ::= ( ( '!' | '-' ) Unary ) | Basic
Basic     ::= ( '(' Exp [ ',' Exp ] ')' ) | int | char | 'False' | 'True' | FunCall | '[]' | ( id Field )
Field     ::= ( '.hd' | '.tl' | '.fst' | '.snd' )*
FunCall   ::= id '(' [ ActArgs ] ')'
ActArgs   ::= Exp [ ',' ActArgs ]
int       ::= digit+
char      ::= '$\texttt{\textquotesingle}$' ( '\b' | '\f' | '\n' | '\r' | '\t' | '\v' | 'ASCII'$\footnotemark{}$ ) '$\texttt{\textquotesingle}$'
id        ::= alpha ( '_' | alphaNum )*
"""
