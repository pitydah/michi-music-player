"""Exactly one WorkerManager instance in production composition."""
from __future__ import annotations

import re

from tests.architecture._helpers import composition_source


def _count_instantiations(class_name: str) -> int:
    source = composition_source()
    return len(re.findall(rf"\b{class_name}\(", source))


def test_single_worker_manager_instance() -> None:
    assert _count_instantiations("WorkerManager") == 1, (
        "Production composition must create exactly one WorkerManager"
    )
