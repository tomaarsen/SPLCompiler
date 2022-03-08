from __future__ import annotations

from dataclasses import dataclass, field
from platform import node
from pprint import pprint
from typing import List, Optional

from compiler.grammar_parser import NT
from compiler.token import Token
from compiler.type import Type

# TODO: Type.MINUS *sometimes* left attaches (e.g. -12)
LEFT_ATTACHED_TOKENS = {
    Type.LRB,  # (
    Type.LSB,  # [
    Type.NOT,  # !
}

RIGHT_ATTACHED_TOKENS = {
    Type.RRB,  # )
    Type.RSB,  # ]
    Type.COMMA,
    Type.SEMICOLON,
    Type.HD,
    Type.TL,
    Type.FST,
    Type.SND,
}

SPACES_PER_INDENT = 4


@dataclass
class Tree:
    nt: NT
    c: List[Tree | Token] = field(kw_only=True, default_factory=list)

    def add_child(self, child: Tree) -> None:
        # print(f"Placing {child} in tree of type {self.nt}")
        # breakpoint()
        self.c.append(child)

    def add_children(self, children: List[Tree]) -> None:
        # print(f"Placing {children} in tree of type {self.nt}")
        # breakpoint()
        self.c.extend(children)

    def __iter__(self):
        return self.c

    def __len__(self):
        return len(self.c)

    def __getitem__(self, index: int) -> Tree | Token:
        return self.c[index]

    def __bool__(self) -> bool:
        return True

    def __str__(self):
        depth = 0
        program = ""
        last_token = None

        for token in self.yield_tokens():
            # Modify depth before this token
            if token.type == Type.RCB:  # }
                depth -= 1

            # Ensure indentation is correct
            if program and program[-1] == "\n":
                program += " " * (SPACES_PER_INDENT * depth)

            # Modify depth after this token
            if token.type == Type.LCB:  # {
                depth += 1

            # Remove the last space if this is a tightly bound character, e.g. ';'
            # OR if `token` is the `(` after an `id` (i.e. a function call)
            if (
                program
                and program[-1] == " "
                and (
                    token.type in RIGHT_ATTACHED_TOKENS
                    or (
                        last_token
                        and last_token.type == Type.ID
                        and token.type == Type.LRB
                    )
                )
            ):
                program = program[:-1]

            # Print this token
            program += token.text

            # Print space that follows this token if applicable
            if token.type not in LEFT_ATTACHED_TOKENS:
                program += " "

            # Print a newline if applicable
            if token.type in {Type.RCB, Type.LCB, Type.SEMICOLON}:
                program += "\n"

            last_token = token

        return program.strip()

    def yield_tokens(self) -> str:
        for child in self.c:
            match child:
                case Token():
                    yield child

                case Tree():
                    yield from child.yield_tokens()


@dataclass
class NodeFactory:
    c: List[Tree | Token] = field(kw_only=True, default_factory=list)

    # def add_children(self, child: Tree) -> None:
    # self.c.append(child)

    def add_children(self, children: List[Tree] | Tree) -> None:
        print("Before")
        print(children)
        try:
            self.c.extend(children)
        except TypeError:
            # print("TypeError when extending")
            self.c.append(children)
        print("After")
        print(children)
        print("\n\n")

    def build(self):
        raise NotImplementedError()


@dataclass
class VarDeclFactory(NodeFactory):
    def build(self):
        assert len(self.c) == 5  # nosec

        return VarDeclNode(self.c[0], self.c[1], self.c[3])


@dataclass
class FunDeclFactory(NodeFactory):
    def build(self):
        print(self.c)
        # breakpoint()

        # return VarDeclNode(self.c[0], self.c[1], self.c[3])


@dataclass
class ExpFactory(NodeFactory):
    def build(self):
        # print(self.c)
        # breakpoint()
        if len(self.c) == 2:
            node = self.c[1]
            node.left = self.c[0]
            return node
        elif len(self.c) == 1:
            return self.c[0]
        # return Tree(None, c=self.c)


@dataclass
class ExpPrimeFactory(NodeFactory):
    def build(self):
        if len(self.c) == 2:
            return Op2Node(left=None, operator=self.c[0], right=self.c[1])
        # breakpoint()
        # elif len(self.c) == 1:
        #     return self.c[0]


@dataclass
class BasicFactory(NodeFactory):
    def build(self):
        match self.c:
            # Tuple ( left , right )
            case [
                Token(type=Type.LRB),
                _,
                Token(type=Type.COMMA),
                _,
                Token(type=Type.RRB),
            ]:
                return TupleNode(self.c[1], self.c[3])
            # Bracket ( exp )
            case [Token(type=Type.LRB), _, Token(type=Type.RRB)]:
                return self.c[1]
            # Empty list [ ]
            case [Token(type=Type.LSB), Token(type=Type.RSB)]:
                return ListNode(None)
            case [_]:
                return self.c[0]
        raise Exception()


@dataclass
class TypeFactory(NodeFactory):
    def build(self):
        if len(self.c) == 1:
            return self.c[0]
        print(self.c)
        # breakpoint()


@dataclass
class SPLFactory(NodeFactory):
    def build(self):
        # breakpoint()
        if len(self.c) == 1 and isinstance(self.c[0], SPLNode):
            return self.c[0]
        return SPLNode(self.c)


@dataclass
class BasicTypeFactory(NodeFactory):
    def build(self):
        assert len(self.c) == 1  # nosec
        return self.c[0]


@dataclass
class DefaultFactory(NodeFactory):
    def build(self):
        # print(self.c)
        # breakpoint()
        return self.c


# class ExpHandler:
#     def add_children(*args, **kwargs):

#         return Op2Node(left, op, right)


class Node:
    # def add_children(*args, **kwargs):
    #     raise NotImplementedError()
    pass


@dataclass
class TupleNode(Node):
    left: Node
    right: Node


@dataclass
class SPLNode(Node):
    body: List[Node]


@dataclass
class VarDeclNode(Node):
    type: Token | Node
    id: VariableNode
    exp: Node


@dataclass
class VariableNode(Node):
    id: Token  # (type=Type.ID)


@dataclass
class ListNode(Node):
    body: Optional[Node]


@dataclass
class Op2Node(Node):
    left: Node
    operator: Token
    right: Node

    # def add_children(*args, **kwargs):

    #     return


@dataclass
class Op1Node(Node):
    operator: Token
    operand: Node


"""
Tree(nt=<NT.VarDecl: 2>,
             c=[Token(text='int', type=<Type.ID: 1>),
                Token(text='x', type=<Type.ID: 1>),
                Token(text='=', type=<Type.EQ: '='>),
                Tree(nt=<NT.Exp: 14>,
                     c=[Tree(nt=<NT.Sum: 18>,
                             c=[Token(text='1', type=<Type.DIGIT: 2>),
                                Tree(nt=<NT.Sum': 19>,
                                     c=[Token(text='+', type=<Type.PLUS: '+'>),
                                        Tree(nt=<NT.Basic: 24>,
                                             c=[Token(text='(',
                                                      type=<Type.LRB: '('>),
                                                Tree(nt=<NT.Fact: 20>,
                                                     c=[Token(text='3',
                                                              type=<Type.DIGIT: 2>),
                                                        Tree(nt=<NT.Fact': 21>,
                                                             c=[Token(text='*',
                                                                      type=<Type.STAR: '*'>),
                                                                Token(text='4',
                                                                      type=<Type.DIGIT: 2>)])]),
                                                Token(text=')',
                                                      type=<Type.RRB: ')'>)])])]),
                        Tree(nt=<NT.Eq': 15>,
                             c=[Token(text='==', type=<Type.DEQUALS: '=='>),
                                Token(text='12', type=<Type.DIGIT: 2>)])]),
                Token(text=';', type=<Type.SEMICOLON: ';'>)])])
"""
