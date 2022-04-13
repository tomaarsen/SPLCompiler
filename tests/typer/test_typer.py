from tests.typer.util import type_tree


def test_typer(valid_typed_file: str):
    """Ensure that we can Type all files without crashing or throwing an exception."""
    type_tree(valid_typed_file)
