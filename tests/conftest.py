from typing import List
import pytest
from glob import glob

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session")
def bool_program() -> str:
    with open("data/given/valid/bool.spl", "r", encoding="utf8") as f:
        return f.read()


def files() -> List[str]:
    return [
        file
        for file in glob("data/given/**/*.spl", recursive=True)
        if "list_ops" not in file
    ]


@pytest.fixture(scope="session", params=files())
def file(request) -> str:
    return request.param
