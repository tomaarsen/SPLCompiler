from pprint import pprint

from compiler import Scanner
from compiler.grammar import Parser

with open("data/given/valid/bool.spl", "r", encoding="utf8") as f:
    # with open("data/bracketed.spl", "r", encoding="utf8") as f:
    # with open("data/given/invalid/unbalanced_parenthesis2.spl", "r", encoding="utf8") as f:
    program = f.read()

program = """
// At the moment, the only valid Expression is an integer
func (a, b) {
    while (a < 5) {
        a = a + 1;
    }

    if (a != b) {
        return b;
    }
}
"""

program = """
var a = 4 / 1 + 2 * 3 == 5 > 3;
"""


scanner = Scanner(program)
tokens = scanner.scan()
# pprint(tokens)

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
parser = Parser(program, grammar_str=grammar)
# parser.parse(tokens)
