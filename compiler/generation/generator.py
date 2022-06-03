import subprocess  # nosec
from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path
from pprint import pprint
from re import U
from typing import Iterator, List, Tuple

from compiler.generation.instruction import Instruction
from compiler.generation.line import Line
from compiler.generation.std_lib import STD_LIB_LIST
from compiler.generation.utils import ForCounterVisitor
from compiler.token import Token
from compiler.tree import Node
from compiler.tree.visitor import Variable, YieldVisitor
from compiler.type import Type

from compiler.tree.tree import (  # isort:skip
    BoolTypeNode,
    CharTypeNode,
    CommaListNode,
    FieldNode,
    ForNode,
    FunCallNode,
    FunDeclNode,
    FunTypeNode,
    IfElseNode,
    IndexNode,
    IntTypeNode,
    ListAbbrNode,
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
        )
        return ssm_code

    def run(self, ssm_code: str, gui: bool = False) -> str:
        tempfile_path = Path("ssm", "temp.ssm")
        with open(tempfile_path, "w") as f:
            f.write(ssm_code)
        params = (
            ["java", "-jar", "ssm.jar", "--guidelay", "1", "--file", tempfile_path.name]
            if gui
            else ["java", "-jar", "ssm.jar", "--cli", "--file", tempfile_path.name]
        )
        out = subprocess.check_output(  # nosec
            params,
            cwd="ssm",
        ).decode()
        return "".join(out.rsplit("\r\nmachine halted\r\n", 1))


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
        self.for_counter = 0
        self.functions = []
        self.include_function = set()

        self.for_visitor = ForCounterVisitor()

    def types_to_label(self, types: List[TypeNode]) -> str:
        return (
            "".join("_" + str(t) for t in types)
            .replace(" ", "")
            .replace(",", "_")
            .replace("(", "Tuple_")
            .replace(")", "")
            .replace("[", "List_")
            .replace("]", "")
        )

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
        if "main" in fun_decls:
            yield from self.visit(fun_decls["main"], *args, **kwargs)
        yield Line(Instruction.HALT)

        implemented = {"main"}
        while self.functions:
            function = self.functions.pop()
            name = function["name"]
            types = function["type"]
            label = name + self.types_to_label(types)
            if label not in implemented:
                if name == "print":
                    yield from self.print(types)
                elif name == "_eq":
                    yield from self.eq(types[0])
                elif name == "bool":
                    yield from self.bool(types)
                elif name == "_ListAbbr":
                    yield from self.ListAbbr_func()
                elif name == "_deepcopy":
                    yield from self.deep_copy(types[0])
                else:
                    fun_decl = fun_decls[name]
                    yield from self.visit(fun_decl, *args, types=types, **kwargs)
            implemented.add(label)

        while self.include_function:
            function = self.include_function.pop()
            yield from STD_LIB_LIST[function]

    def visit_FunDeclNode(self, node: FunDeclNode, *args, types=None, **kwargs):
        # Mark a label from this point onwards
        label = node.id.text + (self.types_to_label(types) if types else "")
        # print(f"Defining {label}")
        yield Line(label=label)
        # Link to conveniently move MP and SP
        n_local_vars = len(node.var_decl) + self.for_visitor.count(node)
        yield Line(Instruction.LINK, n_local_vars)
        # Set the function arguments, this is the order that they are above the MP
        if node.args:
            self.variables["arguments"] = {
                token: arg_type for token, arg_type in zip(node.args.items, types)
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
        # Set self.get_list_addr=True, such that we know whether a new address should be created for a list
        self.var_decl_assignment = node.id
        yield from self.visit(node.exp, *args, exp_type=exp_type, **kwargs)

        if in_func:
            # Local variable definition
            self.variables["local"][node.id] = exp_type.var

        else:
            # Global variable definition
            self.variables["global"][node.id] = exp_type.var

    def bool(self, var_types: TypeNode) -> Iterator[Line]:
        var_type = var_types[0]
        label = "bool" + self.types_to_label(var_types)
        yield Line(label=label)
        yield Line(Instruction.LINK, 0)
        yield Line(Instruction.LDL, -2)  # Load argument
        match var_type:
            case IntTypeNode():
                # No changes needed
                yield from []
            case PolymorphicTypeNode() | ListNode(body=None):
                # Polymorphic type node must be the empty list
                yield Line(Instruction.LDC, 0)

            case ListNode():
                # Yield not of isEmpty
                self.include_function.add("_is_empty")
                yield Line(Instruction.BSR, "_is_empty")
                yield Line(Instruction.AJS, -1)
                yield Line(Instruction.LDR, "RR")
                yield Line(Instruction.NOT)

            case TupleNode() | CharTypeNode():
                # Always true, since a tuples and characters cannot be empty in SPL
                yield Line(Instruction.LDC, -1)

            case _:
                raise NotImplementedError(
                    f"bool of {var_type} hasn't been implemented yet"
                )

        yield Line(Instruction.STR, "RR")
        yield Line(Instruction.UNLINK)
        yield Line(Instruction.RET)

    def print(self, var_types: TypeNode) -> Iterator[Line]:

        var_type = var_types[0]
        label = "print" + self.types_to_label(var_types)
        yield Line(label=label)
        yield Line(Instruction.LINK, 2 if isinstance(var_type, ListNode) else 0)
        yield Line(Instruction.LDL, -2)  # Load argument

        match var_type:
            case CharTypeNode():
                # Print as a character
                yield Line(Instruction.TRAP, 1)

            case IntTypeNode():
                # Print as integer
                yield Line(Instruction.TRAP, 0)

            case BoolTypeNode():
                # Print as integer
                yield Line(Instruction.BRT, "_print_Bool_Then")

                # Else branch
                yield Line(Instruction.LDC, 70, label="_print_Bool_Else", comment="'F'")
                yield Line(Instruction.TRAP, 1)
                yield Line(Instruction.LDC, 97, comment="'a'")
                yield Line(Instruction.TRAP, 1)
                yield Line(Instruction.LDC, 108, comment="'l'")
                yield Line(Instruction.TRAP, 1)
                yield Line(Instruction.LDC, 115, comment="'s'")
                yield Line(Instruction.TRAP, 1)
                yield Line(Instruction.LDC, 101, comment="'e'")
                yield Line(Instruction.TRAP, 1)
                yield Line(Instruction.BRA, "_print_Bool_End")

                # Then branch
                yield Line(Instruction.LDC, 84, label="_print_Bool_Then", comment="'T'")
                yield Line(Instruction.TRAP, 1)
                yield Line(Instruction.LDC, 114, comment="'r'")
                yield Line(Instruction.TRAP, 1)
                yield Line(Instruction.LDC, 117, comment="'u'")
                yield Line(Instruction.TRAP, 1)
                yield Line(Instruction.LDC, 101, comment="'e'")
                yield Line(Instruction.TRAP, 1)

                yield Line(label="_print_Bool_End")

            # Special print for strings
            case ListNode(CharTypeNode()):
                # Load the length and list pointer
                yield Line(Instruction.LDMH, 0, 2)
                # Store them
                yield Line(Instruction.STL, 2)  # (Next) List pointer
                yield Line(Instruction.STL, 1)  # Length

                # Start loop body, starting with check for length
                yield Line(Instruction.LDL, 1, label=label + "_loop")
                yield Line(Instruction.BRF, label + "_end")
                # Load list address again
                yield Line(Instruction.LDL, 2)
                # Load next value, pointer
                yield Line(Instruction.LDMH, 0, 2)
                # Update list pointer
                yield Line(Instruction.STL, 2)
                # Recursively print the value
                self.functions.append({"name": "print", "type": [var_type.body]})
                yield Line(
                    Instruction.BSR, "print" + self.types_to_label([var_type.body])
                )
                yield Line(Instruction.AJS, -1)
                # Decrease length of remaining list
                yield Line(Instruction.LDL, 1)
                yield Line(Instruction.LDC, 1)
                yield Line(Instruction.SUB)
                yield Line(Instruction.STL, 1)
                # Loop
                yield Line(Instruction.BRA, label + "_loop")

                yield Line(label=label + "_end")

            case ListNode():
                # Print "["
                yield Line(Instruction.LDC, 91, comment="Load '['")
                yield Line(Instruction.TRAP, 1, comment="Print '['")
                if var_type.body:
                    # Load the length and list pointer
                    yield Line(Instruction.LDMH, 0, 2)
                    # Store them
                    yield Line(Instruction.STL, 2)  # (Next) List pointer
                    yield Line(Instruction.STL, 1)  # Length

                    # Start loop body, starting with check for length
                    yield Line(Instruction.LDL, 1, label=label + "_loop")
                    yield Line(Instruction.BRF, label + "_end")
                    # Load list address again
                    yield Line(Instruction.LDL, 2)
                    # Load next value, pointer
                    yield Line(Instruction.LDMH, 0, 2)
                    # Update list pointer
                    yield Line(Instruction.STL, 2)
                    # Recursively print the value
                    self.functions.append({"name": "print", "type": [var_type.body]})
                    yield Line(
                        Instruction.BSR, "print" + self.types_to_label([var_type.body])
                    )
                    yield Line(Instruction.AJS, -1)
                    # Decrease length of remaining list
                    yield Line(Instruction.LDL, 1)
                    yield Line(Instruction.LDC, 1)
                    yield Line(Instruction.SUB)
                    yield Line(Instruction.STL, 1)
                    # Determine whether to print comma
                    yield Line(Instruction.LDL, 1)
                    yield Line(Instruction.BRF, label + "_end")
                    # Else print comma
                    yield Line(Instruction.LDC, 44, comment="Load ','")
                    yield Line(Instruction.TRAP, 1, comment="Print ','")
                    # Print " "
                    yield Line(Instruction.LDC, 32, comment="Load ' '")
                    yield Line(Instruction.TRAP, 1, comment="Print ' '")
                    # Loop
                    yield Line(Instruction.BRA, label + "_loop")

                    yield Line(label=label + "_end")
                # Print "]"
                yield Line(Instruction.LDC, 93, comment="Load ']'")
                yield Line(Instruction.TRAP, 1, comment="Print ']'")

            case TupleNode():
                # Print as tuple
                # Print "("
                yield Line(Instruction.LDC, 40, comment="Load '('")
                yield Line(Instruction.TRAP, 1, comment="Print '('")

                # Load the Tuple
                yield Line(Instruction.LDMH, 0, 2, comment="Load left and right")
                yield Line(Instruction.SWP, comment="Put left on top")

                # Recursively print the left node
                self.functions.append({"name": "print", "type": [var_type.left]})
                yield Line(
                    Instruction.BSR, "print" + self.types_to_label([var_type.left])
                )
                yield Line(Instruction.AJS, -1)

                # Print ","
                yield Line(Instruction.LDC, 44, comment="Load ','")
                yield Line(Instruction.TRAP, 1, comment="Print ','")

                # Print " "
                yield Line(Instruction.LDC, 32, comment="Load ' '")
                yield Line(Instruction.TRAP, 1, comment="Print ' '")

                # Recursively print the right node
                self.functions.append({"name": "print", "type": [var_type.right]})
                yield Line(
                    Instruction.BSR, "print" + self.types_to_label([var_type.right])
                )
                yield Line(Instruction.AJS, -1)

                # Print ")"
                yield Line(Instruction.LDC, 41, comment="Load ')'")
                yield Line(Instruction.TRAP, 1, comment="Print ')'")

            case PolymorphicTypeNode():
                # Polymorphic type node must be the empty list
                # Print "["
                yield Line(Instruction.LDC, 91, comment="Load '['")
                yield Line(Instruction.TRAP, 1, comment="Print '['")
                # Print "]"
                yield Line(Instruction.LDC, 93, comment="Load ']'")
                yield Line(Instruction.TRAP, 1, comment="Print ']'")

            case _:
                raise NotImplementedError(
                    f"Printing {var_type} hasn't been implemented yet"
                )

        yield Line(Instruction.UNLINK)
        yield Line(Instruction.RET)

    def visit_FunCallNode(self, node: FunCallNode, *args, exp_type=None, **kwargs):
        # First handle the function call arguments
        arg_types = []
        if node.args:
            for arg in node.args.items:
                arg_type = Variable(None)
                yield from self.visit(arg, *args, exp_type=arg_type, **kwargs)
                arg_types.append(arg_type.var)

        # if node.func.text == "print":
        #     # Store this function to be implemented
        #     self.functions.append({"name": node.func.text, "type": node.type})

        #     # Branch to the function that is being called
        #     label = node.func.text + self.types_to_label(node.type.types)
        #     yield Line(
        #         Instruction.BSR,
        #         label,
        #         comment=str(node),
        #     )
        if node.func.text == "isEmpty":
            self.include_function.add("_is_empty")
            yield Line(Instruction.BSR, "_is_empty")
            yield Line(Instruction.AJS, -1)
            yield Line(Instruction.LDR, "RR")
            set_variable(exp_type, node.type.ret_type)
        elif node.func.text == "length":
            self.include_function.add("_length")
            yield Line(Instruction.BSR, "_length")
            yield Line(Instruction.AJS, -1)
            yield Line(Instruction.LDR, "RR")
            set_variable(exp_type, node.type.ret_type)
        elif node.func.text == "get_Int":
            yield Line(Instruction.TRAP, 10)
            set_variable(exp_type, node.type.ret_type)
        elif node.func.text == "get_Chr":
            yield Line(Instruction.TRAP, 11)
            set_variable(exp_type, node.type.ret_type)
        elif node.func.text == "get_Str":
            self.functions.append({"name": "_ListAbbr", "type": []})
            self.include_function |= {
                "_get_Str",
                "_prepend_element",
                "_index",
                "_length",
                "_reverse_List_Char",
            }
            # Get the input
            yield Line(Instruction.BSR, "_get_Str")
            yield Line(Instruction.LDR, "RR")
            # Reverse the list
            yield Line(Instruction.BSR, "_reverse_List_Char")
            yield Line(Instruction.AJS, -1)
            yield Line(Instruction.LDR, "RR")

            set_variable(exp_type, node.type.ret_type)
        elif node.func.text == "exit":
            yield Line(Instruction.HALT)
        elif node.func.text == "println":
            self.functions.append({"name": "print", "type": arg_types})
            label = "print" + self.types_to_label(arg_types)
            yield Line(Instruction.BSR, label)
            # print \n
            yield Line(Instruction.LDC, 10)
            yield Line(Instruction.TRAP, 1)
            # Reset SP to before LDC
            yield Line(Instruction.AJS, -1)
        elif node.func.text == "ord" or node.func.text == "chr":
            set_variable(exp_type, node.type.ret_type)
        else:
            # Store this function to be implemented
            self.functions.append({"name": node.func.text, "type": arg_types})

            # Branch to the function that is being called
            label = node.func.text + self.types_to_label(arg_types)
            yield Line(Instruction.BSR, label, comment=str(node))

            # Clean up the stack that still has the function call arguments on it
            if node.args:
                yield Line(Instruction.AJS, -len(node.args.items))

            if node.func.text != "print":
                # Place the function return back on the stack
                yield Line(Instruction.LDR, "RR")

                # Set the return value as the expression type, if requested higher
                # on the tree
                set_variable(exp_type, node.type.ret_type)

    def visit_IfElseNode(self, node: IfElseNode, *args, **kwargs):
        then_label = f"Then{self.if_else_counter}"
        else_label = f"Else{self.if_else_counter}"
        end_label = f"IfEnd{self.if_else_counter}"
        self.if_else_counter += 1
        # Condition
        yield from self.visit(node.cond, *args, **kwargs)
        if node.else_body:
            # Jump over the else body, if the condition is true
            yield Line(Instruction.BRT, then_label)
            # Execute the else branch
            yield Line(label=else_label)
            for stmt in node.else_body:
                yield from self.visit(stmt, *args, **kwargs)
            # Jump over body
            yield Line(Instruction.BRA, end_label)
        else:
            # Jump over then branch, if there is no else branch to execute
            yield Line(Instruction.BRF, end_label)

        yield Line(label=then_label)
        for stmt in node.body:
            yield from self.visit(stmt, *args, **kwargs)
        yield Line(label=end_label)

    def visit_ForNode(self, node: ForNode, *args, exp_type=None, **kwargs):
        # TODO: What if the list is empty?
        # Get the loop type
        exp_type = Variable(None)
        yield from self.visit(node.loop, *args, exp_type=exp_type, **kwargs)

        loop_label = f"ForLoop{self.for_counter}"
        end_label = f"ForEndLink{self.for_counter}"
        true_end_label = f"ForEnd{self.for_counter}"
        self.for_counter += 1

        # Store the variable as a local variable
        self.variables["local"][node.id] = exp_type.var.body
        # yield from self.visit(node.id, *args, **kwargs)

        # Stack: List Pointer 1
        yield Line(Instruction.LDMH, 0, 2)
        # Stack: Length, List Pointer 2
        yield Line(Instruction.LINK, 0, label=loop_label)
        # Stack: Length, List Pointer 2, MP

        yield Line(Instruction.LDL, -2)  # Length
        # Stack: Length, List Pointer 2, MP, Length
        # Skip to end if length is 0
        yield Line(Instruction.BRF, end_label)
        # Otherwise, decrement length
        yield Line(Instruction.LDL, -2)
        yield Line(Instruction.LDC, 1)
        yield Line(Instruction.SUB)
        yield Line(Instruction.STL, -2)
        # Stack: Length, List Pointer 2, MP
        yield Line(Instruction.UNLINK)
        # Stack: Length, List Pointer 2
        yield Line(Instruction.LDMH, 0, 2)
        # Stack: Length, Value, List Pointer 2
        yield Line(Instruction.SWP)
        # Stack: Length, List Pointer 2, Value
        index = list(self.variables["local"]).index(node.id)
        offset = index + 1
        yield Line(Instruction.STL, offset, comment=str(node))
        # Stack: Length, List Pointer 2

        # Run loop body:
        for stmt in node.body:
            kwargs["loop_type"] = "for"
            yield from self.visit(stmt, *args, **kwargs)

        # Continue the loop
        yield Line(Instruction.BRA, loop_label)

        # Unlink and remove the list length and pointer for this for loop
        yield Line(Instruction.UNLINK, label=end_label)
        yield Line(Instruction.AJS, -2, label=true_end_label)

        del self.variables["local"][node.id]

    def visit_WhileNode(self, node: WhileNode, *args, **kwargs):
        condition_label = f"WhileCond{self.while_counter}"
        body_label = f"WhileBody{self.while_counter}"
        end_label = f"WhileEnd{self.while_counter}"
        self.while_counter += 1

        # Condition
        yield Line(label=condition_label)
        yield from self.visit(node.cond, *args, **kwargs)
        # Jump over while body if condition is false
        yield Line(Instruction.BRF, end_label)
        # While body
        yield Line(label=body_label)
        for stmt in node.body:
            kwargs["loop_type"] = "while"
            yield from self.visit(stmt, *args, **kwargs)
        # Jump back to condition
        yield Line(Instruction.BRA, condition_label)
        yield Line(label=end_label)

    def visit_StmtAssNode(self, node: StmtAssNode, *args, exp_type=None, **kwargs):
        exp_type = Variable(None)
        yield from self.visit(node.exp, *args, exp_type=exp_type, **kwargs)

        # If there are fields, then we want to get the address of the location to update on the stack
        # And then we can STMA
        if node.id.field and node.id.field.fields:

            yield from self.visit(
                node.id,
                *args,
                get_addr=True,
                **kwargs,
            )
            # if node.id.id in self.variables["local"]:
            #     self.variables["local"][node.id.id] = exp_type.var
            # elif node.id.id in self.variables["arguments"]:
            #     self.variables["arguments"][node.id.id] = exp_type.var
            # elif node.id.id in self.variables["global"]:
            #     self.variables["global"][node.id.id] = exp_type.var
            # else:
            #     raise Exception(f"Variable {node.id.id.text!r} does not exist")
            yield Line(Instruction.STA, 0, comment=str(node))

        elif node.id.id in self.variables["local"]:
            # Local variables are positive relative to MP, starting from 1
            index = list(self.variables["local"]).index(node.id.id)
            offset = index + 1
            yield Line(Instruction.STL, offset, comment=str(node))
            self.variables["local"][node.id.id] = exp_type.var

        elif node.id.id in self.variables["arguments"]:
            # Index 0 means we need to get the first argument, so the furthest away one
            # The last argument is at -2
            index = list(self.variables["arguments"]).index(node.id.id)
            offset = index - 1 - len(self.variables["arguments"])
            # Load the function argument using the offset from MP
            yield Line(Instruction.STL, offset, comment=str(node))
            self.variables["arguments"][node.id.id] = exp_type.var

        elif node.id.id in self.variables["global"]:
            # Global variables are positive relative to Global Pointer (GP), starting from 1
            index = list(self.variables["global"]).index(node.id.id)
            offset = index + 1

            # Load heap address, and then store the value there
            yield Line(Instruction.LDR, "R5", comment="Load Global Pointer (GP)")
            yield Line(Instruction.STA, offset, comment=str(node))
            self.variables["global"][node.id.id] = exp_type.var

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
        self,
        node: FieldNode,
        *args,
        get_addr=False,
        exp_type=None,
        **kwargs,
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

                case Token(type=Type.HD):
                    # SP points to the variable on which we are applying the .hd/.tl
                    yield Line(Instruction.BSR, "_head")
                    self.include_function.add("_head")
                    yield Line(
                        Instruction.AJS, -1
                    )  # Clear up address of which head was gotten
                    yield Line(Instruction.LDR, "RR")
                    # No need to update if we're on the left side of the assignment, i.e.
                    # if get_addr is True
                    if exp_type and not get_addr:
                        exp_type.set(exp_type.var.body)
                    # If we're assigning, then for the last iteration we want the address
                    # instead of the value. In all other cases, get the value still
                    if not get_addr or i != len(node.fields):
                        yield Line(Instruction.LDA, 0)

                case Token(type=Type.TL):
                    # We are assigning
                    if get_addr and i == len(node.fields):
                        yield Line(Instruction.LINK, 0)
                        # Load new value:
                        yield Line(Instruction.LDL, -2)
                        yield Line(Instruction.LDA, 0)

                        # Load address to replace value
                        yield Line(Instruction.LDL, -1)
                        yield Line(Instruction.LDA, 0)

                        # Set new value:
                        yield Line(Instruction.STA, 0)

                        # At this point, the value has been set, and we need to update the length of the list we are assigning to
                        length_of_remaining_list = [
                            sum(
                                1 if isinstance(x, Token) and x.text == ".tl" else 0
                                for x in group
                            )
                            for _, group in groupby(node.fields)
                        ][-1]
                        # Compute new length:
                        yield Line(Instruction.LDL, -2)
                        yield Line(Instruction.LDA, -1)
                        yield Line(Instruction.LDC, length_of_remaining_list)
                        yield Line(Instruction.ADD)

                        # Start to assign length
                        yield Line(Instruction.LDL, -3)
                        # Based on the number of heads, we need to iterate through the nested lists
                        num_of_heads = sum(
                            [
                                1
                                if isinstance(field, Token) and field.text == ".hd"
                                else 0
                                for field in node.fields
                            ]
                        )
                        for _ in range(0, num_of_heads):
                            yield Line(Instruction.LDA, 0)
                            yield Line(Instruction.LDA, -1)
                        # Set the length
                        yield Line(Instruction.STA, -1)
                        # Clean-up
                        yield Line(Instruction.UNLINK)
                        yield Line(Instruction.AJS, -1)

                        if exp_type:
                            exp_type.set(exp_type.var.body)
                    else:
                        yield Line(Instruction.BSR, "_tail")
                        self.include_function.add("_tail")
                        yield Line(
                            Instruction.AJS, -1
                        )  # Clear up address of which tail was gotten
                        yield Line(Instruction.LDR, "RR")

                case IndexNode():
                    # Discard length and take only list pointer
                    yield Line(Instruction.LDH, 0)
                    # Then load index
                    yield from self.visit(field.exp, *args, **kwargs)
                    # Stack: List pointer, index
                    yield Line(Instruction.BSR, "_index")
                    self.include_function.add("_index")
                    yield Line(
                        Instruction.AJS, -2
                    )  # Clear up address of which tail was gotten
                    yield Line(Instruction.LDR, "RR")
                    # We now have the address, but we usually want the value instead:
                    if not get_addr or i != len(node.fields):
                        yield Line(Instruction.LDH, -1)
                    else:
                        # Otherwise, offset by 1, so we get the address of the value
                        # That way, it can be updated like x[0] = 1
                        yield Line(Instruction.LDC, 1)
                        yield Line(Instruction.SUB)

                    # Update the expected type so higher layers in the AST know which type this is
                    if exp_type and not get_addr:
                        exp_type.set(exp_type.var.body)

                case _:
                    raise NotImplementedError(
                        f"The {field!r} field is not implemented."
                    )

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

    def visit_IntTypeNode(self, node: IntTypeNode, *args, exp_type=None, **kwargs):
        # No need to generate code for this node or its children
        set_variable(exp_type, node)
        yield from []

    def visit_CharTypeNode(self, node: CharTypeNode, *args, exp_type=None, **kwargs):
        # No need to generate code for this node or its children
        set_variable(exp_type, node)
        yield from []

    def visit_BoolTypeNode(self, node: BoolTypeNode, *args, exp_type=None, **kwargs):
        # No need to generate code for this node or its children
        set_variable(exp_type, node)
        yield from []

    def visit_VoidTypeNode(self, node: VoidTypeNode, *args, exp_type=None, **kwargs):
        # No need to generate code for this node or its children
        set_variable(exp_type, node)
        yield from []

    def visit_PolymorphicTypeNode(
        self, node: PolymorphicTypeNode, *args, exp_type=None, **kwargs
    ):
        # No need to generate code for this node or its children
        set_variable(exp_type, node)
        yield from []

    def visit_ListNode(self, node: ListNode, *args, exp_type=None, **kwargs):
        # TODO: Note the distinction between if node.exp exists (then it's a type)
        # and if it doesn't (then it's an empty list)
        set_variable(exp_type, node)

        yield from STD_LIB_LIST["_get_empty_list"]

    def visit_TupleNode(self, node: TupleNode, *args, exp_type=None, **kwargs):
        left_exp_type = Variable(None)
        yield from self.visit(node.left, *args, exp_type=left_exp_type, **kwargs)
        right_exp_type = Variable(None)
        yield from self.visit(node.right, *args, exp_type=right_exp_type, **kwargs)
        set_variable(exp_type, TupleNode(left_exp_type.var, right_exp_type.var))
        yield Line(Instruction.STMH, 2, comment=str(node))

    def eq(self, var_type: TypeNode) -> Iterator[Line]:
        label = "_eq" + self.types_to_label([var_type, var_type])
        yield Line(label=label)
        yield Line(Instruction.LINK, 4 if isinstance(var_type, ListNode) else 0)
        # Load arguments
        yield Line(Instruction.LDL, -3)
        yield Line(Instruction.LDL, -2)

        match var_type:
            case CharTypeNode() | IntTypeNode() | BoolTypeNode():
                # Compare as a character, integer or boolean
                yield Line(Instruction.EQ)

            case ListNode():
                # We set the partial result to False, just in casae the lengths are not the same
                yield Line(Instruction.LDC, 0)  # False
                yield Line(Instruction.STL, 4)  # And store it as the partial result
                # Stack: List 1 addr, List 2 addr
                yield Line(Instruction.LDH, -1)
                yield Line(Instruction.SWP)
                yield Line(Instruction.LDH, -1)
                # Stack: List 2 length, List 1 length
                yield Line(Instruction.EQ)
                # Skip if lengths are not equal
                yield Line(Instruction.BRF, label + "_end")

                # Load 4 local variables: length, list 1 (next) pointer, list 2 (next) pointer, True
                yield Line(Instruction.LDL, -3)
                yield Line(Instruction.LDH, -1)  # Get length of list 1
                yield Line(Instruction.STL, 1)  # And store it
                yield Line(Instruction.LDL, -3)  # Get list 1
                yield Line(Instruction.LDH, 0)
                yield Line(Instruction.STL, 2)  # And store it
                yield Line(Instruction.LDL, -2)  # Get list 2
                yield Line(Instruction.LDH, 0)
                yield Line(Instruction.STL, 3)  # And store it
                yield Line(Instruction.LDC, -1)  # True
                yield Line(Instruction.STL, 4)  # And store it
                # True is the partial result so far

                # Check if length is (both) 0, if so, end with True
                yield Line(Instruction.LDL, 1)
                yield Line(Instruction.BRF, label + "_end")

                # Start loop body
                # Load list 1 address again
                yield Line(Instruction.LDL, 2, label=label + "_loop")
                # Load next value, pointer
                yield Line(Instruction.LDMH, 0, 2)
                # Update list pointer
                yield Line(Instruction.STL, 2)
                # Stack: Value from List 1
                # Load list 2 address again
                yield Line(Instruction.LDL, 3)
                # Load next value, pointer
                yield Line(Instruction.LDMH, 0, 2)
                # Update list pointer
                yield Line(Instruction.STL, 3)
                # Stack: Value from List 1, Value from List 2
                self.functions.append(
                    {"name": "_eq", "type": [var_type.body, var_type.body]}
                )
                yield Line(
                    Instruction.BSR,
                    "_eq" + self.types_to_label([var_type.body, var_type.body]),
                )
                yield Line(Instruction.AJS, -2)
                yield Line(Instruction.LDR, "RR")
                # Stack: boolean
                # Load and update partial result
                yield Line(Instruction.LDL, 4)
                yield Line(Instruction.AND)
                yield Line(Instruction.STL, 4)

                # Decrease length of remaining list
                yield Line(Instruction.LDL, 1)
                yield Line(Instruction.LDC, 1)
                yield Line(Instruction.SUB)
                yield Line(Instruction.STL, 1)

                # Check if we need to loop more
                yield Line(Instruction.LDL, 1)
                yield Line(Instruction.BRT, label + "_loop")

                yield Line(label=label + "_end")
                # Load now no longer partial result
                yield Line(Instruction.LDL, 4)

            case TupleNode():
                # On stack: Tuple 1 addr, Tuple 2 addr
                yield Line(Instruction.LINK, 0)
                # On stack: Tuple 1 addr, Tuple 2 addr, MP

                yield Line(Instruction.LDL, -2)
                yield Line(Instruction.LDH, 0, comment="Load right of Tuple 1")
                # On stack: Tuple 1 addr, Tuple 2 addr, MP, Tuple 1 right
                yield Line(Instruction.LDL, -1)
                yield Line(Instruction.LDH, 0, comment="Load right of Tuple 2")
                # On stack: Tuple 1 addr, Tuple 2 addr, MP, Tuple 1 right, Tuple 2 right

                self.functions.append(
                    {"name": "_eq", "type": [var_type.right, var_type.right]}
                )
                yield Line(
                    Instruction.BSR,
                    "_eq" + self.types_to_label([var_type.right, var_type.right]),
                )
                yield Line(Instruction.AJS, -2)
                yield Line(Instruction.LDR, "RR")
                # On stack: Tuple 1 addr, Tuple 2 addr, MP, boolean

                yield Line(Instruction.LDL, -2)
                yield Line(Instruction.LDH, -1, comment="Load left of Tuple 1")
                # On stack: Tuple 1 addr, Tuple 2 addr, MP, boolean, Tuple 1 left
                yield Line(Instruction.LDL, -1)
                yield Line(Instruction.LDH, -1, comment="Load left of Tuple 2")
                # On stack: Tuple 1 addr, Tuple 2 addr, MP, boolean, Tuple 1 left, Tuple 2 left

                self.functions.append(
                    {"name": "_eq", "type": [var_type.left, var_type.left]}
                )
                yield Line(
                    Instruction.BSR,
                    "_eq" + self.types_to_label([var_type.left, var_type.left]),
                )
                yield Line(Instruction.AJS, -2)
                yield Line(Instruction.LDR, "RR")
                # On stack: Tuple 1 addr, Tuple 2 addr, MP, boolean, boolean

                yield Line(Instruction.AND)
                # On stack: Tuple 1 addr, Tuple 2 addr, MP, boolean

                yield Line(Instruction.STL, -2)
                # On stack: boolean, Tuple 2 addr, MP

                yield Line(Instruction.UNLINK)
                # On stack: boolean, Tuple 2 addr

                yield Line(Instruction.AJS, -1)
                # On stack: boolean

            case _:
                raise NotImplementedError(
                    f"Equality between {var_type} types hasn't been implemented yet"
                )

        yield Line(Instruction.STR, "RR")
        yield Line(Instruction.UNLINK)
        yield Line(Instruction.RET)

    def visit_Op2Node(self, node: Op2Node, *args, exp_type=None, **kwargs):
        # First recurse into both children
        left_exp_type = Variable(None)
        yield from self.visit(node.left, *args, exp_type=left_exp_type, **kwargs)
        right_exp_type = Variable(None)
        yield from self.visit(node.right, *args, exp_type=right_exp_type, **kwargs)

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
            case Token(type=Type.DEQUALS) | Token(type=Type.NEQ):
                set_variable(exp_type, BoolTypeNode())
                types = [left_exp_type.var, right_exp_type.var]
                if isinstance(types[0], ListNode) and isinstance(types[1], ListNode):
                    # If both lists are without a known type, then its simply True
                    if not types[0].body and not types[1].body:
                        # Clean up the stack that still has the function call arguments on it
                        yield Line(Instruction.AJS, -2)
                        yield Line(Instruction.LDC, -1)
                        return

                    # If one of the types is without a known type, then use the other type in the
                    # function call
                    if not types[0].body:
                        types[0] = types[1]
                    if not types[1].body:
                        types[1] = types[0]

                self.functions.append({"name": "_eq", "type": types})
                # Branch to the function that is being called
                label = "_eq" + self.types_to_label(types)
                yield Line(Instruction.BSR, label, comment=str(node))

                # Clean up the stack that still has the function call arguments on it
                yield Line(Instruction.AJS, -2)

                # Place the function return back on the stack
                yield Line(Instruction.LDR, "RR")

                if node.operator.type == Type.NEQ:
                    yield Line(Instruction.NOT, comment=str(node))

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
                # Assume Stack is like:
                #   Value to prepend to list
                #   Pointer to (length, next*)
                """
                We should copy the entire array if either the left or the right side of colon operator contains an ID,
                and that ID is different from the ID we are assigning to.
                """
                copy_left = (
                    isinstance(node.left, Token)
                    and node.left.type == Type.ID
                    and node.left.text != self.var_decl_assignment.text
                )
                copy_right = (
                    isinstance(node.right, Token)
                    and node.right.type == Type.ID
                    and node.right.text != self.var_decl_assignment.text
                )

                if copy_left:
                    type_left = exp_type.var
                    yield Line(
                        Instruction.BSR, "_deep_copy" + self.types_to_label([type_left])
                    )
                    yield Line(Instruction.AJS, -1)
                    yield Line(Instruction.LDR, "RR")

                    self.functions.append({"name": "_deepcopy", "type": [type_left]})

                if copy_right:
                    type_right = exp_type.var
                    yield Line(
                        Instruction.BSR,
                        "_deep_copy" + self.types_to_label([type_right]),
                    )
                    yield Line(Instruction.AJS, -1)
                    yield Line(Instruction.LDR, "RR")

                    self.functions.append({"name": "_deepcopy", "type": [type_right]})

                # Prepend the element to the list
                yield Line(Instruction.BSR, "_prepend_element")
                # Remove element from the stack, but maintain the pointer to the list
                yield Line(Instruction.SWP)
                yield Line(Instruction.AJS, -1)

                if "_prepend_element" not in self.include_function:
                    # yield from STD_LIB_LIST["_prepend_element"]
                    self.include_function.add("_prepend_element")

                # if not isinstance(node.right, ListNode):
                # yield Line(Instruction.STMH, 2, comment=str(node))
                yield from []
            case _:
                raise NotImplementedError(repr(node.operator))

    def deep_copy(self, node: ListNode) -> Iterator[Line]:
        # Assumes the variable to be copied is on top of the stack

        label = "_deep_copy" + self.types_to_label([node])

        # Clear RR
        yield Line(Instruction.LDC, 0)
        yield Line(Instruction.STR, "RR")
        match node:
            case ListNode(body=ListNode()):

                yield Line(label=label)
                yield Line(Instruction.LINK, 0)
                # Top of stack in subroutine is:
                # Length remaining
                # Current pointer to copy from
                # Create a stack as described above:

                # Load length
                yield Line(Instruction.LDL, -2)
                yield Line(Instruction.LDH, -1)
                # Copy the length, for later use
                yield Line(Instruction.LDL, 1)
                # Check if length == 0
                yield Line(Instruction.LDC, 0)
                yield Line(Instruction.EQ)
                # Jump to end of loop if local length == 0
                yield Line(Instruction.BRT, f"_return_new_list_{label}")
                # Set current reference to copy from
                yield Line(Instruction.LDL, -2)
                # Update reference to first element
                # Get reference
                yield Line(Instruction.LDL, 2)
                # Get new reference
                yield Line(Instruction.LDA, 0)
                # Update reference
                yield Line(Instruction.STL, 2)
                yield Line(label=f"_load_loop_{label}")
                # Recursively load all elements of list
                # Get reference
                yield Line(Instruction.LDL, 2)
                # Get element
                yield Line(Instruction.LDA, -1)
                # Update reference
                yield Line(Instruction.LDL, 2)
                yield Line(Instruction.LDA, 0)
                yield Line(Instruction.STL, 2)

                # Decrement length of remaining element
                # Get length
                yield Line(Instruction.LDL, 1)
                # Decrement by 1
                yield Line(Instruction.LDC, 1)
                yield Line(Instruction.SUB)
                # Store it
                yield Line(Instruction.STL, 1)

                # Load the current list
                yield Line(Instruction.LDL, 3)

                yield Line(
                    Instruction.BSR, "_deep_copy" + self.types_to_label([node.body])
                )
                yield Line(Instruction.AJS, -1)
                yield Line(Instruction.LDR, "RR")
                self.functions.append({"name": "_deepcopy", "type": [node.body]})
                yield Line(Instruction.SWP)

                # Check if need to continue the loop
                # Get length
                yield Line(Instruction.LDL, 1)
                # Length == 0?
                yield Line(Instruction.LDC, 0)
                yield Line(Instruction.EQ)
                # Continue loop
                yield Line(Instruction.BRF, f"_load_loop_{label}")
                # At this point all elements of the original list are in order on the stack
                # Reset the local length
                # Load reference to copy from
                yield Line(Instruction.LDL, -2)
                # # Load length
                yield Line(Instruction.LDH, -1)
                # Store the length, for later use
                yield Line(Instruction.STL, 1)
                # Create empty reference
                yield Line(Instruction.LDC, 0)  # Length
                yield Line(Instruction.LDC, 47806)  # Pointer
                yield Line(Instruction.STMH, 2)  # Put on stack
                # Store in RR
                yield Line(Instruction.STR, "RR")
                yield Line(Instruction.LDR, "RR")
                yield Line(label=f"_store_loop_{label}")
                # Recursively store all elements of list, by prepending
                yield Line(Instruction.BSR, f"_prepend_element")
                # Remove prepended element from stack
                yield Line(Instruction.SWP)
                yield Line(Instruction.AJS, -1)
                # Decrement length of remaining element
                # Get length
                yield Line(Instruction.LDL, 1)
                # Decrement by 1
                yield Line(Instruction.LDC, 1)
                yield Line(Instruction.SUB)
                # Store it
                yield Line(Instruction.STL, 1)
                # Check if need to continue the loop
                # Get length
                yield Line(Instruction.LDL, 1)
                # Length == 0?
                yield Line(Instruction.LDC, 0)
                yield Line(Instruction.EQ)
                # Continue loop
                yield Line(Instruction.BRF, f"_store_loop_{label}")
                # End the loop, and return the reference to the new list
                yield Line(label=f"_return_new_list_{label}")

                # If RR is empty, create a new empty list, otherwise return the RR
                yield Line(Instruction.LDR, "RR")
                yield Line(Instruction.LDC, 0)
                yield Line(Instruction.EQ)
                yield Line(Instruction.BRT, f"_return_empty_{label}")
                # Clean-up
                yield Line(Instruction.UNLINK)
                # Replace the pointer with a new pointer
                yield Line(Instruction.RET)

                yield Line(label=f"_return_empty_{label}")
                yield Line(Instruction.LDC, 0)  # Length
                yield Line(Instruction.LDC, 0xBABE)  # Pointer
                yield Line(Instruction.STMH, 2)  # Put on stack
                yield Line(Instruction.STR, "RR")

                # Clean-up
                yield Line(Instruction.UNLINK)
                # Replace the pointer with a new pointer
                yield Line(Instruction.RET)
            case ListNode():
                yield Line(label=label)
                yield Line(Instruction.LINK, 0)
                # Top of stack in subroutine is:
                # Length remaining
                # Current pointer to copy from
                # Create a stack as described above:

                # Load length
                yield Line(Instruction.LDL, -2)
                yield Line(Instruction.LDH, -1)
                # Copy the length, for later use
                yield Line(Instruction.LDL, 1)
                # Check if length == 0
                yield Line(Instruction.LDC, 0)
                yield Line(Instruction.EQ)
                # Jump to end of loop if local length == 0
                yield Line(Instruction.BRT, f"_return_new_list_{label}")
                # Set current reference to copy from
                yield Line(Instruction.LDL, -2)
                # Update reference to first element
                # Get reference
                yield Line(Instruction.LDL, 2)
                # Get new reference
                yield Line(Instruction.LDA, 0)
                # Update reference
                yield Line(Instruction.STL, 2)
                yield Line(label=f"_load_loop_{label}")
                # Recursively load all elements of list
                # Get reference
                yield Line(Instruction.LDL, 2)
                # Get element
                yield Line(Instruction.LDA, -1)
                # Update reference
                yield Line(Instruction.LDL, 2)
                yield Line(Instruction.LDA, 0)
                yield Line(Instruction.STL, 2)

                # Decrement length of remaining element
                # Get length
                yield Line(Instruction.LDL, 1)
                # Decrement by 1
                yield Line(Instruction.LDC, 1)
                yield Line(Instruction.SUB)
                # Store it
                yield Line(Instruction.STL, 1)
                # Check if need to continue the loop
                # Get length
                yield Line(Instruction.LDL, 1)
                # Length == 0?
                yield Line(Instruction.LDC, 0)
                yield Line(Instruction.EQ)
                # Continue loop
                yield Line(Instruction.BRF, f"_load_loop_{label}")
                # At this point all elements of the original list are in order on the stack
                # Reset the local length
                # Load reference to copy from
                yield Line(Instruction.LDL, -2)
                # # Load length
                yield Line(Instruction.LDH, -1)
                # Store the length, for later use
                yield Line(Instruction.STL, 1)
                # Create empty reference
                yield Line(Instruction.LDC, 0)  # Length
                yield Line(Instruction.LDC, 47806)  # Pointer
                yield Line(Instruction.STMH, 2)  # Put on stack
                # Store in RR
                yield Line(Instruction.STR, "RR")
                yield Line(Instruction.LDR, "RR")
                yield Line(label=f"_store_loop_{label}")
                # Recursively store all elements of list, by prepending
                yield Line(Instruction.BSR, f"_prepend_element")
                # Remove prepended element from stack
                yield Line(Instruction.SWP)
                yield Line(Instruction.AJS, -1)
                # Decrement length of remaining element
                # Get length
                yield Line(Instruction.LDL, 1)
                # Decrement by 1
                yield Line(Instruction.LDC, 1)
                yield Line(Instruction.SUB)
                # Store it
                yield Line(Instruction.STL, 1)
                # Check if need to continue the loop
                # Get length
                yield Line(Instruction.LDL, 1)
                # Length == 0?
                yield Line(Instruction.LDC, 0)
                yield Line(Instruction.EQ)
                # Continue loop
                yield Line(Instruction.BRF, f"_store_loop_{label}")
                # End the loop, and return the reference to the new list
                yield Line(label=f"_return_new_list_{label}")

                # If RR is empty, create a new empty list, otherwise return the RR
                yield Line(Instruction.LDR, "RR")
                yield Line(Instruction.LDC, 0)
                yield Line(Instruction.EQ)
                yield Line(Instruction.BRT, f"_return_empty_{label}")
                # Clean-up
                yield Line(Instruction.UNLINK)
                # Replace the pointer with a new pointer
                yield Line(Instruction.RET)

                yield Line(label=f"_return_empty_{label}")
                yield Line(Instruction.LDC, 0)  # Length
                yield Line(Instruction.LDC, 0xBABE)  # Pointer
                yield Line(Instruction.STMH, 2)  # Put on stack
                yield Line(Instruction.STR, "RR")
                # Clean-up
                yield Line(Instruction.UNLINK)
                # Replace the pointer with a new pointer
                yield Line(Instruction.RET)
            # Elements of list
            case _:
                pass

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

    def ListAbbr_func(self):
        base_label = "_ListAbbr"
        end_init_label = f"{base_label}_end_init"
        loop_label = f"{base_label}_loop"
        end_label = f"{base_label}_end"

        left = -3
        current = -2
        step = 1
        pointer = 2

        yield Line(Instruction.LINK, 2, label=base_label)
        yield Line(Instruction.LDL, left)
        yield Line(Instruction.LDL, current)

        # Get step: 1 if lower < upper, otherwise -1
        yield Line(Instruction.LT)
        yield Line(Instruction.STL, step)
        yield Line(Instruction.LDL, step)
        yield Line(Instruction.BRT, end_init_label)
        yield Line(Instruction.LDL, step)
        yield Line(Instruction.LDC, step)
        yield Line(Instruction.ADD)
        yield Line(Instruction.STL, step)

        # Store a pointer to a new empty list
        yield Line(label=end_init_label)
        yield from STD_LIB_LIST["_get_empty_list"]
        yield Line(Instruction.STL, pointer)

        # Loop body: Grab the current
        yield Line(Instruction.LDL, current, label=loop_label)
        yield Line(Instruction.LDL, pointer)
        # Prepend the element to the list
        self.include_function.add("_prepend_element")
        yield Line(Instruction.BSR, "_prepend_element")
        # Remove element from the stack, but maintain the pointer to the list
        yield Line(Instruction.SWP)
        yield Line(Instruction.AJS, -1)
        yield Line(Instruction.STL, pointer)

        # Compare the left (lower, -3) and current (right, upper, -2)
        # If they are the same, go to the end
        yield Line(Instruction.LDL, left)
        yield Line(Instruction.LDL, current)
        yield Line(Instruction.EQ)
        yield Line(Instruction.BRT, end_label)

        # Update the current by step
        yield Line(Instruction.LDL, current)
        yield Line(Instruction.LDL, step)
        yield Line(Instruction.ADD)
        yield Line(Instruction.STL, current)

        yield Line(Instruction.BRA, loop_label)

        # End, store pointer to RR, unlink, and adjust stack to only keep the pointer
        yield Line(Instruction.STR, "RR", label=end_label)
        yield Line(Instruction.UNLINK)
        # yield Line(Instruction.AJS, -2)
        yield Line(Instruction.RET)

    def visit_ListAbbrNode(self, node: ListAbbrNode, *args, exp_type=None, **kwargs):
        # Place lower and upper bounds on the stack
        left_exp_type = Variable(None)
        yield from self.visit(node.left, *args, exp_type=left_exp_type, **kwargs)
        yield from self.visit(node.right, *args, **kwargs)

        yield Line(Instruction.BSR, "_ListAbbr")
        self.functions.append(
            {"name": "_ListAbbr", "type": []}  # Type is irrelevant here
        )
        yield Line(Instruction.AJS, -2)
        yield Line(Instruction.LDR, "RR")

        set_variable(exp_type, ListNode(left_exp_type.var))

    def visit_Token(self, node: Token, *args, exp_type=None, loop_type="", **kwargs):
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
                    yield Line(Instruction.LDA, offset, comment=str(node))

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

            case Token(type=Type.CONTINUE):
                if loop_type == "for":
                    label = f"ForLoop{self.for_counter - 1}"
                elif loop_type == "while":
                    label = f"WhileCond{self.while_counter - 1}"
                yield Line(Instruction.BRA, label)

            case Token(type=Type.BREAK):
                if loop_type == "for":
                    label = f"ForEnd{self.for_counter - 1}"
                elif loop_type == "while":
                    label = f"WhileEnd{self.while_counter - 1}"
                yield Line(Instruction.BRA, label)

            case _:
                raise NotImplementedError(repr(node))
