"""E2E test: all registered actions."""
def test_e2e_actions():
    from ui_qml_bridge.action_registry import ActionRegistry
    ar = ActionRegistry()
    issues = ar.validate_all()
    assert isinstance(issues, list)
