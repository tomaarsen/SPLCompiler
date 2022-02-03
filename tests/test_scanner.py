
from typing import List
from compiler import Scanner, Token, Type

# import sys
# sys.path.insert(0, "..")
# sys.path.insert(0, "../compiler")

def test_scan(bool_lines: List[str]):
    scanner = Scanner()
    tokens = scanner.scan(lines=bool_lines)
    
    # breakpoint()

    expected = [
        Token("xor", Type.ID, 1),
        Token("(", Type.LRB, 1),
        Token("a", Type.ID, 1),
        Token(",", Type.COMMA, 1),
        Token("b", Type.ID, 1)
    ]

    assert tokens[:5] == expected