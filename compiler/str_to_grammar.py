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
        if symbols:
            self.symbols = list(symbols)
        else:
            self.symbols = []

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

last_range = False


def parse(non_terminal, production, i=0, prev_is_or=False) -> list:
    if i >= len(production):
        return

    symbol = production[i]
    is_star = has_star(symbol)
    is_plus = has_plus(symbol)
    # Terminals and non_terminals

    if is_terminal(symbol) or is_non_terminal(symbol):
        if is_star:
            NT_final[non_terminal].append(
                NT_final[non_terminal][-1].add(Star(symbol[:-1]))
                if prev_is_or
                else Star(symbol[:-1])
            )
        elif is_plus:
            NT_final[non_terminal].append(
                NT_final[non_terminal][-1].add(Plus(symbol[:-1]))
                if prev_is_or
                else Plus(symbol[:-1])
            )
        else:
            NT_final[non_terminal].append(
                NT_final[non_terminal][-1].add(symbol) if prev_is_or else symbol
            )

        prev_is_or = False

    elif symbol == "|":
        # Create or object.
        # If the previous is already an Or object:
        if isinstance(NT_final[non_terminal][-1], Or):
            # Append to it only if the current is not an opening bracket
            NT_final[non_terminal][-1].add(symbol)
        else:
            # Create new OR object
            NT_final[non_terminal][-1] = Or(NT_final[non_terminal][-1])
        prev_is_or = True
    elif symbol == "[" or symbol == "(":
        # Ignore for now, and combine later
        NT_final[non_terminal].append(symbol)
        prev_is_or = False
    elif symbol == "]":
        # All symbols between '[' and ']' are optional.
        # Find '[':
        start_index = NT_final[non_terminal].index("[")
        # Create empty Optional object, to which we can add symbols to.
        NT_final[non_terminal][start_index] = Optional()
        for optional in NT_final[non_terminal][start_index + 1 :]:
            NT_final[non_terminal][start_index].add(optional)
            # TODO: Remove added object
    elif symbol == ")" or symbol == ")*" or symbol == ")+":
        # Check if we have any +/* as next symbol
        try:
            is_star = symbol[1] == "*"
            is_plus = symbol[1] == "+"
        except IndexError:
            is_star = is_plus = False

        start_index = NT_final[non_terminal].index("(")

        try:
            if isinstance(NT_final[non_terminal][start_index - 1], Or):
                prev_is_or = True
        except IndexError:
            prev_is_or = False

        if is_star:
            # Create Star Optional object, to which we can add symbols to.
            NT_final[non_terminal][start_index] = Star()
            for optional in NT_final[non_terminal][start_index + 1 :]:
                NT_final[non_terminal][start_index].add(optional)
        elif is_plus:
            # Create Plus Optional object, to which we can add symbols to.
            NT_final[non_terminal][start_index] = Plus()
            for optional in NT_final[non_terminal][start_index + 1 :]:
                NT_final[non_terminal][start_index].add(optional)

            prev_is_or = False

        else:
            del NT_final[non_terminal][start_index]

        if prev_is_or:
            NT_final[non_terminal].insert(start_index, Or())
            for optional in NT_final[non_terminal][start_index + 1 :]:
                NT_final[non_terminal][start_index].add(optional)

    else:
        print("xxxx", symbol)

    parse(non_terminal, production, i + 1, prev_is_or)
    return


# Todo convert to recursive
for non_terminal, segment in NT.items():
    segment = segment.strip().split(" ")
    parse(non_terminal, segment)
    print(non_terminal, "::= ", NT_final[non_terminal])
