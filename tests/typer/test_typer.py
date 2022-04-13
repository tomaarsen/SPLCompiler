from tests.typer.util import type_tree


def test_typer(valid_typed_file: str):
    """Ensure that we can Type all files without crashing or throwing an exception."""
    type_tree(valid_typed_file)


def test_duplicate_param_name():
    try:
        type_tree("data/custom/typerError/duplicate_param_name.spl")
    except Exception:  # TODO: TyperError/TyperException
        pass
    else:
        assert False, "Duplicate parameter names in the same function should fail."
