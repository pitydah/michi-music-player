"""E12 compatibility checks against the *actual* Player navigation implementation.

Unlike the page registration seam, this verifies that the Player's closed
AppRoute enum, navigation service, shell and wheel resources accept Ecosystem.
This is a static preflight only: it is NOT proof of Qt runtime startup.
"""

from __future__ import annotations

from pathlib import Path

_REQUIRED: tuple[tuple[str, str], ...] = (
    ("src/michi/domain/navigation.py", 'ECOSYSTEM = "ecosystem"'),
    ("src/michi/application/navigation_service.py", "E12_STAGE_INTEGRATION"),
    ("src/michi/presentation/navigation_bridge.py", "ecosystemRoute = Property"),
    ("src/michi/presentation/qml/shell/Sidebar.qml", 'id: "ecosystem"'),
    ("src/michi/presentation/qml/shell/ContentHost.qml", "ecosystemContentLoader"),
    ("pyproject.toml", '"presentation/qml/ecosystem/*.qml"'),
    ("pyproject.toml", '"presentation/qml/ecosystem/*/*.qml"'),
)


def player_navigation_errors(player_repo: Path) -> tuple[str, ...]:
    """Return actionable NO-GO reasons without importing Player or touching it."""
    repo = Path(player_repo)
    errors: list[str] = []
    contents: dict[str, str] = {}
    for relative, required in _REQUIRED:
        source = repo / relative
        if not source.is_file():
            errors.append(f"PLAYER_MISSING: {relative}")
            continue
        if relative not in contents:
            contents[relative] = source.read_text(encoding="utf-8")
        if required not in contents[relative]:
            errors.append(f"PLAYER_E12_NOT_WIRED: {relative}: {required}")
    return tuple(errors)
