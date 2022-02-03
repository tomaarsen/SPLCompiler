
from typing import List
import pytest

import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(scope="session")
def bool_program() -> List[str]:
    with open("data/given/valid/bool.spl", "r", encoding="utf8") as f:
        return f.read()
