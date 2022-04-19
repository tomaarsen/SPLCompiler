from compiler.tree.tree import (  # isort:skip
    BoolTypeNode,
    FunDeclNode,
    FunTypeNode,
    ListNode,
    SPLNode,
    TupleNode,
    VarDeclNode,
)

from tests.typer.util import type_tree


def test_typer(valid_typed_file: str):
    """Ensure that we can Type all files without crashing or throwing an exception."""
    type_tree(valid_typed_file)


def test_duplicate_param_name():
    try:
        type_tree("data/tests/typer_error/duplicate_param_name.spl")
    except Exception:  # TODO: typer_error/TyperException
        pass
    else:
        assert False, "Duplicate parameter names in the same function should fail."


def test_complex_fields():
    tree = type_tree("data/tests/typer_error/complex_fields.spl")

    match tree:
        case SPLNode(
            body=[
                FunDeclNode(
                    type=FunTypeNode(
                        types=[
                            ListNode(TupleNode(ListNode(a1), b1)),
                            ListNode(TupleNode(ListNode(a2), b2)),
                        ],
                        ret_type=BoolTypeNode(),
                    ),
                    var_decl=[
                        VarDeclNode(type=ListNode(a3)),
                        VarDeclNode(type=a4),
                        VarDeclNode(type=ListNode(a5)),
                        VarDeclNode(type=a6),
                    ],
                ),
            ]
        ):
            assert a1 == a2 == a3 == a4 == a5 == a6
            assert b1 == b2

        case _:
            print(tree)
            raise Exception("Did not match expected typing scheme.")
