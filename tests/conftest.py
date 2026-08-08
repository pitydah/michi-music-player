"""Root conftest: ensures core package is fully loaded before any test."""
import core  # noqa: F401 — ensures core/__init__.py runs first

from pathlib import Path

import pytest

# PROVISIONAL directory-level classification (policy: directory rules only).
# Every matching rule applies, so a file under tests/qml/settings/ receives
# both "qml" and "quarantine". Classification is additive only: it never
# deselects, skips, or alters collection.
_DIRECTORY_MARKER_RULES: tuple[tuple[str, str], ...] = (
    ("tests/perf/", "performance"),
    ("tests/test_large_library.py", "performance"),
    ("tests/test_performance_baseline.py", "performance"),
    ("tests/e2e/", "integration"),
    ("tests/e2e/", "environmental"),
    ("tests/qml/", "qml"),
    ("tests/qml/settings/", "quarantine"),
    ("tests/qml/tagging/", "quarantine"),
    ("tests/qml/queue/", "quarantine"),
    ("tests/qml/decommission/", "legacy"),
)


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Apply PROVISIONAL directory-level markers to collected tests.

    Path-prefix rules only (fast, deterministic, no collection slowdown).
    The quarantine/legacy rules reflect the FASE 0 baseline audit
    (known-failing vertical clusters) and are PROPOSED, not enforced:
    quarantined tests remain collected and executed by default. No test
    is classified as "stable" here - that marker is opt-in only.
    """
    root = Path(config.rootpath)
    applied: dict[str, int] = {}
    for item in items:
        path = Path(item.path)
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = path.as_posix()
        for prefix, marker in _DIRECTORY_MARKER_RULES:
            if rel.startswith(prefix):
                item.add_marker(marker)
                applied[marker] = applied.get(marker, 0) + 1
    summary = ", ".join(f"{name}={count}" for name, count in sorted(applied.items()))
    print(f"[test-authority] directory markers applied: {summary}")
