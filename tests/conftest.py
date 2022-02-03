
from typing import List
import pytest

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def bool_lines() -> List[str]:
    with open("data/bool.spl", "r", encoding="utf8") as f:
        return f.readlines()

@pytest.fixture(scope="session")
def empty_lines() -> List[str]:
    return []