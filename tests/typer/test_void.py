from compiler.error.typer_error import TyperException
from tests.typer.util import type_tree


def test_void_assign():
    try:
        type_tree("data/tests/typer_error/void/assign.spl")
    except TyperException as e:
        assert "'Void'" in str(e)
        assert "assign" in str(e)
        assert "variable" in str(e)
        assert "-> 2." in str(e)


def test_void_fun_call_arg():
    try:
        type_tree("data/tests/typer_error/void/fun_call_arg.spl")
    except TyperException as e:
        assert "'Void'" in str(e)
        assert "function call argument" in str(e)
        assert "-> 6." in str(e)


def test_void_op2():
    try:
        type_tree("data/tests/typer_error/void/op2.spl")
    except TyperException as e:
        assert "'Void'" in str(e)
        assert "binary operation" in str(e)
        assert "-> 6." in str(e)


def test_void_return():
    try:
        type_tree("data/tests/typer_error/void/return.spl")
    except TyperException as e:
        assert "'Void'" in str(e)
        assert "return" in str(e)
        assert "-> 2." in str(e)


def test_void_tuple():
    try:
        type_tree("data/tests/typer_error/void/tuple.spl")
    except TyperException as e:
        assert "'Void'" in str(e)
        assert "tuple" in str(e)
        assert "-> 6." in str(e)
