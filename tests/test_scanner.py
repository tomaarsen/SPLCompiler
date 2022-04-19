import pytest

from compiler import Scanner, Token, Type
from compiler.error.scanner_error import ScannerException
from tests.test_util import open_file


def test_scan(bool_program: str):
    scanner = Scanner(bool_program)
    tokens = scanner.scan()

    expected = [
        Token("xor", Type.ID, 1),
        Token("(", Type.LRB, 1),
        Token("a", Type.ID, 1),
        Token(",", Type.COMMA, 1),
        Token("b", Type.ID, 1),
    ]

    assert tokens[:5] == expected


def test_empty():
    scanner = Scanner("")
    tokens = scanner.scan()
    assert tokens == []


def test_remove_comments(file: str):
    program: str = open_file(file)
    scanner = Scanner(program)

    modified = scanner.remove_comments(scanner.og_program)
    # Ensure that the number of lines remains the same
    assert len(program.splitlines()) == len(modified.splitlines())
    # Ensure that this method only reduces length, or changes nothing
    assert len(modified) == len(program)

    remodified = scanner.remove_comments(modified)
    # Ensure that reusing `remove_comments` makes no further changes
    assert modified == remodified


def test_scan(file: str):
    program: str = open_file(file)
    scanner = Scanner(program)

    tokens = scanner.scan()
    # Ensure that we get a non-empty list of tokens,
    # unless the program itself is empty or just whitespace.
    # Specifically, ensure no crashing.
    assert len(tokens) > 1 or not program.strip()


def test_DanglingMultiLineCommentError_1():
    program: str = open_file(
        "data/custom/scannerError/DanglingMultiLineCommentError_1.spl"
    )
    scanner = Scanner(program)

    with pytest.raises(ScannerException) as excinfo:
        scanner.scan()
    assert "ScannerError" in str(excinfo) and "-> 5. " in str(excinfo)


def test_DanglingMultiLineCommentError_2():
    program: str = open_file(
        "data/custom/scannerError/DanglingMultiLineCommentError_2.spl"
    )
    scanner = Scanner(program)

    with pytest.raises(ScannerException) as excinfo:
        scanner.scan()
    assert "ScannerError" in str(excinfo) and "-> 5. " in str(excinfo)


def test_EmptyQuoteError():
    program: str = open_file("data/custom/scannerError/EmptyQuoteError.spl")
    scanner = Scanner(program)

    with pytest.raises(ScannerException) as excinfo:
        scanner.scan()
    assert "ScannerError" in str(excinfo) and "-> 6. " in str(excinfo)


def test_LonelyQuoteError_1():
    program: str = open_file("data/custom/scannerError/LonelyQuoteError_1.spl")
    scanner = Scanner(program)

    with pytest.raises(ScannerException) as excinfo:
        scanner.scan()
    assert "ScannerError" in str(excinfo) and "-> 6. " in str(excinfo)


def test_LonelyQuoteError_2():
    program: str = open_file("data/custom/scannerError/LonelyQuoteError_2.spl")
    scanner = Scanner(program)

    with pytest.raises(ScannerException) as excinfo:
        scanner.scan()
    assert "ScannerError" in str(excinfo) and "-> 6. " in str(excinfo)


def test_UnexpectedCharacterError_1():
    program: str = open_file("data/custom/scannerError/UnexpectedCharacterError_1.spl")
    scanner = Scanner(program)

    with pytest.raises(ScannerException) as excinfo:
        scanner.scan()
    assert (
        "ScannerError" in str(excinfo)
        and "'~'" in str(excinfo)
        and "-> 4. " in str(excinfo)
    )


def test_UnexpectedCharacterError_2():
    program: str = open_file("data/custom/scannerError/UnexpectedCharacterError_2.spl")
    scanner = Scanner(program)

    with pytest.raises(ScannerException) as excinfo:
        scanner.scan()
    assert (
        "ScannerError" in str(excinfo)
        and "'~~'" in str(excinfo)
        and "-> 4. " in str(excinfo)
    )


def test_char():
    program: str = open_file("data/custom/tokens.spl")

    scanner = Scanner(program)
    tokens = scanner.scan()
    assert tokens
