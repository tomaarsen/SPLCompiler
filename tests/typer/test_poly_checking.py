import glob

from compiler.error.typer_error import TyperException
from tests.typer.util import type_tree


def test_poly_valid():
    for path in glob.glob("data/tests/typer_error/poly_checking/valid/*"):
        # Ensure that typing this does not throw an exception
        type_tree(path)


def test_poly_invalid():
    for path in glob.glob("data/tests/typer_error/poly_checking/invalid/*"):
        # Ensure that typing this throws an exception
        try:
            type_tree(path)
        except TyperException:
            pass
        else:
            assert (
                False
            ), f"The program in {path!r} should have thrown a TyperException, but did not."
