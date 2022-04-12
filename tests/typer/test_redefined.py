from pprint import pprint

from compiler.error.error import CompilerException
from compiler.error.typerError import TyperException
from tests.typer.util import type_tree

from compiler.tree.tree import (  # isort:skip
    CharTypeNode,
    FunDeclNode,
    FunTypeNode,
    IntTypeNode,
    Node,
    PolymorphicTypeNode,
    SPLNode,
    VarDeclNode,
)


def test_redefined_1():
    """
    Expected:

    double(n) :: Int -> Int {
        return n + n;
    }

    foo(a) :: Int -> Int  {
        Int double = double(a);
        return double;
    }
    """
    tree = type_tree("data/custom/typerError/redefinitions/redefined_1.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    )
                ),
                FunDeclNode(
                    type=FunTypeNode(
                        types=[IntTypeNode()],
                        ret_type=IntTypeNode(),
                    ),
                    var_decl=[VarDeclNode(type=IntTypeNode())],
                ),
            ]
        ):
            pass

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")


def test_redefined_2():
    """
    Expected to fail
    """
    try:
        type_tree("data/custom/typerError/redefinitions/redefined_2.spl")
    except Exception:  # TODO: Turn this into TyperException
        pass
    else:
        assert False, "Redefinition of function should fail"


def test_redefined_3():
    """
    Expected to fail
    """
    try:
        type_tree("data/custom/typerError/redefinitions/redefined_3.spl")
    except Exception:  # TODO: Turn this into TyperException
        pass
    else:
        assert False, "Redefinition of (global) variable should fail"
