from compiler import Scanner, Token, Type

from tests.test_util import open_file


def test_scan(bool_program: str):
    scanner = Scanner()
    tokens = scanner.scan(bool_program)

    expected = [
        Token("xor", Type.ID, 1),
        Token("(", Type.LRB, 1),
        Token("a", Type.ID, 1),
        Token(",", Type.COMMA, 1),
        Token("b", Type.ID, 1),
    ]

    assert tokens[:5] == expected


def test_empty():
    scanner = Scanner()
    tokens = scanner.scan("")
    assert tokens == []


def test_remove_comments(file: str):
    program: str = open_file(file)
    scanner = Scanner()

    modified = scanner.remove_comments(program)
    # Ensure that the number of lines remains the same
    assert len(program.splitlines()) == len(modified.splitlines())
    # Ensure that this method only reduces length, or changes nothing
    assert len(modified) <= len(program)

    remodified = scanner.remove_comments(modified)
    # Ensure that reusing `remove_comments` makes no further changes
    assert modified == remodified


def test_scan(file: str):
    program: str = open_file(file)
    scanner = Scanner()

    tokens = scanner.scan(program)
    # Ensure that we get a non-empty list of tokens,
    # unless the program itself is empty or just whitespace.
    # Specifically, ensure no crashing.
    assert len(tokens) > 1 or not program.strip()
