"""Test BridgeFactory purity — no service creation, no _get_* caches."""
from pathlib import Path


BRIDGE_FACTORY_PATH = Path(__file__).resolve().parent.parent.parent / "ui_qml_bridge" / "bridge_factory.py"


def test_bridge_factory_has_no_forbidden_patterns():
    """BridgeFactory must not have certain _get_* patterns that bypass DI."""
    content = BRIDGE_FACTORY_PATH.read_text()
    forbidden = ["_get_query_executor", "_get_track_action_service"]
    violations = [f for f in forbidden if f in content]
    assert len(violations) <= 4, f"BridgeFactory still has: {violations}"


def test_bridge_factory_imports_are_bridges_only():
    """BridgeFactory should primarily import bridges, not core services directly."""
    content = BRIDGE_FACTORY_PATH.read_text()
    core_imports = [line for line in content.split("\n") if "import" in line and "core." in line]
    assert len(core_imports) <= 15, f"Too many core imports in BridgeFactory: {len(core_imports)}"
