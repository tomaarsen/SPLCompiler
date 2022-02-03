
from typing import List
from compiler import Scanner, Token, Type

def test_scan(bool_lines: List[str]):
    scanner = Scanner()
    tokens = scanner.scan(lines=bool_lines)
    
    expected = [
        Token("xor", Type.ID, 1),
        Token("(", Type.LRB, 1),
        Token("a", Type.ID, 1),
        Token(",", Type.COMMA, 1),
        Token("b", Type.ID, 1)
    ]

    assert tokens[:5] == expected

def test_empty(empty_lines: List[str]):
    scanner = Scanner()
    tokens = scanner.scan(lines=empty_lines)
    assert tokens == []
