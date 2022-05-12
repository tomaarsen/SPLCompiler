from dataclasses import dataclass, field
from pprint import pprint
from typing import Iterator, Tuple

from compiler.generation.instruction import Instruction
from compiler.generation.line import Line
from compiler.generation.std_lib import STD_LIB
from compiler.token import Token
from compiler.tree.visitor import Variable, YieldVisitor
from compiler.type import Type

from compiler.tree.tree import (  # isort:skip
    BoolTypeNode,
    CharTypeNode,
    CommaListNode,
    FieldNode,
    FunCallNode,
    FunDeclNode,
    FunTypeNode,
    IfElseNode,
    IntTypeNode,
    ListNode,
    Node,
    Op1Node,
    Op2Node,
    PolymorphicTypeNode,
    ReturnNode,
    SPLNode,
    StmtAssNode,
    StmtNode,
    TupleNode,
    TypeNode,
    VarDeclNode,
    VariableNode,
    VoidTypeNode,
    WhileNode,
)


class Generator:
    def __init__(self, tree: SPLNode) -> None:
        self.generator_yielder = GeneratorYielder()
        # self.tree = self.add_std_lib(tree)
        self.tree = tree

    def generate(self) -> str:
        ssm_code = "\n".join(
            str(line) for line in self.generator_yielder.visit(self.tree)
        )  # + STD_LIB
        return ssm_code


def set_variable(var: Variable, value):
    if var:
        var.set(value)


class GeneratorYielder(YieldVisitor):
    def __init__(self) -> None:
        super().__init__()
        self.variables = {
            "global": {},
            "arguments": {},
            "local": {},
        }
        self.if_else_counter = 0
        self.while_counter = 0
        self.functions = []

    def visit_SPLNode(self, node: SPLNode, *args, **kwargs):
        # yield Line(Instruction.BRA, "main")

        # fun_decls = {}
        # for node in node.body:
        #     match node:
        #         case FunDeclNode():
        #             fun_decls[node.id.text] = node

        #         case VarDeclNode():
        #             yield from self.visit(node, *args, **kwargs)

        var_decls = [node for node in node.body if isinstance(node, VarDeclNode)]

        if var_decls:
            yield Line(Instruction.LINK, len(var_decls))
            yield Line(Instruction.LDR, "MP")
            yield Line(Instruction.STR, "R5", comment="Globals Pointer (GP)")
            for offset, var_decl in enumerate(var_decls, start=1):
                yield from self.visit(var_decl, *args, **kwargs)
                yield Line(
                    Instruction.STL,
                    offset,
                    comment=f"Store {var_decl.id.text!r} locally.",
                )

        fun_decls = {
            node.id.text: node for node in node.body if isinstance(node, FunDeclNode)
        }
        yield from self.visit(fun_decls["main"], *args, **kwargs)
        yield Line(Instruction.HALT)

        while self.functions:
            function = self.functions.pop()
            name = function["name"]
            fun_type = function["type"]
            # TODO: Make print implementations
            if name == "print":
                continue
            fun_decl = fun_decls[name]
            yield from self.visit(fun_decl, *args, fun_type=fun_type, **kwargs)

    def visit_FunDeclNode(self, node: FunDeclNode, *args, fun_type=None, **kwargs):
        # Mark a label from this point onwards
        label = node.id.text + (
            "".join("_" + str(t) for t in fun_type.types) if fun_type else ""
        )
        # print(f"Defining {label}")
        yield Line(label=label)
        # Link to conveniently move MP and SP
        yield Line(Instruction.LINK, len(node.var_decl))
        # Set the function arguments, this is the order that they are above the MP
        if node.args:
            self.variables["arguments"] = {
                token: arg_type
                for token, arg_type in zip(node.args.items, fun_type.types)
            }

        # Place the local variables on the stack
        for offset, var_decl in enumerate(node.var_decl, start=1):
            yield from self.visit(var_decl, *args, in_func=True, **kwargs)
            yield Line(
                Instruction.STL, offset, comment=f"Store {var_decl.id.text!r} locally."
            )

        for stmt in node.stmt:
            yield from self.visit(stmt, *args, in_main=node.id.text == "main", **kwargs)

        # Remove the function and local arguments again
        self.variables["arguments"].clear()
        self.variables["local"].clear()

    def visit_VarDeclNode(self, node: VarDeclNode, *args, in_func=False, **kwargs):
        # No need to pass the in_func any deeper
        exp_type = Variable(None)
        yield from self.visit(node.exp, *args, exp_type=exp_type, **kwargs)

        if in_func:
            # Local variable definition
            self.variables["local"][node.id] = exp_type.var

        else:
            # Global variable definition
            yield Line(Instruction.STH, comment=str(node))
            self.variables["global"][node.id] = exp_type.var

    def print(self, node: FunCallNode, var_type: TypeNode) -> Iterator[Line]:
        match var_type:
            case CharTypeNode():
                # Print as a character
                yield Line(Instruction.TRAP, 1, comment=str(node))

            case IntTypeNode():
                # Print as integer
                yield Line(Instruction.TRAP, 0, comment=str(node))

            case BoolTypeNode():
                # Print as integer
                # yield Line(Instruction.TRAP, 0, comment=str(node))
                yield Line(Instruction.BSR, "_print_Bool", comment=str(node))

            case TupleNode():
                # Print as tuple
                # Print "("
                yield Line(Instruction.LDC, 40, comment="Load '('")
                yield Line(Instruction.TRAP, 1, comment="Print '('")

                # Load the Tuple
                yield Line(Instruction.LDMH, 0, 2, comment="Load left and right")
                yield Line(Instruction.SWP, comment="Put left on top")

                # Recursively print the left node
                # TODO: Passing `node` isn't quite right
                yield from self.print(node, var_type.left)

                # Print ","
                yield Line(Instruction.LDC, 44, comment="Load ','")
                yield Line(Instruction.TRAP, 1, comment="Print ','")

                # Print " "
                yield Line(Instruction.LDC, 32, comment="Load ' '")
                yield Line(Instruction.TRAP, 1, comment="Print ' '")

                # Recursively print the right node
                # TODO: Passing `node` isn't quite right
                yield from self.print(node, var_type.right)

                # Print ")"
                yield Line(Instruction.LDC, 41, comment="Load ')'")
                yield Line(Instruction.TRAP, 1, comment="Print ')'")

            case _:
                # breakpoint()
                raise NotImplementedError(
                    f"Printing {var_type} hasn't been implemented yet"
                )

    def visit_FunCallNode(self, node: FunCallNode, *args, exp_type=None, **kwargs):
        # First handle the function call arguments
        arg_types = []
        if node.args:
            for arg in node.args.items:
                arg_type = Variable(None)
                yield from self.visit(arg, *args, exp_type=arg_type, **kwargs)
                arg_types.append(arg_type.var)

        if node.func.text == "print":
            # Naively determine type of whats being printed
            yield from self.print(node, arg_types[0])

            # No need to clean up the stack here, as TRAP already eats
            # up the one element that is being printed
        # TODO: isEmpty
        else:
            # Store this function to be implemented
            self.functions.append({"name": node.func.text, "type": node.type})

            # Branch to the function that is being called
            label = node.func.text + "".join("_" + str(t) for t in node.type.types)
            yield Line(Instruction.BSR, label, comment=str(node))

            # Clean up the stack that still has the function call arguments on it
            if node.args:
                yield Line(Instruction.AJS, -len(node.args.items))

            # Place the function return back on the stack
            yield Line(Instruction.LDR, "RR")

            # Set the return value as the expression type, if requested higher
            # on the tree
            set_variable(exp_type, type.ret_type)

    def visit_IfElseNode(self, node: IfElseNode, *args, **kwargs):
        then_label = f"Then{self.if_else_counter}"
        else_label = f"Else{self.if_else_counter}"
        end_label = f"IfEnd{self.if_else_counter}"
        self.if_else_counter += 1
        # Condition
        yield from self.visit(node.cond)
        if node.else_body:
            # Jump over the else body, if the condition is true
            yield Line(Instruction.BRT, then_label)
            # Execute the else branch
            yield Line(label=else_label)
            for stmt in node.else_body:
                yield from self.visit(stmt)
            # Jump over body
            yield Line(Instruction.BRA, end_label)
        else:
            # Jump over then branch, if there is no else branch to execute
            yield Line(Instruction.BRF, end_label)

        yield Line(label=then_label)
        for stmt in node.body:
            yield from self.visit(stmt)
        yield Line(label=end_label)

    def visit_WhileNode(self, node: WhileNode, *args, **kwargs):
        condition_label = f"WhileCond{self.while_counter}"
        body_label = f"WhileBody{self.while_counter}"
        end_label = f"WhileEnd{self.while_counter}"
        self.while_counter += 1

        # Condition
        yield Line(label=condition_label)
        yield from self.visit(node.cond)
        # Jump over while body if condition is false
        yield Line(Instruction.BRF, end_label)
        # While body
        yield Line(label=body_label)
        for stmt in node.body:
            yield from self.visit(stmt)
        # Jump back to condition
        yield Line(Instruction.BRA, condition_label)
        yield Line(label=end_label)

    def visit_StmtAssNode(self, node: StmtAssNode, *args, **kwargs):
        yield from self.visit(node.exp, *args, **kwargs)

        # If there are fields, then we want to get the address of the location to update on the stack
        # And then we can STA
        if node.id.field and node.id.field.fields:
            yield from self.visit(
                node.id, *args, get_addr=True, exp_type=None, **kwargs
            )
            yield Line(Instruction.STA, 0, comment=str(node))

        elif node.id.id in self.variables["local"]:
            # Local variables are positive relative to MP, starting from 1
            index = self.variables["local"].index(node.id.id)
            offset = index + 1
            yield Line(Instruction.STL, offset, comment=str(node))

        elif node.id.id in self.variables["arguments"]:
            # Index 0 means we need to get the first argument, so the furthest away one
            # The last argument is at -2
            index = self.variables["arguments"].index(node.id.id)
            offset = index - 1 - len(self.variables["arguments"])
            # Load the function argument using the offset from MP
            yield Line(Instruction.STL, offset, comment=str(node))

        elif node.id.id in self.variables["global"]:
            # Global variables are positive relative to Global Pointer (GP), starting from 1
            index = list(self.variables["global"]).index(node.id.id)
            offset = index + 1

            # Load heap address, and then store the value there
            yield Line(Instruction.LDR, "R5", comment="Load Global Pointer (GP)")
            yield Line(Instruction.LDA, offset, comment="Load Heap address")
            yield Line(Instruction.STA, 0, comment=str(node))

        else:
            # TODO: Implement a backup error saying that there is no such variable,
            # should never occur.
            raise Exception(f"Variable {node.id.id.text!r} does not exist")

    def visit_VariableNode(self, node: VariableNode, *args, exp_type=None, **kwargs):
        # Place the variable on the stack
        yield from self.visit(node.id, *args, exp_type=exp_type, **kwargs)
        # Apply the fields
        yield from self.visit(node.field, *args, exp_type=exp_type, **kwargs)

    def visit_FieldNode(
        self, node: FieldNode, *args, get_addr=False, exp_type=None, **kwargs
    ):
        # If get_addr is True, then for the *last* field we want to put the address instead of the
        # value on the stack.
        # TODO: Verify that exp_type updating doesn't cause issues here with a.fst = 12;

        for i, field in enumerate(node.fields, start=1):
            match field:
                case Token(type=Type.FST) | Token(type=Type.SND):
                    # The SP is now pointing at the top of the stack, which has
                    # the Heap address of the right side of the Tuple.
                    # We offset by -1 if we want the left side,
                    # and 0 if we want the right side
                    if get_addr and i == len(node.fields):
                        # The current stack is already pointing to the SND address
                        # so we only need to update on FST.
                        if field.type == Type.FST:
                            yield Line(Instruction.LDC, -1)
                            yield Line(Instruction.ADD)
                    else:
                        if exp_type:
                            exp_type.set(
                                exp_type.var.left
                                if field.type == Type.FST
                                else exp_type.var.right,
                            )
                        yield Line(
                            Instruction.LDH,
                            -1 if field.type == Type.FST else 0,
                            comment=str(field),
                        )
                # case Token(type=Type.HD):
                #     pass
                # case Token(type=Type.TL):
                #     pass
                case _:
                    raise NotImplementedError("The {field!r} field is not implemented.")

    def visit_FunTypeNode(self, node: FunTypeNode, *args, **kwargs):
        yield from []

    def visit_ReturnNode(self, node: ReturnNode, *args, in_main=False, **kwargs):
        # Recurse into children
        if node.exp:
            yield from self.visit(node.exp, *args, **kwargs)

        # Store return value in RR register, if something was returned
        if node.exp:
            yield Line(Instruction.STR, "RR")
        # Delete local variables
        yield Line(Instruction.UNLINK)
        # Actually return, but only if we're not in main
        if not in_main:
            yield Line(Instruction.RET, comment=str(node))

    def visit_IntTypeNode(self, node: IntTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_CharTypeNode(self, node: CharTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_BoolTypeNode(self, node: BoolTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_VoidTypeNode(self, node: VoidTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_PolymorphicTypeNode(self, node: PolymorphicTypeNode, *args, **kwargs):
        # No need to generate code for this node or its children
        yield from []

    def visit_ListNode(self, node: ListNode, *args, **kwargs):
        # TODO: Note the distinction between if node.exp exists (then it's a type)
        # and if it doesn't (then it's an empty list)
        yield from []

    def visit_TupleNode(self, node: TupleNode, *args, exp_type=None, **kwargs):
        left_exp_type = Variable(None)
        yield from self.visit(node.left, *args, exp_type=left_exp_type, **kwargs)
        right_exp_type = Variable(None)
        yield from self.visit(node.right, *args, exp_type=right_exp_type, **kwargs)
        set_variable(exp_type, TupleNode(left_exp_type.var, right_exp_type.var))
        yield Line(Instruction.STMH, 2, comment=str(node))

    def visit_Op2Node(self, node: Op2Node, *args, exp_type=None, **kwargs):
        # First recurse into both children
        left_exp_type = Variable(None)
        yield from self.visit(node.left, *args, exp_type=left_exp_type, **kwargs)
        yield from self.visit(node.right, *args, **kwargs)

        match node.operator:
            # Boolean operations
            case Token(type=Type.AND):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.AND, comment=str(node))
            case Token(type=Type.OR):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.OR, comment=str(node))

            # Arithmetic operations
            case Token(type=Type.PLUS):
                set_variable(exp_type, IntTypeNode())
                yield Line(Instruction.ADD, comment=str(node))
            case Token(type=Type.MINUS):
                set_variable(exp_type, IntTypeNode())
                yield Line(Instruction.SUB, comment=str(node))
            case Token(type=Type.STAR):
                set_variable(exp_type, IntTypeNode())
                yield Line(Instruction.MUL, comment=str(node))
            case Token(type=Type.SLASH):
                set_variable(exp_type, IntTypeNode())
                yield Line(Instruction.DIV, comment=str(node))
            case Token(type=Type.PERCENT):
                set_variable(exp_type, IntTypeNode())
                yield Line(Instruction.MOD, comment=str(node))

            # Equality
            case Token(type=Type.DEQUALS):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.EQ, comment=str(node))
            case Token(type=Type.NEQ):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.NE, comment=str(node))

            # Arithmetic Equality
            case Token(type=Type.LT):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.LT, comment=str(node))
            case Token(type=Type.GT):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.GT, comment=str(node))
            case Token(type=Type.LEQ):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.LE, comment=str(node))
            case Token(type=Type.GEQ):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.GE, comment=str(node))

            # Lists
            case Token(type=Type.COLON):
                set_variable(exp_type, ListNode(left_exp_type.var))
                # yield Line(Instruction.GE, comment=str(node))

            case _:
                raise NotImplementedError(repr(node.operator))

    def visit_Op1Node(self, node: Op1Node, *args, exp_type=None, **kwargs):
        # First recurse into the child
        yield from self.visit(node.operand, *args, **kwargs)

        match node.operator:
            case Token(type=Type.NOT):
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.NOT, comment=str(node))

            case Token(type=Type.MINUS):
                set_variable(exp_type, IntTypeNode())
                yield Line(Instruction.NEG, comment=str(node))

            case _:
                raise NotImplementedError(repr(node.operator))

    def visit_Token(self, node: Token, *args, exp_type=None, **kwargs):
        match node:
            case Token(type=Type.TRUE):
                # True is encoded as -1
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.LDC, -1, comment=str(node))

            case Token(type=Type.FALSE):
                # True is encoded as 0
                set_variable(exp_type, BoolTypeNode())
                yield Line(Instruction.LDC, 0, comment=str(node))

            case Token(type=Type.ID):
                if node in self.variables["local"]:
                    # Local variables are positive relative to MP, starting from 1
                    index = list(self.variables["local"]).index(node)
                    offset = index + 1
                    set_variable(exp_type, self.variables["local"][node])
                    yield Line(Instruction.LDL, offset, comment=str(node))

                elif node in self.variables["arguments"]:
                    # Index 0 means we need to get the first argument, so the furthest away one
                    # The last argument is at -2
                    index = list(self.variables["arguments"]).index(node)
                    offset = index - 1 - len(self.variables["arguments"])
                    # Load the function argument using the offset from MP
                    set_variable(exp_type, self.variables["arguments"][node])
                    yield Line(Instruction.LDL, offset, comment=str(node))

                elif node in self.variables["global"]:
                    # Global variables are positive relative to Global Pointer (GP), starting from 1
                    index = list(self.variables["global"]).index(node)
                    offset = index + 1

                    set_variable(exp_type, self.variables["global"][node])
                    yield Line(
                        Instruction.LDR, "R5", comment="Load Global Pointer (GP)"
                    )
                    yield Line(Instruction.LDA, offset, comment="Load Heap address")
                    yield Line(Instruction.LDH, 0, comment="Load Heap value")

                else:
                    # TODO: Implement a backup error saying that there is no such variable,
                    # should never occur.
                    raise Exception(f"Variable {node.text!r} does not exist")

            case Token(type=Type.DIGIT):
                # TODO: Disallow overflow somewhere?
                set_variable(exp_type, IntTypeNode())
                yield Line(Instruction.LDC, int(node.text), comment=str(node))

            case Token(type=Type.CHARACTER):
                # Get the character range. Can be larger than length 1 if '\\n' etc.
                character = node.text[1:-1]
                # Remove duplicate escaping, i.e. '\\n' -> '\n'
                character = character.encode().decode("unicode_escape")
                set_variable(exp_type, CharTypeNode())
                yield Line(Instruction.LDC, ord(character), comment=str(node))

            case _:
                raise NotImplementedError(repr(node))
