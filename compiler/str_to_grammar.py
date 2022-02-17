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
    def __init__(self, symbols) -> None:
        self.symbols = symbols

    def __repr__(self):
        return f"Star({self.symbols})"


class Plus:
    def __init__(self, symbols) -> None:
        self.symbols = symbols

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
Basic     ::= '(' Exp [ ',' Exp ] ')' | int | char | 'False' | 'True' | FunCall | '[]' | id Field
Field     ::= ( '.hd' | '.tl' | '.fst' | '.snd' )*
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
NT[prev_match[1]] = grammar[prev_match.span()[1] :]


def has_star(symbol: str):
    return symbol[-1] == "*"


def has_plus(symbol: str):
    return symbol[-1] == "+"


def is_terminal(symbol: str):
    return symbol[0] == "'"


def is_non_terminal(symbol: str):
    return symbol in NT.keys() or symbol[:-1] in NT.keys()


NT_final = defaultdict(list)
i = 0

last_range = False


def list_rindex(li, x):
    for i in reversed(range(len(li))):
        if li[i] == x:
            return i


prev_is_or = False
for non_terminal, segment in NT.items():
    segment = segment.strip().split(" ")

    for i, s in enumerate(segment):
        is_star = has_star(s)
        is_plus = has_plus(s)
        if prev_is_or:
            prev_is_or = False
            if s != "(" and s != "[":
                NT_final[non_terminal][-1].add(s)
                continue
        if is_terminal(s):
            if is_star:
                NT_final[non_terminal].append(Star(s[:-1]))
            elif is_plus:
                NT_final[non_terminal].append(Plus(s[:-1]))
            else:
                NT_final[non_terminal].append(s)
        elif is_non_terminal(s):
            if is_star:
                NT_final[non_terminal].append(Star(s[:-1]))
            elif is_plus:
                NT_final[non_terminal].append(Plus(s[:-1]))
            else:
                NT_final[non_terminal].append(s)
        elif s == "(" or s == "[":
            NT_final[non_terminal].append(s)
            continue
        elif s == ")":
            open_index = NT_final[non_terminal].index("(")
            del NT_final[non_terminal][open_index]
        elif s == "]":
            open_index = NT_final[non_terminal].index("[")
            NT_final[non_terminal][open_index] = Optional(
                NT_final[non_terminal][open_index + 1]
            )
            del NT_final[non_terminal][open_index + 1]
            for i, e in enumerate(NT_final[non_terminal][open_index + 1 :]):
                NT_final[non_terminal][open_index].add(e)
                del NT_final[non_terminal][open_index + 1]
        elif s == "*":
            if NT_final[non_terminal][-1] == ")":
                index = NT_final[non_terminal].index("(")
                del NT_final[non_terminal][index]
                temp = []
                NT_final[non_terminal] = Star(NT_final[non_terminal][index - 1 :])
        elif s == "|":
            prev_is_or = True
            if NT_final[non_terminal][-1]:
                if not isinstance(NT_final[non_terminal][-1], Or):
                    NT_final[non_terminal][-1] = Or(NT_final[non_terminal][-1])
        else:
            print(s, is_non_terminal(s))

    print(non_terminal, "::= ", NT_final[non_terminal])
