from typing import List
import pytest
from glob import glob

import os
import sys

from tests.test_util import open_file

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session")
def bool_program() -> str:
    return open_file("data/given/valid/bool.spl")


@pytest.fixture(scope="session")
def list_program() -> str:
    return open_file("data/given/valid/list.spl")


def files() -> List[str]:
    return [
        file
        for file in glob("data/given/**/*.spl", recursive=True)
        if "list_ops" not in file
    ]


@pytest.fixture(scope="session", params=files())
def file(request) -> str:
    return request.param
