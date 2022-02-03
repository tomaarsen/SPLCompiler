
from typing import List
from compiler import Scanner, Token, Type

def test_scan(bool_program: str):
    scanner = Scanner()
    tokens = scanner.scan(bool_program)
    
    expected = [
        Token("xor", Type.ID, 1),
        Token("(", Type.LRB, 1),
        Token("a", Type.ID, 1),
        Token(",", Type.COMMA, 1),
        Token("b", Type.ID, 1)
    ]

    assert tokens[:5] == expected

def test_empty():
    scanner = Scanner()
    tokens = scanner.scan("")
    assert tokens == []

# aa, a0, 00 should work
# 0a should error
