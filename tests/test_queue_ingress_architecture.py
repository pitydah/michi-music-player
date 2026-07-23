"""AST gate enforcing QueueService as the only production queue ingress."""

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

LEGACY_QUEUE_METHODS = frozenset(
    {
        "clear_queue",
        "enqueue",
        "enqueue_next",
        "play_next",
        "play_prev",
        "play_queue",
        "play_queue_index",
        "reorder_queue",
        "set_queue",
        "set_repeat",
        "set_repeat_mode",
        "set_shuffle",
        "toggle_repeat",
        "toggle_shuffle",
    }
)

CANONICAL_QUEUE_RECEIVERS = frozenset(
    {"_queue", "queue", "queue_service", "_queue_service", "_queue_svc"}
)

EXCLUDED_DIRECTORIES = frozenset(
    {
        ".git",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".tox",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "env",
        "node_modules",
        "scripts",
        "tests",
        "tools",
        "venv",
    }
)

OWNER_FILES = frozenset(
    {
        "audio/player.py",
        "audio/player_service.py",
        "core/queue_service.py",
    }
)


def _is_owner(relative_path: Path) -> bool:
    path = relative_path.as_posix()
    return path in OWNER_FILES or path.startswith("audio/backends/")


def _receiver_leaf(receiver: ast.expr) -> str | None:
    if isinstance(receiver, ast.Name):
        return receiver.id
    if isinstance(receiver, ast.Attribute):
        return receiver.attr
    return None


def _receiver_is_allowed(receiver: ast.expr, method: str) -> bool:
    leaf = _receiver_leaf(receiver)
    is_queue_getter = (
        isinstance(receiver, ast.Call)
        and isinstance(receiver.func, ast.Attribute)
        and receiver.func.attr == "_require_queue"
    )
    return (
        leaf in CANONICAL_QUEUE_RECEIVERS
        or is_queue_getter
        or (leaf == "_tas" and method == "play_next")
    )


def _literal_getattr(node: ast.Call) -> tuple[ast.expr, str] | None:
    is_getattr = isinstance(node.func, ast.Name) and node.func.id == "getattr"
    is_builtin_getattr = (
        isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "builtins"
        and node.func.attr == "getattr"
    )
    if not (is_getattr or is_builtin_getattr) or len(node.args) < 2:
        return None

    method_node = node.args[1]
    if isinstance(method_node, ast.Constant) and isinstance(method_node.value, str):
        return node.args[0], method_node.value
    return None


def _find_violations(source: str, relative_path: Path) -> list[str]:
    tree = ast.parse(source, filename=relative_path.as_posix())
    violations: set[tuple[int, str]] = set()

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        receiver: ast.expr
        method: str
        if isinstance(node.func, ast.Attribute):
            receiver = node.func.value
            method = node.func.attr
        else:
            getattr_call = _literal_getattr(node)
            if getattr_call is None:
                continue
            receiver, method = getattr_call

        if method not in LEGACY_QUEUE_METHODS or _receiver_is_allowed(receiver, method):
            continue

        call = f"{ast.unparse(receiver)}.{method}"
        violations.add((node.lineno, call))

    return [
        f"{relative_path.as_posix()}:{line_number} {call}"
        for line_number, call in sorted(violations)
    ]


def _production_python_files() -> list[Path]:
    files = []
    for path in REPO_ROOT.rglob("*.py"):
        relative_path = path.relative_to(REPO_ROOT)
        if EXCLUDED_DIRECTORIES.isdisjoint(relative_path.parts) and not _is_owner(relative_path):
            files.append(path)
    return sorted(files)


def test_legacy_queue_calls_enter_through_queue_service() -> None:
    violations = []
    for path in _production_python_files():
        relative_path = path.relative_to(REPO_ROOT)
        violations.extend(_find_violations(path.read_text(encoding="utf-8"), relative_path))

    assert not violations, "Legacy queue API ingress violations:\n" + "\n".join(violations)


def test_detector_rejects_player_and_accepts_queue_service() -> None:
    source = """\
player.enqueue(track)
queue_service.enqueue(track)
self._require_queue().enqueue(track)
getattr(player, "set_queue")(tracks)
getattr(_queue_svc, "set_queue")(tracks)
"""

    assert _find_violations(source, Path("example.py")) == [
        "example.py:1 player.enqueue",
        "example.py:4 player.set_queue",
    ]
