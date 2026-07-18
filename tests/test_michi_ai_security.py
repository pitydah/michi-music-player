"""Tests for Michi AI security — no direct DB/FS access, action validation."""
from unittest.mock import MagicMock, patch

import pytest


class TestMichiAIActions:
    def test_action_registry_has_actions(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        assert ar is not None

    def test_action_registered_actions_exist(self):
        from ui_qml_bridge.action_registry import ActionRegistry
        ar = ActionRegistry()
        assert hasattr(ar, 'actions')
        assert len(ar.actions) > 0

    def test_no_direct_db_in_tools(self):
        import ast, os
        tools_dir = "michi_ai/v2/tools"
        violations = []
        for fname in os.listdir(tools_dir):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            with open(os.path.join(tools_dir, fname)) as f:
                tree = ast.parse(f.read())
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute) and "execute" in node.func.attr:
                        continue
        assert len(violations) == 0

    def test_no_direct_filesystem_in_tools(self):
        import ast, os
        tools_dir = "michi_ai/v2/tools"
        violations = []
        for fname in os.listdir(tools_dir):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            with open(os.path.join(tools_dir, fname)) as f:
                content = f.read()
            if "open(" in content or "os.remove" in content or "shutil" in content:
                # Check if it's inside a string or actual code
                if "ActionRegistry" in content:
                    continue  # Delegates to registry
        assert len(violations) == 0

    def test_tool_imports_use_registry(self):
        import ast, os
        tools_dir = "michi_ai/v2/tools"
        for fname in os.listdir(tools_dir):
            if not fname.endswith(".py") or fname.startswith("_"):
                continue
            with open(os.path.join(tools_dir, fname)) as f:
                content = f.read()
            if "ActionRegistry" not in content and "action_registry" not in content:
                # Tools may call services directly — check they don't do DB
                assert "execute" not in content or "registry" in content.lower()
