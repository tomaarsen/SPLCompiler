import re


class Or:
    def __init__(self, *argv) -> None:
        self.symbols = list(argv)


class Star:
    def __init__(self, symbols) -> None:
        self.symbols = symbols


class Plus:
    def __init__(self, symbols) -> None:
        self.symbols = symbols


class Optional:
    def __init__(self, symbols) -> None:
        self.symbols = symbols


grammar = r"""
SPL       ::= Decl*
Decl      ::= VarDecl
            | FunDecl
VarDecl   ::= ( 'var' | Type ) id  '=' Exp ';'
FunDecl   ::= id '(' [ FArgs ] ')' [ '::' FunType ] '{' VarDecl* Stmt+ '}'
RetType   ::= Type
            | 'Void'
FunType   ::= [ FTypes ] '->' RetType
FTypes    ::= Type [ FTypes ]
Type      ::= BasicType
            | '(' Type ',' Type ')'
            | '[' Type ']'
            | id
BasicType ::= 'Int'
            | 'Bool'
            | 'Char'
FArgs     ::= id [ ',' FArgs ]
Stmt      ::= 'if' '(' Exp ')' '{' Stmt* '}' [ 'else' '{' Stmt* '}' ]
            | 'while' '(' Exp ')' '{' Stmt* '}'
            | id Field '=' Exp ';'
            | FunCall ';'
            | 'return' [ Exp ] ';'
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
Unary     ::= ( '!' | '-' ) Unary | Basic
Basic     ::= '(' Exp ')' | '(' Exp ',' Exp ')'
              | int | char | 'False' | 'True' | FunCall | '[]' | id Field
Field     ::= ( '.' 'hd' | '.' 'tl' | '.' 'fst' | '.' 'snd' )*
FunCall   ::= id '(' [ ActArgs ] ')'
ActArgs   ::= Exp [ ',' ActArgs ]
int       ::= digit+
char      ::= '$\texttt{\textquotesingle}$' ( '\b' | '\f' | '\n' | '\r' | '\t' | '\v' | 'ASCII'$\footnotemark{}$ ) '$\texttt{\textquotesingle}$'
id        ::= alpha ( '_' | alphaNum )*
"""

pattern = re.compile(r"(?P<Non_Literal>\w*'?)\s*::= ", flags=re.X)

matches = pattern.finditer(grammar)

prev_match = None
NT = {}
for match in matches:
    if match is None or match.lastgroup is None:
        raise Exception("Unmatchable")

    if prev_match is None:
        prev_match = match

    # Get the production rule
    production = grammar[prev_match.span()[1] : match.span()[0]]
    # Remove whitespace
    production = re.sub(r"\s+", " ", production)

    # Get non terminals.
    NT[prev_match[1]] = production
    prev_match = match


for non_terminal, segment in NT.items():
    # Find any symbols grouped by ()
    # Adding out ( and ) ensure that we keep the split
    segment = re.split(r"((?<!\')\((?!\').*(?<!\')\)(?!\'))", segment)

    print(segment)

    # Split on | for OR object.
    # segment = re.split(r"(?<!\|)\|(?!\|)", segment)
    # print(segments)
